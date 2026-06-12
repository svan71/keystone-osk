from qt_window_test_helpers import *
from keystone_osk.widgets import ModifierCancelOverlay


# ---------------------------------------------------------------------------
# Emoji-cancel overlay: separate non-popup overlay (new)
# ---------------------------------------------------------------------------

def test_emoji_cancel_overlay_is_distinct_from_modifier_cancel_overlay(app) -> None:
    """_emoji_cancel_overlay must be a separate object from _modifier_cancel_overlay."""
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    assert hasattr(window, "_emoji_cancel_overlay"), "_emoji_cancel_overlay must exist"
    assert window._emoji_cancel_overlay is not window._modifier_cancel_overlay
    window.close()


def test_emoji_cancel_overlay_flags_no_popup(app) -> None:
    """_emoji_cancel_overlay and its child segments must have Tool as the window type, not bare Popup.

    Qt's Tool flag (0xb) is a superset of Popup bits (0x9).  The distinguishing
    check is that the low-nibble window-type field equals Tool, NOT the bare
    Popup value.  A window created with Qt.Popup has low nibble 0x9; one created
    with Qt.Tool has 0xb (Popup | extra-bit).  We verify the extra bit is set so
    the compositor treats this as a passive tool window rather than a grab-owner.
    """
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    overlay = window._emoji_cancel_overlay
    _WTYPE_MASK = 0xF
    tool_val = int(Qt.WindowType.Tool) & _WTYPE_MASK   # 0xb
    popup_val = int(Qt.WindowType.Popup) & _WTYPE_MASK  # 0x9
    # Parent segment: window type must be Tool (0xb), not bare Popup (0x9)
    parent_type = int(overlay.windowFlags()) & _WTYPE_MASK
    assert parent_type == tool_val, f"parent window type must be Tool (0x{tool_val:x}), got 0x{parent_type:x}"
    assert parent_type != popup_val, "parent must not be bare Popup"
    # Child segments
    for i, seg in enumerate(overlay._segments):
        seg_type = int(seg.windowFlags()) & _WTYPE_MASK
        assert seg_type == tool_val, f"segment {i} window type must be Tool (0x{tool_val:x}), got 0x{seg_type:x}"
    window.close()


def test_emoji_cancel_overlay_flags_has_tool(app) -> None:
    """_emoji_cancel_overlay and its child segments must have Tool as window type (0xb in low nibble)."""
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    overlay = window._emoji_cancel_overlay
    _WTYPE_MASK = 0xF
    tool_val = int(Qt.WindowType.Tool) & _WTYPE_MASK  # 0xb
    parent_type = int(overlay.windowFlags()) & _WTYPE_MASK
    assert parent_type == tool_val, f"parent must have Tool window type (0x{tool_val:x}), got 0x{parent_type:x}"
    for i, seg in enumerate(overlay._segments):
        seg_type = int(seg.windowFlags()) & _WTYPE_MASK
        assert seg_type == tool_val, f"segment {i} must have Tool window type (0x{tool_val:x}), got 0x{seg_type:x}"
    window.close()


def test_modifier_cancel_overlay_still_has_popup(app) -> None:
    """_modifier_cancel_overlay (used for menus) must have bare Popup as window type, not Tool."""
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    overlay = window._modifier_cancel_overlay
    _WTYPE_MASK = 0xF
    popup_val = int(Qt.WindowType.Popup) & _WTYPE_MASK  # 0x9
    tool_val = int(Qt.WindowType.Tool) & _WTYPE_MASK    # 0xb
    parent_type = int(overlay.windowFlags()) & _WTYPE_MASK
    assert parent_type == popup_val, f"modifier overlay parent must be Popup (0x{popup_val:x}), got 0x{parent_type:x}"
    assert parent_type != tool_val, "modifier overlay parent must not be Tool"
    for i, seg in enumerate(overlay._segments):
        seg_type = int(seg.windowFlags()) & _WTYPE_MASK
        assert seg_type == popup_val, f"modifier overlay segment {i} must be Popup (0x{popup_val:x}), got 0x{seg_type:x}"
    window.close()


