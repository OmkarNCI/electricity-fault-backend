from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import boto3

from src.common.config import CONFIG
from src.common.models import DetectionResult

logger = logging.getLogger(__name__)

ALERT_TYPE_DESCRIPTIONS = {
    "UNDERVOLTAGE": "Voltage Level Critical",
    "OVERLOAD": "Current Overload Detected",
    "OVERHEATING": "Temperature Overheat Warning",
    "TILT_CRITICAL": "Pole Tilt Critical Alert",
    "TILT_WARNING": "Pole Tilt Warning",
    "LINE_FAULT": "Line Fault Detected",
}

SEVERITY_BADGES = {
    "CRITICAL": "🔴 CRITICAL",
    "WARNING": "🟡 WARNING",
    "INFO": "🔵 INFO",
}


class SNSNotifier:
    """
    Handles SNS email notifications for electricity grid alerts.
    """

    def __init__(self) -> None:
        self.region = CONFIG.aws["region"]
        self.sns_topic_arn = CONFIG.aws.get("sns_topic_arn")
        
        if not self.sns_topic_arn:
            logger.warning("SNS topic ARN not configured in settings.yaml")
            self.sns_client = None
        else:
            self.sns_client = boto3.client("sns", region_name=self.region)
            logger.info(
                "SNSNotifier initialized | region=%s topic_arn=%s",
                self.region,
                self.sns_topic_arn,
            )

    def _format_alert_subject(self, alert: DetectionResult) -> str:
        """
        Format email subject line for alert.
        """
        alert_type_label = ALERT_TYPE_DESCRIPTIONS.get(
            alert.alert_type, alert.alert_type
        )
        return f"[{alert.severity}] Grid Alert: {alert_type_label} @ {alert.area_id}/{alert.pole_id}"

    def _format_alert_body_text(self, alert: DetectionResult) -> str:
        """
        Format plain text email body for alert.
        """
        timestamp_str = (
            alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(alert.timestamp, datetime)
            else str(alert.timestamp)
        )

        alert_type_label = ALERT_TYPE_DESCRIPTIONS.get(
            alert.alert_type, alert.alert_type
        )
        severity_badge = SEVERITY_BADGES.get(alert.severity, alert.severity)

        # Build details string
        details_str = "\n".join(
            f"  • {key}: {value}"
            for key, value in alert.details.items()
        )

        body = f"""
ELECTRICITY GRID ALERT NOTIFICATION
====================================

Alert Status: {severity_badge}
Alert Type: {alert_type_label}
Timestamp: {timestamp_str}

LOCATION DETAILS
================
Area ID: {alert.area_id}
Pole ID: {alert.pole_id}

ALERT DETAILS
=============
{details_str}

ALERT CLASSIFICATION
====================
Severity Level: {alert.severity}
System ID: {alert.alert_type}

ACTION REQUIRED
===============
Please review this alert immediately. Contact your grid management team if further investigation is needed.

---
This is an automated alert from the Power Fog-Edge Computing System.
For support, contact: gridmanagement@example.com
Timestamp (UTC): {timestamp_str}
"""
        return body



    def send_alert_notification(self, alert: DetectionResult) -> dict[str, Any] | None:
        """
        Send an email notification for a detected alert via SNS.
        
        Returns:
            Response from SNS publish, or None if SNS is not configured.
        """
        if not self.sns_client or not self.sns_topic_arn:
            logger.warning(
                "SNS notification skipped - SNS not configured | area=%s pole=%s alert_type=%s",
                alert.area_id,
                alert.pole_id,
                alert.alert_type,
            )
            return None

        try:
            subject = self._format_alert_subject(alert)
            message_text = self._format_alert_body_text(alert)

            # Create SNS message structure - needs to be JSON string when MessageStructure="json"
            message_structure = {
                "default": message_text,
                "email": message_text,
            }

            logger.info(
                "Sending SNS email alert | topic_arn=%s area=%s pole=%s alert_type=%s severity=%s",
                self.sns_topic_arn,
                alert.area_id,
                alert.pole_id,
                alert.alert_type,
                alert.severity,
            )

            response = self.sns_client.publish(
                TopicArn=self.sns_topic_arn,
                Subject=subject,
                Message=json.dumps(message_structure),  # Must be JSON string when MessageStructure="json"
                MessageStructure="json",
                MessageAttributes={
                    "area_id": {"DataType": "String", "StringValue": alert.area_id},
                    "pole_id": {"DataType": "String", "StringValue": alert.pole_id},
                    "alert_type": {"DataType": "String", "StringValue": alert.alert_type},
                    "severity": {"DataType": "String", "StringValue": alert.severity},
                },
            )

            logger.info(
                "SNS email alert sent successfully | message_id=%s area=%s pole=%s",
                response.get("MessageId"),
                alert.area_id,
                alert.pole_id,
            )

            return response

        except Exception:
            logger.exception(
                "Failed to send SNS email alert | area=%s pole=%s alert_type=%s",
                alert.area_id,
                alert.pole_id,
                alert.alert_type,
            )
            return None


# Global instance
_notifier_instance: SNSNotifier | None = None


def get_sns_notifier() -> SNSNotifier:
    """
    Get or create the SNS notifier singleton instance.
    """
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = SNSNotifier()
    return _notifier_instance
