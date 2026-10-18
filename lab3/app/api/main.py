import os
import time
import logging
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger("api")

DB_HOST = os.getenv("DB_HOST", "postgres-rw")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "shop")
DB_USER = os.getenv("DB_USER", "shop")
DB_PASSWORD = os.getenv("DB_PASSWORD", "shop")
HEALTH_FAIL = os.getenv("HEALTH_FAIL", "false").lower() == "true"


def get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    )


def init_db():
    for attempt in range(30):
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS orders (
                            id SERIAL PRIMARY KEY,
                            item TEXT NOT NULL,
                            quantity INT NOT NULL,
                            status TEXT NOT NULL DEFAULT 'new',
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                    """)
                conn.commit()
            log.info(json.dumps({"event": "db_initialized"}))
            return
        except Exception as e:
            log.warning(json.dumps({"event": "db_wait", "attempt": attempt, "error": str(e)}))
            time.sleep(2)
    raise RuntimeError("could not initialize db")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


class OrderIn(BaseModel):
    item: str
    quantity: int


@app.get("/health")
def health():
    if HEALTH_FAIL:
        log.error(json.dumps({"event": "health_fail"}))
        raise HTTPException(status_code=500, detail="intentional failure")
    return "ok"


@app.post("/order")
def create_order(order: OrderIn):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO orders (item, quantity) VALUES (%s, %s) RETURNING *",
                (order.item, order.quantity),
            )
            row = cur.fetchone()
        conn.commit()
    log.info(json.dumps({"event": "order_created", "order_id": row["id"]}))
    return row


@app.get("/orders")
def list_orders():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 100")
            rows = cur.fetchall()
    return rows