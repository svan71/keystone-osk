# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from qt_window_test_helpers import *

def test_only_lockable_keys_get_purple_press_style() -> None:
    normal_press = key_paint_style(is_hovered=True, is_pressed=False, is_locked=False)
    locked_press = key_paint_style(is_hovered=True, is_pressed=True, is_locked=False)

    assert normal_press.border_color == "#f8f8f2"
    assert locked_press.border_color == "#bd93f9"

def test_full_numpad_secondary_labels_are_large_enough_to_read_under_numbers() -> None:
    full_scale = min(FULL_WINDOW_WIDTH / 1120, FULL_WINDOW_HEIGHT / 470)

    assert numpad_secondary_font_size("Home", full_scale) == 7
    assert numpad_secondary_font_size("▲", full_scale) == 7

def test_minimized_restore_icon_uses_dracula_purple() -> None:
    assert restore_icon_foreground_color().name() == "#bd93f9"

def test_minimized_restore_icon_uses_dracula_background() -> None:
    color = restore_icon_background_color()

    assert color.red() == 40
    assert color.green() == 42
    assert color.blue() == 54
    assert color.alpha() == 179

def test_shift_changes_symbol_key_main_label_to_shifted_output() -> None:
    key = PositionedKey("slash", "/", Rect(0, 0, 1, 1), shifted="?")

    display = key_label_display(key, {"Shift"})

    assert display.main == "?"
    assert display.alternate == "/"

def test_unshifted_symbol_key_keeps_shifted_output_as_corner_hint() -> None:
    key = PositionedKey("slash", "/", Rect(0, 0, 1, 1), shifted="?")

    display = key_label_display(key, set())

    assert display.main == "/"
    assert display.alternate == "?"

def test_shifted_symbol_corner_label_stays_readable_at_small_keyboard_size() -> None:
    style = shifted_label_style(scale=0.46)

    assert style.font_size >= 8
    assert style.font_weight == QFont.Weight.Medium
    assert style.left_inset > 3
    assert style.top_inset > 2
    assert style.main_left_bias >= 0.42

def test_full_keyboard_labels_stay_visually_compact() -> None:
    full_scale = min(FULL_WINDOW_WIDTH / 1120, FULL_WINDOW_HEIGHT / 470)

    full_left = key_label_font_size(PositionedKey("full-row1-q", "q", Rect(0, 0, 1, 22)), "q", full_scale)
    full_number = key_label_font_size(PositionedKey("full-row0-1", "1", Rect(0, 0, 1, 44)), "1", full_scale)
    full_function = key_label_font_size(PositionedKey("full-main-f1", "F1", Rect(0, 0, 1, 44), role="function"), "F1", full_scale)
    full_nav_long = key_label_font_size(
        PositionedKey("full-nav-prtsc", "PrtSc", Rect(0, 0, 1, 44), role="navigation"), "PrtSc", full_scale
    )
    full_numpad = key_label_font_size(PositionedKey("full-num", "Num", Rect(0, 0, 1, 22), role="numpad"), "Num", full_scale)
    full_nav = key_label_font_size(
        PositionedKey("full-insert", "Insert", Rect(0, 0, 1, 44), role="navigation"), "Insert", full_scale
    )
    full_numpad_enter = key_label_font_size(
        PositionedKey("full-numpad-enter", "Enter", Rect(0, 0, 44, 88), role="numpad"), "Enter", full_scale
    )

    assert full_left <= 9
    assert full_number <= 9
    assert full_function < full_left
    assert full_nav_long < full_left
    assert full_numpad_enter < full_left
    assert full_numpad < full_left
    assert full_nav < full_left

def test_full_shared_keys_use_separate_small_board_font_rules() -> None:
    scale = 0.51

    assert key_label_font_size(PositionedKey("full-row1-q", "q", Rect(0, 0, 1, 22)), "q", scale) < key_label_font_size(
        PositionedKey("row1-q", "q", Rect(0, 0, 1, 22)), "q", scale
    )
    assert key_label_font_size(
        PositionedKey("full-row1-tab", "Tab", Rect(0, 0, 1, 36), role="tab"), "Tab", scale
    ) < key_label_font_size(PositionedKey("row1-tab", "Tab", Rect(0, 0, 1, 36), role="tab"), "Tab", scale)

def test_full_keyboard_uses_uniform_label_font_across_key_roles() -> None:
    full_scale = min(FULL_WINDOW_WIDTH / 1120, FULL_WINDOW_HEIGHT / 470)
    main_keys = (
        PositionedKey("full-row0-1", "1", Rect(0, 0, 44, 42), shifted="!"),
        PositionedKey("full-numpad-1", "1", Rect(0, 0, 44, 42), role="numpad"),
    )
    action_keys = (
        PositionedKey("full-nav-prtsc", "PrtSc", Rect(0, 0, 44, 42), role="navigation"),
        PositionedKey("full-row1-tab", "Tab", Rect(0, 0, 44, 42), role="tab"),
        PositionedKey("full-bottom-ctrl", "Ctrl", Rect(0, 0, 44, 42), role="modifier"),
    )

    main_sizes = {key_label_font_size(key, key.label, full_scale) for key in main_keys}
    action_sizes = {key_label_font_size(key, key.label, full_scale) for key in action_keys}

    assert main_sizes == {8}
    assert action_sizes == {7}
    assert key_label_font_weight(main_keys[0], main_keys[0].label) == QFont.Weight.Medium
    assert key_label_font_weight(action_keys[0], action_keys[0].label) == QFont.Weight.Normal

