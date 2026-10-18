import os
import time
import logging
import json
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger("worker")

DB_HOST = os.getenv("DB_HOST", "postgres-rw")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "shop")
DB_USER = os.getenv("DB_USER", "shop")
DB_PASSWORD = os.getenv("DB_PASSWORD", "shop")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "3"))


def get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    )


def process_batch():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE orders
                SET status = 'processed'
                WHERE id IN (
                    SELECT id FROM orders
                    WHERE status = 'new'
                    ORDER BY id
                    LIMIT 10
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id
            """)
            rows = cur.fetchall()
        conn.commit()
    return [r["id"] for r in rows]


def main():
    log.info(json.dumps({"event": "worker_started"}))
    while True:
        try:
            processed = process_batch()
            if processed:
                log.info(json.dumps({"event": "batch_processed", "ids": processed}))
            time.sleep(POLL_INTERVAL)
        except Exception as e:
            log.error(json.dumps({"event": "worker_error", "error": str(e)}))
            time.sleep(5)


if __name__ == "__main__":
    main()