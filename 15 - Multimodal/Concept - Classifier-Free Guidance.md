---
tags: [concept, domain/multimodal, level/core]
aliases: [CFG, guidance scale]
summary: "The inference-time trick that trades sample diversity for prompt adherence by extrapolating away from the unconditional prediction."
---
> **One-paragraph hook:** Every text-to-image model you've used has a "guidance scale" or "CFG scale" slider, and it is doing something specific and mechanical, not vibes: it is extrapolating the model's noise prediction *away* from what it would predict with no prompt at all, and *toward* what it predicts with the prompt — by more than the raw difference between the two. Turn it up and the model obeys your text more literally at the cost of diversity and, past a point, image quality; turn it to 1 (off) and you get a diverse but often prompt-ignoring sample. Classifier-free guidance (Ho & Salimans 2022) is the single highest-leverage inference-time knob in diffusion, and understanding its mechanism explains both why it works and why cranking it up breaks things.

## The mechanism

Classifier guidance (Dhariwal & Nichol 2021) originally got prompt adherence by training a *separate* noise-robust classifier and adding its gradient $\nabla_x \log p(c \mid x_t)$ to the diffusion score at sampling time — effective, but it required training and maintaining an extra noise-aware classifier for every conditioning signal you wanted. Classifier-free guidance removes that classifier entirely with a training-time trick: train **one** model for both the conditional and unconditional case, by randomly replacing the condition $c$ with a fixed null token $\varnothing$ about 10% of the time during training. The same network $\epsilon_\theta$ now knows how to predict noise both with and without the prompt.

At sampling time, run the model twice per step — once conditioned, once unconditioned — and extrapolate:

$$\hat\epsilon = \epsilon_\theta(x_t, \varnothing) + w \cdot \big(\epsilon_\theta(x_t, c) - \epsilon_\theta(x_t, \varnothing)\big)$$

where $w$ is the guidance scale. At $w=1$ this reduces to plain conditional sampling (no guidance effect); $w=0$ is pure unconditional generation; $w>1$ is where the technique does its work — it pushes the prediction *past* the conditional estimate, in the direction the condition moved it relative to no condition at all. This is mathematically equivalent to sampling from an implicitly sharpened distribution $p(x\mid c)^{w} \, p(x)^{1-w}$: raising the conditional likelihood to a power greater than 1 concentrates probability mass on samples that are *unusually* well-explained by the prompt, which is exactly the sharpening-toward-adherence effect you see, and exactly why it's not a normalized probability distribution once $w \ne 1$ — you're deliberately sampling off the model's learned data manifold.

## In practice

Typical guidance scales: **$w \approx 7.5$** was the long-standing Stable Diffusion 1.x/2.x default; SDXL and later models trained with better data/CFG-aware tuning typically use lower scales, **$w \approx 3$–$5$**, because their conditional and unconditional predictions are already closer together (less "correction" needed). **Negative prompts** are a purely inference-time extension of the same formula: instead of using the null token $\varnothing$ as the unconditional branch, you embed a negative prompt (e.g., "blurry, extra fingers") and use *that* as the subtracted term — the extrapolation then pushes away from the negative prompt's typical outputs, not just away from "no prompt." This costs nothing at training time, since the negative branch is just another conditional forward pass through the same trained model.

Because CFG doubles the number of forward passes per step (conditional + unconditional), it directly doubles the compute cost contributed by [[Concept - Diffusion Samplers and Schedulers|sampling]] — a 30-step DDIM run with CFG is 60 network calls, which is the practical reason **guidance-distilled** models (FLUX-dev, SDXL-Turbo-style checkpoints) exist: they bake the guidance behavior into the weights during a distillation pass so inference needs only one forward pass per step.

## Failure modes

- **Oversaturation and the "deep-fried" look at high $w$.** Because the extrapolation pushes the estimate off-manifold, large guidance scales (roughly $w>15$ for SD-era models) produce blown highlights, oversaturated colors, and hard artifacts — the model is confidently predicting a direction that leaves the region of latents it was actually trained to denoise well. Detection: contrast/saturation histograms that clip at extremes, or simply visible "crunchy," overcontrasted output.
- **Reduced diversity as $w$ increases.** Guidance concentrates probability mass, so a batch of samples at high $w$ converges toward similar compositions for the same prompt; if you need diverse variations, high guidance actively fights that goal.
- **Guidance interacts with the sampler and step count**, not just the model — the same $w$ can look fine at 50 steps and oversaturated at 20, because coarser step schedules amplify the off-manifold push per step.