def test_full_number_row_shifted_symbols_do_not_crowd_main_labels() -> None:
    full_scale = min(FULL_WINDOW_WIDTH / 1120, FULL_WINDOW_HEIGHT / 470)
    key = PositionedKey("full-row0-1", "1", Rect(0, 0, 44, 42), shifted="!")
    style = shifted_label_style(full_scale, is_full=True)

    assert style.font_size >= 9
    assert style.font_weight == QFont.Weight.Medium
    assert style.left_inset > 3
    assert style.top_inset > 1
    assert style.main_left_bias >= 0.42
    assert shifted_main_font_size(key, "1", full_scale) <= 10

def test_shifted_secondary_symbols_are_centered_in_hint_area(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    key = PositionedKey("row0-1", "1", Rect(0, 0, 44, 42), shifted="!")
    scale = 0.6
    style = shifted_label_style(scale)
    hint_rect = QRectF(style.left_inset, style.top_inset, key.rect.width * 0.40, key.rect.height * 0.40)

    assert hint_rect.left() > key.rect.left
    assert hint_rect.center().x() > key.rect.left + style.left_inset
    assert hint_rect.right() < key.rect.center_x

    window.close()

def test_full_shifted_punctuation_keys_are_large_enough_to_read() -> None:
    full_scale = min(FULL_WINDOW_WIDTH / 1120, FULL_WINDOW_HEIGHT / 470)
    style = shifted_label_style(full_scale, is_full=True)
    keys = (
        PositionedKey("full-row0-grave", "`", Rect(0, 0, 44, 42), shifted="~"),
        PositionedKey("full-row0-minus", "-", Rect(0, 0, 44, 42), shifted="_"),
        PositionedKey("full-row0-equals", "=", Rect(0, 0, 44, 42), shifted="+"),
        PositionedKey("full-row2-semicolon", ";", Rect(0, 0, 44, 42), shifted=":"),
        PositionedKey("full-row3-comma", ",", Rect(0, 0, 44, 42), shifted="<"),
        PositionedKey("full-row3-dot", ".", Rect(0, 0, 44, 42), shifted=">"),
        PositionedKey("full-row3-slash", "/", Rect(0, 0, 44, 42), shifted="?"),
    )

    assert style.font_size >= 9
    assert all(shifted_main_font_size(key, key.label, full_scale) >= 10 for key in keys)

def test_full_shifted_underscore_draws_inside_upper_left_key_area() -> None:
    full_scale = min(FULL_WINDOW_WIDTH / 1120, FULL_WINDOW_HEIGHT / 470)
    key = PositionedKey("full-row0-minus", "-", Rect(100, 50, 44, 42), shifted="_")

    line = shifted_underscore_line(key, full_scale)

    assert key.rect.left < line.x1() < key.rect.center_x
    assert key.rect.left < line.x2() < key.rect.center_x
    assert key.rect.top < line.y1() < key.rect.top + key.rect.height * 0.45
    assert line.y1() == line.y2()
    assert 7 <= line.length() <= key.rect.width * 0.24

def test_shifted_secondary_glyph_font_scales_down_with_key_height() -> None:
    # The corner hint glyph must shrink with the key (like shifted_main_font_size),
    # not stay floored at a fixed size — the fixed floor clipped at the smallest size.
    from keystone_osk import visual

    small = PositionedKey("full-row0-2", "2", Rect(0, 0, 44, 18), shifted="@")
    large = PositionedKey("full-row0-2", "2", Rect(0, 0, 120, 60), shifted="@")
    assert visual.shifted_secondary_font_size(small, 0.468) < visual.shifted_secondary_font_size(large, 1.19)


def test_shifted_secondary_glyph_font_stays_smaller_than_main_number() -> None:
    from keystone_osk import visual

    for key_h, scale in ((18, 0.468), (42, 0.894), (60, 1.19)):
        key = PositionedKey("full-row0-2", "2", Rect(0, 0, 44, key_h), shifted="@")
        assert visual.shifted_secondary_font_size(key, scale) < shifted_main_font_size(key, "2", scale)


def test_shifted_secondary_glyph_font_has_minimum_floor() -> None:
    from keystone_osk import visual

    tiny = PositionedKey("full-row0-2", "2", Rect(0, 0, 10, 6), shifted="@")
    assert visual.shifted_secondary_font_size(tiny, 0.1) >= 7


def test_full_number_row_secondary_glyph_fits_hint_rect_without_clipping(app) -> None:
    # Regression for the smallest full keyboard: the shifted symbol (@, #, $ ...)
    # was drawn into a hint rect shorter than its own font box, so drawText clipped it.
    from keystone_osk import visual
    from keystone_osk.geometry import build_full_key_geometry
    from keystone_osk.rendering import KEYBOARD_FONT_FAMILY
    from PySide6.QtGui import QFont, QFontMetricsF

    width, height = MIN_FULL_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
    geometry = build_full_key_geometry(width, height)
    render_scale = min(width / 1120, height / 470)
    number_keys = [k for k in geometry.keys if k.id.startswith("full-row0-") and k.shifted]
    assert number_keys  # sanity: we actually found the number row
    for key in number_keys:
        size = visual.shifted_secondary_font_size(key, render_scale)
        glyph_height = QFontMetricsF(QFont(KEYBOARD_FONT_FAMILY, size, QFont.Weight.Medium)).height()
        hint_rect = visual.shifted_secondary_hint_rect(key, render_scale)
        assert glyph_height <= hint_rect.height()


def test_full_backspace_glyph_is_smaller_than_previous_oversized_label() -> None:
    full_scale = min(FULL_WINDOW_WIDTH / 1120, FULL_WINDOW_HEIGHT / 470)

    backspace_size = key_label_font_size(
        PositionedKey("full-row0-backspace", "Backspace", Rect(0, 0, 72, 42), role="backspace"), "Backspace", full_scale
    )
    tab_size = key_label_font_size(PositionedKey("full-row1-tab", "Tab", Rect(0, 0, 44, 42), role="tab"), "Tab", full_scale)

    assert backspace_size == 8
    assert backspace_size > tab_size

def test_full_backspace_label_rect_sits_slightly_below_center_without_clipping() -> None:
    full_scale = min(FULL_WINDOW_WIDTH / 1120, FULL_WINDOW_HEIGHT / 470)
    key = PositionedKey("full-row0-backspace", "Backspace", Rect(100, 50, 72, 42), role="backspace")

    text_rect = key_label_text_rect(key, full_scale)

    assert text_rect.left() > key.rect.left
    assert text_rect.top() > key.rect.top
    assert text_rect.right() < key.rect.right
    assert text_rect.bottom() < key.rect.bottom
    assert abs(text_rect.center().x() - key.rect.center_x) < 0.01
    assert 1 <= text_rect.center().y() - key.rect.center_y <= 2

def test_compact_backspace_glyph_is_smaller_and_sits_slightly_below_center() -> None:
    scale = 0.6
    key = PositionedKey("row0-backspace", "Backspace", Rect(100, 50, 68, 36), role="backspace")

    backspace_size = key_label_font_size(key, "⌫", scale)
    text_rect = key_label_text_rect(key, scale)

    assert backspace_size == 10
    assert text_rect.left() > key.rect.left
    assert text_rect.right() < key.rect.right
    assert 1 <= text_rect.center().y() - key.rect.center_y <= 2

def test_action_key_labels_are_a_tad_smaller_on_both_boards() -> None:
    compact_scale = 0.6
    full_scale = min(FULL_WINDOW_WIDTH / 1120, FULL_WINDOW_HEIGHT / 470)

    assert key_label_font_size(PositionedKey("row1-tab", "Tab", Rect(0, 0, 1, 36), role="tab"), "Tab", compact_scale) <= 13
    assert key_label_font_size(PositionedKey("row2-caps", "Caps", Rect(0, 0, 1, 36), role="caps"), "Caps", compact_scale) <= 13
    assert key_label_font_size(PositionedKey("row3-shift", "Shift", Rect(0, 0, 1, 36), role="shift"), "Shift", compact_scale) <= 13
    assert key_label_font_size(PositionedKey("full-row1-tab", "Tab", Rect(0, 0, 1, 44), role="tab"), "Tab", full_scale) <= 12
    assert key_label_font_size(PositionedKey("full-row2-caps", "Caps", Rect(0, 0, 1, 44), role="caps"), "Caps", full_scale) <= 12

def test_caps_only_uppercases_letters_without_shifting_symbols() -> None:
    letter = PositionedKey("a", "a", Rect(0, 0, 1, 1))
    symbol = PositionedKey("slash", "/", Rect(0, 0, 1, 1), shifted="?")

    assert key_label_display(letter, {"Caps"}).main == "A"
    assert key_label_display(symbol, {"Caps"}).main == "/"

def test_caps_and_shift_make_letters_lowercase_but_symbols_shifted() -> None:
    letter = PositionedKey("a", "a", Rect(0, 0, 1, 1))
    symbol = PositionedKey("slash", "/", Rect(0, 0, 1, 1), shifted="?")

    assert key_label_display(letter, {"Caps", "Shift"}).main == "a"
    assert key_label_display(symbol, {"Caps", "Shift"}).main == "?"
