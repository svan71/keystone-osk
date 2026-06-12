from qt_window_test_helpers import *


@pytest.mark.parametrize(
    "key_spec",
    (
        PositionedKey("a", "a", Rect(0, 0, 1, 1)),
        PositionedKey("one", "1", Rect(0, 0, 1, 1), shifted="!"),
        PositionedKey("space", "Space", Rect(0, 0, 1, 1), role="space"),
        PositionedKey("backspace", "Backspace", Rect(0, 0, 1, 1), role="backspace"),
        PositionedKey("left", "Left", Rect(0, 0, 1, 1), role="arrow"),
        PositionedKey("full-numpad-7", "7", Rect(0, 0, 1, 1), role="numpad"),
        PositionedKey("full-numpad-plus", "+", Rect(0, 0, 1, 1), role="numpad"),
    ),
)
def test_obvious_typing_keys_are_repeatable(key_spec: PositionedKey) -> None:
    assert is_repeatable_key(key_spec)


@pytest.mark.parametrize("label", ("Enter", "Tab", "Caps", "Shift", "Ctrl", "Alt", "AltGr", "Super", "Menu", "Delete", "Num"))
def test_non_typing_action_and_modifier_keys_do_not_repeat(label: str) -> None:
    assert not is_repeatable_key(key(label))


