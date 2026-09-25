---
tags: [concept, domain/safety-interp, level/advanced]
aliases: [logit lens, tuned lens]
summary: "Projecting an intermediate residual-stream state through the model's own unembedding to read its provisional next-token guess at that layer."
---
> **One-paragraph hook:** A transformer officially "answers" once, at the final layer, but the [[Deep Dive - Mechanistic Interpretability|residual stream]] it builds that answer from is available at every layer on the way. The logit lens is the cheapest interpretability probe there is. Take the intermediate residual stream at layer $\ell$, run it through the same final normalization and unembedding the model would use if that were the last layer, and read off a provisional next-token distribution. No training, no intervention, one matrix multiply using machinery the model already has. That provisional distribution often turns out to be a readable guess that sharpens layer by layer, which gives you a free view of *when* in the forward pass an answer forms.

## The mechanism

The technique, from nostalgebraist (2020, LessWrong), is the model's own last step applied early. If the model normally computes final logits as $\text{logits} = \text{LN}_f(x_L)\,W_U$ from the final residual stream $x_L$ and unembedding matrix $W_U$, the logit lens computes:

$$\text{logits}_\ell = \text{LN}_f(x_\ell)\,W_U, \qquad \ell < L$$

That is, it feeds an earlier layer's residual stream $x_\ell$ into the same final [[Concept - RMSNorm and LayerNorm|LayerNorm]] and [[Concept - Softmax|softmax]] pipeline the model uses at layer $L$. The result means something only because the residual stream is additive and linear (see [[Deep Dive - Mechanistic Interpretability]]). $x_\ell$ already holds a partial sum of everything that will make up $x_L$, so projecting it early through the model's own readout gives a legitimate, incomplete version of the same computation, not nonsense from an arbitrary intermediate tensor.

Run it layer by layer across a prompt and you see prediction as iterative refinement across depth, not a single event at the end. Early layers' readout is often dominated by detokenization noise, sorting out surface artifacts like [[Concept - Embeddings as Learned Representations|subword/BPE]] boundary ambiguity and saying little about the eventual answer. Middle layers start promoting semantically related candidates without committing. Late layers sharply promote the actual output token, often several layers before the final one. Finding the layer where the correct answer first becomes the top logit-lens candidate is now a standard diagnostic for "where in the network does this fact live." It complements, and costs far less than, full [[Concept - Activation Patching|activation patching]] to establish the same thing causally.

The raw lens has a systematic bias. $W_U$ and $\text{LN}_f$ were only trained to work on $x_L$, so applying them to $x_\ell$ assumes intermediate layers already share the final layer's basis, which isn't quite true. The **tuned lens** (Belrose et al. 2023) fixes this with a small learned per-layer affine translator, $x_\ell \mapsto A_\ell x_\ell + b_\ell$, trained cheaply by distillation against the model's actual final-layer output to correct each layer's bias before the shared unembedding. It's consistently more faithful than the raw lens, most of all in early layers where the basis mismatch is worst, at the cost of a little per-model training.

## In practice

The layer-wise readout has engineering uses beyond diagnosis. It guides **early-exit** decoding and some [[Concept - Speculative Decoding|speculative-decoding]] draft strategies, where "has the answer stabilized by layer $\ell$?" decides whether computation for that token can stop early without changing the sampled output. It also underlies **DoLa** decoding (Chuang et al. 2023), which contrasts a logit-lens-style distribution from an early (premature) layer with the final-layer distribution and amplifies the difference. The idea is that factual knowledge tends to sharpen in later layers, so the contrast suppresses low-confidence, hallucination-prone tokens an early layer would have favored.

It costs one matrix multiply against activations you'd typically cache anyway, so the logit lens is usually the *first* thing a practitioner runs before anything from the [[Concept - Sampling and Decoding Parameters|decoding]] or [[Deep Dive - Mechanistic Interpretability|circuits]] toolkits. It's cheap enough to run on every layer of every prompt by habit, unlike patching or SAE feature extraction, which need deliberate setup.

## Failure modes

- **Over-reading garbled early-layer output.** In the first several layers the readout is often a jumble of unrelated or oddly specific subword fragments, because early residual-stream states really haven't been refined into anything like the final-layer basis. Detection: read early-layer output as telling you *whether* the model has settled on an answer (it usually hasn't), not *what* it's thinking. Don't narrate a story from noise.
- **Basis mismatch in architectures with strong per-layer rescaling.** Models with aggressive RMSNorm scaling or certain rotary-embedding interactions can keep intermediate representations rotated or rescaled away from the final unembedding basis further than the raw lens assumes. The readouts then become systematically misleading, which is worse than uninformative. Detection: compare raw-lens and tuned-lens output on the same model. A large, consistent gap means the raw lens is actively misleading there.
- **Treating the projected distribution as the model's literal belief.** The logit lens is a linear projection of an intermediate state. It doesn't show the model "thinking token X" at layer $\ell$ in any deeper sense. The caution about reading attention weights as explanations applies: a legible number isn't automatically a faithful one. Detection: back a logit-lens finding with a causal check ([[Concept - Activation Patching|patching]]) before treating "layer $\ell$ is where fact X lives" as established.

## The non-obvious

The logit lens only works because the residual stream and the unembedding share a basis that the model is implicitly pushed to maintain across layers. That's a side effect of the additive residual structure, not a guaranteed property of every possible architecture. So how well the lens works is itself evidence about the model. If the raw lens is unusually garbled at a layer where the tuned lens is clean, that layer's representation is rotated relative to the output basis, which is the gap the tuned lens was built to measure and correct. Push further: nothing in the architecture stops a model from routing some computation *off* the shared basis entirely, out of view of a lens that only looks through the final unembedding. That's part of why the field treats the logit lens as a fast first look and never the final word, and reaches for [[Gotchas - Interpreting Model Internals|causal, structural methods]] when the stakes justify the cost.

## Connections
- [[Deep Dive - Mechanistic Interpretability]] — the residual-stream linearity that makes this technique possible at all, and the broader toolkit it's the cheapest member of.
- [[Concept - RMSNorm and LayerNorm]] — the exact final normalization step the lens reuses at every intermediate layer (cross-domain: neural networks).
- [[Concept - Softmax]] — the final step that turns projected logits into a readable probability distribution (cross-domain: neural networks).
- [[Concept - Embeddings as Learned Representations]] — the embedding/unembedding relationship the lens's projection matrix $W_U$ is drawn from (cross-domain: neural networks).
- [[Concept - Activation Patching]] — the causal follow-up method used to confirm what the logit lens only suggests.
- [[Concept - Sampling and Decoding Parameters]] — the surface-level decoding context the lens's uses (early exit, DoLa) ultimately modify (cross-domain: inference & serving).
- [[Concept - Speculative Decoding]] — a production decoding technique the layer-wise stabilization insight directly informs (cross-domain: inference & serving).
- [[Gotchas - Interpreting Model Internals]] — the broader catalog of ways a legible-looking readout from this toolkit can still mislead a practitioner who over-trusts it.

## Sources
- nostalgebraist (2020) — "interpreting GPT: the logit lens" (LessWrong). Introduces the technique.
- Belrose, Furman, Smith, et al. (2023) — "Eliciting Latent Predictions from Transformers with the Tuned Lens." Learns per-layer affine probes correcting the raw lens's basis-mismatch bias.
- Chuang, Xie, Luo, et al. (2023) — "DoLa: Decoding by Contrasting Layers." Uses a logit-lens-style early/late layer contrast to reduce hallucination during generation.
