---
tags: [concept, domain/safety-interp, level/advanced]
aliases: [SynthID-Text, text watermarking, AI text detection]
summary: "Biasing generation toward a secret token pattern to make LLM output statistically detectable, and why post-hoc detectors without a watermark fail."
---
# Concept - LLM Watermarking and Detection

> **One-paragraph hook:** You can't look at a paragraph and reliably tell whether an LLM wrote it. Perplexity "tells" are noisy, style varies by prompt, and human writers increasingly read like models anyway. Watermarking skips after-the-fact detection. It perturbs generation itself, at the moment tokens are [[Concept - Sampling and Decoding Parameters|sampled]], so that a later statistical test can separate watermarked from non-watermarked text with a computable false-positive rate. It's the one part of the provenance problem with a real mechanism behind it. Everything else in this space (DetectGPT, GPTZero-style classifiers) pattern-matches against a moving target and has already failed publicly.

## The mechanism

**Green/red list logit biasing** (Kirchenbauer et al. 2023, "A Watermark for Large Language Models," Maryland) is the reference scheme. At each generation step, hash the preceding token (or last *k* tokens) with a secret key to pseudo-randomly split the vocabulary $V$ into a green list $G$ of size $\gamma|V|$ (typically $\gamma = 0.25$–$0.5$) and a red list of everything else. Before softmax, add a fixed bias $\delta$ (typically 2–4 in logit units) to every green token's logit:

$$z_i' = z_i + \delta \cdot \mathbb{1}[i \in G]$$

Sampling then runs normally from the biased distribution. The green/red split is deterministic given the key and the preceding context, so a detector holding the key can recompute it for any passage without the generating model. For a passage of $T$ tokens, count the green tokens $|s|_G$ and compute a one-sided z-statistic against the null of unwatermarked text, where green tokens appear at their base rate $\gamma$:

$$z = \frac{|s|_G - \gamma T}{\sqrt{T\gamma(1-\gamma)}}$$

A threshold around $z > 4$ gives a false-positive rate near $3\times10^{-5}$. That's cheap detection with no model access and a calibrated error rate, which post-hoc classifiers can't offer.

**Distortion-free / cryptographic schemes** leave the output distribution unbiased. Aaronson's Gumbel-max scheme derives a pseudorandom score vector from a context hash and picks the token maximizing $\log p_i + G_i$, a Gumbel-max reparameterization of sampling from $p$. The *marginal* distribution of any single token is untouched, but the joint sequence correlates with the pseudorandom key, and a detector can recover that. Kuditipudi et al. 2023 ("Robust Distortion-free Watermarks for Language Models") add an edit-distance-based alignment detector, giving up some detection power for much better robustness to insertions and deletions.

**SynthID-Text** (Dathathri et al., Google DeepMind, 2024, published in *Nature*) uses tournament sampling. Candidate tokens compete over several pseudorandom-scored rounds, like a bracket, and the winner is emitted. It's the first watermarking scheme deployed at production scale, shipping in Gemini-generated text (as of 2024), because it was engineered for the quality/detectability tradeoff at that scale instead of as a research proof of concept.

## In practice

The core design tradeoff is a triangle: **watermark strength vs. text quality vs. robustness to edits.** A larger $\delta$ makes detection more reliable on short passages but visibly distorts word choice, since the model reaches for green-list synonyms even when they fit worse. A smaller $\delta$ keeps quality but needs a longer passage before the z-test clears threshold. Teams tune $\gamma$ and $\delta$ against a fixed detection target (e.g., $z > 4$ at $T \geq 200$ tokens), not in isolation.

Detection needs only the secret key (or, for open schemes, the hash function), not the generating model's weights. That's the practical advantage over classifier-based detection, which needs the original model or a trained surrogate and degrades as models get fine-tuned or swapped. Deployments use watermarking for provenance labeling, i.e. identifying a lab's own output at scale, and not as an adversarial anti-cheating tool, because a determined adversary can defeat it (below).

## Failure modes

