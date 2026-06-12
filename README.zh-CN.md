# codex-workflow-skills

- English: [README.md](./README.md)
- 中文： [README.zh-CN.md](./README.zh-CN.md)

这是两个从本地可用 Codex 环境中导出的工作流技能：

- `roadmap` —— 把一个中大型任务拆成多个可 review、可验证的版本
- `program` —— 把一个超大目标组织成多个按顺序推进的 child roadmaps
- 可选 roadmap hooks —— 给想要“完整自动化体验”的用户补上 session-start 上下文注入、prompt 提交时 workflow enforcement、以及 Bash pre-tool 检查

这两个技能适合安装到 Codex 的本地 skills 目录中，并配合项目级 `AGENTS.md` 一起使用。

## 包含的技能

| 技能 | 显式触发词 | 适用场景 | 状态文件目录 |
| --- | --- | --- | --- |
| `roadmap` | `$roadmap` | 一个中大型目标，需要拆成 3–7 个可独立 review / 验证的版本 | `roadmap-codex/` |
| `program` | `$program` | 一个超大目标，需要拆成多个有顺序的 roadmap，并且同一时间只激活一个 roadmap | `program-codex/` |

补充说明：

- 这两个技能里，`/roadmap` 和 `/program` 被视为 intent marker。
- 真正的显式 skill 调用写法是 `$roadmap` 和 `$program`。
- `program` 是建立在 `roadmap` 之上的编排层，不是替代单 roadmap 的工作流。
- 仓库里还包含一套可选 hook 分享包，适合想把 workflow guardrails 一起分享给朋友的人。

## 仓库结构

```text
config-examples/
  roadmap-hooks.example.toml
hooks/
  roadmap_hook.py
roadmap-assets/
  verifier-prompt.md
  verifier.schema.json
skills/
  roadmap/
    SKILL.md
    agents/openai.yaml
  program/
    SKILL.md
    agents/openai.yaml
```

## 安装方法

### 方案 A：clone 仓库后复制到本地 Codex skills 目录

```bash
git clone https://github.com/Jason1122138/codex-workflow-skills.git
cd codex-workflow-skills
mkdir -p ~/.codex/skills
cp -R skills/roadmap ~/.codex/skills/
cp -R skills/program ~/.codex/skills/
```

### 方案 B：用 symlink 安装，后续更新更方便

```bash
git clone https://github.com/Jason1122138/codex-workflow-skills.git
cd codex-workflow-skills
mkdir -p ~/.codex/skills
ln -sfn "$PWD/skills/roadmap" ~/.codex/skills/roadmap
ln -sfn "$PWD/skills/program" ~/.codex/skills/program
```

### Windows PowerShell 安装

```powershell
git clone https://github.com/Jason1122138/codex-workflow-skills.git
cd codex-workflow-skills
New-Item -ItemType Directory -Force -Path "$HOME/.codex/skills" | Out-Null
Copy-Item -Recurse -Force "skills/roadmap" "$HOME/.codex/skills/roadmap"
Copy-Item -Recurse -Force "skills/program" "$HOME/.codex/skills/program"
```

### 安装后验证

检查本地目录：

```bash
ls ~/.codex/skills/roadmap
ls ~/.codex/skills/program
```

每个技能目录下都应该能看到：

- `SKILL.md`
- `agents/openai.yaml`

如果 Codex 没有马上识别到新技能，重开一个新的 Codex session 即可。

## 可选：安装 roadmap hooks

如果你想把“完整体验”分享给朋友，那只发 skill 还不够。这个仓库里还包含：

- `hooks/roadmap_hook.py`
- `roadmap-assets/verifier-prompt.md`
- `roadmap-assets/verifier.schema.json`
- `config-examples/roadmap-hooks.example.toml`

这些内容是可选的，但当你希望朋友也拥有下面这些能力时会很有用：

- session start 时自动注入 active roadmap/program 上下文；
- 用户提交 prompt 时自动补 workflow enforcement 提示；
- 对 Bash 工具调用增加 roadmap 相关的 pre-tool 检查。

### Hook 前置依赖

朋友那台机器在安装这套 hook 之前，最好已经具备：

- `bash`
- `python3`
- `git`

如果还想启用高级自动 verifier 路径，还需要：

- `PATH` 上可用的 `codex` CLI
- 支持 `codex exec`

平台说明：

- 这个仓库里分享的 hook 命令是 **POSIX 风格**；
- 对 Windows 用户，更适合把它理解为 **WSL / Git Bash 方案**，而不是原生 PowerShell hook 教程。

### Hook 安装（macOS / Linux）

```bash
mkdir -p ~/.codex/hooks ~/.codex/roadmap
cp hooks/roadmap_hook.py ~/.codex/hooks/roadmap_hook.py
cp roadmap-assets/verifier-prompt.md ~/.codex/roadmap/verifier-prompt.md
cp roadmap-assets/verifier.schema.json ~/.codex/roadmap/verifier.schema.json
```

然后把下面这个示例片段：

```text
config-examples/roadmap-hooks.example.toml
```

合并到：

```text
~/.codex/config.toml
```

