from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, QPoint, QRect, QRectF, QSize, Qt, Slot
from PySide6.QtGui import QAction, QGuiApplication, QPainter, QPen, QRegion
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from keystone_osk.constants import APP_NAME
from keystone_osk.platform import restore_icon_window_flags
from keystone_osk.state import (
    DEFAULT_RESTORE_ICON_HEIGHT,
    DEFAULT_RESTORE_ICON_WIDTH,
    MAX_RESTORE_ICON_HEIGHT,
    MAX_RESTORE_ICON_WIDTH,
    MIN_RESTORE_ICON_HEIGHT,
    MIN_RESTORE_ICON_WIDTH,
    load_restore_icon_geometry,
    save_restore_icon_geometry,
)
from keystone_osk.theme import app_menu_style_sheet, normalized_theme_name, restore_icon_background_color, restore_icon_foreground_color
from keystone_osk.visual import (
    desktop_geometry,
    minimized_keyboard_body_rect,
    minimized_keyboard_key_rects,
    scaled_minimized_keyboard_icon_rects,
)

KEYBOARD_TITLE = APP_NAME
PANEL_RESTORE_WIDTH = 48
PANEL_RESTORE_HEIGHT = 42
PANEL_RESTORE_RIGHT_MARGIN = 14
PANEL_RESTORE_TOP_MARGIN = 4
DESKTOP_RESTORE_RESIZE_MARGIN = 9
DESKTOP_RESTORE_MIN_HIT_MARGIN = 10.0
DESKTOP_RESTORE_CONTEXT_MENU_GAP = 8
DESKTOP_RESTORE_BODY_LEFT = 9
DESKTOP_RESTORE_BODY_TOP = 13
DESKTOP_RESTORE_BODY_HORIZONTAL_INSET = 18
DESKTOP_RESTORE_BODY_BOTTOM_INSET = 25


class PanelRestoreButton(QWidget):
    def __init__(self, restore_callback: Callable[[], None], theme: str = "dark") -> None:
        super().__init__(None)
        self._restore_callback = restore_callback
        self._theme_name = normalized_theme_name(theme)
        self._drag_offset: QPoint | None = None
        self._drag_start = QPoint()
        self.setWindowTitle(KEYBOARD_TITLE)
        self.resize(PANEL_RESTORE_WIDTH, PANEL_RESTORE_HEIGHT)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        icon_color = restore_icon_foreground_color(self._theme_name)
        painter.setPen(QPen(icon_color, 2.5))
        painter.drawRoundedRect(minimized_keyboard_body_rect(), 5, 5)
        painter.setBrush(icon_color)
        painter.setPen(Qt.PenStyle.NoPen)
        for key_rect in minimized_keyboard_key_rects():
            painter.drawRoundedRect(key_rect, 1.2, 1.2)
        painter.end()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._restore_callback()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._drag_start = event.globalPosition().toPoint()
        self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is None or not event.buttons() & Qt.MouseButton.LeftButton:
            return
        self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        del event
        self._drag_offset = None

    def set_theme(self, theme: str) -> None:
        self._theme_name = normalized_theme_name(theme)
        self.update()

    def move_to_top_bar(self) -> None:
        screen = QApplication.primaryScreen()
        geometry = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)
        self.move(
            geometry.right() - self.width() - PANEL_RESTORE_RIGHT_MARGIN,
            geometry.top() + PANEL_RESTORE_TOP_MARGIN,
        )


