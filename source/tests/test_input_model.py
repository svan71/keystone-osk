from qt_window_test_helpers import *

def test_numpad_number_sends_number_when_num_is_locked(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend
    window._locked_key_labels = {"Num"}

    window._queue_key_press(PositionedKey("full-numpad-7", "7", Rect(0, 0, 1, 1), shifted="Home", output="KP7", role="numpad"))

    assert backend.calls == [("7", ())]

def test_numpad_number_sends_navigation_when_num_is_unlocked(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._queue_key_press(
        PositionedKey("full-numpad-7", "7", Rect(0, 0, 1, 1), shifted="Home", output="KP7", shifted_output="Home", role="numpad")
    )

    assert backend.calls == [("Home", ())]

def test_numpad_arrow_glyph_sends_navigation_when_num_is_unlocked(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._queue_key_press(
        PositionedKey("full-numpad-8", "8", Rect(0, 0, 1, 1), shifted="▲", output="KP8", shifted_output="Up", role="numpad")
    )

    assert backend.calls == [("Up", ())]

def test_numpad_labels_flip_when_num_is_unlocked() -> None:
    display = key_label_display(PositionedKey("full-numpad-7", "7", Rect(0, 0, 1, 1), shifted="Home", role="numpad"), set())

    assert display.main == "Home"
    assert display.alternate == "7"

def test_numpad_labels_keep_numbers_primary_when_num_is_locked() -> None:
    display = key_label_display(
        PositionedKey("full-numpad-7", "7", Rect(0, 0, 1, 1), shifted="Home", role="numpad"), {"Num"}
    )

    assert display.main == "7"
    assert display.alternate == "Home"

def test_delete_key_displays_as_del() -> None:
    display = key_label_display(PositionedKey("delete", "Delete", Rect(0, 0, 1, 1), role="delete"), set())

    assert display.main == "Del"


def _np(name, label, output, shifted="", shifted_output=""):
    return PositionedKey(f"full-numpad-{name}", label, Rect(0, 0, 1, 1),
                         shifted=shifted, output=output, shifted_output=shifted_output, role="numpad")


def _emit(key, locked, mode):
    return output_key_for(key, locked, numpad_output_mode=mode).label


def test_reliable_mode_numpad_7_sends_main_row_7() -> None:
    assert _emit(_np("7", "7", "KP7", shifted="Home", shifted_output="Home"), {"Num"}, "reliable") == "7"

def test_reliable_mode_numpad_dot_sends_main_row_dot() -> None:
    assert _emit(_np("dot", ".", "KPDot", shifted="Del", shifted_output="Delete"), {"Num"}, "reliable") == "."

def test_reliable_mode_numpad_slash_sends_kpslash() -> None:
    assert _emit(_np("slash", "/", "KPSlash"), {"Num"}, "reliable") == "KPSlash"

def test_reliable_mode_numpad_star_sends_kpstar() -> None:
    assert _emit(_np("star", "*", "KPStar"), {"Num"}, "reliable") == "KPStar"

def test_reliable_mode_numpad_minus_sends_kpminus() -> None:
    assert _emit(_np("minus", "-", "KPMinus"), {"Num"}, "reliable") == "KPMinus"

def test_reliable_mode_numpad_plus_sends_kpplus() -> None:
    assert _emit(_np("plus", "+", "KPPlus"), {"Num"}, "reliable") == "KPPlus"

def test_reliable_mode_numpad_enter_sends_kpenter() -> None:
    assert _emit(_np("enter", "Enter", "KPEnter"), {"Num"}, "reliable") == "KPEnter"

def test_true_keypad_mode_numpad_7_sends_kp7() -> None:
    assert _emit(_np("7", "7", "KP7", shifted="Home", shifted_output="Home"), {"Num"}, "true-keypad") == "KP7"

def test_true_keypad_mode_numpad_dot_sends_kpdot() -> None:
    assert _emit(_np("dot", ".", "KPDot", shifted="Del", shifted_output="Delete"), {"Num"}, "true-keypad") == "KPDot"

def test_true_keypad_mode_numpad_enter_sends_kpenter() -> None:
    assert _emit(_np("enter", "Enter", "KPEnter"), {"Num"}, "true-keypad") == "KPEnter"

def test_numpad_7_sends_home_when_numlock_off() -> None:
    assert _emit(_np("7", "7", "KP7", shifted="Home", shifted_output="Home"), set(), "reliable") == "Home"

def test_numpad_0_sends_insert_when_numlock_off() -> None:
    assert _emit(_np("0", "0", "KP0", shifted="Ins", shifted_output="Insert"), set(), "true-keypad") == "Insert"

def test_numpad_dot_sends_delete_when_numlock_off() -> None:
    assert _emit(_np("dot", ".", "KPDot", shifted="Del", shifted_output="Delete"), set(), "reliable") == "Delete"


# -- is_accent_press_candidate tests --

from keystone_osk.input_model import COMMAND_MODIFIERS, is_accent_press_candidate


def test_is_accent_candidate_true_for_accent_letter_no_modifiers():
    key = PositionedKey("row0-a", "a", Rect(0, 0, 1, 1), role="key")
    assert is_accent_press_candidate(key, set()) is True


def test_is_accent_candidate_true_for_accent_letter_with_shift():
    key = PositionedKey("row0-a", "a", Rect(0, 0, 1, 1), role="key")
    assert is_accent_press_candidate(key, {"Shift"}) is True


def test_is_accent_candidate_true_for_accent_letter_with_caps():
    key = PositionedKey("row0-a", "a", Rect(0, 0, 1, 1), role="key")
    assert is_accent_press_candidate(key, {"Caps"}) is True


def test_is_accent_candidate_false_with_ctrl():
    key = PositionedKey("row0-a", "a", Rect(0, 0, 1, 1), role="key")
    assert is_accent_press_candidate(key, {"Ctrl"}) is False


def test_is_accent_candidate_false_with_alt():
    key = PositionedKey("row0-a", "a", Rect(0, 0, 1, 1), role="key")
    assert is_accent_press_candidate(key, {"Alt"}) is False


def test_is_accent_candidate_false_with_altgr():
    key = PositionedKey("row0-a", "a", Rect(0, 0, 1, 1), role="key")
    assert is_accent_press_candidate(key, {"AltGr"}) is False


def test_is_accent_candidate_false_with_super():
    key = PositionedKey("row0-a", "a", Rect(0, 0, 1, 1), role="key")
    assert is_accent_press_candidate(key, {"Super"}) is False


def test_is_accent_candidate_false_for_non_alpha():
    key = PositionedKey("row0-1", "1", Rect(0, 0, 1, 1), role="key")
    assert is_accent_press_candidate(key, set()) is False


def test_is_accent_candidate_false_for_non_accent_alpha():
    key = PositionedKey("row0-b", "b", Rect(0, 0, 1, 1), role="key")
    assert is_accent_press_candidate(key, set()) is False


def test_is_accent_candidate_false_for_multi_char_label():
    key = PositionedKey("row0-tab", "Tab", Rect(0, 0, 1, 1), role="key")
    assert is_accent_press_candidate(key, set()) is False


def test_is_accent_candidate_false_for_non_key_role():
    key = PositionedKey("row0-a", "a", Rect(0, 0, 1, 1), role="modifier")
    assert is_accent_press_candidate(key, set()) is False


def test_is_accent_candidate_uppercase_letter_without_modifiers():
    key = PositionedKey("row0-a", "A", Rect(0, 0, 1, 1), role="key")
    assert is_accent_press_candidate(key, set()) is True


def test_command_modifiers_contains_expected():
    assert COMMAND_MODIFIERS == {"Ctrl", "Alt", "AltGr", "Super"}
