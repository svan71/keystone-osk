# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from qt_window_test_helpers import *

import json

from keystone_osk.state import (
    readable_window_state_path,
    save_keyboard_mode,
    window_state_path as current_window_state_path,
)

def test_keyboard_theme_defaults_to_dark(tmp_path) -> None:
    assert load_keyboard_theme(tmp_path / "missing-window-state.json") == "dracula"


def test_persisted_keyboard_theme_is_none_when_unset(tmp_path) -> None:
    from keystone_osk.state_io import persisted_keyboard_theme

    assert persisted_keyboard_theme(tmp_path / "missing-window-state.json") is None


def test_persisted_keyboard_theme_returns_saved_value(tmp_path) -> None:
    from keystone_osk.state_io import persisted_keyboard_theme

    path = tmp_path / "window-state.json"
    path.write_text('{"theme":"mocha"}', encoding="utf-8")
    assert persisted_keyboard_theme(path) == "mocha"

def test_xdg_window_state_path_wins_over_legacy_config_path(tmp_path, monkeypatch) -> None:
    config_home = tmp_path / "config"
    state_home = tmp_path / "state"
    legacy_path = config_home / "keystone-osk" / "window-state.json"
    current_path = state_home / "keystone-osk" / "window-state.json"
    legacy_path.parent.mkdir(parents=True)
    current_path.parent.mkdir(parents=True)
    legacy_path.write_text('{"theme":"light"}', encoding="utf-8")
    current_path.write_text('{"theme":"dark"}', encoding="utf-8")
    monkeypatch.delenv("KEYSTONE_OSK_STATE_FILE", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_home))

    assert current_window_state_path() == current_path
    assert readable_window_state_path() == current_path
    assert load_keyboard_theme() == "dark"

def test_window_state_reads_legacy_config_path_when_xdg_state_is_missing(tmp_path, monkeypatch) -> None:
    config_home = tmp_path / "config"
    state_home = tmp_path / "state"
    legacy_path = config_home / "keystone-osk" / "window-state.json"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text('{"theme":"light"}', encoding="utf-8")
    monkeypatch.delenv("KEYSTONE_OSK_STATE_FILE", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_home))

    assert readable_window_state_path() == legacy_path
    assert load_keyboard_theme() == "light"

def test_window_state_write_migrates_legacy_data_to_xdg_state_path(tmp_path, monkeypatch) -> None:
    config_home = tmp_path / "config"
    state_home = tmp_path / "state"
    legacy_path = config_home / "keystone-osk" / "window-state.json"
    current_path = state_home / "keystone-osk" / "window-state.json"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text('{"theme":"light"}', encoding="utf-8")
    monkeypatch.delenv("KEYSTONE_OSK_STATE_FILE", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_home))

    save_keyboard_mode("full")

    assert legacy_path.exists()
    assert json.loads(legacy_path.read_text(encoding="utf-8")) == {"theme": "light"}
    assert json.loads(current_path.read_text(encoding="utf-8")) == {"theme": "light", "mode": "full"}

def test_full_keyboard_remembers_its_own_size(app, tmp_path, monkeypatch) -> None:
    state_path = tmp_path / "window-state.json"
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(state_path))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=True)

    window._toggle_keyboard_mode()
    window.resize(1040, 280)
    window._toggle_keyboard_mode()
    window.resize(620, 260)
    window._toggle_keyboard_mode()

    assert window.size() == QSize(1040, 280)
    assert load_full_window_size(state_path) == QSize(1040, 280)

    window.close()

def test_restart_restores_last_used_full_keyboard_mode(app, tmp_path, monkeypatch) -> None:
    state_path = tmp_path / "window-state.json"
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(state_path))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=True)

    window._toggle_keyboard_mode()
    window.resize(1040, 280)
    window._save_window_state()
    window.close()
    restarted = KeyboardWindow(persist_window_state=True)

    assert load_keyboard_mode(state_path) == "full"
    assert restarted._keyboard_mode == "full"
    assert restarted.size() == QSize(1040, 280)

    restarted.close()

def test_restart_restores_last_used_compact_keyboard_mode(app, tmp_path, monkeypatch) -> None:
    state_path = tmp_path / "window-state.json"
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(state_path))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=True)

    window.resize(640, 270)
    window._save_window_state()
    window.close()
    restarted = KeyboardWindow(persist_window_state=True)

    assert load_keyboard_mode(state_path) == "compact"
    assert restarted._keyboard_mode == "compact"
    assert restarted.size() == QSize(640, 270)

    restarted.close()

def test_save_window_state_persists_main_window_position(app, tmp_path, monkeypatch) -> None:
    state_path = tmp_path / "window-state.json"
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(state_path))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=True)

    window.move(123, 91)
    window._save_window_state()

    assert load_window_position(state_path) == QPoint(123, 91)

    window.close()

