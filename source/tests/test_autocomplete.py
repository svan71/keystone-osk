# SPDX-FileCopyrightText: 2026 keystoneosk
# SPDX-License-Identifier: GPL-3.0-or-later

import json

from keystone_osk.autocomplete import (
    AutocompleteEngine,
    completion_suffix,
    is_private_or_sensitive,
    load_engine,
    load_ranked_words,
    save_engine,
)


def test_suggestions_are_limited_to_three() -> None:
    engine = AutocompleteEngine(
        tech_words=("systemd", "server", "session", "settings"),
        common_words=("season", "second", "secure", "simple"),
    )

    assert engine.suggestions("se") == ("server", "session", "settings")


def test_suggestions_can_return_five_when_requested() -> None:
    engine = AutocompleteEngine(
        tech_words=("systemd", "server", "session", "settings", "service", "secure"),
        common_words=(),
    )

    assert engine.suggestions("se", limit=5) == ("server", "session", "settings", "service", "secure")


def test_amazing_is_prioritized_for_short_everyday_prefix() -> None:
    engine = AutocompleteEngine()

    assert "amazing" in engine.suggestions("am", limit=4)


def test_tech_words_can_appear_after_two_letters() -> None:
    engine = AutocompleteEngine(tech_words=("kernel",), common_words=("keep",))

    assert engine.suggestions("ke")[0] == "kernel"


def test_common_words_require_three_letters() -> None:
    engine = AutocompleteEngine(tech_words=(), common_words=("people",))

    assert engine.suggestions("pe") == ()
    assert engine.suggestions("peo") == ("people",)


def test_everyday_words_beat_tech_words_for_everyday_prefixes() -> None:
    engine = AutocompleteEngine()

    assert engine.suggestions("ap")[0] == "apple"
    assert engine.suggestions("fo")[0] == "for"


def test_common_app_words_continue_suggesting_after_apple_prefix() -> None:
    engine = AutocompleteEngine()

    assert "appendix" in engine.suggestions("appe")
    assert "appendix" in engine.suggestions("appen")


def test_static_suggestions_tolerate_one_missing_doubled_letter() -> None:
    engine = AutocompleteEngine()

    assert engine.suggestions("apen")[0] == "appendix"
    assert engine.suggestions("apend")[0] == "appendix"


def test_default_dictionary_is_large_ranked_word_list() -> None:
    words = load_ranked_words("common_words.txt")

    assert len(words) >= 10000
    assert words.index("for") < words.index("folder")
    assert words.index("apple") < words.index("appendix")


def test_default_dictionary_covers_common_words_beyond_curated_examples() -> None:
    engine = AutocompleteEngine()

    assert "computer" in engine.suggestions("comp")
    assert "keyboard" in engine.suggestions("key")
    assert "appendix" in engine.suggestions("appen")


def test_recent_learned_word_can_outrank_stale_higher_count_word() -> None:
    engine = AutocompleteEngine(
        tech_words=(),
        common_words=(),
        learned_counts={"plasma": 6, "planet": 2},
    )
    engine.events = 100
    engine.learned_seen = {"plasma": 0, "planet": 100}

    assert engine.suggestions("pl", limit=2) == ("planet", "plasma")


def test_recency_decays_to_count_ordering_at_window_edge() -> None:
    engine = AutocompleteEngine(
        tech_words=(),
        common_words=(),
        learned_counts={"plasma": 6, "planet": 2},
    )
    engine.events = 50
    engine.learned_seen = {"plasma": 0, "planet": 0}

    assert engine.suggestions("pl", limit=2) == ("plasma", "planet")


def test_learned_boost_still_dominates_score_then_equal_score_sorts_alphabetically() -> None:
    engine = AutocompleteEngine(
        tech_words=(),
        common_words=(),
        learned_counts={"apex": 2, "apartment": 2, "apricot": 7},
        learned_boosts={"apex": 1},
    )
    engine.events = 100
    engine.learned_seen = {"apex": 0, "apartment": 100, "apricot": 50}

    assert engine.suggestions("ap", limit=3) == ("apex", "apartment", "apricot")


def test_learned_words_surface_after_two_manual_uses() -> None:
    engine = AutocompleteEngine(tech_words=(), common_words=())

    engine.observe_typed_word("plasma")

    assert engine.suggestions("pl") == ()

    engine.observe_typed_word("plasma")

    assert engine.suggestions("pl") == ("plasma",)


