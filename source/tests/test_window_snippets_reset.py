# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for snippets menu error/warning actions and 'Restore example snippets…' reset."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from qt_window_test_helpers import FULL_WINDOW_HEIGHT, FULL_WINDOW_WIDTH, KeyboardWindow, QSize

ENV_KEY = "KEYSTONE_OSK_SNIPPETS_FILE"


@pytest.fixture
def window(app, tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_KEY, str(tmp_path / "snippets.json"))
    win = KeyboardWindow(startup_size=QSize(FULL_WINDOW_WIDTH, FULL_WINDOW_HEIGHT), persist_window_state=False)
    win.backend = MagicMock()
    yield win
    win.close()


def _write_snippets(tmp_path, payload):
    (tmp_path / "snippets.json").write_text(json.dumps(payload), encoding="utf-8")


# ---------------------------------------------------------------------------
# Warning action for invalid entries
# ---------------------------------------------------------------------------

def test_build_snippets_menu_warns_for_invalid_entries(window, tmp_path):
    """If any entries fail to parse, a warning action appears at the top."""
    _write_snippets(tmp_path, {"snippets": [
        {"Gmail": "you@example.com"},           # bad: no label/text keys
        {"label": "Good", "text": "ok"},
    ]})
    menu = window._build_snippets_menu()
    texts = [a.text() for a in menu.actions() if not a.isSeparator()]
    # First action must be a warning
    assert "⚠" in texts[0]
    # It must mention count and invite editing
    assert "1" in texts[0]
    # Valid snippet must still appear
    assert any("Good" in t for t in texts)


def test_build_snippets_menu_warning_pluralizes_count(window, tmp_path):
    """'2 snippets couldn't load' not '2 snippet couldn't load'."""
    _write_snippets(tmp_path, {"snippets": [
        {"Gmail": "bad1"},
        {"Yahoo": "bad2"},
        {"label": "Good", "text": "ok"},
    ]})
    menu = window._build_snippets_menu()
    texts = [a.text() for a in menu.actions() if not a.isSeparator()]
    assert "2" in texts[0]
    assert "⚠" in texts[0]


def test_build_snippets_menu_invalid_entries_warning_triggers_open(window, tmp_path, monkeypatch):
    """Clicking the warning action must open the snippets file."""
    _write_snippets(tmp_path, {"snippets": [
        {"bad": "entry"},
        {"label": "Good", "text": "ok"},
    ]})
    opened = {}
    monkeypatch.setattr(window, "_open_snippets_file", lambda: opened.setdefault("called", True))
    menu = window._build_snippets_menu()
    # First action is the warning
    warn_action = next(a for a in menu.actions() if "⚠" in a.text())
    warn_action.trigger()
    assert opened.get("called") is True


# ---------------------------------------------------------------------------
# Warning action for broken JSON
# ---------------------------------------------------------------------------

def test_build_snippets_menu_shows_error_for_broken_json(window, tmp_path):
    """When the whole file is invalid JSON, menu shows a file-level error instead of 'No snippets yet'."""
    (tmp_path / "snippets.json").write_text("{ not json", encoding="utf-8")
    menu = window._build_snippets_menu()
    texts = [a.text() for a in menu.actions() if not a.isSeparator()]
    # Must NOT show "No snippets yet" for a broken file
    assert not any("No snippets yet" in t for t in texts)
    # Must show the file-level error
    assert any("⚠" in t for t in texts)
    assert any("error" in t.lower() or "invalid" in t.lower() or "JSON" in t for t in texts)


def test_build_snippets_menu_broken_json_error_triggers_open(window, tmp_path, monkeypatch):
    """Clicking the file-level error action opens the snippets file."""
    (tmp_path / "snippets.json").write_text("{ not json", encoding="utf-8")
    opened = {}
    monkeypatch.setattr(window, "_open_snippets_file", lambda: opened.setdefault("called", True))
    menu = window._build_snippets_menu()
    warn_action = next(a for a in menu.actions() if not a.isSeparator())
    warn_action.trigger()
    assert opened.get("called") is True


# ---------------------------------------------------------------------------
# "Restore example snippets…" always-present reset action
# ---------------------------------------------------------------------------

def test_build_snippets_menu_always_has_restore_action(window, tmp_path):
    """'Restore example snippets…' must appear in the menu regardless of file state."""
    _write_snippets(tmp_path, {"snippets": [{"label": "A", "text": "a"}]})
    menu = window._build_snippets_menu()
    texts = [a.text() for a in menu.actions() if not a.isSeparator()]
    assert any("Restore" in t for t in texts)


def test_restore_action_present_when_no_file(window):
    """Menu must have restore action even if snippets file doesn't exist."""
    menu = window._build_snippets_menu()
    texts = [a.text() for a in menu.actions() if not a.isSeparator()]
    assert any("Restore" in t for t in texts)


def test_restore_action_present_with_broken_json(window, tmp_path):
    (tmp_path / "snippets.json").write_text("{ bad json", encoding="utf-8")
    menu = window._build_snippets_menu()
    texts = [a.text() for a in menu.actions() if not a.isSeparator()]
    assert any("Restore" in t for t in texts)


def test_restore_action_backs_up_and_rewrites_and_opens(window, tmp_path, monkeypatch):
    """Clicking Restore: backs up existing file, writes template, opens file."""
    original = '{"snippets":[{"label":"Mine","text":"keep"}]}'
    (tmp_path / "snippets.json").write_text(original, encoding="utf-8")

    opened = {}
    monkeypatch.setattr(window, "_open_snippets_file", lambda: opened.setdefault("called", True))

    menu = window._build_snippets_menu()
    restore_action = next(a for a in menu.actions() if not a.isSeparator() and "Restore" in a.text())
    restore_action.trigger()

    # Backup must exist with original content
    bak = tmp_path / "snippets.json.bak"
    assert bak.exists()
    assert bak.read_text(encoding="utf-8") == original

    # Main file must now be the template
    content = (tmp_path / "snippets.json").read_text(encoding="utf-8")
    assert "_README" in content

    # File must have been opened
    assert opened.get("called") is True


def test_restore_action_no_existing_file_still_works(window, tmp_path, monkeypatch):
    """Restore with no existing file: writes template, opens it, no .bak."""
    opened = {}
    monkeypatch.setattr(window, "_open_snippets_file", lambda: opened.setdefault("called", True))

    menu = window._build_snippets_menu()
    restore_action = next(a for a in menu.actions() if not a.isSeparator() and "Restore" in a.text())
    restore_action.trigger()

    assert (tmp_path / "snippets.json").exists()
    assert not (tmp_path / "snippets.json.bak").exists()
    assert opened.get("called") is True
