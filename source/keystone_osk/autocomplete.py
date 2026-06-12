from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from keystone_osk.config import learned_words_path as config_learned_words_path


FALLBACK_TECH_WORDS = (
    "access",
    "arch",
    "archive",
    "audio",
    "backup",
    "bash",
    "bluetooth",
    "boot",
    "browser",
    "cache",
    "cachyos",
    "cli",
    "cloud",
    "command",
    "computer",
    "compile",
    "config",
    "console",
    "container",
    "daemon",
    "debug",
    "desktop",
    "device",
    "directory",
    "display",
    "driver",
    "editor",
    "ethernet",
    "firewall",
    "firmware",
    "flatpak",
    "folder",
    "git",
    "github",
    "gnome",
    "graphics",
    "hardware",
    "hostname",
    "install",
    "journal",
    "json",
    "kernel",
    "keyboard",
    "kde",
    "konsole",
    "launcher",
    "linux",
    "login",
    "mirror",
    "network",
    "nvidia",
    "openssl",
    "pacman",
    "package",
    "partition",
    "pipewire",
    "plasma",
    "profile",
    "python",
    "reboot",
    "restore",
    "script",
    "security",
    "server",
    "service",
    "session",
    "settings",
    "shell",
    "snapshot",
    "socket",
    "ssh",
    "storage",
    "sudo",
    "sync",
    "systemd",
    "systemctl",
    "terminal",
    "theme",
    "update",
    "upload",
    "usb",
    "video",
    "wayland",
    "window",
    "wireguard",
    "xorg",
    "xwayland",
)

FALLBACK_COMMON_WORDS = (
    "about",
    "after",
    "again",
    "always",
    "another",
    "around",
    "available",
    "because",
    "before",
    "between",
    "better",
    "change",
    "check",
    "clean",
    "clear",
    "complete",
    "could",
    "current",
    "different",
    "done",
    "during",
    "early",
    "enough",
    "every",
    "example",
    "expected",
    "first",
    "found",
    "great",
    "important",
    "inside",
    "later",
    "local",
    "maybe",
    "missing",
    "normal",
    "option",
    "other",
    "people",
    "please",
    "possible",
    "problem",
    "ready",
    "really",
    "right",
    "same",
    "should",
    "simple",
    "small",
    "something",
    "source",
    "state",
    "still",
    "support",
    "there",
    "these",
    "thing",
    "think",
    "through",
    "today",
    "using",
    "verify",
    "while",
    "where",
    "which",
    "without",
    "working",
    "would",
)

BOOSTED_COMMON_WORDS = (
    "also",
    "amazing",
    "apple",
    "appendix",
    "append",
    "application",
    "apply",
    "back",
    "come",
    "find",
    "for",
    "from",
    "good",
    "have",
    "help",
    "into",
    "just",
    "know",
    "like",
    "look",
    "make",
    "more",
    "need",
    "only",
    "open",
    "over",
    "save",
    "some",
    "take",
    "test",
    "than",
    "that",
    "this",
    "time",
    "want",
    "well",
    "when",
    "with",
    "word",
    "work",
)


SENSITIVE_PREFIXES = ("sk-", "pk-", "ghp_", "gho_", "ghu_", "ghs_", "github_pat_")
LEARNED_SURFACE_THRESHOLD = 2
RECENCY_WINDOW = 50
RECENCY_WEIGHT = 5.0


def learned_words_path() -> Path:
    return config_learned_words_path()


def normalize_word(word: str) -> str:
    return word.strip().lower()


def is_private_or_sensitive(word: str) -> bool:
    stripped = word.strip()
    lowered = stripped.lower()
    if len(stripped) < 3:
        return True
    if lowered.startswith(SENSITIVE_PREFIXES):
        return True
    if any(marker in stripped for marker in ("@", "://", "/", "\\")):
        return True
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", stripped):
        return True
    if re.search(r"[a-z]+[A-Z][a-zA-Z]*", stripped):
        return True
    if re.search(r"[0-9a-fA-F]{12,}", stripped):
        return True
    symbol_count = sum(1 for char in stripped if not char.isalnum())
    digit_count = sum(1 for char in stripped if char.isdigit())
    if symbol_count >= 2 or digit_count >= 4:
        return True
    return not bool(re.fullmatch(r"[A-Za-z][A-Za-z-]*", stripped))


def completion_suffix(suggestion: str, prefix: str) -> str:
    if suggestion.lower().startswith(prefix.lower()):
        return suggestion[len(prefix) :]
    return suggestion


def load_ranked_words(filename: str, fallback: tuple[str, ...] = ()) -> tuple[str, ...]:
    try:
        text = resources.files("keystone_osk").joinpath("data", filename).read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError):
        return fallback
    words = []
    seen = set()
    for line in text.splitlines():
        word = normalize_word(line)
        if not word or word in seen or is_private_or_sensitive(word):
            continue
        seen.add(word)
        words.append(word)
    return tuple(words) or fallback


TECH_WORDS = load_ranked_words("tech_words.txt", FALLBACK_TECH_WORDS)
COMMON_WORDS = load_ranked_words("common_words.txt", FALLBACK_COMMON_WORDS)
EARLY_COMMON_WORDS = COMMON_WORDS[:2500]


