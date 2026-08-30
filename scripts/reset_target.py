#!/usr/bin/env python3
"""Clear the target's in-memory conversation state and rate-limit counters.

Called between trials so one scenario run does not contaminate the next. Safe to
run when nothing is in state; it just reports zero cleared turns.

Usage:
    python scripts/reset_target.py [--url http://127.0.0.1:8000]
"""

from __future__ import annotations

import argparse
import sys

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="target base URL")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    base = args.url.rstrip("/")
    try:
        resp = httpx.post(f"{base}/reset", timeout=args.timeout)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"reset failed: {exc}", file=sys.stderr)
        return 1

    data = resp.json()
    print(
        f"reset ok  mode={data.get('mode')}  cleared_turns={data.get('cleared_turns')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
