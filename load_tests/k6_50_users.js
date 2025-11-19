import http from 'k6/http';
import { sleep, check } from 'k6';

export let options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '2m', target: 50 },
    { duration: '30s', target: 0 }
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500'],
    'http_req_failed': ['rate<0.02']
  }
};

const BASE = 'http://127.0.0.1:8000/api';

export default function () {
  // GET posts and a community endpoint
  let res = http.get(`${BASE}/foro/posts/?page=1`);
  check(res, { 'get posts ok': (r) => r.status === 200 });

  let res2 = http.get(`${BASE}/foro/communities/`);
  check(res2, { 'get communities ok': (r) => r.status === 200 });

  // Simulate a post creation attempt (likely 401 if unauthenticated)
  let payload = JSON.stringify({ title: 'Load test post', content: 'testing' });
  let postRes = http.post(`${BASE}/foro/posts/`, payload, { headers: { 'Content-Type': 'application/json' } });
  check(postRes, { 'post attempt ok or auth fail': (r) => r.status === 201 || r.status === 401 || r.status === 403 });

  sleep(1);
}
