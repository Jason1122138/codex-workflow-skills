---
name: "plan-check"
description: "Use when the user explicitly invokes $plan-check or $plan-review, or asks to check, audit, review, or validate a plan before execution, including plain implementation plans, roadmap plans, and program plans."
---

# Plan Check

Use this skill to audit a plan before execution. It is a review gate: it does
not create the plan, execute the plan, update workflow state, or act as a hook.

`$plan-check` is not an active workflow. It does not claim repo/worktree root
ownership, create local workflow markers, or continue restricting execution
after the reviewed plan records `P0: none; P1: none` clearance. That clearance
only means the plan may go to human approval; it is not user approval.

## Entry Rules

- Treat `$plan-check` and `$plan-review` as explicit requests to use this skill.
- Use this skill when the user asks to check, audit, review, or validate a plan
  before execution.
- `$roadmap` and `$program` must use this skill as a preflight on complete draft
  plans before user approval or implementation.
- Read `references/checklist.md` every time, then apply the universal checks and
  the section for the detected plan type.
- Before outputting `Human Review HTML`, read
  `references/human-review-html.md` and follow its structure, language, and
  readiness rules.
- By default, write the same `Human Review HTML` to
  `plan-check-codex/human-review.html` in the current repo/worktree root.
- Default to review findings. Do not rewrite the plan unless the user explicitly
  asks for revised wording.

## Boundaries

Do not:

- execute the reviewed plan;
- edit plan files or source files;
- create or update roadmap or program state;
- stage, commit, push, deploy, or open pull requests;
- define or run hook gates;
- replace `$roadmap` or `$program` generation and execution workflows.

Allowed write:

- `plan-check-codex/human-review.html` only. This is a local preview artifact
  for human discussion. Overwrite it on each review, keep it out of git, and do
  not create a manifest or JSON approval record.

If the user asks to implement after review, finish the review first and report
whether the plan is ready for human approval.

## Plan Types

- **Plain plan**: prose, checklist, issue plan, TODO list, or implementation
  outline that is not in roadmap or program format.
- **Roadmap**: one goal split into independently reviewable versions.
- **Program**: one larger goal coordinated through multiple child roadmaps.

Read only the context needed to judge the plan: the plan text, active project
rules, directly referenced docs, and lightweight project facts needed to verify
feasibility. Avoid deep implementation research unless the plan cannot be
judged without it.

## Review Process

1. Classify the plan type.
2. Audit goal, scope, execution units, `Done when`, hard acceptance conditions,
   verification, dependencies, sequencing, risks, and exit criteria.
3. For roadmaps, review every version as its own executable unit.
4. For programs, review child roadmap structure, child version acceptance,
   cross-roadmap dependencies, and final program acceptance.
5. Assign severity and verdict from the strongest finding.
6. Add an `Approval Checklist` only when the plan is ready for human approval.
7. Include a self-contained `Human Review HTML` block when practical, using
   `references/human-review-html.md`.
8. Write the same HTML to `plan-check-codex/human-review.html` by default. If
   the file cannot be written, say so and still provide the text review; do not
   silently skip the artifact.

## Severity And Verdict

- `P0`: the plan cannot be safely executed or accepted as written.
- `P1`: the plan has a material gap that should be fixed before human approval.
- `P2`: the plan is usable, but a clarity or maintainability improvement would
  reduce friction.

Verdicts:

- `PASS`: no `P0` or `P1`; the plan may go to human approval.
- `CONCERNS`: findings exist. If they are only `P2`, the plan may still go to
  human approval. If any `P1` exists, fix the plan before human approval.
- `BLOCKED`: at least one `P0` exists; do not approve or execute the plan.

## Output Format

Write a concise text review first. Use the user's language for visible headings
and prose; the field names below define the required content:

```markdown
Verdict: PASS | CONCERNS | BLOCKED
Severity Summary: P0=<count>, P1=<count>, P2=<count>

Findings
- <P0 | P1 | P2> | <check name> | <basis from plan or project facts> | <impact>

Open Questions
- <only questions that materially affect verdict or next step, or "None">

Recommended Next Step
- <one concrete next step>

Approval Checklist
- [ ] <unit label>: <human approval item>
```

If there are no findings, write `Findings: None`.

If any `P0` or `P1` exists, do not output checkbox items. End with:

```markdown
Approval Checklist
- Not ready for human approval until P0/P1 findings are resolved.
```

For roadmap and program approval discussions, a hook prompt may remind the agent
to write `plan-check-codex/human-review.html` and include its path in the
response. Do not treat that file as a hook gate, manifest, or user approval.

## Approval Checklist Rules

- Output checklist items only for `PASS` or `CONCERNS` with `P2` findings only.
- Use one checkbox per independently reviewable execution unit.
- For a plain plan, use milestone or task labels.
- For a roadmap, use version labels.
- For a program, use child roadmap/version labels and a final program item when
  the program has overall acceptance criteria.
- Derive each item from the unit's `Done when` and hard acceptance condition.
- Keep each item short enough for a human to approve directly.
- Do not include real file paths, command logs, evidence catalogs, or source
  labels in the checklist.
- Do not use metric-owner wording. Say what must be true, not who owns it.
- Use the user's language for checklist items. Preserve technical identifiers,
  commands, file names, API names, and quoted text exactly.
- If a unit has no concrete `Done when` or hard acceptance condition, report it
  as a finding and mark the plan not ready for human approval.
- The HTML checklist follows the same readiness rule: checkbox inputs appear
  only for `PASS` or `CONCERNS` with `P2` findings only. For `P0` or `P1`, the
  HTML checklist section must say the user's-language equivalent of `Not ready
  for human approval until P0/P1 findings are resolved.`

## Rewrite Requests

When the user explicitly asks for suggested wording or a revised draft:

- keep findings first;
- add `Suggested Edits` after `Recommended Next Step`;
- preserve the user's workflow choice;
- do not silently convert a plain plan into `$roadmap` or `$program`.
