# codex-workflow-skills

- English: [README.md](./README.md)
- 中文： [README.zh-CN.md](./README.zh-CN.md)

这是两个从本地可用 Codex 环境中导出的工作流技能：

- `roadmap` —— 把一个中大型任务拆成多个可 review、可验证的版本
- `program` —— 把一个超大目标组织成多个按顺序推进的 child roadmaps

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

## 仓库结构

```text
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
