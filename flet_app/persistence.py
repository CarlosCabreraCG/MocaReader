# Persistencia JSON
# ______________________

import json
from pathlib import Path

# KEYWORD: DATA_DIR
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

PALETTES_FILE = DATA_DIR / "palettes.json"
SETTINGS_FILE = DATA_DIR / "settings.json"


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_palettes():
    return _read_json(PALETTES_FILE, [])


def save_palettes(palettes):
    _write_json(PALETTES_FILE, palettes)


def load_settings():
    return _read_json(SETTINGS_FILE, {})


def save_settings(settings):
    _write_json(SETTINGS_FILE, settings)