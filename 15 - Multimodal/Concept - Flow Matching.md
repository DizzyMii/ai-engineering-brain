---
tags: [concept, domain/multimodal, level/frontier]
aliases: [CFM, conditional flow matching, rectified flow]
summary: "The continuous-time ODE framework that generalizes diffusion with a simpler regression target and straighter sampling paths — powers SD3 and FLUX."
---
> **One-paragraph hook:** [[Deep Dive - Diffusion Models|Diffusion models]] work by design, but their training target (predict the noise added along a specific curved stochastic path) drags a lot of schedule-and-parameterization bookkeeping with it. Think of the zero-terminal-SNR bug and the epsilon/x0/v-prediction split. Flow matching (Lipman et al. 2022) and the closely related rectified flow (Liu et al. 2022) strip that down. Pick *any* smooth path from noise to data and train a network to regress the velocity along it. Make the path a straight line and the model is simpler to train and cheaper to sample, because a straight-line ODE needs far fewer integration steps to approximate accurately than a curved one. SD3 and FLUX.1 are trained on this objective, and as of 2026 it's steadily replacing DDPM-style diffusion as the default for new image and video generators.

## The mechanism

Treat generation as moving samples from a simple noise distribution $x_1 \sim \mathcal N(0,I)$ to the data distribution $x_0 \sim p_{data}$ along a continuous path indexed by $t \in [0,1]$. A learned **velocity field** $v_\theta(x, t)$ drives it through the ODE $dx/dt = v_\theta(x,t)$. Sampling means solving that ODE from $t{=}1$ (noise) to $t{=}0$ (data) with any off-the-shelf integrator (Euler, Heun, RK4).

You can't compute the marginal velocity field that carries the *whole* noise distribution to the *whole* data distribution; that intractable object is what you're trying to learn. **Conditional flow matching** gets around it with the trick DDPM used for the score. Define a simple, tractable *per-sample* path between one noise sample and one data sample, and regress the network on that path's known velocity. Lipman et al. show the conditional loss has the same gradient (in expectation) as the intractable marginal objective, so training on the tractable one is valid.

The simplest and most common choice is the **linear (optimal-transport) interpolation path**:

$$x_t = (1-t)\,x_0 + t\,x_1$$

Its time-derivative is constant: $\dot x_t = x_1 - x_0$. The training objective is then:

$$L_{CFM} = \mathbb E_{t,\,x_0,\,x_1}\Big[\big\| v_\theta(x_t, t) - (x_1 - x_0) \big\|^2\Big]$$

Next to diffusion's $L_{simple}$ there's no $\bar\alpha_t$ and no schedule-dependent noise-vs-signal weighting to get right. The target is the constant straight-line displacement between the two endpoints you sampled. That's what "no noise-schedule bookkeeping" means in practice: the schedule-design problem that produces bugs like zero-terminal-SNR (see [[Gotchas - Diffusion Training and Sampling]]) doesn't exist in this formulation.

**Rectified flow** (Liu et al. 2022) goes a step further. After one round of training on straight-line conditional paths, run the current model forward, pair its own noise/output samples, and retrain. That's **reflow**. The model's *learned* transport paths are already nearly straight, reflow straightens them more, and repeating it can get paths straight enough to integrate accurately in one step. Some 1-2-step distilled generators are built on this.

```
Diffusion (curved path, schedule-dependent):        Flow matching (straight OT path):

  x1 (noise)                                            x1 (noise)
     \_                                                    \
       \___                                                 \
           \___     <- curved SDE/ODE trajectory              \   <- straight-line ODE
               \___     shaped by β_t schedule                  \
                   \__                                            \
                      x0 (data)                                    x0 (data)

  more curvature -> more discretization error          less curvature -> fewer steps needed
  per fixed step count                                 for the same integration accuracy
```

## In practice

Formally, diffusion is a **curved-path special case** of flow matching. The DDPM forward process traces a particular curved trajectory in $(x, t)$ space set by the noise schedule. Conditional flow matching lets you pick the path, and a straight line is both valid and, for numerical integration, close to optimal: zero curvature means a first-order Euler solver's local truncation error per step is far smaller than on a curved SDE-derived path. So the switch to flow matching cut the required sampling steps largely for *free*, from path geometry alone, with no new distillation machinery.

SD3 (Esser et al. 2024) trains with rectified flow and **logit-normal timestep sampling**. $t$ isn't drawn uniformly; training puts more density on the intermediate timesteps that matter most for quality. A **resolution-dependent shift** on top reweights timesteps for higher-resolution images, which need more signal at a given noise level to stay well-posed. FLUX.1 (Black Forest Labs 2024) uses the same rectified-flow recipe at 12B parameters on a [[Concept - Diffusion Transformers (DiT)|DiT/MMDiT]] backbone and ships guidance-distilled variants (`FLUX.1-schnell`) that fold [[Concept - Classifier-Free Guidance|CFG]]-equivalent behavior into the weights for 1-4-step generation.

