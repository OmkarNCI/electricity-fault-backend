"""
Thread-safe simulation state for dynamic scenario switching.
"""

from threading import Lock
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SimulationState:
    def __init__(self):
        self._current_scenario = "normal"
        self._lock = Lock()
        logger.info("Simulation state initialized")

    def get_scenario(self) -> str:
        """Get current scenario (thread-safe)."""
        with self._lock:
            logger.info("Getting current scenario")
            return self._current_scenario

    def set_scenario(self, scenario: str) -> None:
        """Set current scenario (thread-safe)."""
        with self._lock:
            self._current_scenario = scenario
            logger.info(f"Scenario changed to {scenario}")

    def get_status(self) -> dict:
        """Get current scenario status."""
        logger.info("Getting simulation status")
        return {
            "current_scenario": self.get_scenario(),
            "timestamp": "live"
        }


# Global singleton instance
current_scenario = SimulationState()