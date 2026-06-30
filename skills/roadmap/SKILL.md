---
name: "roadmap"
description: "Use when the user invokes $roadmap, says /roadmap as an intent marker, asks to create or continue a roadmap workflow, or wants a medium/large Codex task split into reviewable, verifiable versions with status files."
---

# Roadmap Workflow

Use this skill to plan and run medium or large Codex work as versioned files under `roadmap-codex/`. A roadmap is a working contract, not a loose outline.

## Entry Rules

- Treat `$roadmap`, `/roadmap`, and "roadmap workflow" as requests to use this workflow.
- Use project instructions together with this skill.
- If hooks are unavailable or untrusted, run the same workflow manually and say automation is inactive.
- Use `roadmap-codex/` for roadmap state.
- A repo/worktree root may have only one active workflow: `$roadmap` or `$program`.
- Every new roadmap requires `$plan-check` before user approval or implementation.
- A completed roadmap phase must be closed out immediately; root `roadmap-codex/<phase-slug>/` is only for active or unfinished phases.

## Create A Roadmap

1. Read project context first: project instructions, relevant docs, existing `roadmap-codex/`, and files directly implied by the goal.
2. Derive a short phase slug from the goal.
3. If `roadmap-codex/<phase-slug>/` already exists and all versions are `done`, close it out before planning new work; do not add `vN+1` to a completed phase.
4. Split the goal into usually 3-7 versions. Each version should be independently reviewable and independently verifiable.
5. Write `roadmap-codex/<phase-slug>/index.md` and all `v<N>-<slug>.md` files before reporting the roadmap.
6. Run `$plan-check` on the complete draft roadmap before asking the user to approve it.
7. Record the exact plan-check verdict in `**Plan review**`, such as `PASS ($plan-check YYYY-MM-DD; P0: none; P1: none; Findings: None)`.
8. If `$plan-check` returns any `P0` or `P1`, fix only the concrete plan findings and rerun at most twice. If any `P0` or `P1` remains, stop and report blockers.
9. If `$plan-check` returns `CONCERNS` with only `P2`, show those concerns and ask whether to approve with them.
10. Show the user a concise version summary, done-when checks, metrics, risks, open decisions, plan-check verdict, and `plan-check-codex/human-review.html` preview path. Stop for approval.
11. Treat approval as authorization for the whole planned phase unless the user explicitly limits scope.
12. After approval, set v1 to `in_progress`, fill `Started at`, and begin work.
13. Continue through planned versions automatically after each successful version commit unless a stop condition applies.

## Phase Layout

```text
roadmap-codex/<phase-slug>/
  index.md
  v1-<slug>.md
  v2-<slug>.md
roadmap-codex/archive/YYYY-MM-DD-HHMM-<phase-slug>/
  index.md
  v1-<slug>.md
```

Rules:

- Use sequential version numbers with no gaps.
- Keep version plans as siblings of `index.md`.
- Keep exactly one `Current` version in the phase index.
- New roadmaps start with v1 as `not_started`; approval starts v1.
- Use `date '+%Y-%m-%d %H:%M %Z'` for timestamps.
- Do not use `roadmap-codex/archive/` as an active roadmap source.

## Phase Index Template

```markdown
# Phase: <phase-name>
Goal: <one-line phase goal>

**Started**: YYYY-MM-DD HH:MM TZ
**Current**: v1
**Plan review**: -

## v1: <slug>
- **Goal**: <one-line goal>
- **Plan**: [./v1-<slug>.md](./v1-<slug>.md)
- **Status**: not_started
- **Started at**: -
- **Done at**: -
```

## Version Plan Template

```markdown
# v<N>: <slug>

**Phase**: [<phase-name>](./index.md)

## Goal
<specific result this version achieves>

## Scope
- In: <files, behaviors, docs, or interfaces this version may touch>
- Out: <explicit non-goals or deferred work>

## Done when
- [ ] <observable, testable criterion>

## Metrics
- <metric name>: <evidence source or check> must show <target threshold or binary pass condition>

## Approach
1. <concrete step>
2. <concrete step>
3. <concrete step>

## Verification
- <command, test, search, or manual check that proves the criteria>

## Risks
- <risk or "None known">

## Decisions
- <decision needed from user or "None">

## Notes
- retry: 0
- review_retry: 0
- last_review_verdict: -
- last_review_blockers: -
```

## Version Commit Policy

- One version maps to one git commit.
- A version is not complete until local verification passes, per-version review passes, scoped changes are staged, the version review gate passes, and `git commit` succeeds.
- Before every version commit, run `git status --short`.
- Stage only files that belong to the current version scope.
- Use commit message format: `roadmap(<phase-slug>): complete v<N>-<slug>`.

## Continue A Roadmap

1. Read the active phase index and active version plan.
2. Work only inside the current version scope and approved phase.
3. Re-read every `Done when` item and run verification before reporting a version ready.
4. Run per-version review after local verification passes. Fix concrete findings at most twice; if review still fails, mark the version `blocked` and stop.
5. Stage only scoped files and run `git commit` with the standard version commit message. Hooks run the version review gate when active.
6. On successful commit, mark the version `done` and fill `Done at`. If a next version exists, update `Current`, set the next version to `in_progress`, fill `Started at`, read its plan, and continue. If no next version exists, close out the completed phase immediately.
7. On verifier `FAIL` with `retry < 3`, increment `retry`, keep the version `in_progress`, fix the concrete failure, and verify again.
8. On verifier `FAIL` at retry 3, mark the version `blocked`, record the blocker, and stop.

## Pending Transition Enforcement

When hooks are active, verifier `PASS` creates `roadmap-codex/<phase-slug>/.codex-pending-transition.json`.

Rules:

- A successful version commit is not the end of the version. Consume the pending transition first.
- `SessionStart` reports an unconsumed marker before normal roadmap context.
- New `git commit` commands and final answers are blocked while a transition is required.
- Advancing `index.md` correctly, or closing out a completed final phase, clears the marker automatically.
- Do not stage or commit `.codex-pending-transition.json`.

## Hook Integration

Global hooks may automate context injection, plan approval checks, pending transition checks, and commit-time verification through `~/.codex/hooks/roadmap_hook.py`. Hooks are optional enforcement; this skill remains the standard workflow.
