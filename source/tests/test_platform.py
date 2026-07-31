# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from qt_window_test_helpers import *

def test_color_scheme_from_portal_value_treats_default_as_light() -> None:
    from keystone_osk.platform import color_scheme_from_portal_value

    assert color_scheme_from_portal_value(1) == "dark"   # prefer-dark
    assert color_scheme_from_portal_value(2) == "light"  # prefer-light
    assert color_scheme_from_portal_value(0) == "light"  # GNOME "Default" / no preference
    assert color_scheme_from_portal_value(None) is None


def test_detect_color_scheme_uses_portal_reader() -> None:
    from keystone_osk.platform import detect_color_scheme

    assert detect_color_scheme(reader=lambda: 1) == "dark"
    assert detect_color_scheme(reader=lambda: 0) == "light"
    assert detect_color_scheme(reader=lambda: None) is None


def test_gnome_uses_managed_tool_window_flags() -> None:
    flags = keyboard_window_flags(is_kde=False)

    assert flags & Qt.WindowType.WindowType_Mask == Qt.WindowType.Tool
    assert not flags & Qt.WindowType.BypassWindowManagerHint

def test_kde_keyboard_uses_tool_window_flags_to_avoid_popup_mouse_grab() -> None:
    flags = keyboard_window_flags(is_kde=True)

    assert flags & Qt.WindowType.WindowType_Mask == Qt.WindowType.Tool
    assert flags & Qt.WindowType.BypassWindowManagerHint

def test_platform_detects_kde_from_desktop_environment() -> None:
    assert is_kde_session({"XDG_CURRENT_DESKTOP": "KDE", "KDE_FULL_SESSION": ""})
    assert is_kde_session({"XDG_CURRENT_DESKTOP": "plasma:KDE", "KDE_FULL_SESSION": ""})
    assert is_kde_session({"XDG_CURRENT_DESKTOP": "GNOME", "KDE_FULL_SESSION": "true"})
    assert not is_kde_session({"XDG_CURRENT_DESKTOP": "GNOME", "KDE_FULL_SESSION": ""})

def test_kde_minimized_icon_uses_tool_window_flags_to_avoid_popup_mouse_grab() -> None:
    flags = restore_icon_window_flags(is_kde=True)

    assert flags & Qt.WindowType.WindowType_Mask == Qt.WindowType.Tool
    assert flags & Qt.WindowType.BypassWindowManagerHint

def test_gnome_minimized_icon_uses_managed_tool_window_flags() -> None:
    flags = restore_icon_window_flags(is_kde=False)

    assert flags & Qt.WindowType.WindowType_Mask == Qt.WindowType.Tool
    assert not flags & Qt.WindowType.BypassWindowManagerHint

def test_gnome_keeps_original_keyboard_panel_inset() -> None:
    panel = keyboard_panel_rect(width=1120, height=470, is_kde=False)

    assert panel.left() == 18
    assert panel.top() == 18
    assert panel.width() == 1084
    assert panel.height() == 434

def test_kde_keeps_tight_keyboard_panel_for_halo_fix() -> None:
    panel = keyboard_panel_rect(width=1120, height=470, is_kde=True)

    assert panel.left() == 2
    assert panel.top() == 2
    assert panel.width() == 1116
    assert panel.height() == 466

def test_qt_platform_prefers_keystone_osk_override() -> None:
    assert keyboard_app.preferred_qt_platform({"KEYSTONE_OSK_QT_PLATFORM": "wayland"}) == "wayland"
    assert keyboard_app.preferred_qt_platform({"KEYSTONE_OSK_QT_PLATFORM": "xcb", "WAYLAND_DISPLAY": "wayland-0"}) == "xcb"

def test_qt_platform_defaults_to_xcb_on_wayland_sessions() -> None:
    # XWayland is the default even under Wayland: native Wayland regresses the
    # dock-icon (no skip-taskbar) and the minimized icon (no client positioning).
    assert keyboard_app.preferred_qt_platform({"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}) == "xcb"
    assert keyboard_app.preferred_qt_platform({"WAYLAND_DISPLAY": "wayland-0"}) == "xcb"

def test_qt_platform_uses_xcb_for_x11_sessions_without_override() -> None:
    assert keyboard_app.preferred_qt_platform({"DISPLAY": ":0"}) == "xcb"
    assert keyboard_app.preferred_qt_platform({}) == "xcb"

def test_display_environment_detects_wayland_or_x11() -> None:
    assert not keyboard_app.has_display_environment({})
    assert keyboard_app.has_display_environment({"WAYLAND_DISPLAY": "wayland-0"})
    assert keyboard_app.has_display_environment({"DISPLAY": ":0"})
