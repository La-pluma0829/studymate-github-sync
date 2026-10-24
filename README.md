# studymate-github-sync

配合 StudyMate，把正在学、已学概览和下一步同步到 GitHub 私有仓库，让组员打开首页就能看到彼此的进度。

这是作者全力依靠codex plus作出的skill 环境是MBA m5 16g macOSTahoe 26.4 如有报错希望大家在拜托自己的ai老师解决的同时也能与作者通信便于维护项目/笑

以下为codex老师自己撰写的readme请大家欣赏（）：

## 它做什么

这是 [Study-Mate](https://github.com/Miaotofu01/Study-Mate) 的配套技能，独立开发，未修改或打包上游插件。读取正式学习进度与练习证据，为本人生成“当前正在学 / 已学概览 / 下一步”，增量更新团队私有仓库 README。

只修改本人的行和阶段记录，保留队友内容及资料链接；没有新进度就不提交。学习计划不会当成已掌握，也不上传完整聊天、答案、误解库或账号凭据。

## 安装（Codex / DSH，Windows / macOS）

需要 Python 3.9+。下载并解压仓库，在解压目录运行安装器；DSH 与 Codex 使用同一套技能文件。

Windows / DSH（PowerShell；把路径换成实际学习工作区）：

```powershell
py -3 -X utf8 scripts/install.py --host dsh --workspace 'D:\学习\电赛' --dry-run
py -3 -X utf8 scripts/install.py --host dsh --workspace 'D:\学习\电赛'
```

macOS / DSH：

```sh
python3 -X utf8 scripts/install.py --host dsh --workspace '/实际学习工作区'
```

Codex：Windows 使用 `py -3 -X utf8 scripts/install.py --host codex`；macOS 使用 `python3 -X utf8 scripts/install.py --host codex`。

DSH 安装器定位项目根下 `.dsh/skills/studymate-github-sync/SKILL.md`，不修改 Profile 配置；自定义扫描目录用 `--skills-dir`。Codex 默认个人技能目录取 `$CODEX_HOME/skills` 或 `~/.codex/skills`。安装后在对应工作区打开会话加载技能。已存在时默认拒绝覆盖，审阅后加 `--update`，会备份旧版本。

技能需要已安装的 StudyMate 和可读取的学习档案。Windows 命令同步需另装 [GitHub CLI](https://cli.github.com/)，由用户完成 `gh auth login`，不向 AI 粘贴令牌；可使用当前宿主可用的 GitHub 连接器或已授权浏览器。macOS 用户指定 Safari 时仍按 Safari 操作。

详细路径、PowerShell 命令、登录、同步与排错见 [DSH / Windows 适配说明](references/dsh-windows.md)。技能本身不要求额外付费 API；宿主及模型服务费用按相应平台计算。

## 使用

向助手发送：

> 加载 studymate-github-sync，配合 StudyMate 在学习结束后把我的进度同步到团队私有仓库。先确认我的 GitHub 用户名和目标仓库。

Codex 可显式使用 `$studymate-github-sync`；DSH 让助手按已发现的技能名加载，不依赖 Codex 专用工具。

首次确认仓库、分支、README 路径、个人用户名和允许发布的内容；其他组员使用时配置自己的账号，不继承作者或队友授权。

技能随会话执行，不是后台常驻服务。希望每次 StudyMate 收尾都同步时，在实际学习工作区的项目指令里加入上述入口，并保留既有指令；自动发现不保证每次都触发。定时同步需要另行配置任务。

## README 约定

首页使用五列表格：`GitHub 用户名 | 分工 | 当前正在学 | 已学概览 | 下一步`。个人记录的小节标题为 `### 用户名 · 阶段记录`。首次没有对应行时，由助手核对布局后新增，不猜测成员身份。

## 本地差异助手

`scripts/patch_readme.py` 只准备本地差异，不联网、不提交。使用 Python 3.9+，无需第三方包。输入 JSON 需要 `username`、`role`、`current`、`learned`、`next` 字符串；可选 `detail` 为本人阶段小节的完整 Markdown。

```sh
python3 scripts/patch_readme.py --readme latest-README.md --summary summary.json --output proposed-README.md
```

输出必须另存为新文件。查不到本人、出现重复行或表格列数不符时会报错；脚本不替代事实判断、授权与远端冲突检查。真正提交前必须读取远端最新版本，并核对差异。

## GitHub 命令同步

`scripts/sync_github.py` 基于已认证的 GitHub CLI，默认只读预览；确认 diff 后，用返回的 sha 加 `--apply --expected-sha` 提交。脚本检查当前账号与学习者一致、目标为私有且可写，发生版本冲突就停止；成功后重新读取 README 核对。无变化不提交，不使用强制推送。

完整命令与摘要格式见[适配说明](references/dsh-windows.md#windows-同步到-github)。两个脚本均不会自行评价学习成果，也不会监听 StudyMate。

## 验证与限制

```sh
python3 -X utf8 -m unittest discover -s tests -v
```

Windows 将 `python3` 换为 `py -3`。15 项本地测试覆盖本人增量更新、队友/链接保留、重复执行、缺失/重复成员、中文与空格路径、UTF-8 BOM、CRLF、安装根定位/备份、模拟 GitHub 的预览、无变化、账号/权限/私有状态、SHA 冲突和提交后核验。

2026-10-24 在 macOS 运行通过；DSH 扫描规则已对照官方文档。尚未在 Windows 实机或 DSH 会话内完成端到端验证，也未用真实 GitHub API 提交学习记录。此处的兼容实现与模拟测试不等于实机验证。身份验证或权限阻塞时保留待同步摘要，提交结果不明先查历史。

## 项目文件

- `SKILL.md`：工作流程与发布边界。
- `agents/openai.yaml`：Codex 技能入口信息。
- `scripts/patch_readme.py`：本地增量更新助手。
- `scripts/install.py`：DSH/Codex 跨平台安装器。
- `scripts/sync_github.py`：预览、提交及核验 GitHub 进度。
- `references/dsh-windows.md`：DSH/Windows 说明与官方依据。
- `tests/test_sync.py`：本地回归测试。

本仓库仅分发配套技能及自写工具，不包含 StudyMate 源码、任何人的学习档案、私人仓库配置或凭据。
