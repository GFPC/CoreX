<div align="center">

# ⚡ GFP CoreX

### Production-Ready Multi-Tenant FastAPI Platform

*Dynamic plugin execution · Per-tenant DB & Redis isolation · AST security sandbox · Horizontal scaling*

---

[![CI/CD](https://github.com/fealx15/CoreX/actions/workflows/ci.yml/badge.svg)](https://github.com/fealx15/CoreX/actions)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0_async-D71F00?logo=sqlalchemy&logoColor=white)](https://docs.sqlalchemy.org)
[![Redis](https://img.shields.io/badge/Redis-async_pool-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-compose_+_scale-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![Nginx](https://img.shields.io/badge/Nginx-load_balancer-009639?logo=nginx&logoColor=white)](https://nginx.org)
[![Prometheus](https://img.shields.io/badge/Prometheus-metrics-E6522C?logo=prometheus&logoColor=white)](https://prometheus.io)
[![Tests](https://img.shields.io/badge/tests-14_passed-22c55e?logo=pytest&logoColor=white)](./tests)
[![Coverage](https://img.shields.io/badge/coverage-52%25-yellow)](./tests)
[![Ruff](https://img.shields.io/badge/code_style-ruff-orange)](https://docs.astral.sh/ruff)
[![License](https://img.shields.io/badge/license-MIT-informational)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.3.0-blueviolet)](CHANGELOG.md)

</div>

---

## 🧭 What is GFP CoreX?

**GFP CoreX** is a framework-level FastAPI backend built around one idea: **a single server instance serves many completely isolated environments simultaneously** — each with its own database, Redis pool, JWT auth system, and plugin namespace.

This is not just a REST API. It is a **platform** where:

- 🏢 New environments (`dev`, `prod`, `staging`, `client-X`) are provisioned via a **single API call** — zero downtime, zero restarts
- 🧩 Business logic is deployed as **hot-reload Python plugins** — upload code, it runs immediately
- 🛡️ Every plugin is **statically analyzed** with a custom AST security inspector before execution
- 📈 The stack is **horizontally scalable** out of the box via Nginx load balancer

---

## 🏛️ System Architecture

```mermaid
graph TD
    Client["🌐 Client<br/>(Browser / Postman / SDK)"]
    Client -->|"HTTP REST"| LB

    subgraph Infra["☁️ Infrastructure Layer (docker-compose.scale.yml)"]
        LB["🔁 Nginx Load Balancer<br/>Least Connections"]
        LB --> App1["⚡ CoreX Instance 1"]
        LB --> App2["⚡ CoreX Instance 2"]
        LB --> App3["⚡ CoreX Instance 3"]
    end

    subgraph Core["🧠 Core Engine (per instance)"]
        App1 & App2 & App3 --> Router["📡 Universal Router<br/>/api/c/{config_name}/api/v1/"]
        Router --> ConfigMgr["📋 ConfigManager<br/>YAML Loader + Cache"]
        Router --> AuthSvc["🔑 AuthService<br/>JWT HS256 + bcrypt"]
        Router --> PluginMgr["🧩 PluginManager"]
        PluginMgr -->|"Static AST Check"| Sandbox["🛡️ Security Sandbox<br/>(AST Inspector)"]
        Sandbox -->|"✅ safe"| Exec["exec() in isolated module"]
        Sandbox -->|"❌ blocked"| Reject["SecurityValidationError"]
    end

    subgraph Data["💾 Shared Data Layer"]
        ConfigMgr --> DevDB[("🗄️ Dev DB")]
        ConfigMgr --> ProdDB[("🗄️ Prod DB")]
        ConfigMgr --> DevRedis[("🔴 Dev Redis")]
        ConfigMgr --> ProdRedis[("🔴 Prod Redis")]
    end

    subgraph Obs["📊 Observability"]
        App1 & App2 & App3 -->|"/metrics"| Prometheus["📊 Prometheus"]
        Prometheus --> Grafana["📈 Grafana Dashboard"]
    end
```

---

## ✨ Key Features

<table>
<tr>
<td width="50%">

### 🏢 True Multi-Tenancy
- One server, many **fully isolated** environments
- Each config gets its own DB connection pool, Redis pool, and plugin namespace
- New tenant provisioned via `POST /api/configs` — zero downtime

### 🧩 Dynamic Plugin Engine
- Upload Python code via API → runs **immediately**, no restart
- Hot-reload on code change
- Per-tenant plugin isolation — tenant A cannot access tenant B's plugins

</td>
<td width="50%">

### 🛡️ AST Security Sandbox
- Static code analysis **before execution** using Python's native `ast` module
- Blocks dangerous imports: `os`, `sys`, `subprocess`, `socket`, `ctypes`, `threading`, `pickle`
- Blocks dangerous builtins: `eval`, `exec`, `open`, `__import__`, `compile`
- Zero runtime overhead — analysis runs only on load

### ⚡ Full Async Stack
- FastAPI + SQLAlchemy 2.0 asyncio + `aiomysql`/`asyncpg`
- Isolated async Redis connection pools per tenant
- Non-blocking I/O end-to-end

</td>
</tr>
<tr>
<td>

### 🔐 JWT Authentication
- Per-tenant user databases with RBAC roles
- `bcrypt` password hashing (direct, cost-configurable)
- Perpetual tokens for service-to-service communication
- Session management with configurable auto-expiry

</td>
<td>

### 📦 Production Scale
- Nginx (least-conn) → 3× CoreX → shared MySQL + Redis
- Distributed rate limiting via a shared Redis counter
- Live Prometheus metrics (`/metrics`) + auto-provisioned Grafana
- k6 load test with p95 / error-rate budgets
- Redis Sentinel for high availability

</td>
</tr>
</table>

---

## ⚡ Quick Start

### 🐳 Option 1: Docker (Recommended — 2 commands)

```bash
git clone https://github.com/fealx15/CoreX.git && cd CoreX
docker compose up -d
```

| Service | URL |
|---|---|
| 🚀 API | http://localhost:8000 |
| 📚 Swagger UI | http://localhost:8000/docs |
| 📖 ReDoc | http://localhost:8000/redoc |
| ❤️ Health | http://localhost:8000/health |

### 🐍 Option 2: Local Development (Poetry)

```bash
git clone https://github.com/fealx15/CoreX.git && cd CoreX
pip install poetry && poetry install
python start_backend.py        # CLI
# or
python backend_gui.py          # Tkinter GUI with live logs
```

### 📈 Option 3: Production Scale Mode

```bash
# Nginx LB + 3 CoreX instances + MySQL + Redis + Prometheus + Grafana
docker compose -f docker-compose.scale.yml up -d --build
```

| Service | URL | Credentials |
|---|---|---|
| 🔁 API (load-balanced) | http://localhost:80 | — |
| 📊 Grafana | http://localhost:3000 | admin / admin |
| 🔍 Prometheus | http://localhost:9090 | — |
| 🗄️ MySQL | localhost:3306 | gfp_user / gfp_password |

---

## 🧩 Plugin System — Live Demo

```bash
# 1. Upload a plugin (zero restart required)
curl -X POST "http://localhost:8000/api/c/dev/api/v1/plugins" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "calculator",
    "code": "def add(a, b):\n    return {\"result\": a + b}"
  }'

# 2. Execute it immediately
curl -X POST "http://localhost:8000/api/c/dev/api/v1/plugins/calculator/execute" \
  -H "Content-Type: application/json" \
  -d '{"function_name": "add", "kwargs": {"a": 42, "b": 8}}'
# → {"result": 50}

# 3. Try to upload malicious code — BLOCKED by AST sandbox
curl -X POST "http://localhost:8000/api/c/dev/api/v1/plugins" \
  -H "Content-Type: application/json" \
  -d '{"name": "evil", "code": "import os\nos.system(\"rm -rf /\")"}'
# → 422: "Security violation: Importing restricted module 'os' is not allowed."
```

---

## 🔐 Auth API

```bash
# Register a new user (per-tenant)
curl -X POST "http://localhost:8000/api/c/dev/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "email": "john@acme.com", "password": "Secret123!", "confirm_password": "Secret123!"}'

# Login → receive JWT
curl -X POST "http://localhost:8000/api/c/dev/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "Secret123!"}'
# → {"access_token": "eyJ...", "token_type": "bearer"}
```

---

## 🔄 CI/CD Pipeline

The project ships with a **GitHub Actions** workflow that runs on every `push` and `pull_request` to `main`:

```
┌─────────────────────────────────────────────────────────┐
│                  CI/CD Pipeline                         │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │ 1. Checkout  │───▶│ 2. Python    │───▶│ 3. Poetry │  │
│  │    & Setup   │    │    3.12      │    │   Install │  │
│  └──────────────┘    └──────────────┘    └───────────┘  │
│                                                ▼         │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │ 6. Docker    │◀───│ 5. pytest    │◀───│ 4. Ruff   │  │
│  │    Build     │    │    + cov     │    │   Lint    │  │
│  └──────────────┘    └──────────────┘    └───────────┘  │
└─────────────────────────────────────────────────────────┘
```

**`.github/workflows/ci.yml`** — two parallel jobs:

| Job | Steps | Triggers |
|---|---|---|
| `lint-and-test` | Setup Python 3.12 → Install Poetry (cached) → Ruff lint → pytest + coverage XML | push, PR |
| `docker-build` | Docker Buildx → Build image (no push) | push, PR |

```yaml
# Simplified excerpt
jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: poetry install --no-interaction
      - run: poetry run ruff check .
      - run: poetry run pytest tests/ --cov=src/gfpcorex --cov-report=xml

  docker-build:
    runs-on: ubuntu-latest
    steps:
      - uses: docker/build-push-action@v5
        with: { push: false, tags: gfp-corex:ci-test }
```

---

## 🐳 Docker Architecture

### Dev Environment (`docker-compose.yml`)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  CoreX App  │────▶│  MySQL 8.0  │     │  Redis 7    │
│  :8000      │     │  :3307      │     │  :6379      │
└─────────────┘     └─────────────┘     └─────────────┘
```

```bash
docker compose up -d          # start
docker compose logs -f app    # tail logs
docker compose down           # stop
```

### Production Scale (`docker-compose.scale.yml`)

```
              ┌──────────────────────────────┐
              │   Nginx Load Balancer :80    │
              │   (least_conn, health check)│
              └────────┬─────┬──────┬───────┘
                       │     │      │
             ┌─────────▼┐ ┌──▼────┐ ┌▼─────────┐
             │ CoreX #1 │ │CoreX  │ │ CoreX #3 │
             │   :8001  │ │  #2   │ │   :8003  │
             └─────────┬┘ └──┬────┘ └┬─────────┘
                       └─────┼────────┘
                    ┌────────▼─────────┐
                    │  Shared MySQL    │  ←── persistent volume
                    │  Shared Redis    │  ←── maxmemory 512mb LRU
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   Prometheus     │  ←── scrapes /metrics
                    │   Grafana :3000  │  ←── dashboards
                    └──────────────────┘
```

**Dockerfile highlights:**

```dockerfile
FROM python:3.12-slim          # ✅ matches pyproject.toml

# Non-root user (security best practice)
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Health check for Docker orchestrators
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

---

## 🧪 Testing

```bash
# Run all tests with coverage
python -m pytest tests/ -v

# Output:
# tests/test_auth.py ....       ← JWT creation, bcrypt, invalid token
# tests/test_config.py ....     ← YAML loading, Pydantic validation
# tests/test_sandbox.py ......  ← AST security: safe code, os/eval/open blocking
# ====== 14 passed in 3.2s ======
```

### Coverage Report

| Module | Coverage | What's tested |
|---|---|---|
| `plugins/sandbox.py` | **96%** | Safe code, OS import, eval, open, syntax errors |
| `models/user_role.py` | **94%** | Model structure |
| `models/user.py` | **74%** | Model fields |
| `schemas/auth.py` | **76%** | Pydantic v2 validators |
| `core/config.py` | **69%** | YAML loading, validation, CRUD |
| `services/auth.py` | **39%** | JWT, bcrypt |

---

## 📁 Project Structure

```
CoreX/
├── 📂 src/gfpcorex/
│   ├── 📂 api/
│   │   ├── auth.py               # Register, login, profile, admin
│   │   ├── config.py             # Dynamic config CRUD
│   │   ├── middleware.py         # Rate limit (Redis/in-mem) + body-size guard
│   │   ├── plugins.py            # Plugin CRUD + reload
│   │   └── plugin_integration.py # Plugin function execution
│   ├── 📂 core/
│   │   ├── config.py             # YAML loader + Pydantic v2 models + cache
│   │   ├── database.py           # Async SQLAlchemy engine per tenant
│   │   ├── metrics.py            # 📊 Prometheus exposition (stdlib-only)
│   │   └── redis_manager.py      # Async Redis pool per tenant
│   ├── 📂 plugins/
│   │   ├── manager.py            # Load / hot-reload / exec lifecycle
│   │   └── sandbox.py            # 🛡️ AST security inspector
│   ├── 📂 models/                # SQLAlchemy ORM (User, Plugin, AuthSession, UserRole)
│   ├── 📂 schemas/               # Pydantic v2 schemas (migrated from v1)
│   ├── 📂 services/
│   │   └── auth.py               # bcrypt + JWT business logic
│   └── main.py                   # App factory, startup lifecycle
│
├── 📂 tests/
│   ├── conftest.py               # Shared fixtures (Config, user data, plugin snippets)
│   ├── test_sandbox.py           # AST security test cases
│   ├── test_config.py            # ConfigManager test cases
│   ├── test_auth.py              # JWT + password test cases
│   ├── test_metrics.py           # Prometheus exposition rendering
│   └── test_rate_limit.py        # In-memory rate-limiter logic
│
├── 📂 configs/
│   ├── dev.yaml                  # Dev environment
│   └── prod.yaml                 # Production environment
│
├── 📂 .github/workflows/
│   └── ci.yml                    # GitHub Actions: lint → test → docker build
│
├── 📂 bench/
│   ├── load-test.js              # k6 load test (p95 / error-rate thresholds)
│   └── README.md                 # How to run + interpret benchmarks
├── 📂 grafana/                   # Auto-provisioned datasource + RED dashboard
│
├── 🐳 Dockerfile                 # Python 3.12-slim, non-root, proxy-headers, health check
├── 🐳 docker-compose.yml         # Dev: App + MySQL + Redis
├── 🐳 docker-compose.scale.yml   # Prod: Nginx + 3× App + MySQL + Redis + Prometheus + Grafana
├── 🔧 nginx.scale.conf           # Load balancer (least-conn, gzip, failover)
├── 🔧 prometheus.yml             # Scrape config for app1/app2/app3 /metrics
├── 🔧 redis-sentinel.conf        # Redis Sentinel HA monitor
├── 🔧 Makefile                   # Developer shortcuts (make test, make bench, ...)
├── 🔧 .pre-commit-config.yaml    # Pre-commit: ruff + yaml/toml checks
├── backend_gui.py                # Tkinter GUI launcher with live log streaming
├── pyproject.toml                # Poetry + Ruff + pytest + mypy config
└── CHANGELOG.md                  # Version history
```

---

## ⚙️ Configuration Reference

```yaml
# configs/dev.yaml — full example
app:
  title: "GFP CoreX Dev"
  version: "1.0.0"
  debug: true
  cors_origins: ["*"]

db:
  url: "mysql+aiomysql://gfp_user:gfp_password@localhost:3307/gfp_dev_db"
  pool_size: 10
  max_overflow: 20
  echo: true                         # SQL query logging in dev

redis:
  url: "redis://localhost:6379/0"
  pool_size: 10
  decode_responses: true

auth:
  secret_key: "your-super-secret-key-minimum-32-characters-long"
  algorithm: "HS256"
  access_token_expire_minutes: 30
  refresh_token_expire_days: 7

logging:
  level: "INFO"                      # DEBUG / INFO / WARNING / ERROR
  format: "json"                     # json | text
  handlers: ["console"]

security:
  bcrypt_rounds: 12
  rate_limit_per_minute: 100
  max_request_size: "10MB"
```

---

## 🗄️ Database Schema

```sql
-- Auto-created on first startup via SQLAlchemy metadata

CREATE TABLE user_roles (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(50) UNIQUE NOT NULL,  -- 'admin', 'user'
    description TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    username        VARCHAR(50)  UNIQUE NOT NULL,
    email           VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,      -- bcrypt
    first_name      VARCHAR(50),
    last_name       VARCHAR(50),
    phone           VARCHAR(20),
    bio             TEXT,
    avatar_url      VARCHAR(255),
    is_active       BOOLEAN DEFAULT TRUE,
    is_superuser    BOOLEAN DEFAULT FALSE,
    role_id         INT REFERENCES user_roles(id),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE plugins (
    id        INT PRIMARY KEY AUTO_INCREMENT,
    name      VARCHAR(100) UNIQUE NOT NULL,
    code      TEXT NOT NULL,
    hashsum   VARCHAR(64) NOT NULL,    -- SHA-256 for hot-reload detection
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE auth_sessions (
    id         INT PRIMARY KEY AUTO_INCREMENT,
    user_id    INT NOT NULL REFERENCES users(id),
    token      VARCHAR(512) UNIQUE NOT NULL,
    expires_at TIMESTAMP,             -- NULL = perpetual token
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 📊 Observability

Every instance exposes Prometheus metrics at **`GET /metrics`** in the standard
text exposition format — implemented with the **standard library alone** (see
`src/gfpcorex/core/metrics.py`), so it adds zero dependencies.

`PrometheusMiddleware` records the **RED** signals on every request:

| Metric | Type | Labels |
|---|---|---|
| `gfp_http_requests_total` | counter | `method`, `path`, `status` |
| `gfp_http_request_duration_seconds` | histogram | `method`, `path` (11 buckets) |
| `gfp_http_requests_in_progress` | gauge | — |

The `path` label uses the **matched route template** (e.g.
`/api/c/{config_name}/api/v1/auth/login`) rather than the concrete URL, so
per-tenant traffic collapses onto one low-cardinality series instead of exploding
one series per tenant.

In scale mode, **Prometheus** scrapes all three instances and **Grafana**
auto-loads the *GFP CoreX — Overview* dashboard (datasource + panels provisioned
from `grafana/`, no manual clicking):

- Request rate **per instance** — watch Nginx spread load across `app1`/`app2`/`app3`
- Latency **p50 / p95 / p99** (computed from the histogram)
- **Error rate** (5xx) and requests by status class
- **In-flight** requests per instance

```bash
make docker-scale       # brings up the full stack
make metrics            # peek at raw metrics through the load balancer
# → Grafana at http://localhost:3000  (admin / admin)
```

> Request-size and rate limits are configured via environment variables
> (`GFP_MAX_REQUEST_BYTES`, `GFP_RATE_LIMIT_PER_MIN`, `GFP_RATE_LIMIT_REDIS_URL`),
> since they apply globally across every tenant. In scale mode the app instances
> share one Redis-backed rate-limit counter, so the limit holds across all three.

### Load testing

A [k6](https://k6.io) load test drives the scale stack and enforces a
latency/error budget as **pass/fail thresholds** — usable as a CI performance gate:

```bash
make bench              # ramps to 200 VUs; fails if p95 > 500ms or error rate > 1%
```

See [`bench/README.md`](bench/README.md) for the traffic profile and thresholds.

---

## 🛡️ Security Model

| Layer | Mechanism |
|---|---|
| **Authentication** | JWT HS256 via `python-jose`, bcrypt rounds=12 (direct `bcrypt`) |
| **Authorization** | RBAC — `role_id` per user, enforced per-tenant |
| **Rate limiting** | Per-client-IP, distributed via shared Redis (atomic Lua), in-memory fallback |
| **Request size** | Body-size cap enforced before the handler (`413`), configured via env |
| **Plugin execution** | Static AST analysis runs before every `exec()` call |
| **Forbidden imports** | `os`, `sys`, `subprocess`, `socket`, `ctypes`, `threading`, `pickle`, `importlib` |
| **Forbidden builtins** | `eval`, `exec`, `open`, `__import__`, `compile`, `breakpoint` |
| **Tenant isolation** | Separate async DB engine + Redis pool per config name |
| **Docker runtime** | Non-root `appuser`, configs mounted read-only (`:ro`) |
| **Dunder access** | `__class__`, `__globals__`, etc. blocked in plugin AST |

---

## 📊 Tech Stack

| Layer | Technology | Version |
|---|---|---|
| **API Framework** | FastAPI + Uvicorn | 0.116+ |
| **Async ORM** | SQLAlchemy (asyncio mode) | 2.0+ |
| **MySQL driver** | aiomysql | 0.2+ |
| **PostgreSQL driver** | asyncpg | 0.29+ |
| **Cache** | Redis + hiredis | 7+ |
| **Auth** | python-jose (JWT) + bcrypt | latest |
| **Config & Validation** | Pydantic v2 + PyYAML | 2.11+ |
| **Packaging** | Poetry | 1.8+ |
| **Testing** | pytest + pytest-asyncio + pytest-cov | 8+ |
| **Linting** | Ruff | 0.5+ |
| **Type Checking** | Mypy | 1.8+ |
| **Pre-commit** | pre-commit | 3.7+ |
| **CI/CD** | GitHub Actions | — |
| **Containers** | Docker + docker-compose | 3.8+ |
| **Load Balancer** | Nginx | alpine |
| **Monitoring** | Prometheus + Grafana | latest |
| **Load testing** | k6 | latest |
| **GUI** | Tkinter | stdlib |

---

## 🛠️ Developer Commands

```bash
make help          # Show all available commands

make install       # Install all dependencies
make dev           # Start dev server with hot reload
make gui           # Open Tkinter GUI launcher

make test          # Run pytest suite
make test-cov      # Run tests + open HTML coverage report
make lint          # Ruff linter check
make format        # Auto-fix code style with ruff
make type-check    # Run mypy

make docker-up     # Start dev environment (docker compose up -d)
make docker-scale  # Start production scale environment
make docker-down   # Stop all containers
make docker-logs   # Tail container logs

make bench         # Run k6 load test against the scale stack
make metrics       # Sample live Prometheus metrics from the LB

make clean         # Remove .pyc, __pycache__, .coverage
```

---

## 🤝 Contributing

```bash
# Fork & clone
git clone https://github.com/YOUR_USERNAME/CoreX.git && cd CoreX

# Install all deps including dev
make install

# Install pre-commit hooks (runs Ruff on every commit)
make pre-commit

# Make your changes, write tests
make test

# Submit PR — CI pipeline validates lint + tests + docker build automatically
```

Please read [CHANGELOG.md](CHANGELOG.md) for version history.

---

## 📄 License

[MIT License](LICENSE) — Copyright © 2026 [fealx15](https://github.com/fealx15)

---

<div align="center">

**Built with ⚡ FastAPI · asyncio · Python 3.12**

*If this project helped you — consider giving it a ⭐*

</div>
