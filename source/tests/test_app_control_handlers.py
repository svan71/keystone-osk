# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from qt_window_test_helpers import *


class RecordingBackend:
    def __init__(self, *args, **kwargs) -> None:
        self.ensure_calls = 0

    def ensure_numlock_on(self) -> None:
        self.ensure_calls += 1

    def shutdown(self) -> None:
        pass


def test_control_show_returns_ok(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    assert window._control_show("") == "OK"
    window.close()


def test_control_status_reports_actual_qt_platform(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    try:
        status = window._control_status("")
    finally:
        window.close()

    assert status.startswith("OK status ")
    assert f"qt-platform={app.platformName()}" in status
    assert "input-backend=ydotoold/uinput" in status
    assert "geometry=" in status
    assert "620x260" in status


def test_control_mode_full_applies_and_returns_ok(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    assert window._control_mode("full") == "OK"
    assert window._keyboard_mode == "full"
    window.close()


def test_control_mode_invalid_returns_err_and_no_change(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    before = window._keyboard_mode
    assert window._control_mode("sideways") == "ERR invalid mode"
    assert window._keyboard_mode == before
    window.close()


def test_control_numpad_true_keypad_applies_and_returns_ok(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend
    assert window._control_numpad("true-keypad") == "OK"
    assert window._numpad_output_mode == "true-keypad"
    assert backend.ensure_calls == 1
    window.close()


def test_control_numpad_reliable_does_not_ensure_numlock(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend
    assert window._control_numpad("reliable") == "OK"
    assert backend.ensure_calls == 0
    window.close()


def test_control_numpad_invalid_returns_err(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    assert window._control_numpad("octal") == "ERR invalid numpad mode"
    window.close()


def test_control_theme_invalid_returns_err(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    assert window._control_theme("definitely-not-a-theme") == "ERR invalid theme"
    window.close()


def test_control_numpad_command_reliable(app) -> None:
    window = KeyboardWindow(persist_window_state=False, theme="dracula")
    try:
        assert window._control_numpad("reliable") == "OK"
    finally:
        window.close()


def test_control_numpad_command_true_keypad(app) -> None:
    window = KeyboardWindow(persist_window_state=False, theme="dracula")
    try:
        backend = RecordingBackend()
        window.backend = backend
        assert window._control_numpad("true-keypad") == "OK"
        assert window._numpad_output_mode == "true-keypad"
        assert backend.ensure_calls == 1
    finally:
        window.close()


def test_control_numpad_command_invalid(app) -> None:
    window = KeyboardWindow(persist_window_state=False, theme="dracula")
    try:
        assert window._control_numpad("xx") == "ERR invalid numpad mode"
    finally:
        window.close()


def test_control_mode_command_compact(app) -> None:
    window = KeyboardWindow(persist_window_state=False, theme="dracula")
    try:
        assert window._control_mode("compact") == "OK"
    finally:
        window.close()


def test_numpad_command_applies_and_persists_mode(app, tmp_path, monkeypatch) -> None:
    import keystone_osk.state as state_module
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(tmp_path / "state.json"))
    window = KeyboardWindow(persist_window_state=True, theme="dracula", enable_control_server=False)
    try:
        backend = RecordingBackend()
        window.backend = backend
        assert window._control_numpad("true-keypad") == "OK"
        assert state_module.load_numpad_output_mode() == "true-keypad"
        assert backend.ensure_calls == 1
    finally:
        window.close()


def test_persisted_true_keypad_ensures_numlock_on_startup(app, tmp_path, monkeypatch) -> None:
    import keystone_osk.state as state_module
    created: list[RecordingBackend] = []
    state_path = tmp_path / "state.json"
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(state_path))
    state_module.save_numpad_output_mode("true-keypad")

    class BackendFactory(RecordingBackend):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            created.append(self)

    monkeypatch.setattr(keyboard_app, "BackendWorkerQueue", BackendFactory)
    window = KeyboardWindow(persist_window_state=True, theme="dracula", enable_control_server=False)
    try:
        assert created[0].ensure_calls == 1
    finally:
        window.close()


def test_mode_command_applies_and_persists_mode(app, tmp_path, monkeypatch) -> None:
    import keystone_osk.state as state_module
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(tmp_path / "state.json"))
    window = KeyboardWindow(persist_window_state=True, theme="dracula", enable_control_server=False)
    try:
        assert window._control_mode("full") == "OK"
        assert state_module.load_keyboard_mode() == "full"
    finally:
        window.close()
