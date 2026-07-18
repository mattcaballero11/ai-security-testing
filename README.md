# AI Security Testing

Methodology, vulnerability taxonomy, and lab demonstrations for testing AI and LLM systems.

## Why this exists

I do AI security testing professionally as part of my consulting work. Those engagements are covered by NDAs, so this repo contains no client data, findings, or engagement details. What it does contain is the methodology and approach I use, rebuilt against public frameworks and intentionally vulnerable targets so the work is visible and verifiable.

This is the same reason I built my other portfolio repos. The capability is real, the client work is not shareable, so the methodology and lab work are the proof.

## What's in this repo

**Methodology.** How I scope, threat-model, test, and report on AI systems end to end.

**Vulnerability taxonomy.** The main classes of AI and LLM vulnerabilities, organized by attack surface: prompt injection (direct and indirect), jailbreaking, training data poisoning, model extraction, adversarial inputs, agent and tool-use attacks, insecure output handling, and excessive agency.

**Lab demonstrations.** Hands-on write-ups showing exploitation against intentionally vulnerable AI targets. Each write-up follows a standard structure: overview, scope and authorization, methodology, exploitation, impact, remediation, lessons learned.

**References.** How the methodology maps to public frameworks including OWASP Top 10 for LLM Applications, MITRE ATLAS, and NIST AI Risk Management Framework.

## Scope and disclaimer

This repository documents AI security testing methodology using public frameworks, intentionally vulnerable targets, and educational demonstrations only. It contains no client data, proprietary findings, or confidential engagement details.

All lab demonstrations were conducted in controlled environments against systems designed to be tested: public CTFs, intentionally vulnerable applications, or local setups I built for testing. Nothing in this repo should be interpreted as testing performed against systems I did not have authorization to test.

## Status

This repo is being built in stages. Sections marked live are ready to read. Sections marked in progress are scaffolded but not filled in yet.

- [ ] Methodology (in progress)
- [ ] Vulnerability taxonomy (in progress, prompt injection live)
- [ ] Lab demonstrations (in progress)
- [ ] Framework mappings (in progress)

## Frameworks referenced

- OWASP Top 10 for LLM Applications
- MITRE ATLAS
- NIST AI Risk Management Framework
- Emerging guidance on agent and tool-use security, including MCP and function-calling attack surfaces

## About

Built by [Matthew Caballero](https://github.com/mattcaballero11), Cybersecurity Consultant. Related repos:

- [detection-as-code-lab](https://github.com/mattcaballero11/detection-as-code-lab)
- [home-soc-lab](https://github.com/mattcaballero11/home-soc-lab)

Network and web application pentest methodology repos are on the way.

## License

MIT. See [LICENSE](LICENSE).
