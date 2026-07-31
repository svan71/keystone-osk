# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from logic_test_helpers import *

from keystone_osk.geometry import hit_test

def test_bottom_row_replaces_duplicate_right_ctrl_with_delete() -> None:
    labels = [key.label for key in build_linux_layout().bottom_row]

    assert labels == ["Ctrl", "Super", "Alt", "Space", "AltGr", "Super", "Menu", "Delete"]

def test_full_keyboard_uses_right_ctrl_instead_of_extra_delete() -> None:
    bottom_labels = [
        key.label
        for key in build_full_key_geometry(width=FULL_WINDOW_WIDTH, height=FULL_WINDOW_HEIGHT).keys
        if key.id.startswith("full-bottom-")
    ]

    assert bottom_labels == ["Ctrl", "Super", "Alt", "Space", "AltGr", "Super", "Menu", "Snippets", "Ctrl"]

def test_full_keyboard_geometry_matches_wide_shallow_layout() -> None:
    geometry = build_full_key_geometry(width=FULL_WINDOW_WIDTH, height=FULL_WINDOW_HEIGHT)
    keys_by_id = {key.id: key for key in geometry.keys}

    assert keys_by_id["full-main-esc"].label == "Esc"
    assert keys_by_id["full-main-f12"].label == "F12"
    assert keys_by_id["full-nav-pause"].label == "Pause"
    assert keys_by_id["full-numpad-num"].label == "Num"
    assert keys_by_id["full-numpad-enter"].rect.height > keys_by_id["full-numpad-3"].rect.height
    assert keys_by_id["full-numpad-7"].rect.height > keys_by_id["full-nav-prtsc"].rect.height
    assert keys_by_id["full-numpad-0"].rect.width > keys_by_id["full-numpad-1"].rect.width
    assert abs(keys_by_id["full-nav-pause"].rect.top - keys_by_id["full-numpad-num"].rect.top) < 0.01
    assert keys_by_id["arrow-up"].rect.top > keys_by_id["full-nav-delete"].rect.bottom - 10
    assert keys_by_id["full-main-esc"].rect.height <= 48
    assert keys_by_id["full-nav-insert"].rect.width >= 36
    assert keys_by_id["full-numpad-num"].rect.width >= 36
    assert abs(keys_by_id["arrow-left"].rect.center_x - keys_by_id["full-nav-delete"].rect.center_x) < 1
    assert abs(keys_by_id["arrow-down"].rect.center_x - keys_by_id["full-nav-end"].rect.center_x) < 1
    assert abs(keys_by_id["arrow-right"].rect.center_x - keys_by_id["full-nav-pgdn"].rect.center_x) < 1
    assert keys_by_id["arrow-up"].rect.top > keys_by_id["full-nav-delete"].rect.bottom
    assert keys_by_id["full-numpad-num"].rect.left - keys_by_id["full-nav-pause"].rect.right <= 16
    assert FULL_WINDOW_HEIGHT - keys_by_id["arrow-down"].rect.bottom >= 18

def test_full_keyboard_width_only_resize_expands_nav_and_numpad_keys() -> None:
    narrow = {key.id: key for key in build_full_key_geometry(width=MIN_FULL_WINDOW_WIDTH, height=MIN_WINDOW_HEIGHT).keys}
    wider = {key.id: key for key in build_full_key_geometry(width=1120, height=MIN_WINDOW_HEIGHT).keys}

    assert wider["full-nav-home"].rect.width > narrow["full-nav-home"].rect.width
    assert wider["full-nav-delete"].rect.width > narrow["full-nav-delete"].rect.width
    assert wider["full-numpad-7"].rect.width > narrow["full-numpad-7"].rect.width
    assert wider["full-numpad-9"].rect.width > narrow["full-numpad-9"].rect.width
    assert wider["full-nav-home"].rect.width >= 55
    assert wider["full-numpad-7"].rect.width >= 48
    assert max(key.rect.right for key in wider.values()) < 1120 - 18


