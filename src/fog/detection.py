from __future__ import annotations

import logging

from src.common.config import CONFIG
from src.common.models import DetectionResult, SensorEvent

logger = logging.getLogger(__name__)

THRESHOLDS = CONFIG.thresholds

UNDERVOLTAGE_V = float(THRESHOLDS["undervoltage_v"])
OVERLOAD_A = float(THRESHOLDS["overload_a"])
OVERHEATING_C = float(THRESHOLDS["overheating_c"])
TILT_WARNING_DEG = float(THRESHOLDS["tilt_warning_deg"])
TILT_CRITICAL_DEG = float(THRESHOLDS["tilt_critical_deg"])

DOUBLE_POLE_TILT_JUMP_DEG = float(THRESHOLDS["double_pole_tilt_jump_deg"])
DOUBLE_POLE_VOLTAGE_DROP_V = float(THRESHOLDS["double_pole_voltage_drop_v"])
DOUBLE_POLE_CURRENT_SPIKE_A = float(THRESHOLDS["double_pole_current_spike_a"])
NOMINAL_VOLTAGE_V = float(THRESHOLDS["nominal_voltage_v"])


def detect_threshold_alerts(event: SensorEvent) -> list[DetectionResult]:
    alerts: list[DetectionResult] = []

    if event.voltage_v < UNDERVOLTAGE_V:
        alerts.append(
            DetectionResult(
                area_id=event.area_id,
                pole_id=event.pole_id,
                timestamp=event.timestamp,
                severity="WARNING",
                alert_type="UNDERVOLTAGE",
                details={
                    "voltage_v": event.voltage_v,
                    "threshold_v": UNDERVOLTAGE_V,
                },
            )
        )
        logger.info("UNDERVOLTAGE detected")

    if event.current_a > OVERLOAD_A:
        alerts.append(
            DetectionResult(
                area_id=event.area_id,
                pole_id=event.pole_id,
                timestamp=event.timestamp,
                severity="WARNING",
                alert_type="OVERLOAD",
                details={
                    "current_a": event.current_a,
                    "threshold_a": OVERLOAD_A,
                },
            )
        )
        logger.info("OVERLOAD detected")

    if event.temperature_c > OVERHEATING_C:
        alerts.append(
            DetectionResult(
                area_id=event.area_id,
                pole_id=event.pole_id,
                timestamp=event.timestamp,
                severity="WARNING",
                alert_type="OVERHEATING",
                details={
                    "temperature_c": event.temperature_c,
                    "threshold_c": OVERHEATING_C,
                },
            )
        )
        logger.info("OVERHEATING detected")

    if event.tilt_deg > TILT_CRITICAL_DEG:
        alerts.append(
            DetectionResult(
                area_id=event.area_id,
                pole_id=event.pole_id,
                timestamp=event.timestamp,
                severity="CRITICAL",
                alert_type="TILT_CRITICAL",
                details={
                    "tilt_deg": event.tilt_deg,
                    "threshold_deg": TILT_CRITICAL_DEG,
                },
            )
        )
        logger.info("TILT_CRITICAL detected")
    elif event.tilt_deg > TILT_WARNING_DEG:
        alerts.append(
            DetectionResult(
                area_id=event.area_id,
                pole_id=event.pole_id,
                timestamp=event.timestamp,
                severity="WARNING",
                alert_type="TILT_WARNING",
                details={
                    "tilt_deg": event.tilt_deg,
                    "threshold_deg": TILT_WARNING_DEG,
                },
            )
        )
        logger.info("TILT_WARNING detected")

    if event.line_fault_indicator == 1:
        alerts.append(
            DetectionResult(
                area_id=event.area_id,
                pole_id=event.pole_id,
                timestamp=event.timestamp,
                severity="CRITICAL",
                alert_type="LINE_FAULT_DETECTED",
                details={
                    "line_fault_indicator": event.line_fault_indicator,
                },
            )
        )
        logger.info("LINE_FAULT_DETECTED detected")

    return alerts


def detect_double_pole_failure_risk(event: SensorEvent) -> list[DetectionResult]:
    alerts: list[DetectionResult] = []

    tilt_condition = event.tilt_deg >= DOUBLE_POLE_TILT_JUMP_DEG
    voltage_condition = (NOMINAL_VOLTAGE_V - event.voltage_v) >= DOUBLE_POLE_VOLTAGE_DROP_V
    current_condition = (event.current_a - OVERLOAD_A) >= DOUBLE_POLE_CURRENT_SPIKE_A
    lfi_condition = event.line_fault_indicator == 1

    if tilt_condition and voltage_condition and (current_condition or lfi_condition):
        alerts.append(
            DetectionResult(
                area_id=event.area_id,
                pole_id=event.pole_id,
                timestamp=event.timestamp,
                severity="CRITICAL",
                alert_type="DOUBLE_POLE_FAILURE_RISK",
                details={
                    "tilt_deg": event.tilt_deg,
                    "tilt_jump_threshold_deg": DOUBLE_POLE_TILT_JUMP_DEG,
                    "voltage_v": event.voltage_v,
                    "voltage_drop_v": NOMINAL_VOLTAGE_V - event.voltage_v,
                    "voltage_drop_threshold_v": DOUBLE_POLE_VOLTAGE_DROP_V,
                    "current_a": event.current_a,
                    "current_spike_a": max(event.current_a - OVERLOAD_A, 0.0),
                    "current_spike_threshold_a": DOUBLE_POLE_CURRENT_SPIKE_A,
                    "line_fault_indicator": event.line_fault_indicator,
                },
            )
        )
        logger.info("DOUBLE_POLE_FAILURE_RISK detected")

    return alerts


def detect_event(event: SensorEvent) -> list[DetectionResult]:
    alerts: list[DetectionResult] = []
    alerts.extend(detect_threshold_alerts(event))
    alerts.extend(detect_double_pole_failure_risk(event))

    if alerts:
        logger.info("Detection completed with alerts")
    else:
        logger.info("Detection completed with no alerts")

    return alerts