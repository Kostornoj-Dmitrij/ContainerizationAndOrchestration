import asyncio
import logging
import os
import random
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from pythonjsonlogger import jsonlogger

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

# ---------- Метрики (RED) ----------
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
ERROR_COUNT = Counter(
    "http_errors_total",
    "Total HTTP 5xx errors",
    ["method", "endpoint"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0],
)

# ---------- Логи (JSON с trace_id) ----------
class TraceIdFilter(logging.Filter):
    def filter(self, record):
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            record.trace_id = format(span.get_span_context().trace_id, "032x")
        else:
            record.trace_id = "0" * 32
        return True


def setup_logging():
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(trace_id)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )
    handler.setFormatter(formatter)
    handler.addFilter(TraceIdFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


# ---------- Трейсы (OpenTelemetry → Jaeger) ----------
def setup_tracing(service_name: str):
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


setup_logging()
setup_tracing("api")

logger = logging.getLogger("api")
tracer = trace.get_tracer("api")

app = FastAPI(title="api")
FastAPIInstrumentor.instrument_app(app, excluded_urls="metrics")


# ---------- Middleware: метрики на каждый запрос ----------
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=str(response.status_code),
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method, endpoint=request.url.path
    ).observe(duration)
    if response.status_code >= 500:
        ERROR_COUNT.labels(
            method=request.method, endpoint=request.url.path
        ).inc()

    return response


# ---------- Эндпоинты ----------
@app.get("/health")
async def health():
    logger.info("health check ok")
    return PlainTextResponse("ok")


@app.get("/fail")
async def fail():
    await asyncio.sleep(1.5)
    span = trace.get_current_span()
    span.set_status(Status(StatusCode.ERROR, "intentional failure"))
    span.set_attribute("error.type", "IntentionalError")
    logger.error("intentional failure triggered")
    return Response(status_code=500, content="internal server error")


@app.get("/slow")
async def slow():
    with tracer.start_as_current_span("slow-op") as span:
        delay = random.uniform(1.0, 3.0)
        span.set_attribute("slow.delay_seconds", delay)
        logger.info(f"slow-op sleeping {delay:.2f}s")
        await asyncio.sleep(delay)
    return {"status": "ok", "slept_seconds": round(delay, 2)}


@app.get("/load")
async def load(count: int = 20):
    """Сервис сам дёргает свои эндпоинты, чтобы подскочил RPS."""
    port = int(os.getenv("PORT", "8000"))
    base = f"http://127.0.0.1:{port}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = []
        for i in range(count):
            if i % 5 == 0:
                tasks.append(client.get(f"{base}/fail"))
            elif i % 3 == 0:
                tasks.append(client.get(f"{base}/slow"))
            else:
                tasks.append(client.get(f"{base}/health"))
        await asyncio.gather(*tasks, return_exceptions=True)
    logger.info(f"generated load: {count} requests")
    return {"status": "ok", "requests_sent": count}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)