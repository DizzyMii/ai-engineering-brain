---
tags: [deep-dive, domain/multimodal, level/advanced]
aliases: [DDPM, denoising diffusion probabilistic models, score-based generative models]
summary: "How diffusion models learn to reverse a noising process: DDPM math, score matching, parameterizations, schedules, and sampling."
---
> **One-paragraph hook:** Diffusion models generate data by learning to undo a fixed, gradual corruption. You destroy an image with Gaussian noise over hundreds of steps, train a network to predict what was added at each step, then run that prediction backward from pure noise. Next to a single forward pass through a GAN generator that sounds wasteful, and it is. But the training objective is stable (no adversarial min-max, no mode collapse), and the samples are the current ceiling for image and video fidelity. Every modern text-to-image and text-to-video system (Stable Diffusion, Imagen, Sora, FLUX) descends from this framework, even the newer ones that swapped diffusion's specific math for [[Concept - Flow Matching]].

## The mechanism

**Forward process.** Fix a variance schedule $\beta_1, \dots, \beta_T$ (typically $T=1000$). Define $\alpha_t = 1-\beta_t$ and $\bar\alpha_t = \prod_{s=1}^t \alpha_s$. The forward (noising) process is Markovian and Gaussian:

$$q(x_t \mid x_0) = \mathcal{N}\!\left(x_t;\ \sqrt{\bar\alpha_t}\,x_0,\ (1-\bar\alpha_t)\,I\right)$$

It has a closed form, so getting a training example doesn't require simulating $T$ steps. You jump straight to any $t$:

$$x_t = \sqrt{\bar\alpha_t}\,x_0 + \sqrt{1-\bar\alpha_t}\,\epsilon, \qquad \epsilon \sim \mathcal N(0, I)$$

As $t \to T$, $\bar\alpha_t \to 0$ and $x_t$ becomes indistinguishable from pure Gaussian noise.

**Reverse process.** You want the denoising step $p_\theta(x_{t-1}\mid x_t)$. Ho et al. 2020 (DDPM) showed that if the network predicts the added noise $\epsilon$ instead of $x_0$, the variational lower bound on the data log-likelihood simplifies (after dropping a $t$-dependent weighting term) to a plain denoising regression:

$$L_{simple} = \mathbb E_{t,\,x_0,\,\epsilon}\Big[\big\| \epsilon - \epsilon_\theta(x_t, t) \big\|^2\Big]$$

That's the whole training loop: sample a real image, sample a timestep and noise, corrupt, regress. No adversarial discriminator and no likelihood-free tricks, just supervised regression against a moving target ($\epsilon_\theta$ has to work at every noise level).

**Score connection.** Song & Ermon (2019, 2021) show $\epsilon$-prediction is equivalent, up to a known scale factor, to estimating the score $\nabla_x \log p(x_t)$, the gradient of the log-density of the noised data. So diffusion training discretizes a continuous-time stochastic differential equation (SDE) that turns data into noise, and running it backward denoises. Every SDE has a deterministic probability-flow ODE with the *same* marginals, so you can sample by solving an ODE instead of simulating the stochastic reverse chain. That's what makes deterministic samplers like DDIM possible, and later [[Concept - Flow Matching]] itself.

**Parameterizations.** $\epsilon$-prediction is the DDPM default, but the network can just as well predict $x_0$ directly, or the "velocity" $v = \sqrt{\bar\alpha_t}\,\epsilon - \sqrt{1-\bar\alpha_t}\,x_0$ (Salimans & Ho 2022). v-prediction behaves better at very high noise (where the $\epsilon$-prediction target is nearly degenerate) and at the zero-SNR edge, and it's the standard target for distillation. Loss weighting sits on top of any parameterization. Min-SNR-$\gamma$ (Hang et al. 2023) reweights the per-timestep loss so easy low-noise timesteps don't dominate the gradient, and it measurably speeds convergence.

**Noise schedules.** The original linear schedule ($\beta_1{=}10^{-4}$ to $\beta_T{=}0.02$) spends too much of the step budget at very high noise for small images. Nichol & Dhariwal (2021) introduced a cosine schedule that spreads SNR more evenly and improves low-resolution sample quality and log-likelihood. A separate, nastier schedule bug, where standard schedules never actually reach zero SNR, is covered in [[Gotchas - Diffusion Training and Sampling]].

## Architecture / walkthrough

