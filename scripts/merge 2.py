#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


MERGE_PROMPT = """Below are findings from {n} agents auditing the same codebase,
plus accumulated findings from previous rounds. You can inspect the source code when needed.

You are the merge and review layer for a audit.

Your task is to read all findings from this round, merge them into the 
summary of distinct issues, compare that round summary against accumulated findings,
and keep new or materially improved findings in the updated list. 
And you are encouraged to find more findings based on these findings and source code.

Use only Solidity source files under the target directory as audit evidence.
Do not inspect or rely on README files, docs, audit reports, discord exports, scripts, broadcasts, or other files outside the target directory.

Downgrade severity or confidence when the issue depends on unusual configuration or weak assumptions. 
Be skeptical of documented behavior and pure owner-only configuration issues, but keep defensible findings when they create realistic protocol-level harm such as fund loss, theft, insolvency, permanent lockup, economic manipulation, or permissionless denial of service.
Review the merged findings before finalizing them, and remove only findings that are clearly non-reportable in a audit's main results.

## Accumulated Findings
{existing}

## This Round's Agent Outputs
{outputs}
{exclude_note}

## Output
Return the COMPLETE updated findings list as a JSON array.

Each element must have:
- `id`
- `severity`
- `confidence`
- `title`
- `locations`
- `claim`
- `impact`
- `paths`
- `round`
- `source_agents`

Preserve existing IDs for surviving findings whenever possible.
`source_agents` must include every agent that materially supports the final finding.

Output ONLY valid JSON. No markdown. No prose.
"""


def extract_json_array(text: str) -> list[dict]:
    text = text.strip()
    if not text:
        raise ValueError("empty merge output")

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("could not find JSON array in merge output")

    data = json.loads(text[start : end + 1])
    if not isinstance(data, list):
        raise ValueError("merge output is not a JSON array")
    return data


def load_acc(path: Path) -> list[dict]:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"accumulator must be a JSON array: {path}")
    return data


def collect_outputs(round_dir: Path) -> list[tuple[str, str]]:
    outputs: list[tuple[str, str]] = []
    for agent_dir in sorted(round_dir.glob("agent_*")):
        agent_name = agent_dir.name.replace("agent_", "")
        stdout_path = agent_dir / "stdout.log"
        if not stdout_path.exists():
            continue
        text = stdout_path.read_text(encoding="utf-8", errors="replace")
        if len(text) > 40000:
            text = text[:20000] + "\n\n[... truncated ...]\n\n" + text[-20000:]
        outputs.append((agent_name, text))
    return outputs


def load_excludes(cli_excludes: list[str]) -> list[str]:
    if cli_excludes:
        return cli_excludes

    raw = os.environ.get("AUDITHOUND_EXCLUDE_GLOBS", "").strip()
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"AUDITHOUND_EXCLUDE_GLOBS must be a JSON array: {exc}") from exc

    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise SystemExit("AUDITHOUND_EXCLUDE_GLOBS must be a JSON array of strings")
    return data


def build_prompt(existing: list[dict], outputs: list[tuple[str, str]], excludes: list[str]) -> str:
    rendered_outputs = []
    for name, text in outputs:
        rendered_outputs.append(f"### Agent: {name}\n```\n{text}\n```")
    exclude_note = ""
    if excludes:
        exclude_lines = "\n".join(f"- `{item}`" for item in excludes)
        exclude_note = f"""

## Excluded From Direct Audit Scope
Do not keep findings whose reportable root cause exists solely in files matching:
{exclude_lines}

Those files may still be read as context for in-scope implementation code.
"""
    return MERGE_PROMPT.format(
        n=len(outputs),
        existing=json.dumps(existing, indent=2, ensure_ascii=False) if existing else "None yet.",
        outputs="\n\n".join(rendered_outputs) if rendered_outputs else "No agent outputs found.",
        exclude_note=exclude_note,
    )


