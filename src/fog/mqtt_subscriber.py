import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any

import paho.mqtt.client as paho_mqtt
from awscrt import mqtt as aws_mqtt
from awsiot import mqtt_connection_builder

from src.common.config import CONFIG
from src.common.models import SensorEvent
from src.fog.aggregator import AreaAggregator
from src.fog.aws_dispatcher import AWSDispatcher
from src.fog.connection_manager import manager
from src.fog.detection import detect_event
from src.fog.live_state import live_fog_state

logger = logging.getLogger(__name__)


class MQTTSubscriber:
    def __init__(self):
        # -------------------------
        # LOCAL MQTT (NO CHANGE)
        # -------------------------
        self.broker_host = CONFIG.mqtt.get("broker_host", "localhost")
        self.broker_port = int(CONFIG.mqtt.get("broker_port", 1883))
        self.base_topic = CONFIG.mqtt.get("base_topic", "area")

        self.local_client = paho_mqtt.Client(client_id="electricity-sim")
        self.local_client.on_connect = self.on_local_connect
        self.local_client.on_message = self.on_local_message

        # -------------------------
        # AWS IoT CORE (UNCHANGED)
        # -------------------------
        self.aws_endpoint = "a3rif3julyho61-ats.iot.us-east-1.amazonaws.com"
        self.aws_client_id = "fog-processor-1"
        self.cert_path = "./certs/certificate.pem.crt"
        self.key_path = "./certs/private.pem.key"
        self.ca_path = "./certs/AmazonRootCA1.pem"
        self.aws_conn = None

        # -------------------------
        # STATE / LOGIC
        # -------------------------
        self.aggregator = AreaAggregator()
        self.dispatcher = AWSDispatcher()
        self.summary_interval = CONFIG.fog.get("summary_interval_seconds", 60)
        self.last_summary_time = time.time()

    # -------------------------
    # CONNECT
    # -------------------------
    def connect(self):
        try:
            print(f"Connecting to AWS IoT Core at {self.aws_endpoint}...")

            self.aws_conn = mqtt_connection_builder.mtls_from_path(
                endpoint=self.aws_endpoint,
                cert_filepath=self.cert_path,
                pri_key_filepath=self.key_path,
                ca_filepath=self.ca_path,
                client_id=self.aws_client_id,
                clean_session=False,
                keep_alive_secs=30
            )
            self.aws_conn.connect().result()

            print("✓ Connected to AWS IoT Core")

        except Exception as e:
            logger.error(f"AWS IoT Connection failed: {e}")
            self.aws_conn = None

        print(f"Connecting to local broker {self.broker_host}:{self.broker_port}...")
        self.local_client.connect(self.broker_host, self.broker_port, 60)
        self.local_client.loop_forever()

    # -------------------------
    # MQTT CONNECT
    # -------------------------
    def on_local_connect(self, client, userdata, flags, rc):
        if rc == 0:
            topic = f"{self.base_topic}/+/+/readings"
            print(f"✓ Connected local MQTT → subscribing {topic}")
            client.subscribe(topic)
        else:
            logger.error(f"MQTT connect failed rc={rc}")

    # -------------------------
    # MAIN PIPELINE
    # -------------------------
    def on_local_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            event = self.payload_to_sensor_event(payload)

            alerts = detect_event(event)

            # UI live update
            live_fog_state.update_event(event)

            self.broadcast({
                "type": "sensor",
                "data": live_fog_state._event_to_dict(event)
            })

            # ALERTS
            for alert in alerts:

                self._publish_to_aws(
                    topic=f"area/{alert.area_id}/alerts/{alert.pole_id}",
                    payload=alert.to_payload()
                )

            # TELEMETRY
            self._publish_to_aws(
                topic=f"area/{event.area_id}/telemetry/{event.pole_id}",
                payload=payload
            )

            # SUMMARY
            now = time.time()
            if now - self.last_summary_time >= self.summary_interval:

                for summary in self.aggregator.build_all_area_summaries():

                    self._publish_to_aws(
                        topic=f"area/{summary.area_id}/summaries",
                        payload=summary.to_payload()
                    )

                self.last_summary_time = now

        except Exception as e:
            logger.exception(e)

    # -------------------------
    # AWS PUBLISH
    # -------------------------
    def _publish_to_aws(self, topic: str, payload: dict):
        if not self.aws_conn:
            return

        try:
            if isinstance(payload.get("timestamp"), datetime):
                payload["timestamp"] = payload["timestamp"].isoformat()

            self.aws_conn.publish(
                topic=topic,
                payload=json.dumps(payload),
                qos=aws_mqtt.QoS.AT_LEAST_ONCE
            )

        except Exception as e:
            logger.warning(f"AWS publish failed: {e}")

    # -------------------------
    # WEBSOCKET
    # -------------------------
    def broadcast(self, data: dict):
        try:
            loop = asyncio.get_event_loop()

            if loop.is_running():
                asyncio.create_task(manager.broadcast(data))
            else:
                loop.run_until_complete(manager.broadcast(data))

        except RuntimeError:
            asyncio.run(manager.broadcast(data))

    # -------------------------
    # PARSER
    # -------------------------
    @staticmethod
    def payload_to_sensor_event(payload: dict[str, Any]) -> SensorEvent:
        return SensorEvent(
            area_id=payload["area_id"],
            pole_id=payload["pole_id"],
            timestamp=datetime.fromisoformat(payload["timestamp"]),
            voltage_v=float(payload["voltage_v"]),
            current_a=float(payload["current_a"]),
            tilt_deg=float(payload["tilt_deg"]),
            temperature_c=float(payload["temperature_c"]),
            line_fault_indicator=int(payload["line_fault_indicator"]),
            smart_meter_kw=float(payload["smart_meter_kw"]),
            power_status=int(payload["power_status"]),
        )