---
tags: [concept, domain/training-at-scale, level/unicorn]
aliases: [z-loss, zloss, logit soft-capping, softcap, log-partition regularization, router z-loss]
summary: "Auxiliary-loss and tanh tricks that pin the softmax log-partition near zero to keep pre-softmax logits numerically well-conditioned in bf16."
---

# Concept - z-loss and Logit Soft-Capping

> **One-paragraph hook:** Cross-entropy only cares about differences between logits, not their size. So the absolute scale of the pre-softmax logit vector is an unconstrained degree of freedom, and over a long run it random-walks upward until one day an attention logit crosses ~11 and the fp16 `exp` overflows, or the output softmax saturates and the gradient goes to zero. z-loss and logit soft-capping are the two cheap tricks frontier teams bolt on to pin that free direction. z-loss (PaLM) penalizes the log-partition function; soft-capping (Gemma 2) hard-bounds the logits through a `tanh`. Both are unicorn-tier because the *why* (a gauge freedom in the loss) almost never gets written down, and the *cost* gets learned the hard way: soft-capping silently breaks [[Deep Dive - FlashAttention]].

## The mechanism

Start from the loss. For a target token $y$ with logit vector $z \in \mathbb{R}^V$, the [[Concept - Softmax]] cross-entropy is

$$\mathcal{L}_{CE} = -\log \frac{e^{z_y}}{\sum_i e^{z_i}} = -z_y + \log Z, \qquad Z = \sum_i e^{z_i},$$

where $\log Z = \operatorname{logsumexp}(z)$ is the **log-partition function** (the numerically stable form is in [[Snippet - The Log-Sum-Exp Trick]]). Softmax is invariant to a constant shift: $z \mapsto z + c\mathbf{1}$ leaves every probability unchanged, so $\mathcal{L}_{CE}$ depends only on the *differences* $z_y - z_j$. The common-mode component of the logits (their overall offset and, more loosely, their overall magnitude) is a **gauge freedom**. Cross-entropy puts no pressure on it at all. Under SGD noise that direction drifts, and it tends to drift *up*: larger logits sharpen a correct prediction's margin at second order, and [[Concept - AdamW at Scale]]'s weight decay only weakly opposes the unembedding-matrix growth behind them.

**z-loss** (PaLM, Chowdhery et al. 2022) fixes the gauge. Add

$$\mathcal{L}_{z} = \alpha \,(\log Z)^2, \qquad \alpha \approx 10^{-4},$$

which pushes $\log Z \to 0$, i.e. $Z \to 1$. For a peaked distribution $\log Z \approx \max_i z_i$, so penalizing $(\log Z)^2$ bounds the largest logit's magnitude directly and leaves alone the differences that carry the prediction. It's nearly free, one reduction over a vocab you already computed for the softmax. The same term shows up as **router z-loss** in Mixture-of-Experts (ST-MoE, Zoph et al. 2022; coefficient ~$10^{-3}$), applied to router logits for the same reason; see [[Concept - MoE Training and Load Balancing]].

**Logit soft-capping** (Gemma 2, 2024) uses a hard bound instead of a soft penalty:

$$z \leftarrow \tau \cdot \tanh(z / \tau).$$

`tanh` is monotonic, so the ordering of the logits (and with it the argmax and ranking) survives. It's ~linear for $|z| \ll \tau$ and asymptotes to $\pm\tau$ for large $|z|$. Gemma 2 used $\tau = 30$ on the **final** logits and $\tau = 50$ on the **attention** logits, the $QK^\top/\sqrt{d}$ scores before the attention softmax ([[Concept - Attention Mechanism]]). Nothing can exceed $\tau$ in magnitude, so overflow and saturation can't happen by construction.

Both exist because of the exponential. bf16 and fp32 overflow at $\approx 3.4\times10^{38} = e^{88.7}$, so a logit near ~89 overflows a raw `exp`. fp16 tops out at $65504 = e^{11.09}$, so an fp16 attention logit of ~12 overflows. Max-subtraction in log-sum-exp covers the *final* normalization. It doesn't cover intermediate accumulations, the gradient $\partial \mathcal{L}/\partial z_i = p_i - \mathbb{1}[i=y]$ (which vanishes as $p$ saturates to one-hot and stalls learning), or any un-shifted `exp` inside a fused kernel. Keeping raw magnitudes small with z-loss or capping keeps the whole pre-softmax distribution in a well-conditioned range under [[Concept - Mixed Precision Training]].

## In practice

- **z-loss coefficient**: $10^{-4}$ is the PaLM value and the de-facto default for output z-loss; MoE router z-loss uses $10^{-3}$ (ST-MoE). It's cheap enough that many teams turn it on unconditionally for large bf16 runs, as insurance before any spike.
- **Soft-cap values**: Gemma 2 shipped $\tau=30$ (final) and $\tau=50$ (attention). They're the only widely published cap constants: reasonable starting points, not universal.
- **QK-norm, the third option**: normalizing $Q$ and $K$ before the dot product ([[Concept - Attention Logit Stabilization (QK-Norm and Soft-Capping)]], used by ViT-22B/Dehghani et al. 2023 and OLMo-2) bounds attention logits by construction, since a unit-norm $q\cdot k$ can't exceed $\sqrt{d}$ times the learned scale. Unlike attention soft-capping, it composes cleanly with fused attention. So there's one question, "how do you keep logits bounded?", and three answers: a soft penalty (z-loss), a hard `tanh` clamp (soft-cap), or normalization (QK-norm).
- **Where they sit**: z-loss is one of the standing stabilizers in [[Concept - Training Stability and Loss Spikes]]. When a live run diverges, turning on z-loss + QK-norm is one recovery step ([[Playbook - Debugging a Diverging Training Run]]).

