---
name: "program"
description: "Use when the user invokes $program, says /program as an intent marker, asks for a program workflow, or wants one large Codex goal organized as multiple ordered roadmaps under program-codex/."
---

# Program Workflow

Use this skill when one large goal needs multiple child roadmaps. A program is an orchestration layer above `$roadmap`; it does not replace the single-roadmap workflow.

## Entry Rules

- Treat `$program`, `/program`, and "program workflow" as requests to use this workflow.
- Use local `program-codex/`, never `roadmap-codex/`, for program state.
- A repo/worktree root may have only one active workflow: `$program` or `$roadmap`.
- A program contains multiple child roadmaps, but only one active roadmap by default.
- `program-codex/active/PROGRAM.md` is the only source of truth for the active roadmap.
- `program-codex/` is local Codex state and must not be staged or committed.
- A completed program must be closed out immediately; `active/` is only for the currently active program.
- Every new program requires `$plan-check` before Program Design Review, user approval, or implementation.

## Starting A New Program

Before creating a new program, check whether `program-codex/active/PROGRAM.md` already exists.

Rules:

- If no active `PROGRAM.md` exists, create the new program under `program-codex/active/` and start child roadmap numbering at `R001`.
- If the existing active program is `done`, close out the whole `active/` state before new planning.
- If the existing active program is `blocked`, keep it under `active/` by default so the blocker remains visible; close it out only when the user explicitly asks.
- Closeout path: `program-codex/archive/YYYY-MM-DD-HHMM-P001-<program-slug>/`.
- The closeout copy must include the old `PROGRAM.md` and its complete `roadmaps/` directory.
- After closeout, remove `program-codex/active/`; the next active program recreates it from scratch.
- Do not continue child roadmap numbering from completed history. Every new active program starts at `R001`.

## Layout

```text
program-codex/
  active/
    PROGRAM.md
    roadmaps/
      R001-<slug>/
        index.md
        v1-<slug>.md
      R002-<slug>/
        index.md
        v1-<slug>.md
  archive/
    YYYY-MM-DD-HHMM-P001-<program-slug>/
      PROGRAM.md
      roadmaps/
```

## PROGRAM.md Template

```markdown
# Program: <name>
Goal: <one-line program goal>

**Program ID**: P001-<slug>
**Status**: draft
**Approval**: pending
**Started**: -
**Done at**: -
**Active roadmap**: R001-<slug>
**Policy**: sequential
**Plan review**: -

## Roadmaps

### R001-<slug>
- **Goal**: <one-line roadmap goal>
- **Path**: [./roadmaps/R001-<slug>/index.md](./roadmaps/R001-<slug>/index.md)
- **Status**: not_started
- **Priority**: P0
- **Depends on**: none
- **Final verification**: -
- **Design review retry**: 0
- **State review retry**: 0
- **Last review verdict**: -
- **Last review blockers**: -
```

Allowed program statuses: `draft`, `in_progress`, `done`, and `blocked`.
Allowed roadmap statuses: `not_started`, `in_progress`, `paused`, `done`, and `blocked`.

## Child Roadmaps

Each child roadmap uses the `$roadmap` format inside `program-codex/active/roadmaps/RNNN-<slug>/`.

Rules:

- Use sequential roadmap IDs: `R001`, `R002`, `R003`.
- Use exactly one active roadmap in `PROGRAM.md`.
- Child roadmap `index.md` manages only its own active version.
- Every child roadmap version has a hard metric contract tied to that version's goal and `Done when`.
- Run the `$roadmap` per-version review for every child roadmap version before staging its version commit.
- Add roadmap-level final verification before marking a child roadmap `done`.

## Plan Check Preflight

After writing `PROGRAM.md` and all child roadmap files, run `$plan-check` on the complete draft program before Program Design Review or user approval.

Rules:

- `$plan-check` approval is not user approval.
- Review `PROGRAM.md`, every child roadmap `index.md`, and every child version plan file needed to judge split, order, done-when checks, and verification.
- Record the exact verdict in `**Plan review**`, such as `PASS ($plan-check YYYY-MM-DD; P0: none; P1: none; Findings: None)`.
- If `$plan-check` returns any `P0` or `P1`, fix only concrete plan findings and rerun at most twice. If any remains, mark the program `blocked` and report blockers.
- After `PASS` or P2-only `CONCERNS`, show the Program Design Review, plan-check result, and `plan-check-codex/human-review.html` preview path, then stop for explicit approval.

## Program Design Review

After `$plan-check` passes or has only P2 concerns, call a subagent to review the design before showing it to the user. A passing Program Design Review means the program is ready for the user's approval decision; it does not authorize implementation.

The review checks child roadmap split, ordering, dependencies, active roadmap uniqueness, child roadmap paths, version files, hard metrics, and compatibility with standalone `roadmap-codex/` state.

If review fails, the main agent may fix only review findings and retry at most twice. After two failed repair attempts, mark the program `blocked` and stop.

## User Approval

Before implementation, the user must explicitly approve the program after seeing the `$plan-check` result and Program Design Review.

After explicit approval, update `**Status**: in_progress`, set `**Approval**: approved (YYYY-MM-DD HH:MM TZ; user)`, fill `**Started**`, mark only the first approved child roadmap and its first version `in_progress`, then begin implementation.

## Program State Review

When the active child roadmap is complete and before activating the next roadmap, call a subagent to review the state transition. The review checks all versions are `done`, final verification is recorded, dependencies are satisfied, only local `program-codex/active/` state changed, and no `program-codex/` files are staged.

## Pending Transition Enforcement

When hooks are active, verifier `PASS` inside a program creates `program-codex/active/.codex-pending-transition.json`.

Rules:

- A successful child version commit is not complete until the pending transition is consumed.
- If the child roadmap has another version, mark the committed version `done`, activate the next version, and continue inside the same child roadmap.
- If the committed version was the final version of a child roadmap, record final verification, run Program State Review, mark the child roadmap `done`, and activate the next child roadmap.
- If the committed version was the final version of the final child roadmap, record final verification, run Program State Review for completion, mark the program `done`, and close out `program-codex/active/`.
- New `git commit` commands and final answers are blocked while a transition is required.
- Do not stage or commit `.codex-pending-transition.json`.

## Git Boundary

Version commits use the child roadmap commit format:

```text
roadmap(R001-<slug>): complete v<N>-<slug>
```

There are no program state commits. `program-codex/` must be ignored by git and kept as local Codex state.

## Conflicts

Stop instead of guessing when active program state conflicts with standalone roadmap state, `PROGRAM.md` points to a missing active roadmap, multiple roadmaps are `in_progress`, the active child roadmap has multiple active versions, or any `program-codex/` file is staged for git.
