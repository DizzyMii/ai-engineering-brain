---
tags: [concept, domain/neural-networks, level/unicorn]
aliases: [Adam epsilon, Adam eps, bias correction, RAdam, epsilon placement]
summary: "Adam's epsilon and bias correction: placement conventions, fp16 underflow, the warmup/RAdam overlap, and beta2 second-moment memory."
---

# Concept - Adam's Epsilon and Bias Correction

> **One-paragraph hook:** Two of the smallest-looking constants in the [[Concept - Adam and AdamW|Adam]] update — the $\epsilon$ in the denominator and the $(1-\beta^t)^{-1}$ bias-correction factors — are the ones that silently break reproductions and destabilize large runs. $\epsilon$ is not a divide-by-zero guard; it's a regime selector that decides where Adam stops behaving like sign descent, and its default value $10^{-8}$ literally does not exist in fp16. Bias correction isn't a rounding nicety either; skip it and the first ~2000 steps take updates several times too large. Neither matters on a small model in fp32. Both bite at scale and in low precision, which is exactly where you can't afford them to.

## The mechanism

The Adam update (full derivation in [[Concept - Adam and AdamW]], all update rules tabulated in [[Reference - Optimizer Update Rules]]) is, elementwise:

$$m_t = \beta_1 m_{t-1} + (1-\beta_1) g_t, \quad v_t = \beta_2 v_{t-1} + (1-\beta_2) g_t^2$$
$$\hat m_t = \frac{m_t}{1-\beta_1^t}, \quad \hat v_t = \frac{v_t}{1-\beta_2^t}, \quad \theta_t = \theta_{t-1} - \eta \frac{\hat m_t}{\sqrt{\hat v_t} + \epsilon}$$

The arcana live in the two correction factors and in $\epsilon$.

