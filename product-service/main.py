"""
Product service - manages product catalog
"""
import datetime

from fastapi import FastAPI, HTTPException, Depends
import redis
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, Session
import logging
import os
import json

from sqlalchemy.orm import declarative_base, Session

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/products")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

#  Redis setup
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

class ProductDB(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    price = Column(Float)
    stock = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)

#  Pydantic models
class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=1000)
    price: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)

class Product(ProductCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

app = FastAPI(title="Product Service", version="1.0.0")

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
async def startup_event():
    logger.info("Product Service starting up")

@app.get("/health")
async def health(db: Session = Depends(get_db)):
    try:
        #  check database connection
        db.execute("SELLECT 1")
        # check redis connection
        redis.client.ping()
        return {
            "status": "healthy",
            "service": "product-service",
            "database": "connected",
            "cache": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Service unhealthy")

@app.get("/products", response_model=list[Product])
async def get_products(skip: int = 0, limit: int = 0, db: Session = Depends(get_db)):
    """Get all products with pagination"""
    #  try cache first
    cache_key = f"products-{skip}-{limit}"
    cached = redis_client.get(cache_key)
    if cached:
        logger.info(f"Cache hit for {cache_key}")
        return json.loads(cached)

    logger.info(f"Cache miss for {cache_key}, querying database")
    products = db.query(ProductDB).offset(skip).limit(limit).all()
    result = [Product.model_validate(p) for p in products]

    # Cache for 5 minutes
    redis.client.setex(cache_key, 300, json.dumps([p.model_dump(mode='json') for p in result]))

    return result


@app.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a specific product by ID"""
    cache_key = f"product:{product_id}"
    cached = redis_client.get(cache_key)

    if cached:
        logger.info(f"Cache hit for {cache_key}")
        return json.loads(cached)

    product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    result = Product.model_validate(product)
    redis_client.setex(cache_key, 300, result.model_dump_json())

    return result

@app.post("/products", response_model=Product, status_code=201)
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product"""
    logger.info(f"Creating new product {product.name}")

    db_product = ProductDB(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    #  Invalidate cache
    redis.client.delete("products:*")

    logger.info(f"Product created with ID: {db_product.id}")
    return product.model_validate(db_product)

@app.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: int, product: ProductCreate, db: Session = Depends(get_db)):
    """Update a product"""
    logger.info(f"Updating product {product_id}")
    db_product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    for key, value in product.model_dump().items():
        setattr(db_product, key, value)

    db.commit()
    db.refresh(db_product)

    # Invalidate cache
    redis_client.delete(f"product:{product_id}")
    redis_client.delete("products:*")

    return product.model_validate(db_product)


@app.delete("/products/{product_id}")
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete a product"""
    db_product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(db_product)
    db.commit()

    # Invalidate cache
    redis_client.delete(f"product:{product_id}")
    redis_client.delete("products:*")

    return {"message": "Product deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)