class DesktopRestoreIcon(QWidget):
    def __init__(
        self,
        restore_callback: Callable[[], None],
        close_callback: Callable[[], None] | None = None,
        persist_geometry: bool = True,
        theme: str = "dark",
    ) -> None:
        super().__init__(None)
        self._restore_callback = restore_callback
        self._close_callback = close_callback or self.hide
        self._persist_geometry = persist_geometry
        self._theme_name = normalized_theme_name(theme)
        self._drag_offset: QPoint | None = None
        self._active_resize_edges = None
        self._resize_origin_geometry = QRect()
        self._resize_origin_global = QPoint()
        self._resize_margin = DESKTOP_RESTORE_RESIZE_MARGIN
        self._context_menu = self._build_context_menu()
        self.setWindowTitle(KEYBOARD_TITLE)
        self.setMinimumSize(MIN_RESTORE_ICON_WIDTH, MIN_RESTORE_ICON_HEIGHT)
        self.setMaximumSize(MAX_RESTORE_ICON_WIDTH, MAX_RESTORE_ICON_HEIGHT)
        self.setGeometry(load_restore_icon_geometry())
        self.setWindowFlags(restore_icon_window_flags())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)
        self._apply_shape_mask()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        self._paint_restore_icon(painter)
        painter.end()

    def _paint_restore_icon(self, painter: QPainter) -> None:
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale = self._body_scale()
        body, key_rects = scaled_minimized_keyboard_icon_rects(self._body_rect())
        icon_color = restore_icon_foreground_color(self._theme_name)
        background_color = restore_icon_background_color(self._theme_name)
        background_color.setAlpha(255)
        painter.setBrush(background_color)
        painter.setPen(QPen(icon_color, max(1.25, 2.0 * scale)))
        painter.drawRoundedRect(body, 7 * scale, 7 * scale)
        painter.setBrush(icon_color)
        painter.setPen(Qt.PenStyle.NoPen)
        for key_rect in key_rects:
            painter.drawRoundedRect(key_rect, 1.0 * scale, 1.0 * scale)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_shape_mask()

    def _apply_shape_mask(self) -> None:
        self.setMask(QRegion(self._body_rect().toAlignedRect()))

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._save_geometry()
            self._restore_callback()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        resize_edges = self._resize_edges_at(event.position().x(), event.position().y())
        if resize_edges is not None:
            self._begin_manual_resize(resize_edges, event.globalPosition().toPoint())
            return
        self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._active_resize_edges is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._apply_manual_resize(event.globalPosition().toPoint())
            return
        if self._drag_offset is None:
            self._update_resize_cursor(event.position().x(), event.position().y())
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        del event
        self._finish_manual_resize()

    def leaveEvent(self, event) -> None:  # noqa: N802
        del event
        if self._active_resize_edges is None:
            self.unsetCursor()

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        self._context_menu.popup(self._context_menu_anchor(self._context_menu.sizeHint(), event.globalPos()))
        event.accept()

    def _build_context_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.setStyleSheet(self._context_menu_style_sheet())
        close_action = QAction("Close", self)
        close_action.triggered.connect(self._close_callback)
        menu.addAction(close_action)
        return menu

    def set_theme(self, theme: str) -> None:
        self._theme_name = normalized_theme_name(theme)
        self._context_menu.setStyleSheet(self._context_menu_style_sheet())
        self.update()

    def _context_menu_style_sheet(self) -> str:
        return app_menu_style_sheet(self._theme_name, border=False, menu_padding="2px", item_padding="4px 14px")

    def _context_menu_anchor(self, menu_size: QSize, click_pos: QPoint) -> QPoint:
        anchor = QPoint(
            click_pos.x() + DESKTOP_RESTORE_CONTEXT_MENU_GAP,
            click_pos.y() - menu_size.height() - DESKTOP_RESTORE_CONTEXT_MENU_GAP,
        )
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return anchor
        available = screen.availableGeometry()
        max_x = max(available.left(), available.right() - menu_size.width() + 1)
        max_y = max(available.top(), available.bottom() - menu_size.height() + 1)
        anchor.setX(min(max(anchor.x(), available.left()), max_x))
        anchor.setY(min(max(anchor.y(), available.top()), max_y))
        return anchor

    def _resize_edges_at(self, x: float, y: float):
        body = self._body_rect()
        margin = max(DESKTOP_RESTORE_MIN_HIT_MARGIN, self._resize_margin * self._body_scale())
        edges = None
        if 0 <= x <= max(margin, body.left() + margin):
            edges = Qt.Edge.LeftEdge
        elif min(self.width() - margin, body.right() - margin) <= x <= self.width():
            edges = Qt.Edge.RightEdge
        if 0 <= y <= max(margin, body.top() + margin):
            edges = Qt.Edge.TopEdge if edges is None else edges | Qt.Edge.TopEdge
        elif min(self.height() - margin, body.bottom() - margin) <= y <= self.height():
            edges = Qt.Edge.BottomEdge if edges is None else edges | Qt.Edge.BottomEdge
        return edges

    def _body_scale(self) -> float:
        return min(self.width() / DEFAULT_RESTORE_ICON_WIDTH, self.height() / DEFAULT_RESTORE_ICON_HEIGHT)

    def _body_rect(self) -> QRectF:
        scale = self._body_scale()
        return QRectF(
            DESKTOP_RESTORE_BODY_LEFT * scale,
            DESKTOP_RESTORE_BODY_TOP * scale,
            self.width() - DESKTOP_RESTORE_BODY_HORIZONTAL_INSET * scale,
            self.height() - DESKTOP_RESTORE_BODY_BOTTOM_INSET * scale,
        )

    def _begin_manual_resize(self, edges, global_pos: QPoint) -> None:
        self._active_resize_edges = edges
        self._resize_origin_geometry = self.geometry()
        self._resize_origin_global = global_pos

    def _apply_manual_resize(self, global_pos: QPoint) -> None:
        origin = self._resize_origin_geometry
        delta = global_pos - self._resize_origin_global
        x = origin.x()
        y = origin.y()
        width = origin.width()
        height = origin.height()

        if self._active_resize_edges & Qt.Edge.LeftEdge:
            width = origin.width() - delta.x()
            if width < self.minimumWidth():
                width = self.minimumWidth()
                x = origin.right() - self.minimumWidth() + 1
            else:
                x = origin.x() + delta.x()
        if self._active_resize_edges & Qt.Edge.RightEdge:
            width = min(self.maximumWidth(), max(self.minimumWidth(), origin.width() + delta.x()))
        if self._active_resize_edges & Qt.Edge.TopEdge:
            height = origin.height() - delta.y()
            if height < self.minimumHeight():
                height = self.minimumHeight()
                y = origin.bottom() - self.minimumHeight() + 1
            elif height > self.maximumHeight():
                height = self.maximumHeight()
                y = origin.bottom() - self.maximumHeight() + 1
            else:
                y = origin.y() + delta.y()
        if self._active_resize_edges & Qt.Edge.BottomEdge:
            height = min(self.maximumHeight(), max(self.minimumHeight(), origin.height() + delta.y()))

        if width > self.maximumWidth():
            width = self.maximumWidth()
            if self._active_resize_edges & Qt.Edge.LeftEdge:
                x = origin.right() - self.maximumWidth() + 1

        self.setGeometry(x, y, width, height)
        self._apply_shape_mask()

    def _update_resize_cursor(self, x: float, y: float) -> None:
        edges = self._resize_edges_at(x, y)
        if edges is None:
            self.unsetCursor()
            return
        horizontal = bool(edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge))
        vertical = bool(edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge))
        if horizontal and vertical:
            if edges & Qt.Edge.LeftEdge and edges & Qt.Edge.TopEdge:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif edges & Qt.Edge.RightEdge and edges & Qt.Edge.BottomEdge:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif horizontal:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif vertical:
            self.setCursor(Qt.CursorShape.SizeVerCursor)

    def _save_geometry(self) -> None:
        if self._persist_geometry:
            save_restore_icon_geometry(self.geometry())

    def _finish_manual_resize(self) -> None:
        self._drag_offset = None
        self._active_resize_edges = None
        self.unsetCursor()
        self._save_geometry()


