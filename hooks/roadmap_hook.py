#!/usr/bin/env python3
"""Codex roadmap workflow hook entrypoint.

This script is intentionally small and conservative. It supports the standard
global Codex roadmap workflow and remains compatible with project-local assets.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


HOOK_EVENT_NAMES = {
    "session-start": "SessionStart",
    "user-prompt-submit": "UserPromptSubmit",
    "pre-tool-use": "PreToolUse",
}

ROADMAP_DIR_NAME = "roadmap-codex"
PROGRAM_DIR_NAME = "program-codex"
PROGRAM_FILE_NAME = "PROGRAM.md"


@dataclass
class ActivePlan:
    phase_index: Path
    plan_path: Path
    version: str
    slug: str
    status: str


@dataclass
class ProgramRoadmap:
    roadmap_id: str
    goal: str
    path: Path
    status: str
    priority: str
    depends_on: list[str]
    final_verification: str


@dataclass
class ProgramContext:
    program_path: Path
    active_roadmap_id: str
    active_roadmap: ProgramRoadmap | None
    active_plan: ActivePlan | None
    roadmaps: dict[str, ProgramRoadmap]
    conflicts: list[str]


def main() -> int:
    if os.environ.get("CODEX_ROADMAP_HOOK_SKIP") == "1":
        return 0

    event_key = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    event_name = HOOK_EVENT_NAMES.get(event_key, event_key)
    hook_input = read_hook_input()
    cwd = Path(hook_input.get("cwd") or os.getcwd()).resolve()
    root = find_project_root(cwd)
    log_hook_seen(event_name, root, hook_input)

    try:
        if event_key == "session-start":
            return handle_session_start(event_name, root)
        if event_key == "user-prompt-submit":
            return handle_user_prompt_submit(event_name, hook_input, root)
        if event_key == "pre-tool-use":
            return handle_pre_tool_use(event_name, hook_input, root)
        return 0
    except Exception as exc:  # Hook bugs must not trap the user.
        emit_context(
            event_name,
            "[ROADMAP WARN]",
            f"Roadmap hook error: {type(exc).__name__}: {exc}",
            {"root": str(root)},
        )
        return 0


def read_hook_input() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
    return value if isinstance(value, dict) else {"value": value}


def find_project_root(cwd: Path) -> Path:
    git_root = run_text(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    if git_root:
        return Path(git_root.strip()).resolve()

    for path in [cwd, *cwd.parents]:
        if (
            (path / ".codex").exists()
            or (path / PROGRAM_DIR_NAME).exists()
            or (path / ROADMAP_DIR_NAME).exists()
        ):
            return path
    return cwd


def handle_session_start(event_name: str, root: Path) -> int:
    program = find_program_context(root)
    if program:
        if program.conflicts:
            emit_additional_context(
                event_name,
                "[PROGRAM CONFLICT]",
                "; ".join(program.conflicts),
                program_payload(program),
            )
            return 0
        if program.active_plan and program.active_roadmap:
            emit_additional_context(
                event_name,
                "[PROGRAM CONTEXT]",
                (
                    f"Active roadmap: {program.active_roadmap.roadmap_id}, "
                    f"active version: {program.active_plan.version} "
                    f"({program.active_plan.slug}), plan={program.active_plan.plan_path}. "
                    "Run per-version subagent review before completing it with "
                    "one scoped roadmap commit."
                ),
                program_payload(program),
            )
            return 0
        emit_additional_context(
            event_name,
            "[PROGRAM CONTEXT]",
            (
                "program-codex/PROGRAM.md is present, but no active child "
                "roadmap version is in_progress. Do not fall back to legacy "
                "roadmap-codex/ while program state exists."
            ),
            program_payload(program),
        )
        return 0

    active = find_active_plan(root)
    if not active:
        return 0

    emit_additional_context(
        event_name,
        "[ROADMAP CONTEXT]",
        (
            f"Active roadmap version: {active.version} ({active.slug}), "
            f"status={active.status}, plan={active.plan_path}. "
            'Read "Done when" before editing. Run per-version subagent review, '
            "then complete this version with one scoped git commit before advancing."
        ),
        active_payload(active),
    )
    return 0


def handle_user_prompt_submit(
    event_name: str, hook_input: dict[str, Any], root: Path
) -> int:
    prompt = extract_prompt(hook_input)
    if looks_like_program_request(prompt):
        emit_additional_context(
            event_name,
            "[PROGRAM ENFORCE]",
            (
                "Program request detected. Use program-codex/PROGRAM.md and "
                "program-codex/roadmaps/RNNN-<slug>/ child roadmaps; call "
                "subagent design/state reviews with retry cap 2; run per-version "
                "subagent review inside every child roadmap; if root PROGRAM.md "
                "already exists, continue it, archive it, block/pause it, or "
                "explicitly overwrite it before creating a new program."
            ),
            {"root": str(root), "prompt_excerpt": prompt[:200]},
        )
        return 0

    if not looks_like_roadmap_request(prompt):
        return 0

    emit_additional_context(
        event_name,
        "[ROADMAP ENFORCE]",
        (
            "Roadmap request detected. Write roadmap files instead of only "
            "describing them; use observable Done when items; verify file names "
            "under roadmap-codex/ after writing; wait for user approval before implementation; "
            "after approval, execute the planned phase until complete or blocked; "
            "run subagent review for every version before its scoped git commit."
        ),
        {"root": str(root), "prompt_excerpt": prompt[:200]},
    )
    return 0


def handle_pre_tool_use(
    event_name: str, hook_input: dict[str, Any], root: Path
) -> int:
    command = extract_bash_command(hook_input)
    if not is_git_commit_command(command):
        return 0

    program = find_program_context(root)
    if program:
        legacy_active = find_active_plan(root)
        if legacy_active:
            emit_context(
                event_name,
                "[PROGRAM CONFLICT]",
                (
                    "program-codex/ is active while legacy roadmap-codex/ also "
                    "has an in_progress roadmap. Pause or finish one workflow "
                    "before committing."
                ),
                program_payload(program) | {"legacy_active": active_payload(legacy_active)},
                "deny",
            )
            return 0

        if program.conflicts:
            emit_context(
                event_name,
                "[PROGRAM CONFLICT]",
                "; ".join(program.conflicts),
                program_payload(program),
                "deny",
            )
            return 0

        if is_program_state_commit(root, command):
            result = validate_program_state_gate(root, program, command)
            verdict = result["verdict"]
            permission = "deny" if verdict == "FAIL" else None
            emit_context(
                event_name,
                f"[PROGRAM STATE {verdict}]",
                result["message"],
                program_payload(program) | {"state_gate": result, "command": command},
                permission,
            )
            return 0

        staged = staged_files(root)
        if staged and all(is_program_state_path(path) for path in staged):
            emit_context(
                event_name,
                "[PROGRAM STATE FAIL]",
                (
                    "Only program state files are staged, but the commit message "
                    "does not start with `program:`."
                ),
                program_payload(program) | {"command": command, "staged_files": staged},
                "deny",
            )
            return 0

        if not program.active_plan:
            emit_context(
                event_name,
                "[PROGRAM CONFLICT]",
                "No active child roadmap version was found for the active program roadmap.",
                program_payload(program),
                "deny",
            )
            return 0

        return run_version_gate(event_name, root, program.active_plan, command, program)

    if not (root / ROADMAP_DIR_NAME).is_dir():
        return 0

    active = find_active_plan(root)
    if not active:
        emit_context(
            event_name,
            "[ROADMAP WARN]",
            "git commit detected, but no active in_progress roadmap plan was found.",
            {"root": str(root), "command": command},
        )
        return 0

    return run_version_gate(event_name, root, active, command)


def run_version_gate(
    event_name: str,
    root: Path,
    active: ActivePlan,
    command: str,
    program: ProgramContext | None = None,
) -> int:
    result = run_verifier(root, active, command)
    verdict = result.get("verdict", "WARN")
    label = f"[ROADMAP VERIFIER {verdict}]"
    message = result.get("message") or f"Verifier returned {verdict}."
    if verdict == "PASS":
        message = (
            f"{message} After the commit succeeds, mark this version done "
            "and advance to the next planned version unless a stop condition applies."
        )

    retry_update = None
    if verdict == "FAIL" and os.environ.get("CODEX_ROADMAP_UPDATE_RETRY") == "1":
        retry_update = update_retry_state(active, result)
        message = f"{message} {retry_update['message']}"

    payload = active_payload(active) | {
        "command": command,
        "verifier": result,
    }
    if program:
        payload["program"] = program_payload(program)
    if retry_update:
        payload["retry_update"] = retry_update

    permission_decision = None
    if verdict == "FAIL":
        permission_decision = "deny"

    emit_context(event_name, label, message, payload, permission_decision)

    if verdict == "FAIL" and os.environ.get("CODEX_ROADMAP_FAIL_EXIT"):
        return int(os.environ["CODEX_ROADMAP_FAIL_EXIT"])
    return 0


def run_verifier(root: Path, active: ActivePlan, command: str) -> dict[str, Any]:
    stub = os.environ.get("CODEX_ROADMAP_STUB_VERDICT")
    if stub:
        verdict = stub.upper()
        return {
            "mode": "stub",
            "verdict": verdict,
            "message": os.environ.get(
                "CODEX_ROADMAP_STUB_MESSAGE",
                f"Stub verifier returned {verdict} for {active.plan_path.name}.",
            ),
            "criteria": [{"text": "stub", "satisfied": verdict == "PASS", "evidence": "env"}],
        }

    if os.environ.get("CODEX_ROADMAP_RUN_CODEX_EXEC") != "1":
        return {
            "mode": "disabled",
            "verdict": "WARN",
            "message": (
                "git commit detected, but CODEX_ROADMAP_RUN_CODEX_EXEC is not enabled. "
                "Run the verifier manually or enable it after smoke testing."
            ),
        }

    prompt = build_verifier_prompt(root, active, command)
    schema = roadmap_assets_dir(root) / "verifier.schema.json"
    with tempfile.NamedTemporaryFile(
        "w+", prefix="codex-roadmap-verdict-", suffix=".json", delete=False
    ) as verdict_file:
        verdict_path = Path(verdict_file.name)

    cmd = [
        "codex",
        "exec",
        "--sandbox",
        "read-only",
        "--dangerously-bypass-hook-trust",
        "--skip-git-repo-check",
        "--output-schema",
        str(schema),
        "-o",
        str(verdict_path),
        prompt,
    ]
    env = os.environ.copy()
    env["CODEX_ROADMAP_HOOK_SKIP"] = "1"
    completed = subprocess.run(
        cmd,
        cwd=root,
        text=True,
        capture_output=True,
        env=env,
        timeout=int(os.environ.get("CODEX_ROADMAP_VERIFIER_TIMEOUT", "120")),
        check=False,
    )

    if completed.returncode != 0:
        return {
            "mode": "codex-exec",
            "verdict": "WARN",
            "message": f"codex exec verifier exited {completed.returncode}: {completed.stderr[-500:]}",
        }

    try:
        return json.loads(verdict_path.read_text())
    except Exception as exc:
        return {
            "mode": "codex-exec",
            "verdict": "WARN",
            "message": f"Could not parse verifier output: {type(exc).__name__}: {exc}",
        }


def build_verifier_prompt(root: Path, active: ActivePlan, command: str) -> str:
    plan = active.plan_path.read_text()
    candidate = build_candidate_view(root)
    verifier_prompt = load_verifier_prompt(root)
    return (
        f"{verifier_prompt}\\n\\n"
        f"Active plan path: {active.plan_path}\\n"
        f"Bash command: {command}\\n\\n"
        "## Plan\\n"
        f"{plan}\\n\\n"
        "## Commit candidate\\n"
        f"{candidate}"
    )


def load_verifier_prompt(root: Path) -> str:
    prompt_path = roadmap_assets_dir(root) / "verifier-prompt.md"
    try:
        text = prompt_path.read_text().strip()
    except OSError:
        text = ""
    if text:
        return text
    return (
        "You are a verifier. Decide whether the commit candidate satisfies the "
        "active roadmap version's Done when checklist. Return JSON only."
    )


def build_candidate_view(root: Path) -> str:
    parts = []
    for title, args in [
        ("staged diff", ["git", "diff", "--cached"]),
        ("worktree diff", ["git", "diff"]),
        ("untracked files", ["git", "ls-files", "--others", "--exclude-standard"]),
    ]:
        value = run_text(args, cwd=root)
        parts.append(f"## {title}\\n{value or '(empty)'}")
    return "\\n\\n".join(parts)


def roadmap_assets_dir(root: Path) -> Path:
    configured = os.environ.get("CODEX_ROADMAP_ASSETS_DIR")
    if configured:
        return Path(configured).expanduser().resolve()

    project_assets = root / ".codex" / "roadmap"
    if project_assets.is_dir():
        return project_assets

    return (Path.home() / ".codex" / "roadmap").resolve()


def find_program_context(root: Path) -> ProgramContext | None:
    program_path = root / PROGRAM_DIR_NAME / PROGRAM_FILE_NAME
    if not program_path.is_file():
        return None

    active_roadmap_id, roadmaps = parse_program_file(program_path)
    conflicts: list[str] = []

    if not active_roadmap_id:
        conflicts.append("PROGRAM.md does not declare **Active roadmap**.")

    in_progress = [
        item.roadmap_id for item in roadmaps.values() if item.status == "in_progress"
    ]
    if len(in_progress) > 1:
        conflicts.append(f"Multiple program roadmaps are in_progress: {', '.join(in_progress)}.")

    active_roadmap = roadmaps.get(active_roadmap_id) if active_roadmap_id else None
    if active_roadmap_id and not active_roadmap:
        conflicts.append(f"Active roadmap {active_roadmap_id} is not listed in PROGRAM.md.")

    active_plan = None
    if active_roadmap:
        if not active_roadmap.path.is_file():
            conflicts.append(
                f"Active roadmap path is missing: {active_roadmap.path}."
            )
        else:
            active_versions = find_in_progress_versions(active_roadmap.path)
            if len(active_versions) > 1:
                conflicts.append(
                    "Active child roadmap has multiple in_progress versions: "
                    + ", ".join(active_versions)
                    + "."
                )
            elif active_roadmap.status == "in_progress":
                active_plan = parse_phase_index(active_roadmap.path)
                if not active_plan:
                    conflicts.append(
                        f"Active roadmap {active_roadmap.roadmap_id} has no active version."
                    )

    return ProgramContext(
        program_path=program_path,
        active_roadmap_id=active_roadmap_id,
        active_roadmap=active_roadmap,
        active_plan=active_plan,
        roadmaps=roadmaps,
        conflicts=conflicts,
    )


def parse_program_file(program_path: Path) -> tuple[str, dict[str, ProgramRoadmap]]:
    return parse_program_text(program_path, program_path.read_text())


def parse_program_text(
    program_path: Path, text: str
) -> tuple[str, dict[str, ProgramRoadmap]]:
    active_roadmap_id = ""
    sections: dict[str, dict[str, str]] = {}
    current = None

    for line in text.splitlines():
        active_match = re.match(r"^\*\*Active roadmap\*\*:\s*(.+?)\s*$", line)
        if active_match:
            active_roadmap_id = active_match.group(1).strip()
            continue

        section_match = re.match(r"^###\s+(R\d{3}-[A-Za-z0-9._-]+)\s*$", line)
        if section_match:
            current = section_match.group(1)
            sections[current] = {}
            continue

        if not current:
            continue

        field_match = re.match(r"^-\s+\*\*(.+?)\*\*:\s*(.*)$", line)
        if not field_match:
            continue
        key = field_match.group(1).strip().lower()
        value = field_match.group(2).strip()
        sections[current][key] = value

    roadmaps: dict[str, ProgramRoadmap] = {}
    for roadmap_id, data in sections.items():
        path_value = data.get("path", "")
        link_match = re.search(r"\(([^)]+)\)", path_value)
        rel_path = link_match.group(1) if link_match else path_value
        depends_raw = data.get("depends on", "none")
        depends_on = [
            item.strip()
            for item in re.split(r"[, ]+", depends_raw)
            if item.strip() and item.strip().lower() != "none"
        ]
        roadmaps[roadmap_id] = ProgramRoadmap(
            roadmap_id=roadmap_id,
            goal=data.get("goal", ""),
            path=(program_path.parent / rel_path).resolve(),
            status=data.get("status", ""),
            priority=data.get("priority", ""),
            depends_on=depends_on,
            final_verification=data.get("final verification", ""),
        )

    return active_roadmap_id, roadmaps


def find_in_progress_versions(index: Path) -> list[str]:
    return find_in_progress_versions_text(index.read_text())


def find_in_progress_versions_text(text: str) -> list[str]:
    versions = []
    active_version = None
    for line in text.splitlines():
        section_match = re.match(r"^## (v\d+):", line)
        if section_match:
            active_version = section_match.group(1)
            continue
        if active_version and re.match(r"^- \*\*Status\*\*: in_progress\s*$", line):
            versions.append(active_version)
    return versions


def all_versions_done(index: Path) -> bool:
    return all_versions_done_text(index.read_text())


def all_versions_done_text(text: str) -> bool:
    statuses = []
    for line in text.splitlines():
        status_match = re.match(r"^- \*\*Status\*\*: (\w+)", line)
        if status_match:
            statuses.append(status_match.group(1))
    return bool(statuses) and all(status == "done" for status in statuses)


def is_program_state_commit(root: Path, command: str) -> bool:
    message = extract_commit_message(command)
    return message.startswith("program:")


def validate_program_state_gate(
    root: Path, program: ProgramContext, command: str
) -> dict[str, Any]:
    message = extract_commit_message(command)
    completed_id, next_id = parse_program_state_message(message)
    failures = []
    staged = staged_files(root)
    program_rel = f"{PROGRAM_DIR_NAME}/{PROGRAM_FILE_NAME}"
    candidate_program_text = staged_file_text(root, program_rel)
    if program_rel not in staged or candidate_program_text is None:
        failures.append("PROGRAM.md must be staged for a program state transition.")

    previous_program_text = head_file_text(root, program_rel)
    if previous_program_text is None:
        failures.append(
            "Previous PROGRAM.md is not available in HEAD; cannot validate the previous active roadmap."
        )

    previous_active = ""
    if previous_program_text:
        previous_active, _ = parse_program_text(
            root / PROGRAM_DIR_NAME / PROGRAM_FILE_NAME, previous_program_text
        )

    candidate_active = ""
    candidate_roadmaps: dict[str, ProgramRoadmap] = {}
    if candidate_program_text:
        candidate_active, candidate_roadmaps = parse_program_text(
            root / PROGRAM_DIR_NAME / PROGRAM_FILE_NAME, candidate_program_text
        )

    unstaged_state = unstaged_program_state_files(root)
    if unstaged_state:
        failures.append(
            "Program state files have unstaged changes; stage or discard them before committing: "
            + ", ".join(unstaged_state)
            + "."
        )

    if not completed_id or not next_id:
        failures.append(
            "Program state commit message must match: "
            "program: complete R001-<slug> and activate R002-<slug>."
        )

    completed = candidate_roadmaps.get(completed_id) if completed_id else None
    next_roadmap = candidate_roadmaps.get(next_id) if next_id else None
    if completed_id and not completed:
        failures.append(f"Completed roadmap {completed_id} is not listed in staged PROGRAM.md.")
    if next_id and not next_roadmap:
        failures.append(f"Next roadmap {next_id} is not listed in staged PROGRAM.md.")

    if completed_id and previous_active and completed_id != previous_active:
        failures.append(
            f"Commit message completes {completed_id}, but previous active roadmap was {previous_active}."
        )

    allowed: set[str] = {f"{PROGRAM_DIR_NAME}/{PROGRAM_FILE_NAME}"}
    if completed:
        allowed.add(relative_to_root(root, completed.path))
    if next_roadmap:
        allowed.add(relative_to_root(root, next_roadmap.path))

    if not staged:
        failures.append("No staged files were found for the program state commit.")
    extra = [path for path in staged if path not in allowed]
    if extra:
        failures.append(
            "Program state commits may only include program state files; extra staged files: "
            + ", ".join(extra)
            + "."
        )

    if completed:
        if completed.status != "done":
            failures.append(f"{completed.roadmap_id} must be marked done in staged PROGRAM.md.")
        if not completed.final_verification or completed.final_verification == "-":
            failures.append(
                f"{completed.roadmap_id} must record Final verification before transition."
            )
        completed_index_text = candidate_file_text(root, relative_to_root(root, completed.path))
        if completed_index_text and not all_versions_done_text(completed_index_text):
            failures.append(f"{completed.roadmap_id} still has unfinished versions.")
        elif completed_index_text is None:
            failures.append(f"{completed.roadmap_id} index file is missing from the commit candidate.")

    if next_roadmap:
        if next_roadmap.status != "in_progress":
            failures.append(f"{next_roadmap.roadmap_id} must be marked in_progress.")
        if candidate_active != next_roadmap.roadmap_id:
            failures.append(
                "Staged PROGRAM.md Active roadmap must point to the next roadmap "
                f"{next_roadmap.roadmap_id}."
            )
        unmet = [
            dep
            for dep in next_roadmap.depends_on
            if dep in candidate_roadmaps and candidate_roadmaps[dep].status != "done"
        ]
        unknown = [dep for dep in next_roadmap.depends_on if dep not in candidate_roadmaps]
        if unmet:
            failures.append(
                f"{next_roadmap.roadmap_id} has unmet dependencies: {', '.join(unmet)}."
            )
        if unknown:
            failures.append(
                f"{next_roadmap.roadmap_id} has unknown dependencies: {', '.join(unknown)}."
            )

    if failures:
        return {
            "verdict": "FAIL",
            "message": " ".join(failures),
            "staged_files": staged,
            "allowed_files": sorted(allowed),
        }

    return {
        "verdict": "PASS",
        "message": (
            f"Program state transition is valid: {completed_id} done, "
            f"{next_id} active."
        ),
        "staged_files": staged,
        "allowed_files": sorted(allowed),
    }


def parse_program_state_message(message: str) -> tuple[str, str]:
    match = re.match(
        r"^program:\s+complete\s+(R\d{3}-[A-Za-z0-9._-]+)\s+and\s+activate\s+"
        r"(R\d{3}-[A-Za-z0-9._-]+)\s*$",
        message,
    )
    if not match:
        return "", ""
    return match.group(1), match.group(2)


def staged_files(root: Path) -> list[str]:
    value = run_text(["git", "diff", "--cached", "--name-only"], cwd=root)
    return [line.strip() for line in value.splitlines() if line.strip()]


def unstaged_program_state_files(root: Path) -> list[str]:
    value = run_text(["git", "diff", "--name-only"], cwd=root)
    return sorted(
        line.strip()
        for line in value.splitlines()
        if line.strip() and is_program_state_path(line.strip())
    )


def staged_file_text(root: Path, rel_path: str) -> str | None:
    value = run_text(["git", "show", f":{rel_path}"], cwd=root)
    return value if value else None


def head_file_text(root: Path, rel_path: str) -> str | None:
    value = run_text(["git", "show", f"HEAD:{rel_path}"], cwd=root)
    return value if value else None


def candidate_file_text(root: Path, rel_path: str) -> str | None:
    if rel_path in staged_files(root):
        return staged_file_text(root, rel_path)
    return head_file_text(root, rel_path)


def is_program_state_path(path: str) -> bool:
    if path == f"{PROGRAM_DIR_NAME}/{PROGRAM_FILE_NAME}":
        return True
    return bool(
        re.match(
            rf"^{re.escape(PROGRAM_DIR_NAME)}/roadmaps/R\d{{3}}-[^/]+/index\.md$",
            path,
        )
    )


def relative_to_root(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def extract_commit_message(command: str) -> str:
    try:
        parts = shlex.split(command)
    except ValueError:
        quoted = re.search(r"-m\s+(['\"])(.*?)\1", command)
        return quoted.group(2) if quoted else ""

    message = ""
    for i, part in enumerate(parts):
        if part in {"-m", "--message"} and i + 1 < len(parts):
            message = parts[i + 1]
        elif part.startswith("--message="):
            message = part.split("=", 1)[1]
    return message


def find_active_plan(root: Path) -> ActivePlan | None:
    roadmap = root / ROADMAP_DIR_NAME
    if not roadmap.is_dir():
        return None

    candidates: list[ActivePlan] = []
    for index in sorted(roadmap.glob("*/index.md")):
        parsed = parse_phase_index(index)
        if parsed:
            candidates.append(parsed)

    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        return None

    current_matches = [item for item in candidates if item.status == "in_progress"]
    return current_matches[0] if len(current_matches) == 1 else None


def update_retry_state(active: ActivePlan, result: dict[str, Any]) -> dict[str, Any]:
    plan_text = active.plan_path.read_text()
    retry_match = re.search(r"^- retry: (\d+)$", plan_text, flags=re.MULTILINE)
    retry = int(retry_match.group(1)) if retry_match else 0
    next_retry = retry + 1

    if retry_match:
        plan_text = re.sub(
            r"^- retry: \d+$",
            f"- retry: {next_retry}",
            plan_text,
            count=1,
            flags=re.MULTILINE,
        )
    elif "## Notes" in plan_text:
        plan_text = plan_text.rstrip() + f"\n- retry: {next_retry}\n"
    else:
        plan_text = plan_text.rstrip() + f"\n\n## Notes\n- retry: {next_retry}\n"

    blocked = next_retry >= 3
    if blocked:
        message = result.get("message", "Verifier failed at retry limit.")
        plan_text = plan_text.rstrip() + f"\n- blocker: {message}\n"
        set_version_status(active.phase_index, active.version, "blocked")

    active.plan_path.write_text(plan_text)

    return {
        "previous_retry": retry,
        "retry": next_retry,
        "blocked": blocked,
        "message": (
            f"Retry updated to {next_retry}; version blocked."
            if blocked
            else f"Retry updated to {next_retry}; version remains in_progress."
        ),
    }


def set_version_status(index: Path, version: str, status: str) -> None:
    lines = index.read_text().splitlines()
    in_target = False
    for i, line in enumerate(lines):
        section_match = re.match(r"^## (v\d+):", line)
        if section_match:
            in_target = section_match.group(1) == version
            continue
        if in_target and line.startswith("- **Status**: "):
            lines[i] = f"- **Status**: {status}"
            break
    index.write_text("\n".join(lines) + "\n")


def parse_phase_index(index: Path) -> ActivePlan | None:
    current = None
    sections: dict[str, dict[str, str]] = {}
    active_version = None

    for line in index.read_text().splitlines():
        current_match = re.match(r"^\*\*Current\*\*: (v\d+)", line)
        if current_match:
            current = current_match.group(1)
            continue

        section_match = re.match(r"^## (v\d+):\s*(.+)$", line)
        if section_match:
            active_version = section_match.group(1)
            sections[active_version] = {"slug": section_match.group(2).strip()}
            continue

        if not active_version:
            continue

        status_match = re.match(r"^- \*\*Status\*\*: (\w+)", line)
        if status_match:
            sections[active_version]["status"] = status_match.group(1)
            continue

        plan_match = re.match(r"^- \*\*Plan\*\*: \[[^\]]+\]\(([^)]+)\)", line)
        if plan_match:
            sections[active_version]["plan"] = plan_match.group(1)

    target_version = current if current in sections else None
    if not target_version:
        for version, data in sections.items():
            if data.get("status") == "in_progress":
                target_version = version
                break

    if not target_version:
        return None

    data = sections[target_version]
    if data.get("status") != "in_progress":
        return None

    plan_link = data.get("plan")
    if not plan_link:
        return None

    return ActivePlan(
        phase_index=index,
        plan_path=(index.parent / plan_link).resolve(),
        version=target_version,
        slug=data.get("slug", ""),
        status=data.get("status", ""),
    )


def extract_bash_command(hook_input: dict[str, Any]) -> str:
    paths = [
        ("tool_input", "command"),
        ("tool", "input", "command"),
        ("input", "command"),
        ("command",),
    ]
    for path in paths:
        value: Any = hook_input
        for key in path:
            if not isinstance(value, dict) or key not in value:
                value = None
                break
            value = value[key]
        if isinstance(value, str):
            return value
    return ""


def extract_prompt(hook_input: dict[str, Any]) -> str:
    keys = ["prompt", "user_prompt", "message", "text", "input"]
    for key in keys:
        value = hook_input.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            content = value.get("content")
            if isinstance(content, str):
                return content
    raw = hook_input.get("raw")
    return raw if isinstance(raw, str) else ""


def looks_like_roadmap_request(prompt: str) -> bool:
    text = prompt.lower()
    return any(marker in text for marker in ["/roadmap", "$roadmap", "roadmap workflow"])


def looks_like_program_request(prompt: str) -> bool:
    text = prompt.lower()
    return any(marker in text for marker in ["/program", "$program", "program workflow"])


def is_git_commit_command(command: str) -> bool:
    return bool(re.search(r"(^|[;&|]\s*)git\s+commit($|\s)", command))


def emit_context(
    event_name: str,
    label: str,
    message: str,
    payload: dict[str, Any],
    permission_decision: str | None = None,
) -> None:
    hook_output: dict[str, Any] = {
        "hookEventName": event_name,
        "additionalContext": f"{label} {message}",
    }
    if permission_decision == "deny":
        hook_output["permissionDecision"] = permission_decision
        hook_output["permissionDecisionReason"] = f"{label} {message}"

    output = {"hookSpecificOutput": hook_output}
    log_hook_output(event_name, output, payload)
    print(json.dumps(output, ensure_ascii=False))


def emit_additional_context(
    event_name: str,
    label: str,
    message: str,
    payload: dict[str, Any],
) -> None:
    output = {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": f"{label} {message}",
        }
    }
    log_hook_output(event_name, output, payload)
    print(json.dumps(output, ensure_ascii=False))


def log_hook_seen(event_name: str, root: Path, hook_input: dict[str, Any]) -> None:
    log_path = os.environ.get("CODEX_ROADMAP_LOG")
    if not log_path:
        return
    append_jsonl(
        Path(log_path),
        {
            "event": "seen",
            "hook_event_name": event_name,
            "root": str(root),
            "input_keys": sorted(hook_input.keys()),
        },
    )


def log_hook_output(
    event_name: str,
    output: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> None:
    log_path = os.environ.get("CODEX_ROADMAP_LOG")
    if not log_path:
        return
    append_jsonl(
        Path(log_path),
        {
            "event": "output",
            "hook_event_name": event_name,
            "output": output,
            "payload": payload or {},
        },
    )


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def active_payload(active: ActivePlan) -> dict[str, str]:
    return {
        "phase_index": str(active.phase_index),
        "plan_path": str(active.plan_path),
        "version": active.version,
        "slug": active.slug,
        "status": active.status,
    }


def program_payload(program: ProgramContext) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "program_path": str(program.program_path),
        "active_roadmap_id": program.active_roadmap_id,
        "conflicts": program.conflicts,
        "roadmaps": {
            roadmap_id: {
                "path": str(roadmap.path),
                "status": roadmap.status,
                "depends_on": roadmap.depends_on,
                "final_verification": roadmap.final_verification,
            }
            for roadmap_id, roadmap in program.roadmaps.items()
        },
    }
    if program.active_roadmap:
        payload["active_roadmap"] = {
            "roadmap_id": program.active_roadmap.roadmap_id,
            "path": str(program.active_roadmap.path),
            "status": program.active_roadmap.status,
        }
    if program.active_plan:
        payload["active_plan"] = active_payload(program.active_plan)
    return payload


def run_text(args: list[str], cwd: Path) -> str:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


if __name__ == "__main__":
    raise SystemExit(main())
