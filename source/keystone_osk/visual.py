# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QLineF, QPoint, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from keystone_osk.geometry import PositionedKey


@dataclass(frozen=True)
class ShiftedLabelStyle:
    font_size: int
    left_inset: float
    top_inset: float
    main_left_bias: float
    font_weight: QFont.Weight


def shifted_label_style(scale: float, is_full: bool = False) -> ShiftedLabelStyle:
    if is_full:
        return ShiftedLabelStyle(
            font_size=max(9, int(16 * scale)),
            left_inset=7 * scale,
            top_inset=4 * scale,
            main_left_bias=0.43,
            font_weight=QFont.Weight.Medium,
        )
    return ShiftedLabelStyle(
        font_size=max(8, int(14 * scale)),
        left_inset=7 * scale,
        top_inset=5 * scale,
        main_left_bias=0.43,
        font_weight=QFont.Weight.Medium,
    )


def title_font_size(scale: float) -> int:
    return max(9, int(24 * scale))


def control_font_size(scale: float) -> int:
    return max(9, int(31 * scale))


def shifted_main_font_size(key: PositionedKey, label: str, scale: float) -> int:
    del label
    is_full = key.id.startswith("full-")
    base = 20 if is_full else 26
    height_cap = 0.50 if is_full else 0.56
    return min(max(7, int(base * scale)), max(7, int(key.rect.height * height_cap)))


def shifted_secondary_font_size(key: PositionedKey, scale: float) -> int:
    """Point size for the corner hint glyph (the shifted symbol above the main
    label). Capped by key height like shifted_main_font_size so it scales down on
    small keys instead of staying floored too large — the previous fixed floor
    overflowed its hint area and clipped at the smallest keyboard size. Stays
    smaller than the main label."""
    is_full = key.id.startswith("full-")
    base = 13 if is_full else 14
    height_cap = 0.34 if is_full else 0.40
    return min(max(7, int(base * scale)), max(7, int(key.rect.height * height_cap)))


def shifted_secondary_hint_rect(key: PositionedKey, scale: float) -> QRectF:
    """Top-left area the shifted symbol is drawn into. Tall enough to contain the
    capped secondary font box so drawText (which clips to its rect) never truncates
    the glyph; the main label is biased right (main_left_bias) so the extra height
    does not collide with it."""
    style = shifted_label_style(scale, is_full=key.id.startswith("full-"))
    rect = QRectF(key.rect.left, key.rect.top, key.rect.width, key.rect.height)
    return QRectF(
        rect.left() + style.left_inset,
        rect.top() + style.top_inset,
        rect.width() * 0.40,
        rect.height() * 0.68,
    )


def shifted_underscore_line(key: PositionedKey, scale: float) -> QLineF:
    style = shifted_label_style(scale, is_full=key.id.startswith("full-"))
    rect = QRectF(key.rect.left, key.rect.top, key.rect.width, key.rect.height)
    left = rect.left() + style.left_inset
    y = rect.top() + style.top_inset + max(6.0, rect.height() * 0.20)
    return QLineF(left, y, left + max(7.0, rect.width() * 0.22), y)


def key_label_font_size(key: PositionedKey, label: str, scale: float) -> int:
    if key.id.startswith("full-"):
        is_main_label = len(label) == 1 and (label.isalnum() or label in {"/", "*", "-", ".", ","})
        base = 17
        minimum = 7
        height_cap = 0.38
        if key.role == "backspace":
            base = 15
            minimum = 8
            height_cap = 0.38
        elif not is_main_label:
            base = 14
            minimum = 6
        return min(max(minimum, int(base * scale)), max(minimum, int(key.rect.height * height_cap)))
    if key.role in {"function", "navigation", "numpad", "system"}:
        if key.role == "numpad":
            base = 20
        elif key.role == "navigation":
            base = 18
        else:
            base = 17
        minimum = 7
        if len(label) > 3:
            if key.role == "numpad":
                base = 18
            elif key.role == "navigation":
                base = 17
            else:
                base = 15
        return min(max(minimum, int(base * scale)), max(minimum, int(key.rect.height * 0.62)))
    # full-* keys returned above, so only compact-layout keys reach here.
    base = 27
    minimum = 8
    if key.role in {"tab", "caps", "shift", "enter", "delete"}:
        base = 22
        minimum = 7
    elif key.role == "backspace":
        base = 18
        minimum = 7
    elif key.role == "modifier":
        base = 19
        minimum = 7
    elif len(label) > 1:
        base = 24
    if len(label) > 5:
        base = 20
        minimum = 7
    return min(max(minimum, int(base * scale)), max(minimum, int(key.rect.height * 0.52)))


def key_label_font_weight(key: PositionedKey, label: str) -> QFont.Weight:
    if key.id.startswith("full-") and not (len(label) == 1 and (label.isalnum() or label in {"/", "*", "-", ".", ","})):
        return QFont.Weight.Normal
    return QFont.Weight.Medium


def numpad_secondary_font_size(label: str, scale: float) -> int:
    return max(7, int((11 if len(label) <= 1 else 10) * scale))


