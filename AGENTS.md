Rust/GPUI 代码规范见 `.rules`（上游的 AGENTS.md 是指向它的符号链接，本 fork 改用普通文件承载下面的规则，故需手动引用）。
合并上游后若 `.rules` 有更新，需手动合入本文件；本文件在 git 中必须保持普通文件模式（100644），若变成 symlink 模式（120000）会导致 Linux 下检出为断链。
本 fork 豁免上游 `.rules` 中的 README 横幅 HARD RULE：改源码时不在 `README.md` 加横幅，质量门槛由 `fork_ci` / `fork_check` 等承担（上游该规则为多贡献者 PR 送审模式设计，与本 fork 直接 push 到 main 的流程不契合）。

# 严禁未经用户允许私自安装任何依赖、程序或者环境
本机有 Rust 环境，但请勿尝试编译（项目太大、依赖太多）
阶段性修改直接push到仓库，CI交给github action。用户要求发release就**不用等CI通过直接发**。

本 fork 的 CI 全部自建：上游 workflow 带 `repository_owner == 'zed-industries'` 门禁，且指定 fork 上不存在的 namespace/自托管 runner，所以在 fork 上必然跳过（不要试图改上游那 48 个文件，会和上游合并冲突；跑不了的用 `fork_disable_upstream` 禁用）。
- `fork_ci.yml`：秒级冒烟——fmt、l10n 边界、locale 单测、词典审计
- `fork_check.yml`：对改动过的 crate 跑 `cargo check`，**唯一能发现编译错误的防线**
- `fork_release.yml`：推 `v*` tag 即三平台打包并发布 Release（不签名、dev 渠道、不自动更新）
- `fork_disable_upstream.yml`：禁用上游跑不了的工作流；合并上游后需重跑一次

# 发布与更新
发版：递增 `crates/zed/Cargo.toml` 的版本号 → 提交 → 打 `v<版本>` tag（如 `v0.201.0`）。`fork_release` 会在发布前校验 tag 与 crate 版本一致，不一致直接失败。
应用内更新：`fork_release` 构建时注入 `ZED_FORK_RELEASE_REPO=<owner/repo>`，`crates/auto_update` 据此把菜单里的「检查更新」指向**本仓库**的 Release，下载与安装复用上游原有流程（三个平台都从"运行中的 app 路径"推导目标名，所以 dev 渠道的产物天然兼容）。上游流程相关事实：更新源是 zed.dev，`ReleaseChannel::poll_for_updates()` 对 dev 返回 false，所以官方更新通道永远不会被触发，也不会被官方版覆盖汉化。
只有手动检查，没有后台轮询：不想让一个未签名的自建包在后台静默安装。要开自动轮询的话，在 `auto_update::init` 的 `poll_for_updates` 条件里加上 `|| fork_release_repo().is_some()` 即可。

# 由于该项目为 fork 项目，为防止上游合并冲突，所有对项目的改动都必须遵循以下原则：
1. 最小化改动——仅修改必要的部分，避免大面积重构。
2. 与上游冲突可能性最少
3. 长期可维护——确保改动易于理解、便于后续升级和维护。
4. 打造最佳、最优雅的实现——在不违反上述原则的前提下，追求代码质量和设计美感。

# review规则
项目所有代码、注释都是AI编写，人工只做了极少干预，可能存在我不想有这么个设计，但是代码就这么写的情况，或者明明没有这个案例和坑，注释却幻觉出一个实际踩坑场景。所有不要有"存在即合理、能不改就不改"的思想，导致对问题视而不见，不能轻信注释和代码
但也不能挑刺，提出的所有改进、修复点都需要有充足的理由和逻辑，不确定的就来一次行为模拟、交叉验证、脚本测试来敲定方向

# 汉化规则
只能汉化前端GUI，不能影响模型行为，不能影响模型接收到的信息