注意：

- 确保 Codex 配置里启用了 `hooks = true`；
- **不要**复制别人机器上的 `[hooks.state]` 条目；
- 改完 hook 配置后，重开一个 Codex session。

### 这套 hook 当前会注册什么

- `SessionStart` → 在 startup / resume / clear / compact 时加载 roadmap/program 上下文
- `UserPromptSubmit` → 在提交 prompt 时注入 roadmap/program workflow enforcement 提示
- `PreToolUse`（匹配 `Bash`）→ 检查 roadmap 相关 commit / verifier 流程

### commit-time verifier 的默认行为

默认情况下，这个 hook 可以给出 roadmap verification 流程提醒，但 **不会** 自动启用 `codex exec` verifier 路径；是否开启由使用者自己决定。

一旦开启这个高级 verifier 路径，hook 会启动一层嵌套的：

- `codex exec`
- `--sandbox read-only`
- `--dangerously-bypass-hook-trust`

这是 verifier 流程有意为之的高级模式，所以应当明确把它当作 **可选 opt-in**，而不是默认新手配置。

可选高级开关已经写在：

```text
config-examples/roadmap-hooks.example.toml
```

其中最关键的是：

- `CODEX_ROADMAP_RUN_CODEX_EXEC=1`：开启 `codex exec` verifier 路径
- `CODEX_ROADMAP_FAIL_EXIT=<非零值>`：在 smoke test 通过后，可把 verifier FAIL 变成阻断退出码
- `CODEX_ROADMAP_ASSETS_DIR=...`：覆盖 verifier 资产目录

### 最小 smoke test

安装完 hook 文件和配置片段后，可以先做一个最小本地检查：

```bash
python3 ~/.codex/hooks/roadmap_hook.py session-start </dev/null
```

如果当前目录下没有 active roadmap/program，它应该安静退出，而不是直接崩掉。

## 怎么用

### `roadmap`

当一个任务已经大到不适合一次性做完，但仍然属于**同一条主线**时，用 `roadmap`。

示例：

```text
$roadmap 把这次 auth 重构拆成 4 个可 review 的版本，并给出明确 done-when checks。

$roadmap 继续这个 feature 的既有 roadmap workflow，并完成当前版本。
```

它会做什么：

- 先读项目上下文（`AGENTS.md`、相关文档、已有 roadmap 文件）
- 在 `roadmap-codex/<phase-slug>/` 下创建一个 phase
- 写出一个 `index.md`，以及每个版本对应的 `v<N>-<slug>.md`
- 要求每个版本都有明确的目标、范围、done-when、实现步骤、验证方式、风险、决策点、备注
- 按版本推进，并带有 scoped commit / review gate

适合 `roadmap` 的场景：

- 中大型功能开发
- 需要拆 slice 的重构
- 需要逐步验证的 bugfix 主线
- 需要分阶段推进的文档/迁移工作

不适合 `roadmap` 的场景：

- 很小的一次性任务
- 目标太模糊，当前还无法合理拆分
- 明显应该拆成多条 roadmap 的超大计划

### `program`

当一个目标已经大到**一条 roadmap 不够用**，需要拆成多个 child roadmaps，并明确顺序/依赖关系时，用 `program`。

示例：

```text
$program 把这个遗留数据流水线重建任务拆成多个有顺序的 roadmap：schema 清理、importer 重写、测试恢复、发布准备。

$program 继续当前 program workflow，并从当前 child roadmap 切换到下一个。
```

它会做什么：

- 创建或继续 `program-codex/PROGRAM.md`
- 在 `program-codex/roadmaps/RNNN-<slug>/` 下管理多个 child roadmaps
- 保证根 `PROGRAM.md` 中始终只有一个 active roadmap
- 每个 child roadmap 内部继续沿用 `roadmap` 的格式
- 在 child roadmap 之间加入 program 级别的 design review / state transition review

适合 `program` 的场景：

- 跨多个子系统的大型重写
- 多阶段 modernization / migration
- 每个阶段都需要单独 roadmap 和验证闭环的项目
- 需要明确顺序和依赖关系的大计划

不适合 `program` 的场景：

- 单阶段任务，其实一条 roadmap 就够
- 各阶段没有明确边界，拆开反而更乱
- 很小的快速任务，不值得维护 program 状态文件

## 会生成什么状态文件

### `roadmap`

```text
roadmap-codex/<phase-slug>/
  index.md
  v1-<slug>.md
  v2-<slug>.md
  ...
```

### `program`

```text
program-codex/
  PROGRAM.md
  roadmaps/
    R001-<slug>/
      index.md
      v1-<slug>.md
      ...
    R002-<slug>/
      index.md
      v1-<slug>.md
      ...
```

## 快速判断：该用哪个？

一个简单经验法则：

- **一个 phase，多个 versions** → 用 `roadmap`
- **多个 phases，多个 roadmaps** → 用 `program`

换句话说：

- 工作很大，但还是一条主线 → `roadmap`
- 工作大到需要多个 roadmap 编排 → `program`

## License

MIT。见 [LICENSE](./LICENSE)。
