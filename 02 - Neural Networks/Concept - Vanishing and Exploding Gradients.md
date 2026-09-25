---
tags: [concept, domain/neural-networks, level/advanced]
aliases: [vanishing gradients, exploding gradients, gradient pathologies]
summary: "Gradients scale as a product of per-layer Jacobians — exponential in depth — and the fix stack: init, norm, residuals, clipping, gating."
---

# Concept - Vanishing and Exploding Gradients

> **One-paragraph hook:** Backprop multiplies one Jacobian per layer, and a product of a hundred matrices is an exponential amplifier. Singular values slightly below 1 send early-layer gradients to zero; slightly above 1 sends them to Inf. That one multiplicative fact is why deep nets and vanilla RNNs didn't train before ~2010. Every fix that made modern depth possible (variance-preserving init, ReLU, normalization, residual connections, clipping, gating) attacks the same product. Read per-layer gradient norms and you can diagnose most "my model won't train" incidents from one plot.

## The mechanism

[[Concept - Backpropagation]] computes the gradient at layer 0 as a chained product of local Jacobians:

$$\frac{\partial L}{\partial h_0} = \left(\prod_{l=1}^{L} J_l\right)^{\!\top} \frac{\partial L}{\partial h_L}, \qquad J_l = \frac{\partial h_l}{\partial h_{l-1}}$$

The norm obeys $\lVert \prod_l J_l \rVert \le \prod_l \lVert J_l \rVert_2$. If each layer's spectral norm sits near a common value $s$, the gradient scales like $s^L$: $s=0.9$ at depth 100 gives $0.9^{100} \approx 2.7\times10^{-5}$, and $s=1.1$ gives $\approx 1.4\times10^4$. No single layer is broken. The product is. In an RNN the *same* weight matrix repeats across $T$ timesteps, so its spectral radius governs the behavior: $\rho(W) < 1$ vanishes, $\rho(W) > 1$ explodes, and $T$ plays the role of depth. Pascanu et al. 2013 formalized both conditions and proposed the clipping fix.

Saturating nonlinearities make it worse. Each Jacobian factors as $J_l = \mathrm{diag}(\phi'(z_l))\, W_l$. Sigmoid's derivative peaks at 0.25 and tanh's at 1.0, and both decay to zero in the tails (see [[Concept - Activation Functions]]). A sigmoid stack multiplies in a factor $\le 0.25$ per layer *on top of* whatever the weights do. That capped depth at a handful of layers pre-2010, identified in Hochreiter's 1991 thesis and, for recurrence, by Bengio et al. 1994.

## In practice

The modern fix stack, and what each piece does to the product:

| Fix | Effect on $\prod J_l$ |
|---|---|
| Variance-preserving [[Concept - Weight Initialization]] | sets each $\lVert J_l \rVert \approx 1$ at step 0 |
| ReLU-family activations | derivative is 0 or 1 — no saturation tax on the product |
| [[Concept - RMSNorm and LayerNorm]] | re-scales activations every layer, keeping Jacobians conditioned *throughout training* as well as at init |
| [[Concept - Residual Connections]] | changes each factor to $I + F'$ — an additive identity path the product cannot kill |
| Global-norm gradient clipping (max-norm ~1.0) | caps the update when the product transiently spikes |
| Gating (LSTM/GRU) | an additive cell state with learned gates ≈ a residual connection through time |

Residuals are the strongest entry. They don't *remove* bad Jacobians; they add an identity term, so $\prod_l (I + F_l')$ expands to $I + \sum_l F_l' + \dots$ and the gradient always has a direct, unattenuated path to layer 0, even when every $F_l' \approx 0$. That's why ResNets train at 1000+ layers. Gating in [[Concept - Recurrent Networks and the LSTM]] is the same idea, found a decade earlier, applied to time instead of depth. Modern [[Concept - State Space Models and Mamba]] go after the recurrent version directly by parameterizing the state transition so its eigenvalues stay controllably inside the unit circle.

Clipping goes after `backward()` and before `step()` in [[Concept - The Training Loop]], and under mixed precision you unscale first.

