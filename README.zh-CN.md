# codex-workflow-skills

这是一个最小可运行的 Codex workflow 公开包，只包含三个技能：

- `roadmap`：把一个中大型目标拆成可 review、可验证的多个版本。
- `program`：把一个大型目标组织成多个按顺序推进的 child roadmaps。
- `plan-check`：执行前审核计划，并输出人工审批 checklist。

这个包同时包含最小 roadmap/program hook runtime。它不包含私人 agent rules、无关技能、个人 workflow 历史或本地项目状态。

## 包含文件

```text
install.sh
hooks/
  config.toml.snippet
  roadmap_hook.py
roadmap-assets/
  README.md
  verifier-prompt.md
  verifier.schema.json
skills/
  roadmap/
  program/
  plan-check/
```

## 安装

```bash
git clone https://github.com/Jason1122138/codex-workflow-skills.git
cd codex-workflow-skills
bash install.sh --write-config
```

安装后，在 Codex 里打开 `/hooks`，信任新安装的 command hooks。
安装 skills 或 hooks 后，建议新开一个 Codex session。

## Hook 做什么

这个 hook 只服务 `roadmap`、`program` 和 `plan-check`：

- 在 `SessionStart` 注入 active roadmap/program 上下文；
- 在 roadmap/program 请求时提醒先做 `$plan-check`；
- 当 draft plan 没有有效 `$plan-check` 结论时，阻止请求用户批准；
- 阻止提交 `program-codex/` 和 pending transition marker 等本地 workflow state；
- verifier `PASS` 后写入 pending transition marker；
- pending transition 未消费时，阻止新 commit 和 final answer；
- 对已完成的 roadmap/program 提醒及时收口。

这个 hook 不安装、不引用其他技能。

## 快速检查

```bash
python3 -m py_compile hooks/roadmap_hook.py
CODEX_HOME="$(mktemp -d)" bash install.sh --write-config
```

## 说明

- `roadmap-codex/`、`program-codex/`、`plan-check-codex/` 是用户项目里的本地 workflow state。
- verifier 可用 `CODEX_ROADMAP_STUB_VERDICT=PASS` 或 `FAIL` 做 smoke test。
- 不启用 hooks 时，三个技能仍可按手动 workflow 使用。
