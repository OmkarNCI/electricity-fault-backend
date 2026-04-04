from __future__ import annotations

import sys
import logging
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, File, HTTPException, UploadFile

from src.fog.live_state import live_fog_state
from src.common.config import CONFIG
from src.edge.simulation_state import current_scenario


CURRENT_FILE = Path(__file__).resolve()
SRC_DIR = CURRENT_FILE.parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

router = APIRouter()
logger = logging.getLogger(__name__)

AWS_REGION = CONFIG.aws["region"]
ALERTS_TABLE = CONFIG.aws["alerts_table"]
AREA_SUMMARIES_TABLE = CONFIG.aws["area_summaries_table"]
S3_BUCKET_NAME = CONFIG.aws["s3_bucket_name"]

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
alerts_table = dynamodb.Table(ALERTS_TABLE)
area_summaries_table = dynamodb.Table(AREA_SUMMARIES_TABLE)
s3_client = boto3.client("s3", region_name=AWS_REGION)

logger.info(
    "API module initialized | region=%s alerts_table=%s area_summaries_table=%s s3_bucket=%s",
    AWS_REGION,
    ALERTS_TABLE,
    AREA_SUMMARIES_TABLE,
    S3_BUCKET_NAME,
)

# -------------------------------
# Helpers
# -------------------------------

def convert_decimal(value: Any) -> Any:
    if isinstance(value, list):
        return [convert_decimal(v) for v in value]
    if isinstance(value, dict):
        return {k: convert_decimal(v) for k, v in value.items()}
    if isinstance(value, Decimal):
        return float(value)
    return value


def scan_table(table) -> list[dict[str, Any]]:
    table_name = getattr(table, "name", "unknown")
    logger.info("DynamoDB scan started | table=%s", table_name)

    try:
        response = table.scan()
        items = response.get("Items", [])

        while "LastEvaluatedKey" in response:
            logger.info("DynamoDB pagination continued | table=%s", table_name)
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        converted_items = [convert_decimal(item) for item in items]

        logger.info(
            "DynamoDB scan completed | table=%s item_count=%s",
            table_name,
            len(converted_items),
        )
        return converted_items

    except Exception:
        logger.exception("DynamoDB scan failed | table=%s", table_name)
        raise


