# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

import subprocess  # noqa: F401  (re-exported for tests)
from pathlib import Path  # noqa: F401  (re-exported for tests)

import pytest  # noqa: F401  (re-exported for tests)

import keystone_osk.control as control_module  # module-level import is PySide6-free
import keystone_osk.doctor as doctor_module  # PySide6-free (--doctor runs without Qt)
from keystone_osk.backend import KEYCODES, YdotoolBackend, keycode_for, ydotool_key_args
from keystone_osk.config import (
    learned_words_path,
    system_theme_dir,
    user_theme_dir,
    window_state_path,
)
from keystone_osk.geometry import PositionedKey, Rect, build_full_key_geometry, build_key_geometry
from keystone_osk.input_model import (
    NUMPAD_NAV_LABELS,
    is_repeatable_key,
    key_label_display,
    output_key_for,
)
from keystone_osk.layout import build_linux_layout
from keystone_osk.theme import (
    BUILTIN_THEME_IDS,
    THEME_PACK_FORBIDDEN_SECTIONS,
    THEME_PACK_SAFE_SECTIONS,
    bundled_theme_dir,
    discover_theme_pack_ids,
    load_theme_pack,
    theme_pack_path,
    theme_pack_search_dirs,
    validate_theme_pack,
)

FULL_WINDOW_WIDTH = 960
FULL_WINDOW_HEIGHT = 240
MIN_FULL_WINDOW_WIDTH = 960
MIN_WINDOW_HEIGHT = 220


class RecordingBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []
        self.text_calls: list[str] = []
        self.unicode_text_calls: list[str] = []
        self.ensure_numlock_calls: int = 0

    def ensure_numlock_on(self) -> None:
        self.ensure_numlock_calls += 1

    def press_key(self, key: PositionedKey) -> None:
        self.calls.append((key.label, ()))

    def press_key_with_modifiers(self, key: PositionedKey, modifiers: tuple[str, ...]) -> None:
        self.calls.append((key.label, tuple(modifiers)))

    def type_text(self, text: str) -> None:
        self.text_calls.append(text)

    def type_unicode_text(self, text: str) -> None:
        self.unicode_text_calls.append(text)


def key(label: str) -> PositionedKey:
    return PositionedKey(label.lower(), label, Rect(0, 0, 1, 1))
