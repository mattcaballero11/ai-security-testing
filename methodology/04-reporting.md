# Reporting

## What this page covers

The report is the deliverable. Everything else in the methodology exists to produce findings, and the report is how those findings reach the people who can act on them. A technically brilliant assessment with a poorly written report is a wasted assessment, because the client's security decisions are made from the report, not from the assessor's memory of what they found.

This page covers how to structure findings, calibrate severity, present evidence, write remediation guidance, and assemble the full report for an AI security assessment. The format is close to a traditional penetration test report with adjustments for AI-specific findings, because the audience (security teams, engineering leads, executives) is the same audience that reads traditional pentest reports and they expect a familiar structure.

## Report structure

### Executive summary

One to two pages. Written for someone who will not read the rest of the report. It answers four questions:

1. What was tested? The system's name, purpose, architecture summary (one paragraph, not the full architecture diagram), and the scope of the assessment.
2. What did you find? The finding count by severity (critical, high, medium, low, informational) and a one-sentence summary of the most important findings. No technical detail here. "The system's customer-facing agent can be manipulated through prompt injection to access internal customer records and transmit them to an external address" is the right level. The how comes later.
3. What's the overall risk posture? A qualitative assessment of the system's security. Is this system ready for production? What's the most serious risk? This is the paragraph the executive will quote in their email to the security team.
4. What should they do first? The top three to five actions, ordered by impact. Not the full remediation list. The things that matter most, stated plainly enough that someone who stopped reading here would still know the right next steps.

### Scope and methodology

What was in scope, what was out of scope, what methodology was followed, what tools were used, what access was provided, and how many hours were spent. This section sets the frame for interpreting the findings. If model extraction testing was out of scope, say so here so the client doesn't assume they were tested for it.

Include the dates of testing, the model version tested (models get updated; findings may not reproduce on a newer version), and any limitations encountered. If the client didn't provide system prompt access and you had to extract it, note that. If certain tools were inaccessible during testing, note that. If the time allocation was insufficient for complete coverage of a particular area, note that. This section protects both you and the client.

### Findings

Each finding is a self-contained unit. A reader should be able to understand any single finding without reading the others. The format:

**Title.** A clear, specific description of what's wrong. "Prompt Injection in Customer Support Agent Enables Unauthorized Refund Processing" is useful. "Prompt Injection Vulnerability" is not. The title should tell the reader the attack and the consequence in one line.

**Severity.** Critical, High, Medium, Low, or Informational. Calibrated to business impact, not to technical impressiveness. A technically elegant jailbreak with no downstream consequence is low or medium. A simple prompt injection that chains to data exfiltration is critical. More on severity calibration below.

**Description.** What the vulnerability is, in plain language. One to three paragraphs. Explain the vulnerability class (prompt injection, excessive agency, insecure output handling) briefly so the reader has context, then explain the specific instance you found. The description should make sense to a security engineer who hasn't done AI security before.

**Attack chain.** If the finding involves multiple steps, document the full chain. Step 1: attacker does X. Step 2: model does Y. Step 3: system does Z. Step 4: impact is W. Each step with enough detail to follow. For multi-step chains, a numbered sequence is clearer than prose.

**Reproduction steps.** Exact steps to reproduce the finding. The prompt you sent, the model's response, the tool calls that fired, the outcome. Specific enough that someone else could reproduce it independently. If the finding depends on a specific sequence of messages, include the full sequence. If it depends on content planted in a data source, include that content and where it was placed.

**Evidence.** Screenshots, full prompt-and-response transcripts, tool call logs, network captures, before-and-after comparisons. Annotate the evidence so the reader knows what they're looking at. A screenshot without context is noise. A screenshot with a red box around the leaked system prompt and a caption explaining what's visible is evidence.

**Impact.** What could an attacker actually do with this? Not what's theoretically possible but what's practically achievable given the system's architecture and the attacker's access level. If the finding enables data exfiltration, estimate the scope of data at risk. If it enables unauthorized actions, name the specific actions. If it bypasses a compliance control, name the compliance requirement.

**Remediation.** Specific, actionable guidance for fixing this finding. Not "implement input validation" but "apply HTML entity encoding to model output before rendering in the chat interface" or "reduce the database tool's permissions from read-write to read-only by changing the service account configuration at [specific location]" or "enforce the confirmation step for the email tool in the application layer at [specific code path] rather than relying on the system prompt instruction."

Each remediation recommendation should pass two tests. First, could the engineering team implement it without coming back to ask you what you meant? If not, it's not specific enough. Second, would implementing it actually fix the finding? If the recommendation is "improve prompt engineering" and the finding is insecure output handling, the recommendation doesn't match the finding.

**References.** Link to the relevant vulnerability taxonomy page in the repo, the OWASP Top 10 for LLM Applications entry, and the MITRE ATLAS technique. This gives the reader a path to learn more about the vulnerability class beyond the specific finding.

### Risk summary and prioritization

After all individual findings, a summary that groups them by theme and priority. Common groupings for AI assessments:

- **Prompt injection findings.** All the injection-related findings grouped together, because the remediation often overlaps (input handling, trust boundary design).
- **Excessive agency findings.** All the over-permissioned tools, missing confirmation steps, and unnecessary capabilities. These are often the easiest to fix and the highest leverage.
- **Insecure output handling findings.** All the places model output flows unsafely into downstream systems. These map to traditional injection remediation and engineering teams already know how to fix them.
- **Architecture and design findings.** Trust boundary issues, confused deputy patterns, missing monitoring. These take longer to fix but prevent entire categories of future findings.

