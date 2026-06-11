---
name: "program"
description: "Use when the user invokes $program, says /program as an intent marker, asks for a program workflow, or wants one large Codex goal organized as multiple ordered roadmaps under program-codex/."
---

# Program Workflow

Use this skill when one large goal needs multiple child roadmaps. A program is
an orchestration layer above `$roadmap`; it does not replace the single-roadmap
workflow.

## Entry Rules

- Treat `$program`, `/program`, and "program workflow" as requests to use this workflow.
- Use `program-codex/`, never `roadmap-codex/`, for program state.
- Keep legacy `roadmap-codex/` roadmaps unchanged.
- A program contains multiple child roadmaps, but only one active roadmap by default.
- `program-codex/PROGRAM.md` is the only source of truth for the active roadmap.

## Starting A New Program

Before creating a new program, check whether `program-codex/PROGRAM.md`
already exists.

Rules:

- If no root `PROGRAM.md` exists, create the new program normally.
- If the existing program is `done` or `blocked`, archive the whole current
  `program-codex/` state before creating a new root `PROGRAM.md`.
- Archive path: `program-codex/archive/YYYY-MM-DD-<program-slug>/`.
- The archive must include the old `PROGRAM.md` and its `roadmaps/` directory.
- After archiving, the new active program owns the root `PROGRAM.md` and
  `roadmaps/` directory.
- If the existing program still has an `in_progress` roadmap, do not create a
  new program. Ask the user to choose: continue the existing program, pause or
  block and archive it, or explicitly overwrite it.
- Do not mix roadmaps from two different programs under the root `roadmaps/`.
- Do not use `archive/` as an active program source; hooks only use the root
  `PROGRAM.md`.

## Layout

```text
program-codex/
  PROGRAM.md
  roadmaps/
    R001-<slug>/
      index.md
      v1-<slug>.md
      v2-<slug>.md
    R002-<slug>/
      index.md
      v1-<slug>.md
```

## PROGRAM.md Template

```markdown
# Program: <name>
Goal: <one-line program goal>

**Started**: YYYY-MM-DD HH:MM TZ
**Active roadmap**: R001-<slug>
**Policy**: sequential

## Roadmaps

### R001-<slug>
- **Goal**: <one-line roadmap goal>
- **Path**: [./roadmaps/R001-<slug>/index.md](./roadmaps/R001-<slug>/index.md)
- **Status**: in_progress
- **Priority**: P0
- **Depends on**: none
- **Final verification**: -
- **Design review retry**: 0
- **State review retry**: 0
- **Last review verdict**: -
- **Last review blockers**: -
```

Allowed roadmap statuses: `not_started`, `in_progress`, `paused`, `done`, and
`blocked`.

## Child Roadmaps

Each child roadmap uses the existing `$roadmap` format inside
`program-codex/roadmaps/RNNN-<slug>/`.

Rules:

- Use sequential roadmap IDs: `R001`, `R002`, `R003`.
- Use exactly one active roadmap in `PROGRAM.md`.
- Child roadmap `index.md` manages only its own active version.
- Do not infer active roadmap from child roadmap status when `PROGRAM.md` exists.
- Run the `$roadmap` per-version subagent review for every child roadmap
  version before staging its version commit.
- Add roadmap-level final verification before marking a roadmap `done`.

## Program Design Review

After writing `PROGRAM.md` and all child roadmap files, call a subagent to
review the design before showing it to the user.

The subagent checks:

- child roadmap split, ordering, and dependencies;
- exactly one active roadmap;
- child roadmap paths and version files exist;
- each child roadmap has concrete done-when and verification checks;
- no conflict with legacy `roadmap-codex/`.

If review fails, the main agent may fix only the review findings and retry at
most twice. After two failed repair attempts, mark the program `blocked` and
report the blockers. If the main agent disagrees with the review, stop and
report; do not bypass it.

## Program State Review

When the active child roadmap is complete and before activating the next
roadmap, call a subagent to review the state transition. This is in addition to
the per-version subagent reviews that already ran inside the child roadmap.

The subagent checks:

- active child roadmap has all versions `done`;
- final verification is recorded;
- working tree has no unrelated staged changes;
- next roadmap dependencies are satisfied;
- the program state commit changes only allowed state files.

The same retry cap applies: at most two main-agent fixes, then `blocked`.

## Commit Gates

Version commits use the existing version review gate:

```text
roadmap(R001-<slug>): complete v<N>-<slug>
```

Program state commits use the program state gate:

```text
program: complete R001-<slug> and activate R002-<slug>
```

Program state commits may stage only:

- `program-codex/PROGRAM.md`;
- the completed child roadmap `index.md`;
- the next child roadmap `index.md`.

Do not mix code changes with program state commits.

## Conflicts

Stop instead of guessing when:

- a new program is requested while root `program-codex/PROGRAM.md` already
  exists and has not been archived or explicitly replaced;
- `PROGRAM.md` points to a missing active roadmap;
- multiple roadmaps are `in_progress`;
- the active child roadmap has multiple active versions;
- `program-codex/` is active while legacy `roadmap-codex/` also has an active roadmap;
- a program state commit includes non-state files.

Report the conflict and suggest one of: `status`, `repair`, `switch`, or
`pause`, depending on the situation.
