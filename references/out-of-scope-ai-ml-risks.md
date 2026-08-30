# Out of Scope: AI/ML Risks Not Demonstrated in This Portfolio

Model extraction and adversarial inputs are both real, professionally relevant AI security assessment topics. Neither is demonstrated by any lab in this three-project portfolio, and this file exists to say so plainly rather than let the gap go unmentioned.

The honest reason is access, not disinterest. Model extraction testing that means anything requires a model worth stealing and a query budget large enough to show real fidelity between the original and a substitute. A local 3B instruct model on a Kali VM is neither. Adversarial input testing against production classifiers requires either white-box access to a target worth attacking or the query budget to make a black-box attack practical. Building a shallow version of either against a toy target would produce a demo that looks like coverage without being coverage, and that is exactly the kind of claim this portfolio is built to avoid.

What follows is the original taxonomy content for both categories, kept because the material itself is still accurate and useful reference, with the framework citations corrected to the OWASP 2026 numbering. Neither section below should be read as something this repo has tested.

## Model Extraction

### What it is

Model extraction is when an attacker reconstructs a copy of a model by querying it repeatedly and using the responses to train a substitute. The attacker doesn't need access to the weights, the training data, or the infrastructure. They only need API access, or in many cases just a public-facing interface, and enough queries to learn how the model behaves.

The result is a functional copy. Not identical, but close enough to be useful for whatever the attacker needed. Sometimes that's IP theft: a competitor steals a model that cost millions to train. Sometimes it's attack preparation: a local copy lets you develop adversarial inputs, jailbreaks, or prompt injections offline without tripping the target's monitoring. Sometimes it's circumventing access controls: the original model has rate limits, usage logging, and safety filters. The copy has none of those.

### Why it matters

Two angles on the impact, and they're both real.

The first is intellectual property. Training a competitive model from scratch costs serious money. Fine-tuning on domain-specific data costs less but the data itself is often the competitive moat. Model extraction lets an attacker skip both. For companies whose model is their product, this is a business-critical threat. For companies using a vendor's model, it matters less directly but it still matters if the vendor's pricing assumes their model isn't trivially copyable.

The second angle is what extraction enables downstream. A local copy is the ideal testbed for developing other attacks. You can probe it for hours without the target seeing any traffic. You can run gradient-based jailbreak techniques (like GCG adversarial suffixes) that need white-box access. You can study its decision boundaries to craft adversarial inputs. You can map its safety training to find gaps. The extracted model isn't the end goal; it's the staging environment.

There's also a regulatory dimension worth understanding. Models trained on personal data, medical data, or data subject to privacy regulation may memorize that data. Extracting the model means extracting whatever the model memorized. This turns an IP theft problem into a data breach problem, and the regulatory consequences shift accordingly.

### Where it shows up

**Public APIs with rich outputs.** Any API that returns logits, probabilities, confidence scores, or ranked alternatives gives the attacker more signal per query. The richer the output, the fewer queries needed. Classification models with confidence scores are the textbook case.

**LLM APIs.** Large language models are harder to extract fully because of their size, but partial extraction (capturing behavior in a narrow domain) is practical. An attacker who only cares about how the model handles customer support conversations for a specific industry doesn't need to extract the whole model.

**Embedding models.** Models that return embedding vectors are particularly exposed. The embeddings themselves are the model's learned representation, and a large enough collection of input-embedding pairs can train a substitute.

**Models behind rate-limited but otherwise open interfaces.** If the only protection is a rate limit, the attacker just needs patience or multiple accounts. Rate limits slow extraction; they don't prevent it.

**Fine-tuned models served through vendor platforms.** A company fine-tunes GPT or Claude on proprietary data and serves it through an app. The fine-tuning creates a behavioral fingerprint that can be extracted even though the base model is public. The proprietary value is in the fine-tuning, and the fine-tuning is extractable.

### The techniques