def test_observe_and_boost_update_event_clock_and_seen_word() -> None:
    engine = AutocompleteEngine(tech_words=(), common_words=())

    engine.observe_typed_word("plasma")

    assert getattr(engine, "events", None) == 1
    assert getattr(engine, "learned_seen", {}) == {"plasma": 1}

    engine.boost_word("package")

    assert engine.events == 2
    assert engine.learned_seen == {"plasma": 1, "package": 2}


def test_tapped_suggestion_is_boosted_immediately() -> None:
    engine = AutocompleteEngine(tech_words=("python",), common_words=())

    engine.boost_word("package")

    assert engine.suggestions("pa") == ("package",)


def test_exact_learned_word_is_not_suggested_as_its_own_completion() -> None:
    engine = AutocompleteEngine(tech_words=(), common_words=())

    engine.boost_word("apple")

    assert engine.suggestions("apple") == ()


def test_learned_words_rank_before_tech_and_common_words() -> None:
    engine = AutocompleteEngine(tech_words=("server",), common_words=("service",))
    engine.boost_word("serverless")

    assert engine.suggestions("ser") == ("serverless", "server", "service")


def test_private_words_are_not_learned_or_suggested() -> None:
    engine = AutocompleteEngine(tech_words=(), common_words=())

    for _ in range(3):
        engine.observe_typed_word("sam@example.com")
        engine.observe_typed_word("/home/user/secret")
        engine.observe_typed_word("sk-abc1234567890")

    assert engine.suggestions("st") == ()
    assert engine.suggestions("ho") == ()
    assert engine.suggestions("sk") == ()


def test_sensitive_patterns_are_rejected() -> None:
    sensitive = (
        "sam@example.com",
        "https://example.com",
        "192.168.1.50",
        "/home/user/file",
        "~/.ssh/id_rsa",
        "abc123def4567890",
        "sk-abc1234567890",
        "CamelCaseToken",
    )

    assert all(is_private_or_sensitive(word) for word in sensitive)


def test_completion_suffix_returns_only_remaining_text() -> None:
    assert completion_suffix("systemd", "sys") == "temd"


def test_engine_persists_learned_words_and_learning_state(tmp_path) -> None:
    path = tmp_path / "words.json"
    engine = AutocompleteEngine(tech_words=(), common_words=())
    engine.boost_word("plasma")
    engine.learning_enabled = False

    save_engine(engine, path)

    loaded = load_engine(path)
    assert loaded.learning_enabled is False
    assert loaded.suggestions("pl")[0] == "plasma"


def test_engine_v2_round_trip_preserves_seen_and_events(tmp_path) -> None:
    path = tmp_path / "words.json"
    engine = AutocompleteEngine(
        tech_words=(),
        common_words=(),
        learned_counts={"plasma": 2},
        learned_boosts={"plasma": 1},
    )
    engine.learned_seen = {"plasma": 7}
    engine.events = 7

    save_engine(engine, path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == 2
    assert data["seen"] == {"plasma": 7}
    assert data["events"] == 7

    loaded = load_engine(path)
    assert loaded.learned_seen == {"plasma": 7}
    assert loaded.events == 7
    assert loaded.suggestions("pl")[0] == "plasma"


def test_v1_words_file_loads_without_seen_or_events(tmp_path) -> None:
    path = tmp_path / "words.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "learning_enabled": False,
                "counts": {"plasma": 3},
                "boosts": {"plasma": 1},
            }
        ),
        encoding="utf-8",
    )

    loaded = load_engine(path)

    assert loaded.learning_enabled is False
    assert loaded.learned_counts == {"plasma": 3}
    assert loaded.learned_boosts == {"plasma": 1}
    assert getattr(loaded, "learned_seen", None) == {}
    assert getattr(loaded, "events", None) == 0


def test_disabled_learning_does_not_observe_typed_words() -> None:
    engine = AutocompleteEngine(tech_words=(), common_words=(), learning_enabled=False)

    for _ in range(3):
        engine.observe_typed_word("plasma")

    assert engine.suggestions("pl") == ()


def test_clear_learned_words_removes_local_suggestions() -> None:
    engine = AutocompleteEngine(tech_words=(), common_words=())
    engine.boost_word("plasma")

    engine.clear_learned_words()

    assert engine.suggestions("pl") == ()
    assert engine.learned_seen == {}