def test_repeatable_key_starts_and_stops_repeat_timer(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    repeat_key = key("a")

    window._start_key_repeat(repeat_key)

    assert window._repeat_key == repeat_key
    assert window._repeat_timer.isActive()

    window._stop_key_repeat()

    assert window._repeat_key is None
    assert not window._repeat_timer.isActive()


def test_releasing_shift_key_does_not_clear_shift_latch(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window.backend = RecordingBackend()

    window._queue_key_press(key("Shift"))
    window.mouseReleaseEvent(None)

    assert window._locked_key_labels == {"Shift"}


def test_releasing_repeated_key_clears_one_shot_shift(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window.backend = RecordingBackend()
    repeat_key = key("a")

    window._queue_key_press(key("Shift"))
    window._queue_key_press(repeat_key, clear_one_shot_modifiers=False)
    window._start_key_repeat(repeat_key)
    window.mouseReleaseEvent(None)

    assert window._locked_key_labels == set()


def test_repeated_letter_updates_autocomplete_each_time(app) -> None:
    window = KeyboardWindow(
        startup_size=QSize(620, 260),
        persist_window_state=False,
        autocomplete_engine=AutocompleteEngine(tech_words=("aaa",), common_words=()),
    )
    backend = RecordingBackend()
    window.backend = backend
    window._auto_cap_enabled = False
    window._repeat_key = key("a")

    window._repeat_held_key()
    window._repeat_held_key()
    window._stop_key_repeat(clear_modifiers=False)

    assert backend.calls == [("a", ()), ("a", ())]
    assert window._autocomplete_buffer == "aa"
    assert window._autocomplete_cursor == 2
    assert window._current_word == "aa"


def test_repeated_backspace_updates_autocomplete_each_time(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend
    window._autocomplete_buffer = "abcd"
    window._autocomplete_cursor = 4
    window._current_word = "abcd"
    window._repeat_key = PositionedKey("backspace", "Backspace", Rect(0, 0, 1, 1), role="backspace")

    window._repeat_held_key()
    window._repeat_held_key()
    window._stop_key_repeat(clear_modifiers=False)

    assert backend.calls == [("Backspace", ()), ("Backspace", ())]
    assert window._autocomplete_buffer == "ab"
    assert window._autocomplete_cursor == 2
    assert window._current_word == "ab"


def test_repeated_arrow_updates_autocomplete_cursor_each_time(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend
    window._autocomplete_buffer = "abcd"
    window._autocomplete_cursor = 4
    window._current_word = "abcd"
    window._repeat_key = PositionedKey("left", "Left", Rect(0, 0, 1, 1), role="arrow")

    window._repeat_held_key()
    window._repeat_held_key()
    window._stop_key_repeat(clear_modifiers=False)

    assert backend.calls == [("Left", ()), ("Left", ())]
    assert window._autocomplete_cursor == 2
    assert window._current_word == "ab"


def test_ctrl_alt_combo_sends_next_key_then_clears_one_shot_modifiers(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._queue_key_press(key("Ctrl"))
    window._queue_key_press(key("Alt"))
    window._queue_key_press(key("t"))

    assert backend.calls == [("t", ("Ctrl", "Alt"))]
    assert window._locked_key_labels == set()


def test_ctrl_alt_delete_sends_delete_with_both_modifiers(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._queue_key_press(key("Ctrl"))
    window._queue_key_press(key("Alt"))
    window._queue_key_press(key("Delete"))

    assert backend.calls == [("Delete", ("Ctrl", "Alt"))]
    assert window._locked_key_labels == set()


def test_ctrl_alt_full_nav_delete_sends_delete_with_both_modifiers(app) -> None:
    window = KeyboardWindow(startup_size=QSize(FULL_WINDOW_WIDTH, FULL_WINDOW_HEIGHT), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend
    window._set_keyboard_mode("full")
    full_delete = next(key for key in window._keyboard_geometry().keys if key.id == "full-nav-delete")

    window._queue_key_press(key("Ctrl"))
    window._queue_key_press(key("Alt"))
    window._queue_key_press(full_delete)

    assert backend.calls == [("Delete", ("Ctrl", "Alt"))]
    assert window._locked_key_labels == set()


def test_clicking_full_nav_delete_sends_ctrl_alt_delete(app) -> None:
    window = KeyboardWindow(startup_size=QSize(FULL_WINDOW_WIDTH, FULL_WINDOW_HEIGHT), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend
    window._set_keyboard_mode("full")
    full_delete = next(key for key in window._keyboard_geometry().keys if key.id == "full-nav-delete")

    window._queue_key_press(key("Ctrl"))
    window._queue_key_press(key("Alt"))
    window.mousePressEvent(
        type(
            "MouseEvent",
            (),
            {
                "button": lambda self: Qt.MouseButton.LeftButton,
                "position": lambda self: QPointF(full_delete.rect.center_x, full_delete.rect.center_y),
            },
        )()
    )

    assert backend.calls == [("Delete", ("Ctrl", "Alt"))]
    assert window._locked_key_labels == set()


def test_near_miss_click_on_full_nav_delete_sends_ctrl_alt_delete(app) -> None:
    window = KeyboardWindow(startup_size=QSize(FULL_WINDOW_WIDTH, FULL_WINDOW_HEIGHT), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend
    window._set_keyboard_mode("full")
    full_delete = next(key for key in window._keyboard_geometry().keys if key.id == "full-nav-delete")

    window._queue_key_press(key("Ctrl"))
    window._queue_key_press(key("Alt"))
    window.mousePressEvent(
        type(
            "MouseEvent",
            (),
            {
                "button": lambda self: Qt.MouseButton.LeftButton,
                "position": lambda self: QPointF(full_delete.rect.center_x, full_delete.rect.bottom + 4),
            },
        )()
    )

    assert backend.calls == [("Delete", ("Ctrl", "Alt"))]
    assert window._locked_key_labels == set()


def test_ctrl_a_clears_ctrl_before_delete_even_without_release(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._queue_key_press(key("Ctrl"))
    window._queue_key_press(key("a"), clear_one_shot_modifiers=False)
    window._queue_key_press(key("Delete"))

    assert backend.calls == [("a", ("Ctrl",)), ("Delete", ())]
    assert window._locked_key_labels == set()


def test_ctrl_letter_press_does_not_start_repeat(app, monkeypatch) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend
    letter = key("a")
    monkeypatch.setattr(window, "_key_at", lambda x, y: letter)

    window._queue_key_press(key("Ctrl"))
    window.mousePressEvent(
        type(
            "MouseEvent",
            (),
            {
                "button": lambda self: Qt.MouseButton.LeftButton,
                "position": lambda self: QPoint(10, 10),
            },
        )()
    )

    assert backend.calls == [("a", ("Ctrl",))]
    assert window._locked_key_labels == set()
    assert window._repeat_key is None
    assert not window._repeat_timer.isActive()


def _press_keyboard_background(window) -> None:
    window.mousePressEvent(
        type(
            "MouseEvent",
            (),
            {
                "button": lambda self: Qt.MouseButton.LeftButton,
                "position": lambda self: QPoint(300, 20),
                "globalPosition": lambda self: QPointF(400, 120),
            },
        )()
    )


def test_moving_keyboard_clears_one_shot_modifiers(app, monkeypatch) -> None:
    # GNOME: a non-key (move) click clears one-shot modifiers but keeps Caps,
    # which is cancelled separately via the off-screen cancel overlay.
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    monkeypatch.delenv("KDE_FULL_SESSION", raising=False)
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window.setGeometry(100, 100, 620, 260)
    window._locked_key_labels = {"Ctrl", "Alt", "Caps"}
    monkeypatch.setattr(window, "_key_at", lambda x, y: None)
    monkeypatch.setattr(window, "_resize_edges_at", lambda x, y: None)
    monkeypatch.setattr(window, "_begin_system_move", lambda: False)

    _press_keyboard_background(window)

    assert window._locked_key_labels == {"Caps"}
    assert window._drag_offset == QPoint(300, 20)


def test_kde_moving_keyboard_clears_caps_and_one_shot(app, monkeypatch) -> None:
    # KDE has no cancel overlay, so the non-key (move) click is the cancel
    # gesture and must release Caps along with one-shot modifiers.
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    monkeypatch.setenv("KDE_FULL_SESSION", "true")
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window.setGeometry(100, 100, 620, 260)
    window._locked_key_labels = {"Ctrl", "Alt", "Caps"}
    monkeypatch.setattr(window, "_key_at", lambda x, y: None)
    monkeypatch.setattr(window, "_resize_edges_at", lambda x, y: None)
    monkeypatch.setattr(window, "_begin_system_move", lambda: False)

    _press_keyboard_background(window)

    assert window._locked_key_labels == set()
    assert window._drag_offset == QPoint(300, 20)


def test_typing_letters_updates_autocomplete_suggestions(app) -> None:
    engine = AutocompleteEngine(tech_words=("systemd",), common_words=())
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=engine)
    window.backend = RecordingBackend()

    window._queue_key_press(key("s"))
    window._queue_key_press(key("y"))

    assert window._current_word == "sy"
    assert window._suggestions == ("systemd",)


def test_compact_keyboard_uses_four_suggestions(app) -> None:
    engine = AutocompleteEngine(tech_words=("systemd", "server", "session", "settings", "service"), common_words=())
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=engine)
    window._current_word = "se"

    window._refresh_suggestions()

    assert window._suggestions == ("server", "session", "settings", "service")


def test_full_keyboard_uses_five_suggestions(app) -> None:
    engine = AutocompleteEngine(tech_words=("server", "session", "settings", "service", "secure"), common_words=())
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=engine)
    window._toggle_keyboard_mode()
    window._current_word = "se"

    window._refresh_suggestions()

    assert window._suggestions == ("server", "session", "settings", "service", "secure")


def test_full_keyboard_suggestions_sit_above_function_row(app) -> None:
    window = KeyboardWindow(startup_size=QSize(FULL_WINDOW_WIDTH, FULL_WINDOW_HEIGHT), persist_window_state=False)
    window._toggle_keyboard_mode()
    window._suggestions = ("server", "session", "settings", "service", "secure")
    pixmap = keyboard_app.QPixmap(window.size())
    painter = QPainter(pixmap)

    window._draw_suggestions(painter, min(window.width() / 1120, window.height() / 470))
    painter.end()

    function_top = min(key.rect.top for key in build_full_key_geometry(window.width(), window.height()).keys if key.role == "function")
    suggestion_bottom = max(rect.bottom() for rect, _ in window._suggestion_rects)

    assert suggestion_bottom < function_top


def test_compact_keyboard_four_suggestions_sit_above_number_row(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window._suggestions = ("server", "session", "settings", "service")
    pixmap = keyboard_app.QPixmap(window.size())
    painter = QPainter(pixmap)
    scale = min(window.width() / keyboard_app.DEFAULT_WINDOW_WIDTH, window.height() / keyboard_app.DEFAULT_WINDOW_HEIGHT)
    panel = keyboard_panel_rect(window.width(), window.height())

    window._draw_titlebar(painter, panel, scale)
    window._draw_suggestions(painter, scale)
    painter.end()

    number_top = min(key.rect.top for key in window._keyboard_geometry().keys if key.label == "1")
    suggestion_top = min(rect.top() for rect, _ in window._suggestion_rects)
    suggestion_bottom = max(rect.bottom() for rect, _ in window._suggestion_rects)
    first_suggestion_left = min(rect.left() for rect, _ in window._suggestion_rects)

    assert len(window._suggestion_rects) == 4
    assert first_suggestion_left - window._mode_toggle_rect.right() >= 10 * scale
    assert suggestion_bottom < number_top
    assert abs((suggestion_top - panel.top()) - (number_top - suggestion_bottom)) <= 0.5


def test_suggestion_chips_use_theme_panel_background(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, theme="mocha")
    window._suggestions = ("server",)
    pixmap = keyboard_app.QPixmap(window.size())
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    scale = min(window.width() / keyboard_app.DEFAULT_WINDOW_WIDTH, window.height() / keyboard_app.DEFAULT_WINDOW_HEIGHT)

    window._draw_suggestions(painter, scale)
    painter.end()

    rect, _ = window._suggestion_rects[0]
    sample = pixmap.toImage().pixelColor(int(rect.left() + 12 * scale), int(rect.center().y()))

    assert sample.name() == theme_palette("mocha").panel_top


def test_accepting_suggestion_inserts_remaining_suffix_and_boosts_word(app) -> None:
    engine = AutocompleteEngine(tech_words=("systemd",), common_words=())
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=engine)
    backend = RecordingBackend()
    window.backend = backend
    window._current_word = "sys"
    window._refresh_suggestions()

    window._accept_suggestion("systemd")

    assert backend.calls == [("t", ()), ("e", ()), ("m", ()), ("d", ()), ("Space", ())]
    assert window._current_word == ""
    assert engine.suggestions("sy") == ("systemd",)


def test_punctuation_after_accepted_suggestion_removes_auto_space(app) -> None:
    engine = AutocompleteEngine(tech_words=(), common_words=("apple",))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=engine)
    backend = RecordingBackend()
    window.backend = backend
    window._current_word = "app"

    window._accept_suggestion("apple")
    window._queue_key_press(key("."))

    assert backend.calls[-2:] == [("Backspace", ()), (".", ())]


@pytest.mark.parametrize(
    ("typed_key", "expected_call"),
    (
        (PositionedKey("one", "1", Rect(0, 0, 1, 1), shifted="!"), ("1", ("Shift",))),
        (PositionedKey("slash", "/", Rect(0, 0, 1, 1), shifted="?"), ("/", ("Shift",))),
        (PositionedKey("semicolon", ";", Rect(0, 0, 1, 1), shifted=":"), (";", ("Shift",))),
        (PositionedKey("quote", "'", Rect(0, 0, 1, 1), shifted='"'), ("'", ("Shift",))),
    ),
)
def test_shifted_punctuation_after_accepted_suggestion_removes_auto_space(app, typed_key, expected_call) -> None:
    engine = AutocompleteEngine(tech_words=(), common_words=("apple",))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=engine)
    backend = RecordingBackend()
    window.backend = backend
    window._current_word = "app"

    window._accept_suggestion("apple")
    window._queue_key_press(key("Shift"))
    window._queue_key_press(typed_key)

    assert backend.calls[-2:] == [("Backspace", ()), expected_call]


def test_manual_space_before_punctuation_is_not_removed(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=AutocompleteEngine())
    backend = RecordingBackend()
    window.backend = backend

    window._queue_key_press(key("Space"))
    window._queue_key_press(key("."))

    assert backend.calls == [("Space", ()), (".", ())]


def test_auto_capitalizes_first_letter_and_sentence_start(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=AutocompleteEngine())
    backend = RecordingBackend()
    window.backend = backend

    window._queue_key_press(key("a"))
    window._queue_key_press(key("."))
    window._queue_key_press(key("Space"))
    window._queue_key_press(key("b"))

    assert backend.calls == [("a", ("Shift",)), (".", ()), ("Space", ()), ("b", ("Shift",))]


def test_auto_cap_menu_action_toggles_sentence_capitalization(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=AutocompleteEngine())
    backend = RecordingBackend()
    window.backend = backend

    window._toggle_auto_cap_enabled()
    window._queue_key_press(key("a"))

    assert not window._auto_cap_enabled
    assert window._auto_cap_action.text() == "Auto-Cap: Off"
    assert backend.calls == [("a", ())]


def test_auto_cap_menu_action_persists_to_window_state(app, monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "window-state.json"
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(state_path))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=True, autocomplete_engine=AutocompleteEngine())

    window._toggle_auto_cap_enabled()

    assert not load_auto_cap_enabled()
    restored = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=True, autocomplete_engine=AutocompleteEngine())
    assert not restored._auto_cap_enabled
    window.close()
    restored.close()


def test_backspace_after_completed_word_restores_suggestion_context(app) -> None:
    engine = AutocompleteEngine(tech_words=(), common_words=("apple", "application", "apply"))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=engine)
    window.backend = RecordingBackend()
    window._current_word = "app"

    window._accept_suggestion("apple")
    window._queue_key_press(key("Backspace"))

    assert window._current_word == "apple"
    assert window._suggestions == ()

    window._queue_key_press(key("Backspace"))

    assert window._current_word == "appl"
    assert window._suggestions == ("apple", "application", "apply")


def test_backspace_after_typed_space_restores_previous_word_context(app) -> None:
    engine = AutocompleteEngine(tech_words=(), common_words=("apple", "application", "apply"))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=engine)
    window.backend = RecordingBackend()
    window._current_word = "apple"

    window._queue_key_press(key("Space"))
    window._queue_key_press(key("Backspace"))

    assert window._current_word == "apple"

    window._queue_key_press(key("Backspace"))

    assert window._current_word == "appl"
    assert window._suggestions == ("apple", "application", "apply")


def test_backspace_across_words_suggests_word_at_cursor(app) -> None:
    engine = AutocompleteEngine(tech_words=(), common_words=("apple", "computer", "company", "compile", "system"))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=engine)
    window.backend = RecordingBackend()

    for label in [*list("apple"), "Space", *list("computer"), "Space", *list("system")]:
        window._queue_key_press(key(label))

    assert window._current_word == "system"

    for _ in range(len("system") + 1 + len("uter")):
        window._queue_key_press(key("Backspace"))

    assert window._current_word == "comp"
    assert window._suggestions == ("computer", "company", "compile")


def test_backspace_sentence_edit_suggests_replacement_word(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=AutocompleteEngine())
    window.backend = RecordingBackend()

    for label in "this is extraordinary how well its working at the so little time":
        window._queue_key_press(key("Space" if label == " " else label))
    while not window._autocomplete_buffer.endswith("this is "):
        window._queue_key_press(key("Backspace"))
    window._queue_key_press(key("a"))
    window._queue_key_press(key("m"))

    assert window._current_word == "am"
    assert "amazing" in window._suggestions


def test_backspace_after_cursor_navigation_suggests_edited_word(app) -> None:
    engine = AutocompleteEngine(tech_words=(), common_words=("something", "somewhere", "ending"))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=engine)
    window.backend = RecordingBackend()

    for label in [*list("something"), "Space", *list("ending")]:
        window._queue_key_press(key(label))

    assert window._current_word == "ending"

    for _ in range(len(" ending")):
        window._queue_key_press(key("Left"))
    for _ in range(len("ething")):
        window._queue_key_press(key("Backspace"))

    assert window._current_word == "som"
    assert window._suggestions == ("something", "somewhere")


