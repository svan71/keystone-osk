# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from keystone_osk.geometry import (
    COMPACT_REFERENCE_HEIGHT,
    FULL_REFERENCE_HEIGHT,
    KEYBOARD_REFERENCE_WIDTH,
    build_full_key_geometry,
    build_key_geometry,
)
from keystone_osk.layout import build_linux_layout
from qt_window_test_helpers import FULL_WINDOW_HEIGHT, FULL_WINDOW_WIDTH, KeyboardWindow, QSize


def _full_geometry():
    # Reference full-size dimensions; offscreen, no window needed.
    return build_full_key_geometry(KEYBOARD_REFERENCE_WIDTH, FULL_REFERENCE_HEIGHT)


def test_full_layout_has_a_snippets_key():
    roles = {key.role for key in _full_geometry().keys}
    assert "snippets" in roles


def test_snippets_key_no_wider_than_ctrl():
    keys = _full_geometry().keys
    snip = next(k for k in keys if k.role == "snippets")
    ctrls = [k for k in keys if k.id.startswith("full-bottom-") and k.label == "Ctrl"]
    assert ctrls
    assert snip.rect.width <= min(k.rect.width for k in ctrls) + 0.5


def test_compact_layout_has_no_snippets_key():
    compact = build_key_geometry(
        build_linux_layout(), KEYBOARD_REFERENCE_WIDTH, COMPACT_REFERENCE_HEIGHT
    )
    roles = {key.role for key in compact.keys}
    assert "snippets" not in roles


@pytest.fixture
def window(app, tmp_path, monkeypatch):
    monkeypatch.setenv("KEYSTONE_OSK_SNIPPETS_FILE", str(tmp_path / "snippets.json"))
    win = KeyboardWindow(startup_size=QSize(FULL_WINDOW_WIDTH, FULL_WINDOW_HEIGHT), persist_window_state=False)
    win.backend = MagicMock()
    yield win
    win.close()


def _write_snippets(tmp_path, payload):
    (tmp_path / "snippets.json").write_text(json.dumps(payload), encoding="utf-8")


def test_emit_snippet_types_text_via_backend(window):
    from keystone_osk.snippets import Snippet, SnippetAction
    snip = Snippet(label="Email", actions=(SnippetAction("text", "user@example.com"),))
    window._emit_snippet(snip)
    window.backend.type_text.assert_called_once_with("user@example.com")


def test_show_snippets_menu_lists_labels_and_edit_entry(window, tmp_path):
    _write_snippets(tmp_path, {"snippets": [
        {"label": "Email", "actions": [{"type": "text", "value": "a@b.c"}]},
        {"label": "Addr", "actions": [{"type": "text", "value": "123"}]},
    ]})
    menu = window._build_snippets_menu()
    texts = [a.text() for a in menu.actions() if not a.isSeparator()]
    assert texts[:2] == ["Email", "Addr"]
    assert any("Edit snippets" in t for t in texts)


def test_empty_snippets_menu_shows_clickable_create_hint(window):
    menu = window._build_snippets_menu()
    all_actions = menu.actions()
    non_sep = [a for a in all_actions if not a.isSeparator()]
    # Empty valid file: "No snippets yet…" hint + "Restore example snippets…" = 2 non-sep actions.
    # One separator sits between them → 3 total QAction objects.
    assert len(non_sep) == 2, f"Expected 2 non-separator actions, got {[a.text() for a in non_sep]}"
    assert len(all_actions) == 3, f"Expected 3 total actions (2 items + 1 separator), got {[a.text() for a in all_actions]}"
    hint = next((a for a in non_sep if "create" in a.text().lower() or "edit" in a.text().lower()), None)
    assert hint is not None
    assert hint.isEnabled()


def test_open_snippets_file_creates_template(window, tmp_path, monkeypatch):
    from PySide6.QtGui import QDesktopServices

    opened = {}
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.setdefault("url", url) or True)
    target = tmp_path / "snippets.json"
    assert not target.exists()
    window._open_snippets_file()
    assert target.exists()
    assert "url" in opened


def test_outside_click_dismisses_open_snippets_menu(window):
    # Clicking the cancel overlay (anywhere outside the popup, incl. the keyboard)
    # must close the snippets menu.
    state = {"visible": True}

    class StubMenu:
        def isVisible(self):
            return state["visible"]

        def hide(self):
            state["visible"] = False

    window._snippets_menu = StubMenu()
    window._handle_outside_overlay_click()
    assert state["visible"] is False


def test_show_snippets_cancel_overlay_excludes_menu_rect(window, monkeypatch):
    from PySide6.QtCore import QPoint, QRect

    calls = {}
    monkeypatch.setattr(window._modifier_cancel_overlay, "show_around_rect", lambda rect: calls.setdefault("rect", rect))

    class StubMenu:
        def isVisible(self):
            return True

        def pos(self):
            return QPoint(100, 50)

        def sizeHint(self):
            return QSize(120, 80)

        def raise_(self):
            pass

    window._snippets_menu = StubMenu()
    window._show_snippets_cancel_overlay()
    assert calls["rect"] == QRect(QPoint(100, 50), QSize(120, 80))


def test_snippets_menu_hidden_clears_ref_and_tears_down_overlay(window, monkeypatch):
    torn_down = {}
    monkeypatch.setattr(window._modifier_cancel_overlay, "hide", lambda: torn_down.setdefault("hidden", True))
    window._snippets_menu = object()
    window._on_snippets_menu_hidden()
    assert window._snippets_menu is None
    assert torn_down.get("hidden") is True


def test_snippets_key_renders_glyph_not_text_label(window):
    # The snippets key must not render its raw "Snippets" label as text; it draws
    # the homage glyph instead. We assert via a render hook flag.
    snip_key = next(k for k in _full_geometry().keys if k.role == "snippets")
    from keystone_osk.rendering import is_glyph_key

    assert is_glyph_key(snip_key) is True


def test_snippets_glyph_colors_contrast_with_key_face():
    # Regression guard: the homage squares must NOT fill with the key-face colors,
    # or the glyph is invisible (only a faint outline shows). Both fills must
    # differ from the key gradient and from each other.
    from keystone_osk.rendering import snippets_glyph_colors
    from keystone_osk.theme import theme_palette

    def brightness(hex_color: str) -> float:
        v = int(hex_color.lstrip("#"), 16)
        r, g, b = (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF
        return 0.299 * r + 0.587 * g + 0.114 * b

    for theme in ("dracula", "light", "mocha"):
        palette = theme_palette(theme)
        back, front = snippets_glyph_colors(palette)
        assert back != front, f"{theme}: squares are indistinguishable"
        # Both squares must visibly contrast the key face, not just differ from it
        # (a near-white gray on a white key passes inequality but is invisible).
        key_brightness = brightness(palette.key_normal_top)
        for name, color in (("back", back), ("front", front)):
            gap = abs(brightness(color) - key_brightness)
            assert gap >= 40, f"{theme}: {name} square too close in brightness to the key face"
            assert gap <= 145, f"{theme}: {name} square too heavy/pronounced against the key face"
