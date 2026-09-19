#!/usr/bin/env python3
"""Report GUI strings wrapped in t("...")/t_static("...") that lack a
zh-CN translation.

Read-only by default: prints missing/unused keys and always exits 0.
With `--strict` it exits 1 when a wrapped key has no translation or when a
violation is found, which is how CI runs it. Run from anywhere inside the repo.

`unused` is split in two, because "not a t("...") argument" has three
different causes:

- UNUSED-DYNAMIC: the key's literal does exist in a non-blocklisted crate,
  so a dynamic `t(<variable>)` call can resolve it at runtime (match arms,
  ...). Keep the entry.
- UNUSED: the key's literal does not exist anywhere; either the string was
  renamed upstream (deprecated, keep) or the entry was never wired up
  (review it).
- VIOLATION: the key's literal exists only inside a model-facing path (see
  `script/l10n-blocklist.txt`). Translating it would change what a model
  receives, so it must be removed from the dictionary. Only computed for
  UNUSED keys, since a literal that also occurs in GUI code is ambiguous,
  not a violation.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from l10n_common import (
    decode_source_key,
    read_blocklist,
    repo_root,
    strip_rust_noise,
)

CALL_PATTERN = re.compile(r'(?<!\w)t(?:_format|_static)?\(\s*"((?:[^"\\]|\\.)*)"', re.DOTALL)
# t()/t_format()/t_static() calls whose argument is not a string literal
# (variable, match/if expression). Their runtime values cannot be extracted
# statically,
# so they are listed for manual audit instead of entering missing/unused.
# (Allows newlines between `(` and a literal, so multi-line calls whose key
# is on the next line are not misreported; skips the fn definitions in
# crates/locale itself.)
DYNAMIC_PATTERN = re.compile(r"(?<!\w)(?<!fn )(?<!\$)t(?:_format|_static)?\(\s*(?!\s*\")")
# SCREAMING_CASE keys that *are* recoverable: `t(CONST)` / `t_static(CONST)`
# where the file also defines `const NAME: &str = "..."` or
# `static NAME: &str = "..."`. DYNAMIC_PATTERN files these as "for manual
# audit", which is how nine wrapped labels shipped with a key the dictionary
# never had (crates/editor/src/editor.rs RIGHT_CLICK_HINT,
# crates/workspace/src/pane.rs DELETED_MESSAGE, ...) - they render in English
# forever and `--strict` reports `missing: 0`. Resolving the consts here closes
# that hole without asking anyone to read a list of 130 call sites.
CONST_PATTERN = re.compile(
    r'(?:const|static)\s+([A-Z0-9_]{3,})\s*:\s*&str\s*=\s*"((?:[^"\\]|\\.)*)"'
)
INDIRECT_CALL_PATTERN = re.compile(
    r'(?<!\w)(?<!fn )(?<!\$)(?:locale::)?t(?:_format|_static)?\(\s*([A-Z0-9_]{3,})\s*\)'
)
# DOTALL: `\\.` must also match a `\` + newline line continuation inside a
# string literal, or pairing silently derails for the rest of the file.
LITERAL_PATTERN = re.compile(r'"((?:[^"\\]|\\.)*)"', re.DOTALL)
MAX_LISTED = 50
MISSING_LISTED = 400

def blocked_only_keys(
    root: Path, keys: list[str], blocklist: tuple[str, ...]
) -> list[str]:
    """Keys whose English source occurs inside a model-facing path.

    Callers pass only keys that appear in no non-blocklisted file, so a hit
    means the text exists exclusively on the model side. Multi-line keys are
    probed by their first line: `git grep` is line-based and would never match
    a pattern containing a newline, and a first line long enough to be
    distinctive is a sound superset test.
    """
    violations = []
    for key in keys:
        needle = key if "\n" not in key else key.split("\n")[0].strip()
        if len(needle) < 15:
            continue
        result = subprocess.run(
            ["git", "grep", "--no-color", "-F", "-l", "-e", needle, "--", *blocklist],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            violations.append(key)
    return violations


def main() -> int:
    root = repo_root()
    blocklist = read_blocklist(root)
    used: set[str] = set()
    indirect: dict[str, str] = {}
    dynamic: set[str] = set()
    # First non-blocklisted file in which each string literal occurs, used to
    # tell "reachable through a dynamic t() call" from "no call site at all".
    literal_files: dict[str, str] = {}
    for path in sorted((root / "crates").rglob("*.rs")):
        rel = path.relative_to(root).as_posix() + "/"
        if rel.startswith(blocklist):
            continue
        # `crates/locale` defines `t()` itself; its tests call `t("Hello {name}")`
        # and `t("No Such Translation Key")` as fixtures. Scanning it would report
        # those fixtures as MISSING translations for real GUI strings.
        if rel.startswith("crates/locale/"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        masked = strip_rust_noise(text)
        for match in CALL_PATTERN.finditer(masked):
            key = decode_source_key(match.group(1))
            if key:
                used.add(key)
        consts = {
            name: decode_source_key(value)
            for name, value in CONST_PATTERN.findall(masked)
        }
        for match in INDIRECT_CALL_PATTERN.finditer(masked):
            key = consts.get(match.group(1))
            if key:
                used.add(key)
                indirect.setdefault(key, f"{rel.rstrip('/')}:{match.group(1)}")
        for match in DYNAMIC_PATTERN.finditer(masked):
            line = masked.count("\n", 0, match.start()) + 1
            dynamic.add(f"{rel.rstrip('/')}:{line}")
        for match in LITERAL_PATTERN.finditer(masked):
            literal_files.setdefault(decode_source_key(match.group(1)), rel)

    dictionary_path = root / "assets" / "locales" / "zh-CN.json"
    translated = set(json.loads(dictionary_path.read_text(encoding="utf-8")).keys())

    missing = sorted(used - translated)
    unused = sorted(translated - used)
    unused_dynamic = [key for key in unused if key in literal_files]
    unused_dead = [key for key in unused if key not in unused_dynamic]
    print(f"used: {len(used)}, translated: {len(translated)}")
    print(f"missing: {len(missing)}")
    # `missing` is the actionable list, so it is not truncated the way the
    # (mostly deprecated) unused lists are.
    for key in sorted(missing)[:MISSING_LISTED]:
        # Say so when the key only shows up through a const: the wrapped call
        # site is not visible from the key text alone.
        site = indirect.get(key)
        print(f"  MISSING  {key!r}" + (f"  (via {site})" if site else ""))
    if len(missing) > MISSING_LISTED:
        print(f"  ... and {len(missing) - MISSING_LISTED} more")
    print(f"unused: {len(unused)} ({len(unused_dynamic)} reachable via a dynamic t() call)")
    for key in unused_dead[:MAX_LISTED]:
        print(f"  UNUSED   {key!r}")
    for key in unused_dynamic[:MAX_LISTED]:
        print(f"  UNUSED-DYNAMIC  {key!r}  ({literal_files.get(key)})")
    violations = blocked_only_keys(root, unused_dead, blocklist)
    print(f"violations: {len(violations)}")
    for key in violations[:MAX_LISTED]:
        print(f"  VIOLATION  {key!r}  (exists only in a model-facing path)")
    dynamic_sorted = sorted(dynamic)
    print(f"dynamic: {len(dynamic_sorted)}")
    for site in dynamic_sorted[:MAX_LISTED]:
        print(f"  DYNAMIC  {site}")
    if "--strict" not in sys.argv:
        return 0
    if violations:
        print(f"{len(violations)} key(s) exist only in a model-facing path")
    if missing:
        # A `t("…")` call with no entry renders in English forever and is
        # otherwise invisible here: only the first MAX_LISTED are printed.
        print(f"{len(missing)} wrapped key(s) have no translation")
    return 1 if (violations or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
