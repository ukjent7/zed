# 汉化覆盖普查与待办清单

本文件记录 Simplified Chinese 本地化（`crates/locale`）的覆盖现状、待办与边界。
随每次汉化推进更新。

## 口径

统计只认一种形态：**英文字面量直接作为显示函数实参**（`Label::new("…")`、
`Button::new(id, "…")`、`ContextMenuEntry::new("…")`、`.aria_label("…")`、
`.placeholder("…")`、`Button::new_secondary`、`ListBulletItem::new`、
`Tooltip::simple`、`.primary_message`、`.confirm_label` 等约 55 种调用形状）。

`script/l10n-audit.py` 输出四列：

| 列 | 含义 |
| --- | --- |
| `t()` | 生产代码中的翻译调用数 |
| `unwrapped` | 显示位置上的多词字面量，未包裹 |
| `bare` | 同一位置上的**单词**字面量（`Cancel`、`Evaluate`…），需人工判断：此类也含图标名、HTTP 头、品牌名 |
| `ready` | 词典里**已有译文**但未包裹的位置 —— 只需要包裹，不需要新增词条 |

下列形态仍**不在统计内**，真实缺口大于下表数字：

- 经变量中转后传给显示函数（部分可被 `ready`/`bare` 覆盖，但 `let x = "…"; Label::new(x)` 仍看不到）
- `format!` 拼接出的文案（`agent_ui` 326 处、`editor` 196 处，多数是日志/路径）
- trait 方法返回的文案（全仓 86 处 `tab_content_text` / `tab_content_label` / `breadcrumb`）
  —— 本文件推进中已顺手处理若干（`DebuggerPaneItem`、`DebugSession`、`Keyboard Context`、
  `Syntax Tree`、`Highlights`），其余未普查
- `#[cfg(any(test, feature = "test-support"))]` 下**非** `Component::preview` 的分支
  （`collab_panel.rs:4270` 的 `entries_as_strings` 即是一例，测试断言依赖它，不能译）

复现：`python script/l10n-audit.py`（按 crate 汇总）、`-v <crate>`（明细）。
`crates/<x>` 全量字面量（含 match 臂、元组、helper 实参）另见一次性脚本思路：
按“含空格或首字母大写的单词”过滤 + 排除 `log!`/`telemetry!`/`id`/URL。

命令名覆盖率：`python script/l10n-actions.py`。

## 现状

| 指标 | 值 |
| --- | --- |
| 界面词典 `zh-CN.json` | 2,269 条 |
| 命令词典 `actions-zh-CN.json` | 1,189 / 1,207（98%，剩余 18 条为测试夹具） |
| 代码内翻译调用 | 1,252 处 |
| 待译前端文案 | 467 多词 + 100 单词 |
| 已译未接（`ready`） | 145 处（其中 `agent_ui` 28、`language_models` 11 属结构性不可译，见下） |

CI 门禁：`./script/extract-l10n --strict`（包裹的键必须有译文）、
`./script/check-l10n-boundary`（模型侧路径禁止出现 `locale::`）、`cargo test -p locale`
（占位符一致性）。审计脚本只是分诊工具，不做门禁。

## 已完整覆盖（`-v` 三列均为 0，或剩余项已判定不改）

`settings_ui`、`recent_projects`、`project_panel`、
`title_bar`、`keymap_editor`、`extensions_ui`、`search`、`onboarding`、
`terminal_view`、`outline_panel`、`auto_update`、`command_palette`、
`collab_panel`(ui/components)、`sidebar`、`editor`、`collab_ui`、
`repl`(仅剩 3 处 HTTP 头)、`language_tools`、`workspace`(除 theme_preview)、
`zed`(除 Sentry/开发者视图/测试夹具)、`debugger_ui`(主体，子视图待办)、
`ui`(除 2 处，画廊 preview 已自动排除)。

## P0 · 剩余高频界面

| 区域 | 量 | 备注 |
| --- | --- | --- |
| `ai_onboarding` | 39(+2 bare,+4 ready) | AI 上手引导弹窗。**不在 blocklist**，但同文件含模型元数据，需逐条判断 |
| `debugger_ui` 子视图 | 12(+2 bare,+12 ready) | `breakpoint_list` ~20、`new_process_modal` ~14、`variable_list` ~11、`memory_view` 5、`console` 4、`stack_frame_list` 3、`attach_modal` 1 |
| `git_ui` / `git_ui_core` | 12 + 9(+5 ready) | 新形状带出的少量：`No Changes to Commit`、`Conflict marked as resolved`、`Switch Active Repository` 等 |
| `workspace` | 4 ready | `invalid_item_view.rs` 的 `Open in Default App`、`pane.rs` 2 处、`workspace.rs` 的 `Editor` |
| `tabular_data_preview` | 6 | CSV/JSON 预览表头 |
| 零星 | 约 30 | `languages`、`markdown`、`theme_selector`、`diagnostics`、`picker`、`open_path_prompt`、`call_hierarchy`、`toolchain_selector`、`tasks_ui`、`auto_update_ui` |

## 明确不改

