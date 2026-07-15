---
tags: [gotchas, domain/multimodal, level/unicorn]
aliases: [diffusion gotchas, zero terminal SNR, latent scaling factor, EMA sampling]
summary: "Arcane failure modes and folklore fixes for training and sampling diffusion models — SNR bugs, scaling constants, EMA, fp16 traps."
---
> Aggregated pitfalls in training and sampling [[Deep Dive - Diffusion Models|diffusion]] models, ordered by how much time they cost before you find them. Most of these fail *silently* — no exception, no NaN, just quietly worse images — which is exactly what makes them expensive. VLM-side pitfalls live in [[Gotchas - Vision-Language Models]].

## 1. Forgot (or mismatched) the VAE latent scaling constant → garbage or washed-out output

**Symptom:** A model that trains fine produces noisy, blown-out, or completely garbled images; or a working pipeline breaks the moment you swap in a different checkpoint. No error is raised.
**Cause:** [[Concept - Latent Diffusion|Latent-space]] diffusion multiplies the raw VAE latent by a fixed constant so its variance is $\approx 1$, matching what the noise schedule assumes. The constant is **0.18215 for SD1.x/SD2 and 0.13025 for SDXL** — it is *not* stored in the weights, it is a usage convention. Omit it, or use SD's constant on an SDXL VAE, and the diffusion model sees latents of the wrong variance.
**Fix:** Encode as `z = vae.encode(x).latent_dist.sample() * scaling_factor` and decode as `vae.decode(z / scaling_factor)`. Read `scaling_factor` off the VAE config, never hard-code it across model families.
**Detection:** Print `z.std()` right after scaling — it should be near 1.0. If it's ~5 or ~0.2, you have the wrong (or no) constant.

## 2. Sampling from the raw training weights instead of the EMA copy → mysteriously worse samples

**Symptom:** Your model trains, the loss looks great, but generated images are visibly grainier or less coherent than published results from the "same" architecture.
**Cause:** Diffusion models are sampled from an **exponential moving average** of the weights, not the live optimizer weights. The EMA (decay $\approx 0.999$–$0.9999$) averages out the high-frequency noise in the SGD trajectory; the instantaneous weights sit in a slightly worse basin every step.
**Fix:** Maintain an EMA shadow copy during training and load it for all evaluation and release. Confirm your checkpoint actually contains the EMA weights, not the raw ones.
**Detection:** Sample from EMA and raw weights side by side at the same seed — a clear quality gap confirms you were using raw weights.

## 3. Scheduler ↔ parameterization mismatch (v-pred model run with an ε-pred sampler) → broken images

**Symptom:** A known-good checkpoint outputs pure noise, solid color, or scrambled images even though the code "runs." Common right after switching schedulers or downloading a v-prediction model.
**Cause:** The network can be trained to predict $\epsilon$ (noise), $x_0$, or $v = \sqrt{\bar\alpha_t}\,\epsilon - \sqrt{1-\bar\alpha_t}\,x_0$ (Salimans & Ho 2022). The [[Concept - Diffusion Samplers and Schedulers|sampler]] must invert whichever target the model was trained on. Feed a v-pred model's output into an $\epsilon$-pred update rule and every step steps the wrong direction.
**Fix:** Set the scheduler's `prediction_type` to match the checkpoint (`v_prediction` vs `epsilon`). SD2's 768 model and most zero-terminal-SNR checkpoints are v-pred.
**Detection:** If images are broken from step 0 with a valid checkpoint, suspect the parameterization before the prompt or seed.

## 4. The SDXL VAE decodes to NaN in fp16 → solid black images

**Symptom:** Diffusion sampling produces a perfectly normal-looking latent, but the decoded image is solid black (or has black regions), with no error thrown.
**Cause:** The original SDXL VAE has activations that overflow the fp16 range during decode; the overflow becomes NaN, which the final clamp renders as black. It is purely a numerical-range issue in the decoder, unrelated to the sampler.
**Fix:** Run the VAE decode in fp32 or bf16, or swap in the community fp16-fixed VAE checkpoint. Keep the diffusion U-Net in fp16 if you like — only the decode needs the wider range. See [[Concept - Mixed Precision Training]] and [[Concept - Floating Point for Deep Learning]] for why fp16's narrow exponent range is the culprit.
**Detection:** Decode the same latent in fp32 and fp16 and diff — black-only-in-fp16 is the fingerprint.

## 5. Zero terminal SNR bug → the model can't make pure black or pure white

**Symptom:** Every generation drifts toward medium brightness; you cannot get a truly dark night scene or a truly white background. Contrast feels muddy regardless of prompt.
**Cause:** Standard noise schedules (linear, cosine) never actually reach signal-to-noise ratio $=0$ at the final timestep — a faint trace of the clean image always leaks through in training. But at inference you start from *pure* Gaussian noise. The model learned to expect that leaked low-frequency signal (which encodes overall brightness) and never has to predict it, so it defaults to the dataset-mean brightness. Lin et al. 2023 ("Common Diffusion Noise Schedules and Sample Steps are Flawed") diagnosed this train/test mismatch.
**Fix:** All four changes together — (1) **rescale the betas to enforce zero terminal SNR**, (2) switch to **v-prediction** (ε-pred is numerically undefined at SNR=0), (3) sample using **trailing** timestep selection so the last step is included, and (4) apply **CFG rescale**. Doing only some of the four leaves the fix broken.
**Detection:** Prompt for "a solid black image" / "solid white background." An unfixed model returns gray.

## 6. CFG oversaturation at high guidance → the "deep-fried" look

