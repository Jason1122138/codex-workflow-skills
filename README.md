# codex-workflow-skills

- English: [README.md](./README.md)
- 中文： [README.zh-CN.md](./README.zh-CN.md)

Public export of two Codex workflow skills from a working local Codex setup:

- `roadmap` — break a medium or large task into reviewable, verifiable versions
- `program` — coordinate one large goal as multiple ordered child roadmaps
- optional roadmap hooks — add session-start context injection, prompt-time workflow enforcement, and Bash pre-tool review checks for users who want the fuller automation layer

These skills are meant to be installed into Codex's local skills directory and used together with a project-level `AGENTS.md`.

## Included skills

| Skill | Explicit trigger | Use when | Writes state under |
| --- | --- | --- | --- |
| `roadmap` | `$roadmap` | One medium/large goal should be split into 3–7 independently reviewable versions | `roadmap-codex/` |
| `program` | `$program` | One very large goal needs multiple ordered roadmaps, with only one active roadmap at a time | `program-codex/` |

Notes:

- In these skills, `/roadmap` and `/program` are treated as intent markers.
- The explicit skill invocation is `$roadmap` or `$program`.
- `program` is an orchestration layer above `roadmap`; it does not replace the single-roadmap workflow.
- The repository also includes an optional hook pack for users who want the workflow guardrails, not just the skill text.

## Repository layout

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

## Install

### Option A: clone this repo and copy the skills

```bash
git clone https://github.com/Jason1122138/codex-workflow-skills.git
cd codex-workflow-skills
mkdir -p ~/.codex/skills
cp -R skills/roadmap ~/.codex/skills/
cp -R skills/program ~/.codex/skills/
```

### Option B: symlink the skills for easier updates

```bash
git clone https://github.com/Jason1122138/codex-workflow-skills.git
cd codex-workflow-skills
mkdir -p ~/.codex/skills
ln -sfn "$PWD/skills/roadmap" ~/.codex/skills/roadmap
ln -sfn "$PWD/skills/program" ~/.codex/skills/program
```

### Windows PowerShell copy install

```powershell
git clone https://github.com/Jason1122138/codex-workflow-skills.git
cd codex-workflow-skills
New-Item -ItemType Directory -Force -Path "$HOME/.codex/skills" | Out-Null
Copy-Item -Recurse -Force "skills/roadmap" "$HOME/.codex/skills/roadmap"
Copy-Item -Recurse -Force "skills/program" "$HOME/.codex/skills/program"
```

### Verify install

Check that the files exist locally:

```bash
ls ~/.codex/skills/roadmap
ls ~/.codex/skills/program
```

You should see `SKILL.md` and `agents/openai.yaml` in each skill directory.

If Codex does not pick up the skills immediately, start a new Codex session.

## Optional: install the roadmap hooks

If you want to share the fuller workflow experience with a friend, the skills alone are not the whole story. This repo also includes:

- `hooks/roadmap_hook.py`
- `roadmap-assets/verifier-prompt.md`
- `roadmap-assets/verifier.schema.json`
- `config-examples/roadmap-hooks.example.toml`

These are optional, but useful when you want:

- active roadmap/program context injected at session start;
- roadmap/program request enforcement when the user submits a prompt;
- a Bash pre-tool hook that can inspect roadmap-related commit behavior.

### Hook prerequisites

Before installing the hook pack, the receiving machine should already have:

- `bash`
- `python3`
- `git`

If the user wants the advanced automatic verifier path, they also need:

- a working `codex` CLI on `PATH`
- support for `codex exec`

Platform note:

- the shared hook commands in this repo are **POSIX-oriented**;
- on Windows, treat this as a **WSL / Git Bash style setup**, not a native PowerShell hook recipe.

### Hook install (macOS / Linux)

```bash
mkdir -p ~/.codex/hooks ~/.codex/roadmap
cp hooks/roadmap_hook.py ~/.codex/hooks/roadmap_hook.py
cp roadmap-assets/verifier-prompt.md ~/.codex/roadmap/verifier-prompt.md
cp roadmap-assets/verifier.schema.json ~/.codex/roadmap/verifier.schema.json
```

Then merge the example snippet from:

```text
config-examples/roadmap-hooks.example.toml
```

into:

```text
~/.codex/config.toml
```

Important:

- make sure `hooks = true` is enabled in Codex config;
- do **not** copy another machine's `[hooks.state]` entries;
- restart Codex after updating the hook config.

### What the hook currently registers