## Failure modes

- **z-loss coefficient too high**: at $\alpha \gtrsim 10^{-3}$ on the output softmax, the $(\log Z)^2$ term starts fighting the LM objective. It flattens the logit distribution and raises the actual cross-entropy; you've regularized past the point of stabilizing. Symptoms: the auxiliary z-loss term is a meaningful fraction of total loss, and eval perplexity is worse than a low-$\alpha$ control.
- **Attention soft-capping breaks FlashAttention**: the fused kernel never materializes the full $N\times N$ score matrix. It streams tiles through SRAM with an online softmax, so a `tanh` on the scores means writing a custom kernel or falling off the fast path onto an $O(N^2)$ HBM materialization. This happened: Gemma 2 launched with attention soft-capping, found it incompatible with the standard FlashAttention/vLLM path, and **later Gemma versions dropped attention soft-capping for kernel compatibility**, bounding with QK-norm-style methods instead. The throughput hit killed it, not the math.
- **Capping as a symptom mask**: a hard `tanh` clamp will happily hide a broken LR schedule or a corrupted data shard. The logits stay bounded, the loss curve looks clean, and the underlying instability (see [[Lore - The Loss Spike Chronicles]]) keeps training undetected. Capping bounds the *consequence* of large logits and says nothing about *why* they grew.

## The non-obvious

The gauge argument is the point, and it's almost never stated. Cross-entropy is invariant to a common shift of all logits, so overall logit scale is a flat direction in loss space that nothing pins down until it wanders somewhere numerically dangerous. z-loss is a term that fixes that gauge. "Logit blow-up" is then the expected result of leaving a zero-gradient degree of freedom unregularized, not a mysterious instability. That's also why the fix is so cheap and reliable: it adds the one constraint the loss left out.

The corollary that bites teams: the same unbounded-logit dynamic produces [[Concept - Attention Entropy Collapse]] on the *attention* softmax. A run can be perfectly stable at the output layer (z-loss on) and still diverge through the attention logits (no QK-norm, no cap). The two softmaxes are separate gauges and each needs its own fix.

## Connections
- [[Concept - Training Stability and Loss Spikes]] — z-loss and soft-capping are two of the standing stabilizers cataloged there; this note is the depth treatment of the output-logit half.
- [[Concept - Softmax]] — the shift-invariance and the $p_i - \mathbb{1}[i=y]$ gradient that motivate the whole trick live in the softmax definition.
- [[Concept - MoE Training and Load Balancing]] — router z-loss is the same $(\log Z)^2$ penalty applied to routing logits to keep the expert-selection softmax numerically sane.
- [[Concept - Mixed Precision Training]] — the fp16/bf16 `exp` overflow thresholds are exactly why bounding raw logit magnitude matters, rather than trusting the log-sum-exp shift alone.
- [[Deep Dive - FlashAttention]] — the reason attention soft-capping is expensive: the fused kernel never materializes the scores, so a per-score `tanh` forces a custom kernel or the slow path.
- [[Concept - Attention Mechanism]] — attention soft-capping and QK-norm act on the pre-softmax $QK^\top/\sqrt{d}$ scores defined here.
- [[Concept - Attention Logit Stabilization (QK-Norm and Soft-Capping)]] — QK-norm is the structural, kernel-friendly third option in the same "keep logits bounded" design space.
- [[Concept - Attention Entropy Collapse]] — the attention-side failure that the same unbounded-logit dynamic produces, showing why the output and attention softmaxes are separate gauges.
- [[Snippet - The Log-Sum-Exp Trick]] — the stable evaluation of $\log Z$ that z-loss regularizes, and the max-subtraction that handles final normalization but not intermediate `exp`s.
- [[Lore - The Loss Spike Chronicles]] — the war stories where z-loss and QK-norm entered standard practice as scar tissue from real divergences.
- [[Concept - AdamW at Scale]] — weight decay on the unembedding only weakly opposes the logit-scale drift that z-loss fixes directly; the two interact in stabilizing a run.
- [[Playbook - Debugging a Diverging Training Run]] — enabling z-loss and QK-norm is a concrete recovery action there; this note is the mechanism behind that step.

## Sources
- Chowdhery et al. (2022) — "PaLM: Scaling Language Modeling with Pathways" — introduces output-softmax z-loss with $\alpha = 10^{-4}$ as a stabilizer for a 540B bf16 run and documents its effect on logit-scale drift.
- Zoph et al. (2022) — "ST-MoE: Designing Stable and Transferable Sparse Expert Models" — router z-loss ($\sim 10^{-3}$) on routing logits, the MoE analogue used to stabilize expert selection.
- Gemma Team (2024) — "Gemma 2: Improving Open Language Models at a Practical Size" — final ($\tau=30$) and attention ($\tau=50$) logit soft-capping via `tanh`, and the practical FlashAttention-incompatibility that later drove its removal.
- Dehghani et al. (2023) — "Scaling Vision Transformers to 22 Billion Parameters" — QK-layernorm, the structural alternative that bounds attention logits without a per-score nonlinearity.
