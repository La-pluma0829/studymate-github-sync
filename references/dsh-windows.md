# DSH 与 Windows 适配

核对日期：2026-10-24。依据 DSH 官方 [本地技能提供方说明](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md) 与 [技能系统](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.zh.md)。

## 安装到正确位置

同一份 SKILL.md 支持 Codex 与 DSH。DSH 按 `<扫描根>/<技能名>/SKILL.md` 发现，不能多套一层仓库目录。优先工作区内安装；DSH 的项目根是最近的 .git 祖先，没有 .git 时使用会话 cwd。安装器按此规则选 `.dsh/skills`，不修改 DSH 配置、不添加插件、不迁移 StudyMate 数据。

Windows（PowerShell，进入本仓库解压目录后）：

```powershell
py -3 --version
py -3 -X utf8 scripts/install.py --host dsh --workspace 'D:\学习\电赛' --dry-run
py -3 -X utf8 scripts/install.py --host dsh --workspace 'D:\学习\电赛'
```

macOS：

```sh
python3 -X utf8 scripts/install.py --host dsh --workspace '/实际学习工作区' --dry-run
python3 -X utf8 scripts/install.py --host dsh --workspace '/实际学习工作区'
```

工作区必须真实存在。若使用自定义 Profile，先确认 DSH 实际扫描的 skills 目录，再传 `--skills-dir '实际目录'`，不要假设 Desktop 的 Profile 一定使用 `~/.dsh/skills`。Codex 可用 `--host codex`。已安装时默认拒绝覆盖，审阅后加 `--update`，旧目录会备份，额外本地文件保留。

安装后在 DSH 选择对应工作区，发：“加载 studymate-github-sync，配合 StudyMate 在本次学习结束后同步我的进度。”若未发现，核对扫描根、SKILL.md 层级和当前会话 cwd。不要把 agents/openai.yaml 当作 DSH 必需配置。

## Windows 同步到 GitHub

安装 [Python](https://www.python.org/downloads/windows/) 和 [GitHub CLI](https://cli.github.com/)（依赖不随技能分发）。用户自行完成：

```powershell
gh auth login
gh auth status
```

使用已获私有库写权限的本人 GitHub 账号。不要向 AI 粘贴访问令牌；gh 使用自己的认证配置，不把密钥写进学习记录。

助手依据 StudyMate 正式进度生成仅含本人摘要的 UTF-8 JSON；PowerShell 5 的 UTF-8 BOM 同样可读。以下摘要仅为演示，不作为任何人的掌握证据：

```json
{"username":"YOUR_LOGIN","role":"硬件","current":"当前正在学的内容","learned":"有证据的已学概览","next":"接下来一个任务"}
```

预览（读取远端，不提交）：

```powershell
py -3 -X utf8 scripts/sync_github.py --repo 'OWNER/PRIVATE_REPO' --branch main --username 'YOUR_LOGIN' --summary 'D:\学习\本次摘要.json'
```

在已授权范围核对 diff 后，使用返回的 sha 提交：

```powershell
py -3 -X utf8 scripts/sync_github.py --repo 'OWNER/PRIVATE_REPO' --branch main --username 'YOUR_LOGIN' --summary 'D:\学习\本次摘要.json' --apply --expected-sha '预览返回的sha'
```

macOS 将 `py -3 -X utf8` 换为 `python3 -X utf8`。脚本不需要 Git，不强制推送；README 版本变动时重新预览后处理，不拿旧 sha 强行覆盖。无变化返回 unchanged；成功返回 synced 与提交号；失败退出非零，提交结果不明时先看历史。

## StudyMate 衔接

- 数据来自当前学习工作区 `.learning/subjects/<科目>/progress.yaml`、课程初始快照及已有评估，不从网页大纲推断已学。
- 同步入口在正式档案写入之后；配置“每次学习结束同步”只对已授权的当前工作区生效，不修改上游 StudyMate 或插件缓存。
- DSH 没有 Codex 的聊天检索工具时，使用实际档案；没有档案则请用户提供该科目的进度文件，不声称读过另一应用聊天。
- `scripts/patch_readme.py` 和 `scripts/sync_github.py` 都是执行器；事实核对、下一步摘要和权限范围由当前学习助手负责。

## 验证边界

Python 测试覆盖 Unicode/空格路径、UTF-8 BOM 摘要、CRLF、安装位置计算、拒绝覆盖、模拟 gh 请求、账号与私有状态校验、SHA 冲突、无变化、提交后核验。当前在 macOS 运行，不等于 Windows 或 DSH 内端到端实测。DSH 的读取能力受所选 preset 和插件配置影响。
