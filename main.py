import os
from pathlib import Path
import threading
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from src.core.logging_config import setup_logging, get_log_file_path, clear_log_file
from src.core.s3_log_uploader import upload_log_file_to_s3
from src.dashboard.api import router as dashboard_router
from src.edge.simulator import run_simulator
from src.fog.mqtt_subscriber import MQTTSubscriber
from src.fog.websocket import websocket_endpoint
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Unified Backend")  

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://main.d24uw1llup1b1k.amplifyapp.com",
    ],
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


app.include_router(dashboard_router, prefix="/api")
app.websocket("/ws")(websocket_endpoint)


def start_mqtt():
    logger.info("Starting MQTT subscriber in background thread")
    
    try:
        subscriber = MQTTSubscriber()
        
        thread = threading.Thread(
            target=subscriber.connect,
            daemon=True
        )
        thread.start()
        
    except Exception as e:
        logger.error("Failed to start MQTT subscriber: %s", str(e))
        raise


def start_simulator():
    logger.info("Starting simulator in background thread")
    thread = threading.Thread(
        target=run_simulator,
        kwargs={"use_mqtt": True},
        daemon=True
    )
    thread.start()
    logger.info("Simulator started with dynamic scenario switching")


@app.on_event("startup")
async def startup():
    start_mqtt()
    start_simulator()


@app.get("/health")
def health():
    return {"status": "ok"}


asgi_handler = Mangum(app, lifespan="off")


def handler(event, context):
    log_bucket = os.getenv("LOG_BUCKET_NAME")
    log_file_path = get_log_file_path()

    clear_log_file()
    logger.info("Lambda invocation started")

    try:
        response = asgi_handler(event, context)
        logger.info("Lambda invocation completed successfully")
        return response

    except Exception:
        logger.exception("Lambda invocation failed")
        raise

    finally:
        try:
            if log_bucket:
                s3_key = upload_log_file_to_s3(
                    bucket_name=log_bucket,
                    local_file_path=log_file_path,
                    prefix="backend-logs"
                )
                logger.info("Uploaded log file to S3 | key=%s", s3_key)
            else:
                logger.warning("LOG_BUCKET_NAME is not set, skipping S3 upload")
        except Exception:
            logger.exception("Failed to upload log file to S3")