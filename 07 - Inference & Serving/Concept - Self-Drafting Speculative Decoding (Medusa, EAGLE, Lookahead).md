---
tags: [concept, domain/inference-serving, level/frontier]
aliases: [Medusa, EAGLE, Lookahead decoding, self-speculative decoding, self-drafting]
summary: "Speculative decoding without a second model: extra heads, predicted hidden states, or Jacobi iteration draft tokens from the target itself."
---
# Concept - Self-Drafting Speculative Decoding (Medusa, EAGLE, Lookahead)
> **One-paragraph hook:** [[Concept - Speculative Decoding]] gets its speedup by spending decode's idle compute on verification — but the classic recipe needs a second, separately trained model, with its own VRAM budget and a tokenizer that must stay in lockstep with the target forever. Self-drafting methods cash in the same free lunch without ever loading a second model: the target proposes its own continuation, either through extra prediction heads bolted onto its own hidden state, by autoregressing at the feature level instead of the token level, or by running a parallel fixed-point iteration that needs no separate draft at all. The verification math is unchanged — only the source of the `k` proposed tokens differs.

## The mechanism

All three methods still reduce to the same accept/reject loop [[Snippet - Speculative Decoding Verification]] implements: propose `k` tokens cheaply, score all `k+1` positions in one target forward pass, keep the longest accepted prefix. What changes is where the proposals come from.

**Medusa** (Cai et al. 2024) adds several lightweight linear heads on top of the target's *final* hidden state at position `t`, each trained to predict a different future offset directly: head `i` predicts the token at `t+i`. Because every head conditions on the same single hidden state rather than on the (unknown) intermediate tokens between `t` and `t+i`, accuracy decays with `i` — head 1 is fairly reliable, head 4 is guessing much more. Medusa compensates by generating a small *tree* of candidate continuations from the heads' top-few predictions at each offset, rather than one linear guess, and verifying the whole tree in a single forward pass with a custom attention mask.

**EAGLE** (Li et al. 2024) drafts at the *feature* level instead: a small autoregressive module takes the target's current hidden state plus the embedding of the just-drafted token and predicts the *next* hidden state, which is then passed through the target's own unembedding to get a token. The bet is that hidden-state trajectories are smoother and lower-entropy than sampled token sequences — a token is a discrete draw from a distribution, but the hidden state that produced it is a comparatively continuous, more predictable function of context — so drafting in feature space gets a materially higher acceptance rate than Medusa's token-level heads at similar overhead. EAGLE-2 and EAGLE-3 add dynamic, context-aware draft trees (the shape of the candidate tree adapts per step instead of being fixed), reporting roughly 3-4x wall-clock speedups with mean accepted lengths around 4-5 tokens per verification pass.

**Lookahead decoding** (Fu et al. 2024) needs no draft model or extra heads at all. It reframes decode as a Jacobi-iteration fixed-point problem: guess a window of several future tokens in parallel, run one target forward pass over the guessed window, and some guesses will happen to already be correct (a fixed point of the iteration) even with no model dedicated to proposing them — those get kept, and the pass simultaneously harvests n-grams from the trace into a lookahead cache that seeds better guesses on subsequent steps. It breaks decode's strict sequential dependency using only the target model's own compute, at the cost of a larger per-step token count than a true single-token step.

**Tree verification** is what makes multi-branch proposals worth the extra forward-pass width: instead of scoring one linear chain of `k` guesses, score a *tree* of candidates in a single pass, using an attention mask that restricts each tree node to attend only along its own root-to-leaf path, not across sibling branches:

```
                 root (t)
              /    |    \
           "the"  "a"  "an"      <- offset t+1 candidates
           /  \         \
        "cat" "dog"    "apple"   <- offset t+2 candidates, per-branch
```

The verifier walks the tree top-down and keeps the longest accepted root-to-node path. A wrong guess on one branch only wastes that branch, not the whole call, so tree verification raises the expected accepted length per target pass compared to betting everything on one linear draft sequence — the same reason wider beams help beam search, applied to verification instead of generation.

## In practice

| Method | Proposal source | Extra trained params | Typical accepted length |
|---|---|---|---|
| Medusa | Token-level heads on final hidden state | A few small linear heads | Lower, decays with depth |
| EAGLE-2/3 | Predicted next hidden state (feature-level) | One small autoregressive draft layer | ~4-5 tokens/pass |
| Lookahead | Jacobi-iteration window + n-gram cache | None | Workload-dependent, no training needed |