def test_vertical_navigation_clears_stale_autocomplete_context(app) -> None:
    engine = AutocompleteEngine(tech_words=(), common_words=("ending",))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=engine)
    window.backend = RecordingBackend()

    for label in [*list("ending")]:
        window._queue_key_press(key(label))

    window._queue_key_press(key("Up"))

    assert window._current_word == ""
    assert window._suggestions == ()


def test_completed_word_is_learned_after_three_uses(app) -> None:
    engine = AutocompleteEngine(tech_words=(), common_words=())
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=engine)

    for _ in range(3):
        window._current_word = "plasma"
        window._finish_autocomplete_word()

    assert engine.suggestions("pl") == ("plasma",)


def test_learning_menu_action_toggles_local_learning(app) -> None:
    engine = AutocompleteEngine(tech_words=(), common_words=())
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=engine)

    window._toggle_learning_enabled()

    assert not engine.learning_enabled
    assert window._learning_action.text() == "Learning: Off"


def test_suggestions_menu_action_toggles_visible_suggestions(app) -> None:
    engine = AutocompleteEngine(tech_words=("systemd",), common_words=())
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=engine)
    window._current_word = "sy"
    window._refresh_suggestions()

    assert window._suggestions == ("systemd",)

    window._toggle_suggestions_enabled()

    assert not window._suggestions_enabled
    assert window._suggestions == ()
    assert window._suggestions_action.text() == "Turn Suggestions On"

    window._toggle_suggestions_enabled()

    assert window._suggestions_enabled
    assert window._suggestions == ("systemd",)
    assert window._suggestions_action.text() == "Turn Suggestions Off"


