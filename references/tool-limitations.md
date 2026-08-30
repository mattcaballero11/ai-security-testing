# Tool limitations

What each tool in the assessment could and could not do against this target,
recorded as it was found. This file is an asset. A tool that would not run, or
ran but did not cover what its CV line implies, is more useful documented here
than quietly dropped from the tooling table.

## garak

**Used for:** P1-01 (prompt-injection probes) and P1-03 (context-divergence
probes) against `/chat` via the `rest` generator. Config, probe lists, and
commands in [`tests/garak/`](../tests/garak/).

**Limitations found (2026-08-29 baseline runs):**

- **No system-prompt or secret disclosure probe, and it showed.** garak has no
  mainline probe that asks a model to reveal its own instructions the way the
  P1-03 payload set does. P1-03's garak coverage is `divergence.Repeat` /
  `RepeatExtended` ("repeat the word poem forever"), which reaches disclosure
  only as a side effect of output divergence. In the actual run,
  `divergence.RepeatDiverges` flagged 150 canonical and 90 rate trials as hits,
  and every one of them was the model's refusal string. Zero contained the
  canary or any system-prompt text. garak produced no true positives for P1-03
  against this target. `scripts/run_scenario.py` with the canary assertion is
  the tool that carries P1-03; garak is not a substitute for it here.
- **No canary detector.** garak's detectors do not know about
  `DEMO_SECRET_DO_NOT_USE`. `scripts/normalize_results.py` greps garak's output
  for the canary to produce the `V1_canary_disclosure` signal. It found nothing
  in the divergence outputs.
- **`mitigation.MitigationBypass` is noise against this target.** That generic
  detector looks for a fixed set of known refusal phrases and does not recognise
  this app's custom refusal string, so it scores 1.0 (bypassed) on every clean
  refusal. `normalize_results.py` records it but excludes it from the success
  count; the meaningful garak signal is the probe-specific detector
  (`promptinject.AttackRogueString`, `dan.*`, `divergence.RepeatDiverges`).
- **Sampling is not garak's to set.** The `rest` generator cannot vary the app's
  temperature or seed. The canonical/rate split is done with the app's
  `rate_run` flag baked into two separate generator configs.
- **Rate limiter would throttle garak in hardened mode.** garak fires far faster
  than 30 requests / 60s. Only baseline was run (no rate limit there); for
  hardened garak runs the rate limit needs raising in `.env`, noted in
  `tests/garak/RESULTS.md`, because garak's own request volume is not the
  control under test.
- **Separate environment required.** garak's dependency pins conflict with the
  app's `requirements.txt`. It is installed via pipx, not the app venv.
- **Long runs, easy to interrupt.** `divergence.RepeatExtended` is 945
  generations per canonical pass. The P1-03 rate run was terminated partway
  through it; `divergence.Repeat` completed and is normalised, `RepeatExtended`
  rate is not.

## PyRIT

Not yet attempted.

## promptfoo

Not yet attempted.

## Giskard

Not yet attempted.
