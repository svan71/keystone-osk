from __future__ import annotations

from dataclasses import dataclass

from keystone_osk.layout import ArrowSpec, KeyboardLayout, KeySpec, RowSpec

# Reference design size the layouts are authored against; runtime geometry and
# rendering scale relative to these. The compact and full layouts share a width
# but have different reference heights.
KEYBOARD_REFERENCE_WIDTH = 1120
COMPACT_REFERENCE_HEIGHT = 470
FULL_REFERENCE_HEIGHT = 300


@dataclass(frozen=True)
class Rect:
    left: float
    top: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.left + self.width

    @property
    def bottom(self) -> float:
        return self.top + self.height

    @property
    def center_x(self) -> float:
        return self.left + self.width / 2

    @property
    def center_y(self) -> float:
        return self.top + self.height / 2

    def contains(self, x: float, y: float) -> bool:
        return self.left <= x <= self.right and self.top <= y <= self.bottom


@dataclass(frozen=True)
class PositionedKey:
    id: str
    label: str
    rect: Rect
    shifted: str = ""
    role: str = "key"
    glyph: str = ""
    output: str = ""
    shifted_output: str = ""


@dataclass(frozen=True)
class KeyboardGeometry:
    panel: Rect
    keys: tuple[PositionedKey, ...]


def desktop_padding_scale(is_kde: bool = False) -> float:
    return 0.75 if is_kde else 1.0


def build_key_geometry(layout: KeyboardLayout, width: int, height: int, is_kde: bool = False) -> KeyboardGeometry:
    scale = min(width / KEYBOARD_REFERENCE_WIDTH, height / COMPACT_REFERENCE_HEIGHT)
    padding_scale = desktop_padding_scale(is_kde)
    panel_margin = 18 * padding_scale
    panel = Rect(panel_margin, panel_margin, width - panel_margin * 2, height - panel_margin * 2)
    left = panel.left + 24 * scale * padding_scale
    right = panel.right - 24 * scale * padding_scale
    top = panel.top + 78 * scale * padding_scale
    bottom = panel.bottom - 34 * scale * padding_scale
    gap = max(5, int(8 * scale))
    row_h = (bottom - top - gap * 4) / 5

    keys: list[PositionedKey] = []
    y = top
    for row_index, row in enumerate(layout.rows):
        keys.extend(_position_row(row.keys, Rect(left, y, right - left, row_h), gap, f"row{row_index}"))
        y += row_h + gap

    arrow_w = min(150 * scale, (right - left) * 0.14)
    bottom_rect = Rect(left, y, right - left, row_h)
    bottom_keys_rect = Rect(bottom_rect.left, bottom_rect.top, bottom_rect.width - arrow_w - gap, bottom_rect.height)
    keys.extend(_position_row(layout.bottom_row, bottom_keys_rect, gap, "bottom"))
    keys.extend(_position_arrows(layout, Rect(bottom_keys_rect.right + gap, bottom_rect.top, arrow_w, bottom_rect.height), scale))
    return KeyboardGeometry(panel=panel, keys=tuple(keys))


def build_full_key_geometry(width: int, height: int, is_kde: bool = False) -> KeyboardGeometry:
    scale = min(width / KEYBOARD_REFERENCE_WIDTH, height / FULL_REFERENCE_HEIGHT)
    horizontal_scale = width / KEYBOARD_REFERENCE_WIDTH
    padding_scale = desktop_padding_scale(is_kde)
    panel_margin = 18 * padding_scale
    panel = Rect(panel_margin, panel_margin, width - panel_margin * 2, height - panel_margin * 2)
    left = panel.left + 18 * horizontal_scale * padding_scale
    right = panel.right - 18 * horizontal_scale * padding_scale
    top = panel.top + 58 * scale * padding_scale
    bottom = panel.bottom - 20 * scale * padding_scale
    gap = max(3, int(5 * scale))
    row_h = (bottom - top - gap * 5) / 6

    numpad_w = 205 * horizontal_scale
    nav_w = 180 * horizontal_scale
    side_gap = gap * 3
    main_w = right - left - numpad_w - nav_w - side_gap - gap * 4
    main_left = left
    nav_left = main_left + main_w + gap * 4
    numpad_left = nav_left + nav_w + side_gap

    keys: list[PositionedKey] = []
    keys.extend(_position_function_row(Rect(main_left, top, main_w, row_h), gap))
    layout = _full_main_layout()
    y = top + row_h + gap
    for row_index, row in enumerate(layout.rows):
        keys.extend(_position_row(row.keys, Rect(main_left, y, main_w, row_h), gap, f"full-row{row_index}"))
        y += row_h + gap
    keys.extend(_position_row(layout.bottom_row, Rect(main_left, y, main_w, row_h), gap, "full-bottom"))
    keys.extend(_position_nav_cluster(Rect(nav_left, top, nav_w, row_h * 3 + gap * 2), gap, row_h))
    # -3*scale nudges the arrow cluster up so it visually aligns with the
    # nav cluster's bottom row rather than sitting a hair below it.
    arrow_top = top + row_h * 4 + gap * 4 - 3 * scale
    keys.extend(_position_full_arrows(Rect(nav_left, arrow_top, nav_w, row_h * 2 + gap), gap, row_h))
    keys.extend(_position_numpad(Rect(numpad_left, top, numpad_w, row_h * 6 + gap * 5), gap))
    return KeyboardGeometry(panel=panel, keys=tuple(keys))