The velocity-prediction target also reconciles formally with diffusion's v-prediction and with the Karras et al. EDM sigma-based reframing. Labs converged on flow matching less because it's a different theory and more because it's the cleanest parameterization of the same idea, with better-behaved training and empirically better observed scaling with model size and compute.

## Failure modes

- **ODE-solver error at very few steps.** Even a straight-path model's velocity field is only piecewise-straight in practice (the learned field isn't perfectly linear away from the training distribution). Sampling in 1-2 steps without reflow/distillation loses visible quality. It shows as blur or structural inconsistency that goes away when you add steps or use a reflow-trained checkpoint.
- **The timestep-sampling distribution matters a lot.** Uniform $t$ instead of logit-normal (or no resolution-dependent shift for high-res images) measurably hurts quality. It decides where the model spends its capacity during training, so treat it as a major hyperparameter.
- **Path choice affects quality and speed independently of model capacity.** A curved conditional path (e.g., a variance-preserving diffusion-style path) trained with the same flow-matching machinery doesn't get the straight-path few-step benefit. The win comes from path geometry. The regression-loss framing alone doesn't provide it.

## The non-obvious

Diffusion being a curved special case of flow matching is more than a tidy unification. It showed that the number of sampling steps you need is largely a *geometric* property of the chosen path, and much less an intrinsic measure of "how hard image generation is". People coming from diffusion often assume fewer steps needs model-side tricks (distillation, consistency losses). Flow matching gets a large chunk of that gain for free by choosing straighter conditional paths at training time, before any distillation.

A second trap: the regression target $x_1 - x_0$ is architecture-agnostic, so it's tempting to treat flow matching as a drop-in loss swap for an existing diffusion checkpoint. It isn't one. The timestep-sampling distribution and the model's implicit noise-schedule assumptions (baked into things like classifier-free guidance scale tuning) are calibrated to the specific path, and a diffusion-tuned guidance scale rarely transfers cleanly to a flow-matching model.

## Connections
- [[Deep Dive - Diffusion Models]] — flow matching generalizes this exact framework; diffusion is a curved-path special case of the conditional flow-matching objective.
- [[Concept - Diffusion Transformers (DiT)]] — the transformer backbone flow-matching objectives are typically paired with (SD3's MMDiT, FLUX) to get compute-scaling benefits.
- [[Breakdown - Stable Diffusion]] — SD3's move to rectified flow with logit-normal timestep sampling is documented there as a concrete deployed system.
- [[Concept - Diffusion Samplers and Schedulers]] — the ODE integrators (Euler, Heun) used to solve the flow-matching velocity field at sampling time.
- [[Concept - KL Divergence]] — the theoretical connection between probability-path transport and divergence-minimizing generative objectives that both diffusion and flow matching instantiate.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the velocity field $v_\theta$ is, like any deep network, ultimately a composition of matmuls whose FLOP cost sets the per-step sampling budget.
- [[Concept - Video Generation]] — flow-matching objectives are the current default for state-of-the-art video generators, where step-count reduction from straight paths matters even more given per-frame cost.
- [[Concept - Scaling Laws]] — one cited reason labs adopted flow matching over diffusion is better-observed scaling behavior with model size and compute, echoing the scaling-law framing from language models.
- [[Gotchas - Diffusion Training and Sampling]] — several diffusion-specific arcana (schedule bugs, SNR mismatches) this note's mechanism explicitly sidesteps by construction, worth reading to see what flow matching is escaping.
- [[Concept - Classifier-Free Guidance]] — still applied (or distilled away) on top of flow-matching models, but the extrapolation's interaction with a straight-line ODE path differs from the diffusion case.

## Sources
- Lipman, Chen, Ben-Hamu, Nickel, Le (2022) — Flow Matching for Generative Modeling. Introduces conditional flow matching and the tractable-conditional-objective proof.
- Liu, Gong, Liu (2022) — Flow Straight and Fast: Learning to Generate and Transfer Data with Rectified Flow. Straight-line paths and the reflow procedure.
- Esser, Kulal, Blattmann, et al. (2024) — Scaling Rectified Flow Transformers for High-Resolution Image Synthesis. SD3's rectified-flow + logit-normal timestep training recipe.
- Karras, Aittala, Aila, Laine (2022) — Elucidating the Design Space of Diffusion-Based Generative Models. The sigma/velocity reframing that unifies with the flow-matching view.
