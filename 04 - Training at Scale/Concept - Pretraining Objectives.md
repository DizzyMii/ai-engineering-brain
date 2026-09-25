---
tags: [concept, domain/training-at-scale, level/core]
aliases: [causal language modeling, CLM, self-supervised pretraining objectives]
summary: "The self-supervised objectives that shape LLM pretraining: causal LM, masked LM, span corruption, prefix-LM, and fill-in-the-middle."
---

# Concept - Pretraining Objectives

> **One-paragraph hook:** The pretraining objective decides whether the resulting model can generate text at all, how much of each training document becomes gradient signal, and whether it will ever be any good at completing code with context on both sides. Decoder-only causal language modeling won the field because it is the densest objective whose training-time task is identical to its deployment-time task. Theoretical elegance had little to do with it.

## The mechanism

**Causal LM (CLM)** predicts token $t{+}1$ from tokens $\le t$ under teacher forcing. It minimizes cross-entropy summed over every position in the sequence, over next-token probabilities across the vocabulary that [[Concept - Byte-Pair Encoding]] (or a unigram tokenizer) defines. The loss itself is in [[Concept - Entropy and Cross-Entropy]].

$$\mathcal{L}_{CLM} = -\sum_{t=1}^{T} \log P_\theta(x_t \mid x_{<t})$$

Every position contributes a loss term, so a document of length $T$ yields $T$ training signals from one forward pass. That density is the main reason decoder-only CLM dominates modern LLM pretraining, and it maps directly onto the causal attention pattern in the [[Deep Dive - The Transformer]] architecture.

**Masked LM (MLM)**, from BERT (Devlin et al., 2018), masks ~15% of tokens and predicts them from bidirectional context:

$$\mathcal{L}_{MLM} = -\sum_{t \in M} \log P_\theta(x_t \mid x_{\setminus M})$$

Only the masked ~15% contribute loss, roughly 7x less signal per sequence than CLM. The bidirectional attention that makes MLM representations good for classification also makes the model not natively generative. You can't sample text left-to-right from it without extra machinery.

**Span corruption** (T5, Raffel et al., 2020) generalizes MLM: it masks contiguous spans instead of single tokens and replaces each span with a sentinel token. An encoder-decoder model then generates the corrupted spans autoregressively, delimited by sentinels. UL2 (Tay et al., 2022) puts several corruption regimes behind a mode token the model conditions on at training and inference time: short-span "R-denoising," long-span/high-corruption-rate "X-denoising," and prefix-style "S-denoising."

**Fill-in-the-middle (FIM)** (Bavarian et al., 2022) lets a purely causal decoder infill. A training document is split into prefix/middle/suffix and reordered with sentinel tokens, either prefix-suffix-middle (PSM) or suffix-prefix-middle (SPM), so the model predicts the "middle" span after already seeing the "suffix" earlier in its causal context. It reorders data and leaves the architecture alone, which is why it's cheap to add: FIM rates of 50-90% of training documents cost essentially nothing in the autoregressive loss.

**Prefix-LM** sits between CLM and MLM. Attention over the prompt/prefix region is bidirectional and attention over the continuation stays causal, so one model runs two attention regimes depending on position. It suits tasks with a clear instruction/completion split.

```text
CLM:          x1 x2 x3 x4 x5     each xt attends only to x<=t   (lower-triangular mask)
MLM:          x1 [M] x3 [M] x5   [M] attends to ALL positions   (full bidirectional mask)
Prefix-LM:    <-- prefix (bidir) --> | <-- continuation (causal) -->
FIM (PSM):    <prefix> <SUF> <suffix> <MID> <middle>     -- reordered, still causal
```

## In practice

Production pretraining is overwhelmingly causal-LM-first, with FIM mixed in for models expected to do code completion. StarCoder- and DeepSeek-Coder-style recipes train on a majority-CLM, ~50%+-FIM-sampled mixture instead of a separate FIM-only phase, since a decoder trained purely left-to-right never sees the "suffix already exists" case. Encoder-decoder span corruption and UL2-style denoiser mixtures still matter for retrieval/embedding-adjacent or translation-style models. They lost the frontier-LLM race to decoder-only CLM, largely on loss density and inference simplicity.

[[Deep Dive - Anatomy of a Pretraining Run]] covers where the objective choice sits in overall run design. [[Concept - Tokenizer Training]] explains why sentinel and FIM markers have to be reserved as vocabulary slots before a single byte of the corpus is tokenized. The causal-LM loss carries over unchanged into [[Concept - Supervised Fine-Tuning (SFT)]], which uses loss masking to restrict it to completion tokens.

## Failure modes

- **FIM train/inference format mismatch.** Serving PSM-formatted completions to a model trained SPM (or vice versa) degrades infilling with no error. Completions just get worse.
- **Document-packing attention bleed.** Packing several documents into one training sequence lets attention (and RoPE position IDs) leak across document boundaries unless you insert reset masks or rely on EOS-token separators. The masking and packing machinery is in [[Concept - Loss Masking and Sequence Packing]].
- **Loss computed over padding.** If padding tokens aren't masked out of the CLM loss, the denominator is inflated and the reported loss is biased downward relative to real per-token performance.
- **Unreserved sentinel tokens.** Adding FIM or corruption sentinels to the tokenizer after pretraining has started forces an embedding-matrix resize, and the new rows start with no gradient history.

## The non-obvious

People usually say CLM won because it's simpler. The better reason: CLM is the only major objective with **zero train/deploy mismatch**. The model trains on predicting the next token given everything before it, and that's the task it performs at inference. BERT needs a task-specific head bolted on for anything generative, and span-corruption models need their encoder-decoder machinery reproduced at serving time. At the scale modern LLMs run at, CLM's training-signal density and architectural simplicity more than pay for the representational power MLM gets from bidirectional context. So the field converged on CLM despite MLM's early popularity for encoder-only representation models.

## Connections
- [[Concept - Entropy and Cross-Entropy]] — the loss function every objective in this note is a variant of.
- [[Concept - Byte-Pair Encoding]] — the tokenizer whose vocabulary defines both the prediction targets and the sentinel tokens FIM/span-corruption rely on.
- [[Concept - Data Mixtures]] — how much of the corpus gets FIM-reordered or corrupted is itself a mixture decision.
- [[Deep Dive - The Transformer]] — the architecture whose attention pattern (causal vs bidirectional vs prefix) each objective assumes.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the next pipeline stage, which reuses the causal-LM loss but restricts it to completion tokens via loss masking.
- [[Deep Dive - Anatomy of a Pretraining Run]] — where the objective choice fits into an end-to-end run's design.
- [[Concept - Tokenizer Training]] — sentinel/FIM tokens must be reserved in the vocabulary before training, not added after.
- [[Concept - Loss Masking and Sequence Packing]] — the packing and masking machinery that keeps CLM's dense per-token loss from bleeding across document boundaries.

## Sources
- Devlin et al. (2018) — "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding" — introduced masked language modeling.
- Raffel et al. (2020) — "Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer" (T5) — span corruption with sentinel tokens in an encoder-decoder.
- Tay et al. (2022) — "UL2: Unifying Language Learning Paradigms" — mixture-of-denoisers unifying span corruption, prefix-LM, and CLM-like objectives behind a mode token.
- Bavarian et al. (2022) — "Efficient Training of Language Models to Fill in the Middle" — FIM via document reordering, PSM/SPM formats.
