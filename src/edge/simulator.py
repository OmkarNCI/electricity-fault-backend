from __future__ import annotations

import json
import logging
import random
import time
import math
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Iterator

from Backend.src.common.config import CONFIG
from Backend.src.common.models import SensorEvent
from Backend.src.edge.mqtt_publisher import MQTTPublisher
from Backend.src.edge.simulation_state import current_scenario

logger = logging.getLogger(__name__)


def _build_area_map() -> dict[str, list[str]]:
    area_map: dict[str, list[str]] = {}
    for area in CONFIG.simulation["areas"]:
        area_map[area["id"]] = area["poles"]
    return area_map


AREAS = _build_area_map()
FREQUENCY_SECONDS: float = float(CONFIG.simulation["frequency_seconds"])
DURATION_SECONDS: int = int(CONFIG.simulation["duration_seconds"])
THRESHOLDS = CONFIG.thresholds


def generate_normal_event(area_id: str, pole_id: str) -> SensorEvent:
    nominal_voltage = float(THRESHOLDS["nominal_voltage_v"])
    t = time.time()
    
    return SensorEvent(
        area_id=area_id,
        pole_id=pole_id,
        timestamp=datetime.now(UTC),
        voltage_v=round(nominal_voltage + 5 * math.sin(t / 5) + random.uniform(-2, 2), 2),
        current_a=round(60 + 10 * math.sin(t / 4) + random.uniform(-3, 3), 2),
        tilt_deg=round(2 + 1.5 * math.sin(t / 3) + random.uniform(-0.5, 0.5), 2),
        temperature_c=round(35 + 5 * math.sin(t / 6) + random.uniform(-1, 1), 2),
        smart_meter_kw=round(5 + 2 * math.sin(t / 7) + random.uniform(-1, 1), 2),
        line_fault_indicator=0,
        power_status=1,
    )


def generate_load_shedding_event(area_id: str, pole_id: str) -> SensorEvent:
    t = time.time()
    undervoltage = float(THRESHOLDS["undervoltage_v"])
    overload = float(THRESHOLDS["overload_a"])
    
    return SensorEvent(
        area_id=area_id,
        pole_id=pole_id,
        timestamp=datetime.now(UTC),
        voltage_v=round(undervoltage + 5 * math.sin(t / 5) + random.uniform(-3, 3), 2),
        current_a=round(overload + 15 * math.sin(t / 4) + random.uniform(-5, 5), 2),
        tilt_deg=round(3 + 2 * math.sin(t / 3), 2),
        temperature_c=round(45 + 8 * math.sin(t / 6), 2),
        smart_meter_kw=round(12 + 3 * math.sin(t / 7), 2),
        line_fault_indicator=0,
        power_status=1,
    )


def generate_double_pole_failure_event(area_id: str, pole_id: str) -> SensorEvent:
    undervoltage = float(THRESHOLDS["undervoltage_v"])
    overload = float(THRESHOLDS["overload_a"])
    tilt_critical = float(THRESHOLDS["tilt_critical_deg"])
    
    return SensorEvent(
        area_id=area_id,
        pole_id=pole_id,
        timestamp=datetime.now(UTC),
        voltage_v=round(random.uniform(undervoltage - 30, undervoltage - 5), 2),
        current_a=round(random.uniform(overload + 10, overload + 40), 2),
        tilt_deg=round(random.uniform(tilt_critical, tilt_critical + 10), 2),
        temperature_c=round(random.uniform(50.0, 85.0), 2),
        line_fault_indicator=1,
        smart_meter_kw=round(random.uniform(10.0, 20.0), 2),
        power_status=1,
    )


def generate_event(area_id: str, pole_id: str) -> SensorEvent:
    """Dynamically reads current scenario from shared state."""
    scenario = current_scenario.get_scenario()
    
    logger.info("Generating event | area=%s pole=%s scenario=%s", area_id, pole_id, scenario)
    
    if scenario == "normal":
        return generate_normal_event(area_id, pole_id)
    if scenario == "load_shedding":
        return generate_load_shedding_event(area_id, pole_id)
    if scenario == "double_pole_failure":
        return generate_double_pole_failure_event(area_id, pole_id)
    
    logger.warning("Unsupported scenario '%s', falling back to normal", scenario)
    return generate_normal_event(area_id, pole_id)


def event_stream() -> Iterator[SensorEvent]:
    while True:
        for area_id, poles in AREAS.items():
            for pole_id in poles:
                yield generate_event(area_id, pole_id)


def timed_event_stream(duration_seconds: int = DURATION_SECONDS) -> Iterator[SensorEvent]:
    end_time = time.time() + duration_seconds
    while time.time() < end_time:
        for area_id, poles in AREAS.items():
            for pole_id in poles:
                if time.time() >= end_time:
                    break
                yield generate_event(area_id, pole_id)


def event_to_dict(event: SensorEvent) -> dict:
    data = asdict(event)
    data["timestamp"] = event.timestamp.isoformat()
    return data


def event_to_json(event: SensorEvent) -> str:
    return json.dumps(event_to_dict(event))


def run_simulator(
    frequency_seconds: float = FREQUENCY_SECONDS,
    duration_seconds: int = DURATION_SECONDS,
    use_mqtt: bool = False,
) -> None:
    publisher = None
    
    logger.info("Starting simulator | frequency=%ss | duration=%ss | mqtt=%s", frequency_seconds, duration_seconds, use_mqtt)
    
    if use_mqtt:
        publisher = MQTTPublisher()
        publisher.connect()
    
    try:
        for event in timed_event_stream(duration_seconds=duration_seconds):
            if use_mqtt and publisher:
                logger.info("MQTT publish | area=%s pole=%s", event.area_id, event.pole_id)
                publisher.publish_event(event)
            else:
                logger.debug("Generated event | area=%s pole=%s", event.area_id, event.pole_id)
            
            time.sleep(frequency_seconds)
    finally:
        if publisher:
            publisher.disconnect()
    
    logger.info("Simulator finished")