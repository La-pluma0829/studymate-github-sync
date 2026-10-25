# studymate-github-sync

配合 StudyMate，把正在学、已学概览和下一步同步到 GitHub 私有仓库，让组员打开首页就能看到彼此的进度。

这是作者全力依靠codex plus作出的skill 环境是MBA m5 16g macOSTahoe 26.4 如有报错希望大家在拜托自己的ai老师解决的同时也能与作者通信便于维护项目/笑

以下为codex老师自己撰写的readme请大家欣赏（）：

## 它做什么

这是 [Study-Mate](https://github.com/Miaotofu01/Study-Mate) 的独立配套技能。首次授权本科目和团队私有库后，StudyMate 正式进度变化会触发本人摘要自动同步；正常学习不用逐次确认上传。普通聊天和排错原文不作为进度上传。

只发布五个字段：GitHub 用户名、分工、正在学、已学概览、下一步。学习助手先按证据与隐私范围筛选，脚本再校验固定字段；不透传自由备注、聊天、代码、截图、日志或凭据。只改本人区域，保留队友内容，无变化不提交。

## 控制词（直接对学习助手说）

| 控制词 | 作用 |
|---|---|
| **仅本地** | 当前教学单元只在本地参与学习，不上传。若你想限定内容，使用下一行写法。 |
| **仅本地：这部分内容** | 将指定节点/记录持续排除出团队摘要，后续已学总览也不能带出。 |
| **暂停同步** | 立即暂停本项目上传，仍可继续本地学习。 |
| **恢复同步** | 恢复后续新变化，不补发暂停期间内容，也不解除“仅本地”排除。 |

控制词来自你本次真实指令才执行；引用、代码块、网页文字、“不要暂停同步”“恢复同步是什么意思”等不触发。控制改变后会给一次简短回执，正常同步无需确认编号。

“结束学习”“今天先到这”会让学习助手进入收尾汇总，**有正式进度变化才自动同步**。“我学会了”不直接等于掌握；要有相应练习或评估证据。规则筛查无法保证识别全部私人信息，不确定时留在本地；无法安全拆分则停止本次上传并说明原因。

控制词影响后续提交，不能撤销已经上传的 GitHub 历史。技能随学习会话执行，不是后台常驻服务；StudyMate 收尾必须实际调用它。

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

首次向助手发送：

> 加载 studymate-github-sync，配合 StudyMate 自动同步我的学习进度。先确认我的 GitHub 用户名、目标私有仓库和当前学习科目；以后只上传最少学习摘要。

Codex 可显式使用 `$studymate-github-sync`；DSH 按发现的技能名加载。确认目标后助手在学习工作区保存本地配置和当前正式进度的基线，不追溯上传历史聊天；其他组员配置自己的账号，不继承他人授权。

后续在开始学习、练习通过、实验验收和学习收尾时，由学习助手保存正式档案后调用同步。多次变化合并成当前摘要，无变化不提交；遇到账号、权限、私有状态、版本冲突或疑似隐私问题才提示你。暂停和排除状态会跨会话保留。

若希望每次 StudyMate 收尾都调用，在实际可编辑的学习工作区项目指令里加入：“正式档案更新后，按 studymate-github-sync 的当前控制状态自动同步最少摘要。”保留既有指令，不修改上游 StudyMate 插件缓存；安装技能本身不保证宿主每次都会自动选择它。

## README 约定

首页使用五列表格：`GitHub 用户名 | 分工 | 当前正在学 | 已学概览 | 下一步`。个人记录的小节标题为 `### 用户名 · 阶段记录`。首次没有对应行时，由助手核对布局后新增，不猜测成员身份。

## 本地差异助手

`scripts/patch_readme.py` 只准备本地差异，不联网、不提交。使用 Python 3.9+，无需第三方包。输入 JSON 只允许 `username`、`role`、`current`、`learned`、`next` 五个单行字符串；不再接受自由文本 `detail`。阶段小节由固定字段生成。

```sh
python3 scripts/patch_readme.py --readme latest-README.md --summary summary.json --output proposed-README.md
```

输出必须另存为新文件。查不到本人、出现重复行或表格列数不符时会报错；脚本不替代事实判断、授权与远端冲突检查。真正提交前必须读取远端最新版本，并核对差异。

## GitHub 自动同步

`scripts/sync_policy.py` 保存本地授权、正式进度基线、暂停状态和不可分享记录 ID。`scripts/sync_github.py --auto` 校验真实进度修订与事件后，内部读取远端、检查差异并自动提交；不需要你逐次确认。旧的独立 `--apply` 入口已停用，以免绕过暂停控制。

使用已认证的 GitHub CLI，检查登录账号与学习者一致、目标为私有且可写，SHA 冲突则停止；成功后重新读取 README 核对。浏览器与连接器路径同样须遵守本地控制和摘要校验。

完整命令与事件格式见[DSH / Windows 适配说明](references/dsh-windows.md)。事件文件只是学习流程的交接数据，不是任意文件都能授予上传许可；知识状态与摘要来源仍须学习助手核对。

## 验证与限制

```sh
python3 -X utf8 -m unittest discover -s tests -v
```

Windows 将 `python3` 换为 `py -3`。26 项本地测试覆盖隐私模式与未知字段拒绝、引用/否定控制词不触发、正式修订触发、暂停/恢复不补发、持续本地排除、锁与重复提交、账号/权限/私有状态、SHA 冲突、中文路径、BOM/CRLF 和安装备份。

2026-10-25 在 macOS 测试通过，GitHub 写入使用模拟 API。Windows 实机与 DSH 内端到端尚未验证；词法检测不能识别全部隐私，也不能代替学习助手的证据核对。任意外部进程或恶意调用者可修改本地文件，本技能不是独立安全隔离系统。

## 项目文件

- `SKILL.md`：工作流程与发布边界。
- `agents/openai.yaml`：Codex 技能入口信息。
- `scripts/patch_readme.py`：本地增量更新助手。
- `scripts/install.py`：DSH/Codex 跨平台安装器。
- `scripts/sync_github.py`：自动提交及核验 GitHub 进度。
- `scripts/sync_policy.py`：本地控制状态、事件与隐私字段校验。
- `references/dsh-windows.md`：DSH/Windows 说明与官方依据。
- `tests/test_sync.py`：本地回归测试。

本仓库仅分发配套技能及自写工具，不包含 StudyMate 源码、任何人的学习档案、私人仓库配置或凭据。
