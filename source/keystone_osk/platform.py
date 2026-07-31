# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import os
from collections.abc import Mapping


def preferred_qt_platform(environ: Mapping[str, str] | None = None) -> str:
    values = os.environ if environ is None else environ
    override = values.get("KEYSTONE_OSK_QT_PLATFORM")
    if override:
        return override
    # Default to XWayland (xcb), including on Wayland sessions. The native Wayland
    # platform has no skip-taskbar hint (so the keyboard shows a dock/taskbar
    # entry on GNOME) and forbids clients from positioning/sizing their own
    # windows, which breaks the minimized restore icon's drag, resize, and
    # remembered geometry. Under xcb, Qt.Tool sets _NET_WM_STATE_SKIP_TASKBAR and
    # X11 self-positioning works, so both issues go away. Native Wayland remains
    # available via KEYSTONE_OSK_QT_PLATFORM=wayland.
    return "xcb"


def has_display_environment(environ: Mapping[str, str] | None = None) -> bool:
    values = os.environ if environ is None else environ
    return bool(values.get("DISPLAY") or values.get("WAYLAND_DISPLAY"))


def is_kde_session(environ: Mapping[str, str] | None = None) -> bool:
    values = os.environ if environ is None else environ
    desktop = values.get("XDG_CURRENT_DESKTOP", "")
    return "KDE" in desktop.upper() or bool(values.get("KDE_FULL_SESSION"))


def read_portal_color_scheme() -> int | None:
    """Read the cross-desktop XDG appearance ``color-scheme`` preference
    (0 = no preference, 1 = prefer dark, 2 = prefer light) over D-Bus. Returns
    None when the portal is unavailable or the reply cannot be parsed.

    This reads the portal directly rather than Qt's ``QStyleHints.colorScheme()``
    because the latter is unreliable on GNOME under the xcb platform (it reports
    Dark regardless of the actual setting); the portal Read is authoritative."""
    try:
        from PySide6.QtDBus import QDBusConnection, QDBusMessage
    except Exception:
        return None
    message = QDBusMessage.createMethodCall(
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.portal.Settings",
        "Read",
    )
    message.setArguments(["org.freedesktop.appearance", "color-scheme"])
    reply = QDBusConnection.sessionBus().call(message)
    if reply.type() != QDBusMessage.MessageType.ReplyMessage:
        return None
    arguments = reply.arguments()
    if not arguments:
        return None
    value = arguments[0]
    # The portal wraps the value in nested D-Bus variants ('v' holding 'u').
    for _ in range(3):
        if hasattr(value, "variant"):
            value = value.variant()
        else:
            break
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def color_scheme_from_portal_value(value: int | None) -> str | None:
    """Map an XDG appearance color-scheme value to "dark"/"light". GNOME's
    "Default" appearance reports 0 (no preference) and is the light style, so it
    maps to "light"; only an explicit prefer-dark (1) maps to "dark". Returns
    None when the value is missing/unrecognised so the caller can pick a
    fallback."""
    if value == 1:
        return "dark"
    if value in (0, 2):
        return "light"
    return None


def detect_color_scheme(reader=read_portal_color_scheme) -> str | None:
    """The desktop's light/dark preference as "dark"/"light", or None when it
    cannot be determined."""
    return color_scheme_from_portal_value(reader())


def keyboard_window_flags(is_kde: bool | None = None):
    from PySide6.QtCore import Qt

    session_is_kde = is_kde_session() if is_kde is None else is_kde
    flags = (
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.Tool
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.WindowDoesNotAcceptFocus
    )
    if session_is_kde:
        flags |= Qt.WindowType.BypassWindowManagerHint
    return flags


def keyboard_panel_rect(width: int, height: int, is_kde: bool | None = None):
    from PySide6.QtCore import QRectF

    session_is_kde = is_kde_session() if is_kde is None else is_kde
    margin = 2 if session_is_kde else 18
    return QRectF(margin, margin, width - (margin * 2), height - (margin * 2))


def restore_icon_window_flags(is_kde: bool | None = None):
    from PySide6.QtCore import Qt

    session_is_kde = is_kde_session() if is_kde is None else is_kde
    flags = (
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.Tool
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.WindowDoesNotAcceptFocus
    )
    if session_is_kde:
        flags |= Qt.WindowType.BypassWindowManagerHint
    return flags


def is_corner_resize(edges) -> bool:
    from PySide6.QtCore import Qt

    return bool(edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge)) and bool(edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge))


def should_use_manual_resize(edges, is_kde: bool | None = None) -> bool:
    session_is_kde = is_kde_session() if is_kde is None else is_kde
    return session_is_kde or is_corner_resize(edges)


def keyboard_resize_margin(is_kde: bool | None = None) -> int:
    return 14 if (is_kde_session() if is_kde is None else is_kde) else 28
