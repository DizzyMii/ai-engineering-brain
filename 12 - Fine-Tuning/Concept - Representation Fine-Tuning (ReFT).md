---
tags: [concept, domain/fine-tuning, level/frontier]
aliases: [ReFT, LoReFT]
summary: "ReFT freezes all weights and edits hidden activations via a learned low-rank intervention, needing far fewer trainable params than LoRA."
---

# Concept - Representation Fine-Tuning (ReFT)

> **One-paragraph hook:** Every method in [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]]'s taxonomy — additive, selective, reparameterization — still edits *weights*. ReFT (Wu et al. 2024) doesn't: it freezes every weight in the model and instead learns a small, low-rank intervention on the hidden activations at chosen layers and token positions. LoReFT, the practical variant, reports matching or beating [[Deep Dive - LoRA]] on instruction-following and commonsense-reasoning benchmarks with 10–50x fewer trainable parameters — evidence that a lot of what fine-tuning changes lives in a low-rank subspace of the *residual stream*, not of the weight update.

## The mechanism

Pick a hidden state $h \in \mathbb{R}^d$ at a specific layer and token position — a point on the residual stream, the same object [[Concept - Attention Mechanism]] and the FFN sublayers read from and write to at every step of [[Deep Dive - The Transformer]]. LoReFT's intervention is:

$$h \leftarrow h + R^\top(Wh + b - Rh)$$

where $R \in \mathbb{R}^{r \times d}$ is a learned projection with orthonormal rows ($r \ll d$), and $W \in \mathbb{R}^{r \times d}$, $b \in \mathbb{R}^r$ are a learned linear map. Read it geometrically: $R$ projects $h$ down into an $r$-dimensional subspace, $Wh + b$ computes a *target* value for that subspace, and the intervention replaces $h$'s projection onto that subspace with the target while leaving the orthogonal complement of $h$ completely untouched. This is a direct trainable version of distributed alignment search (Geiger et al. 2023) — an interpretability technique for locating causally-relevant subspaces in activations — repurposed as a fine-tuning mechanism: constrain the *edit* to a small subspace of the residual stream at specific positions and layers, rather than constraining the *weight update*.

Parameter count per intervention site is $\sim 2rd + r$ — for $d{=}4096$, $r{=}4$, that's roughly 33k parameters. Compare a single LoRA-adapted linear layer at $r{=}8$: $r(d_{\text{in}}+d_{\text{out}}) \approx 65\text{k}$ params, applied across four-plus linear layers per transformer block, times dozens of blocks. LoReFT typically intervenes at only a handful of layers and a small set of token positions, which is where the reported 10–50x parameter reduction comes from.

## In practice

- The reference implementation is Stanford NLP's `pyreft` library, built on top of `transformers`.
- Typical configuration intervenes at every layer (or a chosen subset) on the last few prompt tokens or a fixed position set; rank $r$ commonly in the 4–32 range.
- Reported numbers (Wu et al. 2024, on their benchmark suite, *as of 2024*): LoReFT matches or exceeds LoRA on commonsense reasoning and instruction-following with an order of magnitude fewer trainable parameters — treat this as a paper-specific claim to verify against your own [[Playbook - Evaluating a Fine-Tune]], not a universal law.
- Position-specificity is a real design decision, not an implementation detail: unlike LoRA, which is agnostic to sequence position, ReFT's quality depends on *where* along the sequence the intervention fires, and variable-length inputs need an explicit policy (e.g., always target the last prompt token, or every token after a fixed marker).

## Failure modes

- **Not mergeable.** Because the intervention target $Wh+b$ depends on the runtime hidden state and a specific token position, there's no way to fold $R, W, b$ back into the frozen weights and get an equivalent plain model — ReFT is a genuine small architectural addition at inference time, not a reparameterization like LoRA's merge. The overhead per call is tiny given the parameter count, but it is not zero, and it doesn't disappear the way a merged LoRA adapter's does.
- **Serving tooling is immature.** There's no first-class analog to [[Concept - Multi-LoRA Serving]]'s batched-adapter kernels for swapping many ReFT interventions across concurrent requests (as of 2026) — the LoRA ecosystem's "many adapters, one base, hot-swap per request" story isn't yet a solved production path here.
- **Position mismatch is a silent bug.** An intervention tuned on one prompt template/length and then applied to inputs with a different token count at the "same" absolute position can target the wrong semantic location without throwing any error — just quietly worse outputs.
- **The extreme parameter efficiency raises the same ceiling question as any low-rank method** — expect the same qualitative pattern discussed in [[Concept - Why LoRA Underperforms Full Fine-Tuning]], plausibly worse given ReFT's even smaller parameter budget, on tasks requiring a large distribution shift from the base model's behavior.

## The non-obvious

ReFT's headline result is really an interpretability claim wearing a fine-tuning method's clothes. LoRA's implicit claim is "the necessary *weight* change for this adaptation is low-rank." ReFT's claim is stronger and different: "the necessary *activation* change is low-rank, and you don't need to touch the weights at all to produce it." That LoReFT can match LoRA with 10–50x fewer parameters is evidence for the stronger claim, and it connects directly to the linear-representation line of interpretability work — [[Concept - Superposition]]'s picture of features as near-linear directions in activation space implies that steering behavior should naturally be a small-rank edit to that space, and that modifying weights was always a more indirect way of achieving the same effect. Put differently: LoRA asks "what's the smallest weight patch that produces the right behavior," while ReFT asks "what's the smallest activation patch," and the fact that the second question has a dramatically smaller answer is itself informative about where adaptable behavior actually lives in the model.

## Connections
- [[Deep Dive - LoRA]] — the contrasting baseline: LoRA edits weights, ReFT edits activations; the vanilla low-rank claim is the reference point for ReFT's stronger one.
- [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]] — ReFT sits outside PEFT's additive/selective/reparameterization taxonomy, making it a genuine fourth family worth naming explicitly.
- [[Reference - PEFT Method Comparison]] — where ReFT's parameter count and non-mergeability sit against every other method in the lookup table.
- [[Concept - Sparse Autoencoders]] — a different technique for isolating structure in the same residual-stream activations ReFT intervenes on.
- [[Concept - Superposition]] — the representational hypothesis (features as near-linear directions) that explains why a low-rank activation edit can be this effective.
- [[Concept - Induction Heads]] — an example of the kind of interpretable, position-specific circuit that activation-space interventions like ReFT can target directly.
- [[Concept - Attention Mechanism]] — the residual stream ReFT intervenes on is exactly the object attention and FFN sublayers read from and write to.
- [[Deep Dive - The Transformer]] — full architectural context for where in the forward pass the intervention hooks in.

## Sources
- Wu et al. (2024) — "ReFT: Representation Finetuning for Language Models." Introduces LoReFT and the low-rank activation-intervention mechanism.
- Geiger et al. (2023) — work on distributed alignment search that formalizes locating causal subspaces in activations, the interpretability lineage ReFT's intervention formalism builds on.
