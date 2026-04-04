from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

import paho.mqtt.client as mqtt

from Backend.src.common.config import CONFIG
from Backend.src.common.models import SensorEvent
from Backend.src.fog.detection import detect_event
from Backend.src.fog.aggregator import AreaAggregator
from Backend.src.fog.aws_dispatcher import AWSDispatcher
from Backend.src.fog.connection_manager import manager
from Backend.src.fog.live_state import live_fog_state


class MQTTSubscriber:
    def __init__(self) -> None:
        self.broker_host = CONFIG.mqtt["broker_host"]
        self.broker_port = int(CONFIG.mqtt["broker_port"])
        self.keepalive = int(CONFIG.mqtt["keepalive"])
        self.base_topic = CONFIG.mqtt["base_topic"]
        self.client_id_prefix = CONFIG.mqtt["client_id_prefix"]

        self.summary_interval = CONFIG.fog["summary_interval_seconds"]
        self.last_summary_time = time.time()

        client_id = f"{self.client_id_prefix}-subscriber"
        self.client = mqtt.Client(client_id=client_id)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.aggregator = AreaAggregator()
        self.dispatcher = AWSDispatcher()

    def topic_filter(self) -> str:
        return f"{self.base_topic}/+/+/readings"

    def connect(self) -> None:
        print(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")
        self.client.connect(self.broker_host, self.broker_port, self.keepalive)
        self.client.loop_forever()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            topic = self.topic_filter()
            print(f"Connected to MQTT broker")
            print(f"Subscribing to topic: {topic}")
            client.subscribe(topic)
        else:
            print(f"Failed to connect, rc={rc}")

    def broadcast(self, data: dict):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(manager.broadcast(data))
            else:
                loop.run_until_complete(manager.broadcast(data))
        except RuntimeError:
            asyncio.run(manager.broadcast(data))

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            event = self.payload_to_sensor_event(payload)
            alerts = detect_event(event)

            self.aggregator.update_event(event)
            self.aggregator.update_alerts(alerts)

            print(f"\n📡 LIVE EVENT -> {event}")
            live_fog_state.update_event(event)

            self.broadcast({
                "type": "sensor",
                "data": payload
            })

            # SEND ALERTS IMMEDIATELY
            if alerts:
                for alert in alerts:
                    print(f"🚨 ALERT -> {alert}")
                    self.dispatcher.send_alert(alert)
                    self.broadcast({"type": "alert", "data": alert})

            # PERIODIC SUMMARY
            current_time = time.time()
            if current_time - self.last_summary_time >= self.summary_interval:
                print("\n Generating area summaries...\n")

                summaries = self.aggregator.build_all_area_summaries()

                for summary in summaries:
                    print(f"AREA SUMMARY -> {summary}")
                    self.dispatcher.send_area_summary(summary)

                self.last_summary_time = current_time

            # cleanup
            self.aggregator.clear_all_alerts()

        except Exception as e:
            print(f"Error: {e}")

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