def test_suggestions_menu_action_persists_to_window_state(app, monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "window-state.json"
    monkeypatch.setenv("KEYSTONE_OSK_STATE_FILE", str(state_path))
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=True, autocomplete_engine=AutocompleteEngine())

    window._toggle_suggestions_enabled()

    assert not load_suggestions_enabled()
    restored = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=True, autocomplete_engine=AutocompleteEngine())
    assert not restored._suggestions_enabled
    window.close()
    restored.close()


def test_menu_preference_state_defaults_to_enabled(tmp_path) -> None:
    state_path = tmp_path / "missing.json"

    assert load_suggestions_enabled(state_path)
    assert load_auto_cap_enabled(state_path)


def test_menu_preference_state_saves_booleans(tmp_path) -> None:
    state_path = tmp_path / "window-state.json"

    save_suggestions_enabled(False, state_path)
    save_auto_cap_enabled(False, state_path)

    assert not load_suggestions_enabled(state_path)
    assert not load_auto_cap_enabled(state_path)


def test_leaving_keyboard_hides_suggestions_but_keeps_current_word_context(app) -> None:
    engine = AutocompleteEngine(tech_words=("kindergarten",), common_words=())
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, autocomplete_engine=engine)
    window._current_word = "kin"
    window._autocomplete_buffer = "kin"
    window._autocomplete_cursor = 3
    window._refresh_suggestions()

    assert window._suggestions == ("kindergarten",)

    window.leaveEvent(None)

    assert window._suggestions == ()
    assert window._current_word == "kin"
    assert window._autocomplete_buffer == "kin"

    window.backend = RecordingBackend()
    window._queue_key_press(key("d"))

    assert window._current_word == "kind"
    assert window._suggestions == ("kindergarten",)


