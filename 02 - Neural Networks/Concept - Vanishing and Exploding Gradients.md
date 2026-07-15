---
tags: [concept, domain/neural-networks, level/advanced]
aliases: [vanishing gradients, exploding gradients, gradient pathologies]
summary: "Gradients scale as a product of per-layer Jacobians — exponential in depth — and the fix stack: init, norm, residuals, clipping, gating."
---

# Concept - Vanishing and Exploding Gradients

> **One-paragraph hook:** Backprop multiplies a Jacobian per layer, and a product of a hundred matrices is an exponential amplifier: singular values slightly below 1 send early-layer gradients to zero, slightly above 1 send them to Inf. This single multiplicative fact is why deep nets and vanilla RNNs simply did not train before ~2010, and every fix that made modern depth possible — variance-preserving init, ReLU, normalization, residual connections, clipping, gating — is an attack on the same product. If you can read per-layer gradient norms, you can diagnose most "my model won't train" incidents in one plot.

## The mechanism

[[Concept - Backpropagation]] computes the gradient at layer 0 as a chained product of local Jacobians:

$$\frac{\partial L}{\partial h_0} = \left(\prod_{l=1}^{L} J_l\right)^{\!\top} \frac{\partial L}{\partial h_L}, \qquad J_l = \frac{\partial h_l}{\partial h_{l-1}}$$

The norm obeys $\lVert \prod_l J_l \rVert \le \prod_l \lVert J_l \rVert_2$: if each layer's spectral norm sits near a common value $s$, the gradient scales like $s^L$. Concretely, $s=0.9$ at depth 100 gives $0.9^{100} \approx 2.7\times10^{-5}$; $s=1.1$ gives $\approx 1.4\times10^4$. Nothing is "wrong" with any single layer — the pathology is emergent from the product. In an RNN the *same* weight matrix repeats across $T$ timesteps, so the behavior is governed by its spectral radius: $\rho(W) < 1$ vanishes, $\rho(W) > 1$ explodes, and $T$ plays the role of depth (Pascanu et al. 2013 formalized both conditions and proposed the clipping fix).

Saturating nonlinearities compound this. Each Jacobian factors as $J_l = \mathrm{diag}(\phi'(z_l))\, W_l$, and sigmoid's derivative peaks at 0.25, tanh's at 1.0, both decaying to zero in the tails (see [[Concept - Activation Functions]]). A sigmoid stack therefore multiplies in a factor $\le 0.25$ per layer *on top of* whatever the weights do — the mechanistic reason depth was walled at a handful of layers pre-2010, identified by Hochreiter's 1991 thesis and Bengio et al. 1994 for recurrence.

## In practice

The modern fix stack, and what each element does to the product:

| Fix | Effect on $\prod J_l$ |
|---|---|
| Variance-preserving [[Concept - Weight Initialization]] | sets each $\lVert J_l \rVert \approx 1$ at step 0 |
| ReLU-family activations | derivative is 0 or 1 — no saturation tax on the product |
| [[Concept - RMSNorm and LayerNorm]] | re-scales activations every layer, keeping Jacobians conditioned *throughout training*, not just at init |
| [[Concept - Residual Connections]] | changes each factor to $I + F'$ — an additive identity path the product cannot kill |
| Global-norm gradient clipping (max-norm ~1.0) | caps the update when the product transiently spikes |
| Gating (LSTM/GRU) | an additive cell state with learned gates ≈ a residual connection through time |

The residual entry deserves emphasis because it is the strongest: residuals do not *remove* bad Jacobians, they add an identity term so that $\prod_l (I + F_l')$ expands to $I + \sum_l F_l' + \dots$ — gradient always has a direct, unattenuated path to layer 0 even when every $F_l' \approx 0$. That is the concrete reason ResNets train at 1000+ layers. Gating in [[Concept - Recurrent Networks and the LSTM]] is the same idea discovered a decade earlier for time instead of depth; modern [[Concept - State Space Models and Mamba]] attack the recurrent version head-on by parameterizing the state transition so its eigenvalues stay controllably inside the unit circle.

Ordering note: clipping happens after `backward()` and before `step()` in [[Concept - The Training Loop]], and under mixed precision you must unscale first.

**Detection is cheap — instrument it.** Log per-layer gradient norms (a hook per parameter group, every N steps). Healthy training keeps them within roughly an order of magnitude across depth. Vanishing looks like early-layer norms sitting 3–6 orders of magnitude below late-layer norms while loss crawls. Exploding looks like NaN/Inf loss or spikes in the global grad norm — and in large-model practice the spikes cluster at the LR-warmup boundary, where the step size ramps into curvature the model hasn't adapted to yet (the territory of [[Concept - Training Stability and Loss Spikes]]).

## Failure modes

- **Vanishing:** loss plateaus near its init value; early layers' weights barely move from init (check weight-update-to-weight-norm ratio, healthy ≈ 1e-3 per step); grad-norm profile decays geometrically toward the input. Remedies in order of likelihood: fix init, replace saturating activations, add/repair normalization, add residuals.
- **Exploding:** loss spikes or NaNs, often suddenly after a period of health. First response is global-norm clipping plus a lower peak LR or longer warmup; then look for the structural cause rather than living on clipping forever.
- **The RNN special case:** long sequences vanish even with perfect init, because the same $W$ repeats $T$ times — the fix is architectural (gating, truncated BPTT, or an SSM), not a better constant.
- **Misdiagnosis trap:** a disconnected graph (an accidental `.detach()`, an in-place op) produces exactly-zero early gradients that look like severe vanishing. [[Playbook - Debugging a Neural Network That Won't Train]] orders the checks so you rule this out before touching architecture.

## The non-obvious

In transformers, exploding gradients usually do not come from the FFN stack that the classical theory worries about — they enter through **attention logits**. The $q^\top k$ products grow as weights grow during training; large logits saturate softmax, and the mixture of near-argmax attention and rare large-gradient events produces the spike-prone loss surface seen in LLM pretraining. That is why the effective mitigations are logit-level — [[Concept - z-loss and Logit Soft-Capping]], QK-norm — plus clipping and warmup, rather than yet another init tweak. If your 30-layer transformer NaNs at step 8,000 of warmup, look at attention-logit magnitudes before you look at fan-in constants.

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
