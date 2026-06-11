---
name: "roadmap"
description: "Use when the user invokes $roadmap, says /roadmap as an intent marker, asks to create or continue a roadmap workflow, or wants a medium/large Codex task split into reviewable, verifiable versions with status files."
---

# Roadmap Workflow

Use this skill to plan and run medium or large Codex work as versioned files
under `roadmap-codex/`. A roadmap is a working contract, not a loose outline.

## Entry Rules

- Treat `$roadmap`, `/roadmap`, and "roadmap workflow" as requests to use this workflow.
- In Codex, `/roadmap` is an intent marker; `$roadmap` is the explicit skill invocation.
- Use the active project instructions in `AGENTS.md` together with this skill.
- If global hooks are untrusted or unavailable, run the workflow manually and say automation is not active.
- Do not write Codex roadmap state under `roadmap/`; that path may be used by other agents. Use `roadmap-codex/`.
- Do not output only a bare version list unless the user explicitly asks for a sketch. A real roadmap writes the index and every version plan file.

## Create A Roadmap

1. Read project context first: `AGENTS.md`, relevant docs, existing `roadmap-codex/`, and files directly implied by the user's goal.
2. Derive a short phase slug from the goal, such as `user-auth` or `entry-docs-conda-only`. Ask if unclear.
3. If `roadmap-codex/<phase-slug>/` already exists, ask whether to continue, replace, merge, or use a new slug.
4. Split the goal into usually 3-7 versions. Each version should be 0.5-3 hours of focused work, independently reviewable, and independently verifiable.
5. Write `roadmap-codex/<phase-slug>/index.md` and all `v<N>-<slug>.md` files before reporting the roadmap.
6. Show the user a concise summary of versions, done-when checks, risks, and open decisions. Stop for approval.
7. Treat approval as authorization for the whole planned phase unless the user explicitly limits it to one version or a narrower scope.
8. After approval, set v1 to `in_progress`, fill `Started at`, and begin work.
9. Continue through planned versions automatically after each successful version commit. Do not ask for approval between versions unless a stop condition applies.

Push back instead of forcing a roadmap when the goal is too small for versioning
or too large to split coherently with the available context.

## Phase Layout

```text
roadmap-codex/<phase-slug>/
  index.md
  v1-<slug>.md
  v2-<slug>.md
```

Rules:

- Use sequential version numbers with no gaps.
- Keep version plans as siblings of `index.md`.
- Keep exactly one `Current` version in the phase index.
- New roadmaps start with v1 as `not_started`; approval starts v1 and authorizes the planned phase.
- Use `date '+%Y-%m-%d %H:%M %Z'` for timestamps.

## Phase Index Template

```markdown
# Phase: <phase-name>
Goal: <one-line phase goal>

**Started**: YYYY-MM-DD HH:MM TZ
**Current**: v1

## v1: <slug>
- **Goal**: <one-line goal>
- **Plan**: [./v1-<slug>.md](./v1-<slug>.md)
- **Status**: not_started
- **Started at**: -
- **Done at**: -
```

Repeat the version block for every planned version. Preserve blank lines between
blocks; do not collapse fields onto one line.

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

## Quality Gate

Before showing a new roadmap to the user, verify:

- Every version has its own plan file.
- Every version has `Goal`, `Scope`, `Done when`, `Approach`, `Verification`, `Risks`, `Decisions`, and `Notes`.
- Every `Done when` item is observable. Prefer "command/output/visible file state" over broad wording.
- Every `Approach` has concrete steps, not vague intentions.
- Every `Verification` item can actually be run or checked in the current project.
- The index links match real files.
- Status values are only `not_started`, `in_progress`, `done`, or `blocked`.
- No version is marked `in_progress` until the user approves starting the phase or explicitly approves that version.

## Version Commit Policy