def test_opening_emoji_picker_shows_emoji_cancel_overlay(app, monkeypatch) -> None:
    """Opening the picker must show _emoji_cancel_overlay, not _modifier_cancel_overlay."""
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    emoji_shown = {}
    modifier_shown = {}
    monkeypatch.setattr(
        window._emoji_cancel_overlay, "show_around_rect",
        lambda rect: emoji_shown.__setitem__("rect", rect),
    )
    monkeypatch.setattr(
        window._modifier_cancel_overlay, "show_around_rect",
        lambda rect: modifier_shown.__setitem__("rect", rect),
    )

    window._emoji_picker_visible = True
    window._show_emoji_cancel_overlay()

    assert "rect" in emoji_shown, "_emoji_cancel_overlay.show_around_rect must be called"
    assert "rect" not in modifier_shown, "_modifier_cancel_overlay.show_around_rect must NOT be called"
    window.close()


def test_closing_picker_via_toggle_hides_emoji_cancel_overlay(app, monkeypatch) -> None:
    """Closing the picker via toggle must hide _emoji_cancel_overlay."""
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    hidden = {}
    monkeypatch.setattr(
        window._emoji_cancel_overlay, "hide",
        lambda: hidden.__setitem__("hidden", True),
    )
    monkeypatch.setattr(window._emoji_cancel_overlay, "show_around_rect", lambda rect: None)

    window._toggle_emoji_picker()   # open
    hidden.clear()
    window._toggle_emoji_picker()   # close

    assert not window._emoji_picker_visible
    assert hidden.get("hidden") is True
    window.close()


def test_outside_callback_hides_emoji_cancel_overlay(app) -> None:
    """_handle_outside_overlay_click when picker is open must hide _emoji_cancel_overlay."""
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window._emoji_picker_visible = True

    window._handle_outside_overlay_click()

    assert not window._emoji_picker_visible
    assert not window._emoji_cancel_overlay.isVisible()
    window.close()


# ---------------------------------------------------------------------------
# Cancel-overlay integration tests (GNOME: outside click closes picker)
# ---------------------------------------------------------------------------

def test_show_emoji_cancel_overlay_uses_keyboard_frame_rect(app, monkeypatch) -> None:
    """_show_emoji_cancel_overlay must pass the keyboard's frameGeometry to show_around_rect."""
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    captured = {}
    monkeypatch.setattr(
        window._emoji_cancel_overlay,
        "show_around_rect",
        lambda rect: captured.__setitem__("rect", rect),
    )
    window._emoji_picker_visible = True

    window._show_emoji_cancel_overlay()

    assert "rect" in captured
    assert captured["rect"] == window.frameGeometry()

    window.close()


def test_opening_emoji_picker_schedules_cancel_overlay(app, monkeypatch) -> None:
    """_toggle_emoji_picker (open) must schedule _show_emoji_cancel_overlay via QTimer."""
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    scheduled = []
    monkeypatch.setattr(
        keyboard_app.QTimer,
        "singleShot",
        lambda delay, callback: scheduled.append((delay, callback)),
    )

    window._toggle_emoji_picker()

    assert window._emoji_picker_visible
    # At least one deferred call must be _show_emoji_cancel_overlay.
    callbacks = [cb for _, cb in scheduled]
    assert window._show_emoji_cancel_overlay in callbacks

    window.close()


def test_overlay_cancel_callback_closes_emoji_picker(app) -> None:
    """_handle_outside_overlay_click must close the picker and sync the overlay."""
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window._emoji_picker_visible = True

    window._handle_outside_overlay_click()

    assert not window._emoji_picker_visible
    assert not window._emoji_cancel_overlay.isVisible()

    window.close()


def test_toggling_emoji_picker_off_tears_down_overlay(app, monkeypatch) -> None:
    """Closing the picker via toggle must hide the cancel overlay."""
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    torn_down = {}
    monkeypatch.setattr(
        window._emoji_cancel_overlay,
        "hide",
        lambda: torn_down.__setitem__("hidden", True),
    )
    # Patch show_around_rect to be a no-op so the open path does not actually show.
    monkeypatch.setattr(window._emoji_cancel_overlay, "show_around_rect", lambda rect: None)

    # Open then close.
    window._toggle_emoji_picker()   # open
    torn_down.clear()
    window._toggle_emoji_picker()   # close

    assert not window._emoji_picker_visible
    assert torn_down.get("hidden") is True

    window.close()


