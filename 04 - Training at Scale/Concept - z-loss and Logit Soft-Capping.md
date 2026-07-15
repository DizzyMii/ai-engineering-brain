---
tags: [concept, domain/training-at-scale, level/unicorn]
aliases: [z-loss, zloss, logit soft-capping, softcap, log-partition regularization, router z-loss]
summary: "Auxiliary-loss and tanh tricks that pin the softmax log-partition near zero to keep pre-softmax logits numerically well-conditioned in bf16."
---

# Concept - z-loss and Logit Soft-Capping

> **One-paragraph hook:** Cross-entropy does not care how big your logits are — only about their differences — so the absolute scale of the pre-softmax logit vector is an unconstrained degree of freedom that random-walks upward over a long run until, one day, an attention logit crosses ~11 and the fp16 `exp` overflows, or the output softmax saturates and the gradient goes to zero. z-loss and logit soft-capping are the two cheap tricks frontier teams bolt on to pin that free direction: z-loss (PaLM) penalizes the log-partition function, soft-capping (Gemma 2) hard-bounds the logits through a `tanh`. Both are unicorn-tier because the *why* — a gauge freedom in the loss — is almost never written down, and the *cost* — soft-capping silently breaks [[Deep Dive - FlashAttention]] — is learned the hard way.

## The mechanism

Start from the loss. For a target token $y$ with logit vector $z \in \mathbb{R}^V$, the [[Concept - Softmax]] cross-entropy is

$$\mathcal{L}_{CE} = -\log \frac{e^{z_y}}{\sum_i e^{z_i}} = -z_y + \log Z, \qquad Z = \sum_i e^{z_i},$$

where $\log Z = \operatorname{logsumexp}(z)$ is the **log-partition function** (see [[Snippet - The Log-Sum-Exp Trick]] for the numerically stable form). The critical property: softmax is invariant to a constant shift, $z \mapsto z + c\mathbf{1}$ leaves every probability unchanged, so $\mathcal{L}_{CE}$ depends only on the *differences* $z_y - z_j$. The common-mode component of the logits — their overall offset and, more loosely, their overall magnitude — is a **gauge freedom**: cross-entropy exerts no pressure on it whatsoever. Under SGD noise this unconstrained direction drifts, and it tends to drift *up*, because larger logits sharpen a correct prediction's margin at second order while [[Concept - AdamW at Scale]]'s weight decay only weakly opposes the unembedding-matrix growth that produces it.

**z-loss** (PaLM, Chowdhery et al. 2022) is a gauge-fixing term. Add

$$\mathcal{L}_{z} = \alpha \,(\log Z)^2, \qquad \alpha \approx 10^{-4},$$

which pushes $\log Z \to 0$, i.e. $Z \to 1$. Because $\log Z \approx \max_i z_i$ for a peaked distribution, penalizing $(\log Z)^2$ directly bounds the largest logit's magnitude without touching the differences that carry the actual prediction. It is nearly free — one reduction over the vocab you already computed for the softmax — and it reappears verbatim as **router z-loss** in Mixture-of-Experts (ST-MoE, Zoph et al. 2022; coefficient ~$10^{-3}$) applied to the router logits, for exactly the same reason: see [[Concept - MoE Training and Load Balancing]].

**Logit soft-capping** (Gemma 2, 2024) takes the hard-bound route instead of a soft penalty:

$$z \leftarrow \tau \cdot \tanh(z / \tau).$$

`tanh` is monotonic, so it preserves the ordering (and therefore the argmax and the ranking) of the logits, is ~linear for $|z| \ll \tau$, and asymptotes to $\pm\tau$ for large $|z|$. Gemma 2 used $\tau = 30$ on the **final** logits and $\tau = 50$ on the **attention** logits (the $QK^\top/\sqrt{d}$ scores, before the attention softmax — see [[Concept - Attention Mechanism]]). Nothing can exceed $\tau$ in magnitude, so overflow and saturation are structurally impossible.

