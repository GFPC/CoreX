# Load Testing & Benchmarks

Load tests for the GFP CoreX scale stack, written for [k6](https://k6.io/).

The test drives the full production topology — Nginx load balancer in front of
three CoreX instances, backed by shared MySQL and Redis — and enforces a latency
and error budget as pass/fail thresholds.

## Prerequisites

1. **Install k6**

   ```bash
   # macOS
   brew install k6
   # Debian/Ubuntu
   sudo apt-get install k6
   # Windows
   choco install k6
   ```

2. **Bring the scale stack up**

   ```bash
   make docker-scale
   ```

   This starts Nginx (`:80`), three app instances, MySQL, Redis, Prometheus
   (`:9090`) and Grafana (`:3000`, `admin`/`admin`).

## Running

```bash
# Against the local scale stack (default)
make bench

# Or directly, overriding target / tenant
BASE_URL=http://localhost:80 CONFIG=prod k6 run bench/load-test.js
```

While it runs, open the **GFP CoreX — Overview** dashboard at
<http://localhost:3000> — the "Request rate by instance" panel shows Nginx
spreading load across `app1`/`app2`/`app3`, and the latency panel tracks p50/p95/p99
live.

## Load profile

A ramping-VU scenario: warm up to 50 VUs, ramp to 200, hold, then ramp down —
about 3 minutes total. Traffic is a weighted mix:

| Weight | Endpoint                          | Exercises                          |
| -----: | --------------------------------- | ---------------------------------- |
|   60%  | `GET /`                           | routing + middleware only (cheap)  |
|   20%  | `GET /health`                     | MySQL `SELECT 1` + Redis `PING`    |
|   20%  | `GET /api/c/{config}/api/v1/health` | per-tenant config resolution     |

## Thresholds (pass/fail)

| Threshold                        | Budget       |
| -------------------------------- | ------------ |
| `http_req_failed`                | < 1% errors  |
| `http_req_duration` p95          | < 500 ms     |
| `http_req_duration` p95 (`/`)    | < 200 ms     |

k6 exits non-zero if any threshold is breached, so `make bench` doubles as a CI
performance gate.

## Exporting results

```bash
k6 run --summary-export=bench/summary.json bench/load-test.js
```
