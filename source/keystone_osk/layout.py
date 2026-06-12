from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KeySpec:
    label: str
    units: float = 1.0
    shifted: str = ""
    role: str = "key"
    output: str = ""
    shifted_output: str = ""


@dataclass(frozen=True)
class RowSpec:
    keys: tuple[KeySpec, ...]


@dataclass(frozen=True)
class ArrowSpec:
    label: str
    row: int
    column: int
    glyph: str


@dataclass(frozen=True)
class KeyboardLayout:
    rows: tuple[RowSpec, ...]
    bottom_row: tuple[KeySpec, ...]
    arrows: tuple[ArrowSpec, ...]


def build_linux_layout() -> KeyboardLayout:
    rows = (
        RowSpec(
            (
                KeySpec("`", shifted="~"),
                KeySpec("1", shifted="!"),
                KeySpec("2", shifted="@"),
                KeySpec("3", shifted="#"),
                KeySpec("4", shifted="$"),
                KeySpec("5", shifted="%"),
                KeySpec("6", shifted="^"),
                KeySpec("7", shifted="&"),
                KeySpec("8", shifted="*"),
                KeySpec("9", shifted="("),
                KeySpec("0", shifted=")"),
                KeySpec("-", shifted="_"),
                KeySpec("=", shifted="+"),
                KeySpec("Backspace", units=1.55, role="backspace"),
            )
        ),
        RowSpec(
            (
                KeySpec("Tab", units=1.4, role="tab"),
                KeySpec("q"),
                KeySpec("w"),
                KeySpec("e"),
                KeySpec("r"),
                KeySpec("t"),
                KeySpec("y"),
                KeySpec("u"),
                KeySpec("i"),
                KeySpec("o"),
                KeySpec("p"),
                KeySpec("[", shifted="{"),
                KeySpec("]", shifted="}"),
                KeySpec("\\", shifted="|"),
            )
        ),
        RowSpec(
            (
                KeySpec("Caps", units=1.7, role="caps"),
                KeySpec("a"),
                KeySpec("s"),
                KeySpec("d"),
                KeySpec("f"),
                KeySpec("g"),
                KeySpec("h"),
                KeySpec("j"),
                KeySpec("k"),
                KeySpec("l"),
                KeySpec(";", shifted=":"),
                KeySpec("'", shifted='"'),
                KeySpec("Enter", units=1.7, role="enter"),
            )
        ),
        RowSpec(
            (
                KeySpec("Shift", units=2.2, role="shift"),
                KeySpec("z"),
                KeySpec("x"),
                KeySpec("c"),
                KeySpec("v"),
                KeySpec("b"),
                KeySpec("n"),
                KeySpec("m"),
                KeySpec(",", shifted="<"),
                KeySpec(".", shifted=">"),
                KeySpec("/", shifted="?"),
                KeySpec("Shift", units=2.2, role="shift"),
            )
        ),
    )
    bottom_row = (
        KeySpec("Ctrl", units=1.0, role="modifier"),
        KeySpec("Super", units=1.4, role="modifier"),
        KeySpec("Alt", units=1.0, role="modifier"),
        KeySpec("Space", units=5.2, role="space"),
        KeySpec("AltGr", units=1.4, role="modifier"),
        KeySpec("Super", units=1.4, role="modifier"),
        KeySpec("Menu", units=1.4, role="modifier"),
        KeySpec("Delete", units=1.0, role="delete"),
    )
    arrows = (
        ArrowSpec("Up", row=0, column=1, glyph="▲"),
        ArrowSpec("Left", row=1, column=0, glyph="◀"),
        ArrowSpec("Down", row=1, column=1, glyph="▼"),
        ArrowSpec("Right", row=1, column=2, glyph="▶"),
    )
    return KeyboardLayout(rows=rows, bottom_row=bottom_row, arrows=arrows)