def test_hit_test_accepts_near_miss_on_short_full_nav_delete_key() -> None:
    keys = build_full_key_geometry(width=FULL_WINDOW_WIDTH, height=FULL_WINDOW_HEIGHT).keys
    full_delete = next(key for key in keys if key.id == "full-nav-delete")

    hit = hit_test(keys, full_delete.rect.center_x, full_delete.rect.bottom + 4)

    assert hit == full_delete


def test_full_numpad_shows_standard_numlock_off_alternates() -> None:
    keys_by_id = {key.id: key for key in build_full_key_geometry(width=FULL_WINDOW_WIDTH, height=FULL_WINDOW_HEIGHT).keys}

    assert keys_by_id["full-numpad-7"].shifted == "Home"
    assert keys_by_id["full-numpad-7"].output == "KP7"
    assert keys_by_id["full-numpad-7"].shifted_output == "Home"
    assert keys_by_id["full-numpad-8"].shifted == "▲"
    assert keys_by_id["full-numpad-8"].output == "KP8"
    assert keys_by_id["full-numpad-8"].shifted_output == "Up"
    assert keys_by_id["full-numpad-9"].shifted == "PgUp"
    assert keys_by_id["full-numpad-4"].shifted == "◀"
    assert keys_by_id["full-numpad-6"].shifted == "▶"
    assert keys_by_id["full-numpad-1"].shifted == "End"
    assert keys_by_id["full-numpad-2"].shifted == "▼"
    assert keys_by_id["full-numpad-3"].shifted == "PgDn"
    assert keys_by_id["full-numpad-0"].shifted == "Ins"
    assert keys_by_id["full-numpad-0"].output == "KP0"
    assert keys_by_id["full-numpad-0"].shifted_output == "Insert"
    assert keys_by_id["full-numpad-dot"].shifted == "Del"
    assert keys_by_id["full-numpad-dot"].output == "KPDot"
    assert keys_by_id["full-numpad-dot"].shifted_output == "Delete"

def test_full_numpad_operator_keys_have_keypad_output_identities() -> None:
    keys_by_id = {key.id: key for key in build_full_key_geometry(width=FULL_WINDOW_WIDTH, height=FULL_WINDOW_HEIGHT).keys}

    assert keys_by_id["full-numpad-slash"].output == "KPSlash"
    assert keys_by_id["full-numpad-star"].output == "KPStar"
    assert keys_by_id["full-numpad-minus"].output == "KPMinus"
    assert keys_by_id["full-numpad-plus"].output == "KPPlus"
    assert keys_by_id["full-numpad-enter"].output == "KPEnter"

def test_kde_compact_geometry_reduces_internal_padding_without_changing_gnome() -> None:
    layout = build_linux_layout()
    gnome = build_key_geometry(layout, width=1120, height=470, is_kde=False)
    kde = build_key_geometry(layout, width=1120, height=470, is_kde=True)
    gnome_first = next(key for key in gnome.keys if key.id == "row0-grave")
    kde_first = next(key for key in kde.keys if key.id == "row0-grave")

    assert gnome.panel.left == 18
    assert gnome_first.rect.left == 42
    assert gnome_first.rect.top == 96
    assert kde.panel.left == 13.5
    assert kde_first.rect.left == 31.5
    assert kde_first.rect.top == 72
    assert kde_first.rect.width > gnome_first.rect.width
    assert kde_first.rect.height > gnome_first.rect.height

def test_kde_full_geometry_reduces_internal_padding_without_changing_gnome() -> None:
    gnome = build_full_key_geometry(width=1120, height=300, is_kde=False)
    kde = build_full_key_geometry(width=1120, height=300, is_kde=True)
    gnome_first = next(key for key in gnome.keys if key.id == "full-main-esc")
    kde_first = next(key for key in kde.keys if key.id == "full-main-esc")

    assert gnome.panel.left == 18
    assert gnome_first.rect.left == 36
    assert gnome_first.rect.top == 76
    assert kde.panel.left == 13.5
    assert kde_first.rect.left == 27
    assert kde_first.rect.top == 57
    assert kde_first.rect.width > gnome_first.rect.width
    assert kde_first.rect.height > gnome_first.rect.height
