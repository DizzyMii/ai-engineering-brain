---
tags: [concept, domain/training-at-scale, level/core]
aliases: [causal language modeling, CLM, self-supervised pretraining objectives]
summary: "The self-supervised objectives that shape LLM pretraining: causal LM, masked LM, span corruption, prefix-LM, and fill-in-the-middle."
---

# Concept - Pretraining Objectives

> **One-paragraph hook:** The pretraining objective isn't an implementation detail — it decides whether the resulting model can generate text at all, how much of each training document turns into gradient signal, and whether it will ever be any good at completing code with context on both sides. Decoder-only causal language modeling won the field not because it's the most theoretically elegant objective, but because it is the densest one whose training-time task is identical to its deployment-time task.

## The mechanism

**Causal LM (CLM)** predicts token $t{+}1$ from tokens $\le t$ under teacher forcing, minimizing cross-entropy summed over every position in the sequence, computed over next-token probabilities across the vocabulary that [[Concept - Byte-Pair Encoding]] (or a unigram tokenizer) defines — see [[Concept - Entropy and Cross-Entropy]] for the loss itself:

$$\mathcal{L}_{CLM} = -\sum_{t=1}^{T} \log P_\theta(x_t \mid x_{<t})$$

Every position contributes a loss term — a document of length $T$ yields $T$ training signals from one forward pass. This density is the main reason decoder-only CLM dominates modern LLM pretraining, and it maps directly onto the causal attention pattern inside the [[Deep Dive - The Transformer]] architecture.

**Masked LM (MLM)**, from BERT (Devlin et al., 2018), instead masks ~15% of tokens and predicts them using bidirectional context:

$$\mathcal{L}_{MLM} = -\sum_{t \in M} \log P_\theta(x_t \mid x_{\setminus M})$$

Only the masked ~15% contribute loss — roughly 7x less signal per sequence than CLM — and the bidirectional attention that makes MLM's representations good for classification also makes it not natively generative: there's no way to sample text left-to-right from a model trained this way without extra machinery.

**Span corruption** (T5, Raffel et al., 2020) generalizes MLM by masking contiguous spans rather than single tokens and replacing each span with a sentinel token; an encoder-decoder model then generates the corrupted spans, delimited by sentinels, autoregressively. UL2 (Tay et al., 2022) unifies several corruption regimes — short-span "R-denoising," long-span/high-corruption-rate "X-denoising," and prefix-style "S-denoising" — behind a mode token the model conditions on at training and inference time.

**Fill-in-the-middle (FIM)** (Bavarian et al., 2022) is the trick that makes a purely causal decoder capable of infilling: a training document is split into prefix/middle/suffix, then reordered with sentinel tokens — either prefix-suffix-middle (PSM) or suffix-prefix-middle (SPM) — so the model learns to predict the "middle" span having already seen the "suffix" earlier in its causal context. It's a data-reordering trick, not an architecture change, which is why it's cheap to add: FIM rates of 50-90% of training documents cost essentially nothing in the autoregressive loss.

**Prefix-LM** sits between CLM and MLM: attention over the prompt/prefix region is bidirectional, while attention over the continuation stays causal — one model, two attention regimes depending on position, useful for tasks with a clear instruction/completion split.

```text
CLM:          x1 x2 x3 x4 x5     each xt attends only to x<=t   (lower-triangular mask)
MLM:          x1 [M] x3 [M] x5   [M] attends to ALL positions   (full bidirectional mask)
Prefix-LM:    <-- prefix (bidir) --> | <-- continuation (causal) -->
FIM (PSM):    <prefix> <SUF> <suffix> <MID> <middle>     -- reordered, still causal
```

## In practice

Production pretraining is overwhelmingly causal-LM-first, with FIM mixed in for models expected to do code completion — StarCoder- and DeepSeek-Coder-style recipes train on a majority-CLM, ~50%+-FIM-sampled mixture rather than a separate FIM-only phase, because a decoder trained purely left-to-right never sees the "suffix already exists" scenario at all. Encoder-decoder span corruption and UL2-style denoiser mixtures remain relevant for retrieval/embedding-adjacent or translation-style models but lost the frontier-LLM race to decoder-only CLM, largely on loss-density and inference-simplicity grounds. See [[Deep Dive - Anatomy of a Pretraining Run]] for where the objective choice sits in overall run design, and [[Concept - Tokenizer Training]] for why sentinel and FIM markers have to be reserved as vocabulary slots before a single byte of the corpus is tokenized. The causal-LM loss itself carries over unchanged into [[Concept - Supervised Fine-Tuning (SFT)]], which restricts the same objective to completion tokens only via loss masking.

## Failure modes

- **FIM train/inference format mismatch.** Serving PSM-formatted completions when the model was trained SPM (or vice versa) silently degrades infilling quality with no error, just worse completions.
- **Document-packing attention bleed.** Packing multiple documents into one training sequence for efficiency lets attention (and RoPE position IDs) leak across the document boundary unless you insert reset masks or rely on EOS-token separators — the masking and packing machinery itself is covered in [[Concept - Loss Masking and Sequence Packing]].
- **Loss computed over padding.** Forgetting to mask padding tokens out of the CLM loss inflates the denominator and quietly biases the reported loss downward relative to the model's real per-token performance.
- **Unreserved sentinel tokens.** Adding FIM or corruption sentinel tokens to the tokenizer after pretraining has started forces an embedding-matrix resize and initializes those rows with no gradient history behind them.

## The non-obvious

CLM's dominance is usually explained as "it's simpler," but the sharper reason is that CLM is the only major objective with **zero train/deploy mismatch**: the task the model is trained on (predict the next token given everything before it) is exactly the task it performs at inference. BERT needs a task-specific head bolted on for anything generative; span-corruption models need their encoder-decoder machinery reproduced at serving time. Every bit of extra representational power MLM buys from bidirectional context gets paid back, and then some, by CLM's training-signal density and architectural simplicity at the scale modern LLMs operate at — which is why the field converged on it despite MLM's early popularity for encoder-only representation models.

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
