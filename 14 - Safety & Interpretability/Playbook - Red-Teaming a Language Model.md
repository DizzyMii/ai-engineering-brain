---
tags: [playbook, domain/safety-interp, level/advanced]
aliases: [AI red teaming, LLM red teaming]
summary: "End-to-end procedure for adversarially probing a model or LLM app before release: scope, attack library, automation, graded ASR, triage."
---
# Playbook - Red-Teaming a Language Model

> **Goal:** find and measure the ways a model or LLM application produces harmful, policy-violating or unintended output before an adversary finds them in production. **When to run this:** pre-release for a new model, and pre-deployment whenever an existing model gains a capability, a tool or a deployment surface. A red-team suite scoped to chat doesn't cover an agent with [[Concept - Tool Use and Function Calling|tool access]]. **Prerequisites:** a written [[Concept - LLM Threat Modeling|threat model]] naming the harms in scope, and a harm taxonomy to score against. Without them, attacks produce a number with no denominator.

## Steps

1. **Scope harms and threat model.**
   List the specific harms in scope against the threat model (bioweapons uplift, CSAM, fraud instructions, self-harm encouragement, data exfiltration for an agentic deployment, for example) and set a release-blocking attack-success-rate (ASR) threshold per harm category.
   You should end up with a document a non-author can read and know exactly what "in scope" means, with numeric thresholds instead of adjectives like "low risk."
   If reviewers disagree on whether a borderline output counts as a failure, the taxonomy is under-specified. Fix it before running a single attack, because every ASR number downstream inherits the ambiguity.

2. **Assemble an attack library.**
   Pull standardized prompt sets (AdvBench (Zou et al. 2023), HarmBench (Mazeika et al. 2024), JailbreakBench) and extend them with prompts for your threat model that the public sets don't cover: your product's tools, your industry's fraud patterns.
   The result should be a versioned, deduplicated prompt set with per-item harm-category labels, big enough for stable per-category ASR estimates (hundreds per category, not tens).
   A library copied wholesale from one public benchmark will miss every harm specific to your deployment. Public sets test general chat harms, not your agent's tool-misuse surface.

3. **Run manual probing by domain experts.**
   Have subject-matter experts (biosecurity, cybersecurity, clinical, legal, whichever fit your harms) spend dedicated hours attacking the model with open-ended creativity instead of scripted prompts.
   Manual probing should surface failures the automated library missed: novel framings, domain jargon that slips past a classifier, multi-step social-engineering sequences.
   If it finds nothing the automated suite didn't, either the suite is unusually thorough or, more often, the session was too short or too scripted to count as real adversarial creativity.

4. **Run automated attacks.**
   Launch optimization- and search-based attacks, [[Concept - Adversarial Suffixes|GCG]] for white-box targets and PAIR and TAP for black-box iterative refinement, using an attacker LLM to generate and refine jailbreaks against the target (Perez et al. 2022, "Red Teaming Language Models with Language Models") so humans don't hand-write every variant.
   Automated ASR on known-hard prompt families (encoding attacks, roleplay/persona attacks) should roughly match or beat published baselines for a comparably sized model. Far below baseline means the harness is misconfigured, not that the model is unusually robust.
   Near-zero ASR across every family on the first run points to a broken harness (wrong system prompt, refusal miscounted as compliance) far more than to real robustness. Check against one known-successful attack before trusting a clean sweep.

5. **Run multi-turn and agentic red-teaming.**
   Extend attacks across turns with Crescendo-style gradual escalation and many-shot context flooding. For any agentic deployment, attack the [[Deep Dive - The Agent Loop|agent loop]] itself with injected instructions in tool outputs and retrieved content, as well as the chat turn.
   Multi-turn ASR should come out measurably higher than single-turn ASR on the same harms. That gap is expected, and its size tells you how much single-turn testing was undercounting risk.
   If multi-turn and single-turn ASR are identical, the multi-turn harness probably isn't escalating context across turns. Read the transcript, not only the final score.
   
6. **Score attack-success rate with graded judges.**
   Score every attempt with a graded rubric, StrongREJECT (Souly et al. 2024) or an equivalent LLM-judge rubric. Never use naive keyword matching ("does not contain 'I cannot'"), which massively overcounts low-quality, non-actionable "successes."
   Graded ASR should be well below keyword-match ASR on the same transcripts. That gap is the biggest single source of red-team numbers that don't replicate.
   If graded and keyword-match ASR are close, the judge rubric is probably too lenient or miscalibrated. Hand-check a sample of judge-scored "successes."

