"""
Thread-safe simulation state manager for handling dynamic scenario switching during runtime.
"""

from threading import Lock
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SimulationState:
    def __init__(self):
        self._current_scenario = "normal"
        self._lock = Lock()
        # Initialize logging for simulation state changes
        logger.info("Simulation state initialized")

    def get_scenario(self) -> str:
        """Retrieve current scenario in a thread-safe manner."""
        with self._lock:
            logger.info("Getting current scenario")
            return self._current_scenario

    def set_scenario(self, scenario: str) -> None:
        """Update scenario with thread-safe locking."""
        with self._lock:
            self._current_scenario = scenario
            logger.info(f"Scenario changed to {scenario}")

    def get_status(self) -> dict:
        """Get the current simulation status including scenario and timestamp."""
        logger.info("Getting simulation status")
        return {
            "current_scenario": self.get_scenario(),
            "timestamp": "live"
        }


# Global singleton instance that manages the current simulation scenario
current_scenario = SimulationState()