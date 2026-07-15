---
tags: [concept, domain/architectures, level/advanced]
aliases: []
summary: "The additive skip-connection bus every transformer sublayer reads from and writes to — the right mental model for the whole architecture."
---
# Concept - The Residual Stream
> **One-paragraph hook:** A transformer block is not "attention, then FFN" so much as two small functions taking turns reading from and writing to a single shared, running-sum vector that starts at the embedding and ends at the unembedding. Thinking of the architecture as a communication bus rather than a stack of layers is what makes interpretability, architecture edits, and depth-scaling behavior legible instead of mysterious.

## The mechanism
Every sublayer in [[Deep Dive - The Transformer]] has the same shape: `x <- x + f(x)`. Unroll that across a full stack of $N$ blocks and the hidden state at the end is literally a sum:

$$x_N = x_0 + \sum_{\ell=1}^{N} \big(\text{Attn}_\ell(\cdot) + \text{FFN}_\ell(\cdot)\big)$$

Elhage et al. (2021, "A Mathematical Framework for Transformer Circuits") named this the **residual stream** and argued it's the correct primitive for reasoning about transformers: $x_0$ (the token embedding) is a starting balance, and every attention and FFN sublayer is a small deposit or withdrawal on a shared account of width $d_{model}$. Crucially, sublayers don't talk to each other directly — a later layer can only "see" what an earlier layer wrote by reading the current value of $x$, which mixes every previous contribution additively. This is the **linear communication channel** view: features are written as directions in the $d_{model}$-dimensional space, and any later layer that has learned to read that direction can retrieve it, no matter how many layers separate the write from the read.

The two sublayer types play distinct roles on the same bus. [[Concept - Attention Mechanism]] moves information *between* token positions — position $i$'s stream can pick up a linear combination of position $j$'s stream via the attention weights. The [[Concept - Feed-Forward Networks and GLU Variants]] sublayer processes *within* a position only, with no cross-token mixing. Both are just increments to the same vector; the architecture alternates "mix across positions" and "process within a position," writing the results back onto the identical bus each time.

Because the residual path is literally addition — no nonlinearity, no matrix multiply — gradients flow through it undamped: $\partial x_N / \partial x_0 = I$ plus whatever the sublayer Jacobians contribute. This is the direct mechanism behind why deep transformers are trainable at all (contrast with how [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]] changes where a norm sits relative to this addition and thereby changes the gradient path).

```
   embedding                                                    unembedding
      |                                                               ^
      v                                                               |
  x0 -+--> [Attn 1] --+--> [FFN 1] --+--> [Attn 2] --+-- ... --> [FFN N] --+--> logits
      |       (read/write the same d_model-wide bus at every step)        |
      +----------------------------------------------------------------->+
                    residual stream (running sum, never reset)
```

Because [[Deep Dive - The Transformer]] typically ties the input embedding and output unembedding matrices (Press and Wolf 2017), the stream begins and ends in the *same* linear space — which is what makes the **logit lens** work: multiplying the residual stream's value at *any* intermediate layer by the unembedding matrix produces a (rough) token distribution, exposing the model's running best guess before it has finished computing.

## In practice
$d_{model}$ is the width of this bus, and it's a fixed, scarce resource: 4096 for a 7B-class model, 8192 for a 70B-class model, 12288 for GPT-3 175B. Every feature the model represents — syntax, factual associations, in-context task state, refusal signals — has to fit into directions of this same space, shared across every layer and every use of the model. That forces **superposition** (see [[Concept - Superposition]]): more features exist than there are orthogonal directions, so the model represents more concepts than dimensions by tolerating small amounts of interference between near-orthogonal directions. [[Concept - Induction Heads]] are a canonical example of a circuit built entirely from residual-stream reads and writes: an earlier head writes "previous token was X," a later head reads that write to predict "X again," with the residual stream as the sole communication path between them.

Magnitude is not conserved — it grows with depth, since every sublayer adds without subtracting on net. [[Concept - RMSNorm and LayerNorm]] reads of the stream rescale what each sublayer *sees*, but the underlying stream value itself keeps growing, which is exactly the mechanism behind late-layer massive activations and the [[Concept - Attention Sinks]] phenomenon, where a disproportionate amount of attention mass and residual-stream norm concentrates on the first token as a place to "park" unused capacity.

## Failure modes
- **Naive architecture edits break the bus for everyone downstream.** Inserting a new module, changing $d_{model}$, or adding an adapter mid-stack perturbs a resource every later layer already learned to read from a specific state; edits are rarely as local as they look, which is why LoRA/adapter interference and catastrophic forgetting are partly a residual-stream story.
- **Unbounded magnitude growth under pre-norm** concentrates in a few outlier dimensions and the first-token position (attention sinks), degrading quantization ranges and confusing naive activation-magnitude-based interpretability probes that assume roughly uniform scale.
- **Interference from superposition** means two features sharing near-parallel directions can leak into each other's readout, producing spurious correlations that look like a real circuit until you probe with activation patching (see [[Concept - Superposition]]).

## The non-obvious
The residual stream is a **scarce shared communication resource, not a free-form scratchpad** — this is the single most load-bearing mental-model correction for anyone doing architecture work or interpretability. It reframes questions that otherwise look mysterious: why does fine-tuning one capability sometimes degrade an unrelated one? Because they likely share directions in the same $d_{model}$-wide bus. Why does adding depth have diminishing returns? Because later layers are reading an increasingly crowded, increasingly large-magnitude stream where their own additive contribution is a shrinking fraction of the total. Why can you do "logit lens" and activation-patching interpretability at all? Because the stream is linear and additive, so contributions from any layer can be isolated and read out independently — a property that would not hold if sublayers were composed multiplicatively instead of additively.

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