- `SessionStart` → load roadmap/program context on startup/resume/clear/compact
- `UserPromptSubmit` → inject roadmap/program workflow enforcement hints
- `PreToolUse` for `Bash` → check roadmap-related commit/verifier flow

### Commit-time verifier behavior

By default, the hook can warn about roadmap verification flow, but the automatic `codex exec` verifier path is **not** enabled unless the user explicitly opts in.

When that advanced verifier path is enabled, the hook launches a nested:

- `codex exec`
- in `--sandbox read-only`
- with `--dangerously-bypass-hook-trust`

This is intentional for the verifier flow, but it should be treated as an advanced opt-in mode, not a default beginner setup.

Optional advanced toggles are documented in:

```text
config-examples/roadmap-hooks.example.toml
```

In particular:

- `CODEX_ROADMAP_RUN_CODEX_EXEC=1` enables the `codex exec` verifier path
- `CODEX_ROADMAP_FAIL_EXIT=<nonzero>` can make verifier FAIL return a blocking exit code after smoke testing
- `CODEX_ROADMAP_ASSETS_DIR=...` can override where verifier assets are loaded from

### Minimal smoke test

After installing the hook file and config snippet, a minimal local check is:

```bash
python3 ~/.codex/hooks/roadmap_hook.py session-start </dev/null
```

With no active roadmap/program in the current directory, this should exit quietly instead of crashing.

## How to invoke the skills

### `roadmap`

Use `roadmap` when one task is big enough to need versioned execution, but still belongs to a single roadmap.

Examples:

```text
$roadmap Turn this auth refactor into 4 reviewable versions with concrete done-when checks.

$roadmap Continue the existing roadmap workflow for this feature and finish the current version.
```

What it does:

- reads project context first (`AGENTS.md`, relevant docs, existing roadmap files)
- creates a phase under `roadmap-codex/<phase-slug>/`
- writes an `index.md` plus one `v<N>-<slug>.md` file per version
- expects each version to have concrete goal, scope, done-when checks, approach, verification, risks, decisions, and notes
- runs local verification, per-version subagent review, and scoped commit/review gates before advancing

Choose `roadmap` for:

- medium or large implementation tasks
- refactors that need reviewable slices
- bugfix programs that should be broken into verifiable steps
- documentation or migration work that should be completed in ordered versions

Avoid `roadmap` for:

- tiny one-shot tasks
- work that is too vague to split coherently
- giant multi-stream initiatives that need several separate roadmaps

### `program`

Use `program` when one goal is too large for a single roadmap and should be organized as multiple child roadmaps.

Examples:

```text
$program Rebuild this legacy data pipeline as multiple ordered roadmaps: schema cleanup, importer rewrite, test recovery, and release prep.

$program Continue the active program workflow and move from the current child roadmap to the next one.
```

What it does:

- creates or continues `program-codex/PROGRAM.md`
- manages child roadmaps under `program-codex/roadmaps/RNNN-<slug>/`
- keeps exactly one active roadmap in the root `PROGRAM.md`
- uses `roadmap` format inside each child roadmap
- runs per-version subagent review inside every child roadmap
- adds program-level design review and state-transition review between child roadmaps
- archives a completed program immediately so the next new program starts from `R001`

Program completion rule:

- root `program-codex/PROGRAM.md` is only for the current active program;
- when all child roadmaps are done, archive `PROGRAM.md` and `roadmaps/` to `program-codex/archive/YYYY-MM-DD-P001-<program-slug>/`;
- after archiving, root `PROGRAM.md` and root `roadmaps/` should be absent;
- a new program recreates both root files/directories and starts child roadmap IDs at `R001`, not `R00N+1`.

Choose `program` for:

- large rewrites spanning multiple subsystems
- multi-phase modernization work
- migrations where each phase should have its own roadmap and verification
- initiatives that need explicit ordering and dependency tracking across roadmaps

Avoid `program` for:

- single-phase tasks that fit one roadmap
- work with no meaningful separation between phases
- quick tasks that do not need roadmap state files

## Expected state files

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
  archive/
    YYYY-MM-DD-P001-<program-slug>/
      PROGRAM.md
      roadmaps/
```

## Practical workflow guidance

A simple rule of thumb:

- Use **`roadmap`** when the work is big, but still one coherent stream.
- Use **`program`** when the work is so large that it should be split into multiple roadmaps with ordering and dependencies.

In other words:

- one phase, many versions → `roadmap`
- many phases, many roadmaps → `program`

## License

MIT. See [LICENSE](./LICENSE).
