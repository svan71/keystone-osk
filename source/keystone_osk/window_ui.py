# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QPoint, QTimer, Qt

from keystone_osk.input_model import ONE_SHOT_MODIFIERS, is_accent_press_candidate, is_repeatable_key
from keystone_osk.platform import is_kde_session, should_use_manual_resize
from keystone_osk.visual import keyboard_resize_edges_at

EMOJI_RELEASE_DELAY_MS = 80
CONTROL_HIT_SLOP = 4


class WindowInteractionMixin:
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position()
        emoji = self._emoji_at(pos.x(), pos.y())
        if emoji is not None:
            self._pending_emoji = emoji
            return
        if self._emoji_picker_visible and self._emoji_rects:
            self._emoji_picker_visible = False
            self.update()
            self._sync_modifier_cancel_overlay()
            return
        suggestion = self._suggestion_at(pos.x(), pos.y())
        if suggestion is not None:
            self._accept_suggestion(suggestion)
            return
        if self._close_rect.contains(pos):
            self._hide_keyboard_keep_top_icon()
            return
        if self._minimize_rect.contains(pos):
            self._minimize_to_panel()
            return
        if self._mode_toggle_rect.contains(pos):
            self._toggle_keyboard_mode()
            return
        if self._menu_rect.contains(pos):
            self._show_app_menu()
            return
        hit = self._key_at(pos.x(), pos.y()) if not self._is_collapsed else None
        if hit is not None:
            self._hovered_key_id = hit.id
            self._pressed_key_id = hit.id
            if is_accent_press_candidate(hit, self._locked_key_labels):
                self._begin_accent_press(hit)
                self.update()
                return
            should_repeat = is_repeatable_key(hit) and not bool((self._locked_key_labels & ONE_SHOT_MODIFIERS) - {"Shift"})
            self._queue_key_press(hit, clear_one_shot_modifiers=not is_repeatable_key(hit))
            if should_repeat:
                self._start_key_repeat(hit)
            self.update()
            return
        resize_edges = self._resize_edges_at(pos.x(), pos.y())
        if resize_edges is not None:
            self._clear_modifiers_on_background_click()
            if self._begin_system_resize(resize_edges):
                self._system_window_action_active = True
            else:
                self._begin_manual_resize(resize_edges, event.globalPosition().toPoint())
            return
        self._clear_modifiers_on_background_click()
        if self._begin_system_move():
            self._system_window_action_active = True
        else:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._active_resize_edges is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._apply_manual_resize(event.globalPosition().toPoint())
            return
        pos = event.position()
        if self._drag_offset is None:
            self._update_resize_cursor(pos.x(), pos.y())
        hit = self._key_at(pos.x(), pos.y())
        next_hovered = hit.id if hit is not None else None
        if next_hovered != self._hovered_key_id:
            self._hovered_key_id = next_hovered
            self.update()
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        del event
        if getattr(self, '_accent_pending_key', None) is not None:
            if not self._accent_strip_open:
                self._accent_hold_timer.stop()
                self._queue_key_press(self._accent_pending_key, clear_one_shot_modifiers=True)
            self._accent_pending_key = None
            if self._pressed_key_id is not None:
                self._pressed_key_id = None
                self.update()
            return
        pending_emoji = self._pending_emoji
        window_state_changed = self._drag_offset is not None or self._active_resize_edges is not None or self._system_window_action_active
        self._pending_emoji = None
        self._stop_key_repeat()
        self._pending_key = None
        if self._pressed_key_id is not None:
            self._pressed_key_id = None
            self.update()
        self._drag_offset = None
        self._active_resize_edges = None
        self._system_window_action_active = False
        if window_state_changed:
            self._save_window_state()
        if pending_emoji is not None:
            self.update()
            QTimer.singleShot(EMOJI_RELEASE_DELAY_MS, lambda value=pending_emoji: self._type_emoji(value))

    def leaveEvent(self, event) -> None:  # noqa: N802
        del event
        self.unsetCursor()
        if self._hovered_key_id is not None:
            self._hovered_key_id = None
            self.update()
        if self.isVisible() and self._has_cancelable_modifiers():
            self._modifier_cancel_overlay.show_around_rect(self.frameGeometry())
            self.raise_()
            return
        if self._suggestions:
            self._cancel_autocomplete_suggestions()

    def _resize_edges_at(self, x: float, y: float):
        if self._is_collapsed:
            return None
        pos = QPoint(int(x), int(y))
        for rect in (self._close_rect, self._minimize_rect, self._mode_toggle_rect, self._menu_rect):
            if rect.adjusted(
                -CONTROL_HIT_SLOP,
                -CONTROL_HIT_SLOP,
                CONTROL_HIT_SLOP,
                CONTROL_HIT_SLOP,
            ).contains(pos):
                return None
        return keyboard_resize_edges_at(self.width(), self.height(), x, y, self._resize_margin)

    def _begin_system_move(self) -> bool:
        if is_kde_session():
            return False
        handle = self.windowHandle()
        if handle is None:
            return False
        return bool(handle.startSystemMove())

    def _begin_system_resize(self, edges) -> bool:
        if should_use_manual_resize(edges):
            return False
        handle = self.windowHandle()
        if handle is None:
            return False
        return bool(handle.startSystemResize(edges))

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
        min_width = self.minimumWidth()
        min_height = self.minimumHeight()

        if self._active_resize_edges & Qt.Edge.LeftEdge:
            width = origin.width() - delta.x()
            if width < min_width:
                width = min_width
                x = origin.right() - min_width + 1
            else:
                x = origin.x() + delta.x()
        if self._active_resize_edges & Qt.Edge.RightEdge:
            width = max(min_width, origin.width() + delta.x())
        if self._active_resize_edges & Qt.Edge.TopEdge:
            height = origin.height() - delta.y()
            if height < min_height:
                height = min_height
                y = origin.bottom() - min_height + 1
            else:
                y = origin.y() + delta.y()
        if self._active_resize_edges & Qt.Edge.BottomEdge:
            height = max(min_height, origin.height() + delta.y())

        self.setGeometry(x, y, width, height)

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
