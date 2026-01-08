"""
Order Service - Manages customer orders
"""
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Enum as SQLEnum, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from enum import Enum
import os
import logging
import httpx

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/orders")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8001")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, index=True)
    customer_email = Column(String)
    product_id = Column(Integer)
    quantity = Column(Integer)
    total_price = Column(Float)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)


# Pydantic models
class OrderCreate(BaseModel):
    customer_name: str = Field(..., min_length=1)
    customer_email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class Order(BaseModel):
    id: int
    customer_name: str
    customer_email: str
    product_id: int
    quantity: int
    total_price: float
    status: OrderStatus
    created_at: datetime

    class Config:
        from_attributes = True

app = FastAPI(title="Order Service", version="1.0.0")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_product_info(product_id: int):
    """Call product service to get product details"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}")
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.error(f"Product service returned {response.status_code}")
                return None
    except httpx.RequestError as e:
        logger.error(f"Error calling product service: {str(e)}")
        return None

@app.on_event("startup")
async def startup_event():
    logger.info("Order Service starting up")

@app.get("/health")
async def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "order-service",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/orders", response_model=list[Order])
async def get_orders(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """Get all orders with pagination"""
    orders = db.query(OrderDB).offset(skip).limit(limit).all()
    return [Order.model_validate(o) for o in orders]

@app.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get a specific order by ID"""
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return Order.model_validate(order)


@app.post("/orders", response_model=Order, status_code=201)
async def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    """Create a new order"""
    logger.info(f"Creating order for customer: {order.customer_name}")

    product = await get_product_info(order.product_id)
    if not product:
        raise HTTPException(status_code=400, detail="Product not found or unavailable")

    if product['stock'] < order.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    total_price = product['price'] * order.quantity

    db_order = OrderDB(
        **order.model_dump(),
        total_price=total_price,
        status=OrderStatus.PENDING
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    logger.info(f"Order created with ID: {db_order.id}, total: ${total_price:.2f}")
    return Order.model_validate(db_order)


@app.patch("/orders/{order_id}/status")
async def update_order_status(
        order_id: int,
        status: OrderStatus,
        db: Session = Depends(get_db)
):
    """Update order status"""
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    old_status = order.status
    order.status = status
    db.commit()

    logger.info(f"Order {order_id} status changed: {old_status} -> {status}")
    return {"message": "Status updated", "order_id": order_id, "new_status": status}

@app.get("/orders/customer/{email}", response_model=list[Order])
async def get_customer_orders(email: str, db: Session = Depends(get_db)):
    """Get all orders for a customer"""
    orders = db.query(OrderDB).filter(OrderDB.customer_email == email).all()
    return [Order.model_validate(o) for o in orders]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)