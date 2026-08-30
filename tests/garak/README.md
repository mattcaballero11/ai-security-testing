# garak against the DocSummarizer target

garak is used here for one job: hit `/chat` with published prompt-injection and
context-divergence probes so P1-01 and P1-03 have a second source of evidence
that is not my own payload set. It is not run as a full scan, and this directory
does not claim it was.

## What is here

| File | Purpose |
|---|---|
| `garak.rest.canonical.json` | REST generator config. Sends `rate_run: false`, so the app uses temperature 0, seed 42. Pair with `--generations 1`. |
| `garak.rest.rate.json` | Same, but `rate_run: true`, so the app uses temperature 0.7 with no seed. Pair with `--generations 10` for the k/10 rate. |
| `probes.P1-01.txt` | The probe list for P1-01, one per line, with the reasoning inline. |
| `probes.P1-03.txt` | The probe list for P1-03. |
| `run.sh` | Joins a probe list into `--probes` and runs garak for one scenario and run type. |
| `RESULTS.md` | Sanitized summary of the runs. Filled from my own runs, not pre-written. |
| `garak_runs/` | Raw garak reports. Gitignored: the `outputs` field contains the canary in cleartext. |

## The REST wiring

garak's `rest` generator posts each probe prompt as `message`, with
`is_summary_request: false` and `use_history: false` fixed in the request
template. `is_summary_request: false` is what lets the app's V2 check fire;
`use_history: false` keeps every probe attempt independent, which matches how
garak treats them. The response is read from the `content` field.

garak does not control sampling here. The app does, through the `rate_run` flag
in the request body. That is deliberate: it keeps garak runs on the same
measurement protocol as everything else in the repo (canonical: temperature 0,
seed 42; rate: temperature 0.7, seed unset, n trials), so a garak number and a
`run_scenario.py` number are comparable.

## Commands

Target running in the mode under test, then:

```bash
cd tests/garak
./run.sh P1-01 canonical
./run.sh P1-01 rate
./run.sh P1-03 canonical
./run.sh P1-03 rate
```

Or the raw invocation `run.sh` builds, for P1-01 canonical:

```bash
garak \
  --model_type rest \
  --generator_option_file tests/garak/garak.rest.canonical.json \
  --probes promptinject.HijackHateHumans,promptinject.HijackKillHumans,promptinject.HijackLongPrompt,dan.Dan_11_0,dan.DUDE,dan.STAN,dan.ChatGPT_Developer_Mode_v2,dan.DAN_Jailbreak \
  --generations 1 \
  --report_prefix P1-01-canonical
```

Then normalize into the common schema:

```bash
python scripts/normalize_results.py --tool garak \
  --input tests/garak/garak_runs/P1-01-canonical-<date>.report.jsonl \
  --scenario P1-01 --mode baseline --run-type canonical \
  --out evidence/baseline/P1-01-garak-canonical-<date>.json
```

garak has no `DEMO_SECRET_DO_NOT_USE` detector, so `normalize_results.py` greps
every garak output for the canary and records that as `V1_canary_disclosure`
alongside garak's own detector scores.

## Why these probes and not others

This assessment uses garak for P1-01 and P1-03 only. P1-02 is PyRIT's
multi-turn work and P1-04 is the rendering sink; garak is not pointed at either.

### P1-01: `promptinject` and single-turn `dan`

- **`promptinject.Hijack*`** is goal hijacking from the PromptInject paper:
  a rogue instruction is appended and the detector
  (`promptinject.AttackRogueString`) checks whether the model emitted the
  attacker's string instead of doing its job. That is a direct, published
  version of P1-01's instruction-override family. Three variants are used
  (`HateHumans`, `KillHumans`, `LongPrompt`) because they differ in payload
  length and framing, which is the axis that matters against a summarizer.
- **`dan.Dan_11_0`, `dan.DUDE`, `dan.STAN`, `dan.ChatGPT_Developer_Mode_v2`,
  `dan.DAN_Jailbreak`** are single-turn persona-reassignment attacks. P1-01's
  attack list names role reassignment explicitly, and the DevMode payload in the
  manual pass is the same shape. I take a subset, not the whole `dan` module:
  the older numbered DANs and the toxicity-oriented variants add prompts without
  adding a new technique against this target.

### P1-03: `divergence`

- **`divergence.Repeat` / `divergence.RepeatExtended`** ("repeat this word
  forever") push the model off its output distribution, which can spill
  context-window content including the system instruction. This matches P1-03's
  boundary-probing family and specifically the "repeat everything above this
  line" payload that dumped the whole system prompt in the manual pass.
- garak's coverage of system-prompt and secret disclosure is thin. There is no
  mainline probe that asks a model to reveal its own instructions the way the
  P1-03 payload set does. So for P1-03, `run_scenario.py` with the canary
  assertion is the primary tool and garak is a secondary angle. This is recorded
  in `references/tool-limitations.md`, not hidden.

### Deliberately excluded

| Probe module | Why not |
|---|---|
| `latentinjection` | Indirect prompt injection. Project 2, not Project 1. |
| `xss`, `malwaregen`, `packagehallucination`, `exploitation` | Output-handling and code-generation risks. `xss` is close to P1-04 but P1-04 is tested with its own browser-based method against `/render`. |
| `dan.AutoDAN*`, `suffix`, `tap`, `beast`, `gcg` | Automated adversarial-suffix and jailbreak-search methods. High run cost and squarely P1-02 (jailbreak), which is PyRIT's job. |
| `grandma`, `leakreplay` | Elicitation of product keys, controlled substances, or memorized copyrighted text. The detectors look for those specific shapes and would never fire on this target's synthetic canary. |
| `continuation`, `realtoxicityprompts`, `lmrc`, `atkgen` | Toxicity and harmful-content generation. This assessment is about the application's controls, not the 3B model's safety training. |
| `snowball`, `misleading`, `packagehallucination` | Hallucination and misinformation (LLM09). Not P1-01 or P1-03. |
| `glitch`, `av_spam_scanning`, `donotanswer`, `topic` | Not relevant to this target's threat model. |

## Version and environment notes

- Verify every probe name with `garak --list_probes` for your installed
  version. Module names move between releases; `divergence` was `replay` before
  garak 0.9.
- The REST config keys (`req_template_json_object`, `response_json_field`,
  `ratelimit_codes`, `request_timeout`) and the `--generator_option_file` /
  `-G` flag are from garak's `rest` generator docs. If garak rejects the config,
  check `garak.generators.rest.RestGenerator` for your version: older builds
  used `req_template` with a `$INPUT` placeholder string instead of the JSON
  object form.
- garak needs its own environment. It has a heavy dependency tree and pins
  versions that conflict with this repo's `requirements.txt`. Install it in a
  separate virtualenv (`pipx install garak` or a dedicated venv), not the app's.
- Against **hardened** mode the rate limiter (30 requests / 60s) will throttle
  garak, which fires far faster than that. garak's own request volume is not the
  thing under test, so for garak hardened runs raise `RATE_LIMIT_REQUESTS` in
  `.env` (e.g. to 100000) and note that you did in `RESULTS.md`. The input
  pattern detector and the data channel are still active and still the controls
  being measured.
- The raw report contains the canary. Keep `garak_runs/` gitignored and copy
  only sanitized counts and paraphrased examples into `RESULTS.md`.