def hit_test(keys: tuple[PositionedKey, ...], x: float, y: float) -> PositionedKey | None:
    for key in reversed(keys):
        if key.rect.contains(x, y):
            return key
    near_hits = [
        (distance_to_rect(key.rect, x, y), key)
        for key in keys
        if distance_to_rect(key.rect, x, y) <= hit_slop_for(key)
    ]
    if near_hits:
        return min(near_hits, key=lambda item: item[0])[1]
    return None


def distance_to_rect(rect: Rect, x: float, y: float) -> float:
    dx = max(rect.left - x, 0, x - rect.right)
    dy = max(rect.top - y, 0, y - rect.bottom)
    return (dx * dx + dy * dy) ** 0.5


def hit_slop_for(key: PositionedKey) -> float:
    if key.id.startswith(("full-nav-", "full-numpad-")):
        return 5.0
    return 3.0


def _full_main_layout() -> KeyboardLayout:
    return KeyboardLayout(
        rows=(
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
        ),
        bottom_row=(
            KeySpec("Ctrl", units=1.0, role="modifier"),
            KeySpec("Super", units=1.4, role="modifier"),
            KeySpec("Alt", units=1.0, role="modifier"),
            KeySpec("Space", units=5.2, role="space"),
            KeySpec("AltGr", units=1.4, role="modifier"),
            KeySpec("Super", units=1.4, role="modifier"),
            KeySpec("Menu", units=1.4, role="modifier"),
            KeySpec("Snippets", units=1.0, role="snippets"),
            KeySpec("Ctrl", units=1.0, role="modifier"),
        ),
        arrows=(
            ArrowSpec("Up", 0, 1, "▲"),
            ArrowSpec("Left", 1, 0, "◀"),
            ArrowSpec("Down", 1, 1, "▼"),
            ArrowSpec("Right", 1, 2, "▶"),
        ),
    )


def _position_row(keys: tuple[KeySpec, ...], rect: Rect, gap: int, prefix: str) -> list[PositionedKey]:
    total_units = sum(key.units for key in keys)
    unit_w = (rect.width - gap * (len(keys) - 1)) / total_units
    x = rect.left
    positioned: list[PositionedKey] = []
    for index, spec in enumerate(keys):
        w = unit_w * spec.units
        positioned.append(
            PositionedKey(
                id=f"{prefix}-{_key_id_fragment(spec.label, index)}",
                label=spec.label,
                rect=Rect(x, rect.top, w, rect.height),
                shifted=spec.shifted,
                output=spec.output,
                shifted_output=spec.shifted_output,
                role=spec.role,
            )
        )
        x += w + gap
    return positioned


def _key_id_fragment(label: str, index: int) -> str:
    return (
        label.lower()
        .replace(" ", "-")
        .replace("\\", "backslash")
        .replace("`", "grave")
        .replace("[", "left-bracket")
        .replace("]", "right-bracket")
        .replace(";", "semicolon")
        .replace("'", "apostrophe")
        .replace(",", "comma")
        .replace(".", "dot")
        .replace("/", "slash")
        .replace("=", "equals")
        .replace("-", "minus")
        .replace("shift", f"shift-{index}")
    )


def _position_function_row(rect: Rect, gap: int) -> list[PositionedKey]:
    specs = (
        ("esc", KeySpec("Esc", role="system")),
        ("f1", KeySpec("F1", role="function")),
        ("f2", KeySpec("F2", role="function")),
        ("f3", KeySpec("F3", role="function")),
        ("f4", KeySpec("F4", role="function")),
        ("f5", KeySpec("F5", role="function")),
        ("f6", KeySpec("F6", role="function")),
        ("f7", KeySpec("F7", role="function")),
        ("f8", KeySpec("F8", role="function")),
        ("f9", KeySpec("F9", role="function")),
        ("f10", KeySpec("F10", role="function")),
        ("f11", KeySpec("F11", role="function")),
        ("f12", KeySpec("F12", role="function")),
    )
    group_gaps = 3
    key_w = (rect.width - gap * (len(specs) - 1 + group_gaps * 3)) / len(specs)
    x = rect.left
    positioned: list[PositionedKey] = []
    for index, (name, spec) in enumerate(specs):
        if index in {1, 5, 9}:
            x += gap * group_gaps
        positioned.append(PositionedKey(f"full-main-{name}", spec.label, Rect(x, rect.top, key_w, rect.height), role=spec.role))
        x += key_w + gap
    return positioned


