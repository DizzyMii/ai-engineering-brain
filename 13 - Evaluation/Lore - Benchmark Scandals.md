---
tags: [lore, domain/evaluation, level/unicorn]
aliases: [Reflection-70B, GSM1k, The Leaderboard Illusion, Open LLM Leaderboard MMLU discrepancy]
summary: "War stories where benchmark numbers turned out to be marketing: fraud, overfit, harness discrepancies, length gaming, and cherry-picking."
---

# Lore - Benchmark Scandals

> Each of these started as a number in a launch chart and ended as a lesson in the difference between a *measurement* and a *marketing artifact*. Most weren't fraud. The unsettling part is how few of them had to be.

## What happened

### Reflection-70B: the model that couldn't reproduce itself (Sept 2024)

On 5 September 2024, Matt Shumer (CEO of HyperWrite / OthersideAI) announced **Reflection-70B**, a [[Reference - Model Genealogy|Llama-3.1-70B]] fine-tune he called "the world's top open-source model." The pitch was **reflection-tuning**: the model was trained to emit `<thinking>`, `<reflection>` and `<output>` tags so it could catch and fix its own mistakes mid-generation. The launch charts had it beating GPT-4o and Claude 3.5 Sonnet on MMLU (~89%), GSM8K, HumanEval and IFEval.

The weights on Hugging Face scored nowhere near the claims, roughly at base-Llama-3.1 level. Shumer said the HF upload was "corrupted" and pointed testers to a private API endpoint that *did* score high. Independent evaluators (Artificial Analysis and others) probed the endpoint and found signs it was proxying to a hosted frontier model instead of running Reflection weights. It refused to write the literal string "Claude" (a downstream word filter), its outputs matched Claude 3.5 Sonnet's style and refusal patterns, and its behavior shifted as the backing model was swapped without notice. Reflection-tuning is a real idea in the literature, but the Reflection-70B *artifact* was never reproducible. Shumer later posted a partial apology. Community consensus settled on fraud or, charitably, gross misrepresentation.

The mechanical failure is the simplest in this note: **what you benchmarked wasn't what you shipped.** No pinned weights, no reproducible harness. Just a number and an API.

### GSM1k: the memorization audit (2024)

Scale AI's research team (Hugh Zhang et al., 2024, *A Careful Examination of Large Language Model Performance on Grade School Arithmetic*) had human annotators build **GSM1k**, ~1,250 fresh grade-school math problems matched to GSM8K's style and difficulty, and kept it *private* so it stayed out of pretraining corpora. Then they re-scored a range of open and closed models on both.

