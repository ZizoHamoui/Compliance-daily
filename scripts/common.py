"""Shared helpers: paths, config loading, time zone handling, JSON state."""
import json
import hashlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
DATA = ROOT / "data"
CANDIDATES = DATA / "candidates"
EDITIONS = ROOT / "editions"
SITE = ROOT / "site"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"


def load_yaml(name):
    with open(CONFIG / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


PAPER = load_yaml("paper.yaml")
TZ = ZoneInfo(PAPER.get("timezone", "America/Vancouver"))


def now_local():
    return datetime.now(TZ)


def today_local():
    return now_local().strftime("%Y-%m-%d")


def read_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def uid(url):
    return hashlib.sha1(url.strip().encode("utf-8")).hexdigest()[:12]


STATE_FILE = DATA / "state.json"


def get_state():
    return read_json(STATE_FILE, {})


def set_state(**kw):
    s = get_state()
    s.update(kw)
    write_json(STATE_FILE, s)
