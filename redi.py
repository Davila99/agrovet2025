import redis
try:
    r = redis.Redis(host='127.0.0.1', port=6379, db=0, socket_connect_timeout=3)
    print("redis ping ->", r.ping())
except Exception as e:
    print("redis error:", e)
