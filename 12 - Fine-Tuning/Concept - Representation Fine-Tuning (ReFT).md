---
tags: [concept, domain/fine-tuning, level/frontier]
aliases: [ReFT, LoReFT]
summary: "ReFT freezes all weights and edits hidden activations via a learned low-rank intervention, needing far fewer trainable params than LoRA."
---

# Concept - Representation Fine-Tuning (ReFT)

> **One-paragraph hook:** every method in the [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]] taxonomy (additive, selective, reparameterization) still edits *weights*. ReFT (Wu et al. 2024) doesn't. It freezes every weight and learns a small, low-rank intervention on the hidden activations at chosen layers and token positions. LoReFT, the practical variant, reports matching or beating [[Deep Dive - LoRA]] on instruction-following and commonsense-reasoning benchmarks with 10–50x fewer trainable parameters. That's evidence that a lot of what fine-tuning changes lives in a low-rank subspace of the *residual stream*, as opposed to the weight update.

## The mechanism

Pick a hidden state $h \in \mathbb{R}^d$ at a specific layer and token position. That's a point on the residual stream, the object that [[Concept - Attention Mechanism]] and the FFN sublayers read from and write to at every step of [[Deep Dive - The Transformer]]. LoReFT's intervention is:

$$h \leftarrow h + R^\top(Wh + b - Rh)$$

Here $R \in \mathbb{R}^{r \times d}$ is a learned projection with orthonormal rows ($r \ll d$), and $W \in \mathbb{R}^{r \times d}$, $b \in \mathbb{R}^r$ form a learned linear map. Geometrically: $R$ projects $h$ into an $r$-dimensional subspace, $Wh + b$ computes a *target* value for that subspace, and the intervention swaps $h$'s projection onto the subspace for the target while leaving the orthogonal complement of $h$ untouched. It's a trainable version of distributed alignment search (Geiger et al. 2023), an interpretability technique for locating causally relevant subspaces in activations, repurposed for fine-tuning. The constraint goes on the *edit* (a small subspace of the residual stream at specific positions and layers) instead of on the *weight update*.

Each intervention site costs $\sim 2rd + r$ parameters; for $d{=}4096$, $r{=}4$ that's roughly 33k. A single LoRA-adapted linear layer at $r{=}8$ costs $r(d_{\text{in}}+d_{\text{out}}) \approx 65\text{k}$ params, and LoRA applies that to four-plus linear layers per transformer block, times dozens of blocks. LoReFT typically intervenes at only a handful of layers and a small set of token positions. That's where the reported 10–50x parameter reduction comes from.

## In practice

- The reference implementation is Stanford NLP's `pyreft` library, built on `transformers`.
- A typical configuration intervenes at every layer (or a chosen subset) on the last few prompt tokens or a fixed position set, with rank $r$ commonly in the 4–32 range.
- Reported numbers (Wu et al. 2024, on their benchmark suite, *as of 2024*): LoReFT matches or exceeds LoRA on commonsense reasoning and instruction-following with an order of magnitude fewer trainable parameters. Treat that as a paper-specific claim to check with your own [[Playbook - Evaluating a Fine-Tune]], not a universal law.
- Position is a design decision. LoRA doesn't care about sequence position; ReFT's quality depends on *where* in the sequence the intervention fires, and variable-length inputs need an explicit policy (e.g., always target the last prompt token, or every token after a fixed marker).

## Failure modes

- **Not mergeable.** The intervention target $Wh+b$ depends on the runtime hidden state and a specific token position, so $R, W, b$ can't be folded into the frozen weights to give an equivalent plain model. ReFT is a small architectural addition at inference time, not a reparameterization you can merge like LoRA. Per-call overhead is tiny given the parameter count, but it isn't zero, and it doesn't vanish the way a merged LoRA adapter's does.
- **Serving tooling is immature.** There's no counterpart to [[Concept - Multi-LoRA Serving]]'s batched-adapter kernels for swapping many ReFT interventions across concurrent requests (as of 2026). LoRA's "many adapters, one base, hot-swap per request" setup isn't a solved production path here yet.
- **Position mismatch is a silent bug.** Tune an intervention on one prompt template/length, apply it to inputs with a different token count at the "same" absolute position, and it can hit the wrong semantic location. No error, just worse outputs.
- **The extreme parameter efficiency raises the usual low-rank ceiling question.** Expect the qualitative pattern from [[Concept - Why LoRA Underperforms Full Fine-Tuning]], plausibly worse given ReFT's even smaller budget, on tasks that need a large distribution shift from the base model's behavior.

## The non-obvious

ReFT's headline result is an interpretability claim dressed as a fine-tuning method. LoRA implicitly claims "the *weight* change this adaptation needs is low-rank." ReFT claims something stronger: "the *activation* change is low-rank, and you don't need to touch the weights to produce it." LoReFT matching LoRA with 10–50x fewer parameters is evidence for the stronger claim. It ties into the linear-representation line of interpretability work. [[Concept - Superposition]] pictures features as near-linear directions in activation space, which implies steering behavior should be a small-rank edit to that space, and that modifying weights was always an indirect route to the same effect. LoRA asks for the smallest weight patch that produces the right behavior; ReFT asks for the smallest activation patch. The second answer is dramatically smaller, and that tells you something about where adaptable behavior lives in the model.

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
