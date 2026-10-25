"""Preferencias del usuario en %LOCALAPPDATA%\\PeripheralBattery\\settings.json."""
import json
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "PeripheralBattery"
DATA_DIR.mkdir(parents=True, exist_ok=True)
_FILE = DATA_DIR / "settings.json"

DEFAULTS = {
    "low_battery_alert": True,
    "low_battery_threshold": 15,
    # Consultar GitHub Releases solo; desactivable (politica de privacidad / SignPath).
    "auto_update": True,
}


class Settings(dict):
    def __init__(self):
        super().__init__(DEFAULTS)
        try:
            self.update(json.loads(_FILE.read_text()))
        except (OSError, ValueError):
            pass

    def set(self, key, value):
        self[key] = value
        try:
            _FILE.write_text(json.dumps(self, indent=2))
        except OSError:
            pass
