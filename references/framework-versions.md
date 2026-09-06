# Framework Versions

This file records the exact edition of every public framework this repo cites, so a stale citation is a fixable bug rather than a silent inaccuracy. Update it any time a citation is added or a framework publishes a new edition, and re-verify everything below before any public push.

## OWASP Top 10 for LLM Applications

- Edition: 2026
- Published: 4 August 2026 (genai.owasp.org resource page; some secondary write-ups say 3 or 5 August. The month and year are not in dispute.)
- Source: https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/ and https://genai.owasp.org/llm-top-10/
- Verified by me on: 2026-08-30 (against genai.owasp.org, the OWASP project GitHub, and cross-checked against Giskard, Akamai, and Help Net Security summaries)

The 2026 list, with the 2025 position for each entry:

| 2026 | Name | 2025 |
|---|---|---|
| LLM01 | Prompt Injection | LLM01 |
| LLM02 | Sensitive Information Disclosure | LLM02 |
| LLM03 | Excessive Agency | LLM06 |
| LLM04 | Supply Chain | LLM03 |
| LLM05 | Data and Model Poisoning | LLM04 |
| LLM06 | Unbounded Consumption | LLM10 |
| LLM07 | Misinformation | LLM09 |
| LLM08 | Hidden Context Exposure | LLM07 (was System Prompt Leakage; renamed and re-scoped) |
| LLM09 | Vector and Embedding Weaknesses | LLM08 |
| LLM10 | Improper Output Handling | LLM05 |

Confirmed for this repo's citations: P1-01 maps to LLM01, P1-03 maps to LLM02 and LLM08, P1-04 maps to LLM10. All three are current 2026 numbers and names.

## OWASP Top 10 for Agentic Applications

- Edition: 2026
- Published: 9 December 2025
- Source: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- Verified by me on: 2026-08-30 (publication and that it uses ASInn identifiers, cross-checked against Palo Alto Networks and NeuralTrust summaries; the exact ASI01 to ASI10 names still need confirming from the OWASP PDF when Project 3 starts citing them)
- Note: Project 1 in this repo does not cite this list. It is recorded here because Project 3 will, and because taxonomy pages in this repo (excessive-agency.md, agent-tool-use-attacks.md) need to say clearly why an agentic-risk category is not tested here. The LLM list covers the model as a component; the Agentic list takes over once the model is an actor with tools and memory.

## MITRE ATLAS

- Edition: continuously updated matrix, not versioned by edition number; the site itself stamps each technique page with a monthly permalink (currently v2026.08) and a per-technique "Last Modified" date.
- Accessed and re-verified: 2026-09-06
- Source: atlas.mitre.org, cross-checked against the machine-readable STIX export at `github.com/mitre-atlas/atlas-navigator-data` (`dist/stix-atlas.json`), which is fetchable directly and is now the preferred verification method — it doesn't depend on the site's client-side routing the way a plain HTTP fetch of a technique deep-link does. atlas.mitre.org technique deep-links still return 404 to a non-JS fetch (confirmed again on the access date above); loading the site in a real browser and letting it client-route, or reading the STIX export, both work.
- Verified by me on: 2026-09-06 (previous verification, 2026-08-30 via the MISP-galaxy mirror, is superseded — it had two errors, corrected below)

Techniques cited in this repo:

| ID | Name | Tactic(s) |
|---|---|---|
| AML.T0051 | LLM Prompt Injection | Execution |
| AML.T0051.000 | LLM Prompt Injection: Direct | same as parent |
| AML.T0051.001 | LLM Prompt Injection: Indirect | same as parent |
| AML.T0051.002 | LLM Prompt Injection: Triggered | same as parent |
| AML.T0054 | LLM Jailbreak | Defense Evasion, Privilege Escalation |
| AML.T0056 | Extract LLM System Prompt | Exfiltration |
| AML.T0057 | LLM Data Leakage | Exfiltration |

P1-01 is AML.T0051.000 (Direct). P1-03 is AML.T0056 for the system-instruction recovery and AML.T0057 (LLM Data Leakage) for the canary, with AML.T0051.000 as the delivery technique. P1-02 is AML.T0054 (LLM Jailbreak).

**Two corrections from the 2026-08-30 pass, found on re-verification:**

1. **AML.T0051's tactic list was wrong.** It was recorded as "Initial Access, Persistence, Privilege Escalation, Defense Evasion" — that was a guess extrapolated from the technique's prose description, not read off the actual technique page, and it was wrong. The live page (and the STIX export) both give AML.T0051 exactly one tactic: **Execution**. Fixed in every finding that cited it (P1-01, P1-04).
2. **AML.T0056 was renamed.** It is no longer "LLM Meta Prompt Extraction" — the current name is **"Extract LLM System Prompt"** (the mitigation text still uses "meta prompt extraction" as legacy wording, which is how the old name is traceable). Its tactic list also dropped from "Discovery, Exfiltration" to **just Exfiltration**. Fixed in P1-03.

AML.T0051.002 "Triggered" is real and current (tactic: Execution, same as its parent) — the 2026-08-30 note that it "is not in the MISP mirror... so it is not cited here" was accurate about the mirror at the time but is now stale; it's listed above for completeness. It's not cited by name in any finding because none of this repo's scenarios are event-triggered injection.

**Also checked and deliberately not cited:** AML.T0077 "LLM Response Rendering" (tactic: Exfiltration) looked like a possible fit for P1-04 on the name alone. Its actual definition is narrower and different: getting the LLM to emit a markdown/HTML image tag whose URL parameters carry private data to an attacker-controlled server, exfiltrated the moment the client renders it — a covert-channel technique, not "output rendered without escaping." P1-04 is the latter, so AML.T0051 (the injection chain) remains the closest fit and T0077 is not cited.

## NIST AI Risk Management Framework

- Edition: AI RMF 1.0
- Published: January 2023
- Companion: NIST AI 600-1, "Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile", published 26 July 2024. Cite this alongside AI RMF 1.0 for anything generative-AI specific.
- Source: https://www.nist.gov/itl/ai-risk-management-framework and https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf
- Verified by me on: 2026-08-30
- Note: no repo finding currently cites NIST AI RMF directly. Recorded here so that if a finding or the methodology adds a NIST reference, the edition and the GenAI Profile are already pinned.

---

Everything above was verified on 2026-08-30. Re-verify before any public push, especially the MITRE ATLAS technique names (checked via the MISP mirror this round, not the live atlas.mitre.org pages) and the exact OWASP Agentic ASI category names when Project 3 begins.
