from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime

import paho.mqtt.client as mqtt

from src.common.config import CONFIG
from src.common.models import SensorEvent

logger = logging.getLogger(__name__)


class MQTTPublisher:
    def __init__(self) -> None:
        self.broker_host = CONFIG.mqtt["broker_host"]
        self.broker_port = int(CONFIG.mqtt["broker_port"])
        self.keepalive = int(CONFIG.mqtt["keepalive"])
        self.base_topic = CONFIG.mqtt["base_topic"]
        self.client_id_prefix = CONFIG.mqtt["client_id_prefix"]

        client_id = f"{self.client_id_prefix}-publisher"
        self.client = mqtt.Client(client_id=client_id)

        logger.info("MQTT Publisher initialized")

    def connect(self) -> None:
        """
        Connect to the MQTT broker.
        """
        logger.info("Connecting to MQTT broker")
        self.client.connect(self.broker_host, self.broker_port, self.keepalive)
        self.client.loop_start()
        logger.info("Connected to MQTT broker")

    def disconnect(self) -> None:
        """
        Disconnect from the MQTT broker.
        """
        logger.info("Disconnecting from MQTT broker")
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Disconnected from MQTT broker")

    def build_topic(self, event: SensorEvent) -> str:
        """
        Build topic like: grid/AREA_1/P1/readings
        """
        return f"{self.base_topic}/{event.area_id}/{event.pole_id}/readings"

    @staticmethod
    def event_to_dict(event: SensorEvent) -> dict:
        """
        Convert SensorEvent to dictionary and serialize datetime.
        """
        data = asdict(event)
        if isinstance(event.timestamp, datetime):
            data["timestamp"] = event.timestamp.isoformat()
        return data

    def publish_event(self, event: SensorEvent) -> None:
        """
        Publish one SensorEvent to the broker.
        """
        topic = self.build_topic(event)
        payload = json.dumps(self.event_to_dict(event))

        result = self.client.publish(topic, payload)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info("Published event")
        else:
            logger.warning("Failed to publish")