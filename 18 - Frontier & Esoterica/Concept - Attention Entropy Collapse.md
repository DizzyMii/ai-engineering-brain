---
tags: [concept, domain/esoterica, level/frontier]
aliases: [entropy collapse, attention logit explosion, QK-norm]
summary: "Training instability where attention softmaxes sharpen to one-hot, entropy crashes to zero, and loss diverges — fixed by QK-norm, σReparam, or logit soft-capping."
---

# Concept - Attention Entropy Collapse

> **One-paragraph hook:** A few hundred steps before a large transformer's loss blows up, a handful of attention heads stop attending. Their softmax distributions collapse toward one-hot, per-head attention entropy falls to near zero, and the head becomes a saturated dead end that can't be trained. This is *attention entropy collapse*: a self-reinforcing runaway in the query/key dot products, not a random cosmic-ray loss spike. It's one of the main reasons naive bf16 pretraining is fragile at scale. The fixes, [[Concept - Attention Logit Stabilization (QK-Norm and Soft-Capping)|QK-normalization]] and logit soft-capping, are now standard architecture furniture in models like ViT-22B and Gemma 2.

## The mechanism

An [[Concept - Attention Mechanism|attention]] head computes logits $\ell_{ij} = \frac{q_i \cdot k_j}{\sqrt{d_h}}$ and turns them into weights $p_{ij}$ with [[Concept - Softmax|softmax]]. The health metric is row entropy:

$$H_i = -\sum_j p_{ij}\log p_{ij}, \qquad 0 \le H_i \le \log(i)$$

A uniform head over $n$ visible keys has $H = \log n$; a one-hot head has $H = 0$. Collapse is $H_i \to 0$.

What drives it is unbounded logit growth. Nothing in the vanilla block bounds $\|q_i\|$ or $\|k_j\|$. As training pushes the query/key projections to sharpen a useful head, logits scale roughly with $\|q\|\,\|k\|$ and can grow without limit. Once the max logit is large (say $\gtrsim 30$–$50$), softmax saturates: one weight $\approx 1$, the rest $\approx 0$. Two things then break together:

1. **Gradient starvation.** The softmax Jacobian is $\partial p_i/\partial \ell = \mathrm{diag}(p) - pp^\top$. When $p$ is one-hot that's $\approx 0$, so almost no gradient reaches $q$ and $k$. The head can't correct itself; it's stuck where it collapsed.
2. **Curvature explosion.** The loss surface around a saturated softmax is sharp. One optimizer step in bf16 (with its ~3-decimal-digit mantissa) can overshoot and feed an even larger logit into the next step. It's a positive feedback loop, an entropy *runaway*, and mechanistically different from a one-off gradient-norm spike.

Zhai et al. 2023 ("Stabilizing Transformer Training by Preventing Attention Entropy Collapse", Apple) named the phenomenon, showed the tight empirical link between collapsing entropy and divergence, and traced the cause to the spectral norm of the attention weight matrices growing during training. Their fix, **σReparam**, reparameterizes each weight as $\hat W = \frac{\gamma}{\sigma(W)}W$, where $\sigma(W)$ is the spectral norm (estimated by power iteration) and $\gamma$ is a single learned scalar. That bounds how fast logits can grow and leaves one degree of freedom to rescale.

Two blunter, cheaper fixes dominate in practice:

- **QK-normalization.** Apply [[Concept - RMSNorm and LayerNorm|RMSNorm/LayerNorm]] to $q$ and $k$ *before* the dot product. That pins $\|q\|,\|k\|$ to a learned scale, so $\ell_{ij}$ is bounded by construction. Dehghani et al. 2023 needed it to train **ViT-22B**, and it's now common in language models.
- **Logit soft-capping.** Squash logits through $\ell \mapsto t\cdot\tanh(\ell/t)$, which is near-identity for $|\ell|\ll t$ and asymptotes to $\pm t$. **Gemma 2** (2024) caps attention logits at $t\approx 50$ and final logits at $t\approx 30$. It's a hard ceiling with no parameters.

## In practice

The knobs, with the numbers people actually use:

| Fix | Where applied | Cost | Real users |
|---|---|---|---|
| QK-norm (RMSNorm on q,k) | Before $q\cdot k$ | 2 small norms/head, negligible FLOPs | ViT-22B, many 2024+ LLMs |
| Logit soft-cap $t\tanh(\cdot/t)$ | Attn logits & final logits | 1 tanh, breaks Flash fusion unless kernel supports it | Gemma 2 ($t=50/30$) |
| σReparam | All attention weight matrices | power iteration per step | Zhai et al. 2023 ViTs |
| z-loss | Final softmax | scalar reg term | PaLM; the output-side cousin, see [[Concept - z-loss and Logit Soft-Capping]] |

