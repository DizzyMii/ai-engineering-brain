---
tags: [concept, domain/architectures, level/frontier]
aliases: [MTP, multi-token prediction, next-n-token prediction]
summary: "Training a model to predict several future tokens per position — a denser training signal that doubles as a built-in speculative draft."
---

# Concept - Multi-Token Prediction

> **One-paragraph hook:** A standard language model is trained to predict one token: position $t$ predicts token $t{+}1$. Multi-Token Prediction (MTP) adds auxiliary objectives that also predict $t{+}2, t{+}3, \dots$ from the same position. That buys two things. The learning signal gets denser, since each position now supplies gradient for several predictions, which pushes representations to plan ahead. And you get a *free draft model* for [[Concept - Speculative Decoding|speculative decoding]] at inference, because the extra heads already emit guesses for the next few tokens. Few architecture tricks pay off in both training efficiency and serving speed; this is one.

## The mechanism

Standard causal LM training minimizes next-token cross-entropy: at each position $t$, predict $x_{t+1}$ from the hidden state $h_t$. MTP generalizes this to a window of future tokens. Two designs dominate, and they differ in a way that matters.

**Parallel independent heads (Meta, Gloeckle et al. 2024).** One shared transformer trunk, with $n$ independent output heads on top of the final hidden state. Head $i$ predicts $x_{t+i}$. The loss is the sum of $n$ cross-entropies:

$$\mathcal{L} = \sum_{i=1}^{n} \mathrm{CE}\big(\text{Head}_i(h_t),\; x_{t+i}\big)$$

Each head is cheap (one unembedding-style projection), they all share the backbone, and they train in parallel. Head $i$ predicts $i$ tokens ahead *from the same context*, so it only captures what's predictable from $h_t$ alone. It never sees $x_{t+1}$ when guessing $x_{t+2}$.

**Sequential MTP module (DeepSeek-V3).** Here a small extra transformer block predicts the *second-next* token and keeps the causal chain intact. The module at depth $k$ takes the previous depth's representation *plus the embedding of the actual next token* and predicts one token further out. That keeps the conditional structure $p(x_{t+2}\mid x_{\le t+1})$ instead of collapsing to $p(x_{t+2}\mid x_{\le t})$, a strictly better factorization of the sequence likelihood. DeepSeek-V3 uses one such module (one extra token) as an **auxiliary training loss** with weight $\lambda$: 0.3 for the first 10T tokens, decayed to 0.1.

```
Meta (parallel):        Sequential (DeepSeek-V3):
   h_t                     h_t ──► main head ──► x_{t+1}
   ├─ head1 ─► x_{t+1}       │
   ├─ head2 ─► x_{t+2}       └─►[MTP block]◄─ emb(x_{t+1})
   ├─ head3 ─► x_{t+3}              └──────► x_{t+2}
   └─ head4 ─► x_{t+4}       (keeps the causal chain intact)
```

**Why it helps training.** The extra objectives give a denser supervisory signal and a mild lookahead prior. To predict $t{+}2$ and $t{+}3$, the trunk has to encode enough about the near future to make later tokens easier, which nudges representations toward planning and away from purely local continuation. It also partly counters the *teacher-forcing myopia* of pure next-token training. [[Concept - Pretraining Objectives]] places MTP among the training-objective variants, and [[Deep Dive - Anatomy of a Pretraining Run]] shows where the auxiliary loss goes in a real run.

## In practice

- **Meta MTP (Gloeckle et al. 2024)** reports gains that *scale with model size* and concentrate in **code and reasoning**, with meaningful lifts on HumanEval/MBPP-style generative coding. Gains on pure multiple-choice knowledge benchmarks are muted. The headline serving result: using the extra heads as a self-speculative draft gives up to **~3× faster inference** on code with a byte-level tokenizer, and roughly 1.5–2× in more typical settings.
- **DeepSeek-V3** trains with the sequential MTP module, then reuses it at inference as a built-in draft. The model proposes the second-next token and verifies it in the same forward pass. Reported **acceptance rate is 85–90%** for the second token, for **~1.8× decode throughput** (TPS). Training and systems details are in [[Breakdown - DeepSeek-V3 Training]], the full model in [[Breakdown - DeepSeek-V3 Architecture]].
- **Design choices that matter:** parallel independent heads or a sequential module; the loss weight on the extra heads (set it too high and it competes with the primary objective); and whether to **keep or discard** the heads at inference. DeepSeek keeps the module for drafting. A team that only wants the training benefit can drop it and pay zero inference cost.

