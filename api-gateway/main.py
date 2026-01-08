"""
API Gateway Service - ROutes requests to microservices
"""

import logging
import time
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response
import httpx
import os

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('gateway_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('gateway_request_duration_seconds', 'Request duration', ['method', 'endpoint', 'status'])

app = FastAPI(title="API Gateway Service", version="1.0.0")

# Service URLs from environment
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8001")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://order-service:8002")

@app.middleware("http")
async def log_and_metrics(request: Request, call_next):
    start_time = time.time()
    # log request
    logger.info(json.dumps({
        "event": "request_started",
        "method": request.method,
        "path": request.url.path,
        "client": request.client.host,
    }))

    response = await call_next(request)

    # Record metrics
    duration = time.time() - start_time
    REQUEST_DURATION.labels(method=request.method, endpoint=request.url.path, status=response.status_code).observe(duration)

    # Log response
    logger.info(json.dumps({
        "event": "request_completed",
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration": duration
    }))
    return response

@app.get("/")
async def root():
    return {
        "service": "API Gateway",
        "version": "1.0.0",
        "endpoints": {
            "products": "/api/products",
            "orders": "/api/orders",
            "health": "/health",
            "metrics": "/metrics"
        }
    }

@app.get("/health")
async def health():
    """ Health cheeck endpoint"""
    return {
        "status": "healthy",
        "service": "API Gateway",
        "version": "1.0.0",
    }

@app.get("/metrics")
async def metrics():
    """ Prometheus metrics endpoint """
    return Response(content=generate_latest(), media_type="text/plain")

async def proxy_request(service_url: str, path: str, method: str, **kwargs):
    """ Proxy requests to microservices with circuit breaker logic"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{service_url}{path}"
            response = await client.request(method, url, **kwargs)
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code,
            )
    except httpx.TimeoutException:
        logger.error(f"Timeout calling {service_url}{path}")
        raise HTTPException(status_code=504, detail="Service timeout")
    except httpx.RequestError as e:
        logger.error(f"Error calling {service_url}{path}: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")

# Product Service Routes
@app.get("/api/products")
async def get_products(skip: int = 0, limit: int = 10):
    return await proxy_request(
        PRODUCT_SERVICE_URL,
        f"/products?skip={skip}&limit={limit}",
        "GET"
    )

@app.get("/api/products/{product_id}")
async def get_product(product_id: str):
    return await proxy_request(PRODUCT_SERVICE_URL, f"/products/{product_id}", "GET")

@app.post("/api/products")
async def create_product(request: Request):
    body = await request.json()
    return await proxy_request(
        PRODUCT_SERVICE_URL,
        "/products",
        "POST",
        json=body
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)