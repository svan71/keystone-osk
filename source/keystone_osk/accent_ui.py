from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from keystone_osk.theme import ThemePalette
from keystone_osk.visual import accent_strip_geometry

ACCENT_CELL_SIZE = 26
ACCENT_CELL_GAP = 4
ACCENT_MARGIN = 5
ACCENT_FONT_SIZE = 13


class AccentStrip(QWidget):
    def __init__(
        self,
        variants: tuple[str, ...],
        palette: ThemePalette,
        pick_callback: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._variants = variants
        self._bg_color = QColor(palette.panel_top)
        self._cell_bg = QColor(palette.key_normal_top)
        self._text_color = QColor(palette.text)
        self._accent_color = QColor(palette.key_locked_border)
        self._pick_callback = pick_callback
        self._cell_rects: list[QRect] = []

        self.setWindowTitle("Keystone Accents")
        # Popup (not Tool) so the strip joins Qt's popup-grab stack like the
        # snippets QMenu and the ModifierCancelOverlay segments: it then stacks
        # ABOVE the always-on-top keyboard and actually receives cell taps while
        # the cancel overlay (also a Popup) holds the pointer grab. A Tool window
        # renders behind the keyboard and the overlay's grab swallows its clicks.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Popup
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def show_above(self, key_global_rect: QRect, screen_rect: QRect) -> None:
        strip_rect, cell_rects = accent_strip_geometry(
            key_global_rect,
            len(self._variants),
            screen_rect,
            cell=ACCENT_CELL_SIZE,
            gap=ACCENT_CELL_GAP,
            margin=ACCENT_MARGIN,
        )
        self.setGeometry(strip_rect)
        # accent_strip_geometry returns cell rects in GLOBAL/screen coords, but
        # paintEvent and mousePressEvent both work in the widget's LOCAL space.
        # Translate cells to local (relative to the strip's top-left) or they
        # paint off-canvas (invisible) and hit-testing never matches.
        origin = strip_rect.topLeft()
        self._cell_rects = [c.translated(-origin.x(), -origin.y()) for c in cell_rects]
        self.show()
        self.raise_()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self._bg_color)
        painter.setPen(QPen(self._accent_color, 2))
        painter.drawRoundedRect(self.rect(), 8, 8)

        font = QFont("Noto Sans", ACCENT_FONT_SIZE)
        painter.setFont(font)
        for rect, char in zip(self._cell_rects, self._variants):
            painter.setBrush(self._cell_bg)
            painter.setPen(QPen(self._text_color, 1))
            painter.drawRoundedRect(rect, 5, 5)
            painter.setPen(self._text_color)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, char)
        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        for rect, char in zip(self._cell_rects, self._variants):
            if rect.contains(pos):
                self._pick_callback(char)
                return
        self._pick_callback("")
