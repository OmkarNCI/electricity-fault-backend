from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Literal, Any

AreaClass = Literal["NORMAL", "WARNING", "SHEDDING_RISK", "SHEDDING_LIKELY"]


@dataclass(slots=True)
class SensorEvent:
    area_id: str
    pole_id: str
    timestamp: datetime
    voltage_v: float
    current_a: float
    tilt_deg: float
    temperature_c: float
    line_fault_indicator: int
    smart_meter_kw: float
    power_status: int

    def to_payload(self) -> dict[str, Any]:
        """Converts the event to a JSON-ready dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass(slots=True)
class DetectionResult:
    area_id: str
    pole_id: str
    timestamp: datetime
    severity: Literal["INFO", "WARNING", "CRITICAL"]
    alert_type: str
    details: dict[str, float | int | str]

    def to_payload(self) -> dict[str, Any]:
        """Converts the alert to a JSON-ready dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass(slots=True)
class AreaSummary:
    area_id: str
    timestamp: datetime
    score: float
    classification: AreaClass
    active_poles: int
    alert_count: int
    metrics: dict[str, float] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        """Converts the summary to a JSON-ready dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data