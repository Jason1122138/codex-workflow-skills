# codex-workflow-skills

Minimal runnable public package for three Codex workflow skills:

- `roadmap`: split one medium or large goal into reviewable, verifiable versions.
- `program`: coordinate one large goal as multiple ordered child roadmaps.
- `plan-check`: audit a draft plan before execution and produce a human approval checklist.

The package also includes a minimal roadmap/program hook runtime. It does not include private agent rules, unrelated skills, personal workflow history, or local project state.

## Included Files

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

## Install

```bash
git clone https://github.com/Jason1122138/codex-workflow-skills.git
cd codex-workflow-skills
bash install.sh --write-config
```

Then open `/hooks` in Codex and trust the installed command hook entries.
Start a new Codex session after installing skills or hooks.

## What The Hook Does

The hook is intentionally scoped to `roadmap`, `program`, and `plan-check`:

- injects active roadmap/program context on `SessionStart`;
- reminds agents to run `$plan-check` before roadmap/program approval;
- blocks approval requests when the draft plan has no valid `$plan-check` clearance;
- blocks committing local workflow state such as `program-codex/` and pending transition markers;
- writes a pending transition marker after a stubbed or configured verifier `PASS`;
- blocks new commits and final answers until the pending transition is consumed;
- reminds agents to close out completed roadmap/program state.

The hook does not install or reference any other skills.

## Quick Check

```bash
python3 -m py_compile hooks/roadmap_hook.py
CODEX_HOME="$(mktemp -d)" bash install.sh --write-config
```

## Notes

- `roadmap-codex/`, `program-codex/`, and `plan-check-codex/` are local workflow state in user projects.
- The verifier can be smoke-tested with `CODEX_ROADMAP_STUB_VERDICT=PASS` or `FAIL`.
- Without hooks, the skills still describe the manual workflow.