def sort_by_timestamp_desc(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    logger.info("Sorting items by timestamp | item_count=%s", len(items))
    return sorted(items, key=lambda x: x.get("timestamp", ""), reverse=True)


def get_all_areas() -> list[str]:
    logger.info("Collecting all unique area IDs")

    try:
        summaries = scan_table(area_summaries_table)
        alerts = scan_table(alerts_table)

        area_ids = set()

        for item in summaries:
            if item.get("area_id"):
                area_ids.add(item["area_id"])

        for item in alerts:
            if item.get("area_id"):
                area_ids.add(item["area_id"])

        result = sorted(area_ids)

        logger.info("Area collection completed | area_count=%s", len(result))
        return result

    except Exception:
        logger.exception("Failed to collect all areas")
        raise


# -------------------------------
# Historic data routes
# -------------------------------

@router.get("/areas")
def get_areas() -> list[str]:
    logger.info("Route called | GET /areas")

    try:
        areas = get_all_areas()
        logger.info("Areas returned successfully | area_count=%s", len(areas))
        return areas
    except Exception:
        logger.exception("Failed to return areas")
        raise HTTPException(status_code=500, detail="Failed to fetch areas")


@router.get("/areas/{area_id}/latest-summary")
def get_latest_summary(area_id: str) -> dict[str, Any]:
    logger.info("Route called | GET /areas/%s/latest-summary", area_id)

    try:
        items = scan_table(area_summaries_table)
        filtered = [item for item in items if item.get("area_id") == area_id]
        filtered = sort_by_timestamp_desc(filtered)

        if not filtered:
            logger.warning("No latest summary found | area_id=%s", area_id)
            raise HTTPException(status_code=404, detail=f"No summary found for area {area_id}")

        logger.info("Latest summary returned | area_id=%s", area_id)
        return filtered[0]

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch latest summary | area_id=%s", area_id)
        raise HTTPException(status_code=500, detail="Failed to fetch latest summary")


@router.get("/areas/{area_id}/summaries")
def get_area_summaries(area_id: str, limit: int = 20) -> list[dict[str, Any]]:
    logger.info(
        "Route called | GET /areas/%s/summaries | limit=%s",
        area_id,
        limit,
    )

    try:
        items = scan_table(area_summaries_table)
        filtered = [item for item in items if item.get("area_id") == area_id]
        filtered = sort_by_timestamp_desc(filtered)
        result = filtered[:limit]

        logger.info(
            "Area summaries returned | area_id=%s returned_count=%s",
            area_id,
            len(result),
        )
        return result

    except Exception:
        logger.exception("Failed to fetch area summaries | area_id=%s", area_id)
        raise HTTPException(status_code=500, detail="Failed to fetch area summaries")


@router.get("/areas/{area_id}/alerts")
def get_area_alerts(area_id: str, limit: int = 20) -> list[dict[str, Any]]:
    logger.info(
        "Route called | GET /areas/%s/alerts | limit=%s",
        area_id,
        limit,
    )

    try:
        items = scan_table(alerts_table)
        filtered = [item for item in items if item.get("area_id") == area_id]
        filtered = sort_by_timestamp_desc(filtered)
        result = filtered[:limit]

        logger.info(
            "Area alerts returned | area_id=%s returned_count=%s",
            area_id,
            len(result),
        )
        return result

    except Exception:
        logger.exception("Failed to fetch area alerts | area_id=%s", area_id)
        raise HTTPException(status_code=500, detail="Failed to fetch area alerts")


@router.get("/poles/{pole_id}/alerts")
def get_pole_alerts(pole_id: str, limit: int = 20) -> list[dict[str, Any]]:
    logger.info(
        "Route called | GET /poles/%s/alerts | limit=%s",
        pole_id,
        limit,
    )

    try:
        items = scan_table(alerts_table)
        filtered = [item for item in items if item.get("pole_id") == pole_id]
        filtered = sort_by_timestamp_desc(filtered)
        result = filtered[:limit]

        logger.info(
            "Pole alerts returned | pole_id=%s returned_count=%s",
            pole_id,
            len(result),
        )
        return result

    except Exception:
        logger.exception("Failed to fetch pole alerts | pole_id=%s", pole_id)
        raise HTTPException(status_code=500, detail="Failed to fetch pole alerts")


# -------------------------------
# Live dashboard routes
# -------------------------------

@router.get("/live/areas")
def get_live_areas():
    logger.info("Route called | GET /live/areas")

    try:
        areas = live_fog_state.get_available_areas()
        logger.info("Live areas returned | area_count=%s", len(areas))
        return areas

    except Exception:
        logger.exception("Failed to fetch live areas")
        raise HTTPException(status_code=500, detail="Failed to fetch live areas")


@router.get("/live/areas/{area_id}")
def get_area_details(area_id: str):
    logger.info("Route called | GET /live/areas/%s", area_id)

    try:
        poles = []
        latest_events = {}

        for pole_id, event in live_fog_state.latest_event_by_pole.items():
            if event.area_id == area_id:
                poles.append(pole_id)
                latest_events[pole_id] = live_fog_state._event_to_dict(event)

        if not poles:
            logger.warning("No live poles found for area | area_id=%s", area_id)
            raise HTTPException(status_code=404, detail="No poles found")

        result = {
            "area_id": area_id,
            "poles": sorted(poles),
            "latest_pole_events": latest_events,
        }

        logger.info(
            "Live area details returned | area_id=%s pole_count=%s",
            area_id,
            len(result["poles"]),
        )
        return result

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch live area details | area_id=%s", area_id)
        raise HTTPException(status_code=500, detail="Failed to fetch live area details")


@router.get("/live/poles/{pole_id}/history")
def get_pole_history(pole_id: str):
    logger.info("Route called | GET /live/poles/%s/history", pole_id)

    try:
        history = live_fog_state.get_pole_history(pole_id)

        logger.info(
            "Pole history returned | pole_id=%s history_count=%s",
            pole_id,
            len(history) if history else 0,
        )
        return history

    except Exception:
        logger.exception("Failed to fetch pole history | pole_id=%s", pole_id)
        raise HTTPException(status_code=500, detail="Failed to fetch pole history")


@router.get("/live/status")
def get_live_status():
    logger.info("Route called | GET /live/status")

    try:
        status = live_fog_state.get_status()
        logger.info("Live status returned successfully")
        return status

    except Exception:
        logger.exception("Failed to fetch live status")
        raise HTTPException(status_code=500, detail="Failed to fetch live status")


# -------------------------------
# Simulation control routes
# -------------------------------

@router.get("/simulation/status")
def get_simulation_status():
    logger.info("Route called | GET /simulation/status")

    try:
        status = current_scenario.get_status()
        logger.info("Simulation status returned | status=%s", status)
        return status

    except Exception:
        logger.exception("Failed to fetch simulation status")
        raise HTTPException(status_code=500, detail="Failed to fetch simulation status")


@router.post("/simulation/scenario/{scenario}")
def change_scenario(scenario: str):
    logger.info("Route called | POST /simulation/scenario/%s", scenario)

    allowed = {"normal", "load_shedding", "double_pole_failure"}

    if scenario not in allowed:
        logger.warning("Invalid scenario requested | scenario=%s", scenario)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario '{scenario}'. Allowed values: {sorted(allowed)}"
        )

    try:
        previous_status = current_scenario.get_status()
        current_scenario.set_scenario(scenario)
        updated_status = current_scenario.get_status()

        logger.info(
            "Scenario changed successfully | previous_status=%s updated_status=%s",
            previous_status,
            updated_status,
        )

        return {
            "message": f"Scenario changed to {scenario}",
            "status": updated_status,
        }

    except Exception:
        logger.exception("Failed to change scenario | scenario=%s", scenario)
        raise HTTPException(status_code=500, detail="Failed to change scenario")


