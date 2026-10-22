# studymate-github-sync

配合 StudyMate，把正在学、已学概览和下一步同步到 GitHub 私有仓库，让组员打开首页就能看到彼此的进度。

这是作者全力依靠codex plus作出的skill 环境是MBA m5 16g macOSTahoe 26.4 如有报错希望大家在拜托自己的ai老师解决的同时也能与作者通信便于维护项目/笑

以下为codex老师自己撰写的readme请大家欣赏（）：

## 它做什么

这是 [Study-Mate](https://github.com/Miaotofu01/Study-Mate) 的配套技能，独立开发，未修改或打包上游插件。读取正式学习进度与练习证据，为本人生成“当前正在学 / 已学概览 / 下一步”，增量更新团队私有仓库 README。

只修改本人的行和阶段记录，保留队友内容及资料链接；没有新进度就不提交。学习计划不会当成已掌握，也不上传完整聊天、答案、误解库或账号凭据。

## 安装

将本仓库下载并解压为 `studymate-github-sync` 文件夹，放进 Codex 个人技能目录：`$CODEX_HOME/skills/`，未设置时为 `~/.codex/skills/`。最终入口为 `studymate-github-sync/SKILL.md`。重新加载技能或打开新聊天。

需要已安装 StudyMate、可读取的学习工作区，以及有写入权限的 GitHub 私有仓库。根据当前宿主能力，使用用户指定的 Safari、GitHub 连接器或已认证 CLI；技能不提供登录凭据。技能本身不要求额外付费 API；宿主、模型服务的费用由相应平台决定。

## 使用

向助手发送：

> 使用 $studymate-github-sync，学习结束后把我的进度同步到团队私有仓库。先确认我的 GitHub 用户名和目标仓库。

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

## 验证与限制

已通过技能格式校验和本地行为测试：只更新本人、保留队友与链接、重复执行无变化、拒绝缺失或重复成员、转义表格字符。未完成端到端真实 StudyMate 学习后同步测试；Windows/Linux、DSH 宿主尚未实测。当前验证基于 macOS 本地文件。

身份验证、网络、权限或版本冲突会中断同步，助手应保留待同步摘要并说明原因，不会声称成功或强制覆盖队友修改。

## 项目文件

- `SKILL.md`：工作流程与发布边界。
- `agents/openai.yaml`：Codex 技能入口信息。
- `scripts/patch_readme.py`：本地增量更新助手。

本仓库仅分发配套技能及自写工具，不包含 StudyMate 源码、任何人的学习档案、私人仓库配置或凭据。