**Query-based distillation.** The foundational technique. Send inputs, collect outputs, train a student model to mimic them. For classification models this is straightforward: label a dataset using the target model, train a substitute on those labels. For language models it's harder but the same principle applies: generate a corpus of prompt-completion pairs from the target and fine-tune a base model on them.

**Active learning strategies.** Instead of random queries, choose inputs that maximize information gain. Query near decision boundaries. Query where the substitute and the target disagree. This reduces the number of queries needed by an order of magnitude in practice. An attacker using active learning can extract a useful copy of a classification model in a few thousand queries.

**Logit and probability harvesting.** When the API returns probability distributions rather than just top-1 outputs, each query is worth much more. The full distribution over classes (or over tokens, for a language model) encodes the model's uncertainty and its learned relationships. Distillation from logits converges faster and produces better copies than distillation from hard labels.

**Side-channel extraction.** Response timing, token-by-token streaming latency, and API error messages can leak information about model architecture and behavior. A model that takes longer on certain inputs reveals something about its computational path. These signals are weak individually but useful as supplements.

**Embedding theft.** For embedding models specifically: collect a large set of input-embedding pairs, then train a model to reproduce the mapping. The resulting model doesn't need the same architecture. It just needs to produce similar embeddings for similar inputs. This is practical and well-documented.

**Partial extraction for attack development.** The pragmatic version. Don't try to copy the whole model. Query it specifically in the domain where you plan to attack, build a local copy that's accurate in that narrow region, and use it as your testing ground. This is how extraction actually gets used in attack chains: not perfect copies, but good-enough approximations in the zones that matter.

### Testing methodology

Model extraction testing looks different depending on whether you're testing from the outside (can someone extract our model?) or auditing from the inside (are our controls adequate?).

**External testing: can the model be extracted?**

Start by characterizing the API surface. What does the API return? Hard labels only, or probabilities? Token-level logprobs? Embedding vectors? Ranked alternatives? The richer the output, the more extractable the model. Document this as a finding by itself: an API that returns full probability distributions over all classes is making extraction significantly easier than necessary.

Run a small-scale extraction attempt. Pick a narrow domain the model is good at, query it with a few hundred to a few thousand inputs, collect the outputs, and train a small substitute. Measure how well the substitute matches the target on held-out inputs. You don't need a perfect copy. You need enough fidelity to demonstrate the attack is practical.

Measure query efficiency. How many queries did it take to get a useful copy in the target domain? Could an attacker do this within the API's rate limits over a reasonable time period? If the answer is yes with a few thousand queries, that's a finding.

Test whether existing controls detect the attempt. Did the rate limiter trigger? Did any anomaly detection fire? Did the query pattern look different from normal usage in the logs? Often the answer to all three is no, and that's the more important finding.

**Internal audit: are the controls adequate?**

Review what the API returns. The single most impactful remediation for extraction is reducing output richness: return hard labels instead of probabilities, return top-1 instead of top-k, don't return logprobs unless the use case genuinely requires them.

Review rate limiting and authentication. Per-user rate limits, query budgets, and authentication requirements all raise the cost of extraction. None of them prevent it, but they determine whether extraction takes an afternoon or a year.

Review monitoring and anomaly detection. Does the system flag unusual query patterns? High-volume querying, systematic input variation, queries that look like active learning rather than normal usage? Most systems don't, and building this detection is the realistic recommendation.

Review whether the model's training data contains content that would make extraction a data breach rather than just an IP issue. If the model memorizes personal data, extraction is a privacy incident, not just a competitive one.

**Evidence capture.** For extraction attempts, the evidence is the substitute model itself plus the fidelity measurements. For API surface findings, the evidence is the API response format showing what's returned. For control-gap findings, the evidence is the query volume and pattern you ran without being detected or throttled.

### Why remediation is hard

You can't prevent model extraction if you give people access to the model. Every query leaks information. The only question is how much information per query and how many queries it takes to matter.

Practical defense is about raising the cost, not building a wall:

- Reduce output richness. Return the minimum information the application needs. If you don't need probabilities, don't return them. If you don't need logprobs, don't expose them. This is the single highest-impact change and it's almost always available.
- Rate limiting and query budgets. Per-user limits set the pace of extraction. They don't prevent it, but they make large-scale extraction visible and slow.
- Query pattern monitoring. Normal users don't send systematic grid queries or active-learning-shaped input distributions. Detecting these patterns is practical and underdeployed.
- Watermarking. Embed statistical patterns in model outputs that survive distillation and let you prove a copy was derived from your model. Useful for the IP theft case. Not useful for the attack-preparation case, where the attacker doesn't care about provenance.
- Differential privacy in training. Reduces memorization, which reduces the data-breach dimension of extraction. Doesn't prevent functional extraction.
- Legal controls. Terms of service prohibiting extraction, combined with technical measures that make violation detectable. The legal layer matters for commercial competitors. It doesn't matter for adversaries.

### Framework references

- **OWASP Top 10 for LLM Applications:** the 2023 edition of this list carried a dedicated Model Theft entry at LLM10. That entry does not exist in the 2026 list (confirmed against genai.owasp.org on 2026-08-30; the 2026 LLM10 is Improper Output Handling). The closest current analogs are LLM06 Unbounded Consumption, since practical extraction depends on sustained high-volume querying, and LLM03 Excessive Agency, when extraction is enabled by over-permissioned API access. This is an inference, not an OWASP-stated mapping, and it is labelled as one wherever it appears.
- MITRE ATLAS: ML Model Inference API Access, Exfiltration via ML Inference API, and Replicate Model are the core techniques. Names not re-verified this pass; check against atlas.mitre.org if this page moves from archive to cited.
- NIST AI Risk Management Framework: GOVERN and PROTECT functions applied to model access controls and intellectual property protection. AI RMF 1.0 (January 2023); see [`framework-versions.md`](framework-versions.md).

## Adversarial Inputs

### What it is

Adversarial inputs are inputs crafted to make a model produce the wrong output while looking normal to a human. The classic demonstration is an image of a panda with a tiny, invisible perturbation added, and the model now classifies it as a gibbon with high confidence. A human sees a panda. The model sees something else entirely. The perturbation is mathematically optimized to exploit how the model processes the image, not how a person would.

This is the oldest class of attack in ML security, predating the LLM era by a decade. It was discovered against image classifiers and has since been demonstrated against every model type: text classifiers, speech recognition, malware detectors, autonomous driving perception systems, fraud detection models, and now language models. The underlying cause is the same across all of them: the features the model learned to rely on don't perfectly match the features a human would rely on, and the gap between the two is exploitable.

### Why it matters

The severity depends entirely on what the model is deciding. An adversarial input against a content recommendation model is an annoyance. An adversarial input against a malware classifier means malware gets past the scanner. An adversarial input against an autonomous vehicle's perception system means the car misreads a stop sign. The technique is the same; the stakes scale with the deployment.

For the AI security space specifically, adversarial inputs matter for three reasons.

First, they're a real attack against production systems right now. Malware authors routinely modify executables to evade ML-based detection. Spam campaigns modify text to evade ML-based filters. These aren't theoretical, they're the most commercially deployed form of adversarial ML attack, and they've been happening for years.

Second, they're relevant to LLM deployments in ways that are still being mapped out. Safety classifiers that decide whether to block a model's output are themselves ML models, and they're vulnerable to adversarial inputs. Content moderation systems, toxicity detectors, and prompt-injection classifiers all have adversarial-input attack surfaces. Attacking the guardrail model rather than the main model is an increasingly practical bypass strategy.

Third, adversarial robustness is a regulatory topic. The EU AI Act and NIST AI RMF both reference robustness to adversarial inputs as a requirement for high-risk AI systems. Clients in regulated industries will be asked about this, and they'll need assessments that address it.

### Where it shows up

