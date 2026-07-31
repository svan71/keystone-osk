# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from qt_window_test_helpers import *

from PySide6.QtCore import QPointF


def _a_key():
    return PositionedKey("row0-a", "a", Rect(10, 100, 50, 40), role="key")


def _b_key():
    return PositionedKey("row0-b", "b", Rect(10, 100, 50, 40), role="key")


def test_hold_accent_letter_shows_strip_with_variants(app):
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._begin_accent_press(_a_key())
    window._open_accent_strip()

    assert window._accent_strip_open is True
    assert window._accent_strip is not None
    strip = window._accent_strip
    assert strip.isVisible()
    assert len(strip._cell_rects) == 6

    window._dismiss_accent_strip()
    window.close()


def test_tap_strip_cell_types_accent_char_and_closes(app):
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._begin_accent_press(_a_key())
    window._open_accent_strip()

    strip = window._accent_strip
    first_cell_center = strip._cell_rects[0].center()
    strip.mousePressEvent(type('E', (), {
        'button': lambda self: Qt.MouseButton.LeftButton,
        'position': lambda self: QPointF(first_cell_center),
    })())

    assert backend.unicode_text_calls == ["à"]
    assert window._accent_strip_open is False
    assert window._accent_strip is None

    window.close()


def test_quick_tap_emits_base_letter_no_strip(app):
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend
    window._auto_cap_enabled = False
    window._capitalize_next_letter = False

    window._begin_accent_press(_a_key())
    window.mouseReleaseEvent(None)

    assert backend.calls == [("a", ())]
    assert window._accent_strip_open is False
    assert window._accent_pending_key is None
    assert window._accent_strip is None

    window.close()


def test_non_accent_letter_emits_on_press_unchanged(app):
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend
    window._auto_cap_enabled = False
    window._capitalize_next_letter = False

    window._queue_key_press(_b_key())
    assert backend.calls == [("b", ())]
    assert window._accent_strip_open is False

    window.close()


def test_shift_hold_a_shows_uppercase_variants(app):
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._locked_key_labels.add("Shift")
    window._begin_accent_press(_a_key())
    window._open_accent_strip()

    strip = window._accent_strip
    assert strip is not None
    assert strip._variants[0] == "À"

    window._dismiss_accent_strip()
    window.close()


def test_ctrl_press_a_no_strip_normal_emit(app):
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend
    window._auto_cap_enabled = False
    window._capitalize_next_letter = False

    window._locked_key_labels.add("Ctrl")
    hit = _a_key()
    from keystone_osk.input_model import is_accent_press_candidate

    assert is_accent_press_candidate(hit, window._locked_key_labels) is False
    window._queue_key_press(hit)
    assert backend.calls == [("a", ("Ctrl",))]

    window.close()


def test_accent_strip_is_popup_so_it_stacks_above_keyboard(app):
    # Regression: a Tool window renders BEHIND the always-on-top keyboard and the
    # cancel-overlay's pointer grab swallows its taps. It must be a Popup, like
    # the snippets menu and the ModifierCancelOverlay segments.
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._begin_accent_press(_a_key())
    window._open_accent_strip()

    assert bool(window._accent_strip.windowFlags() & Qt.WindowType.Popup)

    window._dismiss_accent_strip()
    window.close()


def test_accent_cells_are_in_local_widget_coordinates(app):
    # Regression: cell rects must be in the strip's LOCAL space (paintEvent and
    # mousePressEvent both work locally). Global coords paint off-canvas and
    # break hit-testing — the strip renders as an empty box.
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._begin_accent_press(_a_key())
    window._open_accent_strip()

    strip = window._accent_strip
    local_bounds = strip.rect()
    assert strip._cell_rects
    for cell in strip._cell_rects:
        assert local_bounds.contains(cell), f"cell {cell} outside local widget {local_bounds}"

    window._dismiss_accent_strip()
    window.close()


def test_outside_click_dismisses_strip_nothing_typed(app):
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._begin_accent_press(_a_key())
    window._open_accent_strip()
    assert window._accent_strip_open is True

    window._handle_outside_overlay_click()

    assert backend.unicode_text_calls == []
    assert window._accent_strip_open is False
    assert window._accent_strip is None

    window.close()
