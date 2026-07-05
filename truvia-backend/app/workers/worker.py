import sys
import os
from rq import Connection, Worker
from redis import Redis

# Add parent directory to path so it can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.config import settings

def run_worker():
    print(f"Starting Truvia Background Worker connected to Redis: {settings.REDIS_URL}...")
    redis_conn = Redis.from_url(settings.REDIS_URL)
    with Connection(redis_conn):
        worker = Worker(["truvia-tasks"])
        worker.work(with_scheduler=True)

if __name__ == "__main__":
    run_worker()
