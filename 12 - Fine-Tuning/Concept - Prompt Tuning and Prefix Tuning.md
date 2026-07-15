---
tags: [concept, domain/fine-tuning, level/advanced]
aliases: [soft prompt tuning, P-tuning, continuous prompts]
summary: "Learnable soft-prompt and prefix vectors that steer a frozen model via attention instead of touching any weight."
---
# Concept - Prompt Tuning and Prefix Tuning

> **One-paragraph hook:** Prompt tuning and prefix tuning are the third branch of the pre-LoRA [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]] family: instead of adding new weight matrices ([[Concept - Adapter Layers]]) or reparameterizing a weight update ([[Deep Dive - LoRA]]), they add nothing to the weights at all — they learn a handful of continuous "soft" vectors that get prepended to the input or to every layer's attention keys and values, and let the frozen model's own [[Concept - Attention Mechanism]] do the steering. The technique matters less as a first-choice fine-tuning method today, but it's the conceptual ancestor of prompt caching and the clearest illustration that steering a model doesn't require touching a single weight.

## The mechanism

**Prompt tuning** (Lester et al. 2021) prepends $k$ learnable embedding vectors directly to the input embedding sequence and trains only those vectors — nothing else in the model changes. Parameter count is just $k \times d$: for $k=20$ soft tokens and $d=4096$ (a typical hidden size), that's about 80,000 trainable parameters, several orders of magnitude below even a modest LoRA adapter. The catch is that prompt tuning only matches full fine-tuning quality at large model scale (empirically, above roughly 10B parameters); on smaller models it's measurably weaker, because there simply isn't enough steering leverage in $k$ input-embedding-space vectors alone.

**Prefix tuning** (Li & Liang 2021) is more aggressive: instead of only touching the input embeddings, it prepends learnable vectors to the **key and value** tensors — the shape and count of which depend on the [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] a model uses — at *every* attention layer, not just the input. This gives the soft prefix direct influence over every layer's attention pattern rather than having to propagate its effect forward from the input alone, at the cost of more parameters. During training, the raw prefix parameters are reparameterized through a small MLP (rather than optimized directly) purely for optimization stability — a detail that mattered enough to the original authors that they kept it even though the MLP is discarded after training and only the resulting K/V vectors are kept at inference time.

**P-tuning v2** (Liu et al. 2021) generalizes prefix tuning further: a deep prefix is learned at *every* layer, and the authors show this configuration matches full fine-tuning quality consistently across model scales and NLU task types, closing the small-model weakness that plain prompt tuning has.

The unifying mechanism intuition: soft prompts don't change what the model *can* compute, only what it *attends to*. They live in the same continuous embedding space as real tokens but are optimized freely rather than tied to any vocabulary entry — which is exactly why they aren't human-readable text, and why staring at a trained soft prompt's nearest-neighbor tokens rarely produces anything interpretable.

## In practice

Costs are real and specific: prefix tokens are prepended to every sequence, so they permanently consume [[Concept - KV Cache]] and context-window budget on every request — unlike a merged LoRA adapter, which is free. Training is also more finicky than LoRA: soft prompts are sensitive to both initialization and learning rate, and the standard mitigation — initializing the soft prompt embeddings from the embeddings of real, semantically relevant tokens rather than from random noise — measurably improves convergence.

For generative LLM fine-tuning, this entire family has been largely superseded by LoRA, which trains faster, is less sensitive to init, and merges to zero serving cost (full comparison in [[Reference - PEFT Method Comparison]]). Prompt/prefix tuning remains relevant in two places: multi-task serving, where swapping a small learned prefix per request is cheaper than swapping full adapter weights when the base model must serve many task variants from one deployment; and conceptually, as the direct ancestor of [[Concept - Prompt Caching]] — both techniques are, at bottom, about treating a chunk of KV state as a reusable, front-loaded unit rather than something recomputed per request. It's worth distinguishing this from [[Concept - In-Context Learning]], which achieves a superficially similar steering effect via discrete example tokens the model was never trained on, rather than a trained continuous vector optimized specifically for the task.

## Failure modes

- **Instability and underfitting below ~1B parameters.** Small models simply don't have enough representational slack for a handful of soft vectors to steer behavior reliably; symptom is a training loss that won't drop below a mediocre floor no matter how long you train. Fix: move to prefix tuning (more capacity via K/V injection at every layer) or to LoRA.
- **Bad initialization stalls convergence.** Randomly initialized soft prompts frequently converge slowly or to a poor local optimum; initializing from real token embeddings (e.g., embeddings of words related to the task) is the standard, well-tested fix.
- **Context budget creep at scale.** Because prefix/prompt tokens occupy real sequence positions, a fleet of tasks each wanting their own multi-token prefix adds up against a model's usable context window — worth budgeting explicitly rather than discovering at deploy time.

## The non-obvious

The reason prefix tuning needs an MLP reparameterization during training but prompt tuning doesn't is a tell about *where* each method's difficulty lives: prompt tuning only has to move gradients through one embedding lookup, a shallow, well-conditioned optimization problem. Prefix tuning is effectively trying to learn a value that, through many layers of attention and nonlinearity, produces a good K/V injection at every layer simultaneously — a much harder, more indirect optimization target, and the MLP reparameterization exists purely to make that landscape tractable to gradient descent, not because the model needs the MLP's extra capacity at inference time (it's thrown away after training). This "steer via hidden state, not weights" idea is generalized much further by newer methods like [[Concept - Representation Fine-Tuning (ReFT)]], which intervenes directly on hidden states at arbitrary layers and positions rather than being confined to the K/V slots at the very front of attention.

## Connections

- [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]] — the additive-family umbrella soft prompts belong to, alongside adapters.
- [[Concept - Adapter Layers]] — the other pre-LoRA PEFT lineage, inserting bottleneck layers rather than steering via input/KV vectors.
- [[Deep Dive - LoRA]] — the reparameterization method that superseded prompt/prefix tuning for most generative fine-tuning.
- [[Reference - PEFT Method Comparison]] — places prompt/prefix tuning's parameter count and mergeability alongside every other PEFT method.
- [[Concept - KV Cache]] — the resource prefix tokens permanently occupy at serving time.
- [[Concept - Attention Mechanism]] — the mechanism soft prompts actually operate through; they inject into keys/values or the input to attention.
- [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — which K/V tensors exist to inject a prefix into depends on the attention variant a model uses.
- [[Concept - Prompt Caching]] — the serving-side technique that soft/prefix tuning is the direct conceptual ancestor of.
- [[Concept - In-Context Learning]] — soft prompts are a trained analog of the discrete few-shot examples in-context learning relies on.
- [[Concept - Representation Fine-Tuning (ReFT)]] — a more modern method that generalizes the idea of steering via hidden-state edits rather than weights, sharing prefix tuning's non-mergeable serving cost.

## Sources
- Lester et al. (2021) — "The Power of Scale for Parameter-Efficient Prompt Tuning." Introduces prompt tuning.
- Li & Liang (2021) — "Prefix-Tuning: Optimizing Continuous Prompts for Generation." Introduces prefix tuning.
- Liu et al. (2021) — "P-Tuning v2: Prompt Tuning Can Be Comparable to Fine-tuning Universally Across Scales and Tasks."
