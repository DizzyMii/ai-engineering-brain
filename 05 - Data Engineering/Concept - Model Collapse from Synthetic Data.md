---
tags: [concept, domain/data-engineering, level/frontier]
aliases: [model collapse, model autophagy disorder, MAD, curse of recursion, recursive training collapse]
summary: "Recursive training on model output narrows the learned distribution and kills the tails — but only under replace, not accumulate."
---
# Concept - Model Collapse from Synthetic Data

> **One-paragraph hook:** Train a model on the output of a previous model, then train the next one on *that* output, and keep going. The learned distribution contracts every generation, the tails go first, and the model converges toward bland, high-probability slop. That's model collapse. It became a headline scare in 2024 ("the internet is filling with AI text and the models will eat themselves"), but the honest version is narrower and more useful. Collapse is a property of the *training protocol*: do you replace real data with synthetic, or accumulate it? It isn't a curse built into [[Concept - Synthetic Training Data]]. Knowing which regime you're in tells you whether to panic.

## The mechanism

Two error sources compound multiplicatively across generations:

1. **Statistical (finite-sample) error.** Each generation trains on a finite sample drawn from the previous model. An event with true probability $p$ appears zero times in a sample of size $m$ with probability $(1-p)^m \approx e^{-pm}$. For rare events ($p < 1/m$) that's a coin-flip or worse. Every resampling step silently deletes a slice of the low-probability tail, and the deletion is *permanent*: generation $n{+}1$ can't re-learn a mode it never saw. This alone causes collapse, even with an infinitely expressive model and a perfect fitter.
2. **Functional (approximation/representation) error.** Real models can't perfectly represent the tail even from data they do see. Limited capacity, finite training and biased estimators (a fitted Gaussian's variance estimate is itself noisy) all pull the learned distribution toward its center of mass.

Shumailov et al. (2024, *Nature*, "AI models collapse when trained on recursively generated data") formalized this on LMs, VAEs and Gaussian mixtures. The toy case: recursively fit a Gaussian by drawing $m$ samples, fitting $(\hat\mu,\hat\sigma^2)$, drawing $m$ more from the fit, refitting. The variance does a random walk whose expected log shrinks each step, so

$$\hat\sigma_n^2 \xrightarrow{\text{a.s.}} 0 \quad \text{as } n\to\infty,$$

i.e. the distribution collapses to a delta almost surely, even though the mean stays unbiased. The Wasserstein distance from the original distribution grows without bound. For language: perplexity on real held-out text rises, rare tokens and constructions vanish, and generations pile up on the mode. Shumailov separates **early collapse** (tails erode, variance shrinks, still fluent) from **late collapse** (the distribution degenerates to a narrow, often repetitive attractor). Alemohammad et al. (2023, "Self-Consuming Generative Models Go MAD") independently named the image-domain version *Model Autophagy Disorder* and showed the same three regimes: fully synthetic loops go MAD fastest, and fresh-data injection each round is the antidote. So it isn't an artifact of one modality.

### The caveat that defuses the scare

The *Nature* setup **replaces** real data with synthetic each round. Gerstgrasser et al. (2024, "Is Model Collapse Inevitable? Breaking the Curse of Recursion by Accumulating Real and Synthetic Data") showed that if you **accumulate** instead, keeping all the real data and *adding* synthetic each generation, test error stays bounded and converges. The intuition: while the original real corpus stays in the mix, the loss on it anchors the fit. The real tail is physically present in the training set every round, so finite-sample tail deletion can't compound. Real pipelines accumulate (nobody deletes The Pile to make room for last quarter's synthetic), which makes the "models will inevitably eat themselves" framing overstated. What's left is a real but manageable risk in specific loops.

## In practice

Where it actually bites:

- **The involuntary web-recursion loop.** Since ChatGPT (Nov 2022), the open web has been filling with LLM output, so each new [[Concept - Common Crawl and Web Data at Scale|Common Crawl]] dump ingests more model text. It's an *unintentional* replace-ish loop nobody opted into. Pre-2023 crawls have picked up scarcity value as a result. The analogy is **low-background steel**: steel smelted before the 1945 nuclear tests, salvaged from pre-war shipwrecks because it's free of fallout radionuclides. Pre-ChatGPT text is "low-background" data, uncontaminated by model output. The same pressure has moved provenance and [[Concept - LLM Watermarking and Detection]] (tagging synthetic text so you can exclude it later) from nice-to-have to strategically valuable, and raised the [[Concept - Copyright and Licensing of Training Data|licensing]] value of clean archival corpora.
- **Naive self-improvement loops.** Iterated self-training (generate SFT data with your model, fine-tune on it, repeat) is a deliberate replace loop and *will* narrow diversity if unguarded. Same family as [[Concept - Mode Collapse in RLHF]], where preference optimization contracts the output distribution toward reward-maximizing modes.
- **Why curated synthetic doesn't collapse.** Phi (see [[Breakdown - The Phi Models and Textbook-Quality Data]]) and WRAP do well on synthetic tokens because they *filter, verify, mix with real data, and generate for coverage*. Collapse comes from **unfiltered recursive replacement**, not from synthetic data per se. A verifier that keeps only correct or diverse samples turns each round from a contraction into a bounded improvement. That's how generate-then-verify (RLVR, rejection sampling) works where naive self-training fails.

