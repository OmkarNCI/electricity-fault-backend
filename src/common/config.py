from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"

class AppConfig:
    def __init__(self, data: dict[str, Any]):
        self.raw = data
        self.simulation = data["simulation"]
        self.thresholds = data["thresholds"]
        self.aws = data["aws"]
        self.fog = data["fog"]
        self.mqtt = data["mqtt"]


def load_config(path: str | Path = CONFIG_PATH) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return AppConfig(data)


CONFIG = load_config()