QK-norm and soft-capping aren't mutually exclusive, but they're usually redundant, so pick one. Soft-capping fights [[Deep Dive - FlashAttention|FlashAttention]]-style fused kernels because the cap sits *inside* the softmax; vanilla flash-attn had to be patched to serve Gemma 2. QK-norm is easier to live with because it acts on $q,k$ before the kernel.

It's also a preventable way for a [[Deep Dive - Anatomy of a Pretraining Run|pretraining run]] to fail. A run that dies at step 8,300 with a loss spike often shows entropy on one or two heads sliding toward zero from step ~8,000. The standard recovery is to add QK-norm and restart from the last good checkpoint.

## Failure modes

- **The signature.** Per-layer attention entropy plummets on a few heads a few hundred steps *before* the visible loss spike, while max attention logit climbs monotonically over the same window. Watch only loss and grad-norm and you see the crash but not the cause.
- **Silent low-precision fragility.** In bf16/fp8, large logits round-trip through a coarse mantissa, and collapse comes earlier and harder than in fp32. That's a big reason [[Concept - Mixed Precision Training|mixed-precision]] runs at scale carry these guards.
- **Outlier-driven.** [[Concept - Massive Activations and Outlier Features|Massive activations]] in a few query/key channels are frequently what inflates $\|q\|,\|k\|$. The collapse and the outlier are one disease seen from two sides.
- **Detection recipe.** Log `attn_entropy` (mean and min over heads) and `max_attn_logit` per layer every N steps. A min-head entropy trending below ~0.5 nats, or a max logit above ~30 and rising, is your early-warning tripwire, and it's cheaper than a failed run.

## The non-obvious

**A sharp, confident head isn't a healthy head.** The instinct is that low entropy means the head "learned something decisive." But near-one-hot attention is where gradients vanish and runs die. The useful regime is *moderately* peaked, short of saturation. So the fixes don't try to *lower* entropy (sharp heads already do that); they *stop* it from bottoming out.

It also changes how to read [[Concept - Attention Sinks|attention sinks]]. Dumping mass on the BOS token is partly the model's own pressure valve: it keeps some entropy alive by giving heads a place to "attend to nothing" without collapsing. Remove the sink (with aggressive KV eviction, say) and you can *induce* the collapse the sink was preventing.

## Connections
- [[Concept - Massive Activations and Outlier Features]] — outlier query/key channels are the concrete driver of the unbounded logit growth; same disease, different lens.
- [[Concept - RMSNorm and LayerNorm]] — QK-norm is just this normalizer applied to q and k, the cheapest fix.
- [[Concept - Attention Mechanism]] — collapse is a pathology of the q·k/√d softmax at its core.
- [[Concept - Softmax]] — the saturation and vanishing-Jacobian behavior is a property of softmax itself.
- [[Concept - Attention Logit Stabilization (QK-Norm and Soft-Capping)]] — the unicorn-level treatment of the exact stabilization tricks named here.
- [[Concept - Mixed Precision Training]] — why bf16/fp8 makes the runaway arrive earlier and harder.
- [[Concept - Attention Sinks]] — sinks act as a homeostatic entropy valve; removing them can trigger collapse.
- [[Concept - Training Stability and Loss Spikes]] — entropy collapse is one named member of the loss-spike family, with a specific detectable precursor.
- [[Deep Dive - Anatomy of a Pretraining Run]] — where you actually monitor entropy and recover a dying run.
- [[Deep Dive - FlashAttention]] — soft-capping sits inside the softmax and breaks naive fused kernels, so flash-attn needs patching to serve capped models.
- [[Concept - z-loss and Logit Soft-Capping]] — the output-softmax analogue: the same logit-growth control applied at the final layer.
- [[Reference - Architecture Numerology]] — the soft-cap constants (t≈50/30) and head-dim scaling live in the magic-constants table.

## Sources
- Zhai et al. (2023) — *Stabilizing Transformer Training by Preventing Attention Entropy Collapse*. Names the phenomenon, ties it to spectral norm growth, introduces σReparam.
- Dehghani et al. (2023) — *Scaling Vision Transformers to 22 Billion Parameters*. QK-norm as the load-bearing stability fix at 22B.
- Gemma Team, Google DeepMind (2024) — *Gemma 2*. Attention and final-logit soft-capping with $t=50/30$ in a production model.