```mermaid
flowchart LR
    subgraph Forward["Forward process q — fixed, closed-form"]
        X0["x0 (image)"] -->|"+ β1 noise"| X1["x1"]
        X1 -->|"..."| Xt["x_t = √ᾱt·x0 + √(1-ᾱt)·ε"]
        Xt -->|"+ βT noise"| XT["x_T ≈ N(0, I)"]
    end
    subgraph Reverse["Reverse process pθ — learned, one εθ call per step"]
        XT -.->|"εθ(x_T, T)"| XTm1["x_(T-1)"]
        XTm1 -.->|"εθ(·,·)"| Xtr["..."]
        Xtr -.->|"εθ(x1, 1)"| X0r["x0 (sample)"]
    end
    XT -.-> Reverse
```

The network $\epsilon_\theta$ runs once per sampling step. Its standard internal shape (pixel-space DDPM; latent-space and DiT variants swap the backbone but keep this conditioning pattern):

```
t (scalar) --> sinusoidal position embedding --> small MLP --> per-block scale/shift (FiLM-style)
x_t (C,H,W)
    -> Down: [ResBlock(+ time-embed) , Self-Attention]  x k, with downsampling, caching skip activations
    -> Mid:  ResBlock -> Self-Attention -> Cross-Attention(text/class embedding) -> ResBlock
    -> Up:   [ResBlock(+ skip-concat) , Self-Attention] x k, with upsampling
    -> output conv -> εθ(x_t, t)  (same shape as x_t)
```

Self-attention only runs at the low-resolution middle stages, since the cost would be quadratic otherwise. Conditioning enters through cross-attention: text, a class label, or, for [[Concept - Classifier-Free Guidance]], the null token. [[Concept - Latent Diffusion]] uses the same wiring for text-to-image.

## Evolution

- Score matching (Song & Ermon 2019) framed generative modeling as learning $\nabla_x \log p(x)$ through denoising score matching at multiple noise levels.
- DDPM (Ho et al. 2020) recast the same idea as a discrete-time Markov chain with a simple regression loss and made it practical.
- DDIM (Song et al. 2021) showed the same trained model admits a non-Markovian, deterministic sampler that needs 20-50 steps instead of 1000.
- [[Concept - Latent Diffusion]] (Rombach et al. 2022) moved the process into a compressed autoencoder latent, putting training and inference within reach of consumer hardware.
- [[Concept - Classifier-Free Guidance]] (Ho & Salimans 2022) gave practitioners a knob to trade diversity for prompt adherence without a separate classifier.
- v-prediction and Karras et al.'s EDM (2022) restated the schedule as noise levels $\sigma$ and unified the design space, improving few-step quality.
- [[Concept - Flow Matching]] (Lipman et al. 2022; rectified flow, Liu et al. 2022) generalized the framework to arbitrary probability paths with a simpler regression target and straighter, cheaper-to-integrate trajectories. SD3 and FLUX train on it.
- [[Concept - Diffusion Transformers (DiT)]] (Peebles & Xie 2023) replaced the convolutional U-Net with a plain transformer over latent patches and showed diffusion quality scales with FLOPs the way LLMs do.

Every step kept the same shell of forward corruption and reverse generation. The path geometry, the backbone and the conditioning mechanism are what changed.

## In practice