| 类别 | 量 | 理由 |
| --- | --- | --- |
| 模型侧路径 | 66+71+32+16+… | `agent_ui`、`language_models`、`edit_prediction_ui`、`copilot_ui`、`context_server`、`copilot_chat`、`edit_prediction*`、`agent`、`prompt_store`、`rpc`、`proto` 等，见 `script/check-l10n-boundary` 的 blocklist。这些位置的 `ready` 计数是**结构性缺口**，不是待办 |
| `crates/ui` 组件画廊 | 2 | `Component::preview` 内的 story 数据，现由审计脚本自动排除（`blank_gallery_previews`，164 → 2） |
| `workspace/theme_preview.rs` | 20 | **本轮判定**：字体/主题样张，Lorem ipsum 与 `Headline Sizes` 用于展示拉丁字形排版，翻译后反而失真 |
| HTTP 请求头 | 32 | `Authorization`、`Content-Type` 等，见 blocklist 说明 |
| Sentry 遥测键名 | 14 | `crates/zed/src/reliability.rs` |
| 开发者工具 | ~45 | `inspector_ui`、`dev_container`、`edit_prediction_cli`、`component_preview`、`miniprofiler_ui`、`telemetry_log.rs`、`watcher_debug.rs` |
| 上游死代码 | 2 | `collab_panel.rs` 的 `channel_tooltip_text`（赋值后从未读取，`Copy Public/Private Channel Link` 永不渲染） |
| 参与序列化的字符串 | — | 见下节“翻译前必须确认的陷阱” |
| 测试夹具 / 命令示例 / 品牌名 / 日志 | — | 含 `test_only` 的 18 条命令名 |

## 翻译前必须确认的陷阱

1. **字符串是否参与序列化或反查**。`DebuggerPaneItem::to_shared_string` 同时是
   调试器面板布局的序列化值（`SharedString` ↔ enum 双向转换），在函数内部翻译会导致
   无法恢复布局；只能在两个渲染点（`tab_content`、`running.rs:297`）翻译。
2. **字符串是否被当作匹配键**。`call_stats_modal.rs` 的 `metric_rating(label,..)`
   `match label { "Latency" => … }`，翻译传参会让所有评级静默落到默认分支；
   正确做法是在 `render_metric_row` 内部翻译 `title`/`description`（一处覆盖 8 条）。
   同理 `language_for_name("Markdown")` 是语言注册表查询键。
3. **参数类型**。`impl Into<SharedString>`（Label/Button/Tooltip/entry/checkbox）直接
   `locale::t(..)`；`&str` 参数（`set_placeholder_text`、`detach_and_prompt_err`、
   `window/cx.prompt`）要 `.as_str()`；`Toast::new` 是 `Into<Cow<'static, str>>`，
   要 `.to_string()`。
4. **`window.prompt` 的按钮角色**。`impl From<&str> for PromptButton` 用
   `to_lowercase()` 匹配 `"ok"`/`"cancel"` 决定按钮角色，且 `Cancel` 分支会**硬编码**
   英文 `"Cancel"` 标签；译文会变成 `Other` 角色。返回值是下标，逻辑不受影响。
5. **静态量无法运行时翻译**。`static EMPTY_LENS_FALLBACK_TITLE`（`0 references`）、
   `static SELECT_DEBUGGER_LABEL`（`Select Debugger`）需要在调用点改造，
   且编辑器 code lens 回退标题与 LSP 给的 `2 references` 同屏，译文无法统一 → 暂未做。
6. **`{}` 位置占位符不能作词典键**。`format!("{:}", x)`、`format!("{}…{}", a, b)`
   必须先改成命名槽（`{count}`、`{path}`…）再走 `t_format`。

## 收口点（改一处覆盖一片）

- `locale::localized_action_name()` —— 命令面板命令名
- `settings_ui::render_settings_item_layout()` —— 全部设置项标题与描述
- `settings_ui/components/input_field.rs` —— 全部设置输入框 placeholder
- `Checkbox` 能力标签渲染点 —— 全部能力开关
- `zed::localize_menus()` —— 应用菜单
- `locale::t_static()` —— 静态键零分配路径
- `ui::ProjectEmptyState::render` —— **本轮新增**：四个面板（Threads/Project/Git/Agent）
  空状态的说明句、面板名与两个按钮。`agent_ui` 只传英文面板名，因此不需要在
  模型侧 crate 里调用 `locale::`
- `workspace::dock` 的 `icon_tooltip` 消费点 —— 所有面板图标 tooltip
- `call_stats_modal::render_metric_row` / `debugger_ui::DebuggerPaneItem::tab_tooltip`
  —— 同类“渲染点收口”写法

## 待决策

1. **Vim 命令名 217 条**：已随命令名批量翻译完成，显示为「删除到行尾 (DeleteToEndOfLine)」，
   搜索两种语言都能命中。若 Vim 用户反馈噪音大，可在 `localized_action_name` 里
   按命名空间前缀（`vim::`）退回纯英文——一处改动。
2. **设置搜索索引**：中文界面下搜「字体」匹配不到 `Font`。需把译文并入
   `documents`/`fuzzy_match_candidates`，属检索行为改动，尚未做。
3. **`ai_onboarding` 是否整体汉化**：文案含营销语（`2,000 accepted edit predictions`）
   与模型/供应商专有名词，需逐条判断，见 P0。
4. **协作/调试是否常用**：本轮已把 `collab_ui` 全量汉化、`debugger_ui` 汉化到面板主体；
   若确认不使用，后续 `debugger_ui` 子视图可降级。
