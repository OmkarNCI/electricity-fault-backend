from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any

import boto3

from src.cloud.lambda_consumer.config import AWS_REGION, ALERTS_TABLE, AREA_SUMMARIES_TABLE

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
alerts_table = dynamodb.Table(ALERTS_TABLE)
area_summaries_table = dynamodb.Table(AREA_SUMMARIES_TABLE)


def _to_dynamodb_compatible(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _to_dynamodb_compatible(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_dynamodb_compatible(v) for v in value]
    return value


def store_alert(data: dict[str, Any]) -> None:
    item = _to_dynamodb_compatible(data)
    alerts_table.put_item(Item=item)
    logger.info(
        "Stored ALERT | area=%s pole=%s alert_type=%s",
        data.get("area_id"),
        data.get("pole_id"),
        data.get("alert_type"),
    )


def store_area_summary(data: dict[str, Any]) -> None:
    item = _to_dynamodb_compatible(data)
    area_summaries_table.put_item(Item=item)
    logger.info(
        "Stored AREA_SUMMARY | area=%s classification=%s",
        data.get("area_id"),
        data.get("classification"),
    )


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    processed_count = 0
    failed_count = 0

    logger.info("Lambda handler started")

    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            message_type = body["type"]
            data = body["data"]

            if message_type == "ALERT":
                store_alert(data)
            elif message_type == "AREA_SUMMARY":
                store_area_summary(data)
            else:
                logger.warning("Unknown message type: %s", message_type)
                failed_count += 1
                continue

            processed_count += 1

        except Exception:
            logger.exception("Error processing record")
            failed_count += 1

    logger.info(
        "Lambda handler finished | processed_count=%s failed_count=%s",
        processed_count,
        failed_count,
    )

    return {
        "statusCode": 200,
        "processed_count": processed_count,
        "failed_count": failed_count,
    }