For each group, provide a prioritized remediation roadmap: what to fix first (quick wins that reduce the most risk), what to fix next (structural changes that take more effort), and what to address long-term (design-level improvements).

### Appendices

Technical details that support the findings but would clutter the main report.

- Full system prompt (if extracted). Present it in the appendix and reference it from the relevant findings.
- Complete tool inventory with permissions and boundary analysis.
- Full prompt-and-response transcripts for complex multi-step attack chains.
- Methodology details beyond what's in the scope section.
- Tool and environment configuration used during testing.

## Severity calibration for AI findings

Severity calibration for AI systems follows the same principle as traditional assessments: severity reflects business impact, not technical sophistication. But the mapping has some AI-specific considerations worth codifying.

**Critical.** Findings where an attacker can reliably achieve high-impact outcomes through the AI system. Data exfiltration through prompt injection chained to a tool with external reach. Unauthorized financial transactions through agent manipulation. Arbitrary code execution through insecure handling of model-generated code. The key word is reliably: a chain that works once in fifty attempts is not the same severity as one that works consistently.

**High.** Findings with significant impact but with meaningful limitations on exploitability or scope. Prompt injection that accesses sensitive data but can't exfiltrate it (read access but no send path). Excessive agency that grants unnecessary permissions but requires chaining with injection to exploit. Jailbreaks that bypass safety controls on an agent with consequential tool access but require multi-turn setup.

**Medium.** Findings with moderate impact or significant exploitation difficulty. System prompt extraction revealing internal configuration but no credentials or sensitive data. Prompt injection that changes model behavior but doesn't chain to tool misuse. Jailbreaks against content policies on systems without tool access. Insecure output handling in contexts with limited downstream impact.

**Low.** Findings that represent genuine weaknesses but with limited practical impact. Inconsistent persona behavior under adversarial pressure. Information disclosure through model behavior (confirming which model is being used, revealing configuration details) without sensitive content. Soft guardrail bypasses that produce mildly out-of-policy content.

**Informational.** Observations that improve the system's security posture but don't represent exploitable vulnerabilities. Recommendations for additional logging, suggestions for system prompt improvements, notes on emerging attack classes the system should be monitored for.

Two calibration traps to avoid.

**Don't over-rate prompt injection without chaining.** "I can inject the model" is not automatically high or critical. The severity depends on what the injection achieves. Injection into a chatbot with no tools and no sensitive context is medium at most. Injection into an agent with database access and email capability is critical. Same technique, different impact, different severity.

**Don't under-rate excessive agency.** "The model has more tools than it needs" doesn't sound dramatic, but it's the finding that determines the ceiling on every other finding's severity. An excessive agency finding that grants unnecessary email access turns every future prompt injection from "the model said something wrong" into "the model sent the attacker your data." Rate it based on the potential impact it enables, not on its standalone drama.

## AI-specific reporting considerations

**Reproduction variance.** LLM behavior is non-deterministic. A finding that reproduces eight times out of ten is a real finding. Document the reproduction rate, not just the successful attempt. Include multiple transcript examples if the behavior varies. Explain to the client that exact reproduction depends on the model's temperature setting and that the reproduction rate is the meaningful metric.

**Model versioning.** Models get updated. A finding confirmed against GPT-4o-2024-05-13 may or may not reproduce against a later version. Note the model version in every finding. Recommend the client re-test after model updates. This is a genuinely new reporting consideration that doesn't exist in traditional pentesting.

**System prompt as both finding and context.** A leaked system prompt is often both a finding on its own (LLM08 Hidden Context Exposure, or LLM02 Sensitive Information Disclosure if it contains sensitive data) and evidence supporting other findings (the prompt reveals tool configurations that explain why excessive agency exists). Reference the prompt in both places. Don't make the reader hunt for it.

**Chain findings vs component findings.** Some findings are individual weaknesses. Some are chains of individually acceptable components that become dangerous in combination. Report both, but make the chain findings prominent because they demonstrate the real-world attack path and they're the findings the client will act on fastest.

**Remediation across team boundaries.** AI system findings often span multiple teams: the model configuration team, the application engineering team, the infrastructure team, the data team. Each finding's remediation section should name which team owns the fix. A finding where three teams each assume someone else will fix it is a finding that never gets fixed.

## Report quality checks

Before delivering the report, run these checks:

- Every finding can be understood in isolation without reading other findings.
- Every reproduction step is specific enough for someone else to follow independently.
- Every severity rating is justified by the impact description, not by the technical complexity.
- Every remediation recommendation is specific enough to implement without follow-up questions.
- The executive summary can be read in under five minutes and gives a complete picture of what was found and what to do about it.
- Model version, testing dates, and scope boundaries are documented explicitly.
- Reproduction rates are included for any finding that doesn't reproduce with 100% reliability.
- Evidence is annotated so a reader knows what they're looking at without additional explanation.
- The report doesn't contain client data, internal hostnames, or other sensitive information beyond what's necessary to document findings (this seems obvious, but check).

## Framework references

- OWASP Top 10 for LLM Applications: the finding categories map directly to the Top 10 entries, which provides a shared vocabulary between the assessor and the client.
- MITRE ATLAS: technique IDs from ATLAS can be referenced in findings for precision, similar to how traditional pentest reports reference CVE IDs or ATT&CK technique IDs.
- NIST AI Risk Management Framework: the MANAGE function's emphasis on risk communication and documentation aligns with the reporting approach described here.
- PTES (Penetration Testing Execution Standard): the traditional report structure this format is based on. Clients familiar with PTES-style reports will recognize the format, which reduces friction.
