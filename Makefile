# Veritas Development Makefile
# Usage: make <target>

.PHONY: help setup dev test clean
.PHONY: db-up db-down db-status db-reset db-logs db-shell
.PHONY: api-setup api-dev api-test api-migrate api-shell api-lint
.PHONY: web-setup web-dev web-build web-lint

# Default target
help:
	@echo "Veritas Development Commands"
	@echo ""
	@echo "Setup & Development:"
	@echo "  make setup          - Setup entire project (db + api + web)"
	@echo "  make dev            - Run API and Web servers concurrently"
	@echo "  make test           - Run all tests"
	@echo "  make clean          - Clean build artifacts"
	@echo ""
	@echo "Database (PostgreSQL via Docker):"
	@echo "  make db-up          - Start PostgreSQL (creates if needed)"
	@echo "  make db-down        - Stop PostgreSQL container"
	@echo "  make db-status      - Check PostgreSQL status"
	@echo "  make db-reset       - Reset database (destroy + recreate)"
	@echo "  make db-logs        - View PostgreSQL logs"
	@echo "  make db-shell       - Open psql shell"
	@echo ""
	@echo "API (FastAPI - apps/api):"
	@echo "  make api-setup      - Install Python dependencies"
	@echo "  make api-dev        - Run API dev server on :8000"
	@echo "  make api-test       - Run pytest"
	@echo "  make api-migrate    - Run Alembic migrations"
	@echo "  make api-shell      - Open Python shell with app context"
	@echo "  make api-lint       - Run ruff linter"
	@echo ""
	@echo "Web (Next.js - apps/web):"
	@echo "  make web-setup      - Install Node dependencies"
	@echo "  make web-dev        - Run Next.js dev server on :3000"
	@echo "  make web-build      - Build for production"
	@echo "  make web-lint       - Run ESLint"

# =============================================================================
# Combined Commands
# =============================================================================

setup: db-up api-setup web-setup api-migrate
	@echo "✅ Project setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Copy apps/api/.env.example to apps/api/.env"
	@echo "  2. Copy apps/web/.env.example to apps/web/.env.local"
	@echo "  3. Run 'make dev' to start development servers"

dev:
	@echo "Starting development servers..."
	@echo "API: http://localhost:8000"
	@echo "Web: http://localhost:3000"
	@echo ""
	@trap 'kill 0' INT; \
	(cd apps/api && uv run uvicorn main:app --reload --port 8000) & \
	(cd apps/web && bun dev) & \
	wait

test: api-test
	@echo "✅ All tests passed!"

clean:
	@echo "Cleaning build artifacts..."
	rm -rf apps/api/.pytest_cache
	rm -rf apps/api/__pycache__
	rm -rf apps/api/src/__pycache__
	rm -rf apps/web/.next
	rm -rf apps/web/node_modules/.cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Clean complete!"

# =============================================================================
# Database Commands
# =============================================================================

db-up:
	@if docker ps -a --format '{{.Names}}' | grep -q '^veritas-db$$'; then \
		if docker ps --format '{{.Names}}' | grep -q '^veritas-db$$'; then \
			echo "✅ PostgreSQL (veritas-db) is already running on localhost:5432"; \
		else \
			echo "Starting existing PostgreSQL container..."; \
			docker start veritas-db; \
			sleep 2; \
			echo "✅ PostgreSQL is running on localhost:5432"; \
		fi \
	else \
		echo "Creating PostgreSQL container..."; \
		docker compose up -d postgres; \
		echo "Waiting for PostgreSQL to be ready..."; \
		sleep 3; \
		echo "✅ PostgreSQL is running on localhost:5432"; \
	fi

db-down:
	@echo "Stopping PostgreSQL..."
	@docker stop veritas-db 2>/dev/null || true
	@echo "✅ PostgreSQL stopped"

