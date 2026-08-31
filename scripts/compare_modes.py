#!/usr/bin/env python3
"""Baseline-versus-hardened delta table, as Markdown.

Two inputs:

1. A P1-05 regression envelope (from tests/promptfoo/run.sh):

       python scripts/compare_modes.py --regression evidence/reports/regression-2026-08-31.json

   -> the guardrail gate table: per check, did baseline assert vulnerable and
      hardened assert controlled, with the reason strings and the overall
      gate_pass.

2. A pair of normalised result files (schema_version 1.0), one per mode, for the
   same scenario and tool (run_scenario, render_probe, or a normalised promptfoo
   / garak / pyrit run):

       python scripts/compare_modes.py \
           --baseline evidence/baseline/P1-01-run_scenario-rate-2026-08-29.json \
           --hardened evidence/hardened/P1-01-run_scenario-rate-2026-08-29.json

   -> the per-payload success-rate delta: baseline k/n, hardened k/n, change.
      Uses the raw (pre-output-control) rate too when the file carries it, so a
      scenario where a hardened output stage changed only what the caller saw is
      not misread as the model changing behaviour.

Write to a file with --out, otherwise stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# --------------------------------------------------------------------------
# regression envelope -> gate table
# --------------------------------------------------------------------------


def _regression_md(env: dict) -> str:
    modes = env.get("modes", {})
    base = modes.get("baseline", {})
    hard = modes.get("hardened", {})
    base_checks = {c["check"]: c for c in base.get("checks", [])}
    hard_checks = {c["check"]: c for c in hard.get("checks", [])}
    order = list(base_checks) or list(hard_checks)
    for c in hard_checks:
        if c not in order:
            order.append(c)

    lines = [
        f"# P1-05 guardrail regression: baseline vs hardened",
        "",
        f"- suite version: `{env.get('suite_version')}`",
        f"- generated: {env.get('generated')}",
        f"- app commit: `{env.get('git_commit')}`",
        f"- model digest: `{env.get('model_digest') or 'n/a'}`",
        f"- run type: `{env.get('run_type')}` (temperature 0, seed 42, one trial per check)",
        "",
        f"**Gate: {'PASS' if env.get('gate_pass') else 'FAIL'}** "
        f"(baseline {base.get('passed', 0)}/{base.get('total', 0)} green, "
        f"hardened {hard.get('passed', 0)}/{hard.get('total', 0)} green)",
        "",
        "A check passes in baseline when the vulnerable behaviour is present, and "
        "in hardened when it is controlled. The gate passes only when every check "
        "is green in both modes: baseline green proves the attacks still "
        "reproduce, hardened green proves the controls still hold.",
        "",
        "| Check | Baseline (attack lands?) | Hardened (control holds?) | Delta |",
        "|---|---|---|---|",
    ]
    for check in order:
        b = base_checks.get(check, {})
        h = hard_checks.get(check, {})
        b_txt = "green" if b.get("pass") else ("red" if b else "-")
        h_txt = "green" if h.get("pass") else ("red" if h else "-")
        if b.get("pass") and h.get("pass"):
            delta = "controls reduce risk as expected"
        elif b and not b.get("pass"):
            delta = "baseline no longer vulnerable here (attack or model drifted)"
        elif h and not h.get("pass"):
            delta = "**hardened control regressed**"
        else:
            delta = ""
        lines.append(f"| `{check}` | {b_txt} | {h_txt} | {delta} |")

    lines += ["", "## Reasons", ""]
    for check in order:
        lines.append(f"### `{check}`")
        b = base_checks.get(check, {})
        h = hard_checks.get(check, {})
        if b.get("description") or h.get("description"):
            lines.append(f"_{b.get('description') or h.get('description')}_")
        lines.append("")
        lines.append(f"- baseline: {'PASS' if b.get('pass') else 'FAIL'} - {b.get('reason', '(not run)')}")
        lines.append(f"- hardened: {'PASS' if h.get('pass') else 'FAIL'} - {h.get('reason', '(not run)')}")
        lines.append("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# two normalised files -> per-payload delta
# --------------------------------------------------------------------------


def _load(path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    if d.get("schema_version") != "1.0":
        print(f"warning: {path} schema_version={d.get('schema_version')!r}, expected '1.0'", file=sys.stderr)
    return d


def _rate_map(result: dict, key: str) -> dict:
    return {pid: v for pid, v in (result.get("summary", {}).get(key, {}) or {}).items()}


def _frac(entry: dict) -> float:
    if "success_fraction" in entry:
        return float(entry["success_fraction"])
    r = entry.get("rate", "0/1")
    try:
        n, d = r.split("/")
        return int(n) / int(d) if int(d) else 0.0
    except ValueError:
        return 0.0


def _delta_md(base: dict, hard: dict, title: str | None) -> str:
    if base.get("scenario") != hard.get("scenario"):
        print(f"warning: scenario mismatch {base.get('scenario')} vs {hard.get('scenario')}", file=sys.stderr)
    scenario = base.get("scenario", "?")
    tool = base.get("tool", "?")
    bm, hm = base.get("metadata", {}), hard.get("metadata", {})

    b_ret, h_ret = _rate_map(base, "by_payload"), _rate_map(hard, "by_payload")
    b_raw, h_raw = _rate_map(base, "by_payload_raw"), _rate_map(hard, "by_payload_raw")
    has_raw = bool(b_raw or h_raw)
    payloads = list(b_ret) + [p for p in h_ret if p not in b_ret]

    lines = [
        f"# {title or f'{scenario} baseline vs hardened'} ({tool})",
        "",
        f"- scenario: `{scenario}`   tool: `{tool}`   run type: `{base.get('run_type')}`",
        f"- model: `{bm.get('model')}`  digest: `{bm.get('model_digest')}`",
        f"- baseline commit: `{bm.get('git_commit')}`   hardened commit: `{hm.get('git_commit')}`",
        f"- temperature: `{bm.get('temperature')}`  seed: `{bm.get('seed')}`",
        "",
    ]
    if has_raw:
        lines += [
            "`returned` is what the caller received. `raw` is the model's output "
            "before any hardened output-stage control (redaction, restricted-content "
            "screen). Where they differ, the control changed the delivered result, "
            "not the model's behaviour.",
            "",
            "| Payload | Family | Baseline returned | Hardened returned | Baseline raw | Hardened raw | Delta (returned) |",
            "|---|---|---|---|---|---|---|",
        ]
    else:
        lines += [
            "| Payload | Family | Baseline | Hardened | Delta |",
            "|---|---|---|---|---|",
        ]

    b_tot = h_tot = b_raw_tot = h_raw_tot = 0.0
    n = 0
    for pid in payloads:
        be, he = b_ret.get(pid, {}), h_ret.get(pid, {})
        fam = be.get("family") or he.get("family") or ""
        b_rate = be.get("rate", "-")
        h_rate = he.get("rate", "-")
        bf, hf = _frac(be) if be else 0.0, _frac(he) if he else 0.0
        b_tot += bf
        h_tot += hf
        n += 1
        delta_pp = round((hf - bf) * 100)
        arrow = "no change" if delta_pp == 0 else (f"{delta_pp:+d} pp")
        if has_raw:
            brr = b_raw.get(pid, {}).get("rate", "-")
            hrr = h_raw.get(pid, {}).get("rate", "-")
            b_raw_tot += _frac(b_raw.get(pid, {})) if b_raw.get(pid) else bf
            h_raw_tot += _frac(h_raw.get(pid, {})) if h_raw.get(pid) else hf
            lines.append(f"| `{pid}` | {fam} | {b_rate} | {h_rate} | {brr} | {hrr} | {arrow} |")
        else:
            lines.append(f"| `{pid}` | {fam} | {b_rate} | {h_rate} | {arrow} |")

    bt = base.get("summary", {}).get("totals", {})
    ht = hard.get("summary", {}).get("totals", {})
    lines += [
        "",
        f"- baseline: {bt.get('successes', '?')}/{bt.get('trials', '?')} trial successes across {bt.get('payloads', '?')} payloads",
        f"- hardened: {ht.get('successes', '?')}/{ht.get('trials', '?')} trial successes across {ht.get('payloads', '?')} payloads",
    ]
    if has_raw and "raw_successes" in ht:
        hr = ht.get("raw_successes")
        hs = ht.get("successes")
        if hr == hs:
            tail = "(equals returned: the input and prompt controls changed the model's behaviour, no output filter needed here)"
        else:
            tail = f"(returned {hs}: the {hr - hs} difference is what the output-stage control caught after the model complied)"
        lines.append(f"- hardened raw (model produced the violating output): {hr}/{ht.get('trials')} {tail}")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--regression", type=Path, help="a P1-05 regression envelope JSON")
    p.add_argument("--baseline", type=Path, help="normalised result file, baseline mode")
    p.add_argument("--hardened", type=Path, help="normalised result file, hardened mode")
    p.add_argument("--title", help="heading for the delta table")
    p.add_argument("--out", type=Path, help="write here; default stdout")
    args = p.parse_args()

    if args.regression:
        md = _regression_md(json.loads(args.regression.read_text(encoding="utf-8")))
    elif args.baseline and args.hardened:
        md = _delta_md(_load(args.baseline), _load(args.hardened), args.title)
    else:
        p.error("pass --regression, or both --baseline and --hardened")
        return 2

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
