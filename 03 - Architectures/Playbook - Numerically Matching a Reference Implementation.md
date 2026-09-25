---
tags: [playbook, domain/architectures, level/unicorn]
aliases: [numerical parity, activation diffing, reference matching, model porting]
summary: "Port a model to a new codebase and prove it correct against the reference by fp32 activation diffing, layer by layer."
---

# Playbook - Numerically Matching a Reference Implementation

> **Goal:** prove your reimplemented or converted model *is* the reference numerically: same logits, not "generations look plausible". Do it before you trust any fine-tune, serving port, or custom kernel built on top.
> **When to run this:** logits, perplexity, or greedy generations differ from the reference (HuggingFace ↔ original repo ↔ your kernel), or you've just written a weight-conversion script and want to gate it.
> **Prerequisites:** both models loadable in the same process, the exact reference weights, a fixed input, and the patience to compare tensors instead of squinting at samples.

## Steps

1. **Freeze and de-noise both models before comparing anything.**
   - Action: `model.eval()` on both (kills dropout), `torch.set_grad_enabled(False)`, both on the **same device**, and **disable TF32**: `torch.backends.cuda.matmul.allow_tf32 = False` and `torch.backends.cudnn.allow_tf32 = False`.
   - Expected: two deterministic functions of the input.
   - Deviation: skip the TF32 flags and you'll chase a phantom `~1e-3` mismatch on Ampere/Hopper. It isn't a bug; A100/H100 are doing tensor-core matmuls in 19-bit mantissa. It costs a whole afternoon, so do this first.

2. **Pin the input contract. "Close but wrong" is born here.**
   - Action: tokenize the *same string* with the *same tokenizer* and check the BOS/EOS/special-token prefix. Print the token IDs from both paths and `assert` they're equal.
   - Expected: identical integer ID sequences into both models.
   - Deviation: if IDs differ, stop. A missing/extra BOS or a different chat template shifts every downstream activation, and you'll blame the model for the divergence. The tokenizer matters here; [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] doesn't.

3. **Compare final logits in fp32 (or fp64) against a tolerance.**
   - Action: cast **both** models to fp32 (fp64 for the first pass if you can, to remove precision noise entirely), run the identical input, and compute `max_abs_diff = (logits_a - logits_b).abs().max()`.
   - Expected: `max_abs_diff < 1e-4` in fp32 for an equivalent implementation; `< 1e-6` in fp64.
   - Deviation: **never compare in bf16.** bf16 has ~3 decimal digits, so two *correct* implementations legitimately differ by `~1e-2`. A bf16 "match" proves nothing, and a bf16 "mismatch" is often just accumulation order. See [[Concept - Floating Point for Deep Learning]].

4. **If logits mismatch, binary-search the residual stream for the first divergent layer.**
   - Action: register forward hooks on each block in both models, capture the block output (the residual-stream tensor), and diff layer by layer. Find the **first** layer whose output exceeds tolerance.
   - Expected: a clean "matches through layer *k*, diverges at layer *k+1*" boundary that points at one sublayer.
   - Deviation: if the diff is already large at the *embedding* output (layer 0 input), the bug is pre-block: embedding table, weight-tying, or positional injection. Attention is off the hook. A diff that's tiny at every layer but grows smoothly with depth is an epsilon/scale issue, not a wiring bug (see step 6's branch table).

5. **Write the weight-name mapping table explicitly, and audit the packed-QKV split.**
   - Action: write the reference-name → your-name map as a literal table and check shapes on every entry. Watch any **fused `wqkv`** tensor. Slicing a fused `[3·d, d]` projection into Q/K/V in the wrong order, or splitting a GQA `[(n_q+2·n_kv)·d_head, d]` pack wrong, is a top silent bug.
   - Expected: every reference tensor maps to one and only one of yours, same shape, same intended role.
   - Deviation: a transposed or mis-sliced projection gives plausible-looking outputs that are wrong from layer 1. Step 4 localizes that signature.