def test_in_keyboard_outside_cell_click_syncs_overlay_away(app, monkeypatch) -> None:
    """The in-keyboard outside-cell guard (window_ui) must sync the overlay down."""
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    torn_down = {}
    monkeypatch.setattr(
        window._emoji_cancel_overlay,
        "hide",
        lambda: torn_down.__setitem__("hidden", True),
    )
    window._emoji_picker_visible = True
    # Populate _emoji_rects by drawing.
    pixmap = keyboard_app.QPixmap(window.size())
    painter = QPainter(pixmap)
    window._draw_emoji_picker(
        painter,
        min(window.width() / keyboard_app.DEFAULT_WINDOW_WIDTH,
            window.height() / keyboard_app.DEFAULT_WINDOW_HEIGHT),
    )
    painter.end()
    assert window._emoji_rects

    # Click outside any emoji cell — triggers the in-keyboard guard.
    window.mousePressEvent(
        type(
            "MouseEvent",
            (),
            {
                "button": lambda self: Qt.MouseButton.LeftButton,
                "position": lambda self: QPointF(1.0, 1.0),
            },
        )()
    )

    assert not window._emoji_picker_visible
    assert torn_down.get("hidden") is True

    window.close()


def test_picking_emoji_keeps_overlay_up(app, monkeypatch) -> None:
    """A pick (multi-pick flow) must NOT hide the overlay."""
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    hide_calls = []
    monkeypatch.setattr(
        window._emoji_cancel_overlay,
        "hide",
        lambda: hide_calls.append(True),
    )
    # Suppress the show path so we start from a clean state.
    monkeypatch.setattr(window._emoji_cancel_overlay, "show_around_rect", lambda rect: None)
    window._emoji_picker_visible = True
    delayed = []
    monkeypatch.setattr(keyboard_app.QTimer, "singleShot", lambda delay, callback: delayed.append((delay, callback)))
    pixmap = keyboard_app.QPixmap(window.size())
    painter = QPainter(pixmap)
    window._draw_emoji_picker(
        painter,
        min(window.width() / keyboard_app.DEFAULT_WINDOW_WIDTH,
            window.height() / keyboard_app.DEFAULT_WINDOW_HEIGHT),
    )
    painter.end()
    first_rect, _ = window._emoji_rects[0]

    window.mousePressEvent(
        type(
            "MouseEvent",
            (),
            {
                "button": lambda self: Qt.MouseButton.LeftButton,
                "position": lambda self: first_rect.center(),
            },
        )()
    )
    window.mouseReleaseEvent(type("MouseReleaseEvent", (), {})())
    # Fire any queued timer callbacks (type_text delay).
    for _, cb in delayed:
        cb()

    assert window._emoji_picker_visible
    assert not hide_calls  # overlay must NOT have been hidden

    window.close()


