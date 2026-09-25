---
tags: [snippet, domain/multimodal, level/advanced]
aliases: [DDPM, DDIM sampling, diffusion training loop, minimal diffusion]
summary: "Minimal runnable PyTorch DDPM: schedule buffers, the L_simple training step, and a deterministic DDIM sampler on toy 2D data."
---
> **What it does:** trains a tiny MLP to denoise samples from a 2D "two-moons" distribution with the DDPM simple loss (Ho et al. 2020), then generates new samples with a deterministic DDIM loop (Song et al. 2021). Every essential piece of a real image-diffusion trainer is here: the closed-form forward process, the noise-schedule buffers, the ε-prediction MSE, the sinusoidal timestep embedding and few-step deterministic sampling. The U-Net is swapped for a 4-layer MLP so the whole thing runs on CPU in under a minute.
>
> **Dependencies:** `python>=3.10`, `torch>=2.0`, `scikit-learn>=1.0`, `numpy`. CPU is fine.
>
> **Expected output:** a printed loss that falls and settles around the **0.03–0.05** band (low because two-moons is nearly a 1-D manifold, so ε is very predictable from $x_t$ and $t$), and final samples with mean ~0 and std ~1 that trace the two-moons shape.

```python
"""Minimal DDPM (Ho et al. 2020) + deterministic DDIM sampler (Song et al. 2021)."""
import math
import torch
import torch.nn as nn
from sklearn.datasets import make_moons

torch.manual_seed(0)

# ---- 1. Noise schedule: precompute once. A real trainer caches these as buffers. ----
T = 1000
betas       = torch.linspace(1e-4, 2e-2, T)      # linear beta schedule (DDPM)
alphas      = 1.0 - betas
alphas_bar  = torch.cumprod(alphas, dim=0)       # ᾱ_t = Π_{s≤t} α_s
sqrt_ab     = torch.sqrt(alphas_bar)             # √ᾱ_t
sqrt_1m_ab  = torch.sqrt(1.0 - alphas_bar)       # √(1-ᾱ_t)

# ---- 2. Sinusoidal timestep embedding (same construction as Transformer pos-enc) ----
def timestep_embedding(t, dim=64):
    half  = dim // 2
    freqs = torch.exp(-math.log(10000) * torch.arange(half) / half)
    args  = t[:, None].float() * freqs[None]
    return torch.cat([torch.cos(args), torch.sin(args)], dim=-1)

# ---- 3. The denoiser ε_θ(x_t, t): a tiny MLP standing in for a U-Net/DiT ----
class EpsMLP(nn.Module):
    def __init__(self, data_dim=2, t_dim=64, h=128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(data_dim + t_dim, h), nn.SiLU(),
            nn.Linear(h, h),                nn.SiLU(),
            nn.Linear(h, h),                nn.SiLU(),
            nn.Linear(h, data_dim),
        )
    def forward(self, x, t):
        return self.net(torch.cat([x, timestep_embedding(t)], dim=-1))

# ---- 4. Forward process: closed form q(x_t | x_0), jump to any t in one shot ----
def q_sample(x0, t, eps):
    #  x_t = √ᾱ_t · x0 + √(1-ᾱ_t) · ε
    return sqrt_ab[t][:, None] * x0 + sqrt_1m_ab[t][:, None] * eps

# ---- 5. Training on L_simple = E‖ ε − ε_θ(x_t, t) ‖² ----
def train(steps=20000, bs=256):
    x, _ = make_moons(n_samples=8192, noise=0.05)
    x0_all = torch.tensor(x, dtype=torch.float32)
    x0_all = (x0_all - x0_all.mean(0)) / x0_all.std(0)         # standardize to ~N(0,1)
    model  = EpsMLP()
    opt    = torch.optim.Adam(model.parameters(), lr=1e-3)
    for step in range(steps):
        x0  = x0_all[torch.randint(0, x0_all.shape[0], (bs,))]
        t   = torch.randint(0, T, (bs,))                       # t ~ Uniform{0..T-1}
        eps = torch.randn_like(x0)
        xt  = q_sample(x0, t, eps)
        loss = ((eps - model(xt, t)) ** 2).mean()              # MSE, no ELBO weighting
        opt.zero_grad(); loss.backward(); opt.step()
        if step % 2000 == 0:
            print(f"step {step:5d}  loss {loss.item():.4f}")
    return model

# ---- 6. Deterministic DDIM sampler (η=0): ~50 steps instead of 1000 ----
@torch.no_grad()
def ddim_sample(model, n=2000, steps=50):
    x  = torch.randn(n, 2)                                     # x_T ~ N(0, I)
    ts = torch.linspace(T - 1, 0, steps).long()
    for i in range(steps):
        t      = ts[i]
        eps    = model(x, torch.full((n,), t))
        ab_t   = alphas_bar[t]
        x0_hat = (x - torch.sqrt(1 - ab_t) * eps) / torch.sqrt(ab_t)   # predict x0
        if i < steps - 1:
            ab_prev = alphas_bar[ts[i + 1]]
            x = torch.sqrt(ab_prev) * x0_hat + torch.sqrt(1 - ab_prev) * eps  # DDIM step
        else:
            x = x0_hat
    return x

if __name__ == "__main__":
    model   = train()
    samples = ddim_sample(model)
    print("sample mean:", [round(v, 3) for v in samples.mean(0).tolist()],
          " std:",        [round(v, 3) for v in samples.std(0).tolist()])
```