class _CancelOverlaySegment(QWidget):
    def __init__(self, cancel_callback: Callable[[], None], popup: bool = True) -> None:
        super().__init__(None)
        self._cancel_callback = cancel_callback
        self.setWindowTitle(KEYBOARD_TITLE)
        if popup:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.Popup
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.WindowDoesNotAcceptFocus
            )
        else:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.Tool
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.WindowDoesNotAcceptFocus
            )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._cancel_callback()
        event.accept()


class ModifierCancelOverlay(_CancelOverlaySegment):
    def __init__(self, cancel_callback: Callable[[], None], is_kde: bool = False, popup: bool = True) -> None:
        super().__init__(cancel_callback, popup=popup)
        # On KDE, aggressive compositor blur effects (e.g. better-blur-dx with
        # BlurNonMatching=true) force-blur this transparent full-screen overlay,
        # blurring the whole screen behind an open menu/accent strip. KDE instead
        # dismisses transient UI via clicks inside the keyboard window, so the
        # overlay never shows here and no blurrable surface is created.
        self._is_kde = is_kde
        self._segments = [_CancelOverlaySegment(cancel_callback, popup=popup) for _ in range(3)]

    def hide(self) -> None:
        super().hide()
        for segment in self._segments:
            segment.hide()

    def show_for_desktop(self) -> None:
        if self._is_kde:
            return
        self.setGeometry(desktop_geometry())
        self.show()
        self.raise_()
        for segment in self._segments:
            segment.hide()

    def show_around_rect(self, excluded_rect: QRect) -> None:
        if self._is_kde:
            return
        desktop = desktop_geometry()
        excluded = excluded_rect.intersected(desktop)
        if excluded.isEmpty():
            self.show_for_desktop()
            return

        rects = [
            QRect(desktop.left(), desktop.top(), desktop.width(), max(0, excluded.top() - desktop.top())),
            QRect(
                desktop.left(),
                excluded.bottom() + 1,
                desktop.width(),
                max(0, desktop.bottom() - excluded.bottom()),
            ),
            QRect(
                desktop.left(),
                excluded.top(),
                max(0, excluded.left() - desktop.left()),
                excluded.height(),
            ),
            QRect(
                excluded.right() + 1,
                excluded.top(),
                max(0, desktop.right() - excluded.right()),
                excluded.height(),
            ),
        ]
        windows = [self, *self._segments]
        for window, rect in zip(windows, rects):
            if rect.width() <= 0 or rect.height() <= 0:
                window.hide()
                continue
            window.setGeometry(rect)
            window.show()
            window.raise_()