def test_emoji_menu_action_opens_keyboard_picker(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    emoji_action = next(action for action in window._app_menu.actions() if action.text() == "Emojis")

    emoji_action.trigger()

    assert window._emoji_picker_visible

    window.close()

def test_keyboard_emoji_picker_draws_common_emojis(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window._emoji_picker_visible = True
    pixmap = keyboard_app.QPixmap(window.size())
    painter = QPainter(pixmap)

    window._draw_emoji_picker(painter, min(window.width() / keyboard_app.DEFAULT_WINDOW_WIDTH, window.height() / keyboard_app.DEFAULT_WINDOW_HEIGHT))
    painter.end()

    assert [emoji for _, emoji in window._emoji_rects] == list(COMMON_EMOJIS)
    assert len(window._emoji_rects) == 24

    window.close()

def test_emoji_picker_font_uses_system_fallback_family() -> None:
    font = emoji_picker_font(1.0)

    assert font.family() != "Noto Color Emoji"
    assert font.pointSize() == 30

def test_keyboard_emoji_picker_click_types_text_after_release(app, monkeypatch) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend
    window._emoji_picker_visible = True
    delayed = []
    monkeypatch.setattr(keyboard_app.QTimer, "singleShot", lambda delay, callback: delayed.append((delay, callback)))
    pixmap = keyboard_app.QPixmap(window.size())
    painter = QPainter(pixmap)
    window._draw_emoji_picker(painter, min(window.width() / keyboard_app.DEFAULT_WINDOW_WIDTH, window.height() / keyboard_app.DEFAULT_WINDOW_HEIGHT))
    painter.end()
    first_rect, first_emoji = window._emoji_rects[0]

    window.mousePressEvent(
        type(
            "MouseEvent",
            (),
            {
                "button": lambda self: Qt.MouseButton.LeftButton,
                "position": lambda self: first_rect.center(),
            },
        )()
    )

    assert backend.unicode_text_calls == []
    window.mouseReleaseEvent(type("MouseReleaseEvent", (), {})())

    assert len(delayed) == 1
    assert delayed[0][0] == 80
    delayed[0][1]()

    assert backend.text_calls == [first_emoji]
    assert window._emoji_picker_visible  # picker stays open after a pick (multi-pick)

    window.close()

def test_type_emoji_sends_text_and_clears_context(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend
    window._current_word = "am"
    window._suggestions = ("amazing",)
    window._emoji_picker_visible = True

    window._type_emoji("🔥")

    assert backend.text_calls == ["🔥"]
    assert window._current_word == ""
    assert window._suggestions == ()
    assert window._emoji_picker_visible  # picker stays open after typing emoji

    window.close()


def test_outside_click_closes_emoji_picker(app, monkeypatch) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window._emoji_picker_visible = True
    pixmap = keyboard_app.QPixmap(window.size())
    painter = QPainter(pixmap)
    window._draw_emoji_picker(painter, min(window.width() / keyboard_app.DEFAULT_WINDOW_WIDTH, window.height() / keyboard_app.DEFAULT_WINDOW_HEIGHT))
    painter.end()
    assert window._emoji_rects  # rects populated

    # Click a point outside any emoji cell (top-left corner, well outside picker)
    window.mousePressEvent(
        type(
            "MouseEvent",
            (),
            {
                "button": lambda self: Qt.MouseButton.LeftButton,
                "position": lambda self: QPointF(1.0, 1.0),
            },
        )()
    )

    assert not window._emoji_picker_visible

    window.close()


def test_two_sequential_picks_type_two_emojis_picker_stays_visible(app, monkeypatch) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend
    window._emoji_picker_visible = True
    delayed = []
    monkeypatch.setattr(keyboard_app.QTimer, "singleShot", lambda delay, callback: delayed.append((delay, callback)))
    pixmap = keyboard_app.QPixmap(window.size())
    painter = QPainter(pixmap)
    window._draw_emoji_picker(painter, min(window.width() / keyboard_app.DEFAULT_WINDOW_WIDTH, window.height() / keyboard_app.DEFAULT_WINDOW_HEIGHT))
    painter.end()
    first_rect, first_emoji = window._emoji_rects[0]
    second_rect, second_emoji = window._emoji_rects[1]

    # First pick
    window.mousePressEvent(
        type(
            "MouseEvent",
            (),
            {
                "button": lambda self: Qt.MouseButton.LeftButton,
                "position": lambda self: first_rect.center(),
            },
        )()
    )
    window.mouseReleaseEvent(type("MouseReleaseEvent", (), {})())
    delayed[0][1]()  # fire the timer callback

    assert backend.text_calls == [first_emoji]
    assert window._emoji_picker_visible

    # Redraw to refresh _emoji_rects for second pick
    window._draw_emoji_picker(painter, min(window.width() / keyboard_app.DEFAULT_WINDOW_WIDTH, window.height() / keyboard_app.DEFAULT_WINDOW_HEIGHT))

    # Second pick
    window.mousePressEvent(
        type(
            "MouseEvent",
            (),
            {
                "button": lambda self: Qt.MouseButton.LeftButton,
                "position": lambda self: second_rect.center(),
            },
        )()
    )
    window.mouseReleaseEvent(type("MouseReleaseEvent", (), {})())
    delayed[1][1]()  # fire second timer callback

    assert backend.text_calls == [first_emoji, second_emoji]
    assert window._emoji_picker_visible

    window.close()
