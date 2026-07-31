# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from qt_window_test_helpers import *


def test_default_restore_icon_geometry_uses_desktop_position() -> None:
    geometry = default_restore_icon_geometry(screen_rect=QRect(0, 0, 1280, 720))

    assert geometry.size() == QSize(96, 72)
    assert geometry.topLeft() == QPoint(1170, 634)

def test_restore_icon_geometry_persists_independently_from_keyboard_size(tmp_path) -> None:
    state_path = tmp_path / "window-state.json"

    save_restore_icon_geometry(QRect(44, 55, 120, 90), state_path)

    assert load_restore_icon_geometry(state_path, screen_rect=QRect(0, 0, 1280, 720)) == QRect(44, 55, 120, 90)

def test_restore_icon_geometry_enforces_minimum_size(tmp_path) -> None:
    state_path = tmp_path / "window-state.json"
    state_path.write_text('{"restore_icon":{"x":10,"y":20,"width":1,"height":2}}', encoding="utf-8")

    geometry = load_restore_icon_geometry(state_path, screen_rect=QRect(0, 0, 1280, 720))

    assert geometry == QRect(10, 20, 48, 36)

def test_restore_icon_geometry_caps_accidental_full_keyboard_size(tmp_path) -> None:
    state_path = tmp_path / "window-state.json"
    state_path.write_text('{"restore_icon":{"x":10,"y":20,"width":960,"height":340}}', encoding="utf-8")

    geometry = load_restore_icon_geometry(state_path, screen_rect=QRect(0, 0, 1280, 720))

    assert geometry == QRect(10, 20, 320, 240)

def test_restore_icon_geometry_clamps_back_onto_screen(tmp_path) -> None:
    state_path = tmp_path / "window-state.json"
    state_path.write_text('{"restore_icon":{"x":383,"y":1261,"width":82,"height":61}}', encoding="utf-8")

    geometry = load_restore_icon_geometry(state_path, screen_rect=QRect(0, 0, 1280, 720))

    assert geometry == QRect(383, 659, 82, 61)

def test_restore_icon_clamp_handles_left_and_top_edges() -> None:
    geometry = clamp_restore_icon_geometry(QRect(-40, -20, 82, 61), screen_rect=QRect(0, 0, 1280, 720))

    assert geometry == QRect(0, 0, 82, 61)
