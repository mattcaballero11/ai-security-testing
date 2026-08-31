# Giskard scan for P1-02 triangulation

Giskard's role in this assessment (build spec section 5) is **one independent
scan pass to triangulate the P1-02 jailbreak finding**. It is not a fourth
scenario set and the effort is capped at one session.

| File | What it is |
|---|---|
| `scan.py` | Wraps `POST /chat` as a Giskard target, routes Giskard's generator and judge LLM calls to the local Ollama model, and runs `giskard.scan.generate_suite` with the prompt-injection and crescendo scenario generators. |
| `requirements.txt` | Giskard v3 pin for its own venv. |
| `RESULTS.md` | Sanitized summary of the run. |
| `giskard_runs/` | Raw `SuiteResult` JSON. Gitignored. |

## What Giskard v3 is

Giskard did a full rewrite in 2025 (`giskard-scan`, the successor to the v2 LLM
scan and RAGET). v3 generates adversarial **multi-turn** scenarios from a
plain-language description of the target, runs them, and scores the answers with
an LLM judge. Both the generator and the judge need an LLM provider.

## Setup

```bash
python3 -m venv ~/venvs/giskard
~/venvs/giskard/bin/pip install -r tests/giskard/requirements.txt
```

Then, with the app target running in the mode under test:

```bash
DO_NOT_TRACK=1 ~/venvs/giskard/bin/python tests/giskard/scan.py --mode baseline --max-scenarios 8
DO_NOT_TRACK=1 ~/venvs/giskard/bin/python tests/giskard/scan.py --mode hardened --max-scenarios 8
```

Normalise each run:

```bash
./venv/bin/python scripts/normalize_results.py --tool giskard \
  --input tests/giskard/giskard_runs/baseline-<date>.json \
  --scenario P1-02 --mode baseline --run-type rate \
  --out evidence/baseline/P1-02-giskard-<date>.json
./venv/bin/python scripts/stamp_evidence.py --run-type rate evidence/baseline/P1-02-giskard-<date>.json
```

## What worked and what did not (2026-08-30, baseline, 2 scenarios)

**Worked.** Giskard v3 installs on Python 3.14 in its own venv. The `/chat`
wrapper is accepted as a target. LLM routing to Ollama works: `giskard.llm.configure("ollama",
provider="openai", base_url="http://127.0.0.1:11434/v1", api_key="ollama")` plus
`set_default_generator(Generator(model="ollama/llama3.2:3b-instruct-q4_K_M"))`.
A trivial routed completion returns in ~2s. Giskard generated coherent
character-roleplay and encoding-injection scenarios aimed at the Aurelian Ledger
topic and ran them multi-turn against the target.

**Did not.** Two problems, both about the model, not the wiring, both recorded in
[`references/tool-limitations.md`](../../references/tool-limitations.md):

1. **Throughput.** A 2-scenario run took 8.6 minutes. Every generator and judge
   call is a 15 to 40 second local inference and there are many per scenario. An
   8-scenario pass is 35 to 45 minutes. Usable for one triangulation run, not for
   iteration.
2. **The judge is the model under test.** Giskard's verdicts came back as
   low-confidence fails ("rule compliance is uncertain", "output compliance but
   the agent did not comply with the rule"). `scripts/normalize_results.from_giskard`
   therefore treats Giskard's status as advisory and takes success from the same
   canary grep used for garak. The finding weighs Giskard's scenarios as a second
   source of attack *ideas*, not as an independent oracle.

In the 2-scenario baseline run the model refused every Giskard interaction with
the fixed refusal string, which agrees with `run_scenario.py` and the manual
pass: the single-turn persona and encoding attacks are stopped by the model's
own caution, and the multi-turn crescendo in `tests/pyrit/` is what actually
gets through.
