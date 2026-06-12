from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGradient, QLinearGradient, QPainter, QPen

from keystone_osk.constants import APP_NAME
from keystone_osk.geometry import COMPACT_REFERENCE_HEIGHT, KEYBOARD_REFERENCE_WIDTH, PositionedKey, Rect
from keystone_osk.input_model import LOCK_KEYS, key_label_display
from keystone_osk.platform import keyboard_panel_rect
from keystone_osk.theme import key_paint_style, theme_palette
from keystone_osk.visual import (
    control_font_size,
    key_label_font_size,
    key_label_font_weight,
    key_label_text_rect,
    numpad_secondary_font_size,
    shifted_label_style,
    shifted_main_font_size,
    shifted_secondary_font_size,
    shifted_secondary_hint_rect,
    shifted_underscore_line,
    title_font_size,
)

KEYBOARD_TITLE = APP_NAME
KEYBOARD_FONT_FAMILY = "Noto Sans"
COMMON_EMOJIS = (
    "😀",
    "😂",
    "🤣",
    "😊",
    "😍",
    "😘",
    "😎",
    "😢",
    "😡",
    "👍",
    "👎",
    "🙏",
    "👏",
    "💪",
    "❤️",
    "🔥",
    "🎉",
    "✅",
    "❌",
    "👀",
    "🤔",
    "🙄",
    "💯",
    "⭐",
)


@lru_cache(maxsize=256)
def _themed_font(size: int, weight: QFont.Weight = QFont.Weight.Normal, family: str = KEYBOARD_FONT_FAMILY) -> QFont:
    # Cached so paintEvent does not allocate a fresh QFont per text draw (dozens
    # per frame). QPainter.setFont copies the font, so sharing instances is safe
    # as long as callers never mutate the returned object.
    return QFont(family, size, weight)


@lru_cache(maxsize=64)
def _vertical_gradient(top_color: str, bottom_color: str, top_alpha: int = 255, bottom_alpha: int = 255) -> QLinearGradient:
    # Object-bounding-mode gradient (0,0)->(0,1) maps to whatever shape it paints,
    # so a single cached instance works for every key rect regardless of size.
    gradient = QLinearGradient(0.0, 0.0, 0.0, 1.0)
    gradient.setCoordinateMode(QGradient.CoordinateMode.ObjectBoundingMode)
    top = QColor(top_color)
    top.setAlpha(top_alpha)
    bottom = QColor(bottom_color)
    bottom.setAlpha(bottom_alpha)
    gradient.setColorAt(0, top)
    gradient.setColorAt(1, bottom)
    return gradient


@lru_cache(maxsize=8)
def emoji_picker_font(scale: float) -> QFont:
    font = QFont()
    font.setPointSize(max(18, int(30 * scale)))
    return font


def is_glyph_key(key: PositionedKey) -> bool:
    """Return True for keys that render a custom glyph instead of a text label."""
    return key.role == "snippets"


def _blend_hex(a: str, b: str, t: float) -> str:
    """Blend two #rrggbb colors; t=0 -> a, t=1 -> b."""
    ai = int(a.lstrip("#"), 16)
    bi = int(b.lstrip("#"), 16)
    out = 0
    for shift in (16, 8, 0):
        ca = (ai >> shift) & 0xFF
        cb = (bi >> shift) & 0xFF
        out |= round(ca + (cb - ca) * t) << shift
    return f"#{out:06x}"


def _brightness(hex_color: str) -> float:
    v = int(hex_color.lstrip("#"), 16)
    return 0.299 * ((v >> 16) & 0xFF) + 0.587 * ((v >> 8) & 0xFF) + 0.114 * (v & 0xFF)


def _cap_contrast(color: str, key_face: str, max_distance: float) -> str:
    """Pull `color` toward `key_face` so its brightness gap never exceeds
    `max_distance`. Keeps boxes from looking too heavy on light themes while
    leaving already-moderate dark-theme colors untouched."""
    distance = abs(_brightness(color) - _brightness(key_face))
    if distance <= max_distance:
        return color
    return _blend_hex(color, key_face, 1 - max_distance / distance)