def key_label_text_rect(key: PositionedKey, scale: float) -> QRectF:
    rect = QRectF(key.rect.left, key.rect.top, key.rect.width, key.rect.height)
    if key.id.startswith("full-") and key.role == "backspace":
        return rect.adjusted(8 * scale, 7 * scale, -8 * scale, -1 * scale)
    if key.role == "backspace":
        return rect.adjusted(8 * scale, 5 * scale, -8 * scale, -1 * scale)
    return rect.adjusted(4 * scale, -1 * scale, -4 * scale, -4 * scale)


def keyboard_resize_edges_at(width: int, height: int, x: float, y: float, margin: int):
    edges = None
    if x <= margin:
        edges = Qt.Edge.LeftEdge
    elif x >= width - margin:
        edges = Qt.Edge.RightEdge
    if y <= margin:
        edges = Qt.Edge.TopEdge if edges is None else edges | Qt.Edge.TopEdge
    elif y >= height - margin:
        edges = Qt.Edge.BottomEdge if edges is None else edges | Qt.Edge.BottomEdge
    return edges


def fit_window_size_to_screen(size: QSize, margin: int = 14, screen_rect: QRect | None = None) -> QSize:
    if screen_rect is None:
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)
    max_width = max(1, screen_rect.width() - (margin * 2))
    max_height = max(1, screen_rect.height() - (margin * 2))
    return QSize(min(int(size.width()), max_width), min(int(size.height()), max_height))


def top_right_window_position(size: QSize, margin: int = 14, screen_rect: QRect | None = None) -> QPoint:
    if screen_rect is None:
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)
    fitted_size = fit_window_size_to_screen(size, margin, screen_rect)
    return QPoint(
        max(screen_rect.left() + margin, screen_rect.right() - int(fitted_size.width()) - margin + 1),
        screen_rect.top() + margin,
    )


def clamp_window_position(position: QPoint, size: QSize, margin: int = 14, screen_rect: QRect | None = None) -> QPoint:
    if screen_rect is None:
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)
    fitted_size = fit_window_size_to_screen(size, margin, screen_rect)
    min_x = screen_rect.left() + margin
    min_y = screen_rect.top() + margin
    max_x = screen_rect.right() - int(fitted_size.width()) - margin + 1
    max_y = screen_rect.bottom() - int(fitted_size.height()) - margin + 1
    return QPoint(
        min(max(int(position.x()), min_x), max(min_x, max_x)),
        min(max(int(position.y()), min_y), max(min_y, max_y)),
    )


def minimized_keyboard_body_rect() -> QRectF:
    return QRectF(4, 9, 40, 26)


def minimized_keyboard_key_rects() -> tuple[QRectF, ...]:
    keys: list[QRectF] = []
    x_positions = (11, 18, 25, 32)
    for y in (15.8, 21.3):
        keys.extend(QRectF(x, y, 5.5, 1.7) for x in x_positions)
    keys.extend(
        (
            QRectF(10, 27, 4.5, 1.7),
            QRectF(16, 27, 16, 1.7),
            QRectF(33.5, 27, 4.5, 1.7),
        )
    )
    return tuple(keys)


def scaled_minimized_keyboard_icon_rects(target_body: QRectF) -> tuple[QRectF, tuple[QRectF, ...]]:
    source_body = minimized_keyboard_body_rect()
    scale_x = target_body.width() / source_body.width()
    scale_y = target_body.height() / source_body.height()

    def scale_rect(rect: QRectF) -> QRectF:
        return QRectF(
            target_body.left() + (rect.left() - source_body.left()) * scale_x,
            target_body.top() + (rect.top() - source_body.top()) * scale_y,
            rect.width() * scale_x,
            rect.height() * scale_y,
        )

    return target_body, tuple(scale_rect(rect) for rect in minimized_keyboard_key_rects())


def tray_icon_key_rect(key_rect: QRectF) -> QRectF:
    return key_rect.adjusted(-0.25, -0.35, 0.25, 0.35)


def accent_strip_geometry(
    key_global_rect: QRect,
    variant_count: int,
    screen_rect: QRect,
    *,
    cell: int,
    gap: int,
    margin: int,
) -> tuple[QRect, list[QRect]]:
    strip_width = margin * 2 + cell * variant_count + gap * (variant_count - 1)
    strip_height = margin * 2 + cell

    strip_x = key_global_rect.center().x() - strip_width // 2
    strip_y = key_global_rect.top() - strip_height - gap

    if strip_y < screen_rect.top():
        strip_y = key_global_rect.bottom() + gap

    max_x = screen_rect.right() - strip_width
    strip_x = max(screen_rect.left(), min(int(strip_x), max_x))

    strip_rect = QRect(int(strip_x), int(strip_y), strip_width, strip_height)

    cell_rects: list[QRect] = []
    cell_x = strip_rect.left() + margin
    cell_y = strip_rect.top() + margin
    for i in range(variant_count):
        cell_rects.append(QRect(cell_x + i * (cell + gap), cell_y, cell, cell))

    return strip_rect, cell_rects


def desktop_geometry() -> QRect:
    screens = QApplication.screens()
    if not screens:
        screen = QApplication.primaryScreen()
        return screen.geometry() if screen is not None else QRect(0, 0, 1280, 720)
    geometry = QRect(screens[0].geometry())
    for screen in screens[1:]:
        geometry = geometry.united(screen.geometry())
    return geometry
