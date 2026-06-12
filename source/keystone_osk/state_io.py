"""PySide6-free window-state I/O.

All persisted-state reading and writing that does NOT need Qt lives here: the
JSON load/store path, and the mode / theme / numpad / boolean field accessors.
It is kept apart from ``state.py`` (which pulls in PySide6 for the geometry
helpers) so that consumers such as ``doctor.py`` can read and resolve persisted
state without importing Qt. Keeping the matched save_*/load_* pairs together in
one module is deliberate: they share the same validation, so they must never
drift apart. ``state.py`` re-exports everything here, so callers can keep
importing these names from ``keystone_osk.state``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from keystone_osk.config import (
    STATE_FILE_ENV,
    legacy_window_state_path as config_legacy_window_state_path,
    window_state_path as config_window_state_path,
)
from keystone_osk.theme import DRACULA_THEME_ID, discover_valid_theme_ids, resolve_theme_id

NUMPAD_OUTPUT_MODES = ("reliable", "true-keypad")
DEFAULT_NUMPAD_OUTPUT_MODE = "reliable"
DEFAULT_SUGGESTIONS_ENABLED = True
DEFAULT_AUTO_CAP_ENABLED = True


def window_state_path() -> Path:
    return config_window_state_path()


def legacy_window_state_path() -> Path:
    return config_legacy_window_state_path()


def readable_window_state_path() -> Path:
    state_path = window_state_path()
    if os.environ.get(STATE_FILE_ENV) or state_path.exists():
        return state_path
    legacy_path = legacy_window_state_path()
    return legacy_path if legacy_path.exists() else state_path


def load_window_state(path: Path | None = None) -> dict:
    state_path = path or readable_window_state_path()
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_window_state(data: dict, path: Path | None = None) -> None:
    state_path = path or window_state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = state_path.with_suffix(f"{state_path.suffix}.tmp")
    tmp_path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    try:
        tmp_path.replace(state_path)
    except OSError:
        # Don't leave a half-written .tmp behind to corrupt the next load.
        tmp_path.unlink(missing_ok=True)
        raise


def save_window_state_fields(updates: dict, path: Path | None = None) -> None:
    # Single read-modify-write for several fields at once. Avoids the N sequential
    # rewrite-and-rename cycles (and N crash windows) of calling each save_* in turn.
    data = load_window_state(path)
    data.update(updates)
    write_window_state(data, path)


def _load_bool_state(key: str, default: bool, path: Path | None = None) -> bool:
    value = load_window_state(path).get(key)
    return value if isinstance(value, bool) else default


def _save_bool_state(key: str, value: bool, path: Path | None = None) -> None:
    data = load_window_state(path)
    data[key] = bool(value)
    write_window_state(data, path)


def load_keyboard_mode(path: Path | None = None) -> str:
    mode = load_window_state(path).get("mode")
    return "full" if mode == "full" else "compact"


def save_keyboard_mode(mode: str, path: Path | None = None) -> None:
    data = load_window_state(path)
    data["mode"] = "full" if mode == "full" else "compact"
    write_window_state(data, path)


def load_keyboard_theme(path: Path | None = None) -> str:
    raw = load_window_state(path).get("theme")
    return resolve_theme_id(raw, discover_valid_theme_ids(), strict=False) or DRACULA_THEME_ID


def persisted_keyboard_theme(path: Path | None = None) -> str | None:
    """The saved theme as a valid id, or None when nothing valid is persisted
    (i.e. a fresh install). Lets the app distinguish "first run" from a user
    who has actually chosen a theme."""
    raw = load_window_state(path).get("theme")
    if not raw:
        return None
    return resolve_theme_id(raw, discover_valid_theme_ids(), strict=False)


def save_keyboard_theme(theme: str, path: Path | None = None) -> None:
    resolved = resolve_theme_id(theme, discover_valid_theme_ids(), strict=False) or DRACULA_THEME_ID
    data = load_window_state(path)
    data["theme"] = resolved
    write_window_state(data, path)


def load_numpad_output_mode(path: Path | None = None) -> str:
    value = load_window_state(path).get("numpad_output_mode")
    return value if value in NUMPAD_OUTPUT_MODES else DEFAULT_NUMPAD_OUTPUT_MODE


def save_numpad_output_mode(mode: str, path: Path | None = None) -> None:
    data = load_window_state(path)
    data["numpad_output_mode"] = mode if mode in NUMPAD_OUTPUT_MODES else DEFAULT_NUMPAD_OUTPUT_MODE
    write_window_state(data, path)


def load_suggestions_enabled(path: Path | None = None) -> bool:
    return _load_bool_state("suggestions_enabled", DEFAULT_SUGGESTIONS_ENABLED, path)


def save_suggestions_enabled(enabled: bool, path: Path | None = None) -> None:
    _save_bool_state("suggestions_enabled", enabled, path)


def load_auto_cap_enabled(path: Path | None = None) -> bool:
    return _load_bool_state("auto_cap_enabled", DEFAULT_AUTO_CAP_ENABLED, path)


def save_auto_cap_enabled(enabled: bool, path: Path | None = None) -> None:
    _save_bool_state("auto_cap_enabled", enabled, path)
