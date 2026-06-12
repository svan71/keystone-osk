"""Tests for the snippets row in doctor_report."""
from __future__ import annotations

import json

import keystone_osk.doctor as doctor_module

ENV_KEY = "KEYSTONE_OSK_SNIPPETS_FILE"

_STUB_KWARGS = dict(
    command_sender=lambda command, environ=None: None,
    process_running=lambda: False,
    which=lambda name: None,
    uinput_checker=lambda: ("OK", "/dev/uinput writable"),
    tray_checker=lambda: "unknown (no Qt application)",
    icon_resolver=lambda theme: "generated pixmap",
)


def _write(tmp_path, payload) -> dict[str, str]:
    target = tmp_path / "snippets.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return {ENV_KEY: str(target)}


def test_doctor_snippets_ok_when_all_parse(tmp_path):
    env = _write(tmp_path, {"snippets": [
        {"label": "Email", "text": "a@b.com"},
        {"label": "Sign", "text": "Thanks!"},
    ]})
    lines = doctor_module.doctor_report(env, **_STUB_KWARGS)
    assert any("OK snippets: 2 loaded" in line for line in lines)


def test_doctor_snippets_warn_for_invalid_entries(tmp_path):
    env = _write(tmp_path, {"snippets": [
        {"Gmail": "bad"},                       # invalid
        {"label": "Good", "text": "ok"},
    ]})
    lines = doctor_module.doctor_report(env, **_STUB_KWARGS)
    assert any(
        line.startswith("WARN snippets:") and "1 loaded" in line and "1 invalid" in line
        for line in lines
    )


def test_doctor_snippets_warn_message_includes_edit_hint(tmp_path):
    env = _write(tmp_path, {"snippets": [
        {"bad": "entry"},
        {"label": "Good", "text": "ok"},
    ]})
    lines = doctor_module.doctor_report(env, **_STUB_KWARGS)
    warn_line = next(l for l in lines if l.startswith("WARN snippets:") and "invalid" in l)
    # Must include a hint to edit the file
    assert "edit" in warn_line.lower() or "snippets.json" in warn_line


def test_doctor_snippets_warn_for_invalid_json(tmp_path):
    target = tmp_path / "snippets.json"
    target.write_text("{ not json", encoding="utf-8")
    env = {ENV_KEY: str(target)}
    lines = doctor_module.doctor_report(env, **_STUB_KWARGS)
    assert any(
        line.startswith("WARN snippets:") and ("invalid JSON" in line or "not valid JSON" in line)
        for line in lines
    )


def test_doctor_snippets_warn_file_error_for_oserror(tmp_path, monkeypatch):
    """An unreadable file must produce 'file error' label, not 'invalid JSON'."""
    from pathlib import Path

    target = tmp_path / "snippets.json"
    target.write_text("{}", encoding="utf-8")
    env = {ENV_KEY: str(target)}

    original_read_text = Path.read_text

    def _fail_read(self, *args, **kwargs):
        if self == target:
            raise OSError("permission denied")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _fail_read)

    lines = doctor_module.doctor_report(env, **_STUB_KWARGS)
    assert any(
        line.startswith("WARN snippets:") and "file error" in line
        for line in lines
    ), f"Expected 'WARN snippets: file error ...' in: {lines}"
    # Must NOT say "invalid JSON" for an OSError
    assert not any(
        line.startswith("WARN snippets:") and "invalid JSON" in line
        for line in lines
    )


def test_doctor_snippets_info_when_file_missing(tmp_path):
    env = {ENV_KEY: str(tmp_path / "nope.json")}
    lines = doctor_module.doctor_report(env, **_STUB_KWARGS)
    assert any(
        line.startswith("INFO snippets:") and "not created" in line
        for line in lines
    )


def test_doctor_snippets_line_present_in_full_report(tmp_path):
    """Any snippets status line must appear — just check one is always there."""
    env = {ENV_KEY: str(tmp_path / "nope.json")}
    lines = doctor_module.doctor_report(env, **_STUB_KWARGS)
    assert any("snippets" in line for line in lines)
