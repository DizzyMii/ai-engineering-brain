---
tags: [concept, domain/architectures, level/advanced]
aliases: []
summary: "The additive skip-connection bus every transformer sublayer reads from and writes to — the right mental model for the whole architecture."
---
# Concept - The Residual Stream
> **One-paragraph hook:** Think of a transformer block less as "attention, then FFN" and more as two small functions taking turns reading from and writing to one shared running-sum vector, which starts at the embedding and ends at the unembedding. Read it as a communication bus instead of a stack of layers and interpretability, architecture edits and depth scaling stop being mysterious.

## The mechanism
Every sublayer in [[Deep Dive - The Transformer]] has the same shape: `x <- x + f(x)`. Unroll that across a full stack of $N$ blocks and the final hidden state is literally a sum:

$$x_N = x_0 + \sum_{\ell=1}^{N} \big(\text{Attn}_\ell(\cdot) + \text{FFN}_\ell(\cdot)\big)$$

Elhage et al. (2021, "A Mathematical Framework for Transformer Circuits") named this the **residual stream** and argued it's the right primitive for reasoning about transformers. $x_0$ (the token embedding) is a starting balance; each attention and FFN sublayer makes a small deposit or withdrawal on a shared account of width $d_{model}$. Sublayers never talk to each other directly. A later layer only "sees" what an earlier one wrote by reading the current value of $x$, which mixes every previous contribution additively. That's the **linear communication channel** view: features are written as directions in the $d_{model}$-dimensional space, and any later layer that has learned to read a direction can retrieve it, however many layers separate the write from the read.

The two sublayer types do different jobs on the same bus. [[Concept - Attention Mechanism]] moves information *between* token positions: position $i$'s stream can pick up a linear combination of position $j$'s stream through the attention weights. The [[Concept - Feed-Forward Networks and GLU Variants]] sublayer works *within* a position, with no cross-token mixing. Both are increments to the same vector: the block alternates "mix across positions" and "process within a position" on one bus.

The residual path is plain addition, with no nonlinearity and no matrix multiply, so gradients flow through it undamped: $\partial x_N / \partial x_0 = I$ plus whatever the sublayer Jacobians contribute. That's the direct reason deep transformers are trainable at all. Compare [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]], which moves the norm relative to this addition and so changes the gradient path.

```
   embedding                                                    unembedding
      |                                                               ^
      v                                                               |
  x0 -+--> [Attn 1] --+--> [FFN 1] --+--> [Attn 2] --+-- ... --> [FFN N] --+--> logits
      |       (read/write the same d_model-wide bus at every step)        |
      +----------------------------------------------------------------->+
                    residual stream (running sum, never reset)
```

[[Deep Dive - The Transformer]] typically ties the input embedding and output unembedding matrices (Press and Wolf 2017), so the stream begins and ends in the *same* linear space. That's what makes the **logit lens** work. Multiply the residual stream at *any* intermediate layer by the unembedding matrix and you get a (rough) token distribution, the model's running best guess before it has finished computing.

## In practice
$d_{model}$ is the width of the bus, and it's fixed and scarce: 4096 for a 7B-class model, 8192 for a 70B-class model, 12288 for GPT-3 175B. Every feature the model represents (syntax, factual associations, in-context task state, refusal signals) has to fit into directions of this one space, shared across every layer and use. That forces **superposition** (see [[Concept - Superposition]]). There are more features than orthogonal directions, so the model packs in more concepts than dimensions by tolerating a little interference between near-orthogonal directions. [[Concept - Induction Heads]] are the canonical circuit built entirely from residual-stream reads and writes: an earlier head writes "previous token was X", a later head reads that to predict "X again", and the residual stream is the only path between them.

Magnitude isn't conserved. It grows with depth, because on net every sublayer adds without subtracting. [[Concept - RMSNorm and LayerNorm]] rescales what each sublayer *sees* when it reads the stream, but the stream value itself keeps growing. That growth drives late-layer massive activations and the [[Concept - Attention Sinks]] phenomenon, where a disproportionate share of attention mass and residual-stream norm piles onto the first token as a place to "park" unused capacity.

## Failure modes
- **Naive architecture edits break the bus for everything downstream.** Inserting a module, changing $d_{model}$ or adding an adapter mid-stack perturbs a resource that every later layer already learned to read in a specific state. Edits are rarely as local as they look, and LoRA/adapter interference and catastrophic forgetting are partly a residual-stream story.
- **Unbounded magnitude growth under pre-norm** concentrates in a few outlier dimensions and the first-token position (attention sinks). It wrecks quantization ranges and misleads naive activation-magnitude interpretability probes that assume roughly uniform scale.
- **Superposition interference.** Two features sharing near-parallel directions can leak into each other's readout, producing spurious correlations that look like a real circuit until you probe with activation patching (see [[Concept - Superposition]]).

## The non-obvious
The residual stream is a **scarce shared communication resource**, and treating it as a free-form scratchpad is the most important mental-model mistake to fix before doing architecture or interpretability work. Why does fine-tuning one capability sometimes degrade an unrelated one? They likely share directions in the same $d_{model}$-wide bus. Why does adding depth give diminishing returns? Later layers read an increasingly crowded, increasingly large-magnitude stream, and their own additive contribution is a shrinking fraction of the total. Why do logit lens and activation patching work at all? The stream is linear and additive, so each layer's contribution can be isolated and read out on its own. If sublayers were composed multiplicatively, that wouldn't hold.

## Connections
- [[Deep Dive - The Transformer]] — the residual stream is the connective tissue that turns a list of sublayers into a single coherent architecture; this note is the mental model, the deep dive is the full data path.
- [[Concept - Attention Mechanism]] — the sublayer that moves information *between* positions on the shared bus; one of the two increment types every block writes.
- [[Concept - Feed-Forward Networks and GLU Variants]] — the sublayer that processes *within* a position on the shared bus, and the sublayer Geva et al.'s key-value-memory reading treats as writing directly into this stream.
- [[Concept - RMSNorm and LayerNorm]] — the operation every sublayer applies when *reading* the stream, rescaling a growing-magnitude vector without resetting the underlying running sum.
- [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]] — placement decides whether the stream stays a clean gradient highway or accumulates unbounded magnitude with depth.
- [[Concept - Superposition]] — the direct consequence of a fixed-width shared bus holding more features than it has dimensions.
- [[Concept - Induction Heads]] — a concrete circuit built entirely from residual-stream writes by one layer and reads by another.
- [[Concept - Attention Sinks]] — the first-token magnitude-parking behavior is a residual-stream-growth phenomenon, not an attention-only one.
- [[Concept - Attention Logit Stabilization (QK-Norm and Soft-Capping)]] — a frontier response to residual-stream and attention-logit magnitude growth at scale; the up-link into unicorn-tier mitigation tribal knowledge.
- [[Concept - Convolutional Neural Networks]] — ResNet's skip connections are the direct architectural ancestor of the residual stream, minus the "shared linear channel" interpretability framing that only became explicit with transformers.
- [[Concept - Backpropagation]] — the identity Jacobian of the residual path is precisely why gradients reach early layers undamped; the down-link prerequisite for this note.

## Sources
- Elhage et al. (2021) — "A Mathematical Framework for Transformer Circuits" (Anthropic). Coins the residual-stream framing and the linear-communication-channel view used throughout interpretability work.
- He et al. (2015) — "Deep Residual Learning for Image Recognition." Introduces the skip connection the residual stream generalizes.
- Press and Wolf (2017) — "Using the Output Embedding to Improve Language Models." The weight-tying result that makes the logit lens meaningful.
