# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for load_snippets_with_errors, reset_snippets_file, and SNIPPETS_TEMPLATE."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from keystone_osk.snippets import (
    SNIPPETS_TEMPLATE,
    load_snippets,
    load_snippets_with_errors,
    reset_snippets_file,
)

ENV_KEY = "KEYSTONE_OSK_SNIPPETS_FILE"


def _write(tmp_path: Path, payload) -> dict[str, str]:
    target = tmp_path / "snippets.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return {ENV_KEY: str(target)}


# ---------------------------------------------------------------------------
# load_snippets_with_errors — basic return contract
# ---------------------------------------------------------------------------

def test_load_with_errors_returns_tuple(tmp_path):
    env = _write(tmp_path, {"snippets": [{"label": "A", "text": "a"}]})
    result = load_snippets_with_errors(env)
    snippets, entry_errors, file_error = result
    assert isinstance(snippets, list)
    assert isinstance(entry_errors, list)
    assert file_error is None


def test_load_with_errors_clean_file_no_errors(tmp_path):
    env = _write(tmp_path, {"snippets": [
        {"label": "Email", "text": "user@example.com"},
        {"label": "Sign", "text": "Thanks!"},
    ]})
    snippets, entry_errors, file_error = load_snippets_with_errors(env)
    assert len(snippets) == 2
    assert entry_errors == []
    assert file_error is None


def test_load_with_errors_missing_file_returns_empty_and_no_error(tmp_path):
    env = {ENV_KEY: str(tmp_path / "nope.json")}
    snippets, entry_errors, file_error = load_snippets_with_errors(env)
    assert snippets == []
    assert entry_errors == []
    assert file_error is None


def test_load_with_errors_malformed_json_returns_file_level_error(tmp_path):
    target = tmp_path / "snippets.json"
    target.write_text("{ not json", encoding="utf-8")
    env = {ENV_KEY: str(target)}
    snippets, entry_errors, file_error = load_snippets_with_errors(env)
    assert snippets == []
    assert entry_errors == []
    assert file_error is not None
    assert "not valid JSON" in file_error or "invalid JSON" in file_error


def test_load_with_errors_wrong_top_level_shape_returns_file_level_error(tmp_path):
    env = _write(tmp_path, ["x"])
    snippets, entry_errors, file_error = load_snippets_with_errors(env)
    assert snippets == []
    assert file_error is not None


def test_load_with_errors_no_snippets_key_returns_file_level_error(tmp_path):
    env = _write(tmp_path, {"nope": 1})
    snippets, entry_errors, file_error = load_snippets_with_errors(env)
    assert snippets == []
    assert file_error is not None


# ---------------------------------------------------------------------------
# load_snippets_with_errors — per-entry errors
# ---------------------------------------------------------------------------

def test_load_with_errors_entry_missing_label_reports_error(tmp_path):
    env = _write(tmp_path, {"snippets": [
        {"text": "x"},                               # bad: no label
        {"label": "Good", "text": "y"},
    ]})
    snippets, entry_errors, file_error = load_snippets_with_errors(env)
    assert [s.label for s in snippets] == ["Good"]
    assert len(entry_errors) == 1
    assert file_error is None
    # Error must mention the entry index (0) or something identifying it
    assert "0" in entry_errors[0] or "entry" in entry_errors[0].lower()


def test_load_with_errors_entry_no_usable_actions_reports_error(tmp_path):
    env = _write(tmp_path, {"snippets": [
        {"label": "Empty", "actions": []},
        {"label": "Good", "text": "ok"},
    ]})
    snippets, entry_errors, file_error = load_snippets_with_errors(env)
    assert [s.label for s in snippets] == ["Good"]
    assert len(entry_errors) == 1
    assert file_error is None
    assert "0" in entry_errors[0] or "entry" in entry_errors[0].lower()


def test_load_with_errors_multiple_bad_entries_one_error_each(tmp_path):
    env = _write(tmp_path, {"snippets": [
        {"text": "no label"},                        # entry 0
        {"label": "Good", "text": "ok"},             # entry 1, valid
        {"label": "Bad", "actions": []},             # entry 2, no usable actions
    ]})
    snippets, entry_errors, file_error = load_snippets_with_errors(env)
    assert len(snippets) == 1
    assert len(entry_errors) == 2
    assert file_error is None


def test_load_with_errors_error_mentions_entry_index(tmp_path):
    env = _write(tmp_path, {"snippets": [
        {"label": "Good", "text": "ok"},             # entry 0
        {"text": "no label"},                        # entry 1 — bad
    ]})
    snippets, entry_errors, file_error = load_snippets_with_errors(env)
    assert len(entry_errors) == 1
    assert "1" in entry_errors[0]


def test_load_with_errors_error_message_is_human_readable(tmp_path):
    """Error text must be suitable for showing in a menu (no tracebacks/codes)."""
    env = _write(tmp_path, {"snippets": [
        {"Gmail": "you@example.com"},               # WRONG: keys not label/text
    ]})
    snippets, entry_errors, file_error = load_snippets_with_errors(env)
    assert snippets == []
    assert len(entry_errors) == 1
    assert file_error is None
    msg = entry_errors[0]
    assert len(msg) < 200
    assert "\n" not in msg


# ---------------------------------------------------------------------------
# load_snippets backward-compat wrapper still works
# ---------------------------------------------------------------------------

def test_load_snippets_wrapper_still_works_with_valid_file(tmp_path):
    env = _write(tmp_path, {"snippets": [{"label": "X", "text": "x"}]})
    result = load_snippets(env)
    assert len(result) == 1


def test_load_snippets_wrapper_still_works_with_bad_file(tmp_path):
    target = tmp_path / "snippets.json"
    target.write_text("not json", encoding="utf-8")
    result = load_snippets({ENV_KEY: str(target)})
    assert result == []