def _lighten_if_dark(color: str, key_face: str, amount: float) -> str:
    """Lighten `color` toward white when it sits darker than the key face (i.e. a
    dark box on a light theme, which looks heavy). Boxes lighter than the key
    face (dark themes) are left alone."""
    if _brightness(color) < _brightness(key_face):
        return _blend_hex(color, "#ffffff", amount)
    return color


def snippets_glyph_colors(palette) -> tuple[str, str]:
    """(back_fill, front_fill) for the Onboard-homage glyph.

    Onboard's logo is two overlapping squares; this is the themed homage. The
    front square uses ``key_locked_border`` — the same accent that lights up
    Ctrl/Caps/Shift when locked — for visual consistency. The back square is a
    computed mid-gray (halfway between text and key face) so it stays clearly
    visible on EVERY theme by construction: a fixed palette gray goes nearly
    invisible on the light theme (near-white on a white key), which is exactly
    the imbalance this avoids.
    """
    # Cap each box's contrast so it never looks too heavy on light themes (where
    # the accent is near-black). The two caps differ so the boxes stay distinct
    # instead of converging to one gray. Both caps exceed the dark-theme values,
    # so Dracula/Mocha are left exactly as tuned.
    gray = _cap_contrast(
        _blend_hex(palette.text, palette.key_normal_top, 0.42), palette.key_normal_top, 118.0
    )
    purple = _cap_contrast(
        _blend_hex(palette.key_locked_border, palette.key_normal_top, 0.18), palette.key_normal_top, 138.0
    )
    gray = _lighten_if_dark(gray, palette.key_normal_top, 0.25)
    purple = _lighten_if_dark(purple, palette.key_normal_top, 0.25)
    return gray, purple


