---
tags: [lore, domain/evaluation, level/unicorn]
aliases: [Reflection-70B, GSM1k, The Leaderboard Illusion, Open LLM Leaderboard MMLU discrepancy]
summary: "War stories where benchmark numbers turned out to be marketing: fraud, overfit, harness discrepancies, length gaming, and cherry-picking."
---

# Lore - Benchmark Scandals

> Every one of these started as a number in a launch chart and ended as a lesson about the difference between a *measurement* and a *marketing artifact*. Most were not fraud. The unsettling part is how few of them had to be.

## What happened

### Reflection-70B — the model that couldn't reproduce itself (Sept 2024)

On 5 September 2024, Matt Shumer (CEO of HyperWrite / OthersideAI) announced **Reflection-70B**, a [[Reference - Model Genealogy|Llama-3.1-70B]] fine-tune he called "the world's top open-source model." The pitch was **reflection-tuning**: the model was trained to emit `<thinking>`, `<reflection>`, and `<output>` tags so it could catch and correct its own mistakes mid-generation. The announcement charts showed it beating GPT-4o and Claude 3.5 Sonnet on MMLU (~89%), GSM8K, HumanEval, and IFEval.

Then people tried to run it. The weights uploaded to Hugging Face scored nowhere near the claims — roughly base-Llama-3.1 level. Shumer said the HF upload was "corrupted" and pointed testers at a private API endpoint that *did* score high. Independent evaluators (Artificial Analysis and others) probed that endpoint and found tells that it was proxying to a hosted frontier model rather than running Reflection weights: it would refuse to write the literal string "Claude" (a downstream word-filter), its outputs matched Claude 3.5 Sonnet's style and refusal patterns, and behavior shifted as the backing model was quietly swapped. Reflection-tuning is a real idea in the literature; the specific Reflection-70B *artifact* was never reproducible. Shumer later posted a partial apology. Community consensus settled on fraud or, charitably, gross misrepresentation.

The mechanical crime is the simplest one in this note: **the thing you benchmarked was not the thing you shipped.** No pinned weights, no reproducible harness — just a number and an API.

### GSM1k — the memorization audit (2024)

Scale AI's research team (Hugh Zhang et al., 2024, *A Careful Examination of Large Language Model Performance on Grade School Arithmetic*) did the obvious experiment nobody had published cleanly: they hired human annotators to build **GSM1k**, ~1,250 fresh grade-school math problems matched to GSM8K's style and difficulty, and held it *private* to keep it out of pretraining corpora. Then they re-scored a swath of open and closed models on both.

Frontier models (GPT-4, Claude, Gemini) showed essentially zero gap — genuine capability. But several open families dropped up to **~13%** from GSM8K to GSM1k, with the worst overfitting concentrated in some Mistral and Phi checkpoints. The killer detail: they measured each model's *probability of generating* verbatim GSM8K test examples (a memorization proxy) and found it **positively correlated** with the GSM8K→GSM1k gap. The models that had most likely seen the test were exactly the ones that fell the most. This is [[Concept - Benchmark Contamination|contamination]] and [[Concept - Goodhart's Law in Model Evaluation|Goodhart]] caught red-handed, quantified.

### The Open LLM Leaderboard MMLU discrepancy (2023)

In 2023, users noticed the Hugging Face Open LLM Leaderboard reported LLaMA-65B's MMLU at around **48%**, while the LLaMA paper reported **63.4%** for the same weights. Fifteen points, same model. Accusations of broken leaderboards flew.

Hugging Face investigated and published *"What's going on with the Open LLM Leaderboard?"* — a rare instance of maintainers dissecting their own number in public. The answer was not a bug; it was that **"MMLU score" is under-specified**. Three widely-used implementations disagreed:

- The **original Hendrycks code** compared the model's probability over the *full answer text* of each option.
- **EleutherAI's lm-eval-harness** (which the leaderboard used) compared the probability of just the *letter tokens* (`A`/`B`/`C`/`D`) as continuations.
- **HELM** used yet another prompt format and extraction.

Each is defensible; each yields a different number; none is "the" MMLU score. Nobody cheated. The scoring rule simply wasn't part of the spec, so the measurement wasn't well-defined — a [[Concept - Statistical Rigor in Model Evaluation|reproducibility]] failure masquerading as a scandal.

### AlpacaEval and the verbosity lever (2023–2024)

AlpacaEval (Dubois et al., Stanford) automated preference evaluation with a GPT-4 judge computing a win-rate against a reference model. It correlated well with human preference — and it inherited human preference's ugliest confound: **longer answers win.** You could raise your AlpacaEval win-rate materially by instructing your model to pad, format, and hedge more, with no change in substance.

