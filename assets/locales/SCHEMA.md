# 汉化词典格式（SCHEMA）

`zh-CN.json`:扁平的英文原文到简体中文的映射。调用点以英文原文为键
（source-as-key），运行时查表；缺词自动回退英文。

```json
{
  "Open Settings": "打开设置",
  "{count} files in {folder}": "{folder}中有 {count} 个文件"
}
```

`actions-zh-CN.json`:命令面板动作 ID 到中文显示名的映射，由
`script/generate-action-metadata` 产出的 `actions.json` 生成骨架后人工翻译：

```json
{
  "editor::GoToDefinition": "转到定义"
}
```

## 规则

1. 键是代码里的英文原文，一字不差（含大小写与标点）。
2. 原文中的 `{name}` 占位符必须在译文中原样保留且不增删；
   `crates/locale` 单测与 `script/check-l10n-boundary` 会校验。
3. 快捷键、代码片段、专有名词（Vim、Git、Agent、Zed）不翻译。
4. 只收 GUI 文案。会进入模型的字符串（prompts、agent、language_model、
   edit_prediction、tool 描述等）一律不收，见 `script/check-l10n-boundary`
   的 blocklist。
5. 上游改了英文原文导致旧键失效时，运行时回退英文，并在下次同步时
   用 `script/extract-l10n` 报出缺词/废弃键。废弃键不删除，只停止使用。
