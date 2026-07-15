---
tags: [playbook, domain/safety-interp, level/advanced]
aliases: [AI red teaming, LLM red teaming]
summary: "End-to-end procedure for adversarially probing a model or LLM app before release: scope, attack library, automation, graded ASR, triage."
---
# Playbook - Red-Teaming a Language Model

> **Goal:** find and measure the ways a model or LLM application produces harmful, policy-violating, or unintended output before an adversary finds them in production. **When to run this:** pre-release for a new model, and pre-deployment any time an existing model gains a new capability, a new tool, or a new deployment surface — a red-team suite scoped to chat does not cover an agent with [[Concept - Tool Use and Function Calling|tool access]]. **Prerequisites:** a written [[Concept - LLM Threat Modeling|threat model]] naming the harms in scope and a harm taxonomy to score against; running attacks without either produces a number with no denominator.

## Steps

1. **Scope harms and threat model.**
   Action: enumerate the specific harms in scope (e.g., bioweapons uplift, CSAM, fraud instructions, self-harm encouragement, data exfiltration for an agentic deployment) against the threat model, and set a release-blocking attack-success-rate (ASR) threshold per harm category.
   Expected observation: a written document a non-author can read and know exactly what "in scope" means, with numeric thresholds, not adjectives like "low risk."
   What deviation means: if reviewers disagree on whether a borderline output counts as a failure, the taxonomy is under-specified — fix the taxonomy before running a single attack, because every downstream ASR number inherits this ambiguity.

2. **Assemble an attack library.**
   Action: pull standardized prompt sets — AdvBench (Zou et al. 2023), HarmBench (Mazeika et al. 2024), JailbreakBench — and extend them with prompts specific to your threat model that the public sets don't cover (your product's tools, your industry's fraud patterns).
   Expected observation: a versioned, deduplicated prompt set with per-item harm-category labels, large enough to give stable ASR estimates per category (hundreds, not tens, per category).
   What deviation means: an attack library copied wholesale from one public benchmark without extension will miss every harm specific to your deployment — the public sets test general chat harms, not your agent's tool-misuse surface.

3. **Run manual probing by domain experts.**
   Action: have subject-matter experts (biosecurity, cybersecurity, clinical, legal, as relevant to your harms) spend dedicated hours attacking the model with open-ended creativity, not scripted prompts.
   Expected observation: manual probing surfaces failure modes the automated library did not — novel framings, domain jargon that slips past a classifier, multi-step social-engineering sequences.
   What deviation means: if manual probing finds nothing the automated suite didn't already find, either the automated suite is unusually thorough or (more often) the manual session was too short or too scripted to count as genuine adversarial creativity.

4. **Run automated attacks.**
   Action: launch optimization- and search-based attacks — [[Concept - Adversarial Suffixes|GCG]] for white-box targets, PAIR and TAP for black-box iterative refinement — using an attacker LLM to generate and refine jailbreaks against the target (Perez et al. 2022, "Red Teaming Language Models with Language Models"), rather than relying on humans to hand-write every variant.
   Expected observation: automated ASR on known-hard prompt families (encoding attacks, roleplay/persona attacks) roughly matches or exceeds published baselines for a comparably-sized model; if it's far below baseline, the harness is misconfigured, not the model unusually robust.
   What deviation means: near-zero ASR across every family on the first run is a stronger signal of a broken harness (wrong system prompt, refusal miscounted as compliance) than of genuine robustness — verify against one known-successful attack before trusting a clean sweep.

5. **Run multi-turn and agentic red-teaming.**
   Action: extend attacks across turns — Crescendo-style gradual escalation, many-shot context flooding — and, for any agentic deployment, attack the [[Deep Dive - The Agent Loop|agent loop]] itself with injected instructions in tool outputs and retrieved content, not just the chat turn.
   Expected observation: multi-turn ASR is measurably higher than single-turn ASR on the same underlying harms — this gap is expected and the size of it tells you how much your single-turn testing was undercounting risk.
   What deviation means: if multi-turn and single-turn ASR are identical, the multi-turn harness likely isn't actually escalating context across turns — inspect the transcript, not just the final score.
   
6. **Score attack-success-rate with graded judges.**
   Action: score every attempt with a graded rubric — StrongREJECT (Souly et al. 2024) or an equivalent LLM-judge rubric — never naive keyword matching ("does not contain 'I cannot'"), which massively overcounts low-quality, non-actionable "successes."
   Expected observation: graded ASR is substantially lower than keyword-match ASR on the same transcripts — this gap is the single biggest source of red-team numbers that don't replicate.
   What deviation means: if graded and keyword-match ASR are close, the judge rubric is probably too lenient or miscalibrated; spot-check a sample of judge-scored "successes" by hand.

7. **Triage and patch.**
   Action: route confirmed failures by root cause — missing safety training data for a harm category, a jailbreak technique that bypasses a specific guardrail layer, an agent-loop design flaw — to the owning team, and re-run the specific attack family after each fix.
   Expected observation: ASR on the patched family drops on re-test without a corresponding rise in refusal rate on the benign/XSTest-style over-refusal set.
   What deviation means: ASR dropping alongside a spike in over-refusal means the "fix" was a blunt classifier tightening, not a real fix — this trades one failure mode for another and should be treated as unresolved.

8. **Freeze a regression suite.**
   Action: lock the finalized attack set (library + confirmed novel findings from steps 3–5) as a versioned regression suite that reruns on every subsequent model or system-prompt change.
   Expected observation: the next release cycle's red-team run starts from this frozen suite plus incremental new attacks, not from scratch.
   What deviation means: re-deriving the attack library from zero each cycle means prior findings can silently regress unnoticed — a fixed jailbreak that returns after an unrelated fine-tune is the single most common preventable red-team miss.

## Verification

Release is gated on two conditions holding simultaneously: graded ASR below the per-category threshold set in Step 1 across **every** attack family (not averaged across families, since averaging hides a category that fully failed), and no regression on the frozen suite from Step 8 relative to the prior release. For frontier-capability releases, require an explicit human red-team sign-off in addition to the numeric gate — the automated ASR number is necessary but Anthropic, OpenAI, and Google DeepMind all report cases where a model passed automated gates but a human found a serious gap the automation's prompt distribution didn't cover.

## When it goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| High ASR concentrated in one attack family | Safety training data didn't cover that technique/framing | Generate targeted adversarial training data for that family (link [[Deep Dive - RLHF End to End]]), re-run Step 4 on just that family |
| Over-refusal spike after a safety patch | Classifier or refusal training tightened too bluntly | Add benign contrastive examples in that category; re-tune threshold rather than binary block |
| New capability or tool shipped, old suite still passes | Suite was scoped to the prior deployment surface, not the new one | Re-scope per Step 1 — do not reuse the old suite as sufficient evidence for a materially different attack surface |
| Graded ASR much lower than keyword-match ASR from an earlier run | Prior measurement used naive keyword matching | Re-score historical runs with the graded judge before comparing trends across releases |
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