Pixel-space DDPM on ImageNet-64 used $T=1000$ and a linear schedule. Almost nobody trains pixel-space diffusion at scale now, because [[Concept - Latent Diffusion]] gets a ~48x cut in spatial elements essentially for free. Inference step counts went from 1000 (ancestral DDPM) to 20-50 (DDIM/[[Concept - Diffusion Samplers and Schedulers]]) to 1-4 with distillation (LCM, ADD). The number of network forward passes is the biggest lever on serving latency, and with classifier-free guidance each step is *two* passes (conditional and unconditional), which is why guidance-distilled models (FLUX-dev/schnell) matter in production. Text conditioning goes in through cross-attention on frozen CLIP or T5 text embeddings. Class-conditional models (e.g., ADM, the diffusion model in classifier guidance's original comparison) add a class embedding into the timestep MLP instead.

## Failure modes

- **Too few sampling steps → blur or structured artifacts.** The reverse process approximates a continuous trajectory with discrete steps, and too coarse a discretization piles up integration error that shows as smeared detail or ringing. Detection: compare FID/visual quality across step counts. For a well-trained model quality should plateau past ~30-50 DDIM steps; if it keeps improving, the sampler or schedule is mismatched.
- **Parameterization/schedule mismatch.** A DDIM/Euler solver tuned for $\epsilon$-prediction run against a v-prediction model (or the reverse) silently gives degraded or shifted outputs, because the solver's update rule assumes a specific target. Detection: outputs look washed out or oversharpened even at high step counts. Check that the sampler's `prediction_type` matches training.
- **Exposure bias.** Training conditions the network on *exact* forward-process samples $x_t$ built from real $x_0$. At inference $x_{t-1}$ is the model's own imperfect estimate, so small early errors compound over hundreds of steps, a train/inference mismatch much like exposure bias in autoregressive sequence models. Detection: samples degrade disproportionately on very long chains or drift toward blur late in generation. Self-conditioning and consistency-style objectives partly mitigate it.

## The non-obvious

The score-matching equivalence is more than elegant theory. It's why deterministic ODE samplers (DDIM and everything after) are *correct* and not a convenient approximation: the probability-flow ODE has exactly the same marginals as the stochastic reverse SDE, so integrating it deterministically samples the same distribution, minus the injected per-step noise. People who haven't absorbed this often think DDIM "cheats" a stochastic process into being deterministic. It actually solves a different, exactly equivalent equation.

A second hard-won lesson: $L_{simple}$ drops the ELBO's per-timestep weighting, so the model *isn't* directly optimizing log-likelihood. It's implicitly reweighted toward mid-noise timesteps. That's why min-SNR-$\gamma$ reweighting (Hang et al. 2023) and cosine schedules (Nichol & Dhariwal 2021) can measurably change perceptual quality even though all of them are "correct" in theory. You can't vary schedule and weighting choices without retraining consequences.

## Connections
- [[Concept - Latent Diffusion]] — the practical move (compress to a VAE latent before doing any of this math) that made diffusion affordable to train and serve; a direct prerequisite-adjacent concept.
- [[Concept - Classifier-Free Guidance]] — the inference-time technique layered on top of the trained $\epsilon_\theta$ to sharpen prompt adherence, built directly on the conditional/unconditional split described here.
- [[Concept - Flow Matching]] — the generalization that replaces the DDPM forward process with an arbitrary probability path, subsuming diffusion as a curved-path special case.
- [[Concept - Diffusion Samplers and Schedulers]] — the numerical-solver detail (DDIM, DPM-Solver++, Karras sigmas) for turning the trained $\epsilon_\theta$ into images in few steps.
- [[Concept - Diffusion Transformers (DiT)]] — the backbone swap (U-Net to transformer) that made diffusion quality scale predictably with compute.
- [[Gotchas - Diffusion Training and Sampling]] — the arcane, hard-won failure modes (zero-terminal-SNR, latent scaling bugs) that this note's clean math doesn't warn you about.
- [[Concept - KL Divergence]] — the ELBO that $L_{simple}$ is a simplification of is built from a sum of KL terms between Gaussians.
- [[Concept - Entropy and Cross-Entropy]] — the information-theoretic frame underlying the variational bound diffusion models are (loosely) optimizing.
- [[Concept - Softmax]] — cross-attention conditioning inside the U-Net uses the same softmax-attention machinery as language transformers.
- [[Snippet - DDPM Training and Sampling Loop]] — the runnable ~30-line version of the training and ancestral-sampling loop derived above.
- [[Concept - Backpropagation]] — the diffusion loss is trained with plain backprop through the denoiser network like any other supervised objective.
- [[Breakdown - Stable Diffusion]] — the system-level case study of this framework deployed at scale, including exact schedules and text-encoder choices across versions.

## Sources
- Ho, Jain, Abbeel (2020) — Denoising Diffusion Probabilistic Models. Introduces the $\epsilon$-prediction reparameterization and $L_{simple}$.
- Song & Ermon (2019) — Generative Modeling by Estimating Gradients of the Data Distribution. The score-matching framing diffusion is equivalent to.
- Song, Meng, Ermon (2021) — Denoising Diffusion Implicit Models (DDIM). The deterministic, non-Markovian few-step sampler.
- Song et al. (2021) — Score-Based Generative Modeling through Stochastic Differential Equations. Unifies diffusion as an SDE/ODE.
- Nichol & Dhariwal (2021) — Improved Denoising Diffusion Probabilistic Models. Cosine noise schedule.
- Salimans & Ho (2022) — Progressive Distillation for Fast Sampling of Diffusion Models. v-prediction.
- Karras, Aittala, Aila, Laine (2022) — Elucidating the Design Space of Diffusion-Based Generative Models (EDM). Sigma-based schedule reframing, Heun sampler.
- Hang et al. (2023) — Efficient Diffusion Training via Min-SNR Weighting Strategy.
