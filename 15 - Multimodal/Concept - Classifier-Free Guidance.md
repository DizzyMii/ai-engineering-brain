---
tags: [concept, domain/multimodal, level/core]
aliases: [CFG, guidance scale]
summary: "The inference-time trick that trades sample diversity for prompt adherence by extrapolating away from the unconditional prediction."
---
> **One-paragraph hook:** Every text-to-image model you've used has a "guidance scale" or "CFG scale" slider, and it does something specific and mechanical. It extrapolates the model's noise prediction *away* from what it would predict with no prompt and *toward* what it predicts with the prompt, by more than the raw difference between the two. Turn it up and the model follows your text more literally, at the cost of diversity and, past some point, image quality. Set it to 1 (off) and you get diverse samples that often ignore the prompt. Classifier-free guidance (Ho & Salimans 2022) is the highest-leverage inference-time knob in diffusion, and its mechanism explains both why it works and why cranking it breaks things.

## The mechanism

Classifier guidance (Dhariwal & Nichol 2021) got prompt adherence by training a *separate* noise-robust classifier and adding its gradient $\nabla_x \log p(c \mid x_t)$ to the diffusion score during sampling. It worked, but you had to train and maintain an extra noise-aware classifier for every conditioning signal. Classifier-free guidance drops the classifier with a training-time trick. Train **one** model for both the conditional and unconditional case by swapping the condition $c$ for a fixed null token $\varnothing$ about 10% of the time. The same network $\epsilon_\theta$ then predicts noise both with and without the prompt.

At sampling time, run the model twice per step, once conditioned and once unconditioned, and extrapolate:

$$\hat\epsilon = \epsilon_\theta(x_t, \varnothing) + w \cdot \big(\epsilon_\theta(x_t, c) - \epsilon_\theta(x_t, \varnothing)\big)$$

$w$ is the guidance scale. At $w=1$ you get plain conditional sampling with no guidance effect, and $w=0$ is pure unconditional generation. The technique does its work at $w>1$, where it pushes the prediction *past* the conditional estimate, in the direction the condition moved it relative to no condition. Mathematically this equals sampling from an implicitly sharpened distribution $p(x\mid c)^{w} \, p(x)^{1-w}$. Raising the conditional likelihood to a power greater than 1 concentrates probability mass on samples the prompt explains *unusually* well. That's the sharpening toward adherence you see. It's also why the result isn't a normalized probability distribution once $w \ne 1$: you're deliberately sampling off the model's learned data manifold.

## In practice

Typical scales: **$w \approx 7.5$** was the long-standing Stable Diffusion 1.x/2.x default. SDXL and later models, trained with better data and CFG-aware tuning, typically use lower scales, **$w \approx 3$–$5$**, because their conditional and unconditional predictions already sit closer together and need less "correction".

**Negative prompts** extend the same formula at inference time. In place of the null token $\varnothing$ in the unconditional branch, you embed a negative prompt (e.g., "blurry, extra fingers") and subtract *that*. The extrapolation now pushes away from the negative prompt's typical outputs as well as away from "no prompt". It costs nothing in training, since the negative branch is one more conditional forward pass through the same model.

CFG doubles the forward passes per step (conditional + unconditional), so it doubles the compute cost of [[Concept - Diffusion Samplers and Schedulers|sampling]]. A 30-step DDIM run with CFG is 60 network calls. That's the practical reason **guidance-distilled** models (FLUX-dev, SDXL-Turbo-style checkpoints) exist: a distillation pass bakes the guidance behavior into the weights, so inference needs one forward pass per step.

## Failure modes

- **Oversaturation and the "deep-fried" look at high $w$.** The extrapolation pushes the estimate off-manifold, so large scales (roughly $w>15$ for SD-era models) give blown highlights, oversaturated colors and hard artifacts. The model is confidently heading in a direction that leaves the region of latents it learned to denoise well. Detect it with contrast/saturation histograms that clip at the extremes, or just by looking at "crunchy", overcontrasted output.
- **Diversity drops as $w$ rises.** Guidance concentrates probability mass, so at high $w$ a batch of samples for one prompt converges on similar compositions. If you want diverse variations, high guidance works against you.
- **Guidance interacts with the sampler and step count**, not only the model. The same $w$ can look fine at 50 steps and oversaturated at 20, because coarser step schedules amplify the off-manifold push per step.

Several fixes for oversaturation shipped, roughly in order of adoption. **Dynamic thresholding** (Imagen, Saharia et al. 2022) clamps the predicted $x_0$ at each step to a percentile of its own pixel-value distribution instead of a hard range, which stops runaway saturation. **Guidance rescaling** (Lin et al. 2023) rescales the guided prediction's standard deviation back to the unguided one's, aimed at the same zero-terminal-SNR-adjacent brightness bias covered in [[Gotchas - Diffusion Training and Sampling]]. **Limited-interval guidance** (Kynkäänniemi et al. 2024) applies CFG only in a middle band of noise levels and skips it at very high and very low noise. The authors show a large FID improvement, because guidance at early and late timesteps was mostly adding artifacts, not adherence.

## The non-obvious

Guidance doesn't give you adherence for free. It deliberately samples from a distribution the model was never trained to produce, and that's *why* it needs correction mechanisms; a better model alone won't remove the need. The second hard-won lesson is that guidance scale doesn't transfer across models, or even between [[Concept - Flow Matching|flow-matching]] and diffusion-parameterized checkpoints. The same numeric $w$ means a different amount of extrapolation depending on the noise schedule, the parameterization ($\epsilon$ vs v vs velocity), and whether the model was trained with zero-terminal-SNR correction. Copying "CFG 7.5" from an SD1.5 workflow into an SDXL or SD3 pipeline routinely does worse than that model's own tuned default. Re-tune the guidance scale per checkpoint.

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