## Why it's written this way

**`L_simple` drops the ELBO weighting on purpose.** The true variational bound weights each timestep's loss by a $t$-dependent factor. Ho et al. 2020 found that *deleting* those weights, leaving plain uniform-over-$t$ MSE on the predicted noise, trains better and is simpler. So the loss is a bare `.mean()` with no schedule term. (Rebalancing $t$ *back* with min-SNR came later; see [[Gotchas - Diffusion Training and Sampling]].)

**Predict ε, not $x_0$.** At high $t$, $x_t$ is almost pure noise and *already contains* most of ε, so the network only has to subtract the small $\sqrt{\bar\alpha_t}x_0$ contribution. ε is a better-conditioned regression target than $x_0$ across the whole schedule, which is why the same trained weights sample cleanly. The [[Concept - Backpropagation|gradients]] flow through a single MSE. No reparameterization tricks are needed, because `q_sample` is a closed-form linear combination.

**DDIM (η=0) is deterministic and few-step.** Ancestral DDPM sampling needs ~1000 stochastic steps. DDIM keeps the same training marginals but defines a *non-Markovian* deterministic reverse process, so the same weights generate in ~50 steps by repeatedly estimating $x_0$ and re-noising to the next timestep. That's why production samplers exist at all; see [[Concept - Diffusion Samplers and Schedulers]].

**The net is a 4-layer MLP because this is a teaching example.** The schedule buffers, `q_sample`, the training step and the DDIM loop are byte-for-byte what a real trainer uses; only `EpsMLP` would become a U-Net or [[Deep Dive - Diffusion Models|DiT]]. The **sinusoidal timestep embedding** is deliberately the same $\sin/\cos$ construction as [[Concept - Positional Encoding]], since timestep conditioning and sequence position are the same problem: inject a scalar index as a smooth vector.

To add text conditioning and [[Concept - Classifier-Free Guidance]], drop the condition ~10% of the time in training and extrapolate `eps_cond`/`eps_uncond` at sampling. Mechanically that's a two-line change to the loop above, and it costs a second forward pass per step.

## Connections
- [[Deep Dive - Diffusion Models]] — the derivation this code implements: forward/reverse processes, the ELBO, and where `L_simple` comes from.
- [[Concept - Diffusion Samplers and Schedulers]] — DDIM is the simplest member; DPM-Solver/Euler/Karras generalize the sampling loop shown here.
- [[Concept - Classifier-Free Guidance]] — the standard conditioning technique layered onto this loop with a two-line change.
- [[Concept - The Training Loop]] — the generic sample→forward→loss→backward→step structure this specializes for diffusion.
- [[Concept - Backpropagation]] — the single-MSE gradient path that makes the closed-form forward process trainable.
- [[Concept - Positional Encoding]] — the sinusoidal timestep embedding reuses the transformer's positional-encoding construction verbatim.
- [[Gotchas - Diffusion Training and Sampling]] — the real-world traps (EMA weights, zero-terminal-SNR, parameterization mismatch) this toy loop deliberately omits.

## Sources
- Ho, Jain, Abbeel (2020) — Denoising Diffusion Probabilistic Models. Defines the forward/reverse processes and the `L_simple` ε-prediction objective.
- Song, Meng, Ermon (2021) — Denoising Diffusion Implicit Models (DDIM). The deterministic, few-step non-Markovian sampler implemented in step 6.