- One version maps to one git commit.
- A version is not complete until local verification passes, the per-version
  subagent review passes, scoped changes are staged, the version review gate
  passes, and `git commit` succeeds.
- Before every version commit, run `git status --short`.
- Stage only files that belong to the current version scope. Do not stage unrelated user changes.
- Use commit message format: `roadmap(<phase-slug>): complete v<N>-<slug>`.
- If the project is not a git repository, commits are disabled, or the user explicitly forbids commits, record the reason in the version notes and report it before advancing.

## Version Subagent Review

Run a subagent review for every version after local verification passes and
before staging the version commit.

The review checks:

- the implementation satisfies the active version's `Done when` items;
- the changes stay inside the active version scope;
- verification evidence is real and not weakened or skipped;
- tests, docs, and user-facing behavior match the version goal;
- unrelated files, secrets, generated junk, and user changes are not included;
- the version is ready to be committed as one scoped commit.

Give the subagent only the active version plan, relevant files or diffs,
verification output, and known constraints. Do not ask it to redesign the
approved roadmap or expand the version scope.

If review fails, the main agent may fix only the concrete review findings and
retry at most twice. Record `review_retry`, `last_review_verdict`, and
`last_review_blockers` in the version notes. After two failed repair attempts,
mark the version `blocked`, record the blockers, and stop for the user.

## Version Review Gate

Codex roadmap uses the same kind of per-version review gate as the Claude
roadmap harness. This is an acceptance verifier, not a broad code review, and
it runs after the per-version subagent review.

- The gate runs on the commit candidate before the commit is recorded.
- It checks the active version plan and the candidate diff.
- It returns `PASS` only when every `Done when` item is satisfied with concrete evidence.
- It returns `FAIL` for empty diffs, missing evidence, contradicted criteria, or weakened tests/checks.
- It does not propose broad rewrites or expand the approved version scope.
- A version may advance only after this gate passes and the scoped commit succeeds.

## Continue A Roadmap

1. Read `AGENTS.md`, the active phase index, and the active version plan.
2. If there is no active phase or multiple ambiguous phases, stop and ask.
3. Work only inside the current version scope and the approved phase.
4. Before reporting a version ready, re-read every `Done when` item and run its verification.
5. After local verification passes, run the per-version subagent review. Fix concrete review findings at most twice; if review still fails, mark the version `blocked` and stop.
6. After subagent review passes, run `git status --short`, stage only scoped files, and run `git commit` with the standard version commit message. The commit triggers the version review gate when hooks are active.
7. On successful commit, mark the version `done` and fill `Done at`. If a next planned version exists, update `Current`, set the next version to `in_progress`, fill `Started at`, read its plan, and continue without asking for another approval. If no next version exists, report the completed phase.
8. On verifier FAIL with `retry < 3`, increment `retry`, keep the version `in_progress`, fix the concrete failure, and verify again.
9. On verifier FAIL at retry 3, mark the version `blocked`, record the blocker, and stop for the user.

## Stop Conditions

After the user approves a roadmap phase, continue until the phase is complete
unless one of these applies:

- Verification fails at retry 3 or the current version is blocked.
- Per-version subagent review fails after two main-agent repair attempts.
- The required version commit cannot be made or is denied by the verifier.
- The next step would exceed the approved roadmap scope.
- The next step requires unplanned destructive git, remote writes, publish or deploy, CI or `.env` changes, new dependencies, or global Codex file changes.
- Roadmap state is ambiguous, conflicting, or appears to be changed by another agent.
- Required input is missing.
- The user asks to pause, stop, or change scope.

## Hook Integration

Global hooks in `~/.codex/config.toml` may automate context injection, roadmap
prompt checks, and commit-time verification through
`~/.codex/hooks/roadmap_hook.py`. Hooks are optional enforcement; this skill is
the standard user-facing workflow.

Project-local `.codex/roadmap/` assets may override verifier assets for fixtures
or isolated tests, but the standard hook registration is global.
