# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from qt_window_test_helpers import *

def test_outside_click_clears_one_shot_modifiers_and_caps(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window.setGeometry(100, 100, 620, 260)
    window._locked_key_labels = {"Caps", "Ctrl", "Alt"}

    window._handle_global_modifier_cancel(QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)

    assert window._locked_key_labels == set()

def test_inside_click_does_not_cancel_one_shot_modifiers(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window.setGeometry(100, 100, 620, 260)
    window._locked_key_labels = {"Ctrl"}

    window._handle_global_modifier_cancel(window.frameGeometry().center(), Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)

    assert window._locked_key_labels == {"Ctrl"}

def test_held_click_does_not_retrigger_one_shot_cancel(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window.setGeometry(100, 100, 620, 260)
    window._locked_key_labels = {"Ctrl"}

    window._handle_global_modifier_cancel(QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)

    assert window._locked_key_labels == {"Ctrl"}

def test_outside_overlay_click_hides_open_app_menu(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window._app_menu.show()
    window._theme_menu.show()

    assert window._app_menu.isVisible()
    assert window._theme_menu.isVisible()

    window._handle_outside_overlay_click()

    assert not window._app_menu.isVisible()
    assert not window._theme_menu.isVisible()

def test_outside_overlay_click_hides_menu_and_clears_one_shot_modifiers(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window._locked_key_labels = {"Caps", "Ctrl"}
    window._app_menu.show()

    window._handle_outside_overlay_click()

    assert not window._app_menu.isVisible()
    assert window._locked_key_labels == set()

def test_show_app_menu_does_not_cover_menu_with_desktop_overlay(app, monkeypatch) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window._menu_rect = QRectF(10, 10, 80, 30)
    calls = {"hide": 0}
    monkeypatch.setattr(window._modifier_cancel_overlay, "hide", lambda: calls.__setitem__("hide", calls["hide"] + 1))
    monkeypatch.setattr(window._app_menu, "popup", lambda point: None)
    window.show()

    window._show_app_menu()
    app.processEvents()

    assert calls["hide"] == 1

    window._app_menu.hide()
    window._modifier_cancel_overlay.hide()
    window.close()

def test_open_app_menu_shows_cancel_overlay_around_menu_and_theme_submenu(app, monkeypatch) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window._app_menu.show()
    captured = []
    monkeypatch.setattr(window._modifier_cancel_overlay, "show_around_rect", lambda rect: captured.append(rect))
    monkeypatch.setattr(window, "raise_", lambda: None)
    monkeypatch.setattr(window._app_menu, "raise_", lambda: None)

    window._show_menu_cancel_overlay()

    assert captured
    assert captured[0].width() >= window._app_menu.sizeHint().width() + window._theme_menu.sizeHint().width()

    window._app_menu.hide()
    window._modifier_cancel_overlay.hide()
    window.close()

def test_one_shot_modifier_shows_cancel_overlay_after_leaving_keyboard(app, monkeypatch) -> None:
    # GNOME path: leaving the keyboard with a latched modifier deploys the
    # full-screen cancel overlay so an outside click cancels it.
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    monkeypatch.delenv("KDE_FULL_SESSION", raising=False)
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    window.show()
    window._queue_key_press(key("Ctrl"))

    overlay_windows = [window._modifier_cancel_overlay, *window._modifier_cancel_overlay._segments]
    assert all(not overlay.isVisible() for overlay in overlay_windows)

    window.leaveEvent(None)

    assert any(overlay.isVisible() for overlay in overlay_windows)
    for overlay in overlay_windows:
        if overlay.isVisible():
            assert not overlay.geometry().intersects(window.frameGeometry())

    window._clear_one_shot_modifiers()

    assert not window._modifier_cancel_overlay.isVisible()
    assert all(not overlay.isVisible() for overlay in window._modifier_cancel_overlay._segments)
    window.close()

def test_kde_session_never_shows_cancel_overlay_on_leave(app, monkeypatch) -> None:
    # KDE path: aggressive compositor blur (e.g. better-blur-dx) force-blurs the
    # transparent full-screen overlay, so KDE suppresses it entirely and relies
    # on in-keyboard dismissal. The latched modifier stays pending (it is only
    # consumed/toggled by normal key taps), and no overlay window is ever shown.
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    monkeypatch.setenv("KDE_FULL_SESSION", "true")
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    window.show()
    window._queue_key_press(key("Ctrl"))

    overlay_windows = [window._modifier_cancel_overlay, *window._modifier_cancel_overlay._segments]
    assert all(not overlay.isVisible() for overlay in overlay_windows)

    window.leaveEvent(None)

    assert all(not overlay.isVisible() for overlay in overlay_windows)
    assert window._has_cancelable_modifiers()
    window.close()

def test_kde_background_click_releases_caps_and_one_shot(app, monkeypatch) -> None:
    # KDE has no cancel overlay, so a click on a non-key area of the keyboard
    # (titlebar text / empty gaps) is the modifier-cancel gesture and must
    # release Caps as well as one-shot modifiers.
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    monkeypatch.setenv("KDE_FULL_SESSION", "true")
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window._locked_key_labels = {"Caps", "Shift", "Ctrl"}

    window._clear_modifiers_on_background_click()

    assert window._locked_key_labels == set()
    window.close()

def test_gnome_background_click_keeps_caps_clears_one_shot(app, monkeypatch) -> None:
    # GNOME keeps Caps on a non-key click (Caps is cancelled via the outside
    # cancel overlay); only one-shot modifiers clear. Unchanged behavior.
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    monkeypatch.delenv("KDE_FULL_SESSION", raising=False)
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window._locked_key_labels = {"Caps", "Shift", "Ctrl"}

    window._clear_modifiers_on_background_click()

    assert window._locked_key_labels == {"Caps"}
    window.close()

def test_cancel_overlay_shows_on_gnome_and_noops_on_kde(app) -> None:
    from keystone_osk.widgets import ModifierCancelOverlay

    rect = QRect(120, 120, 240, 90)

    gnome_overlay = ModifierCancelOverlay(lambda: None, is_kde=False)
    gnome_overlay.show_around_rect(rect)
    gnome_windows = [gnome_overlay, *gnome_overlay._segments]
    assert any(w.isVisible() for w in gnome_windows)
    gnome_overlay.hide()

    kde_overlay = ModifierCancelOverlay(lambda: None, is_kde=True)
    kde_windows = [kde_overlay, *kde_overlay._segments]
    kde_overlay.show_around_rect(rect)
    assert all(not w.isVisible() for w in kde_windows)
    kde_overlay.show_for_desktop()
    assert all(not w.isVisible() for w in kde_windows)
    kde_overlay.hide()

def test_leaving_keyboard_does_not_clear_one_shot_modifier_or_caps(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window._locked_key_labels = {"Caps", "Shift"}

    window.leaveEvent(None)

    assert window._locked_key_labels == {"Caps", "Shift"}

def test_post_press_cleanup_clears_stale_hover_after_modal_interrupt(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window._pressed_key_id = "delete"
    window._hovered_key_id = "delete"

    window._clear_pressed_key()

    assert window._pressed_key_id is None
    assert window._hovered_key_id is None

def test_restore_icon_context_menu_is_compact_and_borderless(app) -> None:
    icon = DesktopRestoreIcon(lambda: None, persist_geometry=False)

    menu_style = icon._context_menu.styleSheet()
    assert "border: 0" in menu_style
    assert "padding: 2px" in menu_style
    assert "padding: 4px 14px" in menu_style

def test_restore_icon_context_menu_anchors_above_and_right(app, monkeypatch) -> None:
    icon = DesktopRestoreIcon(lambda: None, persist_geometry=False)
    icon.setGeometry(100, 100, 96, 72)

    class Screen:
        def availableGeometry(self) -> QRect:
            return QRect(0, 0, 2000, 2000)

    monkeypatch.setattr(icon, "screen", lambda: Screen())

    click_pos = icon.mapToGlobal(QPoint(48, 36))
    local_anchor = icon.mapFromGlobal(icon._context_menu_anchor(QSize(84, 34), click_pos))

    assert local_anchor.x() == 56
    assert local_anchor.y() == -6

def test_top_restore_fallback_hides_when_tray_available() -> None:
    calls: list[str] = []

    class Panel:
        def hide(self) -> None:
            calls.append("hide")

        def move_to_top_bar(self) -> None:
            calls.append("move")

        def show(self) -> None:
            calls.append("show")

        def raise_(self) -> None:
            calls.append("raise")

    show_top_restore_fallback_if_needed(Panel(), tray_available=True)
    assert calls == ["hide"]

    calls.clear()
    show_top_restore_fallback_if_needed(Panel(), tray_available=False)
    assert calls == ["move", "show", "raise"]

def test_desktop_restore_icon_can_be_resized(app) -> None:
    icon = DesktopRestoreIcon(lambda: None, persist_geometry=False)
    icon.setGeometry(100, 100, 96, 72)

    icon._begin_manual_resize(Qt.Edge.RightEdge | Qt.Edge.BottomEdge, QPoint(196, 172))
    icon._apply_manual_resize(QPoint(226, 202))

    assert icon.geometry() == QRect(100, 100, 126, 102)

def test_desktop_restore_icon_resize_hits_visible_body_corner(app) -> None:
    icon = DesktopRestoreIcon(lambda: None, persist_geometry=False)
    icon.setGeometry(100, 100, 96, 72)
    body = icon._body_rect()

    assert icon._resize_edges_at(body.right() - 2, body.bottom() - 2) == Qt.Edge.RightEdge | Qt.Edge.BottomEdge
    assert icon._resize_edges_at(body.left() + 2, body.top() + 2) == Qt.Edge.LeftEdge | Qt.Edge.TopEdge
    assert icon._resize_edges_at(icon.width() - 2, icon.height() - 2) == Qt.Edge.RightEdge | Qt.Edge.BottomEdge
    assert icon._resize_edges_at(2, 2) == Qt.Edge.LeftEdge | Qt.Edge.TopEdge
    assert icon._resize_edges_at(body.center().x(), body.center().y()) is None

def test_desktop_restore_icon_resize_hits_small_visible_body_corner(app) -> None:
    icon = DesktopRestoreIcon(lambda: None, persist_geometry=False)
    icon.setGeometry(100, 100, 48, 36)
    body = icon._body_rect()

    assert icon._resize_edges_at(body.right() - 1, body.bottom() - 1) == Qt.Edge.RightEdge | Qt.Edge.BottomEdge
    assert icon._resize_edges_at(icon.width() - 1, icon.height() - 1) == Qt.Edge.RightEdge | Qt.Edge.BottomEdge
    assert icon._resize_edges_at(body.center().x(), body.center().y()) is None

def test_desktop_restore_icon_paint_event_uses_current_scale(app) -> None:
    icon = DesktopRestoreIcon(lambda: None, persist_geometry=False, theme="light")
    icon.setGeometry(100, 100, 96, 72)

    icon.paintEvent(QPaintEvent(icon.rect()))

def test_desktop_restore_icon_clears_transparent_margins(app) -> None:
    icon = DesktopRestoreIcon(lambda: None, persist_geometry=False, theme="dark")
    icon.resize(96, 72)
    icon.clearMask()
    image = QImage(icon.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(255, 0, 255, 255))

    painter = QPainter(image)
    icon._paint_restore_icon(painter)
    painter.end()

    assert image.pixelColor(1, 1).alpha() == 0
    assert image.pixelColor(icon.width() - 1, icon.height() - 1).alpha() == 0
    assert image.pixelColor(int(icon._body_rect().center().x()), int(icon._body_rect().center().y())).alpha() > 0

def test_desktop_restore_icon_masks_window_to_visible_body(app) -> None:
    icon = DesktopRestoreIcon(lambda: None, persist_geometry=False, theme="dark")
    icon.resize(96, 72)
    icon._apply_shape_mask()
    body = icon._body_rect().toAlignedRect()
    mask = icon.mask()

    assert not mask.isEmpty()
    assert mask.boundingRect() == body
    assert not mask.contains(QPoint(1, 1))
    assert mask.contains(body.center())

def test_desktop_restore_icon_body_is_opaque_to_avoid_kde_blur(app) -> None:
    icon = DesktopRestoreIcon(lambda: None, persist_geometry=False, theme="dark")
    icon.resize(96, 72)
    image = QImage(icon.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    icon._paint_restore_icon(painter)
    painter.end()

    body = icon._body_rect().toAlignedRect()
    sample = QPoint(body.left() + 6, body.top() + 6)
    assert image.pixelColor(sample).alpha() == 255

def test_desktop_restore_icon_close_menu_action_hides_icon_only(app) -> None:
    close_called = False

    def record_close() -> None:
        nonlocal close_called
        close_called = True

    icon = DesktopRestoreIcon(lambda: None, close_callback=record_close, persist_geometry=False)

    assert [action.text() for action in icon._context_menu.actions()] == ["Close"]

    icon._context_menu.actions()[0].trigger()

    assert close_called

def test_desktop_restore_icon_close_menu_keeps_restore_path(app, monkeypatch) -> None:
    monkeypatch.setattr("keystone_osk.app.QSystemTrayIcon.isSystemTrayAvailable", lambda: False)
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    window.show()
    window._minimize_to_panel()
    window._desktop_icon._context_menu.actions()[0].trigger()

    assert not window.isVisible()
    assert not window._desktop_icon.isVisible()
    assert window._panel_button.isVisible()

    window._panel_button.hide()
    window.close()

def test_keyboard_corner_resize_uses_manual_path_even_on_gnome() -> None:
    assert should_use_manual_resize(Qt.Edge.RightEdge | Qt.Edge.BottomEdge, is_kde=False)

def test_keyboard_single_edge_resize_can_use_native_path_on_gnome() -> None:
    assert not should_use_manual_resize(Qt.Edge.RightEdge, is_kde=False)

def test_gnome_keyboard_resize_hits_visible_corner_with_pre_kde_margin(app, monkeypatch) -> None:
    # Asserts the GNOME resize margin (28px), so it must run as a GNOME session
    # regardless of the desktop the suite is executed on (KDE uses a 14px margin
    # and would miss the 19,19 corner).
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    monkeypatch.delenv("KDE_FULL_SESSION", raising=False)
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)

    assert window._resize_edges_at(19, 19) == Qt.Edge.LeftEdge | Qt.Edge.TopEdge

def test_gnome_keyboard_resize_does_not_overlap_close_or_minimize_controls(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window._close_rect = QRect(38, 30, 34, 42)
    window._minimize_rect = QRect(94, 30, 38, 42)

    assert window._resize_edges_at(55, 35) is None
    assert window._resize_edges_at(113, 35) is None

def test_desktop_restore_icon_can_be_resized_repeatedly(app) -> None:
    icon = DesktopRestoreIcon(lambda: None, persist_geometry=False)
    icon.setGeometry(100, 100, 96, 72)

    icon._begin_manual_resize(Qt.Edge.RightEdge | Qt.Edge.BottomEdge, QPoint(196, 172))
    icon._apply_manual_resize(QPoint(226, 202))
    icon._finish_manual_resize()
    icon._begin_manual_resize(Qt.Edge.RightEdge | Qt.Edge.BottomEdge, QPoint(226, 202))
    icon._apply_manual_resize(QPoint(246, 222))

    assert icon.geometry() == QRect(100, 100, 146, 122)

def test_desktop_restore_icon_live_resize_is_capped(app) -> None:
    icon = DesktopRestoreIcon(lambda: None, persist_geometry=False)
    icon.setGeometry(100, 100, 96, 72)

    icon._begin_manual_resize(Qt.Edge.RightEdge | Qt.Edge.BottomEdge, QPoint(196, 172))
    icon._apply_manual_resize(QPoint(596, 572))

    assert icon.geometry() == QRect(100, 100, 320, 240)

def test_minimized_keyboard_key_cluster_is_centered_in_outline() -> None:
    body = minimized_keyboard_body_rect()
    key_rects = minimized_keyboard_key_rects()
    left_gap = min(rect.left() for rect in key_rects) - body.left()
    right_gap = body.right() - max(rect.right() for rect in key_rects)

    assert abs(left_gap - right_gap) <= 0.5
