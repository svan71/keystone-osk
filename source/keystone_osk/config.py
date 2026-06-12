from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from keystone_osk.constants import APP_ID

APP_DIR_NAME = APP_ID
THEME_APP_DIR_NAME = "keystone"
STATE_FILE_ENV = "KEYSTONE_OSK_STATE_FILE"
WORDS_FILE_ENV = "KEYSTONE_OSK_WORDS_FILE"
SNIPPETS_FILE_ENV = "KEYSTONE_OSK_SNIPPETS_FILE"


def config_home_path(environ: Mapping[str, str] | None = None) -> Path:
    values = os.environ if environ is None else environ
    return Path(values.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def state_home_path(environ: Mapping[str, str] | None = None) -> Path:
    values = os.environ if environ is None else environ
    return Path(values.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")


def data_home_path(environ: Mapping[str, str] | None = None) -> Path:
    values = os.environ if environ is None else environ
    return Path(values.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")


def app_config_dir(environ: Mapping[str, str] | None = None) -> Path:
    return config_home_path(environ) / APP_DIR_NAME


def app_state_dir(environ: Mapping[str, str] | None = None) -> Path:
    return state_home_path(environ) / APP_DIR_NAME


def user_theme_dir(environ: Mapping[str, str] | None = None) -> Path:
    return data_home_path(environ) / THEME_APP_DIR_NAME / "themes"


def system_theme_dir() -> Path:
    return Path("/usr/share/keystone/themes")


def window_state_path(environ: Mapping[str, str] | None = None) -> Path:
    values = os.environ if environ is None else environ
    if override := values.get(STATE_FILE_ENV):
        return Path(override)
    return app_state_dir(values) / "window-state.json"


def legacy_window_state_path(environ: Mapping[str, str] | None = None) -> Path:
    return app_config_dir(environ) / "window-state.json"


def learned_words_path(environ: Mapping[str, str] | None = None) -> Path:
    values = os.environ if environ is None else environ
    if override := values.get(WORDS_FILE_ENV):
        return Path(override)
    return app_state_dir(values) / "words.json"


def snippets_path(environ: Mapping[str, str] | None = None) -> Path:
    values = os.environ if environ is None else environ
    if override := values.get(SNIPPETS_FILE_ENV):
        return Path(override)
    return app_config_dir(values) / "snippets.json"