All three are converging into the major serving engines rather than staying research curiosities — [[Breakdown - SGLang and RadixAttention|SGLang]] and its peers increasingly ship tree-based speculative decoding as a built-in scheduling option. They inherit the same operating-regime caveat as vanilla speculative decoding, unchanged: this is a **low-batch, latency-win** family. The extra verification width only exploits *spare* decode compute, which only exists when the GPU is memory-bandwidth-bound; push batch size up into the compute-bound region and the same tree-verification FLOPs that were free at batch 1 start competing with useful decode throughput.

## Failure modes

- **Medusa's accuracy decays with speculation depth.** Heads predicting further offsets have less information to work with (no visibility into the intermediate tokens a real autoregressive pass would have produced), so acceptance rate falls off the deeper the tree goes; tree verification mitigates the wasted-call cost but doesn't fix the underlying miscalibration.
- **EAGLE's draft layer goes stale on fine-tuning.** Because it's trained to track the target's hidden-state trajectory, any fine-tune of the target that shifts its representation space silently degrades EAGLE's acceptance rate the same way a mismatched draft model degrades vanilla speculative decoding — the head needs retraining alongside the target, not just once at launch.
- **Lookahead's window size reintroduces the batch-size problem sooner.** A larger guess window means more tokens processed per step even for a single request, which can push that request's own step out of the memory-bound region at long window sizes, eroding the very free-lunch property the technique depends on.
- **Detection, all three:** monitor mean accepted length per verification call and aggregate fleet throughput before/after enabling the feature — a throughput drop under load while single-stream latency benchmarks still look great is the same regression pattern as vanilla speculative decoding deployed at the wrong batch regime.
- **Tree verification changes floating-point reduction order relative to plain decode.** Batching a variable-shaped candidate tree shifts the order attention and matmul reductions happen in, which can produce token-level divergence between a speculative and a non-speculative run at the same temperature — a concrete instance of the broader [[Concept - Nondeterminism in LLM Inference]] problem, not evidence of a broken accept/reject implementation.

## The non-obvious

"No second model" doesn't mean "zero marginal memory" — Medusa's heads and EAGLE's draft layer still add parameters, and EAGLE's autoregressive feature predictor maintains its own small recurring state that must stay synchronized with the target's [[Concept - KV Cache|KV cache]] during tree verification. The honest framing is that self-drafting trades a *whole second model's* weights and KV cache for a *small fraction* of one (typically well under 5% of target parameters), not that the overhead disappears.

The deeper reason EAGLE beats Medusa at comparable cost isn't a training trick, it's a claim about representation geometry: predicting in a smoother, lower-entropy space (hidden states) is fundamentally easier than predicting the sampled discrete output of that space (tokens). That's the same intuition behind why [[Concept - Knowledge Distillation|distilling]] on soft targets outperforms distilling on hard labels — EAGLE is, in effect, doing next-feature distillation from the target onto a tiny student, online, during inference.

## Connections
- [[Concept - Speculative Decoding]] — the base draft-verify mechanism and losslessness proof this entire family reuses unchanged; only the source of proposed tokens differs.
- [[Concept - KV Cache]] — EAGLE's feature-predictor and Medusa's heads carry their own small autoregressive state that must stay synchronized with the target's cache during tree verification.
- [[Concept - Attention Mechanism]] — cross-domain (03): tree verification depends on a custom attention mask restricting each candidate node to its own root-to-leaf path rather than plain causal attention.
- [[Concept - Knowledge Distillation]] — cross-domain (06): Medusa's heads and EAGLE's draft layer are trained to track the target's own next-token or next-feature distribution — the same objective as training a separate draft model.
- [[Breakdown - SGLang and RadixAttention]] — a concrete serving engine shipping tree-based speculative decoding in production.
- [[Snippet - Speculative Decoding Verification]] — the runnable accept/reject rule this family verifies its proposals with, unchanged from vanilla speculative decoding.
- [[Concept - Latency, Throughput, and Cost in LLM Serving]] — the same low-batch-only regime caveat governs whether self-drafting helps or actively hurts a given deployment.
- [[Concept - The Roofline Model]] — cross-domain (08): the compute-vs-bandwidth framework explaining why self-drafting's extra verification FLOPs are nearly free at low batch and costly at high batch.
- [[Concept - Nondeterminism in LLM Inference]] — tree-batched verification reorders the same floating-point reductions this note's broader nondeterminism problem is about, so speculative and non-speculative runs can diverge even at temperature 0.

## Sources
- Cai et al. (2024) — *Medusa: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads*. Introduces token-level self-drafting heads with tree-attention verification.
- Li et al. (2024) — *EAGLE: Speculative Sampling Requires Rethinking Feature Uncertainty*. Drafts at the hidden-state feature level for higher acceptance; EAGLE-2/3 add dynamic draft trees.
- Fu et al. (2024) — *Break the Sequential Dependency of LLM Inference Using Lookahead Decoding*. Jacobi-iteration parallel decoding with no draft model or extra heads.