class ClipboardBridge(QObject):
    """GUI-thread clipboard accessor that can be called safely from any thread.

    Instances must be created on the GUI thread (the default since QObject
    parent is None and the creating thread is the GUI thread in normal use).
    Worker-thread callables returned by :meth:`reader` and :meth:`writer`
    dispatch through Qt's blocking cross-thread connection so the actual
    QClipboard access always runs on the GUI thread.

    Both callables are safe to call from the GUI thread as well: when the
    caller's thread is already the GUI thread the slot is invoked directly
    to avoid deadlock.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    @Slot(result=str)
    def _read(self) -> str:
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            return ""
        return clipboard.text() or ""

    @Slot(str, result=bool)
    def _write(self, text: str) -> bool:
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            return False
        clipboard.setText(text)
        return True

    def reader(self) -> Callable[[], "str | None"]:
        """Return a callable suitable for YdotoolBackend clipboard_reader."""
        from PySide6.QtCore import QThread

        bridge = self

        def reader_callable() -> "str | None":
            if QThread.currentThread() is bridge.thread():
                result = bridge._read()
            else:
                result_holder: list[str] = []

                def _capture() -> None:
                    result_holder.append(bridge._read())

                _run_on_gui_thread_blocking(bridge, _capture)
                result = result_holder[0] if result_holder else ""
            return result if result else None

        return reader_callable

    def writer(self) -> Callable[[str], bool]:
        """Return a callable suitable for YdotoolBackend clipboard_writer."""
        from PySide6.QtCore import QThread

        bridge = self

        def writer_callable(text: str) -> bool:
            if QThread.currentThread() is bridge.thread():
                return bridge._write(text)
            result_holder: list[bool] = []

            def _capture() -> None:
                result_holder.append(bridge._write(text))

            _run_on_gui_thread_blocking(bridge, _capture)
            return result_holder[0] if result_holder else False

        return writer_callable


class _GuiThreadRunner(QObject):
    """Helper used by ClipboardBridge to execute a callable on the GUI thread."""

    def __init__(self, fn: Callable[[], None], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._fn = fn

    @Slot()
    def run(self) -> None:
        self._fn()


def _run_on_gui_thread_blocking(affinity_obj: QObject, fn: Callable[[], None]) -> None:
    """Run fn on the thread that owns affinity_obj, blocking until done."""
    from PySide6.QtCore import QMetaObject, Qt as _Qt

    runner = _GuiThreadRunner(fn)
    runner.moveToThread(affinity_obj.thread())
    QMetaObject.invokeMethod(runner, "run", _Qt.ConnectionType.BlockingQueuedConnection)
