---
tags: [concept, domain/multimodal, level/core]
aliases: [DDIM, DPM-Solver, Karras sigmas, ODE samplers, noise schedule]
summary: "The solvers and noise schedules that turn a trained diffusion model into an image in N steps, and why N drives latency."
---
> **One-paragraph hook:** A trained denoiser answers one question per call: given a noisy latent at some noise level, what noise (or velocity) produced it? Turning a sequence of those calls into a finished image is a separate numerical-methods problem. You're integrating a differential equation, and *how* you integrate it (which solver, how many steps, what noise-level spacing) changes quality and cost without touching a trained weight. Swap "DDIM 50 steps" for "DPM-Solver++ 20 steps" on the same [[Breakdown - Stable Diffusion]] checkpoint and both your latency bill and your image quality move, with zero retraining.

## The mechanism

[[Deep Dive - Diffusion Models]] shows that reverse diffusion discretizes a probability-flow ODE (or, equivalently, a reverse SDE) with the same marginals. A sampler is the integrator you run along that trajectory. There are two families:

- **Stochastic samplers** re-inject noise every step (ancestral DDPM sampling, the original 1000-step chain, Euler-ancestral variants). Outputs are more diverse, but they need more steps to converge because the injected noise adds variance the solver has to average out.
- **Deterministic ODE samplers** solve the probability-flow ODE with no injected noise. The same input latent and seed always give the same output, and far fewer steps are enough.

**DDIM** (Song et al. 2021) is the standard deterministic sampler, a non-Markovian reformulation of the DDPM chain that can skip timesteps:

$$x_{t-1} = \sqrt{\bar\alpha_{t-1}}\underbrace{\left(\frac{x_t - \sqrt{1-\bar\alpha_t}\,\epsilon_\theta(x_t,t)}{\sqrt{\bar\alpha_t}}\right)}_{\hat x_0} + \sqrt{1-\bar\alpha_{t-1}}\,\epsilon_\theta(x_t,t)$$

Each step re-estimates $\hat x_0$ from the current noise prediction and re-noises it straight to the *next* (lower) noise level, with no walk through every intermediate $t$. That alone cuts step count from ~1000 to 20-50 with little quality loss.

**DPM-Solver / DPM-Solver++** (Lu et al. 2022) go further. They treat the reverse ODE as semi-linear and apply a proper multi-step, high-order (2nd/3rd order) solver taken from classical numerical ODE methods, where DDIM is a first-order approximation. The "++" variant fixes a specific interaction with [[Concept - Classifier-Free Guidance]] and with latent-space models, and it gets Stable Diffusion-family models to good images in 10-20 steps instead of 20-50.

**Karras et al. 2022 (EDM)** recasts the schedule question in terms of the noise magnitude $\sigma$ itself instead of DDPM's $\beta_t/\bar\alpha_t$ parameterization, and shows that how you *space* the sigma values across steps matters as much as the solver:

$$\sigma_i = \left(\sigma_{max}^{1/\rho} + \frac{i}{N-1}\big(\sigma_{min}^{1/\rho} - \sigma_{max}^{1/\rho}\big)\right)^{\rho}, \qquad \rho \approx 7$$

The "Karras schedule" spends more of the step budget near the low-noise end, where fine detail gets resolved, and less near pure noise, where coarse structure settles quickly. It's paired with a 2nd-order Heun sampler. Because it's only a schedule change, it applies to *any* pretrained model with no retraining. Free lunches are rare in this field, and this is one.

## In practice

Step count drives serving cost. Each step is a full forward pass through the backbone (U-Net or [[Concept - Diffusion Transformers (DiT)]]), and with [[Concept - Classifier-Free Guidance]] on, each step runs the backbone *twice*, conditional and unconditional, so wall-clock cost is $2N$ backbone forwards, not $N$. SDXL quality saturates around ~30 DPM-Solver++ steps. Going past that buys essentially nothing; it's a common way production pipelines waste compute. The backbone's FLOPs per step are a plain [[Concept - The Roofline Model]] question: a DiT at high resolution is attention-bound and quadratic in token count, so step count and resolution multiply directly into latency.

When the latency budget is tight, a smarter solver won't save you. You need **fewer steps by construction**. LCM / LCM-LoRA (consistency distillation) cut sampling to 4-8 steps, and SDXL-Turbo / ADD (adversarial diffusion distillation) get to 1-4 steps by training the model to jump most of the trajectory at once. This is [[Concept - Knowledge Distillation]] applied to the sampling trajectory: the student learns to match what many-step sampling would have produced, and along the way bakes a fixed guidance scale into its weights. You give up a swappable sampler and CFG scale for raw speed. [[Concept - Flow Matching]] models get a similar few-step win from "reflow", which straightens ODE trajectories until a straight-line (1-2 step) Euler integration is nearly exact.

The scheduler also has to match how the model was trained. A $v$-prediction model sampled with an $\epsilon$-prediction-tuned solver silently gives broken or washed-out images. A model trained with zero-terminal-SNR correction needs **trailing timestep selection** (the schedule starts at the actual zero-SNR endpoint), or you bring back the brightness bias the training fix was supposed to remove. See [[Gotchas - Diffusion Training and Sampling]].

## Failure modes

- **Too few steps → blur or structured artifacts.** Coarse discretization piles up integration error, which shows as smeared detail, color banding or ringing. To detect it, sweep step count and confirm quality plateaus (past ~20-30 steps for a well-matched solver). If quality keeps improving indefinitely, the solver/schedule pairing is off.
- **Wrong sampler for the parameterization.** An $\epsilon$-prediction-tuned DDIM on a $v$-prediction checkpoint (or the reverse) gives images with plausible structure and wrong color/exposure. Before debugging anything else, compare the `prediction_type` the sampler assumes with how the checkpoint was trained.
- **Ancestral noise at low step counts → visible grain.** Stochastic samplers add fresh noise every step. At very low step counts later steps don't fully "clean up" that noise, and you get grain a deterministic sampler at the same step count wouldn't show.
- **Schedule/timestep-selection mismatch on zero-terminal-SNR models.** A standard (non-trailing) timestep schedule on a zero-SNR-corrected checkpoint brings back the medium-brightness bias the correction fixed.

## The non-obvious

The Karras sigma schedule is a rare pure inference-time change (no retraining, no fine-tuning) that measurably improves quality at a fixed step budget across *unrelated* checkpoints. Most "free" quality wins in this field need a training change. Try it before reaching for a fancier solver.

The second point is the asymmetry between swappable samplers and distilled few-step models. On a base model, CFG scale, sampler and step count are all inference-time knobs you can A/B freely in production. A distilled model (LCM, Turbo) has frozen those choices into its weights. Once you've distilled, "just add classifier-free guidance" or "just use 50 steps for this hard prompt" aren't options anymore. That makes distillation a product decision as much as a technical one.

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