# --------------------------------
# Log upload route
# --------------------------------

@router.post("/upload-log")
async def upload_log_file(file: UploadFile = File(...)):
    logger.info(
        "Route called | POST /upload-log | filename=%s content_type=%s",
        file.filename,
        file.content_type,
    )

    if not S3_BUCKET_NAME:
        logger.error("S3 upload rejected | reason=s3_bucket_not_configured")
        raise HTTPException(
            status_code=500,
            detail="S3_BUCKET_NAME is not configured"
        )

    if not file.filename:
        logger.warning("S3 upload rejected | reason=missing_filename")
        raise HTTPException(
            status_code=400,
            detail="Missing filename"
        )

    allowed_types = {
        "text/plain",
        "text/csv",
        "application/json",
        "application/octet-stream",
    }

    if file.content_type not in allowed_types:
        logger.warning(
            "S3 upload rejected | filename=%s unsupported_content_type=%s",
            file.filename,
            file.content_type,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}"
        )

    safe_name = file.filename.replace(" ", "_")
    object_key = f"logs/{uuid4()}-{safe_name}"

    try:
        file.file.seek(0)

        logger.info(
            "S3 upload started | bucket=%s key=%s filename=%s",
            S3_BUCKET_NAME,
            object_key,
            file.filename,
        )

        s3_client.upload_fileobj(
            Fileobj=file.file,
            Bucket=S3_BUCKET_NAME,
            Key=object_key,
            ExtraArgs={
                "ContentType": file.content_type or "text/plain",
            },
        )

        file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{object_key}"

        logger.info(
            "S3 upload completed | bucket=%s key=%s filename=%s",
            S3_BUCKET_NAME,
            object_key,
            file.filename,
        )

        return {
            "message": "Log uploaded successfully",
            "bucket": S3_BUCKET_NAME,
            "key": object_key,
            "url": file_url,
        }

    except (ClientError, BotoCoreError):
        logger.exception(
            "S3 upload failed | bucket=%s filename=%s key=%s",
            S3_BUCKET_NAME,
            file.filename,
            object_key,
        )
        raise HTTPException(
            status_code=500,
            detail="S3 upload failed"
        )

    except Exception:
        logger.exception(
            "Unexpected upload failure | bucket=%s filename=%s key=%s",
            S3_BUCKET_NAME,
            file.filename,
            object_key,
        )
        raise HTTPException(
            status_code=500,
            detail="Unexpected upload failure"
        )

    finally:
        await file.close()
        logger.info("Uploaded file handle closed | filename=%s", file.filename)


@router.get("/health")
def health() -> dict[str, str]:
    logger.info("Route called | GET /health")
    return {"status": "ok"}