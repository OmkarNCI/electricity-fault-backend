import threading
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.core.logging_config import setup_logging
from src.dashboard.api import router as dashboard_router
from src.edge.simulator import run_simulator
from src.fog.mqtt_subscriber import MQTTSubscriber
from src.fog.websocket import websocket_endpoint

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Unified Backend")

# CORS for React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    client_ip = request.client.host if request.client else "unknown"

    logger.info(
        "Request started | method=%s path=%s client_ip=%s",
        request.method,
        request.url.path,
        client_ip,
    )

    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "Request completed | method=%s path=%s status_code=%s duration_ms=%.2f client_ip=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            client_ip,
        )
        return response

    except Exception:
        logger.exception(
            "Unhandled request failure | method=%s path=%s client_ip=%s",
            request.method,
            request.url.path,
            client_ip,
        )
        raise

@app.on_event("startup")
async def on_startup():
    logger.info("FastAPI application startup complete")

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("FastAPI application shutdown complete")

# REST APIs
app.include_router(dashboard_router, prefix="/api")

# WebSocket
app.websocket("/ws")(websocket_endpoint)

# Start MQTT in background
def start_mqtt():
    logger.info("Starting MQTT subscriber in background thread")
    subscriber = MQTTSubscriber()
    thread = threading.Thread(
        target=subscriber.connect,
        daemon=True
    )
    thread.start()

def start_simulator():
    logger.info("Starting simulator in background thread")
    thread = threading.Thread(
        target=run_simulator,
        kwargs={
            "use_mqtt": True  # No scenario parameter anymore
        },
        daemon=True
    )
    thread.start()
    logger.info("Simulator started with dynamic scenario switching")

# Startup
@app.on_event("startup")
async def startup():
    start_mqtt()
    start_simulator()

# Health
@app.get("/health")
def health():
    return {"status": "ok"}