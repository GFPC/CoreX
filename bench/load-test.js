// k6 load test for the GFP CoreX scale stack.
//
// Drives the Nginx-fronted 3-instance topology (docker-compose.scale.yml) and
// asserts the service holds its latency/error budget under a ramping load.
// While this runs, the Grafana "GFP CoreX — Overview" dashboard (http://localhost:3000)
// shows the traffic spreading across app1/app2/app3 in real time.
//
//   k6 run bench/load-test.js
//   BASE_URL=http://localhost:80 CONFIG=prod k6 run bench/load-test.js
//
// See bench/README.md for prerequisites and interpretation.

import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:80';
const CONFIG = __ENV.CONFIG || 'prod';

export const options = {
  scenarios: {
    ramping_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 50 },   // warm up
        { duration: '1m', target: 200 },   // ramp to peak
        { duration: '1m', target: 200 },   // hold at peak
        { duration: '30s', target: 0 },    // ramp down
      ],
      gracefulStop: '10s',
    },
  },
  // The run fails (non-zero exit) if either budget is breached — suitable for CI.
  thresholds: {
    http_req_failed: ['rate<0.01'],                       // < 1% errors overall
    http_req_duration: ['p(95)<500'],                     // p95 < 500ms overall
    'http_req_duration{endpoint:root}': ['p(95)<200'],    // cheap endpoint stays snappy
  },
};

// Weighted traffic mix: mostly the cheap root endpoint, with a slice of the
// heavier DB/Redis-backed health checks and the per-tenant routed endpoint.
export default function () {
  const roll = Math.random() * 100;
  let res;

  if (roll < 60) {
    res = http.get(`${BASE_URL}/`, { tags: { endpoint: 'root' } });
    check(res, { 'root -> 200': (r) => r.status === 200 });
  } else if (roll < 80) {
    res = http.get(`${BASE_URL}/health`, { tags: { endpoint: 'health' } });
    // /health reports 200 with an "unhealthy" body if a backing store is down,
    // so accept any served response and let the error-rate threshold judge 5xx.
    check(res, { 'health served': (r) => r.status === 200 });
  } else {
    res = http.get(`${BASE_URL}/api/c/${CONFIG}/api/v1/health`, {
      tags: { endpoint: 'config_health' },
    });
    check(res, { 'config_health served': (r) => r.status < 500 });
  }

  // Model think-time so VUs don't behave like a tight synthetic hammer.
  sleep(Math.random() * 0.5);
}
