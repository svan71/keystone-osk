from __future__ import annotations

import errno
import os
import socket
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path

from keystone_osk.constants import APP_ID, SOCKET_NAME

CONTROL_FLAG_COMMANDS = ("show", "hide", "toggle", "quit")
CONTROL_SOCKET_NAME = SOCKET_NAME


class ControlSocketInUseError(RuntimeError):
    pass


def control_socket_path(environ: Mapping[str, str] | None = None) -> Path:
    values = os.environ if environ is None else environ
    runtime_dir = values.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        return Path(runtime_dir) / CONTROL_SOCKET_NAME
    uid = values.get("UID") or str(os.getuid())
    return Path(tempfile.gettempdir()) / f"{APP_ID}-{uid}.sock"


def send_control_command(command: str, timeout: float = 0.4, environ: Mapping[str, str] | None = None) -> str | None:
    return _send_control_command_to_path(control_socket_path(environ), command, timeout)


def _send_control_command_to_path(path: Path, command: str, timeout: float = 0.4) -> str | None:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(timeout)
            client.connect(str(path))
            client.sendall(f"{command}\n".encode("utf-8"))
            return client.recv(256).decode("utf-8", errors="replace").strip()
    except OSError:
        return None


def bind_control_socket(path: Path) -> socket.socket:
    """Bind and return the live listening server socket. Never unlinks a live one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.setblocking(False)
    try:
        server.bind(str(path))
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            server.close()
            raise
        # Something is at the path. If it answers ping, it's a live instance.
        if _send_control_command_to_path(path, "ping", timeout=0.15) == "ok pong":
            server.close()
            raise ControlSocketInUseError(f"control socket already in use: {path}")
        # Dead/stale: remove and bind once more, keeping that socket.
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        # A third process could grab the path here; if so, bind raises and the caller handles it.
        try:
            server.bind(str(path))
        except OSError:
            server.close()
            raise
    try:
        os.chmod(path, 0o600)
        server.listen(8)
    except OSError:
        server.close()
        raise
    return server


class KeyboardControlServer:
    def __init__(self, parent, handlers: Mapping[str, Callable[[str], str]]) -> None:
        from PySide6.QtCore import QSocketNotifier

        self._handlers = dict(handlers)
        self._path = control_socket_path()
        self._server = bind_control_socket(self._path)
        self._notifier = QSocketNotifier(self._server.fileno(), QSocketNotifier.Type.Read, parent)
        self._notifier.activated.connect(self._accept_commands)

    def _accept_commands(self) -> None:
        while True:
            try:
                connection, _ = self._server.accept()
            except BlockingIOError:
                return
            with connection:
                # accept()ed sockets are blocking; a client that connects but
                # never sends would otherwise hang the Qt main thread in recv().
                try:
                    connection.settimeout(0.5)
                    command = connection.recv(128).decode("utf-8", errors="replace").strip()
                    connection.sendall(f"{self._handle_command(command)}\n".encode("utf-8"))
                except OSError:
                    continue

    def _handle_command(self, command: str) -> str:
        if command == "ping":
            return "ok pong"
        parts = command.split(maxsplit=1)
        verb = parts[0] if parts else ""
        arg = parts[1] if len(parts) > 1 else ""
        handler = self._handlers.get(verb)
        if handler is None:
            return "ERR unknown command"
        return handler(arg)