7. **Triage and patch.**
   Route confirmed failures by root cause (missing safety training data for a harm category, a jailbreak technique that gets past a specific guardrail layer, an agent-loop design flaw) to the owning team, and re-run that attack family after each fix.
   ASR on the patched family should drop on re-test without refusal rate rising on the benign/XSTest-style over-refusal set.
   ASR dropping alongside an over-refusal spike means the "fix" was a blunt classifier tightening. It trades one failure mode for another; treat it as unresolved.

8. **Freeze a regression suite.**
   Lock the final attack set (library + confirmed new findings from steps 3–5) as a versioned regression suite that reruns on every later model or system-prompt change.
   The next release cycle's red-team run then starts from this frozen suite plus new attacks, not from scratch.
   Rebuilding the library from zero each cycle lets earlier findings regress unnoticed. A fixed jailbreak that comes back after an unrelated fine-tune is the most common preventable red-team miss.

## Verification

Release is gated on two conditions together. Graded ASR has to be below the per-category threshold from Step 1 for **every** attack family, not averaged across families, since an average hides a category that failed completely. And the frozen suite from Step 8 must show no regression against the prior release. For frontier-capability releases, also require explicit human red-team sign-off. The automated ASR number is necessary, but Anthropic, OpenAI and Google DeepMind all report cases where a model passed automated gates and a human found a serious gap outside the automation's prompt distribution.

## When it goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| High ASR concentrated in one attack family | Safety training data didn't cover that technique/framing | Generate targeted adversarial training data for that family (see [[Deep Dive - RLHF End to End]]), re-run Step 4 on that family |
| Over-refusal spike after a safety patch | Classifier or refusal training tightened too bluntly | Add benign contrastive examples in that category; re-tune the threshold instead of binary blocking |
| New capability or tool shipped, old suite still passes | Suite was scoped to the old deployment surface | Re-scope per Step 1; the old suite isn't sufficient evidence for a materially different attack surface |
| Graded ASR much lower than keyword-match ASR from an earlier run | The earlier measurement used naive keyword matching | Re-score historical runs with the graded judge before comparing trends across releases |
| Automated attacks (GCG/PAIR/TAP) report near-zero ASR everywhere | Harness misconfiguration (wrong endpoint, refusal miscounted as success) | Validate against one known-successful published attack before trusting the sweep |

## Connections
- [[Concept - LLM Threat Modeling]] — the prerequisite scoping document Step 1 depends on; red-teaming without it produces an ASR number with no defined denominator.
- [[Concept - Jailbreak Taxonomy]] — the technique families (competing objectives, mismatched generalization) the attack library in Step 2 must cover.
- [[Reference - Jailbreak and Prompt Injection Attack Catalog]] — the concrete, dated catalog of named attacks to pull into the attack library.
- [[Concept - Adversarial Suffixes]] — the GCG optimization technique used for white-box automated attacks in Step 4.
- [[Concept - Statistical Rigor in Model Evaluation]] — the sampling and variance discipline that makes a graded ASR number trustworthy rather than noise.
- [[Deep Dive - Designing an Eval Harness]] — the general eval-harness engineering this playbook specializes for adversarial testing.
- [[Concept - The Evaluation Gap]] — the broader gap between capability and deployed evaluation infrastructure this playbook is one instance of closing.
- [[Concept - Many-Shot Jailbreaking]] — the specific long-context multi-turn attack Step 5's escalation testing must include for any model with a large context window.

## Sources
- Perez, E. et al. (2022) — "Red Teaming Language Models with Language Models." Establishes automated red-teaming via an attacker LLM, the basis for Step 4's automation.
- Souly, A. et al. (2024) — "A StrongREJECT for Empty Jailbreaks." The graded scoring rubric Step 6 relies on to avoid overcounting low-quality jailbreak "successes."
- Mazeika, M. et al. (2024) — "HarmBench: A Standardized Evaluation Framework for Automated Red Teaming and Robust Refusal." Source of the standardized attack/harm taxonomy used in Step 2.
- Microsoft — PyRIT (Python Risk Identification Toolkit) and NVIDIA — garak. Open-source red-teaming harness tooling implementing this playbook's automation steps.
