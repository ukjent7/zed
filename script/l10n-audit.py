"""Whole-repo localization inventory.

Reports, per crate:
  * how many translate calls (locale::t / t_static / t_format) exist in
    production code;
  * how many user-visible-looking literals sit at a display call site but are
    not wrapped in a translate call (`unwrapped`);
  * how many single-word literals sit at those same call sites (`bare`), which
    `unwrapped` deliberately leaves out;
  * how many display-site literals already have a dictionary entry but are not
    wrapped (`ready`) - these render in English despite being translated, and
    are the only class that needs no dictionary work at all.

Descriptions and titles reach the screen through many call shapes, so the
display-site heuristic is deliberately broad; the point is triage, not a gate.
It now also covers the shapes that used to hide the largest single gap: the
`ui::ContextMenu` builder family (`.action`/`.entry`/`.submenu`/
`.toggleable_entry`), `Tooltip::for_action*`/`with_meta_in`, `Toast::new`,
`.with_title`, the message argument of `prompt`/`prompt_err`, and a prompt's
`&["Save", "Cancel"]` button array (which no call-shape prefix can anchor to).
Widening the shape list measured 467 -> 685 unwrapped and 145 -> 285 already
translated but unwrapped.

Still invisible, so a zero is not coverage: text that reaches a display call
through a variable or a function return (`fn title() -> &'static str`), copy
assembled by `format!`, and anything behind `#[cfg(test)]`/`feature =
"test-support"`.

Test code is excluded everywhere: `#[cfg(test)]` helper functions named `t`
(see crates/agent/src/tool_permissions.rs) otherwise swamp the counts. So is
storybook data: `Component::preview` bodies are blanked (see
blank_gallery_previews), which is what used to put crates/ui at the top.

`bare` is reported apart because that class is dominated by icon names, HTTP
header names and brands, yet it does hide one-word buttons ("Decline",
"Contacts", "Evaluate"). Check it per crate with `-v` before trusting a zero.

Run: python script/l10n-audit.py            # per-crate summary
     python script/l10n-audit.py -v <crate> # per-literal detail for one crate
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

# `window.prompt(.., &["Save", "Don't Save", "Cancel"], cx)` - a button list is
# an array literal, so no display-call prefix can ever anchor onto it. Requiring
# a capitalized first literal keeps `&["key"]` map-lookup noise out.
ANSWER_ARRAY = re.compile(
    r'&\[\s*"[A-Z][^"]*"(?:\s*,\s*"(?:[^"\\]|\\.)*")*\s*\]'
)

# Argument positions that end up rendered on screen.
DISPLAY_CALLS = (
    r'Label::new\(\s*',
    r'Headline::new\(\s*',
    r'Text::new\(\s*',
    r'Button::new\(\s*[^,()]*,\s*',
    r'Button::new_\w+\(\s*[^,()]*,\s*',
    r'ButtonLike::new\(\s*[^,()]*,\s*',
    r'ButtonLike::new_\w+\(\s*[^,()]*,\s*',
    r'IconButton::new\(\s*[^,()]*,\s*',
    r'DropdownMenu::new\(\s*[^,()]*,\s*',
    r'ContextMenuEntry::new\(\s*',
    r'MenuItem::new\(\s*[^,()]*,\s*',
    r'ListBulletItem::new\(\s*',
    r'Tooltip::text\(\s*',
    r'Tooltip::simple\(\s*',
    r'Tooltip::headered\(\s*',
    r'Tooltip::with_meta\(\s*[^,()]*,\s*',
    r'StatusToast::new\(\s*',
    r'EmptyState::new\(\s*',
    r'EmptyState::\w+\(\s*',
    r'MessagePopover::new\(\s*',
    r'Tag::new\(\s*',
    r'Chip::new\(\s*',
    r'ListItem::new\(\s*',
    r'Banner::new\(\s*',
    r'SegmentedControl::new\(\s*',
    r'SharedString::new_static\(\s*',
    r'SharedString::from\(\s*',
    r'InputField::new\([^,]*,',
    r'SwitchField::new\(\s*[^,()]*,\s*',
    r'Switch::new\(\s*[^,()]*,\s*',
    r'Checkbox::new\(\s*[^,()]*,\s*',
    r'ToggleState::new\(\s*[^,()]*,\s*',
    r'\.aria_label\(\s*',
    r'\.aria_description\(\s*',
    r'\.placeholder\(\s*',
    r'\.placeholder_text\(\s*',
    r'\.set_placeholder_text\(\s*',
    r'\.label\(\s*',
    r'\.label_trailing\(\s*',
    r'\.secondary_label\(\s*',
    r'\.set_label\(\s*',
    r'\.text\(\s*',
    r'\.title\(\s*',
    r'\.header_title\(\s*',
    r'\.description\(\s*',
    r'\.description_text\(\s*',
    r'\.header\(\s*',
    r'\.message\(\s*',
    r'\.primary_message\(\s*',
    r'\.secondary_message\(\s*',
    r'\.sub_message\(\s*',
    r'\.confirm_label\(\s*',
    r'\.dismiss_label\(\s*',
    r'\.tooltip\(Tooltip::text\(\s*',
    r'\.notification\(\s*',
    # `ui::ContextMenu` never translates: the builder hands the label straight
    # to `Label::new`, so every `.action("Cut", ..)` is a gap. The label is the
    # first argument there, unlike `Button::new(id, label)`.
    r'\.entry\(\s*',
    r'\.action\(\s*',
    r'\.submenu\(\s*',
    r'\.toggleable_entry\(\s*',
    r'\.more_info_message\(\s*',
    r'\.with_title\(\s*',
    r'\.with_detail\(\s*',
    # Tooltip::for_action* stores the title as `Title::Str` and looks the
    # keystroke up from the action object, so the title is pure display.
    r'Tooltip::for_action\(\s*',
    r'Tooltip::for_action_in\(\s*',
    r'Tooltip::for_action_title\(\s*',
    r'Tooltip::for_action_title_in\(\s*',
    r'Tooltip::with_meta_in\(\s*',
    r'Toast::new\(\s*[^,()]*,\s*',
    # The message is the second `prompt` argument, after `PromptLevel::*`.
    r'\.prompt\(\s*[^,]*,\s*',
    r'\.prompt_err\(\s*',
    r'\.detach_and_prompt_err\(\s*',
)
PREFIX = re.compile(r'(?:' + '|'.join(DISPLAY_CALLS) + r')$', re.DOTALL)

NOT_TEXT = (
    re.compile(r'^[a-z0-9_.\-/]+$'),
    re.compile(r'^\{'),
    re.compile(r'^(https?|zed|mailto)://'),
    re.compile(r'^[\s,|:;/\\-]*$'),
)

# Single-word candidates ("Cancel", "Evaluate", but also "Authorization" and
# every icon name) are reported apart from `unwrapped`; see the module docstring.
SINGLE_WORD = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def looks_like_text(s: str, allow_single_word: bool = False) -> bool:
    if len(s) < 2 or len(s) > 400 or '\n' in s:
        return False
    if any(p.match(s) for p in NOT_TEXT):
        return False
    if not allow_single_word and SINGLE_WORD.match(s):
        return False
    return True


def strip_comments(text: str) -> str:
    """Blank out comments, keeping offsets intact.

    String bodies are walked over without being touched, so a `"` inside a
    comment or an escaped quote inside a literal cannot desynchronise the scan.
    Literals survive because scan() reads them out of the result.
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


