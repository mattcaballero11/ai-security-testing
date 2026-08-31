#!/usr/bin/env python3
"""Reduce one `promptfoo eval -o run.json` file to the P1-05 pass/fail matrix.

promptfoo's native output is verbose and its shape shifts between versions. This
pulls out just what the regression envelope and compare_modes.py need: per check,
did the assertion pass, and why.

Usage:
    python summarize_run.py --mode baseline --input run-baseline.json --out summary-baseline.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _rows(doc: dict) -> list[dict]:
    # promptfoo has used results.results[], results[], and evalResults[] over versions
    for key in ("results", "evalResults"):
        node = doc.get(key)
        if isinstance(node, dict) and isinstance(node.get("results"), list):
            return node["results"]
        if isinstance(node, list):
            return node
    return []


def _check_id(row: dict) -> str:
    v = row.get("vars") or (row.get("testCase") or {}).get("vars") or {}
    if v.get("check"):
        return str(v["check"])
    return str(row.get("description") or (row.get("testCase") or {}).get("description") or "unknown")


def _passed(row: dict) -> bool:
    if "success" in row:
        return bool(row["success"])
    gr = row.get("gradingResult") or {}
    if "pass" in gr:
        return bool(gr["pass"])
    return False


def _reason(row: dict) -> str:
    gr = row.get("gradingResult") or {}
    comps = gr.get("componentResults") or []
    # prefer the assertion's own reason (from assert_p1_05.py) over promptfoo's
    # generic "All assertions passed"
    specific = [str(c.get("reason", "")) for c in comps if c.get("reason")]
    if specific:
        return "; ".join(specific)
    if gr.get("reason"):
        return str(gr["reason"])
    return str(row.get("error") or "")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", required=True, choices=("baseline", "hardened"))
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    doc = json.loads(args.input.read_text(encoding="utf-8"))
    rows = _rows(doc)
    checks = []
    for row in rows:
        checks.append(
            {
                "check": _check_id(row),
                "description": str(row.get("description") or (row.get("testCase") or {}).get("description") or ""),
                "pass": _passed(row),
                "reason": _reason(row)[:500],
            }
        )
    green = all(c["pass"] for c in checks) and bool(checks)
    summary = {
        "mode": args.mode,
        "checks": checks,
        "green": green,
        "total": len(checks),
        "passed": sum(1 for c in checks if c["pass"]),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{args.mode}: {summary['passed']}/{summary['total']} checks passed  green={green}")
    return 0 if green else 1


if __name__ == "__main__":
    raise SystemExit(main())
