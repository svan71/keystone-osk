from qt_window_test_helpers import *
from PySide6.QtWidgets import QLabel, QPushButton


def test_visible_keyboard_menu_contains_core_actions(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, theme="dracula")

    assert [action.text() for action in window._app_menu.actions() if not action.isSeparator()] == [
        "Full Keyboard",
        "Themes (Dracula)",
        "Turn Suggestions Off",
        "Learning: On",
        "Auto-Cap: On",
        "Load on startup",
        "Emojis",
        "Clear Learned Words",
        "Minimize",
        "Close",
        "Quit",
        "Support Keystone ☕",
        "About Keystone…",
    ]
    assert [action.text() for action in window._theme_menu.actions()] == ["Dark", "✓ Dracula", "Dusk", "Light", "Midnight", "Mocha"]
    assert window._theme_actions["dracula"].isChecked()

    window.close()

def test_theme_actions_live_in_themes_submenu(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    assert window._app_menu.actions()[1].menu() is window._theme_menu
    assert all(action in window._theme_menu.actions() for action in window._theme_actions.values())

    window.close()

def test_titlebar_places_close_minimize_switcher_on_left_and_menu_on_right(app) -> None:
    window = KeyboardWindow(startup_size=QSize(1120, 300), persist_window_state=False)
    pixmap = keyboard_app.QPixmap(window.size())
    painter = QPainter(pixmap)
    panel = keyboard_panel_rect(window.width(), window.height(), is_kde=False)

    window._draw_titlebar(painter, panel, min(window.width() / 1120, window.height() / 470))
    painter.end()

    assert window._close_rect.left() < window._minimize_rect.left()
    assert window._minimize_rect.right() < window._mode_toggle_rect.left()
    assert window._mode_toggle_rect.right() < window._menu_rect.left()
    assert window._menu_rect.right() > panel.right() - 20
    assert window._close_rect.width() == pytest.approx(window._mode_toggle_rect.width(), abs=2)
    assert window._close_rect.height() == pytest.approx(window._minimize_rect.height(), abs=1)
    assert window._minimize_rect.width() == pytest.approx(window._mode_toggle_rect.width(), abs=4)
    assert window._mode_toggle_rect.width() <= 36
    assert window._mode_toggle_rect.height() > 14

    window.close()

def test_compact_titlebar_uses_keystone_title(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    pixmap = keyboard_app.QPixmap(window.size())
    painter = QPainter(pixmap)
    panel = keyboard_panel_rect(window.width(), window.height(), is_kde=False)

    window._draw_titlebar(painter, panel, min(window.width() / 1120, window.height() / 470))
    painter.end()

    assert KEYBOARD_TITLE == "Keystone"
    assert not window._title_rect.isNull()

    window.close()

def test_full_titlebar_uses_keystone_title(app) -> None:
    window = KeyboardWindow(startup_size=QSize(FULL_WINDOW_WIDTH, FULL_WINDOW_HEIGHT), persist_window_state=False)
    window._toggle_keyboard_mode()
    pixmap = keyboard_app.QPixmap(window.size())
    painter = QPainter(pixmap)
    panel = keyboard_panel_rect(window.width(), window.height(), is_kde=False)

    window._draw_titlebar(painter, panel, min(window.width() / 1120, window.height() / 470))
    painter.end()

    assert KEYBOARD_TITLE == "Keystone"
    assert not window._title_rect.isNull()

    window.close()

def test_titlebar_hides_keystone_title_when_suggestions_show(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window._suggestions = ("server",)
    pixmap = keyboard_app.QPixmap(window.size())
    painter = QPainter(pixmap)
    panel = keyboard_panel_rect(window.width(), window.height(), is_kde=False)

    window._draw_titlebar(painter, panel, min(window.width() / 1120, window.height() / 470))
    painter.end()

    assert window._title_rect.isNull()

    window.close()

def test_titlebar_control_icons_are_small() -> None:
    assert control_font_size(0.6) <= 18

def test_full_titlebar_menu_sits_in_from_right_edge(app) -> None:
    window = KeyboardWindow(startup_size=QSize(FULL_WINDOW_WIDTH, FULL_WINDOW_HEIGHT), persist_window_state=False)
    window._toggle_keyboard_mode()
    pixmap = keyboard_app.QPixmap(window.size())
    painter = QPainter(pixmap)
    panel = keyboard_panel_rect(window.width(), window.height(), is_kde=False)

    window._draw_titlebar(painter, panel, min(window.width() / 1120, window.height() / 470))
    painter.end()

    assert panel.right() - window._menu_rect.right() >= 18

    window.close()

def test_app_menu_anchor_centers_on_menu_button(app, monkeypatch) -> None:
    window = KeyboardWindow(startup_size=QSize(FULL_WINDOW_WIDTH, FULL_WINDOW_HEIGHT), persist_window_state=False)
    window._toggle_keyboard_mode()
    pixmap = keyboard_app.QPixmap(window.size())
    painter = QPainter(pixmap)
    panel = keyboard_panel_rect(window.width(), window.height(), is_kde=False)
    captured_anchor = None

    class Screen:
        def availableGeometry(self) -> QRect:
            return QRect(-1000, 0, 4000, 2000)

    def capture_popup(point) -> None:
        nonlocal captured_anchor
        captured_anchor = point

    window._draw_titlebar(painter, panel, min(window.width() / 1120, window.height() / 470))
    painter.end()
    monkeypatch.setattr(window, "screen", lambda: Screen())
    monkeypatch.setattr(window._app_menu, "popup", capture_popup)
    monkeypatch.setattr(window._modifier_cancel_overlay, "show_for_desktop", lambda: None)
    monkeypatch.setattr(window._app_menu, "raise_", lambda: None)

    window._show_app_menu()

    local_anchor = window.mapFromGlobal(captured_anchor)
    assert local_anchor.x() + (window._app_menu.sizeHint().width() / 2) == pytest.approx(window._menu_rect.center().x(), abs=1)
    assert local_anchor.y() == int(window._menu_rect.bottom()) + 8

    window.close()

def test_app_menu_anchor_prefers_above_keyboard_when_screen_room_allows(app, monkeypatch) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window._menu_rect = QRectF(400, 30, 80, 30)

    class Screen:
        def availableGeometry(self) -> QRect:
            return QRect(0, -1000, 2000, 2000)

    monkeypatch.setattr(window, "screen", lambda: Screen())

    local_anchor = window.mapFromGlobal(window._app_menu_anchor(QSize(200, 100)))

    assert local_anchor.x() == 340
    assert local_anchor.y() == -78

    window.close()

def test_visible_keyboard_dropdown_has_rounded_borderless_menu(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    menu_style = window._app_menu.styleSheet()
    assert "border: 0" in menu_style
    assert "border-radius: 8px" in menu_style

    window.close()

def test_tray_menu_has_thin_light_border_and_hide_action_when_visible(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    window.show()
    window._refresh_tray_menu_actions()

    assert "border: 1px solid #f8f8f2" in window._tray_menu.styleSheet()
    assert [action.text() for action in window._tray_menu.actions()] == ["Hide", "Quit"]

    window.close()

def test_mocha_theme_tray_menu_uses_mocha_stylesheet(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, theme="mocha")

    assert "background: #1e1e2e" in window._tray_menu.styleSheet()
    assert "color: #cdd6f4" in window._tray_menu.styleSheet()

    window.close()

def test_dusk_theme_tray_menu_preserves_original_mocha_stylesheet(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, theme="dusk")

    assert "background: #313244" in window._tray_menu.styleSheet()
    assert "color: #cdd6f4" in window._tray_menu.styleSheet()

    window.close()

def test_tray_context_menu_is_attached_for_desktop_right_click(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, theme="light")

    assert window._tray_icon.contextMenu() is window._tray_menu

    window.close()

def test_tray_icon_uses_kde_theme_color(app) -> None:
    icon = build_tray_icon(theme="dark", is_kde=True)

    assert not icon.isNull()
    assert tray_icon_color(theme="dark", is_kde=True).name() == "#ffffff"
    assert tray_icon_keyboard_body_rect(is_kde=True) == QRectF(7, 18, 50, 28)

class _NamedThemeIcon:
    def __init__(self, n): self._n = n
    def isNull(self): return False
    def name(self): return self._n


def test_tray_icon_prefers_theme_icon_before_generated_pixmap() -> None:
    calls = []

    def fake_from_theme(name: str):
        calls.append(name)
        return _NamedThemeIcon("keystone-symbolic") if name == "keystone-symbolic" else QIcon()

    icon = build_tray_icon(theme="dark", from_theme=fake_from_theme)

    assert icon.name() == "keystone-symbolic"
    assert calls == [
        "keystone-status-dark-symbolic",
        "keystone-status-symbolic",
        "keystone-symbolic",
    ]

def test_tray_icon_uses_bundled_svg_before_generated_pixmap() -> None:
    calls = []

    def fake_from_theme(name: str) -> QIcon:
        calls.append(name)
        return QIcon()

    icon = build_tray_icon(theme="light", from_theme=fake_from_theme)

    assert not icon.isNull()
    assert calls == list(tray_icon_theme_candidates("light"))
    assert BUNDLED_TRAY_ICON_PATH.exists()

def test_tray_icon_uses_system_keyboard_after_bundled_svg_is_missing(tmp_path) -> None:
    calls = []

    def fake_from_theme(name: str):
        calls.append(name)
        return _NamedThemeIcon("input-keyboard-symbolic") if name == "input-keyboard-symbolic" else QIcon()

    icon = build_tray_icon(theme="light", is_kde=False, from_theme=fake_from_theme, bundled_path=tmp_path / "missing.svg")

    assert icon.name() == "input-keyboard-symbolic"
    assert calls == [*tray_icon_theme_candidates("light"), *tray_icon_system_fallback_candidates()]

def test_tray_icon_uses_generated_pixmap_as_emergency_fallback(tmp_path) -> None:
    calls = []

    def fake_from_theme(name: str) -> QIcon:
        calls.append(name)
        return QIcon()

    icon = build_tray_icon(theme="light", is_kde=False, from_theme=fake_from_theme, bundled_path=tmp_path / "missing.svg")

    assert not icon.isNull()
    assert calls == [*tray_icon_theme_candidates("light"), *tray_icon_system_fallback_candidates()]
    assert not build_generated_tray_icon(theme="light").isNull()

def test_tray_menu_refreshes_label_before_native_menu_opens(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    window.show()
    window._tray_primary_action.setText("Show Keystone")
    window._tray_menu.aboutToShow.emit()

    assert [action.text() for action in window._tray_menu.actions()] == ["Hide", "Quit"]

    window.close()

def test_about_dialog_contains_release_identity_and_links(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    dialog = window._build_about_dialog()
    label_text = "\n".join(label.text() for label in dialog.findChildren(QLabel))
    button_text = [button.text() for button in dialog.findChildren(QPushButton)]

    assert dialog.windowTitle() == "About Keystone"
    assert "Keystone" in label_text
    assert "Version 0.1.0" in label_text
    assert "A practical on-screen keyboard for Linux desktops." in label_text
    assert "GPL-3.0-or-later" in label_text
    assert "Free and source-available. Donations help development." in label_text
    assert button_text == ["Support Keystone", "Source Code", "License", "Close"]

    dialog.close()
    window.close()

def test_about_dialog_buttons_open_expected_urls(app, monkeypatch) -> None:
    from PySide6.QtGui import QDesktopServices

    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url.toString()) or True)

    dialog = window._build_about_dialog()
    buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}
    buttons["Support Keystone"].click()
    buttons["Source Code"].click()
    buttons["License"].click()

    assert opened == [
        "https://ko-fi.com/keystoneosk",
        "https://github.com/svan71/keystone-osk",
        "https://www.gnu.org/licenses/gpl-3.0.html",
    ]

    dialog.close()
    window.close()
