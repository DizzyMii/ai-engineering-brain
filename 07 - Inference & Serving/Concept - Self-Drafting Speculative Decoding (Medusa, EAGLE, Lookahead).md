---
tags: [concept, domain/inference-serving, level/frontier]
aliases: [Medusa, EAGLE, Lookahead decoding, self-speculative decoding, self-drafting]
summary: "Speculative decoding without a second model: extra heads, predicted hidden states, or Jacobi iteration draft tokens from the target itself."
---
# Concept - Self-Drafting Speculative Decoding (Medusa, EAGLE, Lookahead)
> **One-paragraph hook:** [[Concept - Speculative Decoding]] gets its speedup by spending decode's idle compute on verification. The classic recipe needs a second, separately trained model, with its own VRAM budget and a tokenizer that has to stay in lockstep with the target forever. Self-drafting methods get the same free lunch without loading a second model. The target proposes its own continuation in one of three ways: extra prediction heads bolted onto its hidden state, autoregression at the feature level instead of the token level, or a parallel fixed-point iteration with no separate draft at all. The verification math is unchanged; only the source of the `k` proposed tokens differs.

## The mechanism

All three still reduce to the accept/reject loop in [[Snippet - Speculative Decoding Verification]]: propose `k` tokens cheaply, score all `k+1` positions in one target forward pass, keep the longest accepted prefix. What changes is where the proposals come from.

**Medusa** (Cai et al. 2024) adds several lightweight linear heads on top of the target's *final* hidden state at position `t`. Each is trained to predict a different future offset directly: head `i` predicts the token at `t+i`. Every head conditions on that one hidden state and never sees the (unknown) intermediate tokens between `t` and `t+i`, so accuracy decays with `i`. Head 1 is fairly reliable; head 4 is guessing much more. To compensate, Medusa builds a small *tree* of candidate continuations from the heads' top few predictions at each offset and verifies the whole tree in one forward pass with a custom attention mask.

**EAGLE** (Li et al. 2024) drafts at the *feature* level. A small autoregressive module takes the target's current hidden state plus the embedding of the just-drafted token and predicts the *next* hidden state, which goes through the target's own unembedding to produce a token. The bet is that hidden-state trajectories are smoother and lower-entropy than sampled token sequences. A token is a discrete draw from a distribution; the hidden state behind it is a comparatively continuous, more predictable function of context. So drafting in feature space gets a materially higher acceptance rate than Medusa's token-level heads at similar overhead. EAGLE-2 and EAGLE-3 add dynamic, context-aware draft trees whose shape adapts per step, and report roughly 3-4x wall-clock speedups with mean accepted lengths around 4-5 tokens per verification pass.

**Lookahead decoding** (Fu et al. 2024) needs no draft model or extra heads. It treats decode as a Jacobi-iteration fixed-point problem. Guess a window of several future tokens in parallel and run one target forward pass over it. Some guesses will already be correct (a fixed point of the iteration) even though nothing was trained to propose them, and those are kept. The same pass harvests n-grams from the trace into a lookahead cache that seeds better guesses on later steps. This breaks decode's strict sequential dependency using only the target's own compute, at the cost of more tokens per step than a true single-token step.

**Tree verification** is why multi-branch proposals are worth the extra forward-pass width. You score a *tree* of candidates in one pass instead of one linear chain of `k` guesses. The attention mask lets each tree node attend only along its own root-to-leaf path, never across sibling branches:

```
                 root (t)
              /    |    \
           "the"  "a"  "an"      <- offset t+1 candidates
           /  \         \
        "cat" "dog"    "apple"   <- offset t+2 candidates, per-branch
```

The verifier walks the tree top-down and keeps the longest accepted root-to-node path. A wrong guess wastes only its own branch, not the whole call, so expected accepted length per target pass goes up compared with betting everything on one linear draft. Wider beams help beam search for the same reason; here it's applied to verification.

## In practice

| Method | Proposal source | Extra trained params | Typical accepted length |
|---|---|---|---|
| Medusa | Token-level heads on final hidden state | A few small linear heads | Lower, decays with depth |
| EAGLE-2/3 | Predicted next hidden state (feature-level) | One small autoregressive draft layer | ~4-5 tokens/pass |
| Lookahead | Jacobi-iteration window + n-gram cache | None | Workload-dependent, no training needed |

All three are moving into the major serving engines; [[Breakdown - SGLang and RadixAttention|SGLang]] and its peers increasingly ship tree-based speculative decoding as a built-in scheduling option. The operating-regime caveat from vanilla speculative decoding carries over unchanged: this is a **low-batch, latency-win** family. Extra verification width only uses *spare* decode compute, which exists only while the GPU is memory-bandwidth-bound. Push batch size into the compute-bound region and the tree-verification FLOPs that were free at batch 1 start competing with useful decode throughput.

## Failure modes

- **Medusa's accuracy decays with speculation depth.** Heads for further offsets have less to work with, since they can't see the intermediate tokens a real autoregressive pass would have produced. Acceptance falls off the deeper the tree goes. Tree verification reduces the wasted-call cost but doesn't fix the underlying miscalibration.
- **EAGLE's draft layer goes stale on fine-tuning.** It's trained to track the target's hidden-state trajectory, so any fine-tune that shifts the target's representation space silently degrades acceptance, the same way a mismatched draft model hurts vanilla speculative decoding. The head needs retraining alongside the target, not just once at launch.
- **Lookahead's window size brings back the batch-size problem sooner.** A bigger guess window means more tokens per step even for a single request. At long window sizes that can push the request's own step out of the memory-bound region and erode the free-lunch property the technique depends on.
- **Detection, all three:** track mean accepted length per verification call and aggregate fleet throughput before and after enabling the feature. Throughput dropping under load while single-stream latency benchmarks still look great is the same regression pattern you see when vanilla speculative decoding runs at the wrong batch regime.
- **Tree verification changes floating-point reduction order relative to plain decode.** Batching a variable-shaped candidate tree reorders attention and matmul reductions, which can make a speculative and a non-speculative run diverge at the token level at the same temperature. That's an instance of the broader [[Concept - Nondeterminism in LLM Inference]] problem, not evidence of a broken accept/reject implementation.

## The non-obvious

"No second model" doesn't mean "zero marginal memory." Medusa's heads and EAGLE's draft layer still add parameters, and EAGLE's autoregressive feature predictor keeps its own small recurring state that has to stay in sync with the target's [[Concept - KV Cache|KV cache]] during tree verification. The honest framing: self-drafting trades a *whole second model's* weights and KV cache for a *small fraction* of one (typically well under 5% of target parameters). The overhead doesn't disappear.

Why does EAGLE beat Medusa at comparable cost? It's a claim about representation geometry. Predicting in a smoother, lower-entropy space (hidden states) is easier than predicting the sampled discrete output of that space (tokens). Same intuition as [[Concept - Knowledge Distillation|distilling]] on soft targets beating distilling on hard labels. In effect EAGLE does next-feature distillation from the target onto a tiny student, online, during inference.

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