Fixes that shipped in response to the oversaturation problem, roughly in order of adoption: **dynamic thresholding** (Imagen, Saharia et al. 2022) clamps the predicted $x_0$ at each step to a percentile of its own pixel value distribution rather than a hard range, preventing runaway saturation; **guidance rescaling** (Lin et al. 2023) rescales the guided prediction's standard deviation back to match the unguided one, directly targeting the same zero-terminal-SNR-adjacent brightness bias documented in [[Gotchas - Diffusion Training and Sampling]]; **limited-interval guidance** (Kynkäänniemi et al. 2024) applies CFG only during a middle band of noise levels — very high and very low noise timesteps skip guidance entirely — which the authors show gives a large FID improvement because early/late-timestep guidance was mostly adding artifacts, not adherence.

## The non-obvious

Guidance is not free adherence — it is deliberately sampling from a distribution the model was never trained to produce, which is *why* it needs correction mechanisms rather than just "using a very good model." A second hard-won lesson: guidance scale is not portable across models or even across [[Concept - Flow Matching|flow-matching]] vs. diffusion-parameterized checkpoints — the same numeric $w$ means a different amount of extrapolation depending on the noise schedule, the parameterization ($\epsilon$ vs v vs velocity), and whether the model was trained with zero-terminal-SNR correction. Copying "CFG 7.5" from an SD1.5 workflow into an SDXL or SD3 pipeline routinely gives worse results than that model's own tuned default — treat the guidance scale as a per-checkpoint hyperparameter to be re-tuned, not a universal constant.

## Connections
- [[Deep Dive - Diffusion Models]] — CFG is an inference-time technique layered on top of the conditional/unconditional $\epsilon_\theta$ this note's mechanism section derives.
- [[Concept - Latent Diffusion]] — the standard setting where CFG is applied: guiding the cross-attention text conditioning of a latent-space denoiser.
- [[Concept - Diffusion Samplers and Schedulers]] — CFG's double forward-pass cost compounds directly with the sampler's step count to set total inference latency.
- [[Gotchas - Diffusion Training and Sampling]] — catalogs the oversaturation and zero-terminal-SNR interactions this note's failure-modes section summarizes.
- [[Concept - KL Divergence]] — the guidance-sharpened distribution $p(x|c)^w p(x)^{1-w}$ is best understood as deliberately increasing the KL distance from the unconditional model.
- [[Concept - Sampling and Decoding Parameters]] — the LLM-world analog: a hyperparameter chosen at inference time to trade fidelity/adherence against diversity, same tradeoff shape as temperature or top-p.
- [[Concept - Flow Matching]] — modern flow-matching-trained models (SD3, FLUX) still use CFG or a distilled substitute, but the extrapolation interacts differently with straight-line ODE paths.
- [[Concept - ControlNet and Spatial Conditioning for Diffusion]] — a complementary conditioning mechanism operating on the same base model; strong spatial control and high CFG can fight each other for control of the output.

## Sources
- Ho & Salimans (2022) — Classifier-Free Diffusion Guidance. Introduces the joint conditional/unconditional training and the extrapolation formula.
- Dhariwal & Nichol (2021) — Diffusion Models Beat GANs on Image Synthesis. The original classifier-guidance technique CFG replaced.
- Saharia et al. (2022) — Photorealistic Text-to-Image Diffusion Models with Deep Language Understanding (Imagen). Introduces dynamic thresholding.
- Lin, Liu, Wang, et al. (2023) — Common Diffusion Noise Schedules and Sample Steps are Flawed. Guidance rescaling, tied to the zero-terminal-SNR fix.
- Kynkäänniemi, Aittala, Karras, et al. (2024) — Applying Guidance in a Limited Interval Improves Sample and Distribution Quality in Diffusion Models.
