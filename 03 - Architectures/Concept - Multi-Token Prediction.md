---
tags: [concept, domain/architectures, level/frontier]
aliases: [MTP, multi-token prediction, next-n-token prediction]
summary: "Training a model to predict several future tokens per position — a denser training signal that doubles as a built-in speculative draft."
---

# Concept - Multi-Token Prediction

> **One-paragraph hook:** A standard language model is trained to predict exactly one token — position $t$ predicts token $t{+}1$. Multi-Token Prediction (MTP) adds auxiliary objectives that also predict $t{+}2, t{+}3, \dots$ from the same position. This does two things at once: it densifies the learning signal (each position now supplies gradient for several predictions, forcing representations that plan ahead), and it hands you a *free draft model* for [[Concept - Speculative Decoding|speculative decoding]] at inference, because the extra heads already emit guesses for the next few tokens. It is one of the few architecture tricks that pays off in both training efficiency and serving speed.

## The mechanism

Standard causal LM training minimizes next-token cross-entropy: at each position $t$, predict $x_{t+1}$ from the hidden state $h_t$. MTP generalizes this to predict a window of future tokens. Two designs dominate, and they differ in a way that matters:

**Parallel independent heads (Meta — Gloeckle et al. 2024).** Keep one shared transformer trunk, then attach $n$ independent output heads on top of the final hidden state. Head $i$ predicts $x_{t+i}$. The loss is the sum of $n$ cross-entropies:

$$\mathcal{L} = \sum_{i=1}^{n} \mathrm{CE}\big(\text{Head}_i(h_t),\; x_{t+i}\big)$$

The heads are cheap (a single unembedding-style projection each), share the entire backbone, and are trained in parallel. Because head $i$ predicts $i$ tokens ahead *from the same context*, it can only capture what is predictable from $h_t$ alone — it does not see $x_{t+1}$ when guessing $x_{t+2}$.

**Sequential MTP module (DeepSeek-V3).** Instead of independent heads, add a small extra transformer block that predicts the *second-next* token while keeping the causal chain intact: the module for depth $k$ takes the previous depth's representation *plus the embedding of the actual next token* and predicts one token further out. This preserves the conditional structure $p(x_{t+2}\mid x_{\le t+1})$ rather than collapsing to $p(x_{t+2}\mid x_{\le t})$, which is a strictly better factorization of the sequence likelihood. DeepSeek-V3 uses a single such module (predicts one extra token) as an **auxiliary training loss**, weighted $\lambda$ (0.3 for the first 10T tokens, decayed to 0.1).

```
Meta (parallel):        Sequential (DeepSeek-V3):
   h_t                     h_t ──► main head ──► x_{t+1}
   ├─ head1 ─► x_{t+1}       │
   ├─ head2 ─► x_{t+2}       └─►[MTP block]◄─ emb(x_{t+1})
   ├─ head3 ─► x_{t+3}              └──────► x_{t+2}
   └─ head4 ─► x_{t+4}       (keeps the causal chain intact)
```

**Why it helps training.** The extra objectives are a denser supervisory signal and a mild lookahead prior: to predict $t{+}2$ and $t{+}3$ the trunk must encode enough about the near future to make later tokens easier, which nudges representations toward planning rather than purely local continuation. It also partially counters the *teacher-forcing myopia* of pure next-token training. See [[Concept - Pretraining Objectives]] for where MTP sits among training-objective variants and [[Deep Dive - Anatomy of a Pretraining Run]] for where the auxiliary loss slots into a real run.

## In practice

- **Meta MTP (Gloeckle et al. 2024)** reports gains that *scale with model size* and concentrate in **code and reasoning** — meaningful lifts on HumanEval/MBPP-style generative coding — while gains on pure multiple-choice knowledge benchmarks are muted. Their headline serving result: using the extra heads as a self-speculative draft gives up to **~3× faster inference** on code with a byte-level tokenizer, and roughly 1.5–2× in more typical settings.
- **DeepSeek-V3** uses the sequential MTP module during pretraining, then repurposes it at inference as a built-in draft: the model proposes the second-next token and verifies it in the same forward pass. Reported **acceptance rate of 85–90%** for the second token, yielding **~1.8× decode throughput** (TPS). Training and systems details are in [[Breakdown - DeepSeek-V3 Training]]; the full model in [[Breakdown - DeepSeek-V3 Architecture]].
- **Design choices that matter:** parallel independent heads vs. a sequential module; the loss weight on the extra heads (too high and it competes with the primary objective); and whether to **keep or discard** the heads at inference. DeepSeek keeps the module for drafting; a team that only wants the training benefit can drop it and pay zero inference cost.

The self-speculative angle links MTP directly to the draft-head family — [[Concept - Self-Drafting Speculative Decoding (Medusa, EAGLE, Lookahead)|Medusa/EAGLE-style draft heads]] are essentially MTP heads bolted onto a *finished* model post-hoc, whereas MTP bakes them in during pretraining so the trunk co-adapts to them.

## Failure modes

- **Uneven gains / no gain.** MTP's training benefit is uneven across tasks and can be near-zero for small models or knowledge-heavy evals. Blindly assuming it helps is the main trap — measure per-capability, not on aggregate loss.
- **Loss-weight interference.** Weight the auxiliary heads too heavily and they degrade the primary next-token predictor; DeepSeek's decay from 0.3→0.1 exists precisely to stop the extra objective from dominating late training.
- **Draft-quality cliff at high temperature.** The self-speculative payoff depends on the draft head agreeing with the verified distribution. Under high-temperature or heavily-penalized [[Concept - Sampling and Decoding Parameters|sampling]], acceptance rate drops and the speedup evaporates — the 1.8× is a low-temperature, near-greedy figure.
- **Head/trunk mismatch when bolted on late.** Adding MTP heads to an already-trained model (rather than pretraining with them) gives weaker drafts than co-trained heads, because the trunk never learned to make future tokens linearly readable.

## The non-obvious

The quiet insight is that MTP is a form of **self-distillation through the architecture**: the auxiliary heads force the trunk to expose information about tokens it isn't yet committing to, which is why the effect rhymes with [[Concept - Knowledge Distillation]] even though there's no teacher — the model is being pushed to make its own future predictable to itself. The second, more practical piece of tribal knowledge: **the inference speedup and the training-quality gain are separable.** You can pretrain with MTP for the representation benefit and then *throw the heads away* for a plain, fast, single-head serving model — or keep them and get the ~1.8× draft. Frontier teams increasingly treat MTP as "free draft model, plus a small training bonus," and that framing — not the marginal perplexity gain — is why it's spreading. It remains an actively evolving technique with gains that are real but not universal.

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
