"""Pure tests for keystone_osk.autostart — no PySide6 required."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


# Verify the module is importable without PySide6.
from keystone_osk.autostart import (
    autostart_path,
    disable,
    enable,
    is_enabled,
    launcher_command,
)


# ---------------------------------------------------------------------------
# autostart_path
# ---------------------------------------------------------------------------


def test_autostart_path_uses_xdg_config_home(tmp_path: Path) -> None:
    environ = {"XDG_CONFIG_HOME": str(tmp_path / "config")}
    path = autostart_path(environ)
    assert path == tmp_path / "config" / "autostart" / "keystone-osk.desktop"


def test_autostart_path_defaults_to_home_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    environ: dict[str, str] = {}
    path = autostart_path(environ)
    assert path == Path.home() / ".config" / "autostart" / "keystone-osk.desktop"


# ---------------------------------------------------------------------------
# is_enabled
# ---------------------------------------------------------------------------


def test_is_enabled_false_when_file_missing(tmp_path: Path) -> None:
    environ = {"XDG_CONFIG_HOME": str(tmp_path / "config")}
    assert not is_enabled(environ)


def test_is_enabled_true_when_file_exists(tmp_path: Path) -> None:
    environ = {"XDG_CONFIG_HOME": str(tmp_path / "config")}
    dest = autostart_path(environ)
    dest.parent.mkdir(parents=True)
    dest.write_text("[Desktop Entry]\n", encoding="utf-8")
    assert is_enabled(environ)


# ---------------------------------------------------------------------------
# enable
# ---------------------------------------------------------------------------


def test_enable_creates_desktop_file(tmp_path: Path) -> None:
    environ = {"XDG_CONFIG_HOME": str(tmp_path / "config")}
    enable(environ)
    dest = autostart_path(environ)
    assert dest.exists()


def test_enable_desktop_file_contains_start_hidden(tmp_path: Path) -> None:
    environ = {"XDG_CONFIG_HOME": str(tmp_path / "config")}
    enable(environ)
    content = autostart_path(environ).read_text(encoding="utf-8")
    assert "--start-hidden" in content


def test_enable_desktop_file_has_required_fields(tmp_path: Path) -> None:
    environ = {"XDG_CONFIG_HOME": str(tmp_path / "config")}
    enable(environ)
    content = autostart_path(environ).read_text(encoding="utf-8")
    assert "[Desktop Entry]" in content
    assert "Type=Application" in content
    assert "Name=Keystone OSK" in content
    assert "Exec=" in content
    assert "Icon=keystone" in content
    assert "X-GNOME-Autostart-enabled=true" in content


def test_enable_no_tmp_file_left_behind(tmp_path: Path) -> None:
    environ = {"XDG_CONFIG_HOME": str(tmp_path / "config")}
    enable(environ)
    config_dir = tmp_path / "config" / "autostart"
    tmp_files = list(config_dir.glob("*.tmp"))
    assert tmp_files == []


def test_enable_is_idempotent(tmp_path: Path) -> None:
    environ = {"XDG_CONFIG_HOME": str(tmp_path / "config")}
    enable(environ)
    enable(environ)
    assert is_enabled(environ)


def test_enable_creates_parent_directories(tmp_path: Path) -> None:
    environ = {"XDG_CONFIG_HOME": str(tmp_path / "deep" / "config")}
    enable(environ)
    assert is_enabled(environ)


# ---------------------------------------------------------------------------
# disable
# ---------------------------------------------------------------------------


def test_disable_removes_desktop_file(tmp_path: Path) -> None:
    environ = {"XDG_CONFIG_HOME": str(tmp_path / "config")}
    enable(environ)
    assert is_enabled(environ)
    disable(environ)
    assert not is_enabled(environ)


def test_disable_is_idempotent_when_missing(tmp_path: Path) -> None:
    environ = {"XDG_CONFIG_HOME": str(tmp_path / "config")}
    # Should not raise even if file was never created.
    disable(environ)
    disable(environ)
    assert not is_enabled(environ)


# ---------------------------------------------------------------------------
# launcher_command
# ---------------------------------------------------------------------------


def test_launcher_command_returns_a_string() -> None:
    cmd = launcher_command()
    assert isinstance(cmd, str)
    assert len(cmd) > 0


def test_launcher_command_contains_keystone_or_python() -> None:
    cmd = launcher_command()
    assert "keystone" in cmd or "python" in cmd or sys.executable in cmd


def test_launcher_command_prefers_local_bin_when_executable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_local_bin = tmp_path / ".local" / "bin"
    fake_local_bin.mkdir(parents=True)
    fake_launcher = fake_local_bin / "keystone-osk"
    fake_launcher.write_text("#!/bin/sh\nexec true\n")
    fake_launcher.chmod(0o755)

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    cmd = launcher_command()
    assert "keystone-osk" in cmd


def test_launcher_command_falls_back_to_python_when_no_launcher(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Point home at a temp dir with no keystone-osk in it.
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr("keystone_osk.autostart.shutil.which", lambda name: None)

    cmd = launcher_command()
    assert "-m keystone_osk" in cmd
