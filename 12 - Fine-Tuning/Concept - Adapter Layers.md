---
tags: [concept, domain/fine-tuning, level/advanced]
aliases: [Houlsby adapters, Pfeiffer adapters, bottleneck adapters]
summary: "Bottleneck adapters, IA3, and BitFit: the pre-LoRA PEFT lineage, and why their in-series design lost to LoRA's merge."
---
# Concept - Adapter Layers

> **One-paragraph hook:** Before [[Deep Dive - LoRA]] existed, adapters were how you fine-tuned a frozen pretrained model cheaply: insert a small trainable bottleneck into an otherwise-frozen network rather than reparameterizing the weight update itself. Alongside the soft-prompt lineage ([[Concept - Prompt Tuning and Prefix Tuning]]), bottleneck adapters were the other major pre-LoRA approach — Houlsby-style adapters, Pfeiffer's leaner variant, IA3's rescaling vectors, and BitFit's bias-only training established the entire "freeze the base, train a small delta" playbook that [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]] now takes for granted. It's worth understanding this lineage because the one thing it got structurally wrong — adapters sit *in series* with the frozen layer — is exactly the design choice LoRA reversed to win.

## The mechanism

Houlsby et al. (2019) insert a small bottleneck MLP after a sublayer: down-project the $d$-dimensional hidden state to a much smaller bottleneck dimension $m$ ($m \ll d$), apply a nonlinearity, up-project back to $d$, and add a residual connection around the whole thing. One of these bottleneck blocks is inserted after the [[Concept - Attention Mechanism]] sublayer and a second after the feed-forward sublayer, in every [[Deep Dive - The Transformer]] block — each one sitting immediately before that sublayer's [[Concept - RMSNorm and LayerNorm]]. Trainable parameter count is roughly $2 \times (2 d m)$ per block — about 0.5-8% of the base model's parameters depending on $m$ — and Houlsby et al. report near-full-fine-tuning quality on GLUE with only a few percent of parameters trained.

Pfeiffer et al. simplify this: a single adapter per layer, placed only after the feed-forward sublayer rather than after both attention and FFN. This roughly halves the parameter count relative to Houlsby adapters for comparable quality, and became the default configuration in the AdapterHub library.

## In practice

The decisive architectural fact, relative to LoRA, is that Houlsby/Pfeiffer adapters sit **in series** with the frozen layer's output — the bottleneck block is a real extra function composed onto the forward pass, not a parallel branch that can be algebraically folded back in. LoRA's $W + BA$ is additive and mergeable; an adapter's $x \to f(x) \to \text{down} \to \text{nonlinearity} \to \text{up} \to {+x}$ is not — there's a nonlinearity in the middle, so no single merged weight matrix reproduces it. That means every adapter-based fine-tune pays a permanent extra forward-pass latency cost at serving time, whereas a merged LoRA adapter costs nothing. This one property is most of the reason LoRA displaced adapters as the default for large-scale LLM serving, where per-request latency is a hard product constraint under [[Concept - Continuous Batching]] (adapters remain fine for offline/batch use, or where the extra small matmuls per layer are negligible relative to the rest of the request).

Two related methods worth knowing (full side-by-side in [[Reference - PEFT Method Comparison]]):
- **IA3** (Liu et al. 2022) skips bottlenecks entirely and instead learns three vectors of per-channel elementwise rescaling factors, applied to the attention keys, the attention values, and the FFN intermediate activations. It has fewer trainable parameters than LoRA at comparable rank, and is the basis of the T-Few few-shot fine-tuning recipe.
- **BitFit** (Ben-Zaken et al. 2021) is the most extreme version of "freeze everything, train a little": it trains *only* the bias terms throughout the network, roughly 0.08% of parameters. It's surprisingly competitive on small/mid-size models but its relative quality weakens as model scale increases — there's simply not enough capacity in bias terms alone to steer a much larger, more capable base.

**AdapterFusion** composes multiple task-specific adapters trained independently by learning an attention mechanism over their outputs, letting a model draw on several adapters at inference without the cross-task interference that comes from training one shared adapter on a mixture of tasks.

## Failure modes

- **Latency creep from stacked adapters.** Because adapters don't merge, chaining several (or composing via AdapterFusion) adds up: each is a real forward-pass cost. Detection: profile per-adapter latency, not just aggregate throughput, before deciding this is "cheap."
- **Bottleneck dimension too small.** An undersized $m$ starves the adapter of capacity; symptom looks identical to underfitting from too-low LoRA rank — plateaued task loss regardless of more training steps. Fix: sweep $m$ the same way you'd sweep LoRA rank (see [[Reference - Fine-Tuning Hyperparameters]]).
- **BitFit past its regime.** Training only biases on a large, capable base with a hard task frequently underfits outright; the failure isn't subtle — task loss simply won't move much below a floor. Fix: move to adapters or LoRA once bias-only training stalls.

## The non-obvious

The field's move from adapters to LoRA is usually told as a parameter-efficiency story, but the parameter counts are actually comparable at reasonable settings (adapters at $m$ matching LoRA's $r$ land in similar territory). The real driver was the *mergeability* property — additive-in-parallel versus composed-in-series — which has nothing to do with parameter count and everything to do with the linear-algebra shape of the update. Any PEFT method that inserts a nonlinearity into its trainable path inherits this permanent-latency cost regardless of how few parameters it uses; this is why [[Concept - Representation Fine-Tuning (ReFT)]], despite being 10-50x more parameter-efficient than LoRA, still carries adapter-like serving overhead rather than LoRA's zero-cost merge.

## Connections

- [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]] — adapters are the additive family in the standard three-way PEFT taxonomy.
- [[Deep Dive - LoRA]] — the reparameterization-family method that displaced adapters for LLM-scale serving, precisely because it merges and adapters don't.
- [[Concept - Prompt Tuning and Prefix Tuning]] — the other pre-LoRA PEFT lineage, operating on the input/KV space rather than inserting layers.
- [[Concept - Representation Fine-Tuning (ReFT)]] — a modern method that shares adapters' non-mergeable serving cost despite a very different mechanism.
- [[Reference - PEFT Method Comparison]] — the lookup table placing Houlsby, Pfeiffer, IA3, and BitFit's parameter counts and mergeability side by side.
- [[Reference - Fine-Tuning Hyperparameters]] — bottleneck dimension and other adapter-specific knobs in context with LoRA's.
- [[Concept - RMSNorm and LayerNorm]] — adapters are inserted directly adjacent to a transformer block's normalization layers, and placement relative to them affects training stability.
- [[Concept - Attention Mechanism]] — the attention sublayer is one of the two insertion points for a Houlsby adapter.
- [[Deep Dive - The Transformer]] — the block structure (attention sublayer, FFN sublayer) that determines where an adapter can be inserted.
- [[Concept - Continuous Batching]] — the serving mechanism whose per-request latency budget is what adapters' non-mergeability directly taxes.

## Sources
- Houlsby et al. (2019) — "Parameter-Efficient Transfer Learning for NLP." Introduces the bottleneck adapter architecture.
- Liu et al. (2022) — "Few-Shot Parameter-Efficient Fine-Tuning is Better and Cheaper than In-Context Learning" (IA3 / T-Few). Elementwise rescaling instead of bottlenecks.
- Ben-Zaken et al. (2021) — "BitFit: Simple Parameter-efficient Fine-tuning for Transformer-based Masked Language-models." Bias-only fine-tuning.
