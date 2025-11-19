# Load Tests for Agrovet Backend

This folder contains scripts and instructions to run performance/load tests locally using `k6` and `locust`.

Requirements:
- `k6` installed (https://k6.io/docs/getting-started/installation)
- `locust` installed (`pip install locust`)

k6 Scripts:
- `k6_10_users.js`: light smoke test (ramp to 10 users)
- `k6_50_users.js`: medium load (ramp to 50 users)
- `k6_100_users.js`: heavy load (ramp to 100 users)

Run examples:

```bash
# run k6 100 users script
k6 run load_tests/k6_100_users.js

# run k6 50 users
k6 run load_tests/k6_50_users.js
```

Locust:

```bash
# start locust UI
locust -f load_tests/locustfile.py

# open http://127.0.0.1:8089 and start the load
```

Metrics to collect (suggested):
- Latency: p95, p99
- Throughput (req/s)
- Error rate
- Average response time

Expected (simulated) baseline table:

| Test | Users | p95 latency (ms) | p99 latency (ms) | throughput (req/s) | error rate |
|---|---:|---:|---:|---:|---:|
| k6_10_users | 10 | 120 | 240 | 30 | 0.0% |
| k6_50_users | 50 | 300 | 700 | 120 | 0.5% |
| k6_100_users | 100 | 700 | 1200 | 220 | 2.0% |

Adjust the expected table according to your environment. These values are simulated samples to include in the sprint documentation.
