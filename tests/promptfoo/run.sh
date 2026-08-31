#!/usr/bin/env bash
# P1-05 regression gate: run the promptfoo suite against BOTH modes in one
# command and write a single versioned JSON report plus a Markdown delta.
#
#   tests/promptfoo/run.sh
#
# What it does:
#   1. starts the target as APP_MODE=baseline, waits for /healthz
#   2. runs the promptfoo suite with PROMPTFOO_MODE=baseline
#   3. restarts the target as APP_MODE=hardened, waits
#   4. runs the suite with PROMPTFOO_MODE=hardened
#   5. merges both into evidence/reports/regression-<date>.json (versioned)
#   6. renders evidence/reports/regression-<date>.md via scripts/compare_modes.py
#
# Exit code is 0 only if BOTH modes are green (baseline: attacks still land,
# hardened: controls still hold). Any red is the regression.
#
# Requirements: Node >= 18 and promptfoo. Install once:
#     cd tests/promptfoo && npm install         # local, uses package.json pin
# or globally:  npm install -g promptfoo
#
# Override the target with TARGET_URL=... to point at an already-running server;
# in that case pass --single <baseline|hardened> to run just that mode.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SUITE_DIR="$REPO_ROOT/tests/promptfoo"
REPORTS_DIR="$REPO_ROOT/evidence/reports"
VENV_PY="$REPO_ROOT/venv/bin/python"
DATE="$(date -u +%Y-%m-%d)"
SUITE_VERSION="1.0"
PORT="${APP_PORT:-8000}"
TARGET_URL="${TARGET_URL:-http://127.0.0.1:$PORT}"
SINGLE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --single) SINGLE="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$REPORTS_DIR"
TMP="$(mktemp -d)"
cleanup () { rm -rf "$TMP"; [ -n "${SERVER_PID:-}" ] && kill "$SERVER_PID" 2>/dev/null || true; pkill -f "uvicorn app.main:app .*--port ${PORT}" 2>/dev/null || true; }
trap cleanup EXIT

# --- locate promptfoo -------------------------------------------------------
if [ -x "$SUITE_DIR/node_modules/.bin/promptfoo" ]; then
  PROMPTFOO="$SUITE_DIR/node_modules/.bin/promptfoo"
elif command -v promptfoo >/dev/null 2>&1; then
  PROMPTFOO="promptfoo"
elif command -v npx >/dev/null 2>&1; then
  PROMPTFOO="npx --yes promptfoo@latest"
else
  echo "promptfoo not found. Install Node >= 18 then:  cd tests/promptfoo && npm install" >&2
  echo "See tests/promptfoo/README.md and references/tool-limitations.md." >&2
  exit 3
fi

stop_server () {
  [ -n "${SERVER_PID:-}" ] && kill "$SERVER_PID" 2>/dev/null || true
  # uvicorn is a child of the backgrounded subshell; also clear the port
  pkill -f "uvicorn app.main:app .*--port $PORT" 2>/dev/null || true
  for _ in $(seq 1 10); do
    curl -sf "$TARGET_URL/healthz" >/dev/null 2>&1 || return 0
    sleep 1
  done
}

start_server () {
  local mode="$1"
  stop_server
  echo ">> starting target APP_MODE=$mode"
  ( cd "$REPO_ROOT" && exec env APP_MODE="$mode" APP_PORT="$PORT" "$VENV_PY" -m uvicorn app.main:app \
      --host 127.0.0.1 --port "$PORT" >"$TMP/uvicorn-$mode.log" 2>&1 ) &
  SERVER_PID=$!
  for _ in $(seq 1 40); do
    if curl -sf "$TARGET_URL/healthz" | grep -q "\"mode\":\"$mode\""; then
      echo ">> target up in $mode mode"; return 0
    fi
    sleep 1
  done
  echo "target did not come up in $mode mode; log:" >&2
  cat "$TMP/uvicorn-$mode.log" >&2
  exit 4
}

run_mode () {
  local mode="$1"
  if [ -z "${TARGET_URL_FIXED:-}" ]; then start_server "$mode"; fi
  echo ">> promptfoo eval PROMPTFOO_MODE=$mode"
  ( cd "$SUITE_DIR" && PROMPTFOO_MODE="$mode" TARGET_URL="$TARGET_URL" \
      $PROMPTFOO eval -c promptfooconfig.yaml --no-cache \
      --output "$TMP/run-$mode.json" ) || true
  "$VENV_PY" "$SUITE_DIR/summarize_run.py" --mode "$mode" \
      --input "$TMP/run-$mode.json" --out "$TMP/summary-$mode.json" || true
}

MODES=(baseline hardened)
if [ -n "$SINGLE" ]; then MODES=("$SINGLE"); TARGET_URL_FIXED=1; fi

for m in "${MODES[@]}"; do run_mode "$m"; done

# --- versioned envelope ----------------------------------------------------
OUT_JSON="$REPORTS_DIR/regression-$DATE.json"
GIT_COMMIT="$(cd "$REPO_ROOT" && git rev-parse --short HEAD 2>/dev/null || echo unknown)"
MODEL_DIGEST="$(curl -sf "$TARGET_URL/healthz" | "$VENV_PY" -c 'import sys,json;print(json.load(sys.stdin).get("model_digest",""))' 2>/dev/null || echo "")"

"$VENV_PY" - "$OUT_JSON" "$SUITE_VERSION" "$DATE" "$GIT_COMMIT" "$MODEL_DIGEST" \
  "$TMP/summary-baseline.json" "$TMP/summary-hardened.json" <<'PY'
import json, sys, pathlib
out, version, date, commit, digest = sys.argv[1:6]
env = {
    "report": "P1-05 guardrail regression",
    "suite_version": version,
    "generated": date,
    "git_commit": commit,
    "model_digest": digest,
    "run_type": "canonical",
    "modes": {},
}
for path in sys.argv[6:8]:
    p = pathlib.Path(path)
    if not p.exists():
        continue
    d = json.loads(p.read_text())
    env["modes"][d["mode"]] = d
env["gate_pass"] = all(m.get("green") for m in env["modes"].values()) and len(env["modes"]) > 0
pathlib.Path(out).write_text(json.dumps(env, indent=2) + "\n")
print(f"wrote {out}  gate_pass={env['gate_pass']}")
PY

# --- markdown delta ------------------------------------------------------
"$VENV_PY" "$REPO_ROOT/scripts/compare_modes.py" --regression "$OUT_JSON" \
  --out "$REPORTS_DIR/regression-$DATE.md"

echo
echo "report:  $OUT_JSON"
echo "delta:   $REPORTS_DIR/regression-$DATE.md"

"$VENV_PY" -c '
import json,sys
d=json.load(open(sys.argv[1]))
sys.exit(0 if d.get("gate_pass") else 1)
' "$OUT_JSON"