Frontier models (GPT-4, Claude, Gemini) showed essentially no gap, meaning real capability. Several open families dropped by up to **~13%** from GSM8K to GSM1k, with the worst overfitting in some Mistral and Phi checkpoints. The damning detail: they measured each model's *probability of generating* verbatim GSM8K test examples (a memorization proxy) and found it **positively correlated** with the GSM8K→GSM1k gap. The models most likely to have seen the test fell the most. That's [[Concept - Benchmark Contamination|contamination]] and [[Concept - Goodhart's Law in Model Evaluation|Goodhart]] caught in the act, with numbers.

### The Open LLM Leaderboard MMLU discrepancy (2023)

In 2023 users noticed the Hugging Face Open LLM Leaderboard listed LLaMA-65B's MMLU at around **48%**, while the LLaMA paper reported **63.4%** for the same weights. Fifteen points, same model. People accused the leaderboard of being broken.

Hugging Face investigated and published *"What's going on with the Open LLM Leaderboard?"*, a rare case of maintainers taking apart their own number in public. There was no bug. **"MMLU score" is under-specified**, and three widely used implementations disagreed:

- The **original Hendrycks code** compared the model's probability over the *full answer text* of each option.
- **EleutherAI's lm-eval-harness** (which the leaderboard used) compared the probability of only the *letter tokens* (`A`/`B`/`C`/`D`) as continuations.
- **HELM** used yet another prompt format and extraction.

Each is defensible, each gives a different number, and none is "the" MMLU score. Nobody cheated. The scoring rule wasn't part of the spec, so the measurement wasn't well-defined: a [[Concept - Statistical Rigor in Model Evaluation|reproducibility]] failure that looked like a scandal.

### AlpacaEval and the verbosity lever (2023–2024)

AlpacaEval (Dubois et al., Stanford) automated preference evaluation with a GPT-4 judge computing a win rate against a reference model. It correlated well with human preference, and it inherited human preference's worst confound: **longer answers win.** You could raise your AlpacaEval win rate materially by telling your model to pad, format and hedge more, with no change in substance.

Dubois et al. 2024 (*Length-Controlled AlpacaEval*) demonstrated the exploit and fixed it with a regression that separates response length from quality, giving a **length-controlled (LC) win rate**. LC raised Spearman correlation with Chatbot Arena to ~0.98 (from ~0.93 for raw win rate) and neutralized the "just be verbose" attack. The authors found the confound and shipped the fix, but for a year the leaderboard was partly ranking token count.

### Vendor cherry-picking: apples vs oranges by construction

The most common scandal has no single villain; everyone does a little of it. Launch charts routinely put **your** best-of-many-samples number against a **competitor's** single-shot number: `cons@64` or `maj@k` or `pass@k` on your side, `pass@1` on theirs (see [[Concept - Statistical Rigor in Model Evaluation|why k and n must match]]). Or the chart picks, without saying so, the subset, shot count or harness where you win. A reasoning model's `cons@64` *should* beat a rival's `pass@1`; you gave yourself 64 tries. The comparison measures sampling budget, not capability.

The clearest example is the **Devin demo** ([[Lore - The Devin Demo and the SWE-bench Reality Gap]]). Cognition's March 2024 launch claimed 13.86% resolved on SWE-bench "unassisted," against a prior 1.96%. Independent analysis later argued the headline was inflated by edited timing and by tasks that weren't the benchmark's. No single number was fabricated. The *framing* was the artifact.

### The Leaderboard Illusion (2025)

*The Leaderboard Illusion* (Singh et al., 2025) made a systemic critique of [[Breakdown - Chatbot Arena|Chatbot Arena / LMArena]]: that its practices favor large proprietary labs by design. The alleged mechanisms were undisclosed **private testing of many variants**, where a lab submits N models and only the best is revealed (best-of-N selection that inflates the winner); **selective retraction** of poor scores; and **data-access asymmetry**, with big labs harvesting far more Arena battle data to train on. LMArena published a rebuttal disputing the magnitude and intent.

However that resolves, the *statistical* point holds. If you can submit many variants and reveal only the best, the leaderboard reports a maximum instead of an estimate, and a maximum over 20 noisy variants beats an honest single submission for free.

## The lesson

The common thread isn't dishonesty. **"Run a benchmark" has enough degrees of freedom that an honest team optimizing hard will drift into a misleading number without ever lying.** Each scandal left a different one loose:

| Scandal | The loose degree of freedom | The mechanism |
|---|---|---|
| Reflection-70B | *Which artifact* is tested | Untethered from reproducible weights |
| GSM1k | *Which data* the model saw | Contamination → measures memory, not skill |
| MMLU discrepancy | *Which scoring rule* | Score not well-defined across harnesses |
| AlpacaEval | *A metric confound* (length) | Optimizer finds the confound, not quality |
| Cherry-picking | *k, n, subset, shots* mismatched | Not apples-to-apples by construction |
| Leaderboard Illusion | *Which variant* gets revealed | Best-of-N selection inflates the maximum |

As one rule, this is the whole [[Checklist - Trusting a Benchmark Number|trust checklist]]: **a benchmark number without a pinned harness, decontamination, confidence intervals and an apples-to-apples comparison is a marketing artifact, not a measurement.** The gaming is the eval-time cousin of training-time [[Lore - Reward Hacking Hall of Fame|reward hacking]]: an optimizer exploits an unspecified degree of freedom in the objective, on a different clock.

From outside, **the scandal almost always looks like fraud; from inside, like a process failure.** So the defense is procedural, not moral. You can't out-honest a loose spec. You close the degrees of freedom (pin the harness, hold out a private set, report CIs, match k) before you or a competitor is tempted. The counter-example is the [[Lore - The OPT-175B Logbook|OPT-175B logbook]]: a team that wrote down the ugly truth as it happened produced a document nobody could spin later, because the process left nothing unspecified to spin.

## Evidence status

| Case | Status | Basis |
|---|---|---|
| Reflection-70B | **Well-documented fiasco; widely judged fraud** | Public non-reproduction by Artificial Analysis and others; proxy-to-Claude tells; author's partial apology. Not a legal finding; "fraud" is community consensus. |
| GSM1k | **Peer-reviewed / quantified** | Zhang et al. 2024, held-out data, memorization–gap correlation reported. |
| MMLU discrepancy | **Verified, self-documented** | Hugging Face's own post-mortem; three harnesses reproduce three numbers. Not misconduct: an under-specified metric. |
| AlpacaEval length gaming | **Verified, fixed by the authors** | Dubois et al. 2024 demonstrated and debiased it (LC win rate). |
| Vendor cherry-picking | **Recurring pattern** | Structural (mismatched k/subset); individual charts range from sloppy to misleading. Devin demo is the concrete, contested example. |
| The Leaderboard Illusion | **Disputed** | One detailed paper (Singh et al. 2025) plus LMArena rebuttals; the best-of-N statistical concern is sound, the alleged magnitude/intent is contested. |

## Connections

- [[Concept - Benchmark Contamination]] — the mechanism GSM1k exposed; contamination is why fresh test data was needed to catch the overfit.
- [[Concept - Goodhart's Law in Model Evaluation]] — the general principle every one of these stories instantiates: the measure became a target and stopped measuring.
- [[Concept - Statistical Rigor in Model Evaluation]] — the fix for cherry-picking and the Leaderboard Illusion: matched k/n, confidence intervals, and honest sampling.
- [[Breakdown - Chatbot Arena]] — the leaderboard at the center of the 2025 governance critique; its Bradley-Terry CIs are exactly what best-of-N variant submission undermines.
- [[Checklist - Trusting a Benchmark Number]] — the procedural defense; each checklist item traces back to one of these incidents.
- [[Lore - The Devin Demo and the SWE-bench Reality Gap]] — the canonical demo-vs-reality cherry-picking case, told in full.
- [[Lore - Reward Hacking Hall of Fame]] — the training-time cousin; same optimizer-exploits-the-spec shape, seen inside RL instead of on a leaderboard.
- [[Lore - The OPT-175B Logbook]] — the counter-example: radical process honesty that left nothing to spin.
- [[Reference - Model Genealogy]] — Reflection-70B was a Llama-3.1 fine-tune whose provenance (and alleged proxying) is a genealogy question as much as an eval one.

## Sources
- Zhang et al. (2024) — *A Careful Examination of Large Language Model Performance on Grade School Arithmetic* (GSM1k). Held-out rebuild of GSM8K; quantifies overfit and correlates it with memorization.
- Dubois et al. (2024) — *Length-Controlled AlpacaEval*. Demonstrates and debiases the verbosity confound; LC win-rate ~0.98 correlation with Arena.
- Singh et al. (2025) — *The Leaderboard Illusion*. Alleges variant-submission and disclosure asymmetries on Chatbot Arena; disputed by LMArena.
- Hugging Face (2023) — *"What's going on with the Open LLM Leaderboard?"* Maintainer post-mortem of the MMLU cross-harness discrepancy.
- Reflection-70B episode (Sept 2024) — Shumer/HyperWrite claims; non-reproduction reports from Artificial Analysis and independent testers. Contemporaneous, community-documented.