# ---------------------------------------------------------------------------
# reset_snippets_file
# ---------------------------------------------------------------------------

def test_reset_creates_snippets_file_from_template(tmp_path):
    target = tmp_path / "snippets.json"
    env = {ENV_KEY: str(target)}
    # File does not exist yet — reset should still work (no .bak needed)
    reset_snippets_file(env)
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "snippets" in content


def test_reset_overwrites_existing_snippets_with_template(tmp_path):
    target = tmp_path / "snippets.json"
    target.write_text('{"snippets":[{"label":"Mine","text":"keep"}]}', encoding="utf-8")
    env = {ENV_KEY: str(target)}
    reset_snippets_file(env)
    # After reset, file should contain the template (has _README)
    content = target.read_text(encoding="utf-8")
    assert "_README" in content


def test_reset_backs_up_existing_file_before_overwriting(tmp_path):
    target = tmp_path / "snippets.json"
    original = '{"snippets":[{"label":"Mine","text":"keep me"}]}'
    target.write_text(original, encoding="utf-8")
    env = {ENV_KEY: str(target)}
    bak_path = reset_snippets_file(env)
    assert bak_path is not None
    assert bak_path.exists()
    assert bak_path.read_text(encoding="utf-8") == original


def test_reset_backup_path_is_bak_extension(tmp_path):
    target = tmp_path / "snippets.json"
    target.write_text('{"snippets":[]}', encoding="utf-8")
    env = {ENV_KEY: str(target)}
    bak_path = reset_snippets_file(env)
    assert bak_path == target.with_suffix(".json.bak")


def test_reset_overwrites_previous_bak(tmp_path):
    target = tmp_path / "snippets.json"
    bak = tmp_path / "snippets.json.bak"
    bak.write_text("old backup", encoding="utf-8")
    target.write_text('{"snippets":[{"label":"New","text":"new"}]}', encoding="utf-8")
    env = {ENV_KEY: str(target)}
    bak_path = reset_snippets_file(env)
    assert bak_path.read_text(encoding="utf-8") != "old backup"


def test_reset_returns_none_when_no_existing_file(tmp_path):
    target = tmp_path / "snippets.json"
    env = {ENV_KEY: str(target)}
    bak_path = reset_snippets_file(env)
    assert bak_path is None


def test_reset_result_is_parseable_by_load_snippets(tmp_path):
    target = tmp_path / "snippets.json"
    env = {ENV_KEY: str(target)}
    reset_snippets_file(env)
    snippets = load_snippets(env)
    assert len(snippets) >= 1


def test_reset_creates_parent_dirs_if_needed(tmp_path):
    target = tmp_path / "sub" / "snippets.json"
    env = {ENV_KEY: str(target)}
    reset_snippets_file(env)
    assert target.exists()


def test_reset_copy2_failure_does_not_overwrite_original(tmp_path, monkeypatch):
    """If shutil.copy2 raises during backup, write_text must NOT be called and the
    original file content must remain untouched."""
    import shutil

    target = tmp_path / "snippets.json"
    original_content = '{"snippets":[{"label":"Safe","text":"do not lose me"}]}'
    target.write_text(original_content, encoding="utf-8")
    env = {ENV_KEY: str(target)}

    def _fail_copy2(src, dst):
        raise OSError("simulated disk full")

    monkeypatch.setattr(shutil, "copy2", _fail_copy2)

    with pytest.raises(OSError, match="simulated disk full"):
        reset_snippets_file(env)

    # Original file must be untouched
    assert target.read_text(encoding="utf-8") == original_content


# ---------------------------------------------------------------------------
# load_snippets_with_errors — OSError returns file_error, not entry_errors
# ---------------------------------------------------------------------------

def test_load_with_errors_oserror_returns_file_error(tmp_path, monkeypatch):
    """An unreadable file must set file_error, not entry_errors."""
    target = tmp_path / "snippets.json"
    target.write_text("{}", encoding="utf-8")
    env = {ENV_KEY: str(target)}

    from pathlib import Path

    original_read_text = Path.read_text

    def _fail_read(self, *args, **kwargs):
        if self == target:
            raise OSError("permission denied")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _fail_read)

    snippets, entry_errors, file_error = load_snippets_with_errors(env)
    assert snippets == []
    assert entry_errors == []
    assert file_error is not None
    assert "permission denied" in file_error or "read" in file_error.lower()


# ---------------------------------------------------------------------------
# SNIPPETS_TEMPLATE — RIGHT/WRONG example present
# ---------------------------------------------------------------------------

def test_template_contains_right_wrong_example():
    assert "RIGHT" in SNIPPETS_TEMPLATE
    assert "WRONG" in SNIPPETS_TEMPLATE


def test_template_right_example_has_label_and_text_keys():
    # The RIGHT example must show "label" and "text" as the correct keys.
    # The template is a raw JSON string so keys appear as either "label"/"text"
    # (in the snippets section) or as escaped \\"label\\"/\\"text\\" inside the
    # _README JSON string value. Either form is acceptable.
    right_idx = SNIPPETS_TEMPLATE.index("RIGHT")
    excerpt = SNIPPETS_TEMPLATE[right_idx: right_idx + 200]
    assert "label" in excerpt
    assert "text" in excerpt


def test_template_wrong_example_shows_bad_form():
    # The WRONG example should show incorrect usage (a bare key: value without label/text)
    wrong_idx = SNIPPETS_TEMPLATE.index("WRONG")
    excerpt = SNIPPETS_TEMPLATE[wrong_idx: wrong_idx + 200]
    # Should have something that looks like a mapping but without 'label'/'text' pattern
    assert "{" in excerpt or ":" in excerpt
