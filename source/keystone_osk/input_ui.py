from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from keystone_osk.constants import DEBUG_PREFIX
from keystone_osk.geometry import PositionedKey
from keystone_osk.accents import accent_variants_for
from keystone_osk.input_model import (
    COMMAND_MODIFIERS,
    LOCK_KEYS,
    ONE_SHOT_MODIFIERS,
    active_modifiers_for,
    is_repeatable_key,
    output_key_for,
    output_text_for,
)

KEY_REPEAT_DELAY_MS = 400
ACCENT_HOLD_DELAY_MS = 500
KEY_REPEAT_INTERVAL_MS = 60


def log_status(message: str) -> None:
    try:
        print(message, file=sys.stderr, flush=True)
    except OSError:
        pass


class InputUIMixin:
    def _press_key(self, key: PositionedKey) -> None:
        output_key = self._output_key_for(key)
        modifiers = self._active_modifiers_for(output_key)
        try:
            if modifiers:
                self._log_key_debug(f"{DEBUG_PREFIX} press {'+'.join((*modifiers, output_key.label))}")
                self.backend.press_key_with_modifiers(output_key, modifiers)
                return
            self._log_key_debug(f"{DEBUG_PREFIX} press {output_key.label}")
            self.backend.press_key(output_key)
        except Exception as exc:
            log_status(f"ydotool key output failed for {output_key.label}: {exc}")

    def _output_key_for(self, key: PositionedKey) -> PositionedKey:
        return output_key_for(key, self._locked_key_labels, self._numpad_output_mode)

    def _deliver_key_press(self, key: PositionedKey) -> None:
        self._press_key(key)

    def _deliver_and_record_key_press(self, key: PositionedKey) -> None:
        self._deliver_key_press(key)
        self._record_autocomplete_key(self._output_key_for(key))

    def _queue_key_press(self, key: PositionedKey, clear_one_shot_modifiers: bool = True) -> None:
        self._log_key_debug(f"{DEBUG_PREFIX} queue {key.label}")
        if key.role == "snippets":
            self._show_snippets_menu()
            QTimer.singleShot(90, self._clear_pressed_key)
            return
        if key.label in LOCK_KEYS:
            was_latched = key.label in self._locked_key_labels
            self._toggle_lock_state(key)
            if key.label == "Num":
                # Don't emit a raw NumLock keycode (it would toggle the system
                # NumLock and fight ensure_numlock_on). In true-keypad mode the
                # keypad emits real KP scancodes, which only produce digits when
                # system NumLock is on, so sync it on when the Num latch turns on.
                if self._numpad_output_mode == "true-keypad" and "Num" in self._locked_key_labels:
                    self.backend.ensure_numlock_on()
            elif key.label in COMMAND_MODIFIERS and was_latched:
                try:
                    self._log_key_debug(f"{DEBUG_PREFIX} press {key.label}")
                    self.backend.press_key(key)
                except Exception as exc:
                    log_status(f"ydotool key output failed for {key.label}: {exc}")
            self.update()
            # No processEvents() here: re-entering the event loop let a second
            # rapid tap toggle the latch on then immediately off (dropped Shift
            # on touchscreens). update() already schedules the repaint.
            QTimer.singleShot(90, self._clear_pressed_key)
            return
        active_one_shot_modifiers = self._locked_key_labels & ONE_SHOT_MODIFIERS
        self._toggle_lock_state(key)
        output_text = output_text_for(key, self._locked_key_labels)
        self._clean_auto_suggestion_space_before_punctuation(output_text)
        self._deliver_and_record_key_press(key)
        if clear_one_shot_modifiers or bool(active_one_shot_modifiers - {"Shift"}):
            self._clear_one_shot_modifiers()
        QTimer.singleShot(180 if self._is_kde else 90, self._clear_pressed_key)

    def _start_key_repeat(self, key: PositionedKey) -> None:
        self._stop_key_repeat(clear_modifiers=False)
        if not is_repeatable_key(key):
            return
        self._repeat_key = key
        self._repeat_timer.setSingleShot(True)
        self._repeat_timer.start(KEY_REPEAT_DELAY_MS)

    def _stop_key_repeat(self, clear_modifiers: bool = True) -> None:
        had_repeat_key = self._repeat_key is not None
        self._repeat_timer.stop()
        self._repeat_key = None
        if clear_modifiers and had_repeat_key:
            self._clear_one_shot_modifiers()

    def _repeat_held_key(self) -> None:
        if self._repeat_key is None:
            return
        self._deliver_and_record_key_press(self._repeat_key)
        self._repeat_timer.setSingleShot(False)
        self._repeat_timer.start(KEY_REPEAT_INTERVAL_MS)

    def _toggle_lock_state(self, key: PositionedKey) -> None:
        if key.label not in LOCK_KEYS:
            return
        if key.label in self._locked_key_labels:
            self._locked_key_labels.remove(key.label)
        else:
            self._locked_key_labels.add(key.label)
        self._sync_modifier_cancel_overlay()

    def _active_modifiers_for(self, key: PositionedKey) -> tuple[str, ...]:
        return active_modifiers_for(
            key,
            self._locked_key_labels,
            auto_cap_enabled=self._auto_cap_enabled,
            capitalize_next_letter=self._capitalize_next_letter,
        )

    def _clear_one_shot_modifiers(self) -> None:
        self._locked_key_labels.difference_update(ONE_SHOT_MODIFIERS)
        self._sync_modifier_cancel_overlay()
        self.update()

    def _has_one_shot_modifiers(self) -> bool:
        return bool(self._locked_key_labels & ONE_SHOT_MODIFIERS)

    def _clear_modifiers_on_background_click(self) -> None:
        # A click on a non-key area of the keyboard (titlebar text, empty gaps,
        # resize edge). On GNOME, latched modifiers — including Caps — are
        # cancelled by an off-screen click via the cancel overlay, so an
        # in-keyboard non-key click only clears one-shot modifiers. On KDE the
        # overlay is suppressed (it would be force-blurred), so the in-keyboard
        # non-key click is the cancel gesture and must also release Caps.
        if self._is_kde:
            self._clear_cancelable_modifiers()
        else:
            self._clear_one_shot_modifiers()

    def _begin_accent_press(self, key) -> None:
        self._accent_pending_key = key
        self._accent_strip_open = False
        self._accent_hold_timer.setSingleShot(True)
        self._accent_hold_timer.start(ACCENT_HOLD_DELAY_MS)

    def _open_accent_strip(self) -> None:
        if self._accent_pending_key is None:
            return
        uppercase = ("Caps" in self._locked_key_labels) ^ ("Shift" in self._locked_key_labels)
        variants = accent_variants_for(self._accent_pending_key.label, uppercase)
        if not variants:
            return
        from PySide6.QtCore import QRect
        from keystone_osk.accent_ui import AccentStrip
        from keystone_osk.theme import theme_palette

        palette = theme_palette(self._theme_name)
        self._accent_strip = AccentStrip(variants, palette, self._pick_accent)

        key_rect = self._accent_pending_key.rect
        key_global_rect = QRect(
            int(key_rect.left + self.geometry().left()),
            int(key_rect.top + self.geometry().top()),
            int(key_rect.width),
            int(key_rect.height),
        )
        screen = self.screen() or QApplication.instance().primaryScreen()
        screen_rect = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)

        self._accent_strip.show_above(key_global_rect, screen_rect)
        self._accent_strip_open = True

        if "Shift" in self._locked_key_labels and uppercase:
            self._locked_key_labels.discard("Shift")
            self._sync_modifier_cancel_overlay()
            self.update()

        self._modifier_cancel_overlay.hide()
        QTimer.singleShot(0, self._show_accent_cancel_overlay)

    def _show_accent_cancel_overlay(self) -> None:
        if self._accent_strip is None or not self._accent_strip.isVisible():
            return
        strip_rect = self._accent_strip.geometry()
        self._modifier_cancel_overlay.show_around_rect(strip_rect)
        self.raise_()
        # Re-raise the strip above the keyboard last, exactly like the snippets
        # path re-raises its menu after self.raise_().
        self._accent_strip.raise_()

    def _pick_accent(self, char: str) -> None:
        if char:
            self.backend.type_unicode_text(char)
        self._dismiss_accent_strip()

    def _dismiss_accent_strip(self) -> None:
        strip = getattr(self, '_accent_strip', None)
        if strip is not None:
            strip.hide()
            strip.deleteLater()
            self._accent_strip = None
        self._accent_strip_open = False
        self._accent_pending_key = None
        self._sync_modifier_cancel_overlay()

    def _log_key_debug(self, message: str) -> None:
        if self._debug_keys:
            log_status(message)
