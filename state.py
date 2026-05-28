"""
App state persistence (favorites + winner) via a JSON file.
"""
import json
from config import STATE_PATH

_DEFAULT: dict = {"favorites": [], "winner": None}


def load_state() -> dict:
    if STATE_PATH.exists():
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return dict(_DEFAULT)


def save_state(state: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def ensure_state_file() -> None:
    """Create the state file with defaults if it doesn't exist."""
    if not STATE_PATH.exists():
        save_state(dict(_DEFAULT))
