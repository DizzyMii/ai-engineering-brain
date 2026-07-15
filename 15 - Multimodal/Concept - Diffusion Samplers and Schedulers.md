---
tags: [concept, domain/multimodal, level/core]
aliases: [DDIM, DPM-Solver, Karras sigmas, ODE samplers, noise schedule]
summary: "The solvers and noise schedules that turn a trained diffusion model into an image in N steps, and why N drives latency."
---
> **One-paragraph hook:** A trained denoiser only tells you one thing per call: given a noisy latent at some noise level, predict the noise (or velocity) that produced it. Turning a sequence of those calls into a finished image is a separate numerical-methods problem — you're integrating a differential equation, and *how* you integrate it (which solver, how many steps, what noise-level spacing) changes output quality and cost without touching a single trained weight. This is why swapping "DDIM 50 steps" for "DPM-Solver++ 20 steps" on the same [[Breakdown - Stable Diffusion]] checkpoint changes both your latency bill and your image quality with zero retraining.

## The mechanism

[[Deep Dive - Diffusion Models]] establishes that reverse diffusion is a discretization of a probability-flow ODE (or, equivalently, a reverse SDE) sharing the same marginals. A sampler is the specific integrator you run over that trajectory, and they split into two families:

- **Stochastic samplers** re-inject noise at every step (ancestral DDPM sampling, the original 1000-step chain, and Euler-ancestral variants). More diverse outputs, but need more steps to converge because the injected noise adds variance the solver has to average out.
- **Deterministic ODE samplers** solve the probability-flow ODE with no injected noise: same input latent and seed always produces the same output, and far fewer steps suffice.

**DDIM** (Song et al. 2021) is the canonical deterministic sampler — a non-Markovian reformulation of the DDPM chain that lets you skip timesteps:

$$x_{t-1} = \sqrt{\bar\alpha_{t-1}}\underbrace{\left(\frac{x_t - \sqrt{1-\bar\alpha_t}\,\epsilon_\theta(x_t,t)}{\sqrt{\bar\alpha_t}}\right)}_{\hat x_0} + \sqrt{1-\bar\alpha_{t-1}}\,\epsilon_\theta(x_t,t)$$

Each step re-estimates $\hat x_0$ from the current noise prediction, then re-noises it to the *next* (lower) noise level directly — no need to walk through every intermediate $t$. This alone takes step count from ~1000 to 20-50 with little quality loss.

**DPM-Solver / DPM-Solver++** (Lu et al. 2022) go further: they treat the reverse ODE as a semi-linear equation and apply a proper multi-step, high-order (2nd/3rd order) solver, borrowing directly from classical numerical ODE methods rather than DDIM's first-order approximation. The "++" variant fixes a specific interaction with [[Concept - Classifier-Free Guidance]] and with latent-space models, and is what gets Stable Diffusion-family models to good images in 10-20 steps instead of 20-50.

**Karras et al. 2022 (EDM)** reframes the whole schedule question in terms of noise magnitude $\sigma$ directly rather than the $\beta_t/\bar\alpha_t$ DDPM parameterization, and shows that how you *space* the sigma values across steps matters as much as the solver itself:

$$\sigma_i = \left(\sigma_{max}^{1/\rho} + \frac{i}{N-1}\big(\sigma_{min}^{1/\rho} - \sigma_{max}^{1/\rho}\big)\right)^{\rho}, \qquad \rho \approx 7$$

This "Karras schedule" spends more of the step budget near the low-noise end (where fine detail is resolved) and less near pure noise (where coarse structure is set quickly), paired with a 2nd-order Heun sampler. It is a schedule change applicable to *any* pretrained model, with no retraining — one of the few genuinely free lunches in the field.

## In practice

Step-count economics dominate serving cost: each step is one full forward pass through the backbone (U-Net or [[Concept - Diffusion Transformers (DiT)]]), and with [[Concept - Classifier-Free Guidance]] active, every step runs the backbone *twice* — once conditional, once unconditional — so wall-clock cost is $2N$ backbone forwards, not $N$. SDXL saturates quality around ~30 DPM-Solver++ steps; pushing past that buys essentially nothing, which is a common wasted-compute mistake in production pipelines. The FLOPs-per-step of the backbone itself is a straightforward [[Concept - The Roofline Model]] question — a DiT backbone at high resolution is attention-bound and quadratic in token count, so step count and resolution multiply directly into latency.

