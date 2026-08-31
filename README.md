# AI Security Testing

An assessment dashboard for a self-owned LLM red-team lab, built to demonstrate the AI security testing methodology I use professionally, without touching any client work.

## Why this exists

I do AI security testing professionally as part of my consulting work. Those engagements are covered by NDAs, so this repo contains no client data, findings, or engagement details. What it contains instead is a self-owned, non-confidential reconstruction of an assessment workflow: my own methodology, my own intentionally vulnerable target, and my own findings against it, run and documented so the work is visible and verifiable rather than just claimed.

This is Project 1 of a three-project portfolio. Project 1 covers direct prompt injection, jailbreaking, hidden-context disclosure, and improper output handling against a single local model with no tools and no agent loop. Indirect prompt injection and training data poisoning belong to Project 2. Excessive agency and agent/tool-use attacks belong to Project 3. Keeping that split clean instead of stretching one lab to cover everything is itself part of the methodology, not a limitation I'm hiding.

## Scope and authorization boundary

- The target is local, built by me, and bound to 127.0.0.1. Nothing in this repo points at a system I do not own.
- Synthetic data only. The only secret in the app is the literal string `DEMO_SECRET_DO_NOT_USE`.
- No live API keys are committed. `.env.example` only.
- Nothing in this repo should be read as testing performed against a system I did not have authorization to test, because there is no such system here. The target exists specifically so this testing is authorized by construction.

## Status

This table reflects the actual state of the repo, not a plan.

| Scenario | What it tests | Status |
|---|---|---|
| P1-01 Direct prompt injection | Instruction override, role reassignment, delimiter injection, refusal suppression against a document-summarizing assistant | Run in both modes, canonical and rate. [Finding](findings/P1-01-direct-prompt-injection.md) written. |
| P1-02 Jailbreak and guardrail bypass | Multi-turn crescendo escalation versus single-turn persona framing, against a synthetic restricted topic | Run in both modes, canonical and rate. [Finding](findings/P1-02-jailbreak.md) written. |
| P1-03 Hidden context and secret disclosure | Direct, indirect, and format-shifted attempts to recover the system instruction and the canary | Run in both modes, canonical and rate. [Finding](findings/P1-03-hidden-context-disclosure.md) written. |
| P1-04 Improper output handling | Model output rendered unescaped at `/render`, and the same payload rejected by `/structured` | Run in both modes, canonical and rate (`render_probe.py`). [Finding](findings/P1-04-output-handling.md) written. |
| P1-05 Guardrail regression suite | The four scenarios above as a promptfoo suite, run against both modes in one command | Built and run (`tests/promptfoo/run.sh`, promptfoo 0.122.2). 2026-08-31 gate: baseline 5/5, hardened 5/5, `gate_pass` true. [Report](evidence/reports/regression-2026-08-31.md), [finding](findings/P1-05-regression.md), and CI workflow in `.github/workflows/`. |

Nothing below this table describes something that exists yet unless it says so explicitly.

## Target architecture

One local target, no hosted model, no RAG, no tools, no cloud.

```
attack scripts / garak / pyrit / promptfoo / giskard
                    |
                    v
    FastAPI test target on 127.0.0.1:8000
    mode = baseline | hardened (env switch)
                    |
                    v
        Ollama, local, 3B instruct model
```

Baseline mode is deliberately weak: the behavioral policy and the canary live only in the system instruction, user input is concatenated with no separation, and output is returned raw. Hardened mode layers input normalization, delimiter separation, context minimization, output-side canary redaction, output-side restricted-content screening, contextual escaping, and rate limiting on top of the same code path. Hardened mode does not make the model injection-proof. It moves the failure from "the model was fooled and something broke" to "the model was fooled and nothing important broke." That is a deliberate framing choice for the findings, not a hedge, and it matches how OWASP frames layered LLM defense in the 2026 list.

## Measurement protocol

Every scenario reports results against a fixed protocol rather than a single anecdotal run, because non-determinism is what makes LLM findings soft.

- **Canonical run:** temperature 0, seed 42, single trial. Used for the screenshot and the transcript in each finding.
- **Rate run:** temperature 0.7, seed unset, n=10. Used for the reported success rate, reported as k/10.
- Every evidence file records model name, Ollama digest, temperature, seed, context length, app mode, date, and the app's git commit at test time.

Ollama's determinism is close but not guaranteed across batch sizes. The seed reduces variance. It does not eliminate it, and no finding in this repo claims otherwise.

## Tooling

