#!/usr/bin/env python3
"""Minimal public Codex hook for roadmap/program workflows."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROADMAP_DIR = "roadmap-codex"
PROGRAM_DIR = "program-codex"
PROGRAM_ACTIVE = "active"
PROGRAM_FILE = "PROGRAM.md"
PENDING = ".codex-pending-transition.json"
SCHEMA = "codex-roadmap-pending-transition.v1"

EVENT_NAMES = {
    "session-start": "SessionStart",
    "user-prompt-submit": "UserPromptSubmit",
    "pre-tool-use": "PreToolUse",
    "stop": "Stop",
}


@dataclass
class ActivePlan:
    index: Path
    plan: Path
    version: str
    slug: str
    status: str


@dataclass
class ProgramContext:
    path: Path
    program_id: str
    status: str
    approval: str
    active_roadmap: str
    active_roadmap_path: Path | None
    active_plan: ActivePlan | None
    conflicts: list[str]


@dataclass
class PendingStatus:
    marker: Path
    state: str
    workflow: str
    kind: str
    reason: str
    payload: dict[str, Any]


def main() -> int:
    event_key = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    event_name = EVENT_NAMES.get(event_key, event_key)
    data = read_input()
    root = find_root(Path(data.get("cwd") or os.getcwd()).resolve())
    try:
        if event_key == "session-start":
            return session_start(event_name, root)
        if event_key == "user-prompt-submit":
            return prompt_submit(event_name, root, extract_prompt(data))
        if event_key == "pre-tool-use":
            return pre_tool_use(event_name, root, extract_command(data))
        if event_key == "stop":
            return stop(event_name, root, str(data.get("last_assistant_message") or ""))
    except Exception as exc:
        emit(event_name, "[ROADMAP WARN]", f"Hook error: {type(exc).__name__}: {exc}", {"root": str(root)})
    return 0


def read_input() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
    return value if isinstance(value, dict) else {"value": value}


def run(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False).stdout.strip()
    except Exception:
        return ""


def find_root(cwd: Path) -> Path:
    git_root = run(["git", "rev-parse", "--show-toplevel"], cwd)
    if git_root:
        return Path(git_root).resolve()
    for path in [cwd, *cwd.parents]:
        if (path / ROADMAP_DIR).exists() or (path / PROGRAM_DIR).exists():
            return path
    return cwd


def session_start(event: str, root: Path) -> int:
    pending = find_pending(root)
    if pending:
        emit(event, "[PENDING TRANSITION REQUIRED]" if pending.state == "transition_required" else "[PENDING COMMIT OBSERVED]", pending_message(pending), pending_payload(pending))
        return 0

    program = find_program(root)
    if program:
        if program.status == "done":
            emit(event, "[PROGRAM ARCHIVE REQUIRED]", "Active program is Status: done. Close out program-codex/active/ before starting new work.", program_payload(program))
            return 0
        if program.conflicts:
            emit(event, "[PROGRAM CONFLICT]", "; ".join(program.conflicts), program_payload(program))
            return 0
        if program.active_plan:
            emit(event, "[PROGRAM CONTEXT]", f"Active roadmap {program.active_roadmap}, version {program.active_plan.version} ({program.active_plan.slug}), plan={program.active_plan.plan}.", program_payload(program))
            return 0
        emit(event, "[PROGRAM CONTEXT]", "program-codex/active/PROGRAM.md exists, but no active child roadmap version is in_progress.", program_payload(program))
        return 0

    completed = completed_roadmaps(root)
    if completed:
        emit(event, "[ROADMAP ARCHIVE REQUIRED]", "Completed roadmap phases remain at roadmap-codex/ root and must be closed out before new roadmap work.", {"root": str(root), "phases": [str(p) for p in completed]})
        return 0

    active = find_roadmap(root)
    if active:
        emit(event, "[ROADMAP CONTEXT]", f"Active roadmap version {active.version} ({active.slug}), status={active.status}, plan={active.plan}.", active_payload(active))
    return 0


def prompt_submit(event: str, root: Path, prompt: str) -> int:
    pending = find_pending(root)
    if pending and pending.state == "transition_required" and (looks_roadmap(prompt) or looks_program(prompt)):
        emit(event, "[PENDING TRANSITION REQUIRED]", pending_message(pending) + " Finish it before starting another workflow.", pending_payload(pending), "deny")
        return 0
    if looks_program(prompt):
        emit(event, "[PROGRAM ENFORCE]", "Before asking for approval or implementation, create the complete program draft, run $plan-check, record P0: none; P1: none, and show the human review checklist.", {"root": str(root)})
        return 0
    if looks_roadmap(prompt):
        emit(event, "[ROADMAP ENFORCE]", "Before asking for approval or implementation, create the complete roadmap draft, run $plan-check, record P0: none; P1: none, and show the human review checklist.", {"root": str(root)})
    return 0


def pre_tool_use(event: str, root: Path, command: str) -> int:
    if not command:
        return 0
    if not is_git_commit(command):
        return 0

    staged = staged_files(root)
    marker_files = [p for p in staged if p.endswith(PENDING)]
    if marker_files:
        emit(event, "[PENDING TRANSITION LOCAL STATE FAIL]", "Pending transition markers are local state and must not be committed: " + ", ".join(marker_files), {"staged_files": marker_files}, "deny")
        return 0
    program_files = [p for p in staged if p == PROGRAM_DIR or p.startswith(PROGRAM_DIR + "/")]
    if program_files:
        emit(event, "[PROGRAM LOCAL STATE FAIL]", "program-codex/ is local workflow state and must not be committed: " + ", ".join(program_files), {"staged_files": program_files}, "deny")
        return 0

    pending = find_pending(root)
    if pending and pending.state == "transition_required":
        emit(event, "[PENDING TRANSITION REQUIRED]", pending_message(pending) + " New commits are denied until this transition is consumed.", pending_payload(pending) | {"command": command}, "deny")
        return 0

    program = find_program(root)
    active = program.active_plan if program else find_roadmap(root)
    if not active:
        return 0
    msg = commit_message(command)
    if active.version not in msg:
        return 0

    verdict = os.environ.get("CODEX_ROADMAP_STUB_VERDICT", "").upper()
    if verdict == "FAIL":
        emit(event, "[ROADMAP VERIFIER FAIL]", "Stub verifier returned FAIL. Keep the version in_progress and repair the concrete failure.", active_payload(active), "deny")
        return 0
    if verdict != "PASS":
        emit(event, "[ROADMAP VERIFIER SKIPPED]", "No verifier verdict configured. Set CODEX_ROADMAP_STUB_VERDICT=PASS for smoke tests or configure an external verifier.", active_payload(active))
        return 0

    marker = write_pending(root, active, msg, program)
    label, message = transition_label_and_message(root, active, program)
    emit(event, label, message, {"marker": str(marker), "active": active_payload(active)})
    return 0


def stop(event: str, root: Path, message: str) -> int:
    pending = find_pending(root)
    if pending and pending.state == "transition_required":
        block(event, "[PENDING TRANSITION REQUIRED] " + pending_message(pending) + " Advance workflow state before final response.", pending_payload(pending))
        return 0
    program = find_program(root)
    if program and program.status == "done":
        block(event, "[PROGRAM ARCHIVE REQUIRED] Active program is done; close out program-codex/active/ before final response.", program_payload(program))
        return 0
    completed = completed_roadmaps(root)
    if completed:
        block(event, "[ROADMAP ARCHIVE REQUIRED] Completed roadmap phase remains at root; close it out before final response.", {"phases": [str(p) for p in completed]})
        return 0
    if asks_for_approval(message):
        issue = plan_review_issue(root)
        if issue:
            block(event, "[PLAN CHECK REQUIRED] " + issue, {"root": str(root)})
    return 0


def find_roadmap(root: Path) -> ActivePlan | None:
    base = root / ROADMAP_DIR
    if not base.is_dir():
        return None
    active: list[ActivePlan] = []
    for phase in sorted(p for p in base.iterdir() if p.is_dir() and p.name != "archive"):
        plan = active_from_index(phase / "index.md")
        if plan and plan.status == "in_progress":
            active.append(plan)
    return active[0] if len(active) == 1 else None


def active_from_index(index: Path) -> ActivePlan | None:
    if not index.is_file():
        return None
    text = index.read_text(errors="replace")
    current = field(text, "Current") or "v1"
    block = version_block(text, current)
    status = field(block, "Status") or ""
    slug = heading_slug(block, current)
    plan_rel = plan_link(block) or f"{current}-{slug}.md"
    return ActivePlan(index=index, plan=(index.parent / plan_rel).resolve(), version=current, slug=slug, status=status)


def find_program(root: Path) -> ProgramContext | None:
    path = root / PROGRAM_DIR / PROGRAM_ACTIVE / PROGRAM_FILE
    if not path.is_file():
        return None
    text = path.read_text(errors="replace")
    active_id = field(text, "Active roadmap") or ""
    status = field(text, "Status") or ""
    approval = field(text, "Approval") or ""
    program_id = field(text, "Program ID") or ""
    roadmap_path = child_roadmap_path(path.parent, text, active_id)
    active_plan = active_from_index(roadmap_path) if roadmap_path else None
    conflicts = []
    if active_id and not roadmap_path:
        conflicts.append(f"Active roadmap {active_id} path is missing.")
    return ProgramContext(path=path, program_id=program_id, status=status, approval=approval, active_roadmap=active_id, active_roadmap_path=roadmap_path, active_plan=active_plan, conflicts=conflicts)


def child_roadmap_path(active_root: Path, text: str, active_id: str) -> Path | None:
    if not active_id:
        return None
    pattern = re.compile(rf"^###\s+{re.escape(active_id)}\b(?P<body>.*?)(?=^###\s+|\Z)", re.M | re.S)
    match = pattern.search(text)
    if match:
        link = re.search(r"\[.*?\]\((.*?)\)", match.group("body"))
        if link:
            return (active_root / link.group(1)).resolve()
    guess = active_root / "roadmaps" / active_id / "index.md"
    matches = list((active_root / "roadmaps").glob(f"{active_id}*/index.md")) if (active_root / "roadmaps").is_dir() else []
    return matches[0].resolve() if matches else (guess.resolve() if guess.is_file() else None)


def completed_roadmaps(root: Path) -> list[Path]:
    base = root / ROADMAP_DIR
    if not base.is_dir():
        return []
    out = []
    for phase in sorted(p for p in base.iterdir() if p.is_dir() and p.name != "archive"):
        index = phase / "index.md"
        if index.is_file() and all_versions_done(index.read_text(errors="replace")):
            out.append(index)
    return out


def all_versions_done(text: str) -> bool:
    statuses = re.findall(r"^- \*\*Status\*\*:\s*(\S+)", text, re.M)
    return bool(statuses) and all(s == "done" for s in statuses)


def plan_review_issue(root: Path) -> str:
    program = find_program(root)
    if program and program.status == "draft" and not valid_plan_review(program.path.read_text(errors="replace")):
        return "Program draft needs a recorded $plan-check verdict with P0: none; P1: none before asking for approval."
    base = root / ROADMAP_DIR
    if base.is_dir():
        for index in sorted(base.glob("*/index.md")):
            if index.parent.name == "archive":
                continue
            text = index.read_text(errors="replace")
            if "not_started" in text and not valid_plan_review(text):
                return "Roadmap draft needs a recorded $plan-check verdict with P0: none; P1: none before asking for approval."
    return ""


def valid_plan_review(text: str) -> bool:
    value = field(text, "Plan review") or ""
    return "$plan-check" in value and "P0: none" in value and "P1: none" in value


def find_pending(root: Path) -> PendingStatus | None:
    candidates = []
    program_marker = root / PROGRAM_DIR / PROGRAM_ACTIVE / PENDING
    if program_marker.is_file():
        candidates.append(program_marker)
    roadmap_root = root / ROADMAP_DIR
    if roadmap_root.is_dir():
        candidates.extend(p for p in sorted(roadmap_root.glob(f"*/{PENDING}")) if p.parent.name != "archive")
    for marker in candidates:
        status = classify_pending(root, marker)
        if status.state == "cleared":
            try:
                marker.unlink()
            except OSError:
                pass
            continue
        return status
    return None


def classify_pending(root: Path, marker: Path) -> PendingStatus:
    try:
        payload = json.loads(marker.read_text())
    except Exception:
        payload = {}
    head_before = str(payload.get("head_before") or "")
    current = current_head(root)
    if head_before and current == head_before:
        return PendingStatus(marker, "pending_commit", str(payload.get("workflow") or ""), str(payload.get("kind") or ""), "commit has not been observed yet", payload)
    if transition_consumed(root, payload):
        return PendingStatus(marker, "cleared", str(payload.get("workflow") or ""), str(payload.get("kind") or ""), "state already advanced", payload)
    return PendingStatus(marker, "transition_required", str(payload.get("workflow") or ""), str(payload.get("kind") or ""), "commit observed but workflow state has not advanced", payload)


def transition_consumed(root: Path, payload: dict[str, Any]) -> bool:
    workflow = payload.get("workflow")
    kind = payload.get("kind")
    from_version = payload.get("from_version")
    to_version = payload.get("to_version")
    if workflow == "roadmap":
        phase_index = root / str(payload.get("phase_index") or "")
        if not phase_index.exists():
            return kind == "roadmap_completion"
        text = phase_index.read_text(errors="replace")
        if kind == "version_transition":
            return (field(text, "Current") == to_version) and version_status(text, from_version) == "done"
        if kind == "roadmap_completion":
            return all_versions_done(text)
    if workflow == "program":
        program = find_program(root)
        if not program:
            return kind == "program_completion"
        if kind == "version_transition" and program.active_plan:
            text = program.active_plan.index.read_text(errors="replace")
            return (field(text, "Current") == to_version) and version_status(text, from_version) == "done"
        if kind == "program_transition":
            return program.active_roadmap == payload.get("to_roadmap")
        if kind == "program_completion":
            return program.status == "done"
    return False


def write_pending(root: Path, active: ActivePlan, msg: str, program: ProgramContext | None) -> Path:
    next_version = next_version_after(active.index, active.version)
    if program:
        workflow = "program"
        marker = root / PROGRAM_DIR / PROGRAM_ACTIVE / PENDING
        next_roadmap = next_program_roadmap(program)
        if next_version:
            kind = "version_transition"
        elif next_roadmap:
            kind = "program_transition"
        else:
            kind = "program_completion"
        payload = {
            "schema": SCHEMA,
            "workflow": workflow,
            "kind": kind,
            "head_before": current_head(root),
            "commit_message": msg,
            "phase_index": rel(root, active.index),
            "from_version": active.version,
            "to_version": next_version or "",
            "program_id": program.program_id,
            "from_roadmap": program.active_roadmap,
            "to_roadmap": next_roadmap or "",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    else:
        marker = active.index.parent / PENDING
        kind = "version_transition" if next_version else "roadmap_completion"
        payload = {
            "schema": SCHEMA,
            "workflow": "roadmap",
            "kind": kind,
            "head_before": current_head(root),
            "commit_message": msg,
            "phase_index": rel(root, active.index),
            "from_version": active.version,
            "to_version": next_version or "",
            "program_id": "",
            "from_roadmap": "",
            "to_roadmap": "",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return marker


def transition_label_and_message(root: Path, active: ActivePlan, program: ProgramContext | None) -> tuple[str, str]:
    next_version = next_version_after(active.index, active.version)
    if program:
        if next_version:
            return "[ROADMAP VERSION TRANSITION REQUIRED]", f"After commit succeeds, mark {active.version} done and activate {next_version} in child roadmap {program.active_roadmap}."
        next_roadmap = next_program_roadmap(program)
        if next_roadmap:
            return "[PROGRAM TRANSITION REQUIRED]", f"After commit succeeds, record final verification, mark {program.active_roadmap} done, and activate {next_roadmap}."
        return "[PROGRAM COMPLETION REQUIRED]", "After commit succeeds, record final verification, mark the program done, and close out program-codex/active/."
    if next_version:
        return "[ROADMAP VERSION TRANSITION REQUIRED]", f"After commit succeeds, mark {active.version} done and activate {next_version}."
    return "[ROADMAP COMPLETION REQUIRED]", "After commit succeeds, mark the final version done and close out the completed roadmap phase."


def next_program_roadmap(program: ProgramContext) -> str:
    text = program.path.read_text(errors="replace")
    ids = re.findall(r"^###\s+(R\d{3}[-\w]*)", text, re.M)
    if program.active_roadmap in ids:
        idx = ids.index(program.active_roadmap)
        if idx + 1 < len(ids):
            return ids[idx + 1]
    return ""


def pending_message(status: PendingStatus) -> str:
    return f"{status.workflow or 'workflow'} marker {status.marker} is {status.state}: {status.reason}."


def pending_payload(status: PendingStatus) -> dict[str, Any]:
    return {"marker": str(status.marker), "state": status.state, "workflow": status.workflow, "kind": status.kind, "reason": status.reason}


def extract_prompt(data: dict[str, Any]) -> str:
    value = data.get("prompt") or data.get("user_prompt") or ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def extract_command(data: dict[str, Any]) -> str:
    tool_input = data.get("tool_input")
    if isinstance(tool_input, dict):
        value = tool_input.get("command")
        return value if isinstance(value, str) else ""
    return ""


def looks_roadmap(prompt: str) -> bool:
    low = prompt.lower()
    return "$roadmap" in low or "/roadmap" in low or "roadmap workflow" in low


def looks_program(prompt: str) -> bool:
    low = prompt.lower()
    return "$program" in low or "/program" in low or "program workflow" in low


def asks_for_approval(message: str) -> bool:
    low = message.lower()
    return any(term in low for term in ["approve", "approval", "批准", "审批", "同意", "可以开始", "可以执行"])


def is_git_commit(command: str) -> bool:
    for segment in re.split(r"\s*(?:&&|\|\||[;|])\s*", command):
        try:
            parts = shlex.split(segment)
        except ValueError:
            continue
        if len(parts) >= 2 and parts[0] == "git" and parts[1] == "commit":
            return True
    return False


def commit_message(command: str) -> str:
    try:
        parts = shlex.split(command)
    except ValueError:
        return command
    for i, part in enumerate(parts):
        if part in {"-m", "--message"} and i + 1 < len(parts):
            return parts[i + 1]
        if part.startswith("--message="):
            return part.split("=", 1)[1]
    return command


def staged_files(root: Path) -> list[str]:
    out = run(["git", "diff", "--cached", "--name-only"], root)
    return [line for line in out.splitlines() if line]


def current_head(root: Path) -> str:
    return run(["git", "rev-parse", "--verify", "HEAD"], root) or "unborn"


def rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def field(text: str, name: str) -> str:
    match = re.search(rf"^\s*(?:-\s*)?\*\*{re.escape(name)}\*\*:\s*(.*?)\s*$", text, re.M)
    return match.group(1).strip() if match else ""


def version_block(text: str, version: str) -> str:
    match = re.search(rf"^##\s+{re.escape(version)}:\s*.*?(?=^##\s+v\d+|\Z)", text, re.M | re.S)
    return match.group(0) if match else ""


def heading_slug(block: str, version: str) -> str:
    match = re.search(rf"^##\s+{re.escape(version)}:\s*(.+)$", block, re.M)
    return match.group(1).strip() if match else version


def plan_link(block: str) -> str:
    match = re.search(r"^- \*\*Plan\*\*:\s*\[.*?\]\((.*?)\)", block, re.M)
    return match.group(1).strip().lstrip("./") if match else ""


def version_status(text: str, version: str) -> str:
    return field(version_block(text, str(version)), "Status")


def next_version_after(index: Path, version: str) -> str:
    text = index.read_text(errors="replace") if index.is_file() else ""
    versions = re.findall(r"^##\s+(v\d+):", text, re.M)
    if version in versions:
        i = versions.index(version)
        if i + 1 < len(versions):
            return versions[i + 1]
    return ""


def active_payload(active: ActivePlan) -> dict[str, str]:
    return {"index": str(active.index), "plan": str(active.plan), "version": active.version, "slug": active.slug, "status": active.status}


def program_payload(program: ProgramContext) -> dict[str, Any]:
    payload: dict[str, Any] = {"path": str(program.path), "program_id": program.program_id, "status": program.status, "approval": program.approval, "active_roadmap": program.active_roadmap, "conflicts": program.conflicts}
    if program.active_roadmap_path:
        payload["active_roadmap_path"] = str(program.active_roadmap_path)
    if program.active_plan:
        payload["active_plan"] = active_payload(program.active_plan)
    return payload


def emit(event: str, label: str, message: str, payload: dict[str, Any], decision: str | None = None) -> None:
    out: dict[str, Any] = {"hookSpecificOutput": {"hookEventName": event, "additionalContext": f"{label} {message}", "payload": payload}}
    if decision:
        out["hookSpecificOutput"]["permissionDecision"] = decision
    print(json.dumps(out, ensure_ascii=False))


def block(event: str, reason: str, payload: dict[str, Any]) -> None:
    print(json.dumps({"decision": "block", "reason": reason, "payload": payload}, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