**ML-based security tools.** Malware classifiers, phishing detectors, intrusion detection systems, spam filters. These are the highest-volume real-world targets for adversarial inputs. The adversary has clear motivation (bypass the detector) and often has enough access to the model's behavior to craft effective perturbations. If you're doing AI security testing for an enterprise, their ML-based security stack is the first place to look for adversarial-input risk.

**Content moderation and safety classifiers.** Toxicity classifiers, NSFW detectors, prompt-injection detectors, and output safety filters. These sit in the pipeline around LLMs and make binary or categorical decisions. Each one is a model with an adversarial-input surface, and bypassing any of them bypasses whatever policy it was enforcing.

**Computer vision in physical systems.** Autonomous vehicles, facial recognition, surveillance, medical imaging, manufacturing quality inspection. Adversarial inputs in vision models can sometimes be deployed physically: a sticker on a stop sign, a pattern on a pair of glasses, a subtle modification to a medical scan. The physical deployment case gets attention because the consequences are tangible.

**Fraud detection and risk scoring.** Financial transaction classifiers, insurance claim models, credit scoring. Adversaries who understand the model's features can modify transactions to stay under the threshold. This has been happening since before the term "adversarial inputs" existed; the ML security framing just gave it a name.

**Natural language classifiers.** Sentiment analysis, intent classification, document categorization. Text perturbations (synonym substitution, character-level swaps, whitespace manipulation, homoglyph substitution) can flip classification results while preserving readability for humans.

### The techniques

**Gradient-based perturbations (white-box).** When you have access to the model's weights, you can compute exactly which direction to perturb the input to change the output. FGSM, PGD, and C&W are the foundational methods. They produce minimal perturbations that are often imperceptible to humans. This is the research-standard approach and the one used for robustness benchmarking. In practice you rarely have white-box access to a production target, but you often have it for an extracted copy or a similar open model, and perturbations transfer surprisingly well.

**Transferability attacks (gray-box).** Adversarial inputs crafted against one model often fool a different model trained on similar data for the same task. This is the bridge between white-box research and real-world exploitation. The attacker trains or obtains a surrogate model, crafts adversarial inputs against it, and deploys them against the target. Transfer rates vary but are consistently high enough to be practical, especially across models of similar architecture.

**Query-based attacks (black-box).** When you only have API access, you can estimate gradients by observing how the output changes as you perturb the input. Slower than white-box, and requires many queries, but it works against any model you can query. Pairs naturally with model extraction: extract first, then craft adversarial inputs against the local copy.

**Text-specific perturbations.** For NLP models, the perturbation space isn't continuous like pixels. Instead, attackers substitute synonyms, insert zero-width characters, swap homoglyphs (Cyrillic "a" for Latin "a"), add invisible unicode, rephrase sentences to preserve meaning while changing classification, or inject adversarial tokens that disrupt the tokenizer. TextFooler, BERT-Attack, and similar frameworks automate this. These are directly relevant to attacking LLM safety classifiers.

**Physical-world adversarial examples.** Perturbations that survive the transition from digital to physical. Adversarial patches (printed patterns placed in the real world), adversarial textures on 3D objects, adversarial makeup or glasses for facial recognition. These have to survive variable lighting, angle, distance, and camera noise, which makes them harder to construct but also harder to detect.

**Adversarial reprogramming.** Instead of fooling a model, repurpose it. Craft inputs that make a model trained for task A perform task B. Demonstrated in research, rare in practice, but worth knowing about because it challenges the assumption that a model's capability is bounded by its training task.

### Testing methodology

**Understand the model's role and what a wrong output means.** Before crafting a single perturbation, ask: what decision does this model make, and what happens when that decision is wrong? A misclassified support ticket is a different severity than a missed malware detection. The testing approach and the report should be calibrated to the consequence, not to the technical elegance of the bypass.

**Determine your access level.** White-box (full access to weights and architecture), gray-box (access to a similar model or the ability to extract one), or black-box (API access only). The access level determines which techniques are practical. Most real engagements land at gray-box or black-box unless the client gives you model access as part of the scope.