def _position_nav_cluster(rect: Rect, gap: int, row_h: float) -> list[PositionedKey]:
    rows = (
        (("prtsc", "PrtSc"), ("scrlk", "ScrLk"), ("pause", "Pause")),
        (("insert", "Insert"), ("home", "Home"), ("pgup", "PgUp")),
        (("delete", "Delete"), ("end", "End"), ("pgdn", "PgDn")),
    )
    key_w = (rect.width - gap * 2) / 3
    positioned: list[PositionedKey] = []
    for row_index, row in enumerate(rows):
        y = rect.top + row_index * (row_h + gap)
        for col_index, (name, label) in enumerate(row):
            positioned.append(
                PositionedKey(
                    f"full-nav-{name}",
                    label,
                    Rect(rect.left + col_index * (key_w + gap), y, key_w, row_h),
                    role="navigation",
                )
            )
    return positioned


def _position_full_arrows(rect: Rect, gap: int, row_h: float) -> list[PositionedKey]:
    key_w = (rect.width - gap * 2) / 3
    key_h = row_h
    positions = {
        "Up": Rect(rect.left + key_w + gap, rect.top, key_w, key_h),
        "Left": Rect(rect.left, rect.top + key_h + gap, key_w, key_h),
        "Down": Rect(rect.left + key_w + gap, rect.top + key_h + gap, key_w, key_h),
        "Right": Rect(rect.left + 2 * (key_w + gap), rect.top + key_h + gap, key_w, key_h),
    }
    return [
        PositionedKey("arrow-up", "Up", positions["Up"], role="arrow", glyph="▲"),
        PositionedKey("arrow-left", "Left", positions["Left"], role="arrow", glyph="◀"),
        PositionedKey("arrow-down", "Down", positions["Down"], role="arrow", glyph="▼"),
        PositionedKey("arrow-right", "Right", positions["Right"], role="arrow", glyph="▶"),
    ]


def _position_numpad(rect: Rect, gap: int) -> list[PositionedKey]:
    col_w = (rect.width - gap * 3) / 4
    row_h = (rect.height - gap * 4) / 5
    positioned: list[PositionedKey] = []

    def add(
        name: str,
        label: str,
        col: int,
        row: int,
        col_span: int = 1,
        row_span: int = 1,
        shifted: str = "",
        output: str = "",
        shifted_output: str = "",
    ) -> None:
        positioned.append(
            PositionedKey(
                f"full-numpad-{name}",
                label,
                Rect(
                    rect.left + col * (col_w + gap),
                    rect.top + row * (row_h + gap),
                    col_w * col_span + gap * (col_span - 1),
                    row_h * row_span + gap * (row_span - 1),
                ),
                shifted=shifted,
                output=output,
                shifted_output=shifted_output,
                role="numpad",
            )
        )

    for col, (name, label, output) in enumerate(
        (("num", "Num", "Num"), ("slash", "/", "KPSlash"), ("star", "*", "KPStar"), ("minus", "-", "KPMinus"))
    ):
        add(name, label, col, 0, output=output)
    for col, (label, shifted, shifted_output) in enumerate((("7", "Home", "Home"), ("8", "▲", "Up"), ("9", "PgUp", "PgUp"))):
        add(label, label, col, 1, shifted=shifted, output=f"KP{label}", shifted_output=shifted_output)
    add("plus", "+", 3, 1, row_span=2, output="KPPlus")
    for col, (label, shifted, shifted_output) in enumerate((("4", "◀", "Left"), ("5", "", ""), ("6", "▶", "Right"))):
        add(label, label, col, 2, shifted=shifted, output=f"KP{label}", shifted_output=shifted_output)
    for col, (label, shifted, shifted_output) in enumerate((("1", "End", "End"), ("2", "▼", "Down"), ("3", "PgDn", "PgDn"))):
        add(label, label, col, 3, shifted=shifted, output=f"KP{label}", shifted_output=shifted_output)
    add("enter", "Enter", 3, 3, row_span=2, output="KPEnter")
    add("0", "0", 0, 4, col_span=2, shifted="Ins", output="KP0", shifted_output="Insert")
    add("dot", ".", 2, 4, shifted="Del", output="KPDot", shifted_output="Delete")
    return positioned


def _position_arrows(layout: KeyboardLayout, rect: Rect, scale: float) -> list[PositionedKey]:
    arrow_gap = max(4, int(7 * scale))
    key_w = (rect.width - arrow_gap * 2) / 3
    key_h = (rect.height - arrow_gap) / 2
    positions = {
        "Up": Rect(rect.left + key_w + arrow_gap, rect.top, key_w, key_h),
        "Left": Rect(rect.left, rect.top + key_h + arrow_gap, key_w, key_h),
        "Down": Rect(rect.left + key_w + arrow_gap, rect.top + key_h + arrow_gap, key_w, key_h),
        "Right": Rect(rect.left + 2 * (key_w + arrow_gap), rect.top + key_h + arrow_gap, key_w, key_h),
    }
    return [
        PositionedKey(
            id=f"arrow-{arrow.label.lower()}",
            label=arrow.label,
            rect=positions[arrow.label],
            role="arrow",
            glyph=arrow.glyph,
        )
        for arrow in layout.arrows
    ]