Detection is cheap. Log per-layer gradient norms (a hook per parameter group, every N steps). In healthy training they stay within roughly an order of magnitude across depth. Vanishing shows up as early-layer norms 3–6 orders of magnitude below late-layer norms while loss crawls. Exploding shows up as NaN/Inf loss or spikes in the global grad norm. In large-model practice those spikes cluster at the LR-warmup boundary, where the step size ramps into curvature the model hasn't adapted to yet ([[Concept - Training Stability and Loss Spikes]] covers this).

## Failure modes

- **Vanishing:** loss plateaus near its init value; early layers' weights barely move from init (check the weight-update-to-weight-norm ratio, healthy ≈ 1e-3 per step); the grad-norm profile decays geometrically toward the input. Remedies, most likely first: fix init, replace saturating activations, add or repair normalization, add residuals.
- **Exploding:** loss spikes or NaNs, often suddenly after a healthy stretch. First response: global-norm clipping plus a lower peak LR or longer warmup. Then find the underlying cause; don't live on clipping forever.
- **The RNN special case:** long sequences vanish even with perfect init, because the same $W$ repeats $T$ times. The fix is architectural (gating, truncated BPTT, or an SSM); a better constant won't do it.
- **Misdiagnosis trap:** a disconnected graph (an accidental `.detach()`, an in-place op) gives all-zero early gradients that look like severe vanishing. [[Playbook - Debugging a Neural Network That Won't Train]] orders the checks so you rule this out before touching architecture.

## The non-obvious

In transformers, exploding gradients usually don't come from the FFN stack the classical theory worries about. They come in through **attention logits**. The $q^\top k$ products grow as weights grow during training, large logits saturate softmax, and the mix of near-argmax attention and rare large-gradient events produces the spike-prone loss surface seen in LLM pretraining. So the mitigations that work are logit-level ([[Concept - z-loss and Logit Soft-Capping]], QK-norm) plus clipping and warmup, and another init tweak won't help. If a 30-layer transformer NaNs at step 8,000 of warmup, check attention-logit magnitudes before fan-in constants.

## Connections

- [[Concept - Backpropagation]] — the chain-rule product that creates the multiplicative pathology in the first place.
- [[Concept - Weight Initialization]] — the step-0 fix: set every Jacobian's scale to ~1 before training starts.
- [[Concept - Activation Functions]] — saturating derivatives (sigmoid ≤ 0.25) are a per-layer multiplicative tax; ReLU removed it.
- [[Concept - RMSNorm and LayerNorm]] — the during-training fix: re-conditions activations and Jacobians every layer, every step.
- [[Concept - Residual Connections]] — the strongest structural fix: the $I + F'$ identity path that makes 1000-layer training possible.
- [[Concept - The Training Loop]] — where gradient clipping actually lives, and the unscale-before-clip ordering under mixed precision.
- [[Concept - Recurrent Networks and the LSTM]] — gating as the residual-through-time solution to the recurrent version of the problem.
- [[Concept - State Space Models and Mamba]] — modern sequence models that solve recurrence stability by construction, parameterizing eigenvalue decay explicitly.
- [[Concept - Training Stability and Loss Spikes]] — the at-scale manifestation: spike clusters at warmup boundaries and the operational response.
- [[Concept - z-loss and Logit Soft-Capping]] — the transformer-specific mitigation for the attention-logit explosion channel.
- [[Playbook - Debugging a Neural Network That Won't Train]] — the diagnostic procedure that separates true gradient pathology from severed-graph impostors.

## Sources

- Hochreiter (1991) — Untersuchungen zu dynamischen neuronalen Netzen. The original identification of vanishing gradients in deep/recurrent nets.
- Bengio et al. (1994) — Learning long-term dependencies with gradient descent is difficult. The formal argument for recurrence.
- Pascanu et al. (2013) — On the difficulty of training recurrent neural networks. Spectral-radius conditions and gradient clipping.
- Hochreiter & Schmidhuber (1997) — Long Short-Term Memory. Gating as the architectural fix through time.
- He et al. (2016) — Identity Mappings in Deep Residual Networks. The clean-identity-path analysis behind 1000-layer training.