**Bias correction — and which way it actually pushes.** $m$ and $v$ start at 0, so early EMAs underestimate the true first and second moments. Take a persistent gradient $|g|=1$: the *intended* per-coordinate step is $\hat m_t/\sqrt{\hat v_t} \approx 1$ (the smoothed-sign-descent magnitude inherited from [[Concept - Stochastic Gradient Descent and Momentum]]). The *uncorrected* step is $m_t/\sqrt{v_t} = (1-\beta_1^t)/\sqrt{1-\beta_2^t}$. For the standard $(\beta_1,\beta_2)=(0.9,0.999)$ that ratio is **3.2× at step 1, rises to a peak near 6.5× around step ~12, and only decays back to ~1 over the first $\sim\!1/(1-\beta_2)\approx 2000$ steps.** The reason is that $\beta_2 > \beta_1$, so the *second* moment is suppressed far harder than the first, inflating $1/\sqrt{v}$ and making the raw early step too *large*. (This is worth stating carefully because the usual one-line summary — "without correction early steps are too small" — has the sign backwards; it's the second-moment underestimate that dominates.) Bias correction cancels exactly this inflation. Even after correction, $\sqrt{\hat v_t}$ early is estimated from few effective samples, so the adaptive term has high *variance* — the residual that RAdam and warmup exist to handle.

**Epsilon placement — inside vs outside the sqrt.** Adam (and PyTorch/TF) put $\epsilon$ *outside*: $\hat m/(\sqrt{\hat v}+\epsilon)$. LAMB and several variants put it *inside*: $\hat m/\sqrt{\hat v + \epsilon}$. When $\hat v$ is tiny (a well-optimized or flat coordinate) these diverge hard. With $\epsilon=10^{-8}$ the denominator floor is $10^{-8}$ outside but $\sqrt{10^{-8}}=10^{-4}$ inside — four orders of magnitude apart, so the same coordinate can take a step ~$10^4\times$ larger under the outside convention. Porting a config between an Adam-convention and a LAMB-convention codebase silently changes optimization; it is one of the classic cross-framework reproducibility traps.

The deeper point: $\epsilon$ is a **regime selector**. For a coordinate with consistent gradient $g$, $\hat m\approx g$ and $\sqrt{\hat v}\approx|g|$, so the step is $\eta\, g/(|g|+\epsilon)$. When $|g|\gg\epsilon$ this is $\eta\,\mathrm{sign}(g)$ — pure sign descent. When $|g|\ll\epsilon$ it becomes $(\eta/\epsilon)\,g$ — ordinary scaled-gradient (SGD-like) descent. So $\epsilon$ is the gradient-magnitude threshold that separates the sign-descent regime from the linear regime, and *raising* $\epsilon$ deliberately pushes low-signal coordinates into the damped linear regime. That is what "increase eps for stability" actually does.

**Precision — why $10^{-8}$ is fictional in low precision.** fp16's smallest normal is $2^{-14}\approx 6.1\times10^{-5}$ and its smallest subnormal is $2^{-24}\approx 6.0\times10^{-8}$, so $\epsilon=10^{-8}$ flushes to **exactly zero** in fp16 — the denominator floor disappears (see [[Concept - Floating Point for Deep Learning]] and [[Concept - Subnormal Numbers and Gradual Underflow]]). bf16 has the range to hold $10^{-8}$ but only ~2–3 significant decimal digits, so adding it to a $\sqrt{\hat v}\sim 10^{-2}$ rounds straight back to $10^{-2}$ — $\epsilon$ is a no-op. This is one of the concrete reasons Adam's states $m,v$ are kept in an fp32 master copy (8 bytes/param) even when compute runs in bf16 under [[Concept - Mixed Precision Training]].

**Beta2 as second-moment memory.** $\beta_2$ sets the second-moment averaging window at $\sim 1/(1-\beta_2)$ steps: 0.999 → ~1000, 0.98 → ~50, 0.95 → ~20. This choice is coupled to both $\epsilon$ and gradient clipping, and it is the knob most relevant to [[Concept - Training Stability and Loss Spikes]].

## In practice

- **Defaults:** PyTorch/TF AdamW ships $(\beta_1,\beta_2,\epsilon)=(0.9, 0.999, 10^{-8})$ — correct for small nets in fp32. GPT-3 (Brown et al. 2020) used $\beta_2=0.95,\ \epsilon=10^{-8}$; many LLMs use $\beta_2=0.95$ or $0.98$ and raise $\epsilon$ to $10^{-6}$ or even $10^{-5}$ — the "raise Adam eps for big models" folklore catalogued in [[Lore - Hyperparameter Folklore]].
- **Optimizer states are fp32, always.** The whole point of the arcana above is that the numerics don't survive fp16/bf16 storage.
- **Cover the early-variance window** with a linear [[Concept - Learning Rate Schedules for Pretraining|warmup]] of a few hundred to a few thousand steps, or with RAdam. Most LLMs choose warmup; it's simpler and composes with the rest of the schedule.
- **Reproducing a paper across frameworks:** pin $\epsilon$ *placement* (inside vs outside sqrt), confirm bias correction is actually applied (some fused/custom kernels drop or fold it), and match $\beta_2$. These three are the usual reasons two "identical" configs produce different curves.

## Failure modes

- **fp16 $\epsilon$ underflow.** Store states in fp16 with $\epsilon=10^{-8}$ and the floor vanishes; a flat coordinate then divides by $\sqrt{\hat v}$ alone and takes an enormous step → loss spike or NaN. **Detection:** NaNs correlated with low-gradient parameters. **Fix:** fp32 states, or raise $\epsilon$.
- **Skipped bias correction with $\beta_2=0.999$.** The first ~2000 steps run 3–6× too large and high-variance → early divergence or an opening loss spike. Frequently *masked* by warmup, which is why the failure often presents as "it only diverges when I remove warmup." **Detection:** an early spike that vanishes when bias correction or warmup is restored.
- **$\beta_2$ too high at large batch.** A single huge-gradient batch's $g^2$ lingers in $v$ for ~$1/(1-\beta_2)$ steps, suppressing that coordinate's effective LR for ~1000 steps ($\beta_2=0.999$) — a multi-hundred-step scar from one bad batch. **Fix:** $\beta_2=0.95$ plus global-norm clipping.
- **$\epsilon$ too large ($\gtrsim 10^{-3}$).** Too many coordinates fall into the $|g|\ll\epsilon$ linear regime; Adam drifts toward SGD, loses its per-coordinate adaptivity, and its clean LR transfer degrades → slower or worse convergence.
- **Placement mismatch.** Same $\epsilon$ value, different inside/outside convention → silently different training. **Detection:** curves diverge from a reference that used the other framework's convention.

## The non-obvious

Two insights practitioners learn the hard way. First, **$\epsilon$ is a regime selector, not a safety epsilon.** Nearly everyone reads it as "prevent divide-by-zero," but its real job is to set the gradient magnitude below which Adam stops acting like sign descent and reverts to scaled-gradient descent. Raising it from $10^{-8}$ to $10^{-5}$ is a substantive optimization change — a deliberate damping of low-signal directions — not a numerical formality. Second, **bias correction and warmup are partially redundant, and the standard "early steps are too small" summary is wrong.** Because $\beta_2>\beta_1$ inflates $1/\sqrt{v}$, the uncorrected early step is too *large* (verifiably ~3× at step 1, ~6× near step 12); bias correction cancels that deterministic overshoot, while warmup and RAdam (Liu et al. 2019, which frames warmup as a variance-reduction fix for the early adaptive term) tame the residual *variance*. They attack the same early-instability window from two ends — which is exactly why removing bias correction "sometimes doesn't hurt": warmup was quietly covering for it, and you only discover the omission the day you shorten your warmup.

## Connections

- [[Concept - Adam and AdamW]] — the base optimizer; this note is the numerical deep end of its $\epsilon$ and bias-correction terms.
- [[Reference - Optimizer Update Rules]] — the lookup sheet whose footnotes flag exactly the inside-vs-outside $\epsilon$ convention.
- [[Concept - Floating Point for Deep Learning]] — why $10^{-8}$ is unrepresentable in fp16 and lost in bf16.
- [[Concept - Subnormal Numbers and Gradual Underflow]] — the subnormal range ($2^{-24}$) that $\epsilon=10^{-8}$ falls below.
- [[Concept - Mixed Precision Training]] — the fp32 master states that keep $\epsilon$ and $v$ meaningful while compute runs in bf16.
- [[Concept - Stochastic Gradient Descent and Momentum]] — the sign-descent contrast that explains why $\epsilon$'s threshold behavior matters and why Adam LRs transfer.
- [[Concept - Learning Rate Schedules for Pretraining]] — warmup is the standard cover for the early high-variance adaptive term.
- [[Concept - Training Stability and Loss Spikes]] — $\beta_2$ memory, $\epsilon$, and clipping are the levers that turn spikes into divergence or not.
- [[Lore - Hyperparameter Folklore]] — home of the "raise eps / use beta2=0.95 for big models" defaults this note mechanizes.

## Sources

- Kingma & Ba (2015) — Adam: A Method for Stochastic Optimization. Introduces $\epsilon$, the bias-correction factors, and their motivation.
- Loshchilov & Hutter (2019) — Decoupled Weight Decay Regularization. AdamW; context for why the optimizer's numerics are scrutinized at scale.
- Liu et al. (2019) — On the Variance of the Adaptive Learning Rate and Beyond (RAdam). Frames warmup as rectifying the early high-variance adaptive term.
- You et al. (2020) — Large Batch Optimization for Deep Learning (LAMB). The variant whose $\epsilon$-inside-sqrt convention is the reproducibility trap.
- Brown et al. (2020) — Language Models are Few-Shot Learners (GPT-3). Documents $\beta_2=0.95$ at pretraining scale.
