from qt_window_test_helpers import *


def test_minimize_shows_desktop_restore_icon_even_when_tray_available(app, monkeypatch) -> None:
    monkeypatch.setattr("keystone_osk.app.QSystemTrayIcon.isSystemTrayAvailable", lambda: True)
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    window.show()
    window._minimize_to_panel()

    assert not window.isVisible()
    assert window._desktop_icon.isVisible()
    assert not window._panel_button.isVisible()

    window._desktop_icon.hide()
    window.close()

def test_close_button_hides_keyboard_but_keeps_restore_path(app, monkeypatch) -> None:
    quit_called = False

    def record_quit() -> None:
        nonlocal quit_called
        quit_called = True

    monkeypatch.setattr("keystone_osk.app.QApplication.quit", record_quit)
    monkeypatch.setattr("keystone_osk.app.QSystemTrayIcon.isSystemTrayAvailable", lambda: True)
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    window.show()
    window._hide_keyboard_keep_top_icon()

    assert not quit_called
    assert not window.isVisible()
    assert not window._desktop_icon.isVisible()
    assert window._tray_icon.isVisible()

    window.close()

def test_tray_activation_does_not_minimize_restored_keyboard(app, monkeypatch) -> None:
    monkeypatch.setattr("keystone_osk.app.QSystemTrayIcon.isSystemTrayAvailable", lambda: True)
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    window.show()
    window._minimize_to_panel()
    window._handle_tray_activation(window._tray_icon.ActivationReason.Trigger)
    window._handle_tray_activation(window._tray_icon.ActivationReason.Trigger)

    assert window.isVisible()
    assert not window._desktop_icon.isVisible()
    window.close()

def test_control_methods_show_hide_and_toggle_keyboard(app, monkeypatch) -> None:
    monkeypatch.setattr("keystone_osk.app.QSystemTrayIcon.isSystemTrayAvailable", lambda: True)
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    window.show()
    window.hide_keyboard()

    assert not window.isVisible()
    assert not window._desktop_icon.isVisible()

    window.show_keyboard()

    assert window.isVisible()
    assert not window._desktop_icon.isVisible()

    window.toggle_keyboard_visibility()

    assert not window.isVisible()
    assert not window._desktop_icon.isVisible()

    window._desktop_icon.hide()
    window.close()
