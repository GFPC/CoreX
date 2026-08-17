# GFP CoreX — Developer Makefile
# Run `make help` to see all available commands

.PHONY: help install dev gui test test-cov lint format type-check pre-commit \
        docker-up docker-down docker-scale docker-logs docker-build \
        bench metrics clean

# ─────────────────────────────────────────────
#  Help
# ─────────────────────────────────────────────
help:
	@echo ""
	@echo "  ⚡ GFP CoreX — Available Commands"
	@echo "  ─────────────────────────────────"
	@echo "  install        Install all dependencies (prod + dev)"
	@echo "  dev            Start development server (hot reload)"
	@echo "  gui            Start Tkinter GUI launcher"
	@echo ""
	@echo "  test           Run test suite"
	@echo "  test-cov       Run tests with HTML coverage report"
	@echo "  lint           Run Ruff linter"
	@echo "  format         Auto-format code with Ruff"
	@echo "  type-check     Run mypy type checker"
	@echo "  pre-commit     Install and run pre-commit hooks"
	@echo ""
	@echo "  docker-up      Start dev environment (App + MySQL + Redis)"
	@echo "  docker-down    Stop all containers"
	@echo "  docker-scale   Start production scale (Nginx + 3×App + Prometheus + Grafana)"
	@echo "  docker-logs    Tail logs from all containers"
	@echo ""
	@echo "  bench          Run k6 load test against the scale stack"
	@echo "  metrics        Print a sample of live Prometheus metrics"
	@echo ""
	@echo "  clean          Remove .pyc files and caches"
	@echo ""

# ─────────────────────────────────────────────
#  Installation
# ─────────────────────────────────────────────
install:
	poetry install

# ─────────────────────────────────────────────
#  Development
# ─────────────────────────────────────────────
dev:
	uvicorn src.gfpcorex.main:app --reload --host 0.0.0.0 --port 8000

gui:
	python backend_gui.py

# ─────────────────────────────────────────────
#  Testing
# ─────────────────────────────────────────────
test:
	python -m pytest tests/ -v

test-cov:
	python -m pytest tests/ --cov=src/gfpcorex --cov-report=html --cov-report=term-missing
	@echo "Coverage HTML report: htmlcov/index.html"

# ─────────────────────────────────────────────
#  Code Quality
# ─────────────────────────────────────────────
lint:
	python -m ruff check .

format:
	python -m ruff format .
	python -m ruff check --fix .

type-check:
	python -m mypy src/

pre-commit:
	pre-commit install
	pre-commit run --all-files

# ─────────────────────────────────────────────
#  Docker
# ─────────────────────────────────────────────
docker-up:
	docker compose up -d
	@echo "✅ Dev environment running:"
	@echo "   API    → http://localhost:8000"
	@echo "   Docs   → http://localhost:8000/docs"
	@echo "   Health → http://localhost:8000/health"

docker-down:
	docker compose down
	docker compose -f docker-compose.scale.yml down

docker-scale:
	docker compose -f docker-compose.scale.yml up -d --build
	@echo "✅ Scale environment running:"
	@echo "   API (LB)   → http://localhost:80"
	@echo "   Prometheus → http://localhost:9090"
	@echo "   Grafana    → http://localhost:3000 (admin/admin)"

docker-logs:
	docker compose logs -f

docker-build:
	docker build -t gfp-corex:latest .

# ─────────────────────────────────────────────
#  Load testing & observability
# ─────────────────────────────────────────────
bench:
	k6 run bench/load-test.js

metrics:
	@curl -s http://localhost/metrics | head -n 40

# ─────────────────────────────────────────────
#  Cleanup
# ─────────────────────────────────────────────
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -name ".coverage" -delete
	@echo "🧹 Cleaned up caches"
