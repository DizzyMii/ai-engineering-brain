---
tags: [concept, domain/architectures, level/surface]
aliases: [encoder-only, decoder-only, encoder-decoder, seq2seq, causal LM, PrefixLM]
summary: "The transformer taxonomy by attention-masking pattern — encoder-only, decoder-only, encoder-decoder — and why decoder-only won the LLM era."
---
# Concept - Encoder-Decoder and Decoder-Only Architectures
> **One-paragraph hook:** "Transformer" names a family, and the members differ almost entirely in one design choice: which positions may attend to which. That masking decision determines whether a model can generate text at all and whether it needs one parameter stack or two. It also explains why nearly every LLM you use day to day is built the same way, even though the original 2017 paper described something different.

## The mechanism
[[Concept - Attention Mechanism]] is a general operation. Between architecture families, the only thing that changes is which positions each query can see.

**Encoder-only** (BERT, Devlin et al. 2018). Every position attends to every other position in both directions, with no causal mask. Training uses a masked-language-model objective: mask random tokens and predict them from full bidirectional context. The output is a contextualized representation per token, and there's no generation step. An encoder-only model can't produce text autoregressively. It was never trained under a causal constraint and has no notion of "predict the next token given only what came before."

**Decoder-only** (the GPT lineage). A causal mask restricts position $i$ to positions $\le i$. It's trained on a single next-token objective, and it's the architecture in [[Deep Dive - The Transformer]]. One causal stack handles both "understanding" and "generation." There's no separate representation phase, since every forward pass computes a representation of the prefix *and* a next-token prediction from it at the same time.

**Encoder-decoder** (the original Vaswani et al. 2017 transformer; canonicalized for transfer learning by T5, Raffel et al. 2020). A full bidirectional encoder processes the input and a separate causal decoder generates the output. They're joined by **cross-attention**, the one piece with no analog in a pure decoder-only model. In cross-attention, queries come from the decoder's current state and keys and values come from the *encoder's* final output:

```
encoder (bidirectional)          decoder (causal, cross-attends to encoder)
  x1 <-> x2 <-> x3 <-> x4                y1 -> y2 -> y3
     |     |     |     |                  ^     ^     ^
     +-----+-----+-----+---- K,V ---------+-----+-----+
                                    (Q from decoder self-attention output)
```

So every decoder step conditions on the final representation of the *entire* input. That matches seq2seq tasks like translation and summarization: a fixed, fully processed input, then variable-length generation. The price is roughly double the parameters and forward compute of a decoder-only model at matched depth, because you're running two stacks.

**PrefixLM** (T5's "LM" variant; UL2, Tay et al. 2022; GLM, Du et al. 2022) sits in between. It runs a single stack and varies the mask by *segment*: the prompt/prefix gets bidirectional attention, like an encoder, and tokens after it are generated causally, like a decoder. One set of weights and one stack, with a segment-dependent mask. You get some of encoder-decoder's bidirectional-context benefit without a second parameter stack.

## In practice
Decoder-only won the frontier-LLM era mostly on serving and scaling engineering, less on raw quality per parameter:
- A single next-token objective scales uniformly across arbitrary text, with no encoder/decoder split to balance and no decision about how to divide capacity between two stacks.
- The causal mask fits [[Concept - KV Cache]]-based autoregressive generation: each position's key/value is computed once and, unlike under bidirectional attention, never revisited.
- The same stack that gives a good next-token distribution also turns out to support strong in-context learning with no architectural change.
- Wang et al. (2022, "What Language Model Architecture and Pretraining Objective Work Best for Zero-Shot Generalization?") ran controlled comparisons across architecture and objective. Decoder-only with a causal LM objective came out as the strongest all-around choice for the zero-shot regime that dominates modern LLM use, though it wasn't uniformly dominant on every axis. That caveat matters for the non-obvious point below.

Encoder-only and encoder-decoder models are still around wherever the task needs a representation instead of a generation. [[Concept - Embedding Models]] and [[Concept - Rerankers]] are almost universally bidirectional encoders (often BERT-derived, or a decoder adapted to be bidirectional), because retrieval and reranking need a whole-sequence representation tuned for similarity comparison. T5-style encoder-decoders still appear in dedicated translation and summarization systems, where the fixed-input/variable-output shape fits. [[Concept - Vision Transformers]] take the encoder-only pattern directly: a ViT is a BERT-shaped bidirectional encoder run on image patches instead of tokens.

## Failure modes
- **Using an encoder-only model as a generator.** It has no causal training signal and no autoregressive sampling path. Trying to "generate" from a masked-LM model means bolting on a decoder or getting degenerate output.
- **Underestimating encoder-decoder serving cost.** The cross-attention KV cache covers the *encoder's* output and is computed once, but the decoder still needs its own growing KV cache. Two stacks roughly double parameter and activation memory versus a decoder-only model at matched total depth.
- **PrefixLM mask bugs.** Get the boundary between the bidirectional prefix and the causal generation segment wrong (off-by-one, or a causal mask over the whole sequence) and you silently lose the bidirectional-context benefit the design is for.

## The non-obvious
Decoder-only's dominance is partly about *operational* convenience and isn't a settled quality verdict. Wang et al.'s own comparison found encoder-decoder models competitive or ahead on some transfer and multitask setups. The industry picked decoder-only anyway because one stack with one KV-cache shape is far simpler to scale, batch, and serve at the trillion-parameter, million-request-per-day level that matters commercially. [[Concept - Mixture of Experts Architecture]] designs keep attention dense while sparsifying the FFN for the same reason. In this field, an architecture "win" is often as much about compute and serving as about quality. Look at embedding models and rerankers: where the serving-simplicity argument is weaker, bidirectional architectures are still the default, and they aren't a legacy holdout.

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
