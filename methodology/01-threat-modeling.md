# Threat Modeling for AI Systems

## What this page covers

This is the first phase of any AI security assessment. Before you send a single payload, before you open Burp or spin up a testing environment, you need to understand what you're looking at: what the system does, how it's built, who would attack it, and what damage looks like. Threat modeling for AI systems follows the same principles as threat modeling for anything else. The difference is in what you're mapping and what questions you ask.

Skipping this step is the fastest way to produce a report full of technically valid findings that don't matter. A prompt injection against a model with no tools and no sensitive context is a low-severity curiosity. A prompt injection against an agent with email access and database credentials is a critical finding. You can't tell the difference without understanding the system first.

## The questions that structure the assessment

Every AI security threat model answers five questions. The order matters because each answer constrains the next.

**1. What does this system do, and for whom?**

Not what the model does. What the system does. A model is a component. The system is the model plus its tools, its data sources, its users, its interfaces, and its downstream integrations. A "customer support chatbot" is a different assessment target than "a customer support chatbot connected to the order database with refund capability and email integration." Same model, radically different threat surface.

Map the system's purpose, its users (who talks to it and who relies on its outputs), its business context (what decisions does it inform or make), and its operational environment (internal-only, customer-facing, internet-exposed, embedded in another product). This context determines what matters in the assessment. An internal documentation assistant and a public-facing financial advisor use the same underlying technology but have completely different threat profiles.

**2. What is the architecture?**

This is the technical inventory, and getting it right determines whether the rest of the assessment is useful or superficial.

Components to identify:

- **The model itself.** What model, what version, what provider, hosted or self-hosted, fine-tuned or base. For vendor-hosted models, what API features are enabled (function calling, system prompts, logprobs, streaming, vision, code execution). For self-hosted models, what inference infrastructure is running and who manages it.
- **The system prompt and configuration.** What instructions does the model receive? What persona, constraints, and behavioral rules are set? How are they delivered (hardcoded, configurable, pulled from a database at runtime)?
- **Tools and integrations.** Every tool, function, API, plugin, MCP server, or external system the model can invoke. For each: what it does, what permissions it has, what data it can access, whether it can modify state. This is the tool inventory from the excessive agency page, performed here as part of scoping rather than as a finding.
- **Data sources.** Everything the model reads that it wasn't trained on: RAG document stores, databases, web content, email, uploaded files, tool outputs, conversation history, long-term memory. Each one is a potential indirect prompt injection surface.
- **Output destinations.** Where does the model's output go? Rendered in a browser, executed as code, sent as a message, written to a database, passed to another model, used as input to a downstream system. Each destination is a potential insecure output handling surface.
- **Authentication and authorization.** How do users authenticate to the system? How does the system authenticate to downstream tools and APIs? Does the model operate with its own credentials or with the user's? Are there different privilege levels for different users?
- **Monitoring and logging.** What gets logged? Prompts, responses, tool calls, errors? Who reviews the logs? Are there alerts?

The deliverable from this step is an architecture diagram showing every component, every data flow, and every trust boundary. It doesn't have to be pretty. It has to be complete.

**3. Who would attack this system, and why?**

Threat actors for AI systems mostly map to the same categories as traditional systems, with some AI-specific additions.

- **External attackers** targeting the system through its public interfaces. Prompt injection, jailbreaking, adversarial inputs. Their goal is data theft, unauthorized actions, or system abuse.
- **Malicious users** who have legitimate access but want to exceed their authorization. Jailbreaking to get content the system is supposed to refuse, prompt injection to access other users' data, model extraction to steal the vendor's IP.
- **Supply chain attackers** who compromise a component the system depends on. A poisoned training dataset, a compromised MCP tool server, a malicious plugin, a tampered fine-tuning dataset. Their access is indirect but their impact can be deep.
- **Insiders** with access to the model's configuration, training pipeline, or tool integrations. They can modify system prompts, alter training data, change tool permissions, or plant backdoors. Standard insider threat, new attack surface.
- **Competitors** interested in model extraction, training data extraction, or understanding the system's capabilities for competitive advantage.

For each relevant threat actor, document their likely goals, their access level, their sophistication, and the attack classes from the vulnerability taxonomy that are available to them. Not every threat actor is relevant to every system. A purely internal system doesn't face external attackers. A system with no training pipeline doesn't face poisoning threats. Scoping the threat actors prevents wasted testing effort.

**4. What are the attack surfaces?**

This is where the architecture map meets the threat actor analysis. For each component and data flow identified in step 2, ask: can any of the threat actors identified in step 3 influence this? If yes, what vulnerability classes from the taxonomy apply?

