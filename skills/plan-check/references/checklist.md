# Plan Check Review Checklist

Use this file as the review authority for `$plan-check`. Apply `Universal
Checks` to every plan, then apply the section for the detected plan type.

## Universal Checks

- **Goal**: The plan states the intended outcome, not just a list of activities.
- **Scope**: In-scope and out-of-scope boundaries are explicit, or obvious from
  the user request and project context.
- **Execution units**: The work is split into units that can be executed,
  reviewed, and accepted without hidden later work.
- **Done when**: Each executable unit has observable completion criteria.
- **Hard acceptance condition**: Each executable unit has at least one concrete
  pass condition. It may be a command result, file state, UI behavior, API
  behavior, generated artifact property, manual inspection standard, numeric
  threshold, Boolean state, or review finding budget. It may live inside
  `Done when` or verification text; a separate `Metrics` section is not
  required.
- **Verification fit**: The named checks can actually prove the `Done when` and
  hard acceptance conditions, rather than only proving unrelated health.
- **Target fidelity**: The plan preserves the approved target, template,
  mockup, example, behavior, or quality bar unless a narrower target is called
  out for user approval.
- **Optimization and review criteria**: Refactor, optimization, cleanup, and
  review work names the comparison standard, budget, category, threshold, or
  finding policy that makes success decidable.
- **Dependencies**: Required inputs, prior work, tools, credentials,
  environments, external services, and user approvals are visible when they
  affect execution.
- **Sequencing**: Prerequisites appear before dependent work. Risky,
  destructive, remote, or broad changes are behind validation or approval.
- **Risk and stop conditions**: Known assumptions, blockers, fallback behavior,
  and stop points are explicit enough that the executor does not have to guess.
- **Exit criteria**: The plan says what final state, report, unresolved issue,
  skipped check, or handoff must exist at the end.
- **Verification boundary**: The plan distinguishes real checks from generated
  state, seeded fixtures, scripted shortcuts, screenshots, notes, or claims.
- **Review boundary**: Reviewing the plan must not itself require modifying
  files, changing workflow state, committing, deploying, or performing the work.

## Plain Plan Checks

- **Actionability**: Another agent can execute the plan without inventing the
  architecture, ownership boundaries, interfaces, or acceptance criteria.
- **Right-sized workflow**: The plan makes clear whether ordinary execution is
  enough or whether the task should use `$roadmap` or `$program`.
- **Surface intent**: Important files, APIs, schemas, commands, UI surfaces,
  documents, or artifacts are named when they materially affect implementation.
- **Unit acceptance**: If the plan is split into phases, milestones, versions,
  or tasks, each unit has its own `Done when` and hard acceptance condition.
- **Approval boundary**: Broad refactors, destructive operations, new
  dependencies, remote writes, deployments, and scope reductions have explicit
  user approval points.
- **Fallback behavior**: The plan says what to do if a fact is missing, a
  dependency is unavailable, or verification fails.

### Plain Plan P0 Rules

Treat a plain-plan finding as `P0` when any of these apply:

- The goal or scope is too vague to execute safely.
- A required executable unit lacks observable `Done when`.
- A required executable unit lacks a concrete pass condition.
- Verification cannot prove the stated completion criteria.
- The plan requires a risky or destructive action without an approval boundary.

## Roadmap Checks

- **Version split**: Each version is independently reviewable and verifiable.
- **Version scope**: Each version has clear `In` and `Out` boundaries.
- **Version acceptance**: Each version has its own `Done when` and at least one
  hard acceptance condition tied to its goal.
- **Version verification**: Each version names runnable or inspectable checks
  that prove its acceptance criteria.
- **Version target fidelity**: Each version preserves any approved target or
  explicitly asks for approval to narrow it.
- **Version independence**: A version does not require uncommitted work from a
  later version to be accepted.
- **Status integrity**: The roadmap has one current version, coherent statuses,
  and no active/archived state confusion.
- **Commit boundary**: Each version can plausibly become one scoped commit
  without mixing unrelated implementation or workflow-state changes.
- **Review gates**: Subagent review, user approval, retry limits, blockers, and
  stop conditions are visible where the workflow requires them.

### Roadmap P0 Rules

Treat a roadmap finding as `P0` when any of these apply:

- Any version lacks observable `Done when`.
- Any version lacks a concrete pass condition.
- A version is too broad or coupled to be independently reviewed.
- Verification cannot prove a version's acceptance criteria.
- Roadmap state cannot identify the current version.
- Required review, approval, or stop behavior is missing.

## Program Checks

Review both structure and acceptance. A program can have valid state files and
still fail review if its child roadmaps do not prove the program goal.

- **Child roadmap split**: Child roadmaps are separated by coherent outcomes,
  not arbitrary file lists or hidden implementation layers.
- **Single active unit**: The program identifies exactly one active child
  roadmap when active state already exists.
- **Dependency order**: Child roadmap dependencies are explicit and ordered so
  prerequisites complete before dependent work starts.
- **Objective mapping**: Every material program goal and program-level
  `Done when` maps to child roadmap work or final verification.
- **Child version acceptance**: Every child roadmap version has its own
  `Done when`, hard acceptance condition, and verification.
- **Cross-roadmap contract**: Upstream outputs and downstream inputs are
  explicit for every dependency, including relevant interfaces, artifacts,
  state, configuration, migration result, or manual handoff.
- **Integration proof**: When child roadmaps must work together, the program
  includes final integration, smoke, end-to-end, or manual review verification.
- **Acceptance closure**: Child roadmap final checks and program final checks
  together prove the program-level completion criteria.
- **Global invariants**: Cross-roadmap constraints such as target fidelity,
  artifact format, performance budget, security assumption, compatibility, git
  boundary, and workflow-state rule remain protected throughout the program.
- **Failure policy**: The program says what happens if a child roadmap is
  blocked, a dependency changes, verification fails, or a target must be
  reduced.
- **Exit and archive behavior**: The program defines final status, final
  verification, unresolved issues, skipped checks, cleanup, and archive behavior
  when the workflow requires archiving.

### Program P0 Rules

Treat a program finding as `P0` when any of these apply:

- A material program goal does not map to child roadmap work or final
  verification.
- Any child roadmap version lacks observable `Done when`.
- Any child roadmap version lacks a concrete pass condition.
- Child roadmap completion does not prove program-level acceptance.
- A dependency lacks an upstream-output to downstream-input contract.
- Required cross-roadmap integration proof is missing.
- Program state cannot identify the single active child roadmap.
- Active and archived workflow state are mixed in a way that can mislead the
  next run.
- Blocking risks have no stop, repair, replan, or user-approval path.
