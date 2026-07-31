# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtWidgets import QApplication

from keystone_osk.theme import (  # noqa: F401  (re-exported for back-compat)
    BUILTIN_THEME_IDS,
    DRACULA_THEME_ID,
)
from keystone_osk.state_io import (  # noqa: F401  (pure state I/O, re-exported for back-compat)
    DEFAULT_AUTO_CAP_ENABLED,
    DEFAULT_NUMPAD_OUTPUT_MODE,
    DEFAULT_SUGGESTIONS_ENABLED,
    NUMPAD_OUTPUT_MODES,
    _load_bool_state,
    _save_bool_state,
    legacy_window_state_path,
    load_auto_cap_enabled,
    load_keyboard_mode,
    load_keyboard_theme,
    load_numpad_output_mode,
    load_suggestions_enabled,
    load_window_state,
    persisted_keyboard_theme,
    readable_window_state_path,
    save_auto_cap_enabled,
    save_keyboard_mode,
    save_keyboard_theme,
    save_numpad_output_mode,
    save_suggestions_enabled,
    save_window_state_fields,
    window_state_path,
    write_window_state,
)

DEFAULT_WINDOW_WIDTH = 670
DEFAULT_WINDOW_HEIGHT = 314
FULL_WINDOW_WIDTH = 960
FULL_WINDOW_HEIGHT = 240
MIN_WINDOW_WIDTH = 520
MIN_WINDOW_HEIGHT = 220
MIN_FULL_WINDOW_WIDTH = 960
DEFAULT_RESTORE_ICON_WIDTH = 96
DEFAULT_RESTORE_ICON_HEIGHT = 72
MIN_RESTORE_ICON_WIDTH = 48
MIN_RESTORE_ICON_HEIGHT = 36
MAX_RESTORE_ICON_WIDTH = 320
MAX_RESTORE_ICON_HEIGHT = 240


def default_window_size() -> QSize:
    return QSize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)


def load_window_size(path: Path | None = None) -> QSize:
    data = load_window_state(path)
    try:
        width = max(MIN_WINDOW_WIDTH, int(data["width"]))
        height = max(MIN_WINDOW_HEIGHT, int(data["height"]))
        return QSize(width, height)
    except (ValueError, TypeError, KeyError):
        return default_window_size()


def save_window_size(size: QSize, path: Path | None = None) -> None:
    data = load_window_state(path)
    data["width"] = max(MIN_WINDOW_WIDTH, int(size.width()))
    data["height"] = max(MIN_WINDOW_HEIGHT, int(size.height()))
    write_window_state(data, path)


def load_window_position(path: Path | None = None) -> QPoint | None:
    data = load_window_state(path)
    try:
        return QPoint(int(data["x"]), int(data["y"]))
    except (ValueError, TypeError, KeyError):
        return None


def save_window_position(position: QPoint, path: Path | None = None) -> None:
    # Note: on Wayland QWidget.pos() is unreliable (the compositor owns window
    # placement and reports geometry late), so a restored position may not match.
    data = load_window_state(path)
    data["x"] = int(position.x())
    data["y"] = int(position.y())
    write_window_state(data, path)


def load_full_window_size(path: Path | None = None) -> QSize:
    data = load_window_state(path)
    full_data = data.get("full")
    if isinstance(full_data, dict):
        try:
            return QSize(max(MIN_FULL_WINDOW_WIDTH, int(full_data["width"])), max(MIN_WINDOW_HEIGHT, int(full_data["height"])))
        except (TypeError, ValueError, KeyError):
            pass
    return QSize(FULL_WINDOW_WIDTH, FULL_WINDOW_HEIGHT)


def save_full_window_size(size: QSize, path: Path | None = None) -> None:
    data = load_window_state(path)
    data["full"] = {
        "width": max(MIN_FULL_WINDOW_WIDTH, int(size.width())),
        "height": max(MIN_WINDOW_HEIGHT, int(size.height())),
    }
    write_window_state(data, path)


def default_restore_icon_geometry(screen_rect: QRect | None = None) -> QRect:
    if screen_rect is None:
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)
    return QRect(
        screen_rect.right() - DEFAULT_RESTORE_ICON_WIDTH - 13,
        screen_rect.bottom() - DEFAULT_RESTORE_ICON_HEIGHT - 13,
        DEFAULT_RESTORE_ICON_WIDTH,
        DEFAULT_RESTORE_ICON_HEIGHT,
    )


def clamp_restore_icon_geometry(geometry: QRect, screen_rect: QRect | None = None) -> QRect:
    if screen_rect is None:
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)
    width = min(MAX_RESTORE_ICON_WIDTH, max(MIN_RESTORE_ICON_WIDTH, int(geometry.width())))
    height = min(MAX_RESTORE_ICON_HEIGHT, max(MIN_RESTORE_ICON_HEIGHT, int(geometry.height())))
    max_x = screen_rect.right() - width + 1
    max_y = screen_rect.bottom() - height + 1
    return QRect(
        min(max(int(geometry.x()), screen_rect.left()), max_x),
        min(max(int(geometry.y()), screen_rect.top()), max_y),
        width,
        height,
    )


def load_restore_icon_geometry(path: Path | None = None, screen_rect: QRect | None = None) -> QRect:
    data = load_window_state(path)
    icon_data = data.get("restore_icon")
    if not isinstance(icon_data, dict):
        return default_restore_icon_geometry(screen_rect)
    try:
        return clamp_restore_icon_geometry(
            QRect(
                int(icon_data["x"]),
                int(icon_data["y"]),
                int(icon_data["width"]),
                int(icon_data["height"]),
            ),
            screen_rect,
        )
    except (TypeError, ValueError, KeyError):
        return default_restore_icon_geometry(screen_rect)


def save_restore_icon_geometry(geometry: QRect, path: Path | None = None) -> None:
    data = load_window_state(path)
    data["restore_icon"] = {
        "x": int(geometry.x()),
        "y": int(geometry.y()),
        "width": min(MAX_RESTORE_ICON_WIDTH, max(MIN_RESTORE_ICON_WIDTH, int(geometry.width()))),
        "height": min(MAX_RESTORE_ICON_HEIGHT, max(MIN_RESTORE_ICON_HEIGHT, int(geometry.height()))),
    }
    write_window_state(data, path)
