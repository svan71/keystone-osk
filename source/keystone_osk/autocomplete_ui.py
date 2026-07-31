# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import re
import sys

from keystone_osk.autocomplete import completion_suffix, save_engine
from keystone_osk.geometry import PositionedKey, Rect
from keystone_osk.input_model import PUNCTUATION_AFTER_AUTOSPACE


def log_status(message: str) -> None:
    try:
        print(message, file=sys.stderr, flush=True)
    except OSError:
        pass


class AutocompleteUIMixin:
    def _record_autocomplete_key(self, key: PositionedKey) -> None:
        if key.label == "Backspace":
            self._last_space_was_auto_suggestion = False
            self._delete_autocomplete_backward()
            self._sync_current_word_from_buffer()
            self._refresh_suggestions()
            return
        if key.label == "Delete":
            self._last_space_was_auto_suggestion = False
            self._delete_autocomplete_forward()
            self._sync_current_word_from_buffer()
            self._refresh_suggestions()
            return
        if key.label in {"Left", "Right", "Home", "End"}:
            self._move_autocomplete_cursor(key.label)
            self._sync_current_word_from_buffer()
            self._refresh_suggestions()
            return
        if key.label in {"Up", "Down", "PgUp", "PgDn"}:
            self._clear_autocomplete_context()
            self._refresh_suggestions()
            return
        if key.label in {"Space", "Enter", "Tab"}:
            self._ensure_current_word_in_buffer()
            self._finish_autocomplete_word()
            self._insert_autocomplete_text(" ")
            if key.label in {"Space", "Enter"}:
                self._last_space_was_auto_suggestion = False
            return
        if len(key.label) == 1 and key.label.isalpha():
            self._insert_autocomplete_text(key.label.lower())
            self._capitalize_next_letter = False
            self._last_space_was_auto_suggestion = False
            self._refresh_suggestions()
            return
        if key.label in PUNCTUATION_AFTER_AUTOSPACE:
            self._insert_autocomplete_text(key.label)
            self._capitalize_next_letter = key.label in {".", "?", "!"}
            self._last_space_was_auto_suggestion = False
            self._refresh_suggestions()
            return
        if len(key.label) == 1:
            self._finish_autocomplete_word()
            self._insert_autocomplete_text(" ")
            self._last_space_was_auto_suggestion = False

    def _finish_autocomplete_word(self) -> None:
        if self._current_word:
            self.autocomplete.observe_typed_word(self._current_word)
            self._save_autocomplete()
        self._sync_current_word_from_buffer()
        self._refresh_suggestions()

    def _insert_autocomplete_text(self, text: str) -> None:
        before = self._autocomplete_buffer[: self._autocomplete_cursor]
        after = self._autocomplete_buffer[self._autocomplete_cursor :]
        self._autocomplete_buffer = before + text + after
        self._autocomplete_cursor += len(text)
        if len(self._autocomplete_buffer) > 240:
            overflow = len(self._autocomplete_buffer) - 240
            self._autocomplete_buffer = self._autocomplete_buffer[overflow:]
            self._autocomplete_cursor = max(0, self._autocomplete_cursor - overflow)
        self._sync_current_word_from_buffer()

    def _delete_autocomplete_backward(self) -> None:
        if self._autocomplete_cursor <= 0:
            return
        self._autocomplete_buffer = (
            self._autocomplete_buffer[: self._autocomplete_cursor - 1] + self._autocomplete_buffer[self._autocomplete_cursor :]
        )
        self._autocomplete_cursor -= 1

    def _delete_autocomplete_forward(self) -> None:
        if self._autocomplete_cursor >= len(self._autocomplete_buffer):
            return
        self._autocomplete_buffer = (
            self._autocomplete_buffer[: self._autocomplete_cursor] + self._autocomplete_buffer[self._autocomplete_cursor + 1 :]
        )

    def _move_autocomplete_cursor(self, label: str) -> None:
        if label == "Left":
            self._autocomplete_cursor = max(0, self._autocomplete_cursor - 1)
        elif label == "Right":
            self._autocomplete_cursor = min(len(self._autocomplete_buffer), self._autocomplete_cursor + 1)
        elif label == "Home":
            self._autocomplete_cursor = 0
        elif label == "End":
            self._autocomplete_cursor = len(self._autocomplete_buffer)

    def _clear_autocomplete_context(self) -> None:
        self._current_word = ""
        self._autocomplete_buffer = ""
        self._autocomplete_cursor = 0
        self._last_space_was_auto_suggestion = False

    def _cancel_autocomplete_suggestions(self) -> None:
        self._suggestions = ()
        self.update()

    def _ensure_current_word_in_buffer(self) -> None:
        before_cursor = self._autocomplete_buffer[: self._autocomplete_cursor]
        if self._current_word and not before_cursor.endswith(self._current_word):
            self._insert_autocomplete_text(self._current_word)

    def _sync_current_word_from_buffer(self) -> None:
        match = re.search(r"[A-Za-z]+$", self._autocomplete_buffer[: self._autocomplete_cursor])
        self._current_word = match.group(0).lower() if match else ""

    def _clean_auto_suggestion_space_before_punctuation(self, output_text: str) -> None:
        if output_text not in PUNCTUATION_AFTER_AUTOSPACE or not self._last_space_was_auto_suggestion:
            return
        try:
            self.backend.press_key(PositionedKey("backspace", "Backspace", Rect(0, 0, 1, 1), role="backspace"))
            self._delete_autocomplete_backward()
        except Exception as exc:
            log_status(f"ydotool autocomplete punctuation cleanup failed for {output_text}: {exc}")

    def _refresh_suggestions(self) -> None:
        if not self._suggestions_enabled or self._has_one_shot_modifiers():
            self._suggestions = ()
        else:
            self._suggestions = self.autocomplete.suggestions(self._current_word, limit=self._suggestion_limit())
        self.update()

    def _suggestion_limit(self) -> int:
        return 5 if self._keyboard_mode == "full" else 4

    def _accept_suggestion(self, suggestion: str) -> None:
        suffix = completion_suffix(suggestion, self._current_word)
        self._ensure_current_word_in_buffer()
        for char in suffix:
            try:
                self.backend.press_key(PositionedKey(char, char, Rect(0, 0, 1, 1)))
            except Exception as exc:
                log_status(f"ydotool autocomplete output failed for {suggestion}: {exc}")
                return
        try:
            self.backend.press_key(PositionedKey("space", "Space", Rect(0, 0, 1, 1), role="space"))
        except Exception as exc:
            log_status(f"ydotool autocomplete output failed for {suggestion}: {exc}")
            return
        self._insert_autocomplete_text(suffix + " ")
        self._last_space_was_auto_suggestion = True
        self._capitalize_next_letter = False
        self.autocomplete.boost_word(suggestion)
        self._save_autocomplete()
        self._refresh_suggestions()

    def _toggle_emoji_picker(self) -> None:
        from PySide6.QtCore import QTimer
        self._app_menu.hide()
        self._emoji_picker_visible = not self._emoji_picker_visible
        self._emoji_rects = ()
        self._suggestions = ()
        self.update()
        if self._emoji_picker_visible:
            self._modifier_cancel_overlay.hide()
            QTimer.singleShot(0, self._show_emoji_cancel_overlay)
        else:
            self._sync_modifier_cancel_overlay()

    def _type_emoji(self, emoji: str) -> None:
        try:
            self.backend.type_text(emoji)
        except Exception as exc:
            log_status(f"ydotool emoji output failed for {emoji}: {exc}")
            return
        self._clear_autocomplete_context()
        self._refresh_suggestions()

    def _toggle_learning_enabled(self) -> None:
        self.autocomplete.learning_enabled = not self.autocomplete.learning_enabled
        self._refresh_learning_action()
        self._save_autocomplete()

    def _toggle_suggestions_enabled(self) -> None:
        self._suggestions_enabled = not self._suggestions_enabled
        if self._persist_window_state:
            self._save_window_state()
        self._refresh_suggestions_action()
        self._refresh_suggestions()

    def _toggle_auto_cap_enabled(self) -> None:
        self._auto_cap_enabled = not self._auto_cap_enabled
        if self._persist_window_state:
            self._save_window_state()
        self._refresh_auto_cap_action()

    def _clear_learned_words(self) -> None:
        self.autocomplete.clear_learned_words()
        self._refresh_suggestions()
        self._save_autocomplete()

    def _refresh_suggestions_action(self) -> None:
        self._suggestions_action.setText("Turn Suggestions Off" if self._suggestions_enabled else "Turn Suggestions On")

    def _refresh_learning_action(self) -> None:
        self._learning_action.setText("Learning: On" if self.autocomplete.learning_enabled else "Learning: Off")

    def _refresh_auto_cap_action(self) -> None:
        self._auto_cap_action.setText("Auto-Cap: On" if self._auto_cap_enabled else "Auto-Cap: Off")

    def _save_autocomplete(self) -> None:
        # Debounce: word completions can fire several saves in quick succession
        # (Space/Enter/Tab, accepted suggestion, menu toggles). Coalesce them so
        # the synchronous disk write does not run on the UI thread per keystroke.
        if self._persist_autocomplete:
            self._autocomplete_save_pending = True
            self._autocomplete_save_timer.start()

    def _flush_autocomplete_save(self) -> None:
        # Runs both as the debounce timeout and explicitly on shutdown.
        self._autocomplete_save_timer.stop()
        if self._persist_autocomplete and self._autocomplete_save_pending:
            self._autocomplete_save_pending = False
            save_engine(self.autocomplete)
