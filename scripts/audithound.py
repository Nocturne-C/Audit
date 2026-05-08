#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNNER = ROOT / "scripts" / "run_convergence_loop.sh"
DEFAULT_OUTPUT_ROOT = ROOT / "output"


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Manifest must be a JSON object: {path}")
    return data


def resolve_target_and_case_name(target_arg: str) -> tuple[Path, str]:
    raw = Path(target_arg).expanduser().resolve()

    if raw.is_file() and raw.name == "manifest.json":
        manifest = load_manifest(raw)
        target_root = Path(manifest["target_root"]).expanduser().resolve()
        case_name = str(manifest.get("audit_id") or raw.parent.name)
        return target_root, case_name

    manifest_path = raw / "manifest.json"
    if raw.is_dir() and manifest_path.exists():
        manifest = load_manifest(manifest_path)
        target_root = Path(manifest["target_root"]).expanduser().resolve()
        case_name = str(manifest.get("audit_id") or raw.name)
        return target_root, case_name

    if not raw.exists():
        raise SystemExit(f"Target does not exist: {raw}")
    if not raw.is_dir():
        raise SystemExit(f"Target must be a directory, materialized case dir, or manifest.json: {raw}")
    return raw, raw.name


def default_output_dir(case_name: str) -> Path:
    return DEFAULT_OUTPUT_ROOT / f"{case_name}_{int(time.time())}"


def default_model_for_agent(agent: str) -> str:
    if agent == "opencode":
        return os.environ.get("OPENCODE_MODEL", "opencode/minimax-m2.5-free")
    return os.environ.get("CODEX_MODEL", "gpt-5.4")


def effective_excludes(cli_excludes: list[str] | None) -> list[str]:
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


def effective_includes(cli_includes: list[str] | None) -> list[str]:
    if cli_includes:
        return cli_includes

    raw = os.environ.get("AUDITHOUND_INCLUDE_GLOBS", "").strip()
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"AUDITHOUND_INCLUDE_GLOBS must be a JSON array: {exc}") from exc

    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise SystemExit("AUDITHOUND_INCLUDE_GLOBS must be a JSON array of strings")

    return data


