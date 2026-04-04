from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import asdict
from datetime import datetime, UTC
from typing import Any

from Backend.src.common.models import SensorEvent

logger = logging.getLogger(__name__)


class LiveFogState:
    def __init__(self, history_limit: int = 50) -> None:
        self.history_limit = history_limit

        self.latest_event_by_pole: dict[str, SensorEvent] = {}
        self.latest_event_by_area: dict[str, SensorEvent] = {}

        self.history_by_pole: dict[str, deque[SensorEvent]] = defaultdict(
            lambda: deque(maxlen=self.history_limit)
        )

        self.total_messages_received = 0
        self.last_update_time: datetime | None = None

        logger.info("Live fog state initialized")

    def update_event(self, event: SensorEvent) -> None:
        self.total_messages_received += 1
        self.last_update_time = datetime.now(UTC)

        self.latest_event_by_pole[event.pole_id] = event
        self.latest_event_by_area[event.area_id] = event
        self.history_by_pole[event.pole_id].append(event)

        logger.info("Live event updated | area=%s pole=%s", event.area_id, event.pole_id)

    def get_available_areas(self) -> list[str]:
        logger.info("Fetching available areas")
        return sorted(self.latest_event_by_area.keys())

    def get_available_poles(self) -> list[str]:
        logger.info("Fetching available poles")
        return sorted(self.latest_event_by_pole.keys())

    def get_latest_area_event(self, area_id: str) -> dict[str, Any] | None:
        logger.info("Fetching latest area event | area=%s", area_id)
        event = self.latest_event_by_area.get(area_id)
        return self._event_to_dict(event) if event else None

    def get_latest_pole_event(self, pole_id: str) -> dict[str, Any] | None:
        logger.info("Fetching latest pole event | pole=%s", pole_id)
        event = self.latest_event_by_pole.get(pole_id)
        return self._event_to_dict(event) if event else None

    def get_pole_history(self, pole_id: str) -> list[dict[str, Any]]:
        logger.info("Fetching pole history | pole=%s", pole_id)
        history = self.history_by_pole.get(pole_id, [])
        return [self._event_to_dict(event) for event in history]

    def get_status(self) -> dict[str, Any]:
        logger.info("Fetching live fog status")
        return {
            "fog_status": "ONLINE",
            "total_messages_received": self.total_messages_received,
            "active_areas": len(self.latest_event_by_area),
            "active_poles": len(self.latest_event_by_pole),
            "last_update_time": self.last_update_time.isoformat() if self.last_update_time else None,
        }

    @staticmethod
    def _event_to_dict(event: SensorEvent) -> dict[str, Any]:
        data = asdict(event)
        data["timestamp"] = event.timestamp.isoformat()
        return data


live_fog_state = LiveFogState()