@dataclass
class AutocompleteEngine:
    tech_words: tuple[str, ...] = TECH_WORDS
    common_words: tuple[str, ...] = COMMON_WORDS
    learned_counts: dict[str, int] = field(default_factory=dict)
    learned_boosts: dict[str, int] = field(default_factory=dict)
    learned_seen: dict[str, int] = field(default_factory=dict)
    events: int = 0
    learning_enabled: bool = True

    def observe_typed_word(self, word: str) -> None:
        normalized = normalize_word(word)
        if not self.learning_enabled or is_private_or_sensitive(normalized):
            return
        self.learned_counts[normalized] = self.learned_counts.get(normalized, 0) + 1
        self.events += 1
        self.learned_seen[normalized] = self.events

    def boost_word(self, word: str) -> None:
        normalized = normalize_word(word)
        if is_private_or_sensitive(normalized):
            return
        self.learned_counts[normalized] = max(LEARNED_SURFACE_THRESHOLD, self.learned_counts.get(normalized, 0))
        self.learned_boosts[normalized] = self.learned_boosts.get(normalized, 0) + 1
        self.events += 1
        self.learned_seen[normalized] = self.events

    def suggestions(self, prefix: str, limit: int = 3) -> tuple[str, ...]:
        normalized_prefix = normalize_word(prefix)
        if limit <= 0 or len(normalized_prefix) < 2 or is_private_or_sensitive(normalized_prefix + "a"):
            return ()
        ranked: list[str] = []
        ranked.extend(self._matching_learned(normalized_prefix))
        boosted_common = BOOSTED_COMMON_WORDS if self.common_words == COMMON_WORDS else ()
        early_common = EARLY_COMMON_WORDS if self.common_words == COMMON_WORDS else ()
        ranked.extend(self._matching_static(boosted_common, normalized_prefix, min_prefix=2))
        ranked.extend(self._matching_static(self.tech_words, normalized_prefix, min_prefix=2))
        ranked.extend(self._matching_static(early_common, normalized_prefix, min_prefix=2))
        ranked.extend(self._matching_static(self.common_words, normalized_prefix, min_prefix=3))
        return tuple(dict.fromkeys(ranked))[:limit]

    def clear_learned_words(self) -> None:
        self.learned_counts.clear()
        self.learned_boosts.clear()
        self.learned_seen.clear()

    def _matching_learned(self, prefix: str) -> list[str]:
        words = [
            word
            for word, count in self.learned_counts.items()
            if count >= LEARNED_SURFACE_THRESHOLD and word != prefix and word.startswith(prefix) and not is_private_or_sensitive(word)
        ]
        return sorted(words, key=lambda word: (-self.learned_boosts.get(word, 0), -self._learned_score(word), word))

    def _learned_score(self, word: str) -> float:
        recency = max(0.0, 1.0 - (self.events - self.learned_seen.get(word, 0)) / RECENCY_WINDOW)
        return self.learned_counts[word] + RECENCY_WEIGHT * recency

    def _matching_static(self, words: tuple[str, ...], prefix: str, min_prefix: int) -> list[str]:
        # Static word lists are normalized and privacy-filtered at load time
        # (load_ranked_words), so this per-keystroke scan stays cheap.
        if len(prefix) < min_prefix:
            return []
        matches: list[str] = []
        for word in words:
            normalized = normalize_word(word)
            if normalized != prefix and _static_word_matches_prefix(normalized, prefix):
                matches.append(normalized)
        return matches


def _collapse_doubled_letters(word: str) -> str:
    chars: list[str] = []
    for char in word:
        if not chars or chars[-1] != char:
            chars.append(char)
    return "".join(chars)


def _static_word_matches_prefix(word: str, prefix: str) -> bool:
    if word.startswith(prefix):
        return True
    return len(prefix) >= 3 and _collapse_doubled_letters(word).startswith(prefix)


def load_engine(path: Path | None = None) -> AutocompleteEngine:
    words_path = path or learned_words_path()
    try:
        data = json.loads(words_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AutocompleteEngine()
    counts = data.get("counts", {}) if isinstance(data, dict) else {}
    boosts = data.get("boosts", {}) if isinstance(data, dict) else {}
    seen = data.get("seen", {}) if isinstance(data, dict) else {}
    return AutocompleteEngine(
        learned_counts={normalize_word(k): int(v) for k, v in counts.items() if not is_private_or_sensitive(normalize_word(k))},
        learned_boosts={normalize_word(k): int(v) for k, v in boosts.items() if not is_private_or_sensitive(normalize_word(k))},
        learned_seen={normalize_word(k): int(v) for k, v in seen.items() if not is_private_or_sensitive(normalize_word(k))},
        events=int(data.get("events", 0)) if isinstance(data, dict) else 0,
        learning_enabled=bool(data.get("learning_enabled", True)) if isinstance(data, dict) else True,
    )


def save_engine(engine: AutocompleteEngine, path: Path | None = None) -> None:
    words_path = path or learned_words_path()
    words_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": 2,
        "learning_enabled": engine.learning_enabled,
        "counts": engine.learned_counts,
        "boosts": engine.learned_boosts,
        "seen": engine.learned_seen,
        "events": engine.events,
    }
    tmp_path = words_path.with_suffix(words_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    try:
        tmp_path.replace(words_path)
    except OSError:
        # Don't leave a half-written .tmp behind to corrupt the next load.
        tmp_path.unlink(missing_ok=True)
        raise
