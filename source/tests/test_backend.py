import subprocess
import threading

import pytest

import keystone_osk.backend as backend_module
from keystone_osk.backend import BackendWorkerQueue, YdotoolBackend, keycode_for, ydotool_key_args
from keystone_osk.geometry import PositionedKey, Rect

# ---------------------------------------------------------------------------
# ClipboardWriter type alias used by injection tests
# ---------------------------------------------------------------------------
ClipboardWriter = object  # written by injected callable returning bool


def key(label: str) -> PositionedKey:
    return PositionedKey(label.lower(), label, Rect(0, 0, 1, 1))


def test_persistent_keyboard_window_uses_backend_worker_queue(app, tmp_path, monkeypatch) -> None:
    from PySide6.QtCore import QSize

    from keystone_osk.app import KeyboardWindow

    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(tmp_path / "window-state.json"))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=True)
    try:
        assert isinstance(window.backend, BackendWorkerQueue)
    finally:
        window._shutdown_backend()


def test_backend_worker_queue_runs_events_in_order() -> None:
    calls: list[tuple[str, str, tuple[str, ...]]] = []

    class Backend:
        def press_key(self, value: PositionedKey) -> None:
            calls.append(("press", value.label, ()))

        def press_key_with_modifiers(self, value: PositionedKey, modifiers: tuple[str, ...]) -> None:
            calls.append(("modified", value.label, modifiers))

        def type_text(self, text: str) -> None:
            calls.append(("text", text, ()))

        def type_unicode_text(self, text: str) -> None:
            calls.append(("unicode", text, ()))

    worker = BackendWorkerQueue(Backend())
    try:
        worker.press_key(key("a"))
        worker.press_key_with_modifiers(key("Delete"), ("Ctrl", "Alt"))
        worker.type_text("hello")
        worker.type_unicode_text("😀")
        worker.wait_idle()
    finally:
        worker.shutdown()

    assert calls == [
        ("press", "a", ()),
        ("modified", "Delete", ("Ctrl", "Alt")),
        ("text", "hello", ()),
        ("unicode", "😀", ()),
    ]


def test_backend_worker_queue_does_not_parallelize_events() -> None:
    first_started = threading.Event()
    release_first = threading.Event()
    calls: list[str] = []

    class Backend:
        def press_key(self, value: PositionedKey) -> None:
            first_started.set()
            release_first.wait(1)
            calls.append(value.label)

        def type_text(self, text: str) -> None:
            calls.append(text)

    worker = BackendWorkerQueue(Backend())
    try:
        worker.press_key(key("a"))
        assert first_started.wait(1)
        worker.type_text("after")
        assert calls == []
        release_first.set()
        worker.wait_idle()
    finally:
        worker.shutdown()

    assert calls == ["a", "after"]


def test_backend_worker_queue_reports_failures_and_keeps_running() -> None:
    errors: list[str] = []
    calls: list[str] = []

    class Backend:
        def press_key(self, value: PositionedKey) -> None:
            raise RuntimeError(f"failed {value.label}")

        def type_text(self, text: str) -> None:
            calls.append(text)

    worker = BackendWorkerQueue(Backend(), error_handler=lambda exc: errors.append(str(exc)))
    try:
        worker.press_key(key("a"))
        worker.type_text("still-runs")
        worker.wait_idle()
    finally:
        worker.shutdown()

    assert errors == ["failed a"]
    assert calls == ["still-runs"]


def test_backend_worker_queue_rejects_events_after_shutdown() -> None:
    worker = BackendWorkerQueue()
    worker.shutdown()

    with pytest.raises(RuntimeError, match="shut down"):
        worker.press_key(key("a"))


def test_ctrl_alt_delete_uses_delete_keycode() -> None:
    assert ydotool_key_args("Delete", modifiers=("Ctrl", "Alt")) == [
        "ydotool",
        "key",
        "--key-delay",
        "40",
        "29:1",
        "56:1",
        "111:1",
        "111:0",
        "56:0",
        "29:0",
    ]

def test_ydotool_key_args_can_address_keypad_keycodes() -> None:
    assert ydotool_key_args("KP7") == ["ydotool", "key", "71:1", "71:0"]
    assert ydotool_key_args("KPSlash") == ["ydotool", "key", "98:1", "98:0"]
    assert ydotool_key_args("KPEnter") == ["ydotool", "key", "96:1", "96:0"]

def test_ydotool_key_args_can_address_numlock() -> None:
    assert ydotool_key_args("NumLock") == ["ydotool", "key", "69:1", "69:0"]

def test_numlock_is_on_reads_led_brightness(tmp_path) -> None:
    led = tmp_path / "input3::numlock"
    led.mkdir()
    brightness = led / "brightness"

    brightness.write_text("1", encoding="utf-8")
    assert backend_module.numlock_is_on(str(tmp_path)) is True

    brightness.write_text("0", encoding="utf-8")
    assert backend_module.numlock_is_on(str(tmp_path)) is False