**For ML-based security tools specifically.** This is often the most practical testing target on an engagement. Take known-bad samples (malware, phishing emails, toxic content, whatever the tool is supposed to catch) and apply perturbations to see which ones get past the classifier. Start with simple modifications (file padding, string obfuscation for malware; synonym substitution for text classifiers) before moving to gradient-based or query-based methods. Simple bypasses are actually the more impactful finding because they're the ones real adversaries are already using.

**For safety and content classifiers.** Identify the classifier in the pipeline (content moderation, toxicity detection, prompt-injection detection), determine what it blocks, and attempt to pass blocked content through with perturbations. Character-level tricks (homoglyphs, zero-width characters, encoding changes) are the first thing to try. This overlaps with jailbreaking, but the target is different: here you're attacking the classifier model, not the language model behind it.

**For production vision models.** If the scope includes computer vision, test with standard adversarial example libraries (ART, Foolbox, CleverHans) against the target or a surrogate. If physical-world testing is in scope (rare but it happens), test adversarial patches under realistic conditions: multiple angles, distances, and lighting.

**Robustness benchmarking.** For clients who want a quantitative answer to "how robust is our model," run a benchmark: clean accuracy versus accuracy under attack across a standard perturbation budget. AutoAttack is the current standard for image models. For text models, run the perturbation frameworks (TextFooler, etc.) and measure the success rate and semantic preservation.

**Evidence capture.** Original input and classification, perturbed input and classification, the perturbation itself (make it visible, highlight the difference), and a clear statement of the success rate. For physical-world tests, photographs or video of the adversarial object in situ. For security-tool bypasses, show the original detection, the perturbation, and the successful evasion side by side.

### Why remediation is hard

Adversarial robustness is a fundamental limitation of current ML, not a bug in a particular model. Every model has adversarial inputs. Adversarial training (retraining with adversarial examples in the dataset) helps but doesn't solve the problem, and it usually costs accuracy on clean inputs. Certified defenses (provable robustness within a perturbation budget) exist for small models and small perturbations but don't scale to production systems yet.

Practical defense is about layers, not about making a single model bulletproof:

- Adversarial training as a baseline. Train or fine-tune with adversarial examples in the dataset. This raises the bar for the attacker without eliminating the vulnerability. It's the most widely deployed defense and it works well enough against unsophisticated perturbations.
- Input preprocessing and detection. Techniques like input smoothing, feature squeezing, or statistical detection of adversarial properties in the input. These catch some attacks and miss others. Useful as a layer, not as the primary defense.
- Ensemble models. Use multiple models with different architectures or training data. An adversarial input that fools one model is less likely to fool all of them. Works well in practice for security-critical decisions.
- Reduce output richness. Same principle as model extraction defense. Return less information per query, which makes black-box and query-based attacks harder. Confidence scores help attackers; don't return them unless you need to.
- Monitor for perturbation signatures. Adversarial inputs often have statistical properties that differ from natural inputs. Monitoring for these properties in production can catch attacks that bypass the model itself.
- Accept the limitation in the risk assessment. Some models will be adversarially vulnerable and the remediation cost exceeds the risk. The honest recommendation in those cases is "document the risk, monitor for exploitation, and don't put this model on a critical decision path without a human in the loop." Clients appreciate hearing that more than they appreciate a promise of a fix that doesn't exist.

### Framework references

- OWASP Top 10 for LLM Applications: LLM10 Improper Output Handling is adjacent. Adversarial inputs against LLM-adjacent classifiers (safety filters, content moderation) are the primary LLM-relevant case.
- MITRE ATLAS: Evade ML Model, Craft Adversarial Data, and the physical-domain techniques are the core entries. ATLAS has the most detailed technique coverage for adversarial inputs of any framework.
- NIST AI Risk Management Framework: MEASURE function applied to adversarial robustness evaluation. The AI RMF explicitly references adversarial testing as part of trustworthy AI assessment.
