import http from 'k6/http';
import { sleep, check } from 'k6';

export let options = {
  stages: [
    { duration: '30s', target: 2 },
    { duration: '1m', target: 10 },
    { duration: '30s', target: 0 }
  ],
  thresholds: {
    'http_req_failed': ['rate<0.01'],
  }
};

const BASE = 'http://127.0.0.1:8000/api';

export default function () {
  // GET posts
  let res = http.get(`${BASE}/foro/posts/`);
  check(res, { 'get posts ok': (r) => r.status === 200 });

  // POST a lightweight auth (simulated payload) — adapt to your endpoint
  let loginRes = http.post(`${BASE}/auth/login/`, JSON.stringify({ username: 'test', password: 'test' }), { headers: { 'Content-Type': 'application/json' } });
  check(loginRes, { 'login ok or fail gracefully': (r) => r.status === 200 || r.status === 400 });

  sleep(1);
}