6. **Check the divergent layer against the usual culprits.**

   | Culprit | The exact mistake | Symptom signature |
   |---|---|---|
   | RoPE ordering | interleaved (GPT-NeoX) vs half-split (`rotate_half`, HF LLaMA) — see [[Snippet - RoPE Implementation]] | diverges only past short context / on long inputs |
   | RoPE base θ | 10k vs 500k vs 1M mismatch | long-context garbles, short is fine |
   | Norm epsilon | value (1e-5 vs 1e-6) *and* inside-vs-outside the sqrt; fp32 upcast of the norm or not | small diff that grows monotonically with depth |
   | Attention scale | dividing by `d_head` vs `d_model`, or `1/sqrt` applied to the wrong dim | wrong from layer 1, entropy off |
   | GQA repeat | `repeat` vs `repeat_interleave` when expanding KV heads | heads mis-paired, wrong from layer 1 |
   | SwiGLU order | gate_proj vs up_proj swapped, or `d_ff` off | wrong from layer 1, FFN-localized |
   | Soft-cap / QK-norm | Gemma-style logit soft-capping or QK-norm present in ref, absent in yours — see [[Concept - Rotary Position Embeddings (RoPE)]] and normalization notes | small persistent offset, worse at long ctx |
   | Weight tying | untied unembedding in yours vs tied in ref (or vice-versa) | logits scaled/rotated vs ref, all positions |
   | BOS / special tokens | prefix mismatch (caught in step 2 if you did it) | every position off by the same "shift" |

   - Action: check the localized layer's row first.
   - Expected: one of these explains the divergence in >90% of real cases.
   - Deviation: if none fit, suspect an attention-mask difference (padding side, additive vs boolean mask) or kernel numerics. [[Deep Dive - FlashAttention]] and eager attention differ at ~`1e-3` in bf16, and that's legitimate.

7. **Confirm end-to-end once logits match.**
   - Action: greedy-decode N (≥64) tokens from both models and assert identical token IDs. Compute perplexity on a fixed held-out text from both.
   - Expected: identical greedy IDs for all N tokens; perplexity agreeing to 3–4 significant figures.
   - Deviation: identical logits with divergent greedy generation means a sampling/argmax tie-break difference, not a model bug.

## Verification

You're done when (1) fp32 `max_abs_diff` on final logits is `< 1e-4`, (2) greedy generations are token-identical for ≥64 steps, and (3) perplexity on a fixed text agrees to 3–4 sig figs. Anything less leaves a latent bug that a fine-tune will happily amplify. While you're at it, cross-check your config numbers against the [[Reference - Transformer Architecture Cheat Sheet]]; a mismatch there often *is* the bug.

## When it goes wrong

| Symptom | Likely cause | Jump to |
|---|---|---|
| Diverges at **layer 0 / embedding** | embedding table, weight-tying, or positional injection | Step 4, then Step 5 |
| Small diff **grows with depth** | norm epsilon value/placement or residual scaling | Step 6 (norm row); [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]] |
| Fine at short ctx, **breaks at long context** | RoPE base θ or interleave/half ordering | Step 6 (RoPE rows) |
| Wrong from **layer 1**, FFN-shaped | SwiGLU gate/up swap or `d_ff` | Step 6 (SwiGLU row) |
| Wrong from **layer 1**, attention-shaped | attention scale, GQA repeat method, or packed-QKV split | Step 5 + Step 6; [[Gotchas - Implementing Attention]] |
| Off by a constant "shift" on **all positions** | BOS/special-token or tokenizer mismatch | Step 2 |
| Matches in fp32, differs only in **bf16** | not a bug — accumulation order / kernel | accept it; compare in fp32 only |

## Connections

- [[Concept - Rotary Position Embeddings (RoPE)]] — the interleaved-vs-half ordering and base-θ mismatches that are the top long-context divergence causes.
- [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]] — the norm epsilon and placement details behind the "diff grows with depth" signature.
- [[Gotchas - Implementing Attention]] — the reshape, scale, mask, and GQA-repeat bugs this playbook is designed to localize.
- [[Snippet - RoPE Implementation]] — the concrete `rotate_half` code whose convention you must match, down-link to the exact mechanism.
- [[Concept - Floating Point for Deep Learning]] — why bf16 comparisons are meaningless and TF32 must be disabled; the foundation this whole procedure rests on.
- [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — the head-sharing schemes whose KV-repeat and packed-projection layouts are a top silent bug in step 5.
- [[Deep Dive - FlashAttention]] — the kernel whose numerics legitimately differ from eager attention, so you know which mismatches to ignore.
- [[Reference - Transformer Architecture Cheat Sheet]] — the config numbers to reconcile against; a wrong `d_ff` or head count here is often the root cause.

## Sources

- HuggingFace Transformers model-conversion scripts (`convert_*_to_hf.py`) — the canonical worked examples of weight-name mapping and packed-QKV splitting; read one before porting.
- Su et al. (2021) — *RoFormer.* The RoPE definition; the interleaved reference ordering that HF's `rotate_half` deviates from, the single most common port bug.
- NVIDIA TF32 documentation — the Ampere/Hopper reduced-precision matmul mode that produces the phantom `1e-3` mismatch step 1 disables. (Folklore, strongly held: "always disable TF32 before you trust a numerical diff.")
