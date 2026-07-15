---
tags: [concept, domain/architectures, level/surface]
aliases: [encoder-only, decoder-only, encoder-decoder, seq2seq, causal LM, PrefixLM]
summary: "The transformer taxonomy by attention-masking pattern — encoder-only, decoder-only, encoder-decoder — and why decoder-only won the LLM era."
---
# Concept - Encoder-Decoder and Decoder-Only Architectures
> **One-paragraph hook:** "Transformer" is not one architecture — it's a family distinguished almost entirely by one design choice, which positions are allowed to attend to which. That single masking decision determines whether a model can generate text at all, whether it needs one parameter stack or two, and why nearly every LLM you use day to day is built the same way despite the original 2017 paper describing something different.

## The mechanism
[[Concept - Attention Mechanism]] is a general operation — the only thing that changes between architecture families is which positions are visible to which query.

**Encoder-only** (BERT — Devlin et al. 2018): every position attends to every other position, in both directions, with no causal mask. Training uses a masked-language-model objective — randomly mask tokens and predict them from full bidirectional context. The output is a contextualized representation per token, not a generation. An encoder-only model structurally cannot produce text autoregressively, because it was never trained with a causal constraint and has no notion of "predict the next token given only what came before."

**Decoder-only** (the GPT lineage): a causal mask restricts position $i$ to attend only to positions $\le i$. Trained with a single next-token objective, this is the architecture in [[Deep Dive - The Transformer]]. The same causal stack does both "understanding" and "generation" — there's no separate representation-producing phase, because every forward pass through the stack is simultaneously computing a representation of the prefix *and* a prediction of the next token from it.

**Encoder-decoder** (the original Vaswani et al. 2017 transformer; canonicalized for transfer learning by T5, Raffel et al. 2020): a full bidirectional encoder processes the input, and a separate causal decoder generates the output, connected by **cross-attention** — the one architectural piece with no analog in a pure decoder-only model. In cross-attention, queries come from the decoder's current state while keys and values come from the *encoder's* final output:

```
encoder (bidirectional)          decoder (causal, cross-attends to encoder)
  x1 <-> x2 <-> x3 <-> x4                y1 -> y2 -> y3
     |     |     |     |                  ^     ^     ^
     +-----+-----+-----+---- K,V ---------+-----+-----+
                                    (Q from decoder self-attention output)
```

This lets every decoder step condition on the *entire* input sequence's final representation, which is exactly the shape of seq2seq tasks like translation and summarization: a fixed, fully-processed input followed by variable-length generation. It costs roughly double the parameters and forward compute of a decoder-only model at matched depth, since you're maintaining two stacks instead of one.

