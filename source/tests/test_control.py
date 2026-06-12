from qt_window_test_helpers import *

import socket
import keystone_osk.control as control_module


def test_control_flag_commands_name_pins_boolean_cli_flags() -> None:
    assert control_module.CONTROL_FLAG_COMMANDS == ("show", "hide", "toggle", "quit")
    assert not hasattr(control_module, "CONTROL_COMMANDS")


def test_bare_launch_reuses_running_instance(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(keyboard_app, "send_control_command", lambda command: calls.append(command) or "OK")
    monkeypatch.setattr(keyboard_app, "QApplication", lambda args: pytest.fail("bare launch started a second Qt app"))
    assert keyboard_app.main([]) == 0
    assert calls == ["show"]


def test_bare_launch_reports_control_error(monkeypatch) -> None:
    monkeypatch.setattr(keyboard_app, "send_control_command", lambda command: "ERR unknown command")
    monkeypatch.setattr(keyboard_app, "QApplication", lambda args: pytest.fail("bare launch started Qt after control error"))
    assert keyboard_app.main([]) == 1


def test_cli_theme_forwards_to_running_instance(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(keyboard_app, "send_control_command", lambda command: calls.append(command) or "OK")
    monkeypatch.setattr(keyboard_app, "QApplication", lambda args: pytest.fail("theme launch started a second Qt app"))
    assert keyboard_app.main(["--theme", "mocha"]) == 0
    assert calls == ["theme mocha"]


def test_cli_mode_forwards_to_running_instance(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(keyboard_app, "send_control_command", lambda command: calls.append(command) or "OK")
    monkeypatch.setattr(keyboard_app, "QApplication", lambda args: pytest.fail("mode launch started a second Qt app"))
    assert keyboard_app.main(["--mode", "full"]) == 0
    assert calls == ["mode full"]


def test_cli_numpad_output_forwards_to_running_instance(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(keyboard_app, "send_control_command", lambda command: calls.append(command) or "OK")
    monkeypatch.setattr(keyboard_app, "QApplication", lambda args: pytest.fail("numpad launch started a second Qt app"))
    assert keyboard_app.main(["--numpad-output", "true-keypad"]) == 0
    assert calls == ["numpad true-keypad"]


def test_cli_status_prints_running_instance_status(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        keyboard_app,
        "send_control_command",
        lambda command: "OK status qt-platform=wayland input-backend=ydotoold/uinput theme=dark mode=compact visible=1 geometry=10,20,620x260",
    )
    monkeypatch.setattr(keyboard_app, "QApplication", lambda args: pytest.fail("status query started Qt"))

    assert keyboard_app.main(["--status"]) == 0

    assert capsys.readouterr().out.strip() == "qt-platform=wayland input-backend=ydotoold/uinput theme=dark mode=compact visible=1 geometry=10,20,620x260"


def test_cli_status_reports_missing_running_instance_without_starting_qt(monkeypatch, capsys) -> None:
    monkeypatch.setattr(keyboard_app, "send_control_command", lambda command: None)
    monkeypatch.setattr(keyboard_app, "QApplication", lambda args: pytest.fail("status query started Qt"))

    assert keyboard_app.main(["--status"]) == 1

    assert "no running app" in capsys.readouterr().err


def _running(monkeypatch):
    monkeypatch.setattr(keyboard_app, "send_control_command", lambda command: "ok pong" if command == "ping" else "OK")
    monkeypatch.setattr(keyboard_app, "QApplication", lambda args: pytest.fail("started a second Qt app while one was running"))


def test_cli_width_rejected_when_running(monkeypatch, capsys) -> None:
    _running(monkeypatch)
    assert keyboard_app.main(["--width", "900"]) == 2
    assert "already running" in capsys.readouterr().err


def test_cli_height_rejected_when_running(monkeypatch, capsys) -> None:
    _running(monkeypatch)
    assert keyboard_app.main(["--height", "300"]) == 2
    assert "already running" in capsys.readouterr().err


def test_cli_debug_keys_rejected_when_running(monkeypatch, capsys) -> None:
    _running(monkeypatch)
    assert keyboard_app.main(["--debug-keys"]) == 2
    assert "already running" in capsys.readouterr().err


def test_customized_launch_does_not_reuse_running_instance() -> None:
    args = keyboard_app.argparse.Namespace(
        screenshot=None,
        width=None,
        height=None,
        theme="light",
        numpad_output=None,
        debug_keys=False,
    )

    assert not keyboard_app.should_reuse_running_instance(args)


def test_screenshot_mode_does_not_control_running_instance() -> None:
    args = keyboard_app.argparse.Namespace(
        screenshot=keyboard_app.Path("/tmp/keystone-shot.png"),
        width=None,
        height=None,
        mode="full",
        theme=None,
        numpad_output=None,
        debug_keys=False,
    )

    assert keyboard_app.running_instance_commands(args, mode_requested=True) == []

def test_control_socket_path_uses_xdg_runtime_dir() -> None:
    assert keyboard_app.control_socket_path({"XDG_RUNTIME_DIR": "/run/user/1000"}) == keyboard_app.Path("/run/user/1000/keystone-osk.sock")

def test_control_socket_path_uses_uid_specific_tmp_fallback(monkeypatch) -> None:
    monkeypatch.setattr(control_module.os, "getuid", lambda: 1234)
    monkeypatch.setattr(control_module.tempfile, "gettempdir", lambda: "/tmp")

    assert keyboard_app.control_socket_path({}) == keyboard_app.Path("/tmp/keystone-osk-1234.sock")

def test_control_socket_path_fallback_honors_uid_environ(monkeypatch) -> None:
    monkeypatch.setattr(control_module.tempfile, "gettempdir", lambda: "/tmp")

    assert keyboard_app.control_socket_path({"UID": "5678"}) == keyboard_app.Path("/tmp/keystone-osk-5678.sock")

def test_bind_control_socket_refuses_live_socket(tmp_path, monkeypatch) -> None:
    socket_path = tmp_path / "keystone-osk.sock"
    socket_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(control_module, "_send_control_command_to_path", lambda path, command, timeout=0.4: "ok pong")

    with pytest.raises(control_module.ControlSocketInUseError):
        control_module.bind_control_socket(socket_path)

    assert socket_path.exists()  # live socket left untouched


def test_bind_control_socket_replaces_stale_socket(tmp_path, monkeypatch) -> None:
    socket_path = tmp_path / "keystone-osk.sock"
    stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    stale.bind(str(socket_path))
    stale.close()  # path remains, nothing listening (stale socket from a crashed process)
    monkeypatch.setattr(control_module, "_send_control_command_to_path", lambda path, command, timeout=0.4: None)

    sock = control_module.bind_control_socket(socket_path)
    try:
        assert socket_path.exists()
        assert sock.fileno() >= 0  # returned socket is the live, listening server socket
    finally:
        sock.close()
        socket_path.unlink(missing_ok=True)

def test_cli_invalid_theme_returns_exit_2_without_starting_qt(monkeypatch, capsys) -> None:
    monkeypatch.setattr(keyboard_app, "send_control_command", lambda command: None)  # no running instance
    monkeypatch.setattr(keyboard_app, "QApplication", lambda args: pytest.fail("invalid --theme started Qt"))
    result = keyboard_app.main(["--theme", "definitely-not-a-theme"])
    assert result == 2
    assert "definitely-not-a-theme" in capsys.readouterr().err


def test_cli_valid_theme_does_not_trigger_early_error(monkeypatch) -> None:
    # A valid --theme with a running instance should forward normally (exit 0),
    # not be blocked by the early validation guard.
    calls = []
    monkeypatch.setattr(keyboard_app, "send_control_command", lambda command: calls.append(command) or "OK")
    monkeypatch.setattr(keyboard_app, "QApplication", lambda args: pytest.fail("valid --theme should forward, not start Qt"))
    result = keyboard_app.main(["--theme", "dracula"])
    assert result == 0
    assert "theme dracula" in calls


def test_keyboard_window_control_socket_in_use_returns_exit_2(monkeypatch, capsys) -> None:
    # Simulate no running instance (send_control_command always returns None) so
    # main() proceeds to create a QApplication + KeyboardWindow.
    monkeypatch.setattr(keyboard_app, "send_control_command", lambda command: None)
    monkeypatch.setattr(keyboard_app, "instance_is_running", lambda: False)
    # Stub QApplication so we don't actually start Qt.
    monkeypatch.setattr(keyboard_app, "QApplication", lambda args: _FakeQApp())
    # Make KeyboardWindow raise ControlSocketInUseError to simulate bind race.
    monkeypatch.setattr(
        keyboard_app,
        "KeyboardWindow",
        lambda **kw: (_ for _ in ()).throw(control_module.ControlSocketInUseError("already bound")),
    )
    result = keyboard_app.main([])
    assert result == 2
    assert "already running" in capsys.readouterr().err


class _FakeQApp:
    def exec(self):
        return 0


def test_control_server_dispatches_arg_handler() -> None:
    from keystone_osk.control import KeyboardControlServer
    calls = []
    server = object.__new__(KeyboardControlServer)
    server._handlers = {
        "quit": lambda arg: calls.append(("quit", arg)) or "OK",
        "theme": lambda arg: calls.append(("theme", arg)) or ("OK" if arg == "mocha" else "ERR invalid theme"),
    }
    assert server._handle_command("quit") == "OK"
    assert server._handle_command("theme mocha") == "OK"
    assert server._handle_command("theme nope") == "ERR invalid theme"
    assert server._handle_command("bogus") == "ERR unknown command"
    assert server._handle_command("ping") == "ok pong"
    assert calls == [("quit", ""), ("theme", "mocha"), ("theme", "nope")]
