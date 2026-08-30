#!/usr/bin/env python3
"""Write the measurement-protocol metadata header into evidence files.

The measurement protocol requires every evidence file to record: model name,
Ollama digest, temperature, seed, context length, app mode, date, and the app's
git commit. This script pulls those from the running target's /healthz and
stamps them in.

  .md files   get a visible, comment-delimited "Evidence metadata" block at the
              top. Re-running replaces the block rather than stacking a new one.
  .json files get a top-level "metadata" object matching the normalize_results
              schema. Empty fields are filled; existing values are kept unless
              --force. run_scenario.py already writes this block, so stamping its
              output is a no-op unless a field was missing.

The target must be running in the mode the evidence was collected in, because
/healthz reports that mode's model digest and control set.

Usage
-----
    # stamp specific files (canonical run: temp/seed come from /healthz)
    python scripts/stamp_evidence.py evidence/baseline/P1-01-run_scenario-canonical-2026-08-29.md

    # a rate run: temperature 0.7, seed unset, regardless of /healthz defaults
    python scripts/stamp_evidence.py --run-type rate evidence/baseline/P1-03-*-rate-*.md

    # everything under a directory
    python scripts/stamp_evidence.py --dir evidence/hardened
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

MD_START = "<!-- evidence-metadata:start -->"
MD_END = "<!-- evidence-metadata:end -->"
_MD_BLOCK = re.compile(re.escape(MD_START) + r".*?" + re.escape(MD_END), re.DOTALL)

FIELDS = ("model", "model_digest", "temperature", "seed", "num_ctx", "app_mode", "date", "git_commit")


def build_header(health: dict, *, run_type: str, temperature, seed) -> dict:
    gen = health.get("gen_options", {})
    if temperature is None and run_type == "rate":
        temperature = 0.7
    elif temperature is None:
        temperature = gen.get("temperature")
    if seed is ... and run_type == "rate":
        seed = None
    elif seed is ...:
        seed = gen.get("seed")
    return {
        "model": health.get("model", ""),
        "model_digest": health.get("model_digest", ""),
        "temperature": temperature,
        "seed": seed,
        "num_ctx": gen.get("num_ctx"),
        "app_mode": health.get("mode", ""),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "git_commit": health.get("git_commit", ""),
        "run_type": run_type,
    }


def _md_block(header: dict) -> str:
    rows = "\n".join(f"| {k} | `{header[k]}` |" for k in (*FIELDS, "run_type"))
    stamped = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        f"{MD_START}\n"
        f"## Evidence metadata\n\n"
        f"| field | value |\n|---|---|\n{rows}\n"
        f"| stamped | `{stamped}` |\n\n"
        f"{MD_END}"
    )


def stamp_md(path: Path, header: dict) -> str:
    text = path.read_text(encoding="utf-8")
    block = _md_block(header)
    if _MD_BLOCK.search(text):
        new = _MD_BLOCK.sub(lambda _m: block, text, count=1)
        action = "replaced"
    else:
        new = block + "\n\n" + text
        action = "inserted"
    path.write_text(new, encoding="utf-8")
    return action


def stamp_json(path: Path, header: dict, *, force: bool) -> str:
    doc = json.loads(path.read_text(encoding="utf-8"))
    meta = dict(doc.get("metadata", {}))
    changed = []
    for k in FIELDS:
        cur = meta.get(k)
        if force or cur in (None, "", []):
            if meta.get(k) != header[k]:
                meta[k] = header[k]
                changed.append(k)
    meta["run_type"] = header["run_type"]
    meta["stamped"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc["metadata"] = meta
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return f"updated {changed}" if changed else "no field changes"


def _targets(args) -> list[Path]:
    out: list[Path] = []
    for f in args.files:
        out.append(Path(f))
    if args.dir:
        d = Path(args.dir)
        out += sorted(p for p in d.rglob("*") if p.suffix in (".md", ".json"))
    seen = set()
    uniq = []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="*", help="evidence files to stamp (.md or .json)")
    p.add_argument("--dir", help="also stamp every .md and .json under this directory")
    p.add_argument("--url", default="http://127.0.0.1:8000")
    p.add_argument("--run-type", default="canonical", choices=("canonical", "rate"))
    p.add_argument("--temperature", type=float, default=None, help="override; default from /healthz (canonical) or 0.7 (rate)")
    p.add_argument("--seed", default="__default__", help="override; default from /healthz (canonical) or unset (rate)")
    p.add_argument("--force", action="store_true", help="overwrite existing non-empty json metadata values")
    p.add_argument("--timeout", type=float, default=15.0)
    args = p.parse_args()

    targets = _targets(args)
    if not targets:
        print("nothing to stamp: pass files or --dir", file=sys.stderr)
        return 1

    try:
        resp = httpx.get(f"{args.url.rstrip('/')}/healthz", timeout=args.timeout)
        resp.raise_for_status()
        health = resp.json()
    except httpx.HTTPError as exc:
        print(f"could not reach /healthz at {args.url}: {exc}", file=sys.stderr)
        print("start the target in the mode this evidence was collected in first.", file=sys.stderr)
        return 1

    seed = ... if args.seed == "__default__" else (None if args.seed.lower() in ("none", "unset", "null", "") else int(args.seed))
    header = build_header(health, run_type=args.run_type, temperature=args.temperature, seed=seed)

    print(f"mode={header['app_mode']}  model={header['model']}  digest={header['model_digest']}  commit={header['git_commit']}")
    rc = 0
    for path in targets:
        if not path.exists():
            print(f"  skip (missing): {path}", file=sys.stderr)
            rc = 1
            continue
        try:
            if path.suffix == ".md":
                action = stamp_md(path, header)
            elif path.suffix == ".json":
                action = stamp_json(path, header, force=args.force)
            else:
                print(f"  skip (not .md/.json): {path}")
                continue
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  error: {path}: {exc}", file=sys.stderr)
            rc = 1
            continue
        print(f"  {action}: {path}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