class KeyboardRenderingMixin:
    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

            scale = min(self.width() / KEYBOARD_REFERENCE_WIDTH, self.height() / COMPACT_REFERENCE_HEIGHT)
            panel = keyboard_panel_rect(self.width(), self.height())
            palette = theme_palette(self._theme_name)

            painter.setBrush(_vertical_gradient(palette.panel_top, palette.panel_bottom, 250, 250))
            painter.setPen(QPen(QColor(palette.panel_border), max(2, int(4 * scale))))
            painter.drawRoundedRect(panel, 16 * scale, 16 * scale)

            self._draw_titlebar(painter, panel, scale, palette)
            if not self._is_collapsed:
                self._draw_keyboard(painter, panel, scale, palette)
        finally:
            painter.end()

    def _draw_titlebar(self, painter: QPainter, panel: QRectF, scale: float, palette=None) -> None:
        if palette is None:
            palette = theme_palette(self._theme_name)
        title_font = _themed_font(title_font_size(scale), QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(palette.text))
        self._title_rect = QRectF()
        if not self._suggestions:
            self._title_rect = QRectF(panel.left(), panel.top() + 14 * scale, panel.width(), 45 * scale)
            painter.drawText(self._title_rect, Qt.AlignmentFlag.AlignCenter, KEYBOARD_TITLE)

        full_mode = self._keyboard_mode == "full"
        control_size = max(8, int(24 * scale)) if full_mode else control_font_size(scale)
        painter.setFont(_themed_font(control_size))
        control_rect_scale = 0.82 if full_mode else 1.0
        control_rect_width = 42 * scale * control_rect_scale
        control_rect_height = 31 * scale * control_rect_scale
        control_gap = 14 * scale
        self._close_rect = QRectF(
            panel.left() + 20 * scale,
            panel.top() + 14 * scale,
            control_rect_width,
            control_rect_height,
        )
        self._minimize_rect = QRectF(
            self._close_rect.right() + control_gap,
            panel.top() + 14 * scale,
            control_rect_width,
            control_rect_height,
        )
        painter.setBrush(QColor(palette.control_background))
        painter.setPen(QPen(QColor(palette.control_border), max(1, int(2 * scale))))
        painter.drawRoundedRect(self._close_rect, 6 * scale, 6 * scale)
        painter.drawRoundedRect(self._minimize_rect, 6 * scale, 6 * scale)
        painter.setPen(QColor(palette.text))
        painter.drawText(self._close_rect, Qt.AlignmentFlag.AlignCenter, "×")
        painter.drawText(self._minimize_rect, Qt.AlignmentFlag.AlignCenter, "−")

        self._mode_toggle_rect = QRectF(
            self._minimize_rect.right() + control_gap,
            panel.top() + 14 * scale,
            control_rect_width,
            control_rect_height,
        )
        painter.setBrush(QColor(palette.control_background))
        painter.setPen(QPen(QColor(palette.control_border), max(1, int(2 * scale))))
        mode_toggle_frame = self._mode_toggle_rect.adjusted(-2 * scale, -2 * scale, 2 * scale, 2 * scale)
        painter.drawRoundedRect(mode_toggle_frame, 7 * scale, 7 * scale)
        icon_rect = self._mode_toggle_rect.adjusted(8 * scale, 6 * scale, -8 * scale, -6 * scale)
        icon_color = QColor(palette.text)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(icon_color, max(1, int(2 * scale))))
        painter.drawRoundedRect(icon_rect, 3 * scale, 3 * scale)
        key_w = max(1.0, icon_rect.width() / 8.0)
        key_h = max(1.0, icon_rect.height() / 8.0)
        key_gap_x = max(1.0, icon_rect.width() / 6.5)
        key_gap_y = max(1.0, icon_rect.height() / 6.5)
        grid_width = key_w * 3 + key_gap_x * 2
        grid_height = key_h * 3 + key_gap_y * 2
        grid_left = icon_rect.center().x() - grid_width / 2
        grid_top = icon_rect.center().y() - grid_height / 2
        painter.setBrush(icon_color)
        painter.setPen(Qt.PenStyle.NoPen)
        for row in range(3):
            for col in range(3):
                painter.drawRoundedRect(
                    QRectF(
                        grid_left + col * (key_w + key_gap_x),
                        grid_top + row * (key_h + key_gap_y),
                        key_w,
                        key_h,
                    ),
                    0.8 * scale,
                    0.8 * scale,
                )

        menu_width = max(40.0, 68.0 * scale) if full_mode else max(48.0, 78.0 * scale)
        menu_height = max(18.0, 27.0 * scale) if full_mode else max(22.0, 31.0 * scale)
        menu_right_inset = max(18.0, 12.0 * scale) if full_mode else max(8.0, 12.0 * scale)
        menu_top_inset = max(10.0, 14.0 * scale)
        self._menu_rect = QRectF(panel.right() - menu_width - menu_right_inset, panel.top() + menu_top_inset, menu_width, menu_height)
        painter.setBrush(QColor(palette.control_background))
        painter.setPen(QPen(QColor(palette.control_border), max(1, int(2 * scale))))
        painter.drawRoundedRect(self._menu_rect, 6 * scale, 6 * scale)
        painter.setPen(QColor(palette.text))
        menu_font_size = max(8, int(13 * scale)) if full_mode else max(10, int(15 * scale))
        painter.setFont(_themed_font(menu_font_size, QFont.Weight.DemiBold))
        painter.drawText(self._menu_rect, Qt.AlignmentFlag.AlignCenter, "Menu")

    def _draw_keyboard(self, painter: QPainter, panel: QRectF, scale: float, palette=None) -> None:
        del panel
        if palette is None:
            palette = theme_palette(self._theme_name)
        geometry = self._keyboard_geometry()
        self._positioned_keys = geometry.keys
        if self._emoji_picker_visible:
            self._suggestion_rects = ()
        else:
            self._draw_suggestions(painter, scale, palette)
        for key in geometry.keys:
            self._draw_positioned_key(painter, key, scale, palette)
        if self._emoji_picker_visible:
            self._draw_emoji_picker(painter, scale, palette)

    def _draw_suggestions(self, painter: QPainter, scale: float, palette=None) -> None:
        self._suggestion_rects = ()
        if not self._suggestions:
            return
        if palette is None:
            palette = theme_palette(self._theme_name)
        panel = keyboard_panel_rect(self.width(), self.height())
        gap = max(4.0, 8.0 * scale)
        if self._keyboard_mode == "full":
            row_left = panel.left() + 170.0 * scale
            row_right = panel.right() - 170.0 * scale
        else:
            switch_right = (
                self._mode_toggle_rect.right()
                if self._mode_toggle_rect.width() > 0
                else panel.left() + (132.0 + 42.0) * scale
            )
            row_left = switch_right + 14.0 * scale
            row_right = panel.right() - 120.0 * scale
        row_width = max(120.0, row_right - row_left)
        suggestion_count = len(self._suggestions)
        chip_width = (row_width - gap * (suggestion_count - 1)) / suggestion_count
        chip_height = max(17.0, 24.0 * scale)
        if self._keyboard_mode == "full":
            top = panel.top() + 20.0 * scale
        else:
            # _draw_keyboard refreshed _positioned_keys this frame; don't rebuild
            # the full key geometry just to find the "1" row. The fallback covers
            # direct calls (tests) before any keyboard paint has happened.
            keys = self._positioned_keys or self._keyboard_geometry().keys
            number_top = min(key.rect.top for key in keys if key.label == "1")
            top = (panel.top() + number_top - chip_height) / 2.0
        rects: list[tuple[QRectF, str]] = []
        painter.setFont(_themed_font(max(9, int(14 * scale)), QFont.Weight.Medium))
        for index, suggestion in enumerate(self._suggestions):
            rect = QRectF(row_left + index * (chip_width + gap), top, chip_width, chip_height)
            rects.append((rect, suggestion))
            painter.setBrush(QColor(palette.panel_top))
            painter.setPen(QPen(QColor(palette.suggestion_border), max(1, int(2 * scale))))
            painter.drawRoundedRect(rect, 6 * scale, 6 * scale)
            painter.setPen(QColor(palette.text))
            painter.drawText(rect.adjusted(4 * scale, 0, -4 * scale, 0), Qt.AlignmentFlag.AlignCenter, suggestion)
        self._suggestion_rects = tuple(rects)

    def _draw_emoji_picker(self, painter: QPainter, scale: float, palette=None) -> None:
        if palette is None:
            palette = theme_palette(self._theme_name)
        panel = keyboard_panel_rect(self.width(), self.height())
        cols = 8
        rows = 3
        gap = max(5.0, 8.0 * scale)
        width = min(panel.width() - 36.0 * scale, 520.0 * scale)
        cell_width = (width - gap * (cols - 1)) / cols
        cell_height = max(30.0, 42.0 * scale)
        height = rows * cell_height + gap * (rows - 1)
        left = panel.center().x() - width / 2.0
        top = panel.top() + (58.0 if self._keyboard_mode == "compact" else 50.0) * scale
        picker_rect = QRectF(left - 9.0 * scale, top - 9.0 * scale, width + 18.0 * scale, height + 18.0 * scale)
        painter.setBrush(QColor(palette.panel_bottom))
        painter.setPen(QPen(QColor(palette.panel_border), max(1, int(2 * scale))))
        painter.drawRoundedRect(picker_rect, 10 * scale, 10 * scale)

        rects: list[tuple[QRectF, str]] = []
        painter.setFont(emoji_picker_font(scale))
        for index, emoji in enumerate(COMMON_EMOJIS):
            row = index // cols
            col = index % cols
            rect = QRectF(left + col * (cell_width + gap), top + row * (cell_height + gap), cell_width, cell_height)
            rects.append((rect, emoji))
            painter.setBrush(QColor(palette.key_normal_top))
            painter.setPen(QPen(QColor(palette.key_normal_border), max(1, int(2 * scale))))
            painter.drawRoundedRect(rect, 7 * scale, 7 * scale)
            painter.setPen(QColor(palette.text))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, emoji)
        self._emoji_rects = tuple(rects)

    def _draw_positioned_key(self, painter: QPainter, key: PositionedKey, scale: float, palette=None) -> None:
        rect = self._qt_rect(key.rect)
        if palette is None:
            palette = theme_palette(self._theme_name)
        is_hovered = key.id == self._hovered_key_id
        is_pressed = key.id == self._pressed_key_id and key.label in LOCK_KEYS
        is_locked = key.label in self._locked_key_labels
        self._draw_key_shape(
            painter,
            rect,
            scale,
            is_hovered=is_hovered,
            is_pressed=is_pressed,
            is_locked=is_locked,
            radius=6 if key.role == "arrow" else 7,
        )
        label_display = key_label_display(key, self._locked_key_labels)
        label = label_display.main
        if key.role == "arrow":
            painter.setPen(QColor(palette.text))
            painter.setFont(_themed_font(max(7, int(16 * scale)), QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, key.glyph)
            return
        if key.id.startswith("full-numpad-") and label_display.alternate:
            painter.setPen(QColor(palette.text))
            painter.setFont(_themed_font(key_label_font_size(key, label, scale), QFont.Weight.Medium))
            painter.drawText(
                rect.adjusted(2 * scale, 1 * scale, -2 * scale, -rect.height() * 0.26),
                Qt.AlignmentFlag.AlignCenter,
                label,
            )
            painter.setFont(_themed_font(numpad_secondary_font_size(label_display.alternate, scale), QFont.Weight.Medium))
            painter.drawText(
                rect.adjusted(2 * scale, rect.height() * 0.52, -2 * scale, -2 * scale),
                Qt.AlignmentFlag.AlignCenter,
                label_display.alternate,
            )
            return
        if label_display.alternate:
            shifted_style = shifted_label_style(scale, is_full=key.id.startswith("full-"))
            painter.setPen(QColor(palette.text))
            painter.setFont(_themed_font(shifted_secondary_font_size(key, scale), shifted_style.font_weight))
            if label_display.alternate == "_":
                painter.setPen(QPen(QColor(palette.text), max(1, int(2.5 * scale)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(shifted_underscore_line(key, scale))
                painter.setPen(QColor(palette.text))
            else:
                painter.drawText(
                    shifted_secondary_hint_rect(key, scale),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                    label_display.alternate,
                )
            painter.setFont(_themed_font(shifted_main_font_size(key, label, scale), QFont.Weight.Medium))
            painter.drawText(
                rect.adjusted(rect.width() * shifted_style.main_left_bias, rect.height() * 0.04, -6 * scale, -2 * scale),
                Qt.AlignmentFlag.AlignCenter,
                label,
            )
            return

        if is_glyph_key(key):
            self._draw_snippets_glyph(painter, key.rect, scale, palette)
            return

        if not label:
            return
        painter.setPen(QColor(palette.text))
        painter.setFont(_themed_font(key_label_font_size(key, label, scale), key_label_font_weight(key, label)))
        painter.drawText(key_label_text_rect(key, scale), Qt.AlignmentFlag.AlignCenter, label)

    def _draw_key_shape(
        self,
        painter: QPainter,
        rect: QRectF,
        scale: float,
        radius: int = 7,
        is_hovered: bool = False,
        is_pressed: bool = False,
        is_locked: bool = False,
    ) -> None:
        style = key_paint_style(is_hovered=is_hovered, is_pressed=is_pressed, is_locked=is_locked, theme=self._theme_name)
        painter.setBrush(_vertical_gradient(style.top_color, style.bottom_color))
        painter.setPen(QPen(QColor(style.border_color), max(1, int(style.border_width * scale))))
        painter.drawRoundedRect(rect, radius * scale, radius * scale)

    def _draw_snippets_glyph(self, painter: QPainter, rect: Rect, scale: float, palette) -> None:
        """Two overlapping rounded squares — an Onboard-homage snippet indicator."""
        cx, cy = rect.center_x, rect.center_y
        side = min(rect.width, rect.height) * 0.3024
        off = side * 0.40
        radius = side * 0.28
        back = QRectF(cx - side / 2 - off, cy - side / 2 - off, side, side)
        front = QRectF(cx - side / 2 + off, cy - side / 2 + off, side, side)
        back_fill, front_fill = snippets_glyph_colors(palette)
        # No outline: a dark border merges into the dark key on the accent square,
        # shrinking its apparent size. Solid fills + draw order keep both squares
        # the same visual size; the overlap reads from the front drawn over back.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(back_fill))
        painter.drawRoundedRect(back, radius, radius)
        painter.setBrush(QColor(front_fill))
        painter.drawRoundedRect(front, radius, radius)

    def _qt_rect(self, rect: Rect) -> QRectF:
        return QRectF(rect.left, rect.top, rect.width, rect.height)
