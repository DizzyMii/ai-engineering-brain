---
tags: [gotchas, domain/multimodal, level/unicorn]
aliases: [diffusion gotchas, zero terminal SNR, latent scaling factor, EMA sampling]
summary: "Arcane failure modes and folklore fixes for training and sampling diffusion models — SNR bugs, scaling constants, EMA, fp16 traps."
---
> Pitfalls in training and sampling [[Deep Dive - Diffusion Models|diffusion]] models, ordered by how much time they cost before you find them. Most fail *silently* (no exception, no NaN, just worse images), which is what makes them expensive. VLM-side pitfalls are in [[Gotchas - Vision-Language Models]].

## 1. Forgot (or mismatched) the VAE latent scaling constant → garbage or washed-out output

**Symptom:** A model that trains fine produces noisy, blown-out or garbled images, or a working pipeline breaks when you swap checkpoints. No error is raised.
**Cause:** [[Concept - Latent Diffusion|Latent-space]] diffusion multiplies the raw VAE latent by a fixed constant so its variance is $\approx 1$, which is what the noise schedule assumes. The constant is **0.18215 for SD1.x/SD2 and 0.13025 for SDXL**. It's a usage convention and isn't stored in the weights. Leave it out, or use SD's constant on an SDXL VAE, and the diffusion model sees latents with the wrong variance.
**Fix:** Encode as `z = vae.encode(x).latent_dist.sample() * scaling_factor` and decode as `vae.decode(z / scaling_factor)`. Read `scaling_factor` from the VAE config. Never hard-code it across model families.
**Detection:** Print `z.std()` right after scaling. It should be near 1.0; ~5 or ~0.2 means the wrong constant (or none).

## 2. Sampling from the raw training weights instead of the EMA copy → mysteriously worse samples

**Symptom:** The loss looks great, but images are grainier or less coherent than published results from the "same" architecture.
**Cause:** Diffusion models are sampled from an **exponential moving average** of the weights, not the live optimizer weights. The EMA (decay $\approx 0.999$–$0.9999$) averages out the high-frequency noise in the SGD trajectory; at any given step the instantaneous weights sit in a slightly worse basin.
**Fix:** Keep an EMA shadow copy during training and load it for all evaluation and release. Check that your checkpoint holds the EMA weights.
**Detection:** Sample from EMA and raw weights side by side with the same seed. A clear quality gap confirms you were using the raw weights.

## 3. Scheduler ↔ parameterization mismatch (v-pred model run with an ε-pred sampler) → broken images

**Symptom:** A known-good checkpoint outputs pure noise, solid color or scrambled images while the code "runs". Common right after switching schedulers or downloading a v-prediction model.
**Cause:** The network can be trained to predict $\epsilon$ (noise), $x_0$, or $v = \sqrt{\bar\alpha_t}\,\epsilon - \sqrt{1-\bar\alpha_t}\,x_0$ (Salimans & Ho 2022). The [[Concept - Diffusion Samplers and Schedulers|sampler]] has to invert whichever target the model learned. Feed a v-pred model's output into an $\epsilon$-pred update rule and every step goes the wrong way.
**Fix:** Set the scheduler's `prediction_type` to match the checkpoint (`v_prediction` vs `epsilon`). SD2's 768 model and most zero-terminal-SNR checkpoints are v-pred.
**Detection:** If images are broken from step 0 with a valid checkpoint, suspect the parameterization before the prompt or seed.

## 4. The SDXL VAE decodes to NaN in fp16 → solid black images

**Symptom:** Sampling produces a perfectly normal-looking latent, but the decoded image is solid black (or has black regions), and nothing errors.
**Cause:** The original SDXL VAE has activations that overflow fp16 during decode. The overflow becomes NaN, which the final clamp renders as black. It's purely a numerical-range problem in the decoder, unrelated to the sampler.
**Fix:** Decode in fp32 or bf16, or swap in the community fp16-fixed VAE checkpoint. The diffusion U-Net can stay in fp16; only the decode needs the wider range. [[Concept - Mixed Precision Training]] and [[Concept - Floating Point for Deep Learning]] explain why fp16's narrow exponent range is to blame.
**Detection:** Decode the same latent in fp32 and fp16 and diff. Black only in fp16 is the fingerprint.

## 5. Zero terminal SNR bug → the model can't make pure black or pure white