Why either is needed comes down to the exponential. bf16 and fp32 both overflow at $\approx 3.4\times10^{38} = e^{88.7}$, so a logit near ~89 overflows a raw `exp`; fp16's max is only $65504 = e^{11.09}$, so an fp16 attention logit of ~12 overflows. The log-sum-exp max-subtraction trick handles the *final* normalization, but intermediate accumulations, the gradient $\partial \mathcal{L}/\partial z_i = p_i - \mathbb{1}[i=y]$ (which vanishes as $p$ saturates one-hot, stalling learning), and every un-shifted `exp` inside a fused kernel remain exposed. Keeping the raw magnitudes small via z-loss or capping is what keeps the whole pre-softmax distribution in a conditioned range under [[Concept - Mixed Precision Training]].

## In practice

- **z-loss coefficient**: $10^{-4}$ is the PaLM value and the de-facto default for output z-loss; $10^{-3}$ for MoE router z-loss (ST-MoE). It is cheap enough that many teams enable it unconditionally on large bf16 runs as insurance, not as a reaction to a spike.
- **Soft-cap values**: Gemma 2 shipped $\tau=30$ (final), $\tau=50$ (attention). These are the only widely published cap constants; treat them as reasonable starting points, not universal.
- **The third door — QK-norm**: normalizing $Q$ and $K$ before the dot product ([[Concept - Attention Logit Stabilization (QK-Norm and Soft-Capping)]], used by ViT-22B/Dehghani et al. 2023 and OLMo-2) bounds attention logits *structurally* — a unit-norm $q\cdot k$ can't exceed $\sqrt{d}$ times the learned scale — and composes cleanly with fused attention, unlike attention soft-capping. The design space is one question, "how do you keep logits bounded?", with three answers: a soft penalty (z-loss), a hard `tanh` clamp (soft-cap), or a structural normalization (QK-norm).
- **Where they sit in the stack**: z-loss is one of the standing stabilizers in [[Concept - Training Stability and Loss Spikes]]; when a live run diverges, enabling z-loss + QK-norm is a step in the recovery ([[Playbook - Debugging a Diverging Training Run]]).

## Failure modes

- **z-loss coefficient too high**: at $\alpha \gtrsim 10^{-3}$ on the output softmax the $(\log Z)^2$ term starts to fight the LM objective, flattening the logit distribution and raising the actual cross-entropy — you regularized past the point of stabilizing. Detection: the auxiliary z-loss term is a meaningful fraction of total loss, and eval perplexity worsens versus a low-$\alpha$ control.
- **Attention soft-capping breaks FlashAttention**: the fused kernel never materializes the full $N\times N$ score matrix — it streams tiles through SRAM with an online softmax — so inserting a `tanh` on the scores means either writing a custom kernel or falling off the fast path onto an $O(N^2)$ HBM materialization. This is not hypothetical: Gemma 2 launched with attention soft-capping, found it incompatible with the standard FlashAttention/vLLM path, and **later Gemma versions dropped attention soft-capping for kernel compatibility**, relying on QK-norm-style bounding instead. The throughput hit, not the math, killed it.
- **Capping as a symptom mask**: a hard `tanh` clamp will happily hide a genuinely broken LR schedule or a corrupted data shard — the logits stay bounded, the loss curve looks clean, and the underlying instability (see [[Lore - The Loss Spike Chronicles]]) trains on undetected. Capping bounds the *consequence* of large logits; it does not diagnose *why* they grew.

## The non-obvious

The gauge argument is the whole point and is almost never stated: because cross-entropy is invariant to a common shift of all logits, the overall logit scale is a flat, unconstrained direction in loss space that nothing pins down until it wanders into a numerically dangerous regime — z-loss is, precisely, a term that fixes that gauge. This reframes "logit blow-up" from a mysterious instability into an expected consequence of leaving a zero-gradient degree of freedom unregularized, and it explains why the fix is so cheap and so reliable: you are not fighting the optimization, you are adding the one constraint the loss forgot to specify. The corollary that bites teams: the same unbounded-logit dynamic is what produces [[Concept - Attention Entropy Collapse]] on the *attention* softmax, so a run can be perfectly stable at the output layer (z-loss on) and still diverge through the attention logits (no QK-norm, no cap) — the two softmaxes are separate gauges and each needs its own fix.

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