**Symptom:** At high [[Concept - Classifier-Free Guidance|guidance]] scale, colors blow out, highlights clip to white, and images look crunchy and over-contrasted.
**Cause:** CFG extrapolates $\hat\epsilon = \epsilon_\text{uncond} + w\,(\epsilon_\text{cond} - \epsilon_\text{uncond})$; large $w$ pushes the predicted $x_0$ outside the natural pixel range, which the decoder renders as clipped, saturated color. Typical safe scales are $w\approx 7.5$ for SD1.x and $\approx 5$ for SDXL; $w > 15$ reliably fries.
**Fix:** Dynamic thresholding (Imagen, Saharia et al. 2022) clamps predicted $x_0$ by percentile; guidance rescale (Lin et al. 2023) rescales the guided prediction's std back to the conditional's; limited-interval guidance (Kynkäänniemi et al. 2024) applies CFG only in a middle-noise window for a large quality gain at no diversity cost.
**Detection:** Sweep $w$ and watch histogram clipping — saturation climbing with $w$ is the tell.

## 7. Exposure bias → error compounds over the sampling trajectory

**Symptom:** Long sampling schedules don't improve as much as expected, and samples carry subtle accumulated artifacts that short schedules don't.
**Cause:** Training conditions the network on *ground-truth* noised inputs $x_t = \sqrt{\bar\alpha_t}x_0 + \sqrt{1-\bar\alpha_t}\epsilon$, but sampling conditions each step on the model's *own estimate* of the previous step. That distribution shift (train on real $x_t$, infer on approximate $x_t$) compounds across steps.
**Fix:** Perturb the training input slightly (input perturbation, Ning et al. 2023) so the network sees off-manifold inputs like it will at inference; higher-order [[Concept - Diffusion Samplers and Schedulers|solvers]] also reduce per-step error.
**Detection:** Compare a deterministic sampler's trajectory against re-noised ground truth at matched timesteps; growing divergence is exposure bias.

## 8. Unweighted L_simple over-weights easy timesteps → slow convergence

**Symptom:** Training converges slowly and spends most of its gradient budget on high-SNR (nearly-clean) timesteps that were already easy.
**Cause:** The vanilla simple loss weights every timestep equally, but the *difficulty* of denoising is wildly unequal across $t$; easy steps dominate the average and waste capacity.
**Fix:** Min-SNR loss weighting (Hang et al. 2023) caps each timestep's weight at $\min(\text{SNR}(t), \gamma)$ with $\gamma\approx 5$, rebalancing effort toward the hard mid-noise steps and speeding convergence several-fold.
**Detection:** Plot per-timestep loss; a huge imbalance across $t$ means unweighted training is leaving convergence on the table.

## 9. Square-cropping every training image → center bias and cropped subjects

**Symptom:** The model composes subjects dead-center, crops off heads and feet, and struggles with wide or tall aspect ratios.
**Cause:** Center-square-cropping a dataset to a fixed resolution teaches the model that subjects are always centered and that edges get cut — it literally never saw a full-frame off-center composition.
**Fix:** **Aspect-ratio bucketing** — group images by aspect ratio and train each bucket at its native shape, padding batches instead of cropping content. SDXL additionally added *crop-conditioning* embeddings (Podell et al. 2023) that tell the model how the training image was cropped, letting it learn to *not* crop at inference — see [[Breakdown - Stable Diffusion]].
**Detection:** Prompt for full-body or wide-landscape compositions; systematic cropping/centering indicates square-crop training.

## Connections
- [[Deep Dive - Diffusion Models]] — the forward/reverse math, parameterizations, and schedules these gotchas break; read it first.
- [[Concept - Classifier-Free Guidance]] — gotcha #6 (oversaturation) and part of #5 (CFG rescale) live here.
- [[Concept - Diffusion Samplers and Schedulers]] — gotchas #3, #5, #7 are all sampler/scheduler mismatches.
- [[Concept - Latent Diffusion]] — the source of the scaling-constant trap in #1 and the fp16-decode NaN in #4.
- [[Breakdown - Stable Diffusion]] — SDXL's crop-conditioning fix (#9) and per-version scaling constants (#1) in system context.
- [[Concept - Mixed Precision Training]] — the fp16/bf16 choices behind the VAE-decode NaN in #4.
- [[Concept - Floating Point for Deep Learning]] — why fp16's narrow exponent range causes the overflow-to-NaN in #4.
- [[Lore - The Stable Diffusion Release and Its Aftermath]] — the community context in which most of these fixes (fp16 VAE, EMA, zero-SNR) were discovered and circulated.

## Sources
- Lin, Yang, et al. (2023) — Common Diffusion Noise Schedules and Sample Steps are Flawed. The zero-terminal-SNR diagnosis and the four-part fix; also guidance rescale.
- Salimans, Ho (2022) — Progressive Distillation for Fast Sampling of Diffusion Models. Introduces v-prediction, central to gotcha #3 and #5.
- Hang, Gu, et al. (2023) — Efficient Diffusion Training via Min-SNR Weighting Strategy. The loss-weighting fix in #8.
- Saharia, Chan, et al. (2022) — Photorealistic Text-to-Image Diffusion Models (Imagen). Dynamic thresholding for CFG oversaturation.
- Kynkäänniemi, et al. (2024) — Applying Guidance in a Limited Interval Improves Sample and Distribution Quality. Limited-interval CFG.
- Ning, et al. (2023) — Input Perturbation Reduces Exposure Bias in Diffusion Models. The exposure-bias mitigation in #7.
- Podell, et al. (2023) — SDXL. Aspect-ratio bucketing and crop-conditioning (#9).