def test_numlock_is_on_returns_none_without_readable_led(tmp_path) -> None:
    assert backend_module.numlock_is_on(str(tmp_path)) is None

def test_ydotool_backend_ensures_numlock_on_when_led_is_off(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(backend_module, "numlock_is_on", lambda: False)
    backend = YdotoolBackend(runner=lambda args, check: calls.append((list(args), check)))

    backend.ensure_numlock_on()

    assert calls == [(["ydotool", "key", "69:1", "69:0"], True)]

def test_ydotool_backend_does_not_toggle_when_numlock_is_on_or_unknown(monkeypatch) -> None:
    calls = []
    backend = YdotoolBackend(runner=lambda args, check: calls.append((list(args), check)))

    monkeypatch.setattr(backend_module, "numlock_is_on", lambda: True)
    backend.ensure_numlock_on()
    monkeypatch.setattr(backend_module, "numlock_is_on", lambda: None)
    backend.ensure_numlock_on()

    assert calls == []

def test_ydotool_backend_ensure_numlock_on_is_graceful_when_toggle_fails(monkeypatch) -> None:
    monkeypatch.setattr(backend_module, "numlock_is_on", lambda: False)

    def run(args, check):
        raise subprocess.CalledProcessError(1, args)

    YdotoolBackend(runner=run).ensure_numlock_on()

def test_backend_worker_queue_forwards_ensure_numlock_on() -> None:
    calls: list[str] = []

    class Backend:
        def ensure_numlock_on(self) -> None:
            calls.append("ensure")

    worker = BackendWorkerQueue(Backend())
    try:
        worker.ensure_numlock_on()
        worker.wait_idle()
    finally:
        worker.shutdown()

    assert calls == ["ensure"]

def test_ydotool_backend_types_ascii_text_directly_via_ydotool_type() -> None:
    calls = []
    clipboard_reader_calls = []

    def clipboard_reader():
        clipboard_reader_calls.append(True)
        return None

    backend = YdotoolBackend(runner=lambda args, check: calls.append((list(args), check)), clipboard_reader=clipboard_reader)

    backend.type_text("you@example.com")

    assert calls == [
        (["ydotool", "type", "-d", "0", "-e", "0", "you@example.com"], True),
    ]
    assert clipboard_reader_calls == [], "clipboard must not be read for ASCII text"

def test_ydotool_backend_types_unicode_text_via_injected_writer() -> None:
    # Writer is called with the text; settle sleep and Ctrl+V follow.
    runner_calls = []
    writer_calls: list[str] = []

    def writer(text: str) -> bool:
        writer_calls.append(text)
        return True

    backend = YdotoolBackend(
        runner=lambda args, check: runner_calls.append((list(args), check)),
        clipboard_reader=lambda: None,
        clipboard_writer=writer,
        sleeper=lambda _delay: None,
    )

    backend.type_text("😀")

    assert writer_calls == ["😀"]
    assert runner_calls == [
        (["ydotool", "key", "29:1", "47:1", "47:0", "29:0"], True),
    ]


def test_ydotool_backend_falls_back_to_ydotool_type_when_writer_returns_false() -> None:
    runner_calls = []

    backend = YdotoolBackend(
        runner=lambda args, check: runner_calls.append((list(args), check)),
        clipboard_reader=lambda: None,
        clipboard_writer=lambda text: False,
        sleeper=lambda _delay: None,
    )

    backend.type_text("😀")

    assert runner_calls == [
        (["ydotool", "type", "-d", "0", "-e", "0", "😀"], True),
    ]


def test_ydotool_backend_falls_back_to_ydotool_type_when_writer_is_none() -> None:
    runner_calls = []

    backend = YdotoolBackend(
        runner=lambda args, check: runner_calls.append((list(args), check)),
        clipboard_reader=lambda: None,
        clipboard_writer=None,
        sleeper=lambda _delay: None,
    )

    backend.type_text("héllo")

    assert runner_calls == [
        (["ydotool", "type", "-d", "0", "-e", "0", "héllo"], True),
    ]


def test_ydotool_backend_settles_clipboard_before_paste_keystroke() -> None:
    # Settle sleep must fire after the writer is called but before Ctrl+V.
    events: list[tuple] = []

    def writer(text: str) -> bool:
        events.append(("write", text))
        return True

    def run(args, check):
        events.append(("run", args[0]))

    def sleeper(delay):
        events.append(("sleep", delay))

    backend = YdotoolBackend(
        runner=run,
        clipboard_reader=lambda: "previous-content",
        clipboard_writer=writer,
        sleeper=sleeper,
    )

    backend.type_text("héllo")

    write_idx = next(i for i, e in enumerate(events) if e[0] == "write")
    ctrl_v_idx = next(i for i, e in enumerate(events) if e == ("run", "ydotool"))
    settle_idx = next(
        i for i, e in enumerate(events) if e == ("sleep", backend_module.CLIPBOARD_SETTLE_DELAY_S)
    )
    assert write_idx < settle_idx < ctrl_v_idx, (
        f"settle sleep must be between writer call and Ctrl+V, got events: {events}"
    )


def test_ydotool_backend_restores_previous_clipboard_after_paste() -> None:
    runner_calls = []
    writer_calls: list[str] = []
    sleeps: list[float] = []

    backend = YdotoolBackend(
        runner=lambda args, check: runner_calls.append((list(args), check)),
        clipboard_reader=lambda: "previous-content",
        clipboard_writer=lambda text: writer_calls.append(text) or True,
        sleeper=sleeps.append,
    )

    backend.type_text("héllo")

    assert writer_calls == ["héllo", "previous-content"]
    assert runner_calls == [
        (["ydotool", "key", "29:1", "47:1", "47:0", "29:0"], True),
    ]
    assert sleeps == [backend_module.CLIPBOARD_SETTLE_DELAY_S, backend_module.CLIPBOARD_RESTORE_DELAY_S]


def test_ydotool_backend_restores_clipboard_even_when_paste_fails() -> None:
    runner_calls = []
    writer_calls: list[str] = []

    def run(args, check):
        runner_calls.append((list(args), check))
        if args[0] == "ydotool":
            raise subprocess.CalledProcessError(1, args)

    backend = YdotoolBackend(
        runner=run,
        clipboard_reader=lambda: "previous-content",
        clipboard_writer=lambda text: writer_calls.append(text) or True,
        sleeper=lambda _delay: None,
    )

    with pytest.raises(subprocess.CalledProcessError):
        backend.type_text("héllo")

    assert writer_calls == ["héllo", "previous-content"]
    assert runner_calls == [
        (["ydotool", "key", "29:1", "47:1", "47:0", "29:0"], True),
    ]


def test_ydotool_backend_skips_restore_when_clipboard_was_unreadable() -> None:
    runner_calls = []
    writer_calls: list[str] = []

    def sleeper(delay):
        # The settle sleep (CLIPBOARD_SETTLE_DELAY_S) is expected before Ctrl+V.
        # The restore sleep (CLIPBOARD_RESTORE_DELAY_S) must NOT fire when there
        # is nothing to restore.
        if delay == backend_module.CLIPBOARD_RESTORE_DELAY_S:
            pytest.fail("must not sleep for restore when there is nothing to restore")

    backend = YdotoolBackend(
        runner=lambda args, check: runner_calls.append((list(args), check)),
        clipboard_reader=lambda: None,
        clipboard_writer=lambda text: writer_calls.append(text) or True,
        sleeper=sleeper,
    )

    backend.type_text("héllo")

    assert writer_calls == ["héllo"]
    assert [args[0] for args, _check in runner_calls] == ["ydotool"]


def test_ydotool_backend_reader_none_means_no_restore() -> None:
    # When reader is None, previous is always None — no restore call.
    writer_calls: list[str] = []

    backend = YdotoolBackend(
        runner=lambda args, check: None,
        clipboard_reader=None,
        clipboard_writer=lambda text: writer_calls.append(text) or True,
        sleeper=lambda _delay: None,
    )

    backend.type_text("héllo")

    # writer called for the text but NOT for any restore
    assert writer_calls == ["héllo"]

def test_ydotool_backend_types_unicode_text_with_linux_unicode_input() -> None:
    calls = []
    backend = YdotoolBackend(runner=lambda args, check: calls.append((list(args), check)))

    backend.type_unicode_text("🔥")

    assert calls == [
        (["ydotool", "key", "29:1", "42:1", "22:1", "22:0", "42:0", "29:0"], True),
        (["ydotool", "key", "2:1", "2:0"], True),
        (["ydotool", "key", "33:1", "33:0"], True),
        (["ydotool", "key", "6:1", "6:0"], True),
        (["ydotool", "key", "3:1", "3:0"], True),
        (["ydotool", "key", "6:1", "6:0"], True),
        (["ydotool", "key", "28:1", "28:0"], True),
    ]


@pytest.mark.parametrize("label,code", [
    ("KP0", 82), ("KP1", 79), ("KP2", 80), ("KP3", 81), ("KP4", 75),
    ("KP5", 76), ("KP6", 77), ("KP7", 71), ("KP8", 72), ("KP9", 73),
    ("KPDot", 83), ("KPMinus", 74), ("KPPlus", 78), ("KPEnter", 96),
    ("KPSlash", 98), ("KPStar", 55),
])
def test_keycode_for_keypad_names(label, code) -> None:
    assert keycode_for(label) == code
