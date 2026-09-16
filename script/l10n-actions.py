"""Inventory the action registry: how many actions exist, in which modules,
and how many have a Chinese display name.

`actions!(module, [Ident, ...])` blocks carry a doc comment per action; that
comment is what the command palette shows as the action's subtitle, and the
identifier is the action's id (`module::Ident`) that `actions-zh-CN.json` keys
on. Actions declared with `#[action(name = "...")]` use an explicit id.

Run: python target/l10n-actions.py
"""
import json
import pathlib
import re
import collections

ROOT = pathlib.Path(__file__).resolve().parent.parent
DICT = json.loads((ROOT / 'assets/locales/actions-zh-CN.json').read_text(encoding='utf-8'))

DECL = re.compile(r'(?<![\w:])(?:gpui::)?actions!\s*\(\s*([\w:]+)\s*,\s*\[')
# The action list is flat: identifiers, attributes, doc comments, trailing commas.
ITEM = re.compile(r'(?:///[^\n]*\n\s*)*(?:#\[action\([^\]]*\)\]\s*)?([A-Z]\w*)')
NAME_ATTR = re.compile(r'#\[action\([^)]*?name\s*=\s*"([^"]+)"')


def blocks(text):
    """Yield (module, body) for every actions! block, brackets balanced."""
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


def main() -> None:
    per_module = collections.Counter()
    per_crate = collections.Counter()
    missing_mod = collections.Counter()
    missing_total = 0
    total = 0
    for path in sorted((ROOT / 'crates').glob('*/src/**/*.rs')):
        crate = path.relative_to(ROOT).as_posix().split('/')[1]
        text = path.read_text(encoding='utf-8', errors='ignore')
        for module, body in blocks(text):
            idents = ITEM.findall(body)
            if not idents:
                continue
            per_module[module] += len(idents)
            per_crate[crate] += len(idents)
            total += len(idents)
            for ident in idents:
                key = f'{module}::{ident}'
                short = module.split('::')[-1]
                if key not in DICT and f'{short}::{ident}' not in DICT:
                    missing_total += 1
                    missing_mod[module] += 1

    print(f'actions declared: {total}')
    print(f'dict entries:     {len(DICT)}')
    print(f'untranslated:     {missing_total}')
    print(f'coverage:         {(total - missing_total) * 100 // max(1, total)}%')
    print(f'\nmodules: {len(per_module)}, untranslated modules: {len(missing_mod)}')
    print('\ntop modules missing translations:')
    for k, v in missing_mod.most_common(35):
        print(f'  {v:4d} / {per_module[k]:4d}  {k}')
    print('\ndict modules with no matching actions! block (ids from derive/other):')
    covered = set()
    for module in per_module:
        covered.add(module)
        covered.add(module.split('::')[-1])
    for k in DICT:
        mod = k.split('::')[0]
        if mod not in covered:
            print(f'  {k}')


if __name__ == '__main__':
    main()