def blank_gallery_previews(text: str) -> str:
    """Blank out `fn preview` bodies, keeping offsets intact.

    `impl Component for X` lives next to the widget it documents, but its
    `preview` returns storybook data - demo labels and sample copy that only
    render in the developer UI gallery. Counting them as translatable buries
    the real gaps (measured: crates/ui 164 -> 2, notifications 8 -> 0).
    """
    out = list(text)
    n = len(text)

    def skip(open: str, close: str, i: int) -> int:
        """Return the index of the delimiter that closes the one at `i`."""
        depth = 0
        while i < n:
            if text[i] == open:
                depth += 1
            elif text[i] == close:
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return n

    for m in re.finditer(r'\bfn\s+preview\w*\s*\(', text):
        end_sig = skip('(', ')', text.index('(', m.start()))
        body = text.find('{', end_sig)
        if body == -1:
            continue  # trait method declaration, no body
        for k in range(body, min(skip('{', '}', body) + 1, n)):
            if text[k] != '\n':
                out[k] = ' '
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
    """Return (translate_calls, candidates, bare, ready_but_unwrapped)."""
    raw = path.read_text(encoding='utf-8', errors='ignore')
    text = strip_comments(raw)
    # Everything from the first inline test module on is test code.
    m = TEST_MODULE.search(text)
    prod = blank_gallery_previews(text[:m.start()] if m else text)
    calls = len(TRANSLATE.findall(prod))

    cands, bare, ready = [], [], []
    for m in STR.finditer(prod):
        s = m.group(1)
        if not looks_like_text(s, allow_single_word=True):
            continue
        # Anchored at the end of the window, so a literal already inside
        # t("...") is not a candidate: `t(` is not a display shape.
        if not PREFIX.search(prod[max(0, m.start() - 140):m.start()]):
            continue
        line = prod.count('\n', 0, m.start()) + 1
        if s in DICT:
            ready.append((line, s))
        elif SINGLE_WORD.match(s):
            bare.append((line, s))
        else:
            cands.append((line, s))

    seen = {*cands, *bare, *ready}
    for m in ANSWER_ARRAY.finditer(prod):
        line = prod.count("\n", 0, m.start()) + 1
        for lit in STR.finditer(m.group(0)):
            s = lit.group(1)
            if not looks_like_text(s, allow_single_word=True):
                continue
            hit = (line, s)
            if hit in seen:
                continue
            seen.add(hit)
            if s in DICT:
                ready.append(hit)
            elif SINGLE_WORD.match(s):
                bare.append(hit)
            else:
                cands.append(hit)
    return calls, cands, bare, ready


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
        calls, cands, bare, ready = scan(path)
        c = crates.setdefault(
            crate, {'calls': 0, 'cands': 0, 'bare': 0, 'ready': 0, 'files': []}
        )
        c['calls'] += calls
        c['bare'] += len(bare)
        c['ready'] += len(ready)
        if cands or bare or ready:
            c['cands'] += len(cands)
            c['files'].append((rel, cands, bare, ready))

    if verbose:
        for crate in sorted(crates):
            c = crates[crate]
            print(
                f'=== {crate}: {c["calls"]} translate calls, '
                f'{c["cands"]} unwrapped candidates, {c["bare"]} single-word, '
                f'{c["ready"]} already in dictionary'
            )
            for rel, cands, bare, ready in sorted(c['files'], key=lambda x: -len(x[1])):
                if cands:
                    print(f'  -- {rel}  ({len(cands)})')
                    for line, s in cands:
                        print(f'     {line:6d}  {s[:100]}')
                if ready:
                    print(f'  -- {rel}  ({len(ready)} in dictionary, just needs wrapping)')
                    for line, s in ready:
                        print(f'     {line:6d}  {s[:100]}')
                if bare:
                    print(f'  -- {rel}  ({len(bare)} single-word, judge each)')
                    for line, s in bare:
                        print(f'     {line:6d}  {s[:100]}')
        return

    rows = sorted(crates.items(), key=lambda kv: -kv[1]['cands'])
    print(f'{"crate":28} {"t()":>6} {"unwrapped":>10} {"bare":>6} {"ready":>6}')
    for crate, c in rows:
        if c['cands'] or c['calls'] or c['bare'] or c['ready']:
            print(
                f'{crate:28} {c["calls"]:6d} {c["cands"]:10d} {c["bare"]:6d} {c["ready"]:6d}'
            )
    total_calls = sum(c['calls'] for c in crates.values())
    total_cands = sum(c['cands'] for c in crates.values())
    total_bare = sum(c['bare'] for c in crates.values())
    total_ready = sum(c['ready'] for c in crates.values())
    print(f'{"TOTAL":28} {total_calls:6d} {total_cands:10d} {total_bare:6d} {total_ready:6d}')
    print(f'crates scanned: {len(crates)}')


if __name__ == '__main__':
    main()
