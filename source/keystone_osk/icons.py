# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

from keystone_osk.platform import is_kde_session
from keystone_osk.theme import (
    DRACULA_THEME_ID,
    DUSK_THEME_ID,
    GENERIC_DARK_THEME_ID,
    GENERIC_LIGHT_THEME_ID,
    MOCHA_THEME_ID,
    _is_safe_relative_icon_path,
    resolve_theme,
    theme_pack_path,
)
from keystone_osk.tray_icon_names import BUNDLED_TRAY_ICON_PATH, tray_icon_system_fallback_candidates, tray_icon_theme_candidates
from keystone_osk.visual import scaled_minimized_keyboard_icon_rects, tray_icon_key_rect


def tray_icon_keyboard_body_rect(is_kde: bool | None = None) -> QRectF:
    session_is_kde = is_kde_session() if is_kde is None else is_kde
    if session_is_kde:
        return QRectF(7, 18, 50, 28)
    return QRectF(4, 18, 56, 28)


def tray_icon_outline_width(is_kde: bool | None = None) -> int:
    return 5 if (is_kde_session() if is_kde is None else is_kde) else 6


def tray_icon_corner_radius(is_kde: bool | None = None) -> float:
    return 3.0 if (is_kde_session() if is_kde is None else is_kde) else 7.0


def tray_icon_color(theme: str | None = None, is_kde: bool | None = None) -> QColor:
    if theme in {MOCHA_THEME_ID, DUSK_THEME_ID}:
        return QColor("#cdd6f4")
    if theme in {GENERIC_DARK_THEME_ID, "default-dark"}:
        return QColor("#ffffff")
    if theme in {GENERIC_LIGHT_THEME_ID, "default-light"}:
        return QColor("#000000")
    if theme == DRACULA_THEME_ID:
        return QColor("#f8f8f2")
    return QColor("#cdd6f4") if (is_kde_session() if is_kde is None else is_kde) else QColor(255, 255, 255)


def tray_icon_fill_color(theme: str | None = None) -> QColor:
    if theme in {MOCHA_THEME_ID, DUSK_THEME_ID}:
        return QColor("#1e1e2e")
    if theme in {GENERIC_LIGHT_THEME_ID, "default-light"}:
        return QColor("#ffffff")
    return QColor(Qt.GlobalColor.transparent)


def build_generated_tray_icon(theme: str | None = None, is_kde: bool | None = None) -> QIcon:
    is_kde = is_kde_session() if is_kde is None else is_kde
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    body_rect, key_rects = scaled_minimized_keyboard_icon_rects(tray_icon_keyboard_body_rect(is_kde))
    icon_color = tray_icon_color(theme, is_kde)
    fill_color = tray_icon_fill_color(theme)
    painter.setBrush(fill_color if fill_color.alpha() else Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(icon_color, tray_icon_outline_width(is_kde)))
    corner = tray_icon_corner_radius(is_kde)
    painter.drawRoundedRect(body_rect, corner, corner)
    painter.setBrush(icon_color)
    painter.setPen(Qt.PenStyle.NoPen)
    for key_rect in key_rects:
        painter.drawRoundedRect(tray_icon_key_rect(key_rect), 1.4, 1.4)
    painter.end()
    return QIcon(pixmap)


def build_bundled_tray_icon(path: Path = BUNDLED_TRAY_ICON_PATH) -> QIcon:
    if not path.exists():
        return QIcon()
    return QIcon(str(path))


def active_resolved_theme(theme: str | None):
    try:
        return resolve_theme(theme)
    except Exception:
        return None


def active_theme_dir(theme: str | None):
    path = theme_pack_path(theme)
    return path.parent if path is not None else None


def _theme_tray_icon(theme: str | None) -> QIcon | None:
    resolved = active_resolved_theme(theme)
    if resolved is None or not resolved.icons:
        return None
    theme_dir = active_theme_dir(theme)
    if theme_dir is None:
        return None
    for key in ("tray", "fallback_tray"):
        value = resolved.icons.get(key)
        if not isinstance(value, str) or not value:
            continue
        if not _is_safe_relative_icon_path(value, theme_dir):
            continue
        candidate = theme_dir / value
        if candidate.exists():
            icon = QIcon(str(candidate))
            if not icon.isNull():
                return icon
    return None


def build_tray_icon(
    theme: str | None = None,
    is_kde: bool | None = None,
    from_theme=QIcon.fromTheme,
    bundled_path: Path = BUNDLED_TRAY_ICON_PATH,
) -> QIcon:
    effective_kde = is_kde_session() if is_kde is None else is_kde
    theme_icon = _theme_tray_icon(theme)
    if theme_icon is not None:
        return theme_icon
    for icon_name in tray_icon_theme_candidates(theme):
        icon = from_theme(icon_name)
        if not icon.isNull() and icon.name() == icon_name:
            return icon
    if effective_kde:
        return build_generated_tray_icon(theme, is_kde)
    bundled_icon = build_bundled_tray_icon(bundled_path)
    if not bundled_icon.isNull():
        return bundled_icon
    for icon_name in tray_icon_system_fallback_candidates():
        icon = from_theme(icon_name)
        if not icon.isNull() and icon.name() == icon_name:
            return icon
    return build_generated_tray_icon(theme, is_kde)


def show_top_restore_fallback_if_needed(panel_button, tray_available: bool) -> None:
    if tray_available:
        panel_button.hide()
        return
    panel_button.move_to_top_bar()
    panel_button.show()
    panel_button.raise_()
