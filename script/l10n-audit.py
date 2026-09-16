"""Whole-repo localization inventory.

Reports, per crate:
  * how many translate calls (locale::t / t_static / t_format) exist, split
    into production and test code;
  * how many user-visible-looking literals sit at a display call site but are
    not wrapped in a translate call.

Descriptions and titles reach the screen through many call shapes, so the
display-site heuristic is deliberately broad; the point is triage, not a gate.
Test code is excluded everywhere: `#[cfg(test)]` helper functions named `t`
(see crates/agent/src/tool_permissions.rs) otherwise swamp the counts.

Run: python target/l10n-audit.py            # per-crate summary
     python target/l10n-audit.py -v <crate> # per-literal detail for one crate
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DICT = json.loads((ROOT / 'assets/locales/zh-CN.json').read_text(encoding='utf-8'))

# A translate call, either fully qualified or imported into scope. `(?<![\w.])`
# rejects method calls such as `handler.t(...)` in the agent tests.
TRANSLATE = re.compile(r'(?<![\w.])(?:locale::)?t(?:_format|_static)?\(\s*"')

STR = re.compile(r'"((?:[^"\\]|\\.)*)"', re.DOTALL)

# Argument positions that end up rendered on screen.
DISPLAY_CALLS = (
    r'Label::new\(\s*',
    r'Headline::new\(\s*',
    r'Text::new\(\s*',
    r'Button::new\(\s*[^,()]*,\s*',
    r'ButtonLike::new\(\s*[^,()]*,\s*',
    r'IconButton::new\(\s*[^,()]*,\s*',
    r'DropdownMenu::new\(\s*[^,()]*,\s*',
    r'ContextMenuEntry::new\(\s*',
    r'MenuItem::new\(\s*[^,()]*,\s*',
    r'Tooltip::text\(\s*',
    r'Tooltip::with_meta\(\s*[^,()]*,\s*',
    r'StatusToast::new\(\s*',
    r'EmptyState::new\(\s*',
    r'Chip::new\(\s*',
    r'ListItem::new\(\s*',
    r'Banner::new\(\s*',
    r'SegmentedControl::new\(\s*',
    r'SharedString::new_static\(\s*',
    r'SharedString::from\(\s*',
    r'InputField::new\([^,]*,',
    r'SwitchField::new\(\s*[^,()]*,\s*',
    r'Checkbox::new\(\s*[^,()]*,\s*',
    r'ToggleState::new\(\s*[^,()]*,\s*',
    r'\.aria_label\(\s*',
    r'\.aria_description\(\s*',
    r'\.placeholder\(\s*',
    r'\.placeholder_text\(\s*',
    r'\.set_placeholder_text\(\s*',
    r'\.label\(\s*',
    r'\.text\(\s*',
    r'\.message\(\s*',
    r'\.title\(\s*',
    r'\.description\(\s*',
    r'\.header\(\s*',
    r'\.tooltip\(Tooltip::text\(\s*',
    r'\.notification\(\s*',
)
PREFIX = re.compile(r'(?:' + '|'.join(DISPLAY_CALLS) + r')$', re.DOTALL)

NOT_TEXT = (
    re.compile(r'^[a-z0-9_.\-/]+$'),
    re.compile(r'^\{'),
    re.compile(r'^(https?|zed|mailto)://'),
    re.compile(r'^[\s,|:;/\\-]*$'),
    re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$'),          # single bare word
)


def looks_like_text(s: str) -> bool:
    if len(s) < 2 or len(s) > 400 or '\n' in s:
        return False
    return not any(p.match(s) for p in NOT_TEXT)


def strip_comments(text: str) -> str:
    """Blank out comments and string bodies alike, keeping offsets intact.

    String bodies are blanked so that a `"` inside a comment or an escaped
    quote inside a literal cannot desynchronise the scan.
    """
    out = list(text)
    i, n = 0, len(text)

    def blank(s, e):
        for k in range(s, min(e, n)):
            if text[k] != '\n':
                out[k] = ' '

    while i < n:
        two = text[i:i + 2]
        if two == '//':
            e = text.find('\n', i)
            blank(i, n if e == -1 else e)
            i = n if e == -1 else e
        elif two == '/*':
            d, e = 1, i + 2
            while e < n and d:
                if text.startswith('/*', e):
                    d += 1; e += 2
                elif text.startswith('*/', e):
                    d -= 1; e += 2
                else:
                    e += 1
            blank(i, e); i = e
        elif text[i] == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == '\\' else 1
            i += 1
        elif text[i] == "'" and i + 2 < n and (text[i + 1] == '\\' or text[i + 2] == "'"):
            # char literal / lifetime: skip so a '"' inside cannot confuse us
            i += 1
            while i < n and text[i] != "'":
                i += 2 if text[i] == '\\' else 1
            i += 1
        else:
            i += 1
    return ''.join(out)


# An *inline* test module: the only shape that pushes production code out of
# the way. `#[cfg(test)] mod foo;` declares a module in a separate file and is
# routinely placed near the top (crates/sidebar/src/sidebar.rs:86), so it must
# not be treated as the start of the test region - doing so hides the other
# 8000 lines of that file. Likewise `#[cfg(test)] impl X` / `#[cfg(test)] fn`
# sit next to the code they serve, not at the end of the file.
TEST_MODULE = re.compile(
    r'#\[cfg\(test\)\](?:\s*#\[[^\]]*\])*\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+\w+\s*\{'
    r'|(?:^|\n)(?:pub(?:\([^)]*\))?\s+)?mod\s+tests\s*\{'
)


def scan(path: pathlib.Path):
    """Return (translate_calls, candidates) for one file."""
    raw = path.read_text(encoding='utf-8', errors='ignore')
    text = strip_comments(raw)
    # Everything from the first inline test module on is test code.
    m = TEST_MODULE.search(text)
    prod = text[:m.start()] if m else text
    calls = len(TRANSLATE.findall(prod))

    cands = []
    for m in STR.finditer(prod):
        s = m.group(1)
        if not looks_like_text(s) or s in DICT:
            continue
        if not PREFIX.search(prod[max(0, m.start() - 120):m.start()]):
            continue
        cands.append((prod.count('\n', 0, m.start()) + 1, s))
    return calls, cands


def main() -> None:
    verbose = False
    if sys.argv[1:2] == ['-v']:
        verbose = True
        targets = sys.argv[2:]
    else:
        targets = sys.argv[1:]

    crates = {}
    for path in sorted((ROOT / 'crates').glob('*/src/**/*.rs')):
        rel = path.relative_to(ROOT).as_posix()
        crate = rel.split('/')[1]
        if crate == 'locale':
            continue
        if targets and crate not in targets:
            continue
        calls, cands = scan(path)
        c = crates.setdefault(crate, {'calls': 0, 'cands': 0, 'files': []})
        c['calls'] += calls
        if cands:
            c['cands'] += len(cands)
            c['files'].append((rel, cands))

    if verbose:
        for crate in sorted(crates):
            c = crates[crate]
            print(f'=== {crate}: {c["calls"]} translate calls, {c["cands"]} unwrapped candidates')
            for rel, cands in sorted(c['files'], key=lambda x: -len(x[1])):
                print(f'  -- {rel}  ({len(cands)})')
                for line, s in cands:
                    print(f'     {line:6d}  {s[:100]}')
        return

    rows = sorted(crates.items(), key=lambda kv: -kv[1]['cands'])
    print(f'{"crate":28} {"t()":>6} {"unwrapped":>10}')
    for crate, c in rows:
        if c['cands'] or c['calls']:
            print(f'{crate:28} {c["calls"]:6d} {c["cands"]:10d}')
    total_calls = sum(c['calls'] for c in crates.values())
    total_cands = sum(c['cands'] for c in crates.values())
    print(f'{"TOTAL":28} {total_calls:6d} {total_cands:10d}')
    print(f'crates scanned: {len(crates)}')


if __name__ == '__main__':
    main()
