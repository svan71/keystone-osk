from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from keystone_osk.config import snippets_path

# Action types this version can execute. Unknown types are ignored (forward-compat
# for future "key" macro actions) so older builds tolerate newer snippet files.
USABLE_ACTION_TYPES = frozenset({"text"})


@dataclass(frozen=True)
class SnippetAction:
    type: str
    value: str


@dataclass(frozen=True)
class Snippet:
    label: str
    actions: tuple[SnippetAction, ...]


def _parse_action(raw: object) -> SnippetAction | None:
    if not isinstance(raw, Mapping):
        return None
    action_type = raw.get("type")
    value = raw.get("value")
    if not isinstance(action_type, str) or not isinstance(value, str):
        return None
    return SnippetAction(type=action_type, value=value)


def _parse_snippet(raw: object) -> Snippet | None:
    if not isinstance(raw, Mapping):
        return None
    label = raw.get("label")
    if not isinstance(label, str) or not label:
        return None
    raw_actions = raw.get("actions")
    actions: tuple[SnippetAction, ...] = ()
    if isinstance(raw_actions, list):
        actions = tuple(a for a in (_parse_action(x) for x in raw_actions) if a is not None)
    # Beginner shorthand: a top-level "text" string is one text action. Used only
    # when "actions" didn't already supply a usable action (so "actions" wins).
    if not any(a.type in USABLE_ACTION_TYPES for a in actions):
        shorthand = raw.get("text")
        if isinstance(shorthand, str) and shorthand:
            actions = (SnippetAction(type="text", value=shorthand),)
    if not any(a.type in USABLE_ACTION_TYPES for a in actions):
        return None
    return Snippet(label=label, actions=actions)


def load_snippets_with_errors(
    environ: Mapping[str, str] | None = None,
) -> tuple[list[Snippet], list[str], str | None]:
    """Load snippets and return (snippets, entry_errors, file_error).

    entry_errors is a list of human-readable strings, one per dropped snippet
    (each includes the entry index).

    file_error is a single string for file-level failures (bad JSON, wrong
    shape, unreadable), or None when there is no file-level error.

    Both are empty/None when the file is missing (missing is not an error).
    """
    path = snippets_path(environ)
    if not path.exists():
        return [], [], None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [], [], f"snippets.json could not be read: {exc}"
    try:
        data = json.loads(text)
    except ValueError as exc:
        return [], [], f"snippets.json is not valid JSON: {exc}"
    if not isinstance(data, Mapping):
        return [], [], f"snippets.json top-level must be an object, got {type(data).__name__}"
    raw_snippets = data.get("snippets")
    if not isinstance(raw_snippets, list):
        return [], [], f"snippets.json missing 'snippets' list (got {type(raw_snippets).__name__ if raw_snippets is not None else 'nothing'})"
    snippets: list[Snippet] = []
    entry_errors: list[str] = []
    for idx, raw in enumerate(raw_snippets):
        parsed = _parse_snippet(raw)
        if parsed is None:
            # Build a short description of what went wrong for this entry.
            if not isinstance(raw, Mapping):
                reason = f"not an object (got {type(raw).__name__})"
            elif not isinstance(raw.get("label"), str) or not raw.get("label"):
                reason = "missing 'label' key"
            else:
                reason = "no usable 'text' or 'actions' — keys must be exactly 'label' and 'text'"
            entry_errors.append(f"entry {idx}: {reason}")
        else:
            snippets.append(parsed)
    return snippets, entry_errors, None


def load_snippets(environ: Mapping[str, str] | None = None) -> list[Snippet]:
    snippets, _entry_errors, _file_error = load_snippets_with_errors(environ)
    return snippets


def snippet_text(snippet: Snippet) -> str:
    return "".join(a.value for a in snippet.actions if a.type == "text")


# Starter file written for first-time users. JSON has no comments, so the help
# lives in "_README"/"_howto" string fields (the loader only reads "snippets",
# so these are ignored). Two working examples show the format.
SNIPPETS_TEMPLATE = """{
  "_README": [
    "Each line under 'snippets' is one button in the Snippets menu.",
    "To add one: copy a line, then change ONLY the quoted words AFTER the colons.",
    "Keep the words 'label' and 'text' exactly as they are — never rename them.",
    "  \\"label\\": the button name        \\"text\\": what gets typed",
    "Save, then tap the Snippets key again to see your new button.",
    "Put a comma at the end of every line except the last.",
    "Lines starting with _ are just notes and are ignored.",
    "",
    "RIGHT: { \\"label\\": \\"Gmail\\", \\"text\\": \\"you@example.com\\" }",
    "WRONG: { \\"Gmail\\": \\"you@example.com\\" }  <- keys must stay exactly 'label' and 'text'"
  ],
  "snippets": [
    { "label": "My Email", "text": "you@example.com" },
    { "label": "Sign-off", "text": "Thanks!" }
  ]
}
"""


def ensure_snippets_file(environ: Mapping[str, str] | None = None) -> Path:
    """Return the snippets file path, creating it from the template if missing.

    Never overwrites an existing file.
    """
    path = snippets_path(environ)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(SNIPPETS_TEMPLATE, encoding="utf-8")
    return path


def reset_snippets_file(environ: Mapping[str, str] | None = None) -> "Path | None":
    """Overwrite snippets.json with SNIPPETS_TEMPLATE.

    If the file already exists, copy it to snippets.json.bak first (overwriting
    any previous backup), then write the template.

    Returns the Path of the backup file if a backup was made, else None.
    """
    import shutil

    path = snippets_path(environ)
    path.parent.mkdir(parents=True, exist_ok=True)
    bak_path: Path | None = None
    if path.exists():
        bak_path = path.with_suffix(".json.bak")
        shutil.copy2(path, bak_path)  # raises on failure; write_text is NOT reached
    path.write_text(SNIPPETS_TEMPLATE, encoding="utf-8")
    return bak_path