db-status:
	@if docker ps --format '{{.Names}}' | grep -q '^veritas-db$$'; then \
		echo "✅ PostgreSQL (veritas-db) is running"; \
		docker exec veritas-db pg_isready -U postgres; \
	elif docker ps -a --format '{{.Names}}' | grep -q '^veritas-db$$'; then \
		echo "⚠️  PostgreSQL (veritas-db) exists but is stopped"; \
		echo "   Run 'make db-up' to start it"; \
	else \
		echo "❌ PostgreSQL (veritas-db) container not found"; \
		echo "   Run 'make db-up' to create it"; \
	fi

db-reset:
	@echo "Resetting database..."
	@echo "⚠️  This will delete all data in the database!"
	@docker stop veritas-db 2>/dev/null || true
	@docker rm veritas-db 2>/dev/null || true
	@docker volume rm veritas_postgres_data 2>/dev/null || true
	docker compose up -d postgres
	@sleep 3
	@echo "✅ Database reset complete"

db-logs:
	docker logs -f veritas-db

db-shell:
	docker exec -it veritas-db psql -U postgres -d veritas

# =============================================================================
# API Commands (FastAPI)
# =============================================================================

api-setup:
	@echo "Installing API dependencies..."
	cd apps/api && uv sync --all-extras
	@echo "✅ API dependencies installed"

api-dev:
	@echo "Starting API server on http://localhost:8000..."
	cd apps/api && uv run uvicorn main:app --reload --port 8000

api-test:
	@echo "Running API tests..."
	cd apps/api && uv run pytest -v

api-test-fast:
	@echo "Running API tests (fail fast)..."
	cd apps/api && uv run pytest -x -v

api-test-cov:
	@echo "Running API tests with coverage..."
	cd apps/api && uv run pytest --cov=src --cov-report=html
	@echo "Coverage report: apps/api/htmlcov/index.html"

api-migrate:
	@echo "Running database migrations..."
	cd apps/api && uv run alembic upgrade head
	@echo "✅ Migrations complete"

api-migrate-new:
	@read -p "Migration message: " msg; \
	cd apps/api && uv run alembic revision --autogenerate -m "$$msg"

api-shell:
	cd apps/api && uv run python -i -c "from main import app; from src.database import *; from src.models import *; print('App context loaded')"

api-lint:
	cd apps/api && uv run ruff check src tests

api-lint-fix:
	cd apps/api && uv run ruff check --fix src tests

# =============================================================================
# Web Commands (Next.js)
# =============================================================================

web-setup:
	@echo "Installing Web dependencies..."
	cd apps/web && bun install
	@echo "✅ Web dependencies installed"

web-dev:
	@echo "Starting Web server on http://localhost:3000..."
	cd apps/web && bun dev

web-build:
	@echo "Building Web for production..."
	cd apps/web && bun run build

web-lint:
	cd apps/web && bun lint

web-start:
	@echo "Starting production Web server..."
	cd apps/web && bun start

# =============================================================================
# Utility Commands
# =============================================================================

# Check if required tools are installed
check-deps:
	@echo "Checking dependencies..."
	@command -v docker >/dev/null 2>&1 || (echo "❌ Docker not installed" && exit 1)
	@command -v uv >/dev/null 2>&1 || (echo "❌ uv not installed (pip install uv)" && exit 1)
	@command -v bun >/dev/null 2>&1 || (echo "❌ bun not installed (curl -fsSL https://bun.sh/install | bash)" && exit 1)
	@command -v tesseract >/dev/null 2>&1 || (echo "⚠️  Tesseract not installed (brew install tesseract)")
	@echo "✅ All required dependencies installed"

# Show running services
ps:
	@echo "Docker containers:"
	@docker compose ps
	@echo ""
	@echo "Local processes:"
	@lsof -i :3000 -i :8000 2>/dev/null || echo "No servers running on :3000 or :8000"

# Kill development servers
kill:
	@echo "Killing development servers..."
	@lsof -ti :3000 | xargs kill -9 2>/dev/null || true
	@lsof -ti :8000 | xargs kill -9 2>/dev/null || true
	@echo "✅ Servers stopped"
