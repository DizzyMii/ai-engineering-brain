---
tags: [concept, domain/data-engineering, level/frontier]
aliases: [model collapse, model autophagy disorder, MAD, curse of recursion, recursive training collapse]
summary: "Recursive training on model output narrows the learned distribution and kills the tails — but only under replace, not accumulate."
---
# Concept - Model Collapse from Synthetic Data

> **One-paragraph hook:** Model collapse is what happens when you train a model on the output of a previous model, then train the next model on *that* output, and so on: the learned distribution contracts generation after generation, the tails disappear first, and the model converges toward bland, high-probability slop. It became a headline scare in 2024 ("the internet is filling with AI text and the models will eat themselves"), but the honest version is narrower and more useful — collapse is a property of the *training protocol* (do you replace real data with synthetic, or accumulate it?), not a curse inherent to [[Concept - Synthetic Training Data]]. Knowing which regime you're in tells you whether to panic or not.

## The mechanism

Collapse is driven by two error sources that compound multiplicatively across generations:

1. **Statistical (finite-sample) error.** Each generation trains on a finite sample drawn from the previous model. Any event with true probability $p$ appears zero times in a sample of size $m$ with probability $(1-p)^m \approx e^{-pm}$. For rare events — $p < 1/m$ — that's a coin-flip or worse. So every resampling step silently deletes a slice of the low-probability tail, and the deletion is *permanent*: generation $n{+}1$ can't re-learn a mode it never saw. This alone causes collapse even with an infinitely expressive model and a perfect fitter.
2. **Functional (approximation/representation) error.** Real models can't perfectly represent the tail even from the data they do see — limited capacity, finite training, and biased estimators (a fitted Gaussian's variance estimate is itself noisy) all push the learned distribution toward its center of mass.

Shumailov et al. (2024, *Nature*, "AI models collapse when trained on recursively generated data") formalized this on LMs, VAEs, and Gaussian mixtures. The clean toy case: recursively fit a Gaussian by drawing $m$ samples, fitting $(\hat\mu,\hat\sigma^2)$, drawing $m$ more from the fit, refitting. The variance is a random walk whose expected log shrinks each step, so

$$\hat\sigma_n^2 \xrightarrow{\text{a.s.}} 0 \quad \text{as } n\to\infty,$$

i.e. the distribution collapses to a delta almost surely, even though the mean stays unbiased. The Wasserstein distance from the original distribution grows without bound. In language terms: perplexity on real held-out text rises, rare tokens and constructions vanish, and generations pile up on the mode. Shumailov distinguishes **early collapse** (tails erode, variance shrinks, still fluent) from **late collapse** (the distribution degenerates to a narrow, often repetitive attractor). Alemohammad et al. (2023, "Self-Consuming Generative Models Go MAD") independently named the image-domain version *Model Autophagy Disorder* and showed the same three regimes (fully synthetic loops go MAD fastest; fresh-data injection each round is the antidote), so this is not an artifact of one modality.

### The caveat that defuses the scare

The *Nature* setup **replaces** real data with synthetic each round. Gerstgrasser et al. (2024, "Is Model Collapse Inevitable? Breaking the Curse of Recursion by Accumulating Real and Synthetic Data") showed that if instead you **accumulate** — keep all the real data and *add* synthetic each generation — the test error stays bounded and converges rather than diverging. Intuition: as long as the original real corpus remains in the mix, the loss on it anchors the fit and the finite-sample tail deletion can't compound, because the real tail is still physically present in the training set every round. Real pipelines accumulate (nobody deletes The Pile to make room for last quarter's synthetic), so the apocalyptic "models will inevitably eat themselves" framing is overstated. What survives is a real but manageable risk in specific loops.

## In practice

The concrete channels where this actually bites:

- **The involuntary web-recursion loop.** Since ChatGPT (Nov 2022), the open web has been filling with LLM output, so each new [[Concept - Common Crawl and Web Data at Scale|Common Crawl]] dump ingests more model text — an *unintentional* replace-ish loop nobody opted into. This is why pre-2023 crawls have acquired scarcity value, by direct analogy to **low-background steel** (steel smelted before the 1945 nuclear tests, salvaged from pre-war shipwrecks because it's free of fallout radionuclides): pre-ChatGPT text is "low-background" data uncontaminated by model output. It's also why provenance and [[Concept - LLM Watermarking and Detection]] — being able to tag and later exclude synthetic text — have risen from nice-to-have to strategically valuable, and why the [[Concept - Copyright and Licensing of Training Data|licensing]] value of clean archival corpora went up.
- **Naive self-improvement loops.** Iterated self-training — generate SFT data with your model, fine-tune on it, repeat — is a deliberate replace loop and *will* narrow diversity if unguarded. This is the same family as [[Concept - Mode Collapse in RLHF]], where preference optimization contracts the output distribution toward reward-maximizing modes.
- **Why curated synthetic doesn't collapse.** Phi (see [[Breakdown - The Phi Models and Textbook-Quality Data]]) and WRAP thrive on synthetic tokens because they *filter, verify, mix with real data, and generate for coverage*. Collapse is about **unfiltered recursive replacement**, not synthetic data per se — a verifier that keeps only correct/diverse samples turns each round from a contraction into a bounded improvement, which is exactly why generate-then-verify (RLVR, rejection sampling) works where naive self-training fails.

Synthetic tokens accumulated into a [[Concept - Data Mixtures|data mixture]] and anchored by a large real fraction is the safe operating point; the unsafe one is any pipeline where the real fraction trends toward zero over time.

## Failure modes

- **Silent generative narrowing while metrics look fine.** The dangerous case: validation perplexity on real held-out data can *improve* (the model gets very good at the head) while generation diversity dies. If your only monitor is val loss you won't see it. **Detection:** measure generation-side diversity across successive model generations — output entropy, self-BLEU, distinct-$n$, or [[Concept - Entropy and Cross-Entropy|entropy]] of the next-token distribution on a fixed prompt set. A collapsing pipeline shows *monotonically falling* generation diversity; that trend, not any single number, is the signal.
- **Tail deletion hits minorities first.** Rare dialects, long-tail entities, uncommon facts, and stylistic variety are the first casualties because they live in the low-$p$ tail — the same demographic-skew failure that lexical filtering causes, arriving through a different door.
- **Compounding in multi-round distillation.** Distilling generation $k$ from generation $k{-}1$ over many rounds without re-injecting real data reproduces the *Nature* replace regime in miniature.

## The non-obvious

Collapse severity is dominated by the *measurement and protocol choices*, not by whether the data is "fake." The scary result used pure replacement — an unrealistic setting — and the reassuring result used accumulation, which is what real teams do; the same phenomenon looks apocalyptic or benign depending on that one knob. This echoes the lesson of [[Concept - The Emergent Abilities Debate]]: a striking published curve can be an artifact of the protocol and metric rather than a law of nature, so read the axes before you extrapolate. The practical corollary for a data team: your real exposure isn't "we used synthetic data," it's (a) the involuntary web-recursion channel, which you address with provenance filtering and pre-2023 anchors, and (b) any home-grown self-training loop where the real-data fraction quietly decays to zero — which you address by *accumulating and verifying*, and by watching generation diversity, not val loss. Under a fixed token budget the [[Concept - Scaling Laws|scaling-law]] framing sharpens it: synthetic data raises effective quality-per-token only while it adds *new* information; recursive synthetic adds none, so past the point where real data stops anchoring the mix you're spending compute to sharpen the head and amputate the tail.

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
