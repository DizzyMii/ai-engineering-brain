---
tags: [concept, domain/fine-tuning, level/advanced]
aliases: [Houlsby adapters, Pfeiffer adapters, bottleneck adapters]
summary: "Bottleneck adapters, IA3, and BitFit: the pre-LoRA PEFT lineage, and why their in-series design lost to LoRA's merge."
---
# Concept - Adapter Layers

> **One-paragraph hook:** before [[Deep Dive - LoRA]], adapters were how you fine-tuned a frozen pretrained model cheaply. You inserted a small trainable bottleneck into the frozen network instead of reparameterizing the weight update. Next to the soft-prompt lineage ([[Concept - Prompt Tuning and Prefix Tuning]]), bottleneck adapters were the other big pre-LoRA approach. Houlsby-style adapters, Pfeiffer's leaner variant, IA3's rescaling vectors and BitFit's bias-only training set up the whole "freeze the base, train a small delta" playbook that [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]] now takes for granted. The lineage is worth knowing because of the one design choice it got wrong: adapters sit *in series* with the frozen layer, and LoRA won by reversing that.

## The mechanism

Houlsby et al. (2019) insert a small bottleneck MLP after a sublayer. It down-projects the $d$-dimensional hidden state to a much smaller bottleneck dimension $m$ ($m \ll d$), applies a nonlinearity, up-projects back to $d$, and wraps the whole thing in a residual connection. Every [[Deep Dive - The Transformer]] block gets two of these: one after the [[Concept - Attention Mechanism]] sublayer and one after the feed-forward sublayer, each right before that sublayer's [[Concept - RMSNorm and LayerNorm]]. That's roughly $2 \times (2 d m)$ trainable parameters per block, about 0.5-8% of the base model depending on $m$. Houlsby et al. report near-full-fine-tuning quality on GLUE with only a few percent of parameters trained.

Pfeiffer et al. simplify it to a single adapter per layer, after the feed-forward sublayer only. That roughly halves the parameter count relative to Houlsby adapters at comparable quality, and it became the default configuration in the AdapterHub library.

## In practice

The difference from LoRA that matters: Houlsby/Pfeiffer adapters sit **in series** with the frozen layer's output. The bottleneck block is an extra function composed onto the forward pass, and it can't be folded back into the weights. LoRA's $W + BA$ is additive and mergeable. An adapter's $x \to f(x) \to \text{down} \to \text{nonlinearity} \to \text{up} \to {+x}$ has a nonlinearity in the middle, so no single merged weight matrix reproduces it. Every adapter-based fine-tune therefore pays a permanent extra forward-pass latency cost at serving time, while a merged LoRA adapter costs nothing. That one property is most of why LoRA replaced adapters as the default for large-scale LLM serving, where per-request latency is a hard product constraint under [[Concept - Continuous Batching]]. Adapters are still fine for offline/batch use, or when the extra small matmuls per layer are negligible next to the rest of the request.

Two related methods (full side-by-side in [[Reference - PEFT Method Comparison]]):
- **IA3** (Liu et al. 2022) drops the bottleneck and learns three vectors of per-channel elementwise rescaling factors, applied to the attention keys, the attention values and the FFN intermediate activations. It has fewer trainable parameters than LoRA at comparable rank, and it's the basis of the T-Few few-shot fine-tuning recipe.
- **BitFit** (Ben-Zaken et al. 2021) takes "freeze everything, train a little" to the limit: it trains *only* the bias terms, roughly 0.08% of parameters. It's surprisingly competitive on small/mid-size models, but its relative quality weakens as models grow. Bias terms alone don't have the capacity to steer a much larger, more capable base.

**AdapterFusion** composes several independently trained task-specific adapters by learning attention over their outputs. The model can draw on several adapters at inference without the cross-task interference you get from training one shared adapter on a task mixture.

## Failure modes

- **Latency creep from stacked adapters.** Adapters don't merge, so chaining several (or composing them via AdapterFusion) adds up; each one is a real forward-pass cost. Detection: profile per-adapter latency, not only aggregate throughput, before calling it "cheap."
- **Bottleneck dimension too small.** An undersized $m$ starves the adapter of capacity. It looks the same as underfitting from too-low LoRA rank: task loss plateaus no matter how many more steps you run. Fix: sweep $m$ the way you'd sweep LoRA rank (see [[Reference - Fine-Tuning Hyperparameters]]).
- **BitFit past its regime.** Bias-only training on a large, capable base with a hard task frequently underfits outright. It isn't subtle: task loss won't go much below a floor. Fix: move to adapters or LoRA once bias-only training stalls.

## The non-obvious

The move from adapters to LoRA is usually told as a parameter-efficiency story, but at reasonable settings the parameter counts are comparable (adapters with $m$ matching LoRA's $r$ land in similar territory). What drove it was *mergeability*: additive-in-parallel versus composed-in-series. That's about the linear-algebra shape of the update, not parameter count. Any PEFT method with a nonlinearity in its trainable path inherits the permanent latency cost however few parameters it uses. [[Concept - Representation Fine-Tuning (ReFT)]], for example, is 10-50x more parameter-efficient than LoRA and still carries adapter-like serving overhead instead of LoRA's zero-cost merge.

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