**Symptom:** Every generation drifts toward medium brightness. Night scenes never get properly dark, white backgrounds never get pure white, and contrast stays muddy whatever the prompt.
**Cause:** Standard noise schedules (linear, cosine) never actually reach signal-to-noise ratio $=0$ at the final timestep, so a faint trace of the clean image always leaks through in training. At inference, though, you start from *pure* Gaussian noise. The model learned to rely on that leaked low-frequency signal (overall brightness) and never had to predict it, so it falls back to dataset-mean brightness. Lin et al. 2023 ("Common Diffusion Noise Schedules and Sample Steps are Flawed") diagnosed this train/test mismatch.
**Fix:** All four changes together: (1) **rescale the betas to enforce zero terminal SNR**, (2) switch to **v-prediction** (ε-pred is numerically undefined at SNR=0), (3) sample with **trailing** timestep selection so the last step is included, and (4) apply **CFG rescale**. Doing only some of the four leaves it broken.
**Detection:** Prompt for "a solid black image" / "solid white background". An unfixed model gives you gray.

## 6. CFG oversaturation at high guidance → the "deep-fried" look

**Symptom:** At high [[Concept - Classifier-Free Guidance|guidance]] scales, colors blow out, highlights clip to white, and images look crunchy and over-contrasted.
**Cause:** CFG extrapolates $\hat\epsilon = \epsilon_\text{uncond} + w\,(\epsilon_\text{cond} - \epsilon_\text{uncond})$. Large $w$ pushes the predicted $x_0$ outside the natural pixel range, and the decoder renders that as clipped, saturated color. Typical safe scales are $w\approx 7.5$ for SD1.x and $\approx 5$ for SDXL; $w > 15$ reliably fries.
**Fix:** Dynamic thresholding (Imagen, Saharia et al. 2022) clamps the predicted $x_0$ by percentile. Guidance rescale (Lin et al. 2023) rescales the guided prediction's std back to the conditional one's. Limited-interval guidance (Kynkäänniemi et al. 2024) applies CFG only in a middle-noise window, for a large quality gain at no diversity cost.
**Detection:** Sweep $w$ and watch histogram clipping. Saturation rising with $w$ is the tell.

## 7. Exposure bias → error compounds over the sampling trajectory

**Symptom:** Long sampling schedules improve less than expected, and samples carry subtle accumulated artifacts short schedules don't.
**Cause:** Training conditions the network on *ground-truth* noised inputs $x_t = \sqrt{\bar\alpha_t}x_0 + \sqrt{1-\bar\alpha_t}\epsilon$, while sampling conditions each step on the model's *own estimate* of the previous step. That distribution shift (train on real $x_t$, infer on approximate $x_t$) compounds across steps.
**Fix:** Perturb the training input slightly (input perturbation, Ning et al. 2023) so the network sees off-manifold inputs like those at inference. Higher-order [[Concept - Diffusion Samplers and Schedulers|solvers]] also cut per-step error.
**Detection:** Compare a deterministic sampler's trajectory with re-noised ground truth at matched timesteps. Growing divergence is exposure bias.

## 8. Unweighted L_simple over-weights easy timesteps → slow convergence

**Symptom:** Training converges slowly and spends most of its gradient budget on high-SNR (nearly clean) timesteps that were already easy.
**Cause:** The vanilla simple loss weights every timestep equally, but how hard denoising is varies wildly across $t$. The easy steps dominate the average and waste capacity.
**Fix:** Min-SNR loss weighting (Hang et al. 2023) caps each timestep's weight at $\min(\text{SNR}(t), \gamma)$ with $\gamma\approx 5$, shifting effort toward the hard mid-noise steps and speeding convergence several-fold.
**Detection:** Plot per-timestep loss. A huge imbalance across $t$ means unweighted training is leaving convergence on the table.

## 9. Square-cropping every training image → center bias and cropped subjects

**Symptom:** The model puts subjects dead center, crops off heads and feet, and struggles with wide or tall aspect ratios.
**Cause:** Center-square-cropping a dataset to a fixed resolution teaches the model that subjects are always centered and edges get cut. It never saw a full-frame, off-center composition.
**Fix:** **Aspect-ratio bucketing**: group images by aspect ratio and train each bucket at its native shape, padding batches instead of cropping content. SDXL also added *crop-conditioning* embeddings (Podell et al. 2023) that tell the model how each training image was cropped, so it can learn *not* to crop at inference. See [[Breakdown - Stable Diffusion]].
**Detection:** Prompt for full-body or wide scenic compositions. Systematic cropping or centering points to square-crop training.

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