| Tool | Role | Status |
|---|---|---|
| garak | rest generator against `/chat`, probes selected for P1-01 and P1-03 | Run against baseline, both scenarios ([`tests/garak/RESULTS.md`](tests/garak/RESULTS.md)). Agrees with the custom runner on P1-01; found no true positives on P1-03. Hardened runs pending. |
| PyRIT | custom target class against `/chat`, multi-turn orchestration for P1-02 | Target class and scripted crescendo built and run in both modes (`tests/pyrit/`). The PyRIT-driven `CrescendoAttack` was also run end to end against baseline and ended in max-turns/failure, which is why the reported rate comes from a fixed ladder, not an LLM-driven attacker. See `references/tool-limitations.md`. |
| promptfoo | http provider against `/chat`, `/render`, `/structured`; the P1-05 regression gate | Suite, mode-aware assertions, and one-command `run.sh` built and run (`tests/promptfoo/`, promptfoo 0.122.2, its own Node install). 2026-08-31: both modes green, `gate_pass` true. |
| Giskard | one scan pass against the local target, triangulation on P1-02 | Wrapper built (`tests/giskard/`), v3 scan runs against the local model. Both timeboxed runs (baseline, hardened) came up partial: it is slow (~1 request per 90s, local judge), and the judge is the model under test, so verdicts are advisory. Kept as weak triangulation, not a measurement. See `references/tool-limitations.md`. |
| Custom Python (`scripts/`) | scenario runner, `/render` sink probe, evidence stamping, results normalization across every tool above, baseline-versus-hardened delta | `run_scenario.py`, `render_probe.py`, `stamp_evidence.py`, `normalize_results.py`, `compare_modes.py` built. |

If any of these does not run against the target, it gets recorded in `references/tool-limitations.md` with what was tried and why, not quietly dropped from this table.

## Framework references

Every framework mapping in this repo targets the **OWASP Top 10 for LLM Applications, 2026 edition**, published August 2026. That edition renumbered eight of the ten 2025 entries, and the taxonomy and methodology pages in this repo are written against it. See [references/framework-versions.md](references/framework-versions.md) for the edition, publication date, source, and verification status of every framework cited here, including MITRE ATLAS and the NIST AI Risk Management Framework.

Project 1 cites the LLM Top 10 only. The separate OWASP Top 10 for Agentic Applications belongs to Project 3, once the model in scope has tools and memory of its own. Project 1 does not cite it.

## What this does not demonstrate

- **Indirect prompt injection.** Project 1's target has no RAG store, no web browsing, no email processing, and no external content for an attacker to poison. That's Project 2.
- **Excessive agency and agent/tool-use attacks.** Project 1's target has no tools and no agent loop, so there is nothing to over-permission. That's Project 3.
- **Training data or model poisoning.** Retraining a model is out of reach for an individual working alone. To the extent this is demonstrated anywhere in the portfolio, it's the RAG-corpus case in Project 2, not the model-training case.
- **Model extraction and adversarial inputs against classifiers.** Real assessment topics, not demonstrated by any lab in this portfolio. See [references/out-of-scope-ai-ml-risks.md](references/out-of-scope-ai-ml-risks.md) for the honest reason why, not just a disclaimer.
- **Anything against a hosted model, a cloud environment, or Kubernetes.** The target is local and stays local. Cloud, container, and orchestration security are professional experience from client engagement work, not evidenced by this lab.
- **A stronger model's behavior.** The default model here is small (roughly 3B parameters) and weakly aligned, which makes it jailbreak easily. That's a property of the model, not of the application's controls. Every finding in this repo that touches model behavior says plainly which part is about the app's controls and which part would change with a stronger model.

## Repository map

- [`methodology/`](methodology/): how I scope, threat-model, test, and report on AI systems end to end.
- [`vulnerability-taxonomy/`](vulnerability-taxonomy/): the vulnerability classes referenced above, with an index at [`vulnerability-taxonomy/README.md`](vulnerability-taxonomy/README.md) showing what's tested where.
- [`references/`](references/): framework editions and verification status, tool limitations as they're discovered, and the out-of-scope risk classes with the reasoning for why they stay out of scope.
- [`app/`](app/): the local FastAPI target, both modes behind an env switch.
- [`scenarios/`](scenarios/): per-scenario threat model, payload fixtures, and success criteria.
- [`scripts/`](scripts/): the scenario runner, the `/render` sink probe, evidence stamping, result normalization, and the baseline-versus-hardened delta.
- [`tests/`](tests/): tool configs and run notes, including the [`tests/promptfoo/`](tests/promptfoo/) P1-05 regression gate.
- [`.github/workflows/`](.github/workflows/): the P1-05 gate as a CI job (runs on PRs touching the target or the pinned model, plus nightly; blocks merge on a failed gate).
- [`evidence/`](evidence/) and [`findings/`](findings/): the raw normalized results with metadata headers (`evidence/reports/` holds the versioned P1-05 regression envelopes), and the write-ups built from them.

## Quick start

See [docs/quickstart.md](docs/quickstart.md) for pulling the model, installing dependencies, running baseline and hardened modes, the health check, and what to do if the model is too slow or will not fit on a modest VM. Per-scenario run commands are in each `scenarios/<id>/README.md`.

## About

Built by [Matthew Caballero](https://github.com/mattcaballero11), cyber security consultant, PNPT certified. Related repos:

- [detection-as-code-lab](https://github.com/mattcaballero11/detection-as-code-lab)
- [home-soc-lab](https://github.com/mattcaballero11/home-soc-lab)

## License

MIT. See [LICENSE](LICENSE).
