# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from qt_window_test_helpers import *
from keystone_osk.theme import THEMES, ResolvedTheme


def _fake_resolved(opacity):
    return ResolvedTheme(id="dracula", source="builtin", palette=THEMES["dracula"], opacity=opacity)


_OPACITY_TOL = 1 / 255  # Qt quantises opacity to 8-bit; allow one step of rounding


def test_window_applies_theme_opacity_on_startup(app, monkeypatch) -> None:
    import keystone_osk.app as keyboard_app
    monkeypatch.setattr(keyboard_app, "resolve_theme", lambda theme=None: _fake_resolved(0.8))
    window = keyboard_app.KeyboardWindow(persist_window_state=False, theme="dracula")
    try:
        assert abs(window.windowOpacity() - 0.8) < _OPACITY_TOL
    finally:
        window.close()


def test_theme_change_updates_window_opacity(app, monkeypatch) -> None:
    import keystone_osk.app as keyboard_app
    window = keyboard_app.KeyboardWindow(persist_window_state=False, theme="dracula")
    try:
        monkeypatch.setattr(keyboard_app, "resolve_theme", lambda theme=None: _fake_resolved(0.7))
        window._set_keyboard_theme("mocha")
        assert abs(window.windowOpacity() - 0.7) < _OPACITY_TOL
    finally:
        window.close()


def test_window_defaults_to_full_opacity(app) -> None:
    import keystone_osk.app as keyboard_app
    window = keyboard_app.KeyboardWindow(persist_window_state=False, theme="dracula")
    try:
        assert abs(window.windowOpacity() - 1.0) < _OPACITY_TOL
    finally:
        window.close()