def resolve_codex_cli() -> str:
    found = shutil.which("codex")
    if found:
        return found

    candidates = [
        "/Users/lu/.antigravity/extensions/openai.chatgpt-0.4.79-darwin-arm64/bin/macos-aarch64/codex",
        str(Path.home() / ".antigravity/extensions/openai.chatgpt-0.4.79-darwin-arm64/bin/macos-aarch64/codex"),
        str(Path.home() / ".local/bin/codex"),
        "/opt/homebrew/bin/codex",
        "/usr/local/bin/codex",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists() and os.access(path, os.X_OK):
            return str(path)

    raise FileNotFoundError("codex CLI not found in PATH or known install locations")


def run_codex_merge(prompt: str, target_dir: Path, model: str) -> tuple[str, str]:
    reasoning_effort = os.environ.get("CODEX_REASONING_EFFORT", "medium")
    codex_bin = resolve_codex_cli()
    proc = subprocess.run(
        [
            codex_bin,
            "-a",
            "never",
            "exec",
            "--cd",
            str(target_dir),
            "--sandbox",
            "workspace-write",
            "--skip-git-repo-check",
            "-m",
            model,
            "-c",
            f'model_reasoning_effort="{reasoning_effort}"',
            "-",
        ],
        input=prompt,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.stdout, proc.stderr


def normalize_findings(items: list[dict], round_num: int) -> list[dict]:
    normalized: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        locations = item.get("locations", [])
        if isinstance(locations, str):
            locations = [locations] if locations else []
        if not isinstance(locations, list):
            locations = []

        paths = item.get("paths", [])
        if isinstance(paths, str):
            paths = [paths] if paths else []
        if not isinstance(paths, list):
            paths = []

        if not paths:
            legacy_checks = item.get("checks", [])
            if isinstance(legacy_checks, str):
                legacy_checks = [legacy_checks] if legacy_checks else []
            if not isinstance(legacy_checks, list):
                legacy_checks = []
            paths = [value for value in legacy_checks if isinstance(value, str) and value]

        source_agents = item.get("source_agents", [])
        if isinstance(source_agents, str):
            source_agents = [source_agents] if source_agents else []
        if not isinstance(source_agents, list):
            source_agents = []

        obj = {
            "id": item.get("id", ""),
            "severity": item.get("severity", "Informational"),
            "confidence": item.get("confidence", "low"),
            "title": item.get("title", ""),
            "locations": locations,
            "claim": item.get("claim", ""),
            "impact": item.get("impact", ""),
            "paths": paths,
            "round": item.get("round", round_num),
            "source_agents": source_agents,
        }
        normalized.append(obj)
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round-dir", required=True)
    parser.add_argument("--target-dir", required=True)
    parser.add_argument("--acc", required=True)
    parser.add_argument("--round-num", type=int, required=True)
    parser.add_argument("--mode", choices=("manual", "codex"), default="codex")
    parser.add_argument("--model", default="o3")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--output")
    parser.add_argument("--result-file")
    args = parser.parse_args()

    round_dir = Path(args.round_dir).resolve()
    target_dir = Path(args.target_dir).resolve()
    acc_path = Path(args.acc).resolve()
    output_path = Path(args.output).resolve() if args.output else acc_path

    existing = load_acc(acc_path)
    outputs = collect_outputs(round_dir)
    excludes = load_excludes(args.exclude)
    prompt = build_prompt(existing, outputs, excludes)
    (round_dir / "merge_prompt.md").write_text(prompt, encoding="utf-8")

    if args.mode == "manual":
        if not args.result_file:
            print("Manual merge requested. Fill a JSON array and rerun with --result-file.", flush=True)
            return 0
        raw = Path(args.result_file).read_text(encoding="utf-8")
        items = extract_json_array(raw)
    else:
        try:
            stdout, stderr = run_codex_merge(prompt, target_dir, args.model)
        except FileNotFoundError as exc:
            (round_dir / "merge_stderr.log").write_text(str(exc) + "\n", encoding="utf-8")
            raise SystemExit(str(exc))
        (round_dir / "merge_stdout.log").write_text(stdout, encoding="utf-8")
        (round_dir / "merge_stderr.log").write_text(stderr, encoding="utf-8")
        items = extract_json_array(stdout)

    normalized = normalize_findings(items, args.round_num)
    output_path.write_text(json.dumps(normalized, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"total": len(normalized), "path": str(output_path)}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
