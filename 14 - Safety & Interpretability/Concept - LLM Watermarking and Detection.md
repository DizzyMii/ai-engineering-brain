---
tags: [concept, domain/safety-interp, level/advanced]
aliases: [SynthID-Text, text watermarking, AI text detection]
summary: "Biasing generation toward a secret token pattern to make LLM output statistically detectable, and why post-hoc detectors without a watermark fail."
---
# Concept - LLM Watermarking and Detection

> **One-paragraph hook:** You cannot look at a paragraph of text and reliably tell whether an LLM wrote it — perplexity "tells" are noisy, style varies by prompt, and human writers increasingly read like models anyway. Watermarking sidesteps the detection problem by not trying to solve it after the fact: it perturbs generation itself, at the moment tokens are [[Concept - Sampling and Decoding Parameters|sampled]], so that a statistical test applied later can distinguish watermarked from non-watermarked text with a computable false-positive rate. It is the one piece of the provenance problem with an actual mechanism behind it — everything else in this space (DetectGPT, GPTZero-style classifiers) is pattern-matching against a moving target and has already produced public failures.

## The mechanism

**Green/red list logit biasing** (Kirchenbauer et al. 2023, "A Watermark for Large Language Models," Maryland) is the reference scheme. At each generation step, hash the preceding token (or last *k* tokens) with a secret key to pseudo-randomly partition the vocabulary $V$ into a green list $G$ of size $\gamma|V|$ (typically $\gamma = 0.25$–$0.5$) and a red list of the rest. Before softmax, add a fixed bias $\delta$ (typically 2–4 in logit units) to every green-listed token's logit:

$$z_i' = z_i + \delta \cdot \mathbb{1}[i \in G]$$

Sampling proceeds normally from the biased distribution. Because the green/red split is deterministic given the key and the preceding context, a detector holding the key can recompute it for any candidate passage without needing the generating model at all. For a passage of $T$ tokens, count the observed green tokens $|s|_G$ and compute a one-sided z-statistic against the null hypothesis of unwatermarked text (green tokens occurring at their base rate $\gamma$):

$$z = \frac{|s|_G - \gamma T}{\sqrt{T\gamma(1-\gamma)}}$$

A threshold around $z > 4$ gives a false-positive rate near $3\times10^{-5}$ — cheap, no-model-access detection with a calibrated error rate, which is exactly what post-hoc classifiers cannot offer.

**Distortion-free / cryptographic schemes** avoid biasing the output distribution at all. Aaronson's Gumbel-max scheme derives a pseudorandom score vector from a context hash and selects the token that maximizes $\log p_i + G_i$ (a Gumbel-max reparameterization of sampling from $p$) — the *marginal* distribution over any single token is untouched, but the joint sequence carries a correlation with the pseudorandom key that a detector can recover. Kuditipudi et al. 2023 ("Robust Distortion-free Watermarks for Language Models") extend this with an edit-distance-based alignment detector, trading some detection power for much better robustness to insertions and deletions.

**SynthID-Text** (Dathathri et al., Google DeepMind, 2024, published in *Nature*) uses tournament sampling: candidate tokens compete across several pseudorandom-scored rounds analogous to a tournament bracket, and the winner is emitted. This is the first watermarking scheme deployed at production scale — it ships in Gemini-generated text (as of 2024) — because it was engineered explicitly for the quality/detectability tradeoff at that scale rather than as a research proof of concept.

## In practice

The core design axis is a **tradeoff triangle: watermark strength vs. text quality vs. robustness to edits.** A larger $\delta$ makes detection more reliable at short passage lengths but visibly distorts word choice (the model reaches for green-list synonyms even when they fit worse); a smaller $\delta$ preserves quality but needs a longer passage before the z-test clears threshold. Teams tune $\gamma$ and $\delta$ against a fixed detection target (e.g., $z > 4$ at $T \geq 200$ tokens) rather than picking values in isolation.

Detection needs no access to the generating model's weights, only the secret key (or, for open schemes, the hash function) — this is the practical win over classifier-based detection, which requires either the original model or a trained surrogate and degrades as models are fine-tuned or swapped. Deployments use watermarking for content-provenance labeling (distinguishing a lab's own output at scale) rather than as an adversarial anti-cheating tool, because determined adversaries can defeat it (below).

## Failure modes

- **Paraphrasing and round-trip translation** wash out the green/red pattern almost completely — translating a watermarked passage to another language and back, or running it through a second LLM paraphraser, drops the green-token fraction back toward the unwatermarked base rate, since the hash-derived pattern is tied to the exact token sequence, not the meaning. Detection: none reliable; this is the watermark's fundamental weakness, not a bug.
- **Token substitution and the "emoji attack"** (inserting emoji or other easily-strippable tokens the detector's tokenizer segments unpredictably) shift the hashed context window enough to desynchronize green/red assignment for downstream tokens, degrading the z-score without visibly damaging the text.
- **Spoofing**: an attacker who can query a watermarked model enough to infer its green/red pattern for common contexts can forge the watermark onto text the model never generated, or strip it from text it did — a genuine security concern for any scheme trying to use watermark presence as evidence in a dispute.
- **Post-hoc detection without a watermark is unreliable and this is the actual production failure mode people hit.** DetectGPT (Mitchell et al. 2023) uses probability-curvature (watermarked-free text sits at a local maximum of log-probability under small perturbations, human text less so); GPTZero-style tools use perplexity and burstiness heuristics. Both produce meaningful false-positive rates on non-native-English writing, which reads as more uniform/lower-perplexity to these detectors — OpenAI retired its own AI-text classifier in 2023 for exactly this reason, citing a low accuracy rate.

## The non-obvious

Watermarking fundamentally needs generation **entropy** to work: at each step the bias $\delta$ can only change *which* token gets picked if there are multiple plausible tokens to choose between. Low-entropy text — a function signature, a list of known facts, a fixed-format address — has one essentially-forced next token at most positions, so there is no room for a green/red split to leave a signal; the [[Concept - Entropy and Cross-Entropy|per-token entropy]] of the generation, not the length of the passage, is what determines watermark strength. Code and factual boilerplate are close to unwatermarkable in practice regardless of how large you make $\delta$, which is a structural limit, not an implementation gap — it follows directly from what a logit bias can and cannot do to a near-deterministic distribution.

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
