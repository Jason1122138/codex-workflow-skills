# codex-workflow-skills

Public export of two Codex workflow skills from a working local Codex setup:

- `roadmap` — break a medium or large task into reviewable, verifiable versions
- `program` — coordinate one large goal as multiple ordered child roadmaps

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

## Repository layout

```text
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
- advances version by version with scoped commit/review gates

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
- adds program-level design review and state-transition review between child roadmaps

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
