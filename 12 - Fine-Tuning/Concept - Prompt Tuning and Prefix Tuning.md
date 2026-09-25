---
tags: [concept, domain/fine-tuning, level/advanced]
aliases: [soft prompt tuning, P-tuning, continuous prompts]
summary: "Learnable soft-prompt and prefix vectors that steer a frozen model via attention instead of touching any weight."
---
# Concept - Prompt Tuning and Prefix Tuning

> **One-paragraph hook:** prompt tuning and prefix tuning are the third branch of the pre-LoRA [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]] family. [[Concept - Adapter Layers]] add weight matrices and [[Deep Dive - LoRA]] reparameterizes the weight update; these add nothing to the weights. They learn a handful of continuous "soft" vectors, prepend them to the input or to every layer's attention keys and values, and let the frozen model's own [[Concept - Attention Mechanism]] do the steering. As a first-choice fine-tuning method it matters less today. It's still the conceptual ancestor of prompt caching and the clearest demonstration that steering a model doesn't require touching a single weight.

## The mechanism

**Prompt tuning** (Lester et al. 2021) prepends $k$ learnable embedding vectors to the input embedding sequence and trains only those. Nothing else in the model changes. The parameter count is $k \times d$: for $k=20$ soft tokens and $d=4096$ (a typical hidden size) that's about 80,000 trainable parameters, several orders of magnitude below even a modest LoRA adapter. The catch is that it only matches full fine-tuning quality at large scale (empirically, above roughly 10B parameters). On smaller models it's measurably weaker; $k$ vectors in input-embedding space don't give enough steering leverage.

**Prefix tuning** (Li & Liang 2021) goes further. It prepends learnable vectors to the **key and value** tensors at *every* attention layer, not just the input (the shape and count of those tensors depend on the [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] a model uses). The soft prefix then acts on every layer's attention pattern directly instead of propagating its effect forward from the input, at the cost of more parameters. During training the raw prefix parameters go through a small MLP reparameterization for optimization stability. The original authors kept that detail even though the MLP is discarded after training and only the resulting K/V vectors are used at inference.

**P-tuning v2** (Liu et al. 2021) generalizes prefix tuning with a deep prefix learned at *every* layer. The authors show it matches full fine-tuning consistently across model scales and NLU task types, which removes plain prompt tuning's small-model weakness.

The intuition behind all of them: soft prompts change what the model *attends to*, not what it *can* compute. They live in the same continuous embedding space as real tokens but are optimized freely, tied to no vocabulary entry. That's why they aren't human-readable, and why looking at a trained soft prompt's nearest-neighbor tokens rarely tells you anything.

## In practice

The costs are specific. Prefix tokens are prepended to every sequence, so they permanently take [[Concept - KV Cache]] and context-window budget on every request, where a merged LoRA adapter is free. Training is also fussier than LoRA: soft prompts are sensitive to initialization and learning rate. The standard mitigation, initializing the soft prompt from the embeddings of real, semantically relevant tokens instead of random noise, measurably improves convergence.

For generative LLM fine-tuning, LoRA has largely replaced this whole family: it trains faster, cares less about init, and merges to zero serving cost (full comparison in [[Reference - PEFT Method Comparison]]). Prompt/prefix tuning is still relevant in two places. One is multi-task serving, where swapping a small learned prefix per request is cheaper than swapping full adapter weights when one deployment serves many task variants. The other is conceptual: it's the direct ancestor of [[Concept - Prompt Caching]], since both treat a chunk of KV state as a reusable, front-loaded unit that isn't recomputed per request. Don't confuse it with [[Concept - In-Context Learning]], which gets a superficially similar steering effect from discrete example tokens the model was never trained on, not from a continuous vector trained for the task.

## Failure modes

- **Instability and underfitting below ~1B parameters.** Small models don't have the representational slack for a few soft vectors to steer behavior reliably. The symptom is training loss stuck at a mediocre floor however long you train. Fix: move to prefix tuning (more capacity via K/V injection at every layer) or to LoRA.
- **Bad initialization stalls convergence.** Randomly initialized soft prompts frequently converge slowly or to a poor local optimum. Initializing from real token embeddings (e.g., words related to the task) is the standard, well-tested fix.
- **Context budget creep at scale.** Prefix/prompt tokens occupy real sequence positions, so a fleet of tasks each with its own multi-token prefix eats into the usable context window. Budget for it up front so it doesn't surprise you at deploy time.

## The non-obvious

Prefix tuning needs an MLP reparameterization during training and prompt tuning doesn't. That tells you *where* each method's difficulty lives. Prompt tuning only pushes gradients through one embedding lookup, a shallow, well-conditioned problem. Prefix tuning is effectively learning a value that, through many layers of attention and nonlinearity, has to produce a good K/V injection at every layer at once. That's a much harder, more indirect target. The MLP is there only to make that optimization tractable for gradient descent; the model doesn't need its extra capacity at inference, and it's thrown away after training. Newer methods like [[Concept - Representation Fine-Tuning (ReFT)]] push the "steer via hidden state, not weights" idea much further, intervening on hidden states at arbitrary layers and positions instead of only the K/V slots at the front of attention.

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
