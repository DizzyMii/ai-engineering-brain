---
tags: [concept, domain/multimodal, level/frontier]
aliases: [CFM, conditional flow matching, rectified flow]
summary: "The continuous-time ODE framework that generalizes diffusion with a simpler regression target and straighter sampling paths — powers SD3 and FLUX."
---
> **One-paragraph hook:** [[Deep Dive - Diffusion Models|Diffusion models]] work by design, but their training target — predicting noise added along a specific curved stochastic path — carries a lot of schedule-and-parameterization bookkeeping (recall the zero-terminal-SNR bug and the epsilon/x0/v-prediction split). Flow matching (Lipman et al. 2022) and the closely related rectified flow (Liu et al. 2022) strip that down: pick *any* smooth path from noise to data, and train a network to regress the velocity along that path directly. When the path is chosen to be a straight line, the resulting model is both simpler to train and — crucially — cheaper to sample, because a straight-line ODE needs far fewer numerical-integration steps to approximate accurately than a curved one. This is not an incremental tweak; it's the objective SD3 and FLUX.1 are trained against, and it is quietly replacing DDPM-style diffusion as the default for new image and video generators as of 2026.

## The mechanism

Frame generation as transporting samples from a simple noise distribution $x_1 \sim \mathcal N(0,I)$ to the data distribution $x_0 \sim p_{data}$ along a continuous path indexed by $t \in [0,1]$, governed by a learned **velocity field** $v_\theta(x, t)$ through the ordinary differential equation $dx/dt = v_\theta(x,t)$. Sampling is solving this ODE from $t{=}1$ (noise) to $t{=}0$ (data) with any off-the-shelf ODE integrator (Euler, Heun, RK4).

You can't directly compute the marginal velocity field that transports the *whole* noise distribution to the *whole* data distribution — that's the intractable object you're trying to learn. **Conditional flow matching** sidesteps this with the same trick DDPM used for the score: define a simple, tractable *per-sample* conditional path between one noise sample and one data sample, and regress the network against the known velocity of that path; Lipman et al. show the resulting conditional loss has the same gradient (in expectation) as the intractable marginal objective, so training on the tractable version is valid.

The simplest and most common choice is the **linear (optimal-transport) interpolation path**:

$$x_t = (1-t)\,x_0 + t\,x_1$$

whose time-derivative is trivially constant: $\dot x_t = x_1 - x_0$. The training objective is then just:

$$L_{CFM} = \mathbb E_{t,\,x_0,\,x_1}\Big[\big\| v_\theta(x_t, t) - (x_1 - x_0) \big\|^2\Big]$$

Compare this to diffusion's $L_{simple}$: there's no $\bar\alpha_t$, no schedule-dependent noise-vs-signal weighting to get right — the regression target is just the (constant) straight-line displacement between the two endpoints you sampled. This is what "no noise-schedule bookkeeping" means in practice: the entire schedule-design problem that produces bugs like zero-terminal-SNR (see [[Gotchas - Diffusion Training and Sampling]]) simply doesn't arise in this formulation.

**Rectified flow** (Liu et al. 2022) pushes further: after training once with straight-line conditional paths, resample pairs by running the current model forward and pairing its own noise/output samples, then retrain — a procedure called **reflow**. Because the model's *learned* transport paths are already close to straight, reflow straightens them further, and repeating it can push the ODE toward paths straight enough to integrate accurately in a single step, the basis of some 1-2-step distilled generators.

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

Diffusion is, formally, a **curved-path special case** of the flow-matching framework — the DDPM forward process traces a specific curved trajectory in $(x, t)$ space determined by the noise schedule, whereas conditional flow matching lets you choose the path, and a straight line is both a valid choice and, for numerical integration, close to optimal (a straight line has zero curvature, so a first-order Euler solver's local truncation error is far smaller per step than on a curved SDE-derived path). This reframing is why the switch to flow matching produced fewer required sampling steps largely as a *free* consequence of path geometry, without needing new distillation machinery.

SD3 (Esser et al. 2024) trains with rectified flow and a **logit-normal timestep sampling** distribution — rather than sampling $t$ uniformly, it's sampled so training spends more density on the intermediate timesteps that matter most for quality, with an additional **resolution-dependent shift** to the distribution so higher-resolution images (which need more signal at a given noise level to stay well-posed) get appropriately reweighted timesteps. FLUX.1 (Black Forest Labs 2024) follows the same rectified-flow recipe at 12B parameters, paired with a [[Concept - Diffusion Transformers (DiT)|DiT/MMDiT]] backbone, and ships guidance-distilled variants (`FLUX.1-schnell`) that fold [[Concept - Classifier-Free Guidance|CFG]]-equivalent behavior into the weights for 1-4-step generation. The velocity-prediction target used here is also formally reconcilable with diffusion's v-prediction and the Karras et al. EDM sigma-based reframing — labs converged on flow matching less because it's a wholly different theory and more because it's the cleanest parameterization of the same underlying idea, with better-behaved training and empirically better observed scaling with model size and compute.

## Failure modes

- **ODE-solver error at very few steps.** Even a straight-path model's velocity field is only piecewise-straight in practice (the learned field isn't perfectly linear away from the training distribution), so 1-2-step sampling without reflow/distillation shows visible quality loss — detectable as blur or structural inconsistency that disappears when you add steps or apply a reflow-trained checkpoint.
- **Timestep-sampling distribution matters a lot.** Training with uniform $t$ instead of logit-normal (or without the resolution-dependent shift for high-res images) measurably hurts quality — this is not a minor hyperparameter, it's load-bearing for where the model's capacity gets spent during training.
- **Path choice affects sample quality and speed independent of model capacity** — a curved conditional path (e.g., a variance-preserving diffusion-style path) trained with the same flow-matching machinery does not get the straight-path few-step benefit; the win is specifically from path geometry, not from the regression-loss framing alone.

## The non-obvious

The equivalence between diffusion and flow matching (diffusion as a curved special case) is not just a tidy theoretical unification — it's the insight that let researchers realize the number of sampling steps needed is substantially a *geometric* property of the chosen path, not an intrinsic property of "how hard image generation is." Practitioners coming from diffusion often assume fewer steps requires model-side tricks (distillation, consistency losses); flow matching shows a large chunk of that gain is available for free just by choosing straighter conditional paths at training time, before any distillation is applied at all. A second practitioner-level trap: because the regression target $x_1 - x_0$ is architecture-agnostic, it's tempting to assume flow matching is a drop-in loss swap for an existing diffusion checkpoint — it is not, because the timestep-sampling distribution and the model's implicit noise-schedule assumptions (baked into things like classifier-free guidance scale tuning) are calibrated to the specific path, and porting a diffusion-tuned guidance scale onto a flow-matching model rarely transfers cleanly.

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
