# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from keystone_osk import __version__
from keystone_osk.constants import APP_ID, APP_NAME
from keystone_osk.config import app_config_dir, learned_words_path, window_state_path
from keystone_osk.control import control_socket_path, send_control_command
from keystone_osk.platform import detect_color_scheme, is_kde_session, preferred_qt_platform
from keystone_osk.state_io import load_keyboard_mode, load_numpad_output_mode, persisted_keyboard_theme
from keystone_osk.theme import (
    _theme_source,
    first_run_theme_id,
    theme_display_label,
    theme_pack_path,
    theme_pack_report_lines,
    theme_pack_search_dirs,
)
from keystone_osk.tray_icon_names import BUNDLED_TRAY_ICON_PATH, tray_icon_system_fallback_candidates, tray_icon_theme_candidates


def app_version() -> str:
    try:
        return version(APP_ID)
    except PackageNotFoundError:
        return __version__


def package_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "not installed"


def importable_package_version(package_name: str) -> str:
    try:
        importlib.import_module(package_name)
    except Exception:
        return "not installed"
    return package_version(package_name)


def ydotoold_is_running() -> bool:
    try:
        return subprocess.run(["pgrep", "-x", "ydotoold"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=3).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def display_server(values: Mapping[str, str]) -> str:
    if values.get("WAYLAND_DISPLAY"):
        return "wayland"
    if values.get("DISPLAY"):
        return "x11"
    return "none"


def uinput_status(path: Path = Path("/dev/uinput"), access: Callable[[str | Path, int], bool] = os.access) -> tuple[str, str]:
    if not path.exists():
        return "WARN", f"{path} missing; install/load uinput support"
    if not access(path, os.R_OK | os.W_OK):
        return "WARN", f"{path} not writable; add user/group uinput access"
    return "OK", f"{path} writable"


def tray_available_status() -> str:
    try:
        from PySide6.QtWidgets import QApplication, QSystemTrayIcon
    except Exception:
        return "unknown (PySide6 unavailable)"
    if QApplication.instance() is None:
        return "unknown (no Qt application)"
    return "yes" if QSystemTrayIcon.isSystemTrayAvailable() else "no"


def resolved_tray_icon(theme: str, *, has_theme_icon: Callable[[str], bool] | None = None, bundled_path: Path = BUNDLED_TRAY_ICON_PATH, is_kde: bool | None = None) -> str:
    effective_kde = is_kde_session() if is_kde is None else is_kde
    if has_theme_icon is None:
        try:
            from PySide6.QtGui import QIcon

            has_theme_icon = QIcon.hasThemeIcon
        except Exception:
            has_theme_icon = lambda name: False
    for icon_name in tray_icon_theme_candidates(theme):
        if has_theme_icon(icon_name):
            return f"theme:{icon_name}"
    if effective_kde:
        return "generated pixmap"
    if bundled_path.exists():
        return str(bundled_path)
    for icon_name in tray_icon_system_fallback_candidates():
        if has_theme_icon(icon_name):
            return f"theme:{icon_name}"
    return "generated pixmap"


def _snippets_status_line(environ: Mapping[str, str] | None = None) -> str:
    from keystone_osk.config import snippets_path
    from keystone_osk.snippets import load_snippets_with_errors

    path = snippets_path(environ)
    if not path.exists():
        return "INFO snippets: file not created yet"
    snippets, entry_errors, file_error = load_snippets_with_errors(environ)
    if file_error is not None:
        short_msg = file_error.split(":", 1)[-1].strip()
        if "not valid JSON" in file_error or "invalid JSON" in file_error:
            return f"WARN snippets: invalid JSON — {short_msg}"
        return f"WARN snippets: file error — {short_msg}"
    if entry_errors:
        n_loaded = len(snippets)
        n_invalid = len(entry_errors)
        return (
            f"WARN snippets: {n_loaded} loaded, {n_invalid} invalid"
            f" (edit ~/.config/keystone-osk/snippets.json)"
        )
    return f"OK snippets: {len(snippets)} loaded"


def doctor_report(
    environ: Mapping[str, str] | None = None,
    *,
    command_sender: Callable[..., str | None] = send_control_command,
    process_running: Callable[[], bool] = ydotoold_is_running,
    which: Callable[[str], str | None] = shutil.which,
    uinput_checker: Callable[[], tuple[str, str]] = uinput_status,
    tray_checker: Callable[[], str] = tray_available_status,
    icon_resolver: Callable[[str], str] = resolved_tray_icon,
    color_scheme_detector: Callable[[], str | None] = detect_color_scheme,
) -> list[str]:
    values = os.environ if environ is None else environ
    lines = [f"{APP_NAME} doctor"]
    lines.append(f"INFO version: {app_version()}")
    lines.append(f"INFO python: {sys.version.split()[0]}")
    lines.append(f"INFO pyside6: {importable_package_version('PySide6')}")
    qt_platform = values.get("QT_QPA_PLATFORM") or preferred_qt_platform(values)
    lines.append(f"INFO qt-platform: {qt_platform}")
    lines.append("INFO input-backend: ydotoold/uinput")
    ydotool_path = which("ydotool")
    lines.append(f"{'OK' if ydotool_path else 'WARN'} ydotool: {ydotool_path or 'not found'}")
    ydotoold_running = process_running()
    lines.append(f"{'OK' if ydotoold_running else 'WARN'} ydotoold: {'running' if ydotoold_running else 'not running'}")
    uinput_level, uinput_message = uinput_checker()
    lines.append(f"{uinput_level} uinput: {uinput_message}")
    lines.append("INFO clipboard: built-in (Qt QClipboard via xcb/Wayland)")
    runtime_dir = values.get("XDG_RUNTIME_DIR")
    runtime_ok = bool(runtime_dir and Path(runtime_dir).is_dir())
    lines.append(f"{'OK' if runtime_ok else 'WARN'} XDG_RUNTIME_DIR: {runtime_dir or 'unset'}")
    lines.append(f"INFO desktop: {values.get('XDG_CURRENT_DESKTOP') or 'unknown'}")
    lines.append(f"INFO session: {values.get('XDG_SESSION_TYPE') or 'unknown'}")
    lines.append(f"INFO display-server: {display_server(values)}")
    lines.append(f"INFO display: DISPLAY={values.get('DISPLAY') or 'unset'} WAYLAND_DISPLAY={values.get('WAYLAND_DISPLAY') or 'unset'}")
    lines.append(f"INFO config: {app_config_dir(values)}")
    lines.append(f"INFO state: {window_state_path(values)}")
    lines.append(f"INFO words: {learned_words_path(values)}")
    lines.append(f"INFO control-socket: {control_socket_path(values)}")
    lines.append(_snippets_status_line(environ))
    state_path = window_state_path(values)
    # Mirror the app's startup choice: a saved theme wins, otherwise first launch
    # follows the desktop's light/dark preference (Dark/Light, never Dracula).
    current_theme = persisted_keyboard_theme(state_path) or first_run_theme_id(color_scheme_detector())
    lines.append(f"INFO theme: {current_theme} ({theme_display_label(current_theme, values)})")
    active_theme_path = theme_pack_path(current_theme, values)
    lines.append(f"INFO theme-path: {active_theme_path or 'not found'}")
    lines.append(f"INFO theme-source: {_theme_source(current_theme, values)}")
    lines.append("INFO theme-search: " + ", ".join(str(path) for path in theme_pack_search_dirs(values)))
    pack_report = theme_pack_report_lines(values)
    lines.extend(f"INFO theme-pack: {line}" for line in pack_report)
    for report in pack_report:
        fields = report.split("\t")
        status = fields[2] if len(fields) > 2 else ""
        if status.startswith("invalid"):
            lines.append(f"WARN theme-pack: {fields[0]} {status}")
    lines.append(f"INFO numpad-mode: {load_numpad_output_mode(state_path)}")
    lines.append(f"INFO tray-available: {tray_checker()}")
    lines.append(f"INFO tray-icon: {icon_resolver(current_theme)}")
    lines.append(f"INFO layout: {load_keyboard_mode(state_path)}")
    response = command_sender("ping", environ=values)
    lines.append(f"{'OK' if response == 'ok pong' else 'WARN'} control: {'running' if response == 'ok pong' else 'not responding'}")
    if response == "ok pong":
        status_response = command_sender("status", environ=values)
        if status_response and status_response.startswith("OK status "):
            lines.append(f"INFO running-status: {status_response.removeprefix('OK status ')}")
    if not ydotool_path:
        lines.append("WARN setup: install ydotool")
    if not ydotoold_running:
        lines.append("WARN setup: start ydotoold")
    if uinput_level != "OK":
        lines.append("WARN setup: fix /dev/uinput permissions")
    if display_server(values) == "none":
        lines.append("WARN setup: no DISPLAY or WAYLAND_DISPLAY")
    if response != "ok pong":
        lines.append("WARN setup: Keystone control socket is not responding")
    return lines