def test_mouse_release_after_drag_saves_main_window_state(app, tmp_path, monkeypatch) -> None:
    state_path = tmp_path / "window-state.json"
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(state_path))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=True)

    window._drag_offset = QPoint(4, 5)
    window.move(222, 111)
    window.mouseReleaseEvent(type("MouseReleaseEvent", (), {})())

    assert load_window_position(state_path) == QPoint(222, 111)

    window.close()

def test_mouse_release_after_resize_saves_main_window_state(app, tmp_path, monkeypatch) -> None:
    state_path = tmp_path / "window-state.json"
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(state_path))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=True)

    window._active_resize_edges = Qt.Edge.RightEdge | Qt.Edge.BottomEdge
    window.resize(710, 300)
    window.move(123, 91)
    window.mouseReleaseEvent(type("MouseReleaseEvent", (), {})())

    assert load_window_position(state_path) == QPoint(123, 91)
    assert load_window_size(state_path) == QSize(710, 300)

    window.close()

def test_mouse_release_after_key_press_does_not_save_main_window_state(app, tmp_path, monkeypatch) -> None:
    state_path = tmp_path / "window-state.json"
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(state_path))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=True)

    window._pressed_key_id = "row0-a"
    window.mouseReleaseEvent(type("MouseReleaseEvent", (), {})())

    assert load_window_position(state_path) is None

    window.close()

def test_fit_and_position_window_uses_saved_position_when_requested(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(tmp_path / "window-state.json"))
    save_window_position(QPoint(44, 55))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    fit_and_position_window(window, restore_saved_position=True)

    assert window.pos() == QPoint(44, 55)

    window.close()

def test_fit_and_position_window_clamps_saved_position(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(tmp_path / "window-state.json"))
    save_window_position(QPoint(-999, -999))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    fit_and_position_window(window, restore_saved_position=True)

    assert window.pos().x() >= 14
    assert window.pos().y() >= 14

    window.close()

def test_fit_and_position_window_ignores_saved_position_when_not_requested(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(tmp_path / "window-state.json"))
    save_window_position(QPoint(44, 55))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    fit_and_position_window(window, restore_saved_position=False)

    assert window.pos() != QPoint(44, 55)

    window.close()

def test_close_button_persists_current_full_keyboard_size(app, tmp_path, monkeypatch) -> None:
    state_path = tmp_path / "window-state.json"
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(state_path))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=True)

    window._toggle_keyboard_mode()
    window.resize(1120, 300)
    window._hide_keyboard_keep_top_icon()
    restarted = KeyboardWindow(persist_window_state=True)

    assert load_keyboard_mode(state_path) == "full"
    assert restarted._keyboard_mode == "full"
    assert restarted.size() == QSize(1120, 300)

    restarted.close()
    window.close()

def test_default_numpad_output_mode_is_reliable(tmp_path) -> None:
    import keystone_osk.state as state_module
    assert state_module.load_numpad_output_mode(tmp_path / "s.json") == "reliable"


def test_config_accepts_true_keypad_mode(tmp_path) -> None:
    import keystone_osk.state as state_module
    p = tmp_path / "s.json"
    state_module.save_numpad_output_mode("true-keypad", p)
    assert state_module.load_numpad_output_mode(p) == "true-keypad"


def test_invalid_numpad_output_mode_falls_back_to_reliable(tmp_path) -> None:
    import keystone_osk.state as state_module
    p = tmp_path / "s.json"
    state_module.save_numpad_output_mode("octal", p)  # invalid → stored as reliable
    assert state_module.load_numpad_output_mode(p) == "reliable"


def test_close_button_persists_current_compact_keyboard_size(app, tmp_path, monkeypatch) -> None:
    state_path = tmp_path / "window-state.json"
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(state_path))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=True)

    window.resize(700, 290)
    window._hide_keyboard_keep_top_icon()
    restarted = KeyboardWindow(persist_window_state=True)

    assert load_keyboard_mode(state_path) == "compact"
    assert restarted._keyboard_mode == "compact"
    assert restarted.size() == QSize(700, 290)

    restarted.close()
    window.close()


def test_save_keyboard_theme_preserves_discovered_user_pack(tmp_path, monkeypatch) -> None:
    import keystone_osk.state as state_module
    import keystone_osk.state_io as state_io_module
    state_path = tmp_path / "window-state.json"
    # save_keyboard_theme/load_keyboard_theme both resolve through state_io now
    # and gate on VALID discovery, so patch discover_valid_theme_ids there
    # (state.py re-exports the same callables).
    monkeypatch.setattr(state_io_module, "discover_valid_theme_ids", lambda environ=None: state_module.BUILTIN_THEME_IDS + ("custom-kde",))
    state_module.save_keyboard_theme("custom-kde", state_path)
    assert state_module.load_keyboard_theme(state_path) == "custom-kde"


def test_save_keyboard_theme_falls_back_for_unknown(tmp_path) -> None:
    import keystone_osk.state as state_module
    state_path = tmp_path / "window-state.json"
    state_module.save_keyboard_theme("not-a-real-theme", state_path)
    assert state_module.load_keyboard_theme(state_path) == state_module.DRACULA_THEME_ID
