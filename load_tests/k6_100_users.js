import http from 'k6/http';
import { sleep, check } from 'k6';

export let options = {
  stages: [
    { duration: '1m', target: 20 },
    { duration: '3m', target: 100 },
    { duration: '1m', target: 0 }
  ],
  thresholds: {
    'http_req_duration': ['p(95)<700', 'p(99)<1200'],
    'http_req_failed': ['rate<0.03']
  }
};

const BASE = 'http://127.0.0.1:8000/api';

export default function () {
  // GET several endpoints
  http.get(`${BASE}/foro/posts/?page=1`);
  http.get(`${BASE}/foro/posts/?page=2`);

  // Lightweight POST (login simulation)
  http.post(`${BASE}/auth/login/`, JSON.stringify({ username: 'load', password: 'test' }), { headers: { 'Content-Type': 'application/json' } });

  sleep(1);
}
