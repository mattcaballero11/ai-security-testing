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

- Edition: continuously updated matrix, not versioned by edition number.
- Accessed: 2026-08-30
- Source: atlas.mitre.org (technique pages verified through the MISP-galaxy mirror of the ATLAS dataset; atlas.mitre.org technique deep-links were returning 404 to the fetch tool on the access date, so the matrix itself should be re-checked by hand before publishing)
- Verified by me on: 2026-08-30

Techniques cited in this repo:

| ID | Name | Tactic(s) |
|---|---|---|
| AML.T0051 | LLM Prompt Injection | Initial Access, Persistence, Privilege Escalation, Defense Evasion |
| AML.T0051.000 | LLM Prompt Injection: Direct | same as parent |
| AML.T0051.001 | LLM Prompt Injection: Indirect | same as parent |
| AML.T0054 | LLM Jailbreak | Privilege Escalation, Defense Evasion |
| AML.T0056 | LLM Meta Prompt Extraction | Discovery, Exfiltration |
| AML.T0057 | LLM Data Leakage | Exfiltration |

P1-01 is AML.T0051.000 (Direct). P1-03 is AML.T0056 (Meta Prompt Extraction) for the system-instruction recovery and AML.T0057 (Data Leakage) for the canary, with AML.T0051.000 as the delivery technique. P1-02 is AML.T0054 (Jailbreak). A secondary source mentioned an AML.T0051.002 "Triggered" sub-technique; it is not in the MISP mirror of the dataset as of this date, so it is not cited here.

## NIST AI Risk Management Framework

- Edition: AI RMF 1.0
- Published: January 2023
- Companion: NIST AI 600-1, "Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile", published 26 July 2024. Cite this alongside AI RMF 1.0 for anything generative-AI specific.
- Source: https://www.nist.gov/itl/ai-risk-management-framework and https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf
- Verified by me on: 2026-08-30
- Note: no repo finding currently cites NIST AI RMF directly. Recorded here so that if a finding or the methodology adds a NIST reference, the edition and the GenAI Profile are already pinned.

---

Everything above was verified on 2026-08-30. Re-verify before any public push, especially the MITRE ATLAS technique names (checked via the MISP mirror this round, not the live atlas.mitre.org pages) and the exact OWASP Agentic ASI category names when Project 3 begins.
