"""Qt offscreen tests for the Load on startup menu action and --start-hidden."""

from qt_window_test_helpers import *

import keystone_osk.autostart as autostart_module
import keystone_osk.menu_ui as menu_ui_module


# ---------------------------------------------------------------------------
# Menu action — checked state
# ---------------------------------------------------------------------------


def test_autostart_action_exists_in_app_menu(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    try:
        texts = [a.text() for a in window._app_menu.actions()]
        assert "Load on startup" in texts
    finally:
        window.close()


def test_autostart_action_is_checkable(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    try:
        assert window._autostart_action.isCheckable()
    finally:
        window.close()


def test_autostart_action_checked_when_enabled(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    autostart_module.enable({"XDG_CONFIG_HOME": str(tmp_path / "config")})

    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    try:
        window._refresh_autostart_action()
        assert window._autostart_action.isChecked()
    finally:
        window.close()


def test_autostart_action_unchecked_when_disabled(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    # Ensure file does not exist.
    autostart_module.disable({"XDG_CONFIG_HOME": str(tmp_path / "config")})

    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    try:
        window._refresh_autostart_action()
        assert not window._autostart_action.isChecked()
    finally:
        window.close()


def test_autostart_action_refreshed_on_about_to_show(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    autostart_module.disable({"XDG_CONFIG_HOME": str(tmp_path / "config")})

    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    try:
        assert not window._autostart_action.isChecked()
        # Simulate the file appearing externally.
        autostart_module.enable({"XDG_CONFIG_HOME": str(tmp_path / "config")})
        window._app_menu.aboutToShow.emit()
        assert window._autostart_action.isChecked()
    finally:
        window.close()


# ---------------------------------------------------------------------------
# Menu action — toggle invokes enable/disable
# ---------------------------------------------------------------------------


def test_toggle_autostart_calls_enable(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    autostart_module.disable({"XDG_CONFIG_HOME": str(tmp_path / "config")})

    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    try:
        window._refresh_autostart_action()
        assert not window._autostart_action.isChecked()
        window._toggle_autostart()
        assert autostart_module.is_enabled({"XDG_CONFIG_HOME": str(tmp_path / "config")})
    finally:
        window.close()


def test_toggle_autostart_calls_disable(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    autostart_module.enable({"XDG_CONFIG_HOME": str(tmp_path / "config")})

    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    try:
        window._refresh_autostart_action()
        assert window._autostart_action.isChecked()
        window._toggle_autostart()
        assert not autostart_module.is_enabled({"XDG_CONFIG_HOME": str(tmp_path / "config")})
    finally:
        window.close()


def test_toggle_autostart_failure_reverts_checkbox(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    autostart_module.disable({"XDG_CONFIG_HOME": str(tmp_path / "config")})

    def raise_oserror(environ):
        raise OSError("permission denied")

    monkeypatch.setattr(autostart_module, "enable", raise_oserror)

    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    try:
        window._refresh_autostart_action()
        assert not window._autostart_action.isChecked()
        window._toggle_autostart()
        # Checkbox must be reverted to its original state (unchecked = disabled).
        assert not window._autostart_action.isChecked()
    finally:
        window.close()


def test_toggle_autostart_failure_does_not_crash(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    autostart_module.enable({"XDG_CONFIG_HOME": str(tmp_path / "config")})

    def raise_oserror(environ):
        raise OSError("read-only filesystem")

    monkeypatch.setattr(autostart_module, "disable", raise_oserror)

    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    try:
        window._refresh_autostart_action()
        assert window._autostart_action.isChecked()
        # Must not raise.
        window._toggle_autostart()
        # Checkbox reverted to enabled state.
        assert window._autostart_action.isChecked()
    finally:
        window.close()


# ---------------------------------------------------------------------------
# --start-hidden: window must not be visible
# ---------------------------------------------------------------------------


def test_start_hidden_window_is_not_visible(app, monkeypatch) -> None:
    monkeypatch.setattr("keystone_osk.app.QSystemTrayIcon.isSystemTrayAvailable", lambda: True)
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    try:
        # Simulate the --start-hidden path: never call show(), call
        # _hide_keyboard_keep_top_icon() instead.
        window._hide_keyboard_keep_top_icon()
        assert not window.isVisible()
    finally:
        window.close()


def test_start_hidden_tray_icon_still_available(app, monkeypatch) -> None:
    monkeypatch.setattr("keystone_osk.app.QSystemTrayIcon.isSystemTrayAvailable", lambda: True)
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    try:
        window._hide_keyboard_keep_top_icon()
        # Tray icon is created in constructor and is visible when tray is available.
        assert window._tray_icon.isVisible()
    finally:
        window.close()
