# Makefile for Vine & Fig API Docker operations

.PHONY: help build up down logs restart clean dev test shell

help: ## Show this help message
	@echo "Vine & Fig Building Designer API - Docker Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

build: ## Build the Docker image
	docker-compose build

up: ## Start the API in production mode
	docker-compose up -d
	@echo "API running at http://localhost:8080"
	@echo "API docs at http://localhost:8080/docs"

down: ## Stop and remove containers
	docker-compose down

logs: ## View logs (real-time)
	docker-compose logs -f

restart: ## Restart the API service
	docker-compose restart api

clean: ## Stop containers and remove volumes
	docker-compose down -v

dev: ## Start in development mode with hot-reload
	docker-compose -f docker-compose.dev.yml up

dev-build: ## Build and start in development mode
	docker-compose -f docker-compose.dev.yml up --build

test: ## Run tests in container
	docker-compose run --rm api pytest

shell: ## Open a shell in the running container
	docker-compose exec api /bin/bash

ps: ## Show running containers
	docker-compose ps

rebuild: ## Rebuild without cache
	docker-compose build --no-cache

health: ## Check API health
	@curl -s http://localhost:8080/health | python -m json.tool

stats: ## Show container resource usage
	docker stats vine-and-fig-api --no-stream

prune: ## Clean up unused Docker resources
	docker system prune -a --volumes
