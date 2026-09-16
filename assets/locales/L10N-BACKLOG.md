# 汉化覆盖普查与待办清单

本文件记录 Simplified Chinese 本地化（`crates/locale`）的覆盖现状、待办与边界。
随每次汉化推进更新。

## 口径

统计只认一种形态：**英文字面量直接作为显示函数实参**（`Label::new("…")`、
`Button::new(id, "…")`、`ContextMenuEntry::new("…")`、`.aria_label("…")`、
`.placeholder("…")` 等约 35 种调用形状）。

因此下列形态**不在统计内**，真实缺口大于下表数字：

- 经变量中转后传给显示函数
- `format!` 拼接出的文案（`agent_ui` 326 处、`editor` 196 处 `format!`，多数是日志/路径）
- trait 方法返回的文案（全仓 86 处 `tab_content_text` / `tab_content_label` / `breadcrumb`）

复现：`python script/l10n-audit.py`（按 crate 汇总）、`-v <crate>`（明细）、
`python script/l10n-actions.py`（命令名覆盖率）。

## 现状

| 指标 | 值 |
| --- | --- |
| 界面词典 `zh-CN.json` | 1,967 条 |
| 命令词典 `actions-zh-CN.json` | 304 条 |
| 代码内翻译调用 | 916 处，分布在 18 个 crate |
| 命令名覆盖 | 315 / 1,321（23%） |
| 待译前端文案 | 约 480 条 |

## 已完整覆盖

`settings_ui`（231 处调用）、`git_ui`（186）、`recent_projects`（98）、
`project_panel`（62）、`title_bar`（60）、`keymap_editor`（51）、`extensions_ui`（44）、
`search`（36）、`onboarding`（36）、`terminal_view`（28）、`outline_panel`（15）、
`auto_update`（16）、`command_palette`（6）、`ui/components/collab`（8）。

验证方式：`python script/l10n-audit.py` 中这些 crate 的候选数为 0。

## P0 · 高频界面

| 区域 | 量 | 备注 |
| --- | --- | --- |
| 命令面板命令名 | 1,006 | **零代码改动**，只补 `actions-zh-CN.json` |
| `agent_ui` | 69 | Agent 面板，本 fork 核心功能区 |
| `language_models` | 62 | provider 配置界面（Bedrock/Ollama/llama.cpp/LM Studio） |
| `edit_prediction_ui` | 32 | 编辑预测按钮、评分弹窗 |
| `zed` | 22 | REPL 菜单、快速操作栏、安装引导 |
| `workspace` | 14 | 安全弹窗、标签页右键菜单、状态栏 |
| `editor` | 13 | 审查评论、code lens、右键提示 |
| `sidebar` | 13 | 线程侧边栏 |

### 命令名（最大单点）

命令名经 `locale::localized_action_name()` 统一渲染，带译文时显示
`中文 (English)`，因此**搜索在两种语言下都能用**。只需往
`assets/locales/actions-zh-CN.json` 加条目，不动任何 Rust 代码。

未译大户：`editor` 277、`vim` 217、`git` 77、`debugger` 36、`dev` 27、
`git_panel` 23、`markdown` 19、`notebook` 16、`collab_panel` 13、`zed` 13、
`settings_editor` 13。

`test_only` 模块的 23 条是测试夹具，跳过。

## P1 · 中频界面

| 区域 | 量 | 区域 | 量 |
| --- | --- | --- | --- |
| `collab_ui` | 26 | `git_ui_core` | 9 |
| `debugger_ui` | 25 | `git_ui` | 8 |
| `language_tools` | 21 | `tabular_data_preview` | 6 |
| `ai_onboarding` | 19 | `keymap_editor` | 5 |
| `repl` | 19 | `title_bar` | 5 |
| `copilot_ui` | 16 | `languages` / `theme_selector` / `markdown` | 各 4 |
| `workspace/theme_preview.rs` | 18 | 其余零星（`acp_tools`、`diagnostics` 等） | 约 25 |

## 明确不改

| 类别 | 量 | 理由 |
| --- | --- | --- |
| `crates/ui` 组件画廊与样式文档 | 124 | `#[cfg(any(test, feature = "test-support"))]` 下的 Story 数据，只在组件预览页出现 |
| HTTP 请求头 | 32 | `Content-Type`、`X-Api-Key`、`Anthropic-Version`；改协议字段会直接破坏请求（`anthropic` 13、`copilot_chat` 11、`git_hosting_providers` 8） |
| Sentry 遥测键名 | 14 | `crates/zed/src/reliability.rs`，上报数据的键，非 UI |
| 开发者工具 | 32 | `inspector_ui`（GPUI Inspector）、`dev_container`、`edit_prediction_cli`、`component_preview`、`miniprofiler_ui` |
| 模型可见内容 | — | Bedrock 的 tool description、`llama serve` 等命令示例；翻译会改变模型行为 |
| 测试代码 | — | 含 `crates/agent` 中 310 处形似翻译调用、实为测试 helper `t()` |
| 日志、panic、路径、品牌名 | — | 非 UI，或不应翻译（OpenAI / Anthropic / Ollama 等） |

## 待决策

1. **Vim 命令名 217 条**：汉化后命令面板显示「删除到行尾 (DeleteToEndOfLine)」。
   Vim 用户可能更认英文。
2. **`language_models` 约 40 条**：同文件内混有必须译的界面文案（`Access Key ID`、
   `Download Ollama`）与不应译的模型元数据，需逐条判断。
3. **`workspace/theme_preview.rs` 18 条**：`Headline Sizes` 是真标签，但大量
   Lorem ipsum 占位文本（主题预览用）翻了反而失真。
4. **`collab_ui` 52 条（含 `debugger_ui`）**：取决于是否使用协作与调试功能。
5. **设置搜索索引**：中文界面下搜「字体」匹配不到 `Font`。需把译文并入
   `documents`/`fuzzy_match_candidates`，属检索行为改动。

## 已建的收口点

改动集中在这几处即可覆盖大面积 UI，避免逐处包裹：

- `locale::localized_action_name()` —— 命令面板命令名
- `settings_ui::render_settings_item_layout()` —— 全部设置项标题与描述
- `settings_ui/components/input_field.rs` —— 全部设置输入框 placeholder
- `Checkbox` 能力标签渲染点 —— 全部能力开关
- `zed::localize_menus()` —— 应用菜单
- `locale::t_static()` —— 静态键零分配路径（设置页每帧渲染数百条长描述）