Where latency budgets are tight, the fix is not a smarter solver but **fewer steps by construction**: LCM / LCM-LoRA (consistency distillation) collapse sampling to 4-8 steps, and SDXL-Turbo / ADD (adversarial diffusion distillation) push to 1-4 steps by training the model to jump most of the trajectory in one shot. These are [[Concept - Knowledge Distillation]] applied to the sampling trajectory itself — the student learns to match what many-step sampling would have produced, and in doing so effectively bakes a fixed guidance scale into its weights, trading the flexibility of a swappable sampler/CFG-scale for raw speed. [[Concept - Flow Matching]] models get an analogous few-step win from "reflow" — straightening ODE trajectories so a straight-line (1-2 step) Euler integration is nearly exact.

The scheduler must also match how the model was trained: a model trained with $v$-prediction sampled with an $\epsilon$-prediction-tuned solver silently produces broken or washed-out images, and a model trained with zero-terminal-SNR correction requires **trailing timestep selection** (starting the sampling schedule at the actual zero-SNR endpoint) or you reintroduce the exact brightness bias the training fix was meant to remove — see [[Gotchas - Diffusion Training and Sampling]].

## Failure modes

- **Too few steps → blur or structured artifacts.** Coarse discretization of the ODE accumulates integration error; visible as smeared detail, color banding, or ringing. Detection: sweep step count and confirm quality plateaus (it should stop improving past ~20-30 steps for a well-matched solver) — if it keeps improving indefinitely, the solver/schedule pairing is suboptimal.
- **Wrong sampler for the parameterization.** Running an $\epsilon$-prediction-tuned DDIM against a $v$-prediction checkpoint (or vice versa) produces images that look plausible in structure but wrong in color/exposure. Detection: check the `prediction_type` the sampler assumes against how the checkpoint was trained before debugging anything else.
- **Ancestral noise at low step counts → visible grain.** Stochastic samplers inject fresh noise every step; at very low step counts that noise doesn't get fully "cleaned up" by subsequent steps, leaving grain deterministic samplers at the same step count don't have.
- **Schedule/timestep-selection mismatch with zero-terminal-SNR models.** Using a standard (non-trailing) timestep schedule on a zero-SNR-corrected checkpoint reintroduces the medium-brightness bias the correction fixed.

## The non-obvious

The Karras sigma-schedule result is a rare case where a pure inference-time change (no retraining, no fine-tuning) measurably improves output quality at a fixed step budget across *unrelated* checkpoints — most "free" quality wins in this field require touching training. It's worth trying before reaching for a fancier solver. The second non-obvious point is the asymmetry between swappable samplers and distilled few-step models: because CFG scale, sampler choice, and step count are all inference-time knobs on a base model, you can A/B them freely in production; a distilled model (LCM, Turbo) has effectively frozen those choices into its weights, so "just add classifier-free guidance" or "just switch to 50 steps for a hard prompt" are no longer available once you've distilled — a real product decision, not just a technical one.

## Connections
- [[Deep Dive - Diffusion Models]] — establishes the forward/reverse process and the ODE/SDE equivalence that samplers are numerically integrating.
- [[Concept - Classifier-Free Guidance]] — doubles the per-step cost of every sampler and interacts directly with solver choice (DPM-Solver++ was built partly to handle this interaction correctly).
- [[Concept - Flow Matching]] — the continuous-time generalization whose straight-line ODE paths make few-step sampling (reflow) far more accurate than curved diffusion paths at the same step count.
- [[Gotchas - Diffusion Training and Sampling]] — catalogs the exact zero-terminal-SNR and parameterization-mismatch bugs that come from pairing the wrong sampler with a checkpoint.
- [[Concept - Knowledge Distillation]] — the general technique (student matches teacher's trajectory) that LCM and ADD apply specifically to compress the sampling trajectory itself.
- [[Concept - Sampling and Decoding Parameters]] — the analogous inference-time knob set (temperature, top-p) on the LLM side; both domains trade a step/token budget against output quality and determinism.
- [[Concept - The Roofline Model]] — the general framework for why each sampler step's cost is dominated by backbone FLOPs vs memory bandwidth, and why step count multiplies latency linearly.
- [[Concept - Diffusion Transformers (DiT)]] — the modern backbone each sampler step calls; its quadratic attention cost is what makes step count and resolution multiply into serious latency at high resolution.

## Sources
- Song, Meng, Ermon (2021) — Denoising Diffusion Implicit Models (DDIM). The deterministic, step-skipping sampler.
- Lu, Zhou, Bao, Chen, Li, Zhu (2022) — DPM-Solver / DPM-Solver++. High-order ODE solvers for few-step diffusion sampling.
- Karras, Aittala, Aila, Laine (2022) — Elucidating the Design Space of Diffusion-Based Generative Models (EDM). Sigma-based schedule reframing and the Karras step spacing.
- Luo et al. (2023) — Latent Consistency Models (LCM). Consistency distillation for 4-8 step sampling.
- Sauer et al. (2023) — Adversarial Diffusion Distillation (ADD / SDXL-Turbo). 1-4 step distillation via an adversarial objective.
