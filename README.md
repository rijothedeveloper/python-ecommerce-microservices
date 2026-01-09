# E-Commerce Microservices Platform

A production-ready cloud-native microservices application built with Python, FastAPI, Docker, and Kubernetes.

## 🏗️ Architecture

- **API Gateway**: Request routing, load balancing, circuit breaker
- **Product Service**: Product catalog management with caching
- **Order Service**: Order processing with service-to-service communication
- **Infrastructure**: PostgreSQL, Redis, Prometheus, Grafana

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- kubectl (for Kubernetes deployment)

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ecommerce-microservices.git
cd ecommerce-microservices
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Start services:
```bash
make up
# or
docker-compose up --build
```

4. Access services:
- API Gateway: http://localhost:8000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

### Testing the API
```bash
# Create a product
curl -X POST http://localhost:8000/api/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Laptop",
    "description": "High-performance laptop",
    "price": 999.99,
    "stock": 50
  }'

# Get products
curl http://localhost:8000/api/products

# Create an order
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "product_id": 1,
    "quantity": 2
  }'
```

## 📊 Monitoring

- **Metrics**: Prometheus collects metrics from all services
- **Visualization**: Grafana dashboards for real-time monitoring
- **Health Checks**: Each service exposes `/health` endpoint

## ☸️ Kubernetes Deployment
```bash
# Deploy to Kubernetes
make deploy

# Check status
kubectl get pods -n ecommerce

# Delete deployment
make k8s-delete
```

## 🧪 Testing
```bash
# Run all tests
make test

# Run specific service tests
docker-compose exec product-service pytest tests/ -v
```

## 📚 Documentation

- [API Documentation](http://localhost:8000/docs)
- [Architecture Guide](./docs/architecture.md)
- [Deployment Guide](./docs/deployment.md)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📝 License

MIT License