The safe operating point is synthetic tokens accumulated into a [[Concept - Data Mixtures|data mixture]] and anchored by a large real fraction. The unsafe one is any pipeline where the real fraction trends toward zero over time.

## Failure modes

- **Silent generative narrowing while metrics look fine.** This is the dangerous case. Validation perplexity on real held-out data can *improve* (the model gets very good at the head) while generation diversity dies, so a val-loss-only monitor won't see it. **Detection:** measure generation-side diversity across successive model generations: output entropy, self-BLEU, distinct-$n$, or [[Concept - Entropy and Cross-Entropy|entropy]] of the next-token distribution on a fixed prompt set. A collapsing pipeline shows *monotonically falling* generation diversity. The trend is the signal, not any single number.
- **Tail deletion hits minorities first.** Rare dialects, long-tail entities, uncommon facts and stylistic variety live in the low-$p$ tail, so they go first. It's the same demographic skew lexical filtering causes, arriving by a different route.
- **Compounding in multi-round distillation.** Distilling generation $k$ from generation $k{-}1$ over many rounds without re-injecting real data reproduces the *Nature* replace regime in miniature.

## The non-obvious

How bad collapse looks depends mostly on *measurement and protocol choices*, not on whether the data is "fake." The scary result used pure replacement, an unrealistic setting. The reassuring result used accumulation, which is what real teams do. One knob makes the same phenomenon look apocalyptic or benign. [[Concept - The Emergent Abilities Debate]] taught the same lesson: a striking published curve can be an artifact of protocol and metric, so read the axes before you extrapolate.

For a data team, the exposure isn't "we used synthetic data." It's (a) the involuntary web-recursion channel, handled with provenance filtering and pre-2023 anchors, and (b) any home-grown self-training loop where the real-data fraction decays to zero unnoticed, handled by *accumulating and verifying* and by watching generation diversity instead of val loss. The [[Concept - Scaling Laws|scaling-law]] view under a fixed token budget sharpens this. Synthetic data raises effective quality-per-token only while it adds *new* information, and recursive synthetic adds none. Once real data stops anchoring the mix, you're spending compute to sharpen the head and amputate the tail.

## Connections
- [[Concept - Synthetic Training Data]] — the core note on healthy synthetic generation; collapse is its specific failure mode under recursive replacement without filtering.
- [[Concept - Data Mixtures]] — accumulation-not-replacement is a mixture decision: keep a large real fraction anchoring every generation.
- [[Concept - Scaling Laws]] — recursive synthetic adds no new information, so it can't move the quality-per-token term that compute-optimal training is bottlenecked on.
- [[Concept - Entropy and Cross-Entropy]] — the detection instrument: falling generation entropy across model generations is the collapse signature.
- [[Concept - Copyright and Licensing of Training Data]] — provenance and "low-background" pre-2023 corpora gain value precisely because the web is now a recursive loop.
- [[Concept - LLM Watermarking and Detection]] — tagging synthetic text is how you break the involuntary web-recursion channel at ingest time.
- [[Concept - Mode Collapse in RLHF]] — the post-training sibling: distribution narrowing driven by optimization pressure rather than recursive resampling.
- [[Concept - The Emergent Abilities Debate]] — the same meta-lesson that a dramatic curve can be a measurement/protocol artifact; read the axes before extrapolating collapse.
- [[Concept - Common Crawl and Web Data at Scale]] — the involuntary recursion channel: each new dump ingests more model text, making pre-2023 crawls "low-background" data.
- [[Breakdown - The Phi Models and Textbook-Quality Data]] — the counterexample proving synthetic data is safe when filtered, verified, and mixed with real data rather than recursively replaced.
- [[Gotchas - Pretraining Data Pipelines]] — where collapse monitoring (diversity metrics, provenance filtering) lives operationally in a real corpus build.

## Sources
- Shumailov et al. (2024) — "AI models collapse when trained on recursively generated data" (*Nature*): the formal replace-regime result across LMs, VAEs, and GMMs; early vs late collapse.
- Gerstgrasser et al. (2024) — "Is Model Collapse Inevitable? Breaking the Curse of Recursion by Accumulating Real and Synthetic Data": the accumulate-vs-replace distinction that bounds the error.
- Alemohammad et al. (2023) — "Self-Consuming Generative Models Go MAD": the image-domain version (Model Autophagy Disorder) and the three self-consuming regimes.
- Shumailov et al. (2023) — "The Curse of Recursion: Training on Generated Data Makes Models Forget": the earlier preprint that introduced the mechanism.