A middle ground, **PrefixLM** (T5's "LM" variant; UL2, Tay et al. 2022; GLM, Du et al. 2022), runs a single stack but varies the mask by *segment* rather than by architecture: the prompt/prefix is attended to bidirectionally (like an encoder), while tokens after it are generated causally (like a decoder). One set of weights, one stack, but a segment-dependent mask — a hybrid that captures some of encoder-decoder's bidirectional-context benefit without a second parameter stack.

## In practice
Decoder-only won the frontier-LLM era for reasons that are more about serving and scaling engineering than raw quality per parameter. A single next-token objective scales uniformly across arbitrary text with no encoder/decoder split to balance; there's no architectural decision about how to divide capacity between the two stacks; the causal mask is exactly what [[Concept - KV Cache]]-based autoregressive generation wants, since every position's key/value is computed once and never needs to be revisited under bidirectional attention; and the same stack that produces a good next-token distribution also turns out to support strong in-context learning without any architectural change. Wang et al. (2022, "What Language Model Architecture and Pretraining Objective Work Best for Zero-Shot Generalization?") ran controlled comparisons across architecture and objective and found decoder-only with a causal LM objective is the strongest all-around choice for the zero-shot regime that dominates modern LLM usage — though not uniformly dominant on every axis, which matters for the non-obvious point below.

Encoder-only and encoder-decoder haven't disappeared — they persist exactly where the task needs a representation rather than a generation. [[Concept - Embedding Models]] and [[Concept - Rerankers]] are almost universally bidirectional encoders (often BERT-derived or a bidirectionally-adapted decoder), because retrieval and reranking need a whole-sequence representation optimized for similarity comparison, not next-token prediction. T5-style encoder-decoders still show up in dedicated translation and summarization systems where the fixed-input/variable-output shape is a natural fit. [[Concept - Vision Transformers]] borrow the encoder-only pattern directly — a ViT is structurally a BERT-shaped bidirectional encoder applied to image patches instead of tokens.

## Failure modes
- **Treating an encoder-only model as a generator** — it has no causal training signal and no autoregressive sampling path; attempts to "generate" from a masked-LM model either require bolting on a decoder or produce degenerate output.
- **Underestimating encoder-decoder's serving cost** — the cross-attention KV cache is over the *encoder's* output, computed once, but the decoder still needs its own growing KV cache, and running two stacks roughly doubles the parameter and activation memory footprint versus a decoder-only model at matched total depth.
- **PrefixLM mask bugs** — getting the boundary between the bidirectional prefix segment and the causal generation segment wrong (off-by-one, or applying the causal mask to the whole sequence) silently degrades the bidirectional-context benefit the design exists to provide.

## The non-obvious
Decoder-only's dominance is partly an artifact of *operational* convenience, not a settled quality verdict — Wang et al.'s own comparison found encoder-decoder models competitive or ahead on some transfer and multitask setups. The industry converged on decoder-only anyway because a single stack with a single KV-cache shape is dramatically simpler to scale, batch, and serve at the trillion-parameter, million-request-per-day level that matters commercially — the same reason [[Concept - Mixture of Experts Architecture]] designs keep attention dense even as they sparsify the FFN. Architecture "wins" in this field are frequently wins on the compute-and-serving axis as much as the quality axis, and encoder-decoder's persistence in embedding models and rerankers is the tell: wherever the serving-simplicity argument doesn't apply as strongly, bidirectional architectures are still the default, not a legacy holdout.

## Connections
- [[Deep Dive - The Transformer]] — the decoder-only stack this note contrasts against is the canonical architecture that deep dive traces end to end.
- [[Concept - Attention Mechanism]] — masking pattern is a configuration of the same scaled dot-product attention operation across all three families.
- [[Concept - KV Cache]] — the causal mask of decoder-only models is exactly what makes cacheable, never-revisited key/value pairs possible, a core reason decoder-only won on serving grounds.
- [[Concept - Mixture of Experts Architecture]] — MoE designs keep attention dense and sparsify only the FFN, the same "don't touch the mask, change what's inside the sublayer" logic this note applies to architecture families at large.
- [[Concept - Embedding Models]] — the main place bidirectional encoder-only architectures persist in production LLM systems, because retrieval needs whole-sequence representations, not generation.
- [[Concept - Rerankers]] — cross-encoder rerankers are bidirectional encoder-only models applied to query-document pairs, a direct downstream use of this taxonomy.
- [[Concept - Byte-Pair Encoding]] — the tokenizer feeding any of these three architectures is shared infrastructure, independent of the masking choice.
- [[Concept - Vision Transformers]] — borrows the encoder-only bidirectional pattern wholesale, applied to image patches instead of text tokens.
- [[Reference - Model Genealogy]] — situates BERT, T5, and the GPT lineage as the three concrete historical anchors for this taxonomy.
- [[Lore - The Standardization of the Transformer Block]] — the up-link into the folklore of how and why the field converged on the decoder-only default.

## Sources
- Vaswani et al. (2017) — "Attention Is All You Need." Defines the original encoder-decoder architecture with cross-attention.
- Devlin et al. (2018) — "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding." The canonical encoder-only, masked-LM model.
- Raffel et al. (2020) — "Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer" (T5). Canonicalizes encoder-decoder for transfer learning and popularizes PrefixLM-style unified framing.
- Wang et al. (2022) — controlled architecture/objective comparison finding decoder-only causal LM strongest for zero-shot generalization, though not universally.
