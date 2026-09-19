"""Shared helpers for the fork's l10n tools.

`check-l10n-dict.py` and `l10n-audit.py` used to carry private copies of the
blocklist reader and the Rust comment/string masker, and the copies drifted
apart (only one handled raw strings, so a raw string containing `\"` produced
phantom literals in the other). Both import from here now.
`check-l10n-shapes.py` keeps its own line-based stripper deliberately: its two
rules need string contents kept (braces inside literals count toward the
nesting it measures), which is the opposite trade-off from the masker below.

The data these helpers read lives in `script/l10n-blocklist.txt`; see that
file for what each entry means and why it is listed.
"""

import re
import subprocess
from pathlib import Path


def repo_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(out.stdout.strip())


def read_blocklist(root: Path) -> tuple[str, ...]:
    """Model-facing paths, read from `script/l10n-blocklist.txt`.

    Shared with `script/check-l10n-boundary` (which parses the same file in
    bash). Strings under them may reach a model, so they are neither
    GUI-translation candidates nor evidence that a dictionary entry is dead.
    """
    entries = []
    for line in (root / "script" / "l10n-blocklist.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        entry = line.split("#", 1)[0].strip()
        if entry:
            entries.append(entry)
    return tuple(entries)


# Rust string escapes that may appear inside t("...") keys.
_SOURCE_ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "0": "\0",
    '"': '"',
    "'": "'",
    "\\": "\\",
}


def decode_source_key(raw: str) -> str:
    """Decode backslash escapes in a Rust string literal captured from source.

    A backslash at the end of a line is a line continuation: Rust removes it
    together with the following whitespace, so the compiled key has a single
    space there, not a newline. Without this the long, wrapped descriptions
    would be reported as MISSING under a key that differs from the one the
    runtime actually looks up.
    """
    raw = re.sub(r"\\\n[ \t]*", "", raw)
    decoded = re.sub(r"\\(.)", lambda m: _SOURCE_ESCAPES.get(m.group(1), m.group(0)), raw)
    return re.sub(
        r"\\u\{([0-9a-fA-F]+)\}",
        lambda m: chr(int(m.group(1), 16)),
        decoded,
    )


def strip_rust_noise(text: str) -> str:
    """Blank out comments, char literals and raw-string bodies, preserving
    every byte offset.

    Quote characters inside comments (`// the "foo" panel`) would otherwise
    shift string-literal pairing and produce phantom literals. Replacing the
    comment bytes with spaces keeps line numbers and offsets intact. Normal
    string literals are walked over but kept: callers read them out of the
    result.
    """
    out = list(text)
    i, n = 0, len(text)

    def blank(start: int, end: int) -> None:
        for k in range(start, min(end, n)):
            if text[k] != "\n":
                out[k] = " "

    while i < n:
        ch = text[i]
        two = text[i : i + 2]
        if two == "//":
            end = text.find("\n", i)
            blank(i, n if end == -1 else end)
            i = n if end == -1 else end
        elif two == "/*":
            depth, end = 1, i + 2
            while end < n and depth:
                if text.startswith("/*", end):
                    depth += 1
                    end += 2
                elif text.startswith("*/", end):
                    depth -= 1
                    end += 2
                else:
                    end += 1
            blank(i, end)
            i = end
        elif ch == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
            i += 1
        elif ch == "r" and i + 1 < n and text[i + 1] in "#\"":
            hashes = 0
            while text[i + 1 + hashes : i + 2 + hashes] == "#":
                hashes += 1
            # `r#"…"#` is a raw string, but `r#type` is a raw identifier:
            # require the quote, or the terminator search would swallow the
            # rest of the file.
            if text[i + 1 + hashes] != '"':
                i += 1
                continue
            opening = i + 1 + hashes
            end = text.find('"' + "#" * hashes, opening + 1)
            if end == -1:
                i = n
            else:
                # Blank the contents; the delimiting quotes stay behind as a
                # balanced empty pair for the literal regex.
                blank(opening + 1, end)
                i = end + 1 + hashes
        elif ch == "'":
            # A char literal ('x', '\n', '\u{1F600}') and not a lifetime ('a).
            j = i + 1
            if j < n and text[j] == "\\":
                j += 1
                if text[j : j + 2] == "u{":
                    j = text.find("}", j)
                else:
                    j += 1
            elif j < n and text[j] not in "'":
                j += 1
            if j < n and text[j] == "'" and text[i + 1] != "'":
                # Blank fully: a `"` inside ('"') must not reach the literal
                # regex, and the apostrophes themselves are irrelevant to it.
                blank(i, j + 1)
                i = j + 1
            else:
                i += 1
        else:
            i += 1
    return "".join(out)
