#!/usr/bin/env python3
"""
CLI for browsing playbooks – list, show, queries, validate.

Usage:
  th_playbook list
  th_playbook show T1055-process-injection
  th_playbook queries T1055-process-injection [--resolve] [--hours 24]
  th_playbook validate [T1055-process-injection]

Run from project root or set PROJECT_ROOT / BOOTSTRAP_PROJECT_ROOT.
Usable in Jupyter: !python scripts/th_playbook.py list
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure project root is on PYTHONPATH
_PROJECT_ROOT = os.environ.get("BOOTSTRAP_PROJECT_ROOT") or os.environ.get("PROJECT_ROOT")
if _PROJECT_ROOT:
    sys.path.insert(0, str(Path(_PROJECT_ROOT).resolve()))
else:
    # Assume script is in scripts/ under project root
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(_PROJECT_ROOT))

from automation_scripts.playbooks.cli_helpers import (
    get_playbooks_dir,
    list_playbooks,
    show_playbook,
    get_queries_resolved,
    validate_playbook_cli,
)
from automation_scripts.playbooks.query_generator import generate_queries


def _playbooks_dir() -> Path:
    root = Path(_PROJECT_ROOT) if _PROJECT_ROOT else get_playbooks_dir().parent
    return root / "playbooks"


def cmd_list(args: argparse.Namespace) -> int:
    """List playbooks."""
    pb_dir = _playbooks_dir()
    items = list_playbooks(playbooks_dir=pb_dir, include_template=args.template)
    if not items:
        print("No playbooks found.")
        return 0
    for item in items:
        mid = item.get("mitre_technique_id", "") or "-"
        name = item.get("name", "")
        desc = (item.get("description") or "")[:60]
        tc = item.get("tool_classes", [])
        tc_str = ",".join(tc) if tc else "-"
        print(f"  {item['id']:<35} {mid:<8} {name}")
        if desc:
            print(f"    {desc}...")
        if args.tool_classes and tc:
            print(f"    tool_classes: {tc_str}")
    return 0


def _format_meta_val(key: str, val) -> None:
    """Print metadata value (handles nested objects)."""
    if val is None:
        return
    if isinstance(val, str):
        for line in val.strip().split("\n"):
            print(f"  {line}")
    elif isinstance(val, dict):
        for k, v in val.items():
            if isinstance(v, list):
                print(f"  {k}: {v}")
            elif isinstance(v, dict):
                print(f"  {k}:")
                for kk, vv in v.items():
                    print(f"    {kk}: {vv}")
            else:
                print(f"  {k}: {v}")
    elif isinstance(val, list):
        for i, item in enumerate(val):
            if isinstance(item, dict):
                print(f"  [{i+1}] {item.get('name', '')}:")
                for k, v in item.items():
                    if k != "name":
                        print(f"    {k}: {v}")
            else:
                print(f"  - {item}")
    else:
        print(f"  {val}")


def cmd_show(args: argparse.Namespace) -> int:
    """Show playbook metadata (including hypothesis, operational_steps, escalation)."""
    pb_dir = _playbooks_dir()
    try:
        meta = show_playbook(args.playbook_id, playbooks_dir=pb_dir)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(meta, indent=2, default=str))
    else:
        priority_keys = [
            "name", "description", "mitre_technique_id", "mitre_technique_name",
            "technique_description", "environment_requirements",
            "hypothesis", "operational_steps", "escalation",
            "hunting_indicators", "true_positive_conditions", "false_positive_conditions",
        ]
        printed = set()
        for key in priority_keys:
            if key in meta:
                val = meta[key]
                print(f"{key}:")
                _format_meta_val(key, val)
                print()
                printed.add(key)
        for key, val in meta.items():
            if key not in printed:
                print(f"{key}:")
                _format_meta_val(key, val)
                print()
    return 0


def cmd_queries(args: argparse.Namespace) -> int:
    """List or show queries (optionally filter by tool class)."""
    pb_dir = _playbooks_dir()
    tool_class = getattr(args, "tool_class", None)
    try:
        if args.resolve or tool_class:
            entries = get_queries_resolved(
                args.playbook_id,
                hours=args.hours,
                playbooks_dir=pb_dir,
                tool_class=tool_class,
            )
        else:
            from automation_scripts.playbooks.query_loader import load_queries
            playbook_path = pb_dir / args.playbook_id
            entries = load_queries(playbook_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    for e in entries:
        tc = getattr(e, "tool_class", None) or "-"
        print(f"\n--- {e.tool} ({tc}) / {e.mode} / {e.query_path} ---")
        print(e.content)
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate query files for selected hunts and tools."""
    root = Path(_PROJECT_ROOT) if _PROJECT_ROOT else get_playbooks_dir().parent
    pb_dir = root / "playbooks"
    out_dir = root / "queries_generated"
    if getattr(args, "output_dir", None):
        out_dir = Path(args.output_dir)
    try:
        paths = generate_queries(
            hunt_list=args.hunts,
            tool_list=args.tools,
            mode=args.mode,
            output_dir=out_dir,
            time_range_days=args.days,
            playbooks_dir=pb_dir,
            project_root=root,
        )
        print(f"Generated {len(paths)} files in {out_dir}")
        for p in paths:
            print(f"  {p.name}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate playbook(s)."""
    pb_dir = _playbooks_dir()
    playbook_id = getattr(args, "playbook_id", None)
    results = validate_playbook_cli(playbook_id=playbook_id, playbooks_dir=pb_dir)
    if not results:
        print("No playbooks found.")
        return 0
    failed = 0
    for pid, r in results:
        if r.success:
            status = "OK"
            if r.warnings:
                status += f" ({len(r.warnings)} warnings)"
            print(f"  {pid}: {status}")
            for w in r.warnings:
                print(f"    [WARN] {w}")
        else:
            failed += 1
            print(f"  {pid}: FAILED")
            for e in r.errors:
                print(f"    [ERR] {e}")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Browse and validate threat hunting playbooks"
    )
    parser.add_argument(
        "--project-root",
        default=os.environ.get("BOOTSTRAP_PROJECT_ROOT") or os.environ.get("PROJECT_ROOT"),
        help="Project root (th_timmy directory)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = sub.add_parser("list", help="List available playbooks")
    p_list.add_argument("-t", "--template", action="store_true", help="Include template playbook")
    p_list.add_argument("--tool-classes", action="store_true", help="Show available tool_classes per playbook")
    p_list.set_defaults(func=cmd_list)

    # show
    p_show = sub.add_parser("show", help="Show playbook metadata")
    p_show.add_argument("playbook_id", help="Playbook ID (e.g. T1055-process-injection)")
    p_show.add_argument("-f", "--format", choices=["text", "json"], default="text")
    p_show.set_defaults(func=cmd_show)

    # queries
    p_queries = sub.add_parser("queries", help="Show queries (optionally filter by tool class)")
    p_queries.add_argument("playbook_id", help="Playbook ID")
    p_queries.add_argument("-r", "--resolve", action="store_true", help="Resolve {{timestamp_start}}/{{timestamp_end}} (legacy)")
    p_queries.add_argument("--hours", type=int, default=24, help="Hours for time range (default: 24)")
    p_queries.add_argument("--tool-class", choices=["siem", "edr", "data_lake"], help="Filter queries by tool class (analyst selects available tool)")
    p_queries.set_defaults(func=cmd_queries)

    # generate
    p_generate = sub.add_parser("generate", help="Generate query files for hunts and tools")
    p_generate.add_argument("hunts", nargs="+", help="Playbook IDs (e.g. T1059 T1055 T1562)")
    p_generate.add_argument("-t", "--tools", nargs="+", default=["elk", "ms_defender"],
                            help="Tools (default: elk ms_defender)")
    p_generate.add_argument("-m", "--mode", choices=["manual", "API"], default="manual",
                            help="Mode (default: manual)")
    p_generate.add_argument("-d", "--days", type=int, default=7, help="Time range days (default: 7)")
    p_generate.add_argument("-o", "--output-dir", help="Output directory (default: queries_generated/)")
    p_generate.set_defaults(func=cmd_generate)

    # validate
    p_validate = sub.add_parser("validate", help="Validate playbook(s)")
    p_validate.add_argument("playbook_id", nargs="?", help="Playbook ID (optional; validate all if omitted)")
    p_validate.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    if args.project_root:
        os.environ["PROJECT_ROOT"] = args.project_root
        global _PROJECT_ROOT
        _PROJECT_ROOT = args.project_root

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
