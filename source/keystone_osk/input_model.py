from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from keystone_osk.geometry import PositionedKey

ONE_SHOT_MODIFIERS = {"Ctrl", "Shift", "Alt", "AltGr", "Super"}
LOCK_KEYS = {"Caps", "Num", *ONE_SHOT_MODIFIERS}
MODIFIER_ORDER = ("Ctrl", "Shift", "Alt", "AltGr", "Super")
COMMAND_MODIFIERS = {"Ctrl", "Alt", "AltGr", "Super"}
PUNCTUATION_AFTER_AUTOSPACE = {".", "?", "!", ",", ";", ":", '"'}
NUMPAD_NAV_LABELS = {
    "▲": "Up",
    "◀": "Left",
    "▶": "Right",
    "▼": "Down",
    "Ins": "Insert",
    "Del": "Delete",
}

NUMPAD_RELIABLE_MAIN_ROW = {
    "KP0": "0", "KP1": "1", "KP2": "2", "KP3": "3", "KP4": "4",
    "KP5": "5", "KP6": "6", "KP7": "7", "KP8": "8", "KP9": "9",
    "KPDot": ".",
}


@dataclass(frozen=True)
class KeyLabelDisplay:
    main: str
    alternate: str = ""


def key_label_display(key: PositionedKey, locked_key_labels: Collection[str]) -> KeyLabelDisplay:
    if key.role == "space":
        return KeyLabelDisplay("")
    if key.role == "backspace":
        return KeyLabelDisplay("⌫")
    if key.role == "delete":
        return KeyLabelDisplay("Del")
    if key.id.startswith("full-numpad-") and key.shifted and "Num" not in locked_key_labels:
        return KeyLabelDisplay(key.shifted, key.label)
    if len(key.label) == 1 and key.label.isalpha():
        shifted_letter = ("Caps" in locked_key_labels) ^ ("Shift" in locked_key_labels)
        return KeyLabelDisplay(key.label.upper() if shifted_letter else key.label.lower())
    if "Shift" in locked_key_labels and key.shifted:
        return KeyLabelDisplay(key.shifted, key.label)
    return KeyLabelDisplay(key.label, key.shifted)


def is_repeatable_key(key: PositionedKey) -> bool:
    if key.label in LOCK_KEYS or key.label in {"Enter", "Tab", "Menu", "Delete"}:
        return False
    return key.role in {"key", "space", "backspace", "arrow", "numpad"}


def output_key_for(
    key: PositionedKey,
    locked_key_labels: Collection[str],
    numpad_output_mode: str = "reliable",
) -> PositionedKey:
    if key.id.startswith("full-numpad-"):
        if key.shifted and "Num" not in locked_key_labels:
            return PositionedKey(
                key.id,
                key.shifted_output or NUMPAD_NAV_LABELS.get(key.shifted, key.shifted),
                key.rect,
                role=key.role,
                glyph=key.glyph,
            )
        emitted = key.output or key.label
        if numpad_output_mode == "reliable" and emitted in NUMPAD_RELIABLE_MAIN_ROW:
            emitted = NUMPAD_RELIABLE_MAIN_ROW[emitted]
        return PositionedKey(
            key.id,
            emitted,
            key.rect,
            shifted=key.shifted,
            output=key.output,
            shifted_output=key.shifted_output,
            role=key.role,
            glyph=key.glyph,
        )
    if key.output:
        return PositionedKey(
            key.id,
            key.output,
            key.rect,
            shifted=key.shifted,
            output=key.output,
            shifted_output=key.shifted_output,
            role=key.role,
            glyph=key.glyph,
        )
    return key


def output_text_for(key: PositionedKey, locked_key_labels: Collection[str]) -> str:
    return key_label_display(key, locked_key_labels).main


def is_accent_press_candidate(key, locked_key_labels) -> bool:
    from keystone_osk.accents import has_accents
    if key.role != "key":
        return False
    if len(key.label) != 1 or not key.label.isalpha():
        return False
    if COMMAND_MODIFIERS & locked_key_labels:
        return False
    return has_accents(key.label)


def active_modifiers_for(
    key: PositionedKey,
    locked_key_labels: Collection[str],
    *,
    auto_cap_enabled: bool = False,
    capitalize_next_letter: bool = False,
) -> tuple[str, ...]:
    if key.label in LOCK_KEYS:
        return ()
    modifiers = [modifier for modifier in MODIFIER_ORDER if modifier in locked_key_labels]
    if len(key.label) == 1 and key.label.isalpha() and "Caps" in locked_key_labels:
        if "Shift" in modifiers:
            modifiers.remove("Shift")
        else:
            modifiers.append("Shift")
    elif auto_cap_enabled and capitalize_next_letter and len(key.label) == 1 and key.label.isalpha() and not modifiers:
        modifiers.append("Shift")
    return tuple(modifiers)