Dubois et al. 2024 (*Length-Controlled AlpacaEval*) demonstrated the exploit and fixed it: a regression that decomposes response length from quality, yielding a **length-controlled (LC) win-rate**. LC win-rate pushed Spearman correlation with Chatbot Arena to ~0.98 (from ~0.93 for raw win-rate) and neutralized the "just be verbose" attack. This is the honest arc — a confound found, a debias shipped by the authors — but for a year the leaderboard was partly ranking token count.

### Vendor cherry-picking — apples vs oranges by construction

The most common scandal has no single villain because everyone does a little of it. Launch charts routinely compare **your** best-of-many-samples number against a **competitor's** single-shot number: `cons@64` or `maj@k` or `pass@k` on your side, `pass@1` on theirs (see [[Concept - Statistical Rigor in Model Evaluation|why k and n must match]]). Or the chart quietly picks the subset, shot count, or harness where you happen to win. Structurally, a reasoning model's `cons@64` *should* beat a rival's `pass@1` — you gave yourself 64 tries — so the comparison measures sampling budget, not capability.

The purest example is the **Devin demo** ([[Lore - The Devin Demo and the SWE-bench Reality Gap]]): Cognition's March 2024 launch claimed 13.86% resolved on SWE-bench "unassisted," against a prior 1.96% — a headline that independent analysis later argued was inflated by edited timing and tasks that weren't the benchmark's. No single number was fabricated; the *framing* was the artifact.

### The Leaderboard Illusion (2025)

*The Leaderboard Illusion* (Singh et al., 2025) leveled a systemic critique at [[Breakdown - Chatbot Arena|Chatbot Arena / LMArena]]: that its practices structurally advantage large proprietary labs. The alleged mechanisms — undisclosed **private testing of many variants** where a lab submits N models and only the best is revealed (a best-of-N selection that inflates the winner), **selective retraction** of poor scores, and **data-access asymmetry** where big labs harvest far more Arena battle data to train on. LMArena published a rebuttal disputing the magnitude and intent.

Whatever the resolution, the *statistical* point is airtight and worth internalizing: if you can submit many variants and reveal only the best, the leaderboard is reporting a maximum, not an estimate — and a maximum over 20 noisy variants beats an honest single submission for free.

## The lesson

Line the six up and the common thread is not dishonesty — most of these were not fraud. It is that **"run a benchmark" has enough degrees of freedom that an honest team optimizing hard will drift into a misleading number without ever lying.** Each scandal is a different degree of freedom left loose:

| Scandal | The loose degree of freedom | The mechanism |
|---|---|---|
| Reflection-70B | *Which artifact* is tested | Untethered from reproducible weights |
| GSM1k | *Which data* the model saw | Contamination → measures memory, not skill |
| MMLU discrepancy | *Which scoring rule* | Score not well-defined across harnesses |
| AlpacaEval | *A metric confound* (length) | Optimizer finds the confound, not quality |
| Cherry-picking | *k, n, subset, shots* mismatched | Not apples-to-apples by construction |
| Leaderboard Illusion | *Which variant* gets revealed | Best-of-N selection inflates the maximum |

Stated as one rule, this is the whole of the [[Checklist - Trusting a Benchmark Number|trust checklist]]: **a benchmark number without a pinned harness, decontamination, confidence intervals, and an apples-to-apples comparison is a marketing artifact, not a measurement.** The gaming here is the eval-time cousin of training-time [[Lore - Reward Hacking Hall of Fame|reward hacking]] — same shape (optimizer exploits an unspecified degree of freedom in the objective), different clock.

The non-obvious practitioner insight: **the scandal almost always looks like fraud from outside and like a process failure from inside.** The defense is therefore procedural, not moral. You cannot out-honest a loose spec — you have to *close the degrees of freedom* (pin the harness, hold out a private set, report CIs, match k) before you or a competitor is tempted. The counter-example that proves it is the [[Lore - The OPT-175B Logbook|OPT-175B logbook]]: a team that wrote down the ugly truth as it happened produced a document nobody could later spin, precisely because the process left nothing unspecified to spin.

## Evidence status

| Case | Status | Basis |
|---|---|---|
| Reflection-70B | **Well-documented fiasco; widely judged fraud** | Public non-reproduction by Artificial Analysis and others; proxy-to-Claude tells; author's partial apology. Not a legal finding — "fraud" is community consensus. |
| GSM1k | **Peer-reviewed / quantified** | Zhang et al. 2024, held-out data, memorization–gap correlation reported. |
| MMLU discrepancy | **Verified, self-documented** | Hugging Face's own post-mortem; three harnesses reproduce three numbers. Not misconduct — an under-specified metric. |
| AlpacaEval length gaming | **Verified, fixed by the authors** | Dubois et al. 2024 demonstrated and debiased it (LC win-rate). |
| Vendor cherry-picking | **Recurring pattern** | Structural (mismatched k/subset); individual charts range from sloppy to misleading. Devin demo is the concrete, contested exemplar. |
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
