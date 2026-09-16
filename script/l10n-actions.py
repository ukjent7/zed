"""Inventory the action registry: how many actions exist, in which modules,
and how many have a Chinese display name.

`actions!(module, [Ident, ...])` blocks are what `actions-zh-CN.json` keys on,
via `module::Ident` - the id `derive_action.rs` builds from the macro-injected
`namespace` and the struct name. Two shapes must be read carefully:

- a doc comment's first word is capitalised, so a regex sweep over the block
  yields "Opens" / "Toggles" as if they were actions; the block is read line
  by line instead.
- `#[action(name = "FoldAtLevel_1")]` replaces the last segment of the id, so
  the dictionary key is `editor::FoldAtLevel_1`, not `editor::FoldAtLevel1`.

Run: python script/l10n-actions.py
"""
import collections
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
DICT = json.loads((ROOT / 'assets/locales/actions-zh-CN.json').read_text(encoding='utf-8'))

DECL = re.compile(r'(?<![\w:])(?:gpui::)?actions!\s*\(\s*([\w:]+)\s*,\s*\[')


def blocks(text):
    """Yield (module, body) for every actions! block, brackets balanced.

    Nested `actions!` calls (zed_actions/src/lib.rs groups them inside one
    outer list) are found by the same sweep, so their actions land in their
    own namespace rather than the outer one.
    """
    for m in DECL.finditer(text):
        i, depth = m.end() - 1, 0
        while i < len(text):
            if text[i] == '[':
                depth += 1
            elif text[i] == ']':
                depth -= 1
                if depth == 0:
                    yield m.group(1), text[m.end():i]
                    break
            i += 1


def parse_items(body):
    """Action identifiers in an actions! list, as the runtime names them."""
    out = []
    pending = None
    for line in body.split('\n'):
        s = line.strip()
        if not s or s.startswith('//'):
            continue
        attr = re.match(r'#\[action\(([^)]*)\)\]', s)
        if attr:
            nm = re.search(r'name\s*=\s*"([^"]+)"', attr.group(1))
            if nm:
                pending = nm.group(1)
            rest = s[attr.end():].strip()
            if rest:
                m = re.match(r'([A-Z]\w*)', rest)
                if m:
                    out.append(pending or m.group(1))
                    pending = None
            continue
        if s.startswith('#['):
            continue
        m = re.match(r'([A-Z]\w*)\s*,?\s*$', s) or re.match(r'([A-Z]\w*)\s*,', s)
        if m:
            out.append(pending or m.group(1))
            pending = None
    return out


def main() -> None:
    per_module = collections.Counter()
    missing_mod = collections.Counter()
    seen = set()
    missing = set()
    for path in sorted((ROOT / 'crates').glob('*/src/**/*.rs')):
        text = path.read_text(encoding='utf-8', errors='ignore')
        for module, body in blocks(text):
            for ident in parse_items(body):
                key = f'{module}::{ident}'
                if key in seen:
                    continue
                seen.add(key)
                per_module[module] += 1
                if key not in DICT:
                    missing.add(key)
                    missing_mod[module] += 1

    total = len(seen)
    print(f'actions declared: {total}')
    print(f'dict entries:     {len(DICT)}')
    print(f'untranslated:     {len(missing)}')
    print(f'coverage:         {(total - len(missing)) * 100 // max(1, total)}%')
    print(f'\nmodules: {len(per_module)}, untranslated modules: {len(missing_mod)}')
    print('\nmodules missing translations:')
    for k, v in missing_mod.most_common(40):
        print(f'  {v:4d} / {per_module[k]:4d}  {k}')


if __name__ == '__main__':
    main()
