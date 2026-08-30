#!/usr/bin/env bash
# Run garak against the target for one scenario and one run type.
#
#   ./run.sh P1-01 canonical     temp 0, seed 42, 1 generation per prompt
#   ./run.sh P1-01 rate          temp 0.7, seed unset, 10 generations per prompt
#   ./run.sh P1-03 canonical
#   ./run.sh P1-03 rate
#
# The target must already be running in the mode you want to test:
#   APP_MODE=baseline ./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
#
# garak writes its report to garak_runs/ (gitignored). Copy the sanitized
# summary into RESULTS.md by hand; do not commit the raw report, it contains the
# canary in cleartext.
set -euo pipefail

SCENARIO="${1:?usage: run.sh <P1-01|P1-03> <canonical|rate>}"
RUNTYPE="${2:?usage: run.sh <P1-01|P1-03> <canonical|rate>}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$RUNTYPE" in
  canonical) CONFIG="$HERE/garak.rest.canonical.json"; GENERATIONS=1 ;;
  rate)      CONFIG="$HERE/garak.rest.rate.json";      GENERATIONS=10 ;;
  *) echo "run type must be canonical or rate" >&2; exit 2 ;;
esac

PROBE_FILE="$HERE/probes.$SCENARIO.txt"
[ -f "$PROBE_FILE" ] || { echo "no $PROBE_FILE" >&2; exit 2; }

# Join non-comment, non-blank lines with commas.
PROBES="$(grep -vE '^\s*(#|$)' "$PROBE_FILE" | paste -sd, -)"

OUT_DIR="$HERE/garak_runs"
mkdir -p "$OUT_DIR"
PREFIX="${SCENARIO}-${RUNTYPE}-$(date +%Y%m%d)"

echo "scenario=$SCENARIO runtype=$RUNTYPE generations=$GENERATIONS"
echo "probes=$PROBES"
echo

garak \
  --model_type rest \
  --generator_option_file "$CONFIG" \
  --probes "$PROBES" \
  --generations "$GENERATIONS" \
  --report_prefix "$PREFIX" \
  --narrow_output

REPORT="$(ls -t "$HOME"/.local/share/garak/garak_runs/"$PREFIX"*.report.jsonl 2>/dev/null | head -1 || true)"
[ -z "$REPORT" ] && REPORT="$(ls -t garak_runs/"$PREFIX"*.report.jsonl 2>/dev/null | head -1 || true)"

if [ -n "$REPORT" ]; then
  cp "$REPORT" "$OUT_DIR/"
  echo
  echo "report: $OUT_DIR/$(basename "$REPORT")"
  echo "normalize it with:"
  echo "  python scripts/normalize_results.py --tool garak \\"
  echo "    --input tests/garak/garak_runs/$(basename "$REPORT") \\"
  echo "    --scenario $SCENARIO --mode <baseline|hardened> --run-type $RUNTYPE \\"
  echo "    --out evidence/<mode>/$SCENARIO-garak-$RUNTYPE-$(date +%Y-%m-%d).json"
else
  echo "could not locate the garak report automatically; check ~/.local/share/garak/garak_runs/" >&2
fi
