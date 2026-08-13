# Changelog

All notable changes to **GFP CoreX** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] — 2026-08-13

### Added
- **Plugin Security Sandbox** (`src/gfpcorex/plugins/sandbox.py`)
  - Static AST inspection of all plugin code before execution via `PluginSecurityChecker`
  - Blocks dangerous module imports: `os`, `sys`, `subprocess`, `socket`, `ctypes`, `threading`, `pickle`, `importlib`
  - Blocks dangerous builtins: `eval`, `exec`, `open`, `__import__`, `compile`, `breakpoint`
  - `PluginSandbox.get_safe_globals()` generates a restricted execution scope
  - `SecurityValidationError` raised on policy violations

- **GitHub Actions CI/CD** (`.github/workflows/ci.yml`)
  - Pipeline: Ruff lint → pytest with coverage → Docker image build validation
  - Poetry dependency caching for fast runs
  - Triggered on push/PR to `main`/`master`

- **Full pytest test suite** (`tests/`)
  - `test_sandbox.py` — 6 test cases for AST security (safe code, OS import, `eval`, `open`, syntax errors)
  - `test_config.py` — 4 test cases for ConfigManager CRUD and Pydantic validation
  - `test_auth.py` — 4 test cases for JWT creation, bcrypt hashing, invalid token rejection

- **Ruff linter config** and `[tool.pytest.ini_options]` sections in `pyproject.toml`

### Changed
- **Pydantic V2 migration** — All `@validator` deprecated in V2 replaced with `@field_validator` + `@classmethod` and `@model_validator` in:
  - `src/gfpcorex/schemas/auth.py`
  - `src/gfpcorex/core/config.py`
  - Replaced `class Config` with `model_config = ConfigDict(...)` in `UserResponse`
- `PluginManager.load_plugin()` now runs `PluginSandbox.validate_code()` before `exec()`
- **README.md** fully rewritten with architecture diagram, feature table, quick start, and tech stack
- **Dockerfile** base image updated from `python:3.11-slim` to `python:3.12-slim`

### Fixed
- `backend_gui.py`: hardcoded `D:/PROJECTS/...` Python path replaced with `sys.executable`
- `start_backend.py`: hardcoded project `cwd` replaced with `Path(__file__).parent.resolve()`
- Python version mismatch between `pyproject.toml` (`^3.12`) and `Dockerfile` (`3.11`) resolved

---

## [0.1.0] — 2026-07-01 (Initial Release)

### Added
- Multi-tenant FastAPI backend with dynamic routing `/api/c/{config_name}/api/v1/`
- Per-tenant isolated database connections (async SQLAlchemy 2.0 + aiomysql)
- Per-tenant isolated Redis connection pools
- Dynamic plugin system: upload Python code via API, execute without restart
- JWT authentication (HS256) with bcrypt password hashing, RBAC roles
- YAML-based configuration system with in-memory caching
- Auto table creation on startup
- `docker-compose.yml` — dev environment (App + MySQL + Redis)
- `docker-compose.scale.yml` — production scale (Nginx + 3× App + MySQL + Redis + Prometheus + Grafana)
- Tkinter GUI launcher (`backend_gui.py`) with live log streaming