- **Paraphrasing and round-trip translation** almost completely wash out the green/red pattern. Translate a watermarked passage to another language and back, or run it through a second LLM paraphraser, and the green-token fraction drops back toward the base rate, because the hash-derived pattern is tied to the exact token sequence and not the meaning. Detection: nothing reliable. This is the watermark's fundamental weakness, not a bug.
- **Token substitution and the "emoji attack"** (inserting emoji or other easily stripped tokens that the detector's tokenizer segments unpredictably) shift the hashed context window enough to desynchronize green/red assignment for later tokens. The z-score drops and the text looks undamaged.
- **Spoofing.** An attacker who can query a watermarked model enough to infer its green/red pattern for common contexts can forge the watermark onto text the model never wrote, or strip it from text it did. That's a real security problem for any scheme that wants watermark presence to count as evidence in a dispute.
- **Post-hoc detection without a watermark is unreliable, and it's the production failure people actually hit.** DetectGPT (Mitchell et al. 2023) uses probability curvature: watermark-free text sits at a local maximum of log-probability under small perturbations, human text less so. GPTZero-style tools use perplexity and burstiness heuristics. Both have meaningful false-positive rates on non-native-English writing, which looks more uniform and lower-perplexity to these detectors. OpenAI retired its own AI-text classifier in 2023 for this reason, citing a low accuracy rate.

## The non-obvious

Watermarking needs generation **entropy**. The bias $\delta$ can only change *which* token gets picked when several tokens are plausible. Low-entropy text (a function signature, a list of known facts, a fixed-format address) has one essentially forced next token at most positions, leaving no room for a green/red split to leave a signal. The [[Concept - Entropy and Cross-Entropy|per-token entropy]] of the generation sets watermark strength, not passage length. Code and factual boilerplate are close to unwatermarkable in practice however large you make $\delta$. That's a hard limit and not an implementation gap: a logit bias can't do much to a near-deterministic distribution.

## Connections
- [[Concept - Sampling and Decoding Parameters]] — watermarking operates by perturbing the same logit-to-token sampling step this note describes; the bias $\delta$ is applied before the standard temperature/top-p sampling.
- [[Concept - Entropy and Cross-Entropy]] — the per-token entropy of the generation directly bounds how much watermark signal can be embedded, per the non-obvious point above.
- [[Concept - KL Divergence]] — quantifies exactly how much a biased-sampling watermark distorts the output distribution relative to the unwatermarked model, the formal version of the quality cost in the tradeoff triangle.
- [[Concept - Hypothesis Testing and p-values]] — the z-test detection procedure is a direct application of one-sided hypothesis testing against a known null distribution.
- [[Deep Dive - Diffusion Models]] — image/video watermarking (e.g., SynthID for images) faces an analogous detectability/quality tradeoff in a very different sampling process, worth contrasting.
- [[Reference - Jailbreak and Prompt Injection Attack Catalog]] — watermark-stripping via paraphrase sits alongside other adversarial text-transformation attacks catalogued there.
- [[Concept - The Evaluation Gap]] — provenance and detection tooling is one of the concrete gaps between "the model can be misused" and "we have deployed infrastructure to catch it."
- [[Concept - Membership Inference for Contamination Detection]] — a structurally similar detection problem (statistical test for whether text came from a specific source/process) using different signal.

## Sources
- Kirchenbauer, J. et al. (2023) — "A Watermark for Large Language Models." Introduces the green/red list logit-biasing scheme and the z-test detector this note centers on.
- Kuditipudi, R. et al. (2023) — "Robust Distortion-free Watermarks for Language Models." Alignment-based detection for a distortion-free (Gumbel-max) watermark, robust to edits.
- Dathathri, S. et al. (2024) — "Scalable watermarking for identifying large language model outputs" (Nature, Google DeepMind). SynthID-Text's tournament-sampling scheme, deployed in Gemini.
- Mitchell, E. et al. (2023) — "DetectGPT: Zero-Shot Machine-Generated Text Detection using Probability Curvature." The leading post-hoc (no-watermark) detection method and its statistical basis.
