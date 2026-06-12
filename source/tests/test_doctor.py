from logic_test_helpers import *

def test_doctor_report_summarizes_runtime_checks(monkeypatch, tmp_path) -> None:
    state_home = tmp_path / "state"
    (state_home / "keystone-osk").mkdir(parents=True)
    (state_home / "keystone-osk" / "window-state.json").write_text('{"theme":"dracula"}', encoding="utf-8")
    report = doctor_module.doctor_report(
        {
            "XDG_RUNTIME_DIR": "/run/user/1000",
            "XDG_CURRENT_DESKTOP": "GNOME",
            "XDG_SESSION_TYPE": "wayland",
            "DISPLAY": ":0",
            "WAYLAND_DISPLAY": "wayland-0",
            "XDG_CONFIG_HOME": "/home/user/.config",
            "XDG_DATA_HOME": "/home/user/.local/share",
            "XDG_STATE_HOME": str(state_home),
        },
        command_sender=lambda command, environ=None: "ok pong" if command == "ping" else "OK status qt-platform=wayland theme=dracula mode=compact visible=1 geometry=10,20,620x260",
        process_running=lambda: True,
        which=lambda name: f"/usr/bin/{name}" if name in {"ydotool"} else None,
        uinput_checker=lambda: ("OK", "/dev/uinput writable"),
        tray_checker=lambda: "yes",
        icon_resolver=lambda theme: "theme:keystone-status-dracula-symbolic",
    )

    assert any(line.startswith("INFO version: ") for line in report)
    assert any(line.startswith("INFO python: ") for line in report)
    # doctor_report only formats whatever importable_package_version() returns;
    # asserting the line is present keeps this test pure (passes with or without
    # PySide6 installed) rather than asserting on the test machine's environment.
    assert any(line.startswith("INFO pyside6: ") for line in report)
    assert "INFO qt-platform: xcb" in report
    assert "INFO input-backend: ydotoold/uinput" in report
    assert "INFO clipboard: built-in (Qt QClipboard via xcb/Wayland)" in report
    assert "OK ydotool: /usr/bin/ydotool" in report
    assert "OK ydotoold: running" in report
    assert "OK uinput: /dev/uinput writable" in report
    assert "OK control: running" in report
    assert "INFO desktop: GNOME" in report
    assert f"INFO state: {state_home}/keystone-osk/window-state.json" in report
    assert f"INFO words: {state_home}/keystone-osk/words.json" in report
    assert "INFO control-socket: /run/user/1000/keystone-osk.sock" in report
    assert "INFO theme: dracula (Dracula)" in report
    assert any(line.startswith("INFO theme-path: ") and line.endswith("/keystone_osk/themes/dracula/theme.json") for line in report)
    assert "INFO theme-search: /home/user/.local/share/keystone/themes, /usr/share/keystone/themes, " in "\n".join(report)
    assert any(line.startswith("INFO theme-pack: dracula\tDracula\tvalid\tinherits=none\t") for line in report)
    assert "INFO tray-available: yes" in report
    assert "INFO tray-icon: theme:keystone-status-dracula-symbolic" in report
    assert "INFO layout: compact" in report
    assert "INFO running-status: qt-platform=wayland theme=dracula mode=compact visible=1 geometry=10,20,620x260" in report


def test_doctor_reports_first_run_detected_theme_when_none_saved(tmp_path) -> None:
    state_home = tmp_path / "state"
    report = doctor_module.doctor_report(
        {"XDG_STATE_HOME": str(state_home), "XDG_DATA_HOME": "/home/user/.local/share"},
        command_sender=lambda command, environ=None: "ok pong",
        process_running=lambda: True,
        which=lambda name: None,
        uinput_checker=lambda: ("OK", "ok"),
        tray_checker=lambda: "yes",
        icon_resolver=lambda theme: "generated pixmap",
        color_scheme_detector=lambda: "light",
    )

    assert "INFO theme: light (Light)" in report


def test_doctor_report_warns_for_common_setup_problems(tmp_path) -> None:
    report = doctor_module.doctor_report(
        {
            "XDG_RUNTIME_DIR": str(tmp_path / "missing-runtime"),
            "XDG_STATE_HOME": str(tmp_path / "state"),
        },
        command_sender=lambda command, environ=None: None,
        process_running=lambda: False,
        which=lambda name: None,
        uinput_checker=lambda: ("WARN", "/dev/uinput not writable; add user/group uinput access"),
        tray_checker=lambda: "unknown (no Qt application)",
        icon_resolver=lambda theme: "generated pixmap",
    )

    assert "WARN ydotool: not found" in report
    assert "WARN ydotoold: not running" in report
    assert "WARN uinput: /dev/uinput not writable; add user/group uinput access" in report
    assert "WARN setup: install ydotool" in report
    assert "WARN setup: start ydotoold" in report
    assert "WARN setup: fix /dev/uinput permissions" in report
    assert "WARN setup: no DISPLAY or WAYLAND_DISPLAY" in report
    assert "WARN setup: Keystone control socket is not responding" in report


def test_resolved_tray_icon_kde_reports_generated_when_no_theme_icon() -> None:
    # On KDE, build_tray_icon short-circuits to the generated icon before the
    # bundled SVG, so the doctor must report the same (not the SVG path).
    import keystone_osk.doctor as doctor_module
    result = doctor_module.resolved_tray_icon(
        "mocha",
        has_theme_icon=lambda name: False,
        is_kde=True,
        bundled_path=doctor_module.BUNDLED_TRAY_ICON_PATH,
    )
    assert result == "generated pixmap"


def test_resolved_tray_icon_gnome_reports_bundled_svg(tmp_path) -> None:
    import keystone_osk.doctor as doctor_module
    bundled = tmp_path / "tray.svg"
    bundled.write_text("<svg/>", encoding="utf-8")
    result = doctor_module.resolved_tray_icon(
        "dracula",
        has_theme_icon=lambda name: False,
        is_kde=False,
        bundled_path=bundled,
    )
    assert result == str(bundled)


def test_resolved_tray_icon_exact_theme_icon_wins_on_kde() -> None:
    import keystone_osk.doctor as doctor_module
    result = doctor_module.resolved_tray_icon(
        "mocha",
        has_theme_icon=lambda name: name == "keystone-status-mocha-symbolic",
        is_kde=True,
    )
    assert result == "theme:keystone-status-mocha-symbolic"


def test_doctor_reports_numpad_mode_and_theme_source(tmp_path) -> None:
    import keystone_osk.doctor as doctor_module
    lines = doctor_module.doctor_report(
        {"XDG_STATE_HOME": str(tmp_path)},
        command_sender=lambda *a, **k: None,
        process_running=lambda: False,
        which=lambda name: None,
        uinput_checker=lambda: ("OK", "/dev/uinput writable"),
        tray_checker=lambda: "unknown (no Qt application)",
        icon_resolver=lambda theme: "generated pixmap",
    )
    assert any(line.startswith("INFO numpad-mode:") for line in lines)
    assert any(line.startswith("INFO theme-source:") for line in lines)
