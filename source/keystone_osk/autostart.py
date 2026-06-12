"""XDG autostart support — pure (no PySide6).

Toggling on writes ~/.config/autostart/keystone-osk.desktop (respecting
XDG_CONFIG_HOME); toggling off deletes it. Checkbox state = file exists.
"""

from __future__ import annotations

import shlex
import shutil
import sys
from collections.abc import Mapping
from pathlib import Path

_DESKTOP_TEMPLATE = """\
[Desktop Entry]
Type=Application
Name=Keystone OSK
Comment=On-screen keyboard
Exec={exec_line}
Icon=keystone
X-GNOME-Autostart-enabled=true
"""


def autostart_path(environ: Mapping[str, str]) -> Path:
    """Return the autostart .desktop path, honouring XDG_CONFIG_HOME."""
    config_home = environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config_home) / "autostart" / "keystone-osk.desktop"


def is_enabled(environ: Mapping[str, str]) -> bool:
    """Return True if the autostart .desktop file exists."""
    return autostart_path(environ).exists()


def launcher_command() -> str:
    """Return the best available launcher path for keystone-osk.

    Preference order:
    1. ~/.local/bin/keystone-osk if executable
    2. shutil.which("keystone-osk")
    3. <sys.executable> -m keystone_osk
    """
    local_bin = Path.home() / ".local" / "bin" / "keystone-osk"
    if local_bin.is_file() and local_bin.stat().st_mode & 0o111:
        return shlex.quote(str(local_bin))
    found = shutil.which("keystone-osk")
    if found is not None:
        return shlex.quote(found)
    return f"{shlex.quote(sys.executable)} -m keystone_osk"


def enable(environ: Mapping[str, str]) -> None:
    """Write the autostart .desktop file atomically.

    Raises OSError on failure; no .tmp file is left behind.
    """
    dest = autostart_path(environ)
    dest.parent.mkdir(parents=True, exist_ok=True)
    exec_line = f"{launcher_command()} --start-hidden"
    content = _DESKTOP_TEMPLATE.format(exec_line=exec_line)
    tmp = dest.with_suffix(".desktop.tmp")
    tmp.write_text(content, encoding="utf-8")
    try:
        tmp.replace(dest)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def disable(environ: Mapping[str, str]) -> None:
    """Remove the autostart .desktop file; no-op if already gone."""
    autostart_path(environ).unlink(missing_ok=True)