The standard AI-specific attack surfaces:

- **User input interface.** Direct prompt injection, jailbreaking. Present on every system with a user-facing input.
- **Retrieved content (RAG, web, email, documents).** Indirect prompt injection. Present on every system that reads external content.
- **Tool inputs and outputs.** Agent and tool-use attacks. Present on every system with tool integrations.
- **Model output rendering.** Insecure output handling. Present on every system that renders model output in a context where it can have effect.
- **Training and fine-tuning pipeline.** Data poisoning. Present on every system where training data can be influenced.
- **API surface.** Model extraction, adversarial inputs. Present on every system with an accessible API.
- **Tool and plugin supply chain.** Tool poisoning. Present on every system that loads tools from external sources.

Map each attack surface to the vulnerability taxonomy pages. This mapping becomes the testing plan.

**5. What does damage look like?**

Define the impact scenarios before you start testing, because severity ratings without business context are meaningless. A leaked system prompt is a different severity for a general-purpose chatbot than for a system whose prompt contains customer PII or proprietary business logic.

Impact categories to consider:

- **Data breach.** Can the system be made to disclose data it has access to? Customer data, internal documents, credentials, PII, financial records.
- **Unauthorized actions.** Can the system be made to take actions on behalf of the attacker? Send messages, modify records, execute code, spend money, make decisions.
- **Reputation.** Can the system be made to produce content that damages the organization's reputation? Offensive content, misinformation, competitor endorsement.
- **Availability.** Can the system be made to fail, loop, or degrade? Denial of service through adversarial inputs or prompt-based loops.
- **Compliance.** Does a compromise trigger regulatory obligations? Data protection notifications, financial reporting requirements, safety incident reports.
- **Downstream cascade.** If this system's output feeds into another system, what happens when that output is compromised?

Each impact scenario gets a severity estimate based on the organization's own risk tolerance. These severity estimates calibrate the testing effort: spend more time on the attack surfaces that lead to the highest-impact scenarios.

## The deliverable

The output of threat modeling is a scoping document that the rest of the assessment is built on. It contains:

1. System description and architecture diagram showing all components, data flows, and trust boundaries.
2. Threat actor analysis identifying which actors are relevant and what their goals and access levels are.
3. Attack surface inventory mapping each surface to the vulnerability taxonomy, with the threat actors who can reach each surface.
4. Impact scenarios ranked by business severity.
5. Testing plan derived from the above: which attack surfaces to test, in what order, using which techniques, calibrated to the impact scenarios that matter most.

This document is what separates a structured assessment from ad-hoc poking. It's also the document the client sees first, and it's where they either gain or lose confidence in your approach.

## What's different about AI threat modeling

Most of what's on this page applies to any system. The AI-specific elements are worth calling out because they're the ones that get missed when a traditional security team does their first AI assessment.

**Trust boundaries are blurrier.** In a traditional web app, the trust boundary between user input and application logic is well-understood. In an AI system, the model sits inside the trust boundary but processes content from outside it, and it can't reliably distinguish the two. This is why prompt injection exists as a class. The threat model has to account for the fact that the trust boundary is permeable by design, not just by misconfiguration.

**The model is both a component and an attacker.** Once compromised via prompt injection, the model becomes the attacker operating inside the system's trust boundary with the system's own credentials. Traditional threat models assume components either work correctly or fail. AI threat models have to account for a component that continues to function but pursues a different goal.

**Capability scales with integration.** A model in isolation has limited impact. Every tool, data source, and downstream system connected to it multiplies the impact of compromise. Traditional systems also have integration risk, but AI systems accumulate it faster because the whole value proposition is broad integration.

**The attack surface includes content, not just interfaces.** Any content the model processes is a potential attack vector. A web page, a PDF, an email body, a database record, a tool's error message. Traditional threat models focus on interfaces (APIs, forms, protocols). AI threat models have to include content as an attack surface, which dramatically expands what you're mapping.

## Framework references

- OWASP Top 10 for LLM Applications: the threat modeling approach here maps findings to the OWASP categories. The OWASP AI Security and Privacy Guide provides additional threat modeling guidance.
- MITRE ATLAS: the ATT&CK-style matrix provides a structured enumeration of adversary techniques that feeds directly into the threat actor and attack surface analysis.
- NIST AI Risk Management Framework: the MAP function is essentially threat modeling. The framework's emphasis on context, stakeholders, and risk tolerance aligns with the impact scenario analysis described here.
- Microsoft STRIDE: still useful for AI systems as a prompt for thinking about threat categories (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege). Each one maps to AI-specific attack patterns.