def run_loop(args: argparse.Namespace) -> int:
    target_dir, case_name = resolve_target_and_case_name(args.target)
    if args.resume and not args.output_dir:
        raise SystemExit("--resume requires --output-dir so the previous run can be located.")

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir(case_name)
    if args.resume and not output_dir.exists():
        raise SystemExit(f"--resume requested but output directory does not exist: {output_dir}")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    excludes = effective_excludes(args.exclude)
    includes = effective_includes(args.include)

    env = os.environ.copy()
    env["AUDITHOUND_AGENT_TYPE"] = args.agent
    if args.agents:
        env["AUDITHOUND_AGENT_TYPES"] = args.agents
    env["CODEX_MODEL"] = args.model
    env["CODEX_REASONING_EFFORT"] = args.reasoning_effort
    env["AUDITHOUND_MERGE_MODEL"] = args.merge_model or args.model
    env["AUDITHOUND_CODEX_MODEL"] = args.codex_model or args.model
    env["AUDITHOUND_OPENCODE_MODEL"] = args.opencode_model or args.model
    env["AUDITHOUND_SUMMARY_AGENT"] = args.summary_agent
    env["AUDITHOUND_SUMMARY_MODEL"] = args.summary_model or env["AUDITHOUND_MERGE_MODEL"]
    env["AUDITHOUND_SUMMARY_REASONING_EFFORT"] = args.summary_reasoning_effort or args.reasoning_effort
    env["AUDITHOUND_EXCLUDE_GLOBS"] = json.dumps(excludes, ensure_ascii=True)
    env["AUDITHOUND_INCLUDE_GLOBS"] = json.dumps(includes, ensure_ascii=True)
    env["AUDITHOUND_RESUME"] = "1" if args.resume else "0"

    cmd = [
        "bash",
        str(DEFAULT_RUNNER),
        str(target_dir),
        str(output_dir),
        str(args.max_rounds),
        str(args.converge_after),
        args.merge_mode,
        args.model,
        str(args.workers),
    ]

    print(
        json.dumps(
            {
                "target_dir": str(target_dir),
                "output_dir": str(output_dir),
                "agent": args.agent,
                "agents": args.agents,
                "model": args.model,
                "codex_model": env["AUDITHOUND_CODEX_MODEL"],
                "opencode_model": env["AUDITHOUND_OPENCODE_MODEL"],
                "merge_model": env["AUDITHOUND_MERGE_MODEL"],
                "summary_agent": env["AUDITHOUND_SUMMARY_AGENT"],
                "summary_model": env["AUDITHOUND_SUMMARY_MODEL"],
                "summary_reasoning_effort": env["AUDITHOUND_SUMMARY_REASONING_EFFORT"],
                "reasoning_effort": args.reasoning_effort,
                "resume": args.resume,
                "include": includes,
                "exclude": excludes,
                "max_rounds": args.max_rounds,
                "converge_after": args.converge_after,
                "merge_mode": args.merge_mode,
                "workers": args.workers,
            },
            ensure_ascii=True,
        )
    )
    proc = subprocess.run(cmd, env=env, check=False)
    return proc.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="audithound", description="CLI wrapper for AuditHoundV2.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="Run the convergence audit loop on a source directory, materialized case dir, or manifest.json.",
    )
    run_parser.add_argument(
        "target",
        help="Source directory, materialized case directory, or path to manifest.json.",
    )
    run_parser.add_argument(
        "--output-dir",
        help="Output directory. Defaults to AuditHoundV2/output/<case>_<timestamp>.",
    )
    run_parser.add_argument("--agent", default="codex", choices=("codex", "opencode"), help="Code agent to run.")
    run_parser.add_argument(
        "--agents",
        help="Comma-separated agents to run each round, e.g. codex,opencode or codex,codex,opencode. Overrides --agent/--workers shape.",
    )
    run_parser.add_argument("--model", help="Primary model for audit rounds.")
    run_parser.add_argument("--codex-model", help="Model for codex workers. Defaults to --model or codex default.")
    run_parser.add_argument("--opencode-model", help="Model for opencode workers. Defaults to --model or opencode default.")
    run_parser.add_argument(
        "--merge-model",
        help="Model for merge/review. Defaults to --model.",
    )
    run_parser.add_argument(
        "--summary-agent",
        default="codex",
        choices=("codex", "opencode"),
        help="Agent used for round summaries. Defaults to codex.",
    )
    run_parser.add_argument(
        "--summary-model",
        help="Model for round summaries. Defaults to --merge-model.",
    )
    run_parser.add_argument(
        "--summary-reasoning-effort",
        choices=("minimal", "low", "medium", "high", "xhigh"),
        help="Reasoning effort for round summaries. Defaults to --reasoning-effort.",
    )
    run_parser.add_argument(
        "--reasoning-effort",
        default=os.environ.get("CODEX_REASONING_EFFORT", "medium"),
        choices=("minimal", "low", "medium", "high", "xhigh"),
        help="Reasoning effort passed to codex.",
    )
    run_parser.add_argument(
        "--exclude",
        action="append",
        help="Relative glob to exclude from direct audit scope, e.g. interfaces/**. May be repeated.",
    )
    run_parser.add_argument(
        "--include",
        action="append",
        help="Relative glob to include in direct audit scope, e.g. LayerZero/**. May be repeated.",
    )
    run_parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume an interrupted run from an existing --output-dir instead of starting over.",
    )
    run_parser.add_argument("--max-rounds", type=int, default=10, help="Maximum audit rounds.")
    run_parser.add_argument(
        "--converge-after",
        type=int,
        default=2,
        help="Stop after this many consecutive no-new-finding rounds.",
    )
    run_parser.add_argument(
        "--merge-mode",
        default="codex",
        choices=("codex", "manual"),
        help="Merge mode.",
    )
    run_parser.add_argument("--workers", type=int, default=1, help="Parallel workers per round.")
    run_parser.set_defaults(func=run_loop)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "command", None) == "run":
        if not args.model:
            args.model = default_model_for_agent(args.agent)
        if not args.codex_model:
            args.codex_model = os.environ.get("CODEX_MODEL", "gpt-5.4")
        if not args.opencode_model:
            args.opencode_model = os.environ.get("OPENCODE_MODEL", "opencode/minimax-m2.5-free")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
