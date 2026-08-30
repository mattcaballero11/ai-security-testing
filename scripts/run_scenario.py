#!/usr/bin/env python3
"""Run a scenario's payload set against the target and write normalised results.

This is the custom payload runner behind the CV's "Python security automation
for LLM testing" claim. It does not decide severity and it does not write the
finding. It sends each payload, records what app/safeguards.check_violation
reported, and computes k/n.

Two run types (the fixed measurement protocol):

  canonical   temperature 0, seed 42, one trial per payload. The transcript and
              the screenshot in the finding come from this run.
  rate        temperature 0.7, seed unset, n trials per payload. The reported
              success rate (k/10) comes from this run.

Usage
-----
    # canonical pass, one trial per payload
    python scripts/run_scenario.py P1-01 --mode baseline --run canonical

    # rate pass, ten trials per payload
    python scripts/run_scenario.py P1-01 --mode baseline --run rate --trials 10

    # same for P1-03, hardened
    python scripts/run_scenario.py P1-03 --mode hardened --run rate --trials 10

The target must already be running in the matching mode. This script checks
/healthz and refuses to run if the mode does not match.

Output
------
    evidence/<mode>/<id>-run_scenario-<run>-<date>.json   normalised schema
    evidence/<mode>/<id>-run_scenario-<run>-<date>.md     readable transcript

Run scripts/stamp_evidence.py on the .md afterwards to write the metadata header
(the .json already carries it).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import normalize_results as nr  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = REPO_ROOT / "evidence"


def _find_payloads(scenario_id: str) -> Path:
    matches = sorted(REPO_ROOT.glob(f"scenarios/{scenario_id}*/payloads.json"))
    if not matches:
        raise SystemExit(f"no scenarios/{scenario_id}*/payloads.json found")
    if len(matches) > 1:
        raise SystemExit(f"ambiguous scenario id {scenario_id!r}: {[str(m) for m in matches]}")
    return matches[0]


def _healthz(base: str, timeout: float) -> dict:
    resp = httpx.get(f"{base}/healthz", timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _reset(base: str, timeout: float) -> None:
    try:
        httpx.post(f"{base}/reset", timeout=timeout)
    except httpx.HTTPError as exc:
        print(f"  warning: /reset failed ({exc}); continuing", file=sys.stderr)


def _post_chat(base: str, payload: dict, timeout: float, *, retries: int = 3) -> tuple[int, dict]:
    """POST /chat with simple backoff on 429 (rate limit) and 502 (upstream)."""
    delay = 2.0
    last: tuple[int, dict] = (0, {})
    for attempt in range(retries):
        try:
            resp = httpx.post(f"{base}/chat", json=payload, timeout=timeout)
        except httpx.HTTPError as exc:
            last = (0, {"detail": str(exc)})
            time.sleep(delay)
            delay *= 2
            continue
        try:
            body = resp.json()
        except json.JSONDecodeError:
            body = {"detail": resp.text}
        if resp.status_code in (429, 502) and attempt < retries - 1:
            print(f"  HTTP {resp.status_code}, backing off {delay:.0f}s", file=sys.stderr)
            time.sleep(delay)
            delay *= 2
            last = (resp.status_code, body)
            continue
        return resp.status_code, body
    return last


def _success(fired: list[str], success_when: list[str]) -> bool:
    if not success_when:
        return False  # control payloads: a violation is a harness problem, not a success
    return bool(set(fired) & set(success_when))


def _run(
    *,
    scenario_id: str,
    mode: str,
    run_type: str,
    trials: int,
    base: str,
    timeout: float,
) -> dict:
    spec = json.loads(_find_payloads(scenario_id).read_text(encoding="utf-8"))
    scenario = spec["scenario"]
    framework = spec.get("framework", [])
    payloads = spec["payloads"]

    health = _healthz(base, timeout)
    if health.get("mode") != mode:
        raise SystemExit(
            f"target is in {health.get('mode')!r} mode, you asked for {mode!r}. "
            f"Restart the target with APP_MODE={mode}."
        )

    gen = health.get("gen_options", {})
    if run_type == "canonical":
        eff_temp: float | None = gen.get("temperature")
        eff_seed = gen.get("seed")
    else:
        eff_temp = 0.7
        eff_seed = None

    metadata = {
        "model": health.get("model", ""),
        "model_digest": health.get("model_digest", ""),
        "temperature": eff_temp,
        "seed": eff_seed,
        "num_ctx": gen.get("num_ctx"),
        "app_mode": mode,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "git_commit": health.get("git_commit", ""),
    }

    result = nr.new_result(
        scenario=scenario, tool="run_scenario", mode=mode, run_type=run_type, metadata=metadata
    )

    rate_run = run_type == "rate"
    total = len(payloads) * trials
    done = 0
    print(f"{scenario}  mode={mode}  run={run_type}  payloads={len(payloads)}  trials={trials}")

    for pl in payloads:
        pid = pl["id"]
        family = pl.get("family", "")
        is_summary = pl.get("is_summary_request", False)
        use_history = pl.get("use_history", False)
        success_when = pl.get("success_when", [])
        for trial in range(1, trials + 1):
            _reset(base, timeout)
            body_req = {
                "message": pl["message"],
                "is_summary_request": is_summary,
                "use_history": use_history,
                "rate_run": rate_run,
            }
            status, body = _post_chat(base, body_req, timeout)
            done += 1

            fired = body.get("violations", []) or []
            raw_fired = body.get("raw_violations", []) or []
            blocked = bool(body.get("blocked", False))
            ok = _success(fired, success_when) and not blocked
            raw_ok = _success(raw_fired, success_when) and not blocked

            nr.add_attempt(
                result,
                payload_id=pid,
                family=family,
                framework=framework,
                trial=trial,
                input=pl["message"],
                output=str(body.get("content", "")),
                raw_output=str(body.get("raw_content", "")),
                success=ok,
                success_criteria=success_when,
                signals={
                    "violations": fired,
                    "raw_violations": raw_fired,
                    "raw_success": raw_ok,
                    "safeguards": body.get("safeguards", {}),
                    "blocked": blocked,
                    "http_status": status,
                    "timing_ms": body.get("timing_ms"),
                    "detail": body.get("detail"),
                },
                notes=pl.get("notes", ""),
            )
            flag = "HIT " if ok else ("blk " if blocked else "    ")
            print(f"  [{done:>3}/{total}] {flag}{pid} t{trial}  violations={fired or '-'}  raw={raw_fired or '-'}")

    nr.finalize(result)
    _augment_raw_summary(result)
    return result


def _augment_raw_summary(result: dict) -> None:
    """Add a parallel summary computed from raw (pre-redaction) success, so a
    P1-03 finding can show the model disclosed even where a hardened output
    control redacted what the caller saw."""
    from collections import defaultdict

    p_trials: dict = defaultdict(int)
    p_raw: dict = defaultdict(int)
    for a in result["attempts"]:
        pid = a["payload_id"]
        p_trials[pid] += 1
        if a["signals"].get("raw_success"):
            p_raw[pid] += 1
    result["summary"]["by_payload_raw"] = {
        pid: {
            "trials": p_trials[pid],
            "successes": p_raw[pid],
            "rate": f"{p_raw[pid]}/{p_trials[pid]}",
            "success_fraction": round(p_raw[pid] / p_trials[pid], 3) if p_trials[pid] else 0.0,
        }
        for pid in p_trials
    }
    result["summary"]["totals"]["raw_successes"] = sum(p_raw.values())


def _write_transcript(result: dict, path: Path) -> None:
    m = result["metadata"]
    lines = [
        f"# {result['scenario']} {result['tool']} transcript",
        "",
        f"- mode: `{result['mode']}`",
        f"- run type: `{result['run_type']}`",
        f"- generated: {result['generated']}",
        f"- model: `{m['model']}`  digest: `{m['model_digest']}`",
        f"- temperature: `{m['temperature']}`  seed: `{m['seed']}`  num_ctx: `{m['num_ctx']}`",
        f"- git commit: `{m['git_commit']}`",
        "",
        "Run `scripts/stamp_evidence.py` on this file to refresh the metadata header.",
        "",
        "## Summary",
        "",
        "| payload | family | rate (returned) | rate (raw / pre-redaction) |",
        "|---|---|---|---|",
    ]
    raw_sum = result["summary"].get("by_payload_raw", {})
    for pid, d in result["summary"]["by_payload"].items():
        rr = raw_sum.get(pid, {}).get("rate", "-")
        lines.append(f"| {pid} | {d['family']} | {d['rate']} | {rr} |")
    lines += ["", "## Trials", ""]
    for a in result["attempts"]:
        s = a["signals"]
        lines += [
            f"### {a['payload_id']}  trial {a['trial']}  {'HIT' if a['success'] else ('BLOCKED' if s.get('blocked') else 'no hit')}",
            "",
            "**Prompt**",
            "",
            "```",
            a["input"].strip(),
            "```",
            "",
            "**Response (returned to caller)**",
            "",
            "```",
            a["output"].strip() or "(empty)",
            "```",
        ]
        if a["raw_output"] and a["raw_output"] != a["output"]:
            lines += [
                "",
                "**Raw response (before hardened output control)**",
                "",
                "```",
                a["raw_output"].strip(),
                "```",
            ]
        lines += [
            "",
            f"- violations: `{s.get('violations')}`",
            f"- raw_violations: `{s.get('raw_violations')}`",
            f"- blocked: `{s.get('blocked')}`  http: `{s.get('http_status')}`  timing_ms: `{s.get('timing_ms')}`",
            f"- safeguards fired: `{ {k: v for k, v in (s.get('safeguards') or {}).items() if v not in (False, 0, [], None, '')} }`",
            "",
        ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("scenario", help="scenario id, e.g. P1-01 or P1-03")
    p.add_argument("--mode", required=True, choices=nr.MODES)
    p.add_argument("--run", dest="run_type", default="canonical", choices=nr.RUN_TYPES)
    p.add_argument("--trials", type=int, default=None, help="trials per payload; default 1 canonical, 10 rate")
    p.add_argument("--url", default="http://127.0.0.1:8000")
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--out", type=Path, help="output json path; default evidence/<mode>/<id>-run_scenario-<run>-<date>.json")
    p.add_argument("--no-transcript", action="store_true", help="skip the .md transcript")
    args = p.parse_args()

    if args.trials is None:
        trials = 1 if args.run_type == "canonical" else 10
    else:
        trials = args.trials
    if args.run_type == "canonical" and trials != 1:
        print(f"note: canonical run forces one trial per payload, ignoring --trials {trials}", file=sys.stderr)
        trials = 1

    base = args.url.rstrip("/")
    try:
        result = _run(
            scenario_id=args.scenario,
            mode=args.mode,
            run_type=args.run_type,
            trials=trials,
            base=base,
            timeout=args.timeout,
        )
    except httpx.HTTPError as exc:
        print(f"could not reach the target at {base}: {exc}", file=sys.stderr)
        print("start it with:  APP_MODE=<mode> ./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000", file=sys.stderr)
        return 1

    problems = nr.validate(result)
    if problems:
        print("schema problems:\n  " + "\n  ".join(problems), file=sys.stderr)

    date = result["metadata"]["date"]
    stem = f"{result['scenario']}-run_scenario-{args.run_type}-{date}"
    out = args.out or (EVIDENCE / args.mode / f"{stem}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if not args.no_transcript:
        _write_transcript(result, out.with_suffix(".md"))

    t = result["summary"]["totals"]
    print("")
    print(f"wrote {out}")
    if not args.no_transcript:
        print(f"wrote {out.with_suffix('.md')}")
    print(f"returned-output successes: {t['successes']}/{t['trials']}   raw-output successes: {t.get('raw_successes')}/{t['trials']}")
    print("per payload:")
    for pid, d in result["summary"]["by_payload"].items():
        raw = result["summary"]["by_payload_raw"].get(pid, {}).get("rate", "-")
        print(f"  {pid:<34} returned {d['rate']:<7} raw {raw}")
    print("")
    print("Next: fill the observed-result / trial-count / severity / residual-risk")
    print("sections in the finding. The runner does not write those.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
