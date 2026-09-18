#!/usr/bin/env python3
"""Fail when a translated string sits behind a value that also reaches a machine.

`script/l10n-blocklist.txt` guards the *crate* boundary: no `locale::` inside
model-facing paths. It cannot see the shape that produced both real leaks this
fork has had, where the label and the machine-facing consumer live in the same
GUI-only crate:

    impl ToString for KernelStatus -> locale::t("Idle")     # crates/repl
    telemetry::event!("Kernel Status Changed", kernel_status = ..to_string())

So this check is about call-site shape, not path:

  1. no `locale::t*` inside an `impl Display` / `impl ToString` / `to_string`
     body. A `Display` impl is what `format!("{x}")`, log lines and telemetry
     reach for, so localizing one makes the UI language leak into all of them.
     Expose `fn label(&self) -> SharedString` for display sites and keep the
     English text in a separate `fn as_str(&self) -> &'static str`.
  2. no `locale::t*` inside a `telemetry::event!` invocation, including inside a
     `format!` there.

Both rules are deliberately conservative: they scan line windows rather than
parsing Rust, so an exotic layout can slip past. That is acceptable - a missed
warning is cheaper than a false CI failure, and `script/l10n-audit.py` lists
what these two rules cannot see.

Run: python script/check-l10n-shapes.py     # exit 1 on a violation
"""

import os
import pathlib
import re
import sys
from bisect import bisect_right

ROOT = pathlib.Path(__file__).resolve().parent.parent

LOCALE_CALL = re.compile(r"(?<!\w)locale::t(?:_static|_format)?\s*\(")
# An `impl` or a bare `fn to_string` that opens its body on this line.
BODY_OPENER = re.compile(
    r"^\s*(impl(?:<[^>]*>)?\s+(?:fmt::)?(?:ToString|Display)\s+for\b"
    r"|pub(?:\([^)]*\))?\s+fn\s+to_string\s*\(|fn\s+to_string\s*\()"
)


def violations(rel: str, lines: list[str]) -> list[str]:
    found = []
    # Comments can contain braces, `impl` headers and the words `locale::t`, so
    # every rule runs on comment-stripped code. Offsets into `joined` stand in
    # for parse positions; `starts` maps an offset back to a line number.
    codes: list[str] = []
    in_block_comment = False
    for line in lines:
        code, in_block_comment = strip_line_noise(line, in_block_comment)
        codes.append(code)
    joined = "\n".join(codes)
    starts = [0]
    for code in codes:
        starts.append(starts[-1] + len(code) + 1)

    def line_of(offset: int) -> int:
        return bisect_right(starts, offset) - 1 + 1  # 1-based

    def line_start(index: int) -> int:
        return starts[index]

    # Rule 1: the body of `impl Display`/`impl ToString`/`fn to_string`,
    # delimited by real brace depth.
    bodies = []
    for index, code in enumerate(codes):
        if BODY_OPENER.match(code):
            bodies.append(span_of(joined, line_start(index), "{", "}"))
    for match in LOCALE_CALL.finditer(joined):
        for begin, end in bodies:
            if begin <= match.start() <= end:
                found.append(
                    f"{rel}:{line_of(match.start())}: localized text inside a "
                    "Display/ToString body"
                )
                break

    # Rule 2: inside a telemetry::event!(..) invocation, delimited by real
    # parenthesis depth - a line window over-runs into the UI code below and
    # reports perfectly good labels.
    for match in re.finditer(r"\btelemetry::event!\s*\(", joined):
        begin, end = span_of(joined, match.start(), "(", ")")
        hit = LOCALE_CALL.search(joined, begin, end)
        if hit:
            found.append(
                f"{rel}:{line_of(hit.start())}: localized text inside a "
                "telemetry::event! call"
            )
    return found


def span_of(text: str, start: int, opener: str, closer: str) -> tuple[int, int]:
    """The `{begin, end}` offsets of the first balanced `opener..closer` run at
    or after `start`, including both delimiters."""
    depth = 0
    begin = text.find(opener, start)
    if begin < 0:
        return (-1, -1)
    for index in range(begin, len(text)):
        ch = text[index]
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return (begin, index)
    return (begin, len(text))


def strip_line_noise(line: str, in_block_comment: bool) -> tuple[str, bool]:
    """Drop comments from one line, carrying `/* */` state across lines.

    String literals are kept (their braces count toward nesting, which is the
    conservative direction for these two rules).
    """
    out = []
    i = 0
    quote = False
    while i < len(line):
        two = line[i : i + 2]
        if in_block_comment:
            if two == "*/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue
        if quote:
            out.append(line[i])
            if line[i] == '"':
                quote = False
            i += 2 if line[i] == "\\" else 1
            continue
        if two == "//":
            break
        if two == "/*":
            in_block_comment = True
            i += 2
            continue
        if line[i] == '"':
            quote = True
        out.append(line[i])
        i += 1
    return "".join(out), in_block_comment


def main() -> int:
    all_found: list[str] = []
    for path in sorted((ROOT / "crates").rglob("*.rs")):
        rel = path.relative_to(ROOT).as_posix()
        if f"{os.sep}target{os.sep}" in str(path.parent):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "locale::t" not in text:
            continue
        all_found.extend(violations(rel, text.splitlines()))

    if all_found:
        for finding in all_found:
            print(finding)
        print(
            f"\nError: {len(all_found)} localized value(s) reachable from a "
            "Display/ToString body or a telemetry::event! call.\n"
            "Keep the English text in a plain accessor and translate at the "
            "display site (see crates/repl/src/kernels/mod.rs)."
        )
        return 1
    print("l10n shape check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
