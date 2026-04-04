from __future__ import annotations

import logging
from datetime import UTC, datetime

from src.common.config import CONFIG
from src.common.models import AreaSummary, DetectionResult, SensorEvent

logger = logging.getLogger(__name__)

THRESHOLDS = CONFIG.thresholds

NOMINAL_VOLTAGE_V = float(THRESHOLDS["nominal_voltage_v"])
UNDERVOLTAGE_V = float(THRESHOLDS["undervoltage_v"])
OVERLOAD_A = float(THRESHOLDS["overload_a"])
OVERHEATING_C = float(THRESHOLDS["overheating_c"])
TILT_WARNING_DEG = float(THRESHOLDS["tilt_warning_deg"])

SIMULATION_AREAS = CONFIG.simulation["areas"]


def _build_area_pole_count() -> dict[str, int]:
    area_counts: dict[str, int] = {}
    for area in SIMULATION_AREAS:
        area_counts[area["id"]] = len(area["poles"])
    return area_counts


AREA_POLE_COUNT = _build_area_pole_count()


class AreaAggregator:
    def __init__(self) -> None:
        self.latest_events_by_area: dict[str, dict[str, SensorEvent]] = {}
        self.latest_alerts_by_area: dict[str, list[DetectionResult]] = {}
        logger.info("AreaAggregator initialized")

    def update_event(self, event: SensorEvent) -> None:
        """
        Store the latest event for a given pole within its area.
        """
        if event.area_id not in self.latest_events_by_area:
            self.latest_events_by_area[event.area_id] = {}

        self.latest_events_by_area[event.area_id][event.pole_id] = event
        logger.info("Updated event | area=%s pole=%s", event.area_id, event.pole_id)

    def update_alerts(self, alerts: list[DetectionResult]) -> None:
        """
        Store the latest alerts for the area.
        """
        for alert in alerts:
            if alert.area_id not in self.latest_alerts_by_area:
                self.latest_alerts_by_area[alert.area_id] = []

            self.latest_alerts_by_area[alert.area_id].append(alert)
        logger.info("Updated alerts | area=%s alert_count=%s", alerts[0].area_id if alerts else "unknown", len(alerts))

    def build_area_summary(self, area_id: str) -> AreaSummary:
        """
        Build an AreaSummary from the latest pole events in the area.
        """
        logger.info("Building area summary | area=%s", area_id)

        area_events = list(self.latest_events_by_area.get(area_id, {}).values())
        area_alerts = self.latest_alerts_by_area.get(area_id, [])

        active_poles = len(area_events)

        if not area_events:
            logger.warning("No events for area summary | area=%s", area_id)
            return AreaSummary(
                area_id=area_id,
                timestamp=datetime.now(UTC),
                score=0.0,
                classification="NORMAL",
                active_poles=0,
                alert_count=0,
                metrics={},
            )

        undervoltage_count = sum(1 for event in area_events if event.voltage_v < UNDERVOLTAGE_V)
        overload_count = sum(1 for event in area_events if event.current_a > OVERLOAD_A)
        overheating_count = sum(1 for event in area_events if event.temperature_c > OVERHEATING_C)
        tilt_warning_count = sum(1 for event in area_events if event.tilt_deg > TILT_WARNING_DEG)
        line_fault_count = sum(1 for event in area_events if event.line_fault_indicator == 1)

        avg_voltage = sum(event.voltage_v for event in area_events) / active_poles
        avg_current = sum(event.current_a for event in area_events) / active_poles
        avg_temperature = sum(event.temperature_c for event in area_events) / active_poles
        total_smart_meter_kw = sum(event.smart_meter_kw for event in area_events)

        score = self._calculate_score(
            active_poles=active_poles,
            undervoltage_count=undervoltage_count,
            overload_count=overload_count,
            overheating_count=overheating_count,
            tilt_warning_count=tilt_warning_count,
            line_fault_count=line_fault_count,
            avg_voltage=avg_voltage,
        )

        classification = self._classify_score(score)

        logger.info(
            "Area summary built | area=%s score=%.2f classification=%s active_poles=%s",
            area_id,
            score,
            classification,
            active_poles,
        )

        return AreaSummary(
            area_id=area_id,
            timestamp=datetime.now(UTC),
            score=round(score, 2),
            classification=classification,
            active_poles=active_poles,
            alert_count=len(area_alerts),
            metrics={
                "avg_voltage_v": round(avg_voltage, 2),
                "avg_current_a": round(avg_current, 2),
                "avg_temperature_c": round(avg_temperature, 2),
                "total_smart_meter_kw": round(total_smart_meter_kw, 2),
                "undervoltage_count": float(undervoltage_count),
                "overload_count": float(overload_count),
                "overheating_count": float(overheating_count),
                "tilt_warning_count": float(tilt_warning_count),
                "line_fault_count": float(line_fault_count),
                "configured_pole_count": float(AREA_POLE_COUNT.get(area_id, 0)),
            },
        )

    def build_all_area_summaries(self) -> list[AreaSummary]:
        """
        Build summaries for all configured areas.
        """
        logger.info("Building summaries for all areas")
        summaries = [self.build_area_summary(area["id"]) for area in SIMULATION_AREAS]
        logger.info("Built %s area summaries", len(summaries))
        return summaries

    def clear_area_alerts(self, area_id: str) -> None:
        """
        Clear stored alerts for an area after a summary cycle if needed.
        """
        self.latest_alerts_by_area[area_id] = []
        logger.info("Cleared alerts for area=%s", area_id)

    def clear_all_alerts(self) -> None:
        """
        Clear all stored area alerts.
        """
        self.latest_alerts_by_area.clear()
        logger.info("Cleared all area alerts")

    @staticmethod
    def _calculate_score(
        active_poles: int,
        undervoltage_count: int,
        overload_count: int,
        overheating_count: int,
        tilt_warning_count: int,
        line_fault_count: int,
        avg_voltage: float,
    ) -> float:
        """
        Calculate an area risk score from 0 to 100.
        This is a simple weighted scoring model suitable for coursework/demo.
        """
        if active_poles == 0:
            return 0.0

        score = 0.0

        score += (undervoltage_count / active_poles) * 35.0
        score += (overload_count / active_poles) * 25.0
        score += (overheating_count / active_poles) * 15.0
        score += (tilt_warning_count / active_poles) * 10.0
        score += (line_fault_count / active_poles) * 15.0

        if avg_voltage < NOMINAL_VOLTAGE_V:
            voltage_drop_ratio = (NOMINAL_VOLTAGE_V - avg_voltage) / NOMINAL_VOLTAGE_V
            score += voltage_drop_ratio * 20.0

        return min(score, 100.0)

    @staticmethod
    def _classify_score(score: float) -> str:
        """
        Convert numeric score into area class.
        """
        if score >= 80:
            return "SHEDDING_LIKELY"
        if score >= 60:
            return "SHEDDING_RISK"
        if score >= 30:
            return "WARNING"
        return "NORMAL"