The self-speculative angle ties MTP to the draft-head family. [[Concept - Self-Drafting Speculative Decoding (Medusa, EAGLE, Lookahead)|Medusa/EAGLE-style draft heads]] are essentially MTP heads bolted onto a *finished* model post-hoc. MTP bakes them in during pretraining, so the trunk co-adapts to them.

## Failure modes

- **Uneven gains, or none.** The training benefit varies across tasks and can be near-zero for small models or knowledge-heavy evals. The main trap is assuming it helps. Measure per capability, not on aggregate loss.
- **Loss-weight interference.** Weight the auxiliary heads too heavily and the primary next-token predictor gets worse. DeepSeek decays the weight from 0.3→0.1 to keep the extra objective from dominating late training.
- **Draft-quality cliff at high temperature.** The self-speculative payoff depends on the draft head agreeing with the verified distribution. Under high-temperature or heavily penalized [[Concept - Sampling and Decoding Parameters|sampling]], acceptance drops and the speedup disappears. The 1.8× is a low-temperature, near-greedy figure.
- **Head/trunk mismatch when bolted on late.** MTP heads added to an already-trained model give weaker drafts than co-trained ones, because the trunk never learned to make future tokens linearly readable.

## The non-obvious

MTP works like **self-distillation through the architecture**. The auxiliary heads force the trunk to expose information about tokens it isn't committing to yet, which is why the effect resembles [[Concept - Knowledge Distillation]] even with no teacher: the model is pushed to make its own future predictable to itself.

The more practical tribal knowledge: **the inference speedup and the training-quality gain are separable.** You can pretrain with MTP for the representation benefit and *throw the heads away* for a plain, fast, single-head serving model, or keep them and get the ~1.8× draft. Frontier teams increasingly treat MTP as "free draft model, plus a small training bonus," and that framing, more than the marginal perplexity gain, is why it's spreading. The technique is still evolving, and its gains are real but not universal.

## Connections

- [[Concept - Speculative Decoding]] — MTP's headline inference payoff; the extra heads *are* the draft model, no separate network needed.
- [[Concept - Self-Drafting Speculative Decoding (Medusa, EAGLE, Lookahead)]] — the post-hoc cousins; MTP is the pretraining-time version of the same draft-head idea.
- [[Breakdown - DeepSeek-V3 Architecture]] — the highest-profile production use: a sequential MTP module for training signal + ~1.8× decode.
- [[Breakdown - DeepSeek-V3 Training]] — where the MTP auxiliary loss and its weight schedule live in a real run.
- [[Concept - Pretraining Objectives]] — MTP as a variant of the next-token objective; the family it belongs to.
- [[Deep Dive - Anatomy of a Pretraining Run]] — how an auxiliary objective is added and weighted alongside the main loss.
- [[Deep Dive - The Transformer]] — the shared trunk the heads attach to; MTP changes only the output side.
- [[Concept - Knowledge Distillation]] — the mechanistic rhyme: MTP behaves like self-distillation, forcing future-token information into the representation.
- [[Concept - Sampling and Decoding Parameters]] — draft acceptance (and thus the speedup) is sampling-temperature dependent.

## Sources
- Gloeckle et al. (2024) — *Better & Faster Large Language Models via Multi-token Prediction.* Parallel-head MTP; gains scale with size, concentrate in code; ~3× self-speculative inference.
- DeepSeek-AI (2024) — *DeepSeek-V3 Technical Report.* Sequential MTP module, loss weight 0.3→0.1, 85–90% acceptance, ~1.8× TPS.
- Cai et al. (2024) — *Medusa.* Post-hoc multi-head drafting; contrast with pretrained-in MTP.