def test_keypress_labels_are_not_logged_by_default(app, capsys) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    window.backend = RecordingBackend()

    window._queue_key_press(key("a"))

    captured = capsys.readouterr()
    assert "press a" not in captured.err
    assert "queue a" not in captured.err


def test_debug_keys_logs_keypress_labels(app, capsys) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False, debug_keys=True)
    window.backend = RecordingBackend()

    window._queue_key_press(key("a"))

    captured = capsys.readouterr()
    assert "keystone-osk: queue a" in captured.err
    assert "keystone-osk: press Shift+a" in captured.err


def test_super_shift_combo_sends_next_key_then_clears_one_shot_modifiers(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._queue_key_press(key("Super"))
    window._queue_key_press(key("Shift"))
    window._queue_key_press(key("l"))

    assert backend.calls == [("l", ("Shift", "Super"))]
    assert window._locked_key_labels == set()


def test_double_tapping_super_emits_bare_super_tap(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._queue_key_press(key("Super"))
    window._queue_key_press(key("Super"))

    assert backend.calls == [("Super", ())]
    assert window._locked_key_labels == set()


def test_super_combo_does_not_emit_bare_super_tap(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._queue_key_press(key("Super"))
    window._queue_key_press(key("a"))

    assert backend.calls == [("a", ("Super",))]
    assert window._locked_key_labels == set()


def test_double_tapping_non_command_locks_does_not_add_bare_tap(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._queue_key_press(key("Shift"))
    window._queue_key_press(key("Shift"))
    window._queue_key_press(key("Caps"))
    window._queue_key_press(key("Caps"))
    window._queue_key_press(key("Num"))
    window._queue_key_press(key("Num"))

    # Num is a pure latch in reliable mode (like Caps): it never emits a bare
    # keypress, and the command-modifier double-tap path does not apply to it.
    assert backend.calls == []
    assert window._locked_key_labels == set()


def test_unlatching_one_of_two_command_modifiers_emits_only_that_modifier(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._queue_key_press(key("Ctrl"))
    window._queue_key_press(key("Alt"))
    window._queue_key_press(key("Alt"))

    assert backend.calls == [("Alt", ())]
    assert window._locked_key_labels == {"Ctrl"}


def test_caps_stays_locked_after_combo_key_while_ctrl_clears(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._queue_key_press(key("Caps"))
    window._queue_key_press(key("Ctrl"))
    window._queue_key_press(key("a"))

    assert backend.calls == [("a", ("Ctrl", "Shift"))]
    assert window._locked_key_labels == {"Caps"}


def test_menu_is_normal_key_not_latched_modifier(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._queue_key_press(key("Menu"))

    assert backend.calls == [("Menu", ())]
    assert window._locked_key_labels == set()


def test_num_toggles_lock_state_like_caps(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend

    window._queue_key_press(key("Num"))

    assert window._locked_key_labels == {"Num"}
    assert backend.calls == []

    window._queue_key_press(key("Num"))

    assert window._locked_key_labels == set()
    assert backend.calls == []


def test_num_in_true_keypad_ensures_system_numlock_without_keycode_toggle(app) -> None:
    # Regression: the Num key used to emit a raw NumLock keycode (69), which
    # fought ensure_numlock_on and left true-keypad emitting navigation, not
    # digits. Now Num latching on in true-keypad ensures system NumLock via the
    # deterministic backend call and never sends a bare keypress.
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend
    window._numpad_output_mode = "true-keypad"

    window._queue_key_press(key("Num"))

    assert window._locked_key_labels == {"Num"}
    assert backend.calls == []
    assert backend.ensure_numlock_calls == 1

    # Latching Num back off must not toggle the hardware NumLock (leave-it-on).
    window._queue_key_press(key("Num"))

    assert window._locked_key_labels == set()
    assert backend.calls == []
    assert backend.ensure_numlock_calls == 1


def test_num_in_reliable_does_not_touch_system_numlock(app) -> None:
    window = KeyboardWindow(startup_size=QSize(620, 260), persist_window_state=False)
    backend = RecordingBackend()
    window.backend = backend  # default mode is reliable

    window._queue_key_press(key("Num"))

    assert window._locked_key_labels == {"Num"}
    assert backend.calls == []
    assert backend.ensure_numlock_calls == 0
