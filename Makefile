.PHONY: help build up down logs test clean deploy

help:
	@echo "Available commands:"
	@echo "  make build    - Build all Docker images"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make logs     - View logs"
	@echo "  make test     - Run tests"
	@echo "  make clean    - Remove all containers and volumes"
	@echo "  make deploy   - Deploy to Kubernetes"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services starting... waiting for health checks..."
	@sleep 10
	@echo "API Gateway: http://localhost:8000"
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3000 (admin/admin)"

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	docker-compose exec api-gateway pytest tests/ -v
	docker-compose exec product-service pytest tests/ -v
	docker-compose exec order-service pytest tests/ -v

clean:
	docker-compose down -v
	docker system prune -af

deploy:
	kubectl apply -f kubernetes/namespace.yaml
	kubectl apply -f kubernetes/configmap.yaml
	kubectl apply -f kubernetes/secrets.yaml
	kubectl apply -f kubernetes/deployment.yaml
	@echo "Waiting for deployments..."
	kubectl wait --for=condition=available --timeout=300s deployment --all -n ecommerce

k8s-delete:
	kubectl delete -f kubernetes/deployment.yaml
	kubectl delete namespace ecommerce

setup:
	chmod +x scripts/*.sh
	./scripts/setup.sh