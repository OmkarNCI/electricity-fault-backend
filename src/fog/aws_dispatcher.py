from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Any

import boto3

from Backend.src.common.config import CONFIG
from Backend.src.common.models import AreaSummary, DetectionResult

logger = logging.getLogger(__name__)


class AWSDispatcher:
    def __init__(self) -> None:
        self.region = CONFIG.aws["region"]
        self.sqs_queue_url = CONFIG.aws["sqs_queue_url"]

        self.sqs = boto3.client("sqs", region_name=self.region)
        logger.info("AWSDispatcher initialized | region=%s queue_url=%s", self.region, self.sqs_queue_url)

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """
        Convert Python objects into JSON-safe values.
        """
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        return value

    def _serialize_dataclass(self, obj: Any) -> dict[str, Any]:
        """
        Convert dataclass model into a JSON-safe dictionary.
        """
        data = asdict(obj)
        return {key: self._serialize_nested(value) for key, value in data.items()}

    def _serialize_nested(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {k: self._serialize_nested(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._serialize_nested(v) for v in value]
        return self._serialize_value(value)

    def _send_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Send a JSON message to SQS.
        """
        logger.info("Sending message to SQS | queue_url=%s payload_size=%s", self.sqs_queue_url, len(json.dumps(payload)))
        try:
            response = self.sqs.send_message(
                QueueUrl=self.sqs_queue_url,
                MessageBody=json.dumps(payload),
            )
            logger.info("SQS message sent | message_id=%s", response.get("MessageId"))
            return response
        except Exception:
            logger.exception("SQS send failed | queue_url=%s", self.sqs_queue_url)
            raise

    def send_alert(self, alert: DetectionResult) -> dict[str, Any]:
        """
        Send a DetectionResult to SQS as an ALERT message.
        """
        logger.info("Sending ALERT | area=%s pole=%s alert_type=%s", alert.area_id, alert.pole_id, alert.alert_type)
        payload = {
            "type": "ALERT",
            "data": self._serialize_dataclass(alert),
        }
        response = self._send_message(payload)
        logger.info("ALERT sent successfully | message_id=%s", response.get("MessageId"))
        return response

    def send_area_summary(self, summary: AreaSummary) -> dict[str, Any]:
        """
        Send an AreaSummary to SQS as an AREA_SUMMARY message.
        """
        logger.info("Sending AREA_SUMMARY | area=%s classification=%s", summary.area_id, summary.classification)
        payload = {
            "type": "AREA_SUMMARY",
            "data": self._serialize_dataclass(summary),
        }
        response = self._send_message(payload)
        logger.info("AREA_SUMMARY sent successfully | message_id=%s", response.get("MessageId"))
        return response