# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from qt_window_test_helpers import *

from keystone_osk import visual

def test_first_launch_without_saved_theme_uses_dark_when_desktop_is_dark(app, monkeypatch) -> None:
    monkeypatch.setattr(keyboard_app, "detect_color_scheme", lambda *a, **k: "dark")

    window = KeyboardWindow(persist_window_state=False)

    assert window._theme_name == "dark"


def test_first_launch_without_saved_theme_uses_light_when_desktop_is_light(app, monkeypatch) -> None:
    monkeypatch.setattr(keyboard_app, "detect_color_scheme", lambda *a, **k: "light")

    window = KeyboardWindow(persist_window_state=False)

    assert window._theme_name == "light"


def test_saved_theme_takes_precedence_over_desktop_detection(app, monkeypatch) -> None:
    monkeypatch.setattr(keyboard_app, "persisted_keyboard_theme", lambda *a, **k: "mocha")
    monkeypatch.setattr(keyboard_app, "detect_color_scheme", lambda *a, **k: "dark")

    window = KeyboardWindow(persist_window_state=True)

    assert window._theme_name == "mocha"


def test_explicit_theme_overrides_desktop_detection(app, monkeypatch) -> None:
    monkeypatch.setattr(keyboard_app, "detect_color_scheme", lambda *a, **k: "dark")

    window = KeyboardWindow(persist_window_state=False, theme="dusk")

    assert window._theme_name == "dusk"


def test_full_keyboard_menu_action_toggles_back_to_compact(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    window._mode_action.trigger()

    assert window._keyboard_mode == "full"
    assert window._mode_action.text() == "Compact Keyboard"
    assert window.size() == QSize(960, 240)

    window._mode_action.trigger()

    assert window._keyboard_mode == "compact"
    assert window._mode_action.text() == "Full Keyboard"

    window.close()

def test_switching_to_full_keyboard_clamps_current_position_on_screen(app, monkeypatch) -> None:
    # Pin the screen so this holds on any monitor. Without it the test only
    # passes where the screen happens to be 1280 wide, and it silently stops
    # exercising the clamp on a screen narrower than the full layout.
    screen_rect = QRect(0, 0, 1280, 720)
    margin = 14

    class _FixedScreen:
        def availableGeometry(self) -> QRect:
            return screen_rect

    monkeypatch.setattr(visual, "QApplication", type("_App", (), {"primaryScreen": staticmethod(_FixedScreen)}))

    window = KeyboardWindow(startup_size=QSize(520, 220), persist_window_state=False)
    # Near enough to the right edge that the wider full layout must be clamped.
    window.move(screen_rect.right() - 500, screen_rect.top() + margin)

    window._mode_action.trigger()

    assert window._keyboard_mode == "full"
    assert window.geometry().right() <= screen_rect.right() - margin

    window.close()
