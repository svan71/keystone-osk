# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
from pathlib import Path

from keystone_osk.snippets import (
    Snippet,
    ensure_snippets_file,
    load_snippets,
    snippet_text,
)

ENV_KEY = "KEYSTONE_OSK_SNIPPETS_FILE"


def _write(tmp_path: Path, payload) -> dict[str, str]:
    target = tmp_path / "snippets.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return {ENV_KEY: str(target)}


def test_loads_snippets_in_order(tmp_path):
    env = _write(tmp_path, {"snippets": [
        {"label": "Email", "actions": [{"type": "text", "value": "user@example.com"}]},
        {"label": "Addr", "actions": [{"type": "text", "value": "123 Main"}]},
    ]})
    result = load_snippets(env)
    assert [s.label for s in result] == ["Email", "Addr"]
    assert result[0].actions[0].type == "text"
    assert result[0].actions[0].value == "user@example.com"


def test_missing_file_returns_empty(tmp_path):
    assert load_snippets({ENV_KEY: str(tmp_path / "nope.json")}) == []


def test_malformed_json_returns_empty(tmp_path):
    target = tmp_path / "snippets.json"
    target.write_text("{ not json", encoding="utf-8")
    assert load_snippets({ENV_KEY: str(target)}) == []


def test_wrong_top_level_shape_returns_empty(tmp_path):
    assert load_snippets(_write(tmp_path, ["x"])) == []
    assert load_snippets(_write(tmp_path, {"nope": 1})) == []


def test_entry_missing_label_is_skipped(tmp_path):
    env = _write(tmp_path, {"snippets": [
        {"actions": [{"type": "text", "value": "x"}]},
        {"label": "Good", "actions": [{"type": "text", "value": "y"}]},
    ]})
    assert [s.label for s in load_snippets(env)] == ["Good"]


def test_entry_with_no_usable_actions_is_skipped(tmp_path):
    env = _write(tmp_path, {"snippets": [
        {"label": "Empty", "actions": []},
        {"label": "Unknown", "actions": [{"type": "weird", "value": "z"}]},
        {"label": "Good", "actions": [{"type": "text", "value": "y"}]},
    ]})
    assert [s.label for s in load_snippets(env)] == ["Good"]


def test_ensure_creates_a_usable_template_when_missing(tmp_path):
    target = tmp_path / "sub" / "snippets.json"
    env = {ENV_KEY: str(target)}
    returned = ensure_snippets_file(env)
    assert returned == target
    assert target.exists()
    # The template must be valid JSON that yields at least one example snippet,
    # and must carry beginner help text for someone editing it.
    raw = target.read_text(encoding="utf-8")
    assert "_README" in raw or "_howto" in raw
    assert "never rename them" in raw
    snippets = load_snippets(env)
    assert len(snippets) >= 1
    assert all(s.label for s in snippets)


def test_ensure_does_not_overwrite_existing_file(tmp_path):
    env = _write(tmp_path, {"snippets": [
        {"label": "Mine", "actions": [{"type": "text", "value": "keep me"}]},
    ]})
    ensure_snippets_file(env)
    assert [s.label for s in load_snippets(env)] == ["Mine"]


def test_flat_text_shorthand_loads(tmp_path):
    env = _write(tmp_path, {"snippets": [
        {"label": "Email", "text": "user@example.com"},
    ]})
    result = load_snippets(env)
    assert [s.label for s in result] == ["Email"]
    assert snippet_text(result[0]) == "user@example.com"


def test_actions_take_precedence_over_text_shorthand(tmp_path):
    env = _write(tmp_path, {"snippets": [
        {"label": "Both", "text": "ignored", "actions": [{"type": "text", "value": "used"}]},
    ]})
    assert snippet_text(load_snippets(env)[0]) == "used"


def test_empty_text_shorthand_is_skipped(tmp_path):
    env = _write(tmp_path, {"snippets": [
        {"label": "Blank", "text": ""},
        {"label": "Good", "text": "ok"},
    ]})
    assert [s.label for s in load_snippets(env)] == ["Good"]


def test_snippet_text_concatenates_text_actions(tmp_path):
    env = _write(tmp_path, {"snippets": [
        {"label": "Multi", "actions": [
            {"type": "text", "value": "a"},
            {"type": "text", "value": "b"},
        ]},
    ]})
    assert snippet_text(load_snippets(env)[0]) == "ab"
