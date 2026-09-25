---
tags: [concept, domain/multimodal, level/frontier]
aliases: [DiT, MMDiT, diffusion transformer]
summary: "Replacing the diffusion U-Net with a plain transformer over latent patches — the backbone swap behind SD3, FLUX, and Sora."
---
> **One-paragraph hook:** For years every serious diffusion model was a convolutional U-Net. It's a good architecture for images, but it doesn't scale predictably the way transformers do, and it can't reuse the LLM training stack (FlashAttention kernels, tensor/pipeline parallelism, the rest of the transformer infrastructure). Peebles & Xie (2023) showed you can drop convolutions entirely, patchify the [[Concept - Latent Diffusion|latent]] the way a [[Concept - Vision Transformers|Vision Transformer]] patchifies pixels, and use a plain transformer as the denoiser. Diffusion then gets the same clean scaling with compute that LLMs get. FLUX, SD3, Sora and PixArt all descend from that one architectural decision.

## The mechanism

Take the latent (an $H\times W\times C$ tensor from [[Concept - Latent Diffusion]]) and patchify it the way ViT patchifies pixels. Split it into non-overlapping $P\times P$ patches, flatten them, project linearly to the model dimension $d$, and add positional information (2D/3D RoPE for patch grids; pick it carefully, because a plain 1D position embedding ignores image geometry). The resulting token sequence goes through a stack of standard [[Deep Dive - The Transformer]] blocks: self-attention plus MLP, with no convolutions anywhere.

The open question is how to inject conditioning (timestep $t$ plus a pooled text/class embedding) without a separate cross-attention path in every block. DiT uses **adaLN-Zero**. An MLP maps the conditioning vector to a per-block scale $\gamma$, shift $\beta$ and gate $\alpha$, applied around each sub-layer:

$$h = \mathrm{LN}(x)\cdot(1+\gamma) + \beta, \qquad x' = x + \alpha \cdot F(h)$$

$F$ is the attention or MLP sub-layer. The gate $\alpha$ is **zero-initialized**, so at the start of training every block is the identity whatever $F$ computes. The network starts as a well-behaved residual stack and the conditioning pathway only "turns on" as training teaches it to. [[Breakdown - Flamingo]]'s tanh-gated cross-attention and [[Concept - ControlNet and Spatial Conditioning for Diffusion]]'s zero convolutions make the same move: graft new conditioning capacity onto a transformer without destabilizing it at step 0.

**MMDiT** (SD3, Esser et al. 2024) extends this to text-to-image, where the conditioning is itself a long sequence (T5/CLIP token embeddings, not one pooled vector). It uses neither adaLN alone nor cross-attention. Text tokens and image tokens get **separate weight streams**, each with its own QKV projections and adaLN parameters, but attention runs *jointly* over the concatenated text+image sequence, so every image token can attend to every text token and back in one operation. Text rendering and prompt adherence come out noticeably better than in single-stream cross-attention U-Nets. The cost is roughly double the parameters in the attention/MLP blocks, since each modality has its own weights.

## In practice

The headline result (Peebles & Xie 2023) is that FID drops smoothly and monotonically as transformer Gflops go up. It's the same "more compute, predictably better" curve [[Concept - Scaling Laws]] found for language models, applied to image quality. That made scaling *the* lever for diffusion quality and pushed aside a lot of research on tweaking U-Net architecture.

There's a second, easily undervalued reason to pick DiT: it inherits the whole LLM systems stack. [[Deep Dive - FlashAttention]] kernels, tensor and pipeline parallelism, and the same [[Concept - RMSNorm and LayerNorm|normalization]] and optimizer recipes teams already run for language models all carry over. Choosing DiT is partly an infrastructure-reuse decision. FLUX.1 (Black Forest Labs, 2024), SD3, Sora and PixArt-$\alpha$ all use DiT-family backbones, and [[Breakdown - Stable Diffusion]] walks through the version-by-version move from U-Net to MMDiT.

The downside is cost. Attention is quadratic in token count, and a patchified high-resolution latent is still thousands of tokens (a $128\times128$ latent at patch size 2 is $64\times64=4096$ tokens). That's why [[Concept - Video Generation]] needs factorized spatial+temporal attention instead of full 3D attention: full attention over a video's spacetime patches is quadratic in a product that's already large before the time axis is added.

## Failure modes

- **Skipping the zero-init gate destabilizes training.** If $\alpha$ doesn't start at zero, the new conditioning pathway injects large, untrained perturbations into every block from step 1. You get the same divergence as grafting an untrained module onto any pretrained network. The gate is required, not optional scaffolding.
- **High-resolution/video token blowup.** Attention cost is quadratic in token count, so naively scaling resolution or clip length blows up memory and latency. Production systems compensate with windowed or factorized attention, harder latent compression, or both.
- **Positional-encoding mismatches hurt spatial coherence.** A badly chosen or badly interpolated 2D/3D RoPE scheme (the interpolation-degradation problem from [[Concept - Any-Resolution Vision Encoding]]) shows up as broken large-scale structure, with objects split across regions and inconsistent geometry, even when local texture looks fine.

## The non-obvious

The DiT scaling result is arguably image generation's "Chinchilla moment". It was the first time GFLOPs vs. quality showed a clean, usable power law for diffusion, and it's what justified labs pouring compute into bigger DiT/MMDiT backbones instead of hand-designing better U-Net blocks.

The less-discussed point: the zero-init-gate trick shows up in this same form across at least three unrelated multimodal systems (Flamingo's gated cross-attention, DiT's adaLN-Zero, ControlNet's zero convolutions). That suggests it belongs to no single architecture and isn't specific to diffusion. It's a general recipe for safely adding a conditioning pathway to an already-trained (or already-stable) network: start the new path's contribution at zero and let gradient descent open the gate.

## Connections
- [[Deep Dive - Diffusion Models]] — the forward/reverse diffusion math the DiT backbone is trained against; DiT is a backbone swap, not a change to the training objective.
- [[Concept - Flow Matching]] — the objective most modern DiT models (SD3, FLUX) actually train with instead of DDPM's epsilon-prediction.
- [[Concept - Latent Diffusion]] — DiT operates on the same compressed VAE latent, just patchified into tokens instead of processed by convolutions.
- [[Concept - Video Generation]] — extends the DiT pattern to spacetime patches, where the quadratic attention-cost problem becomes the dominant engineering constraint.
- [[Deep Dive - The Transformer]] — the base block (self-attention + MLP) DiT reuses wholesale from language modeling.
- [[Deep Dive - FlashAttention]] — the kernel-level optimization that makes DiT's quadratic attention tractable at the token counts high-resolution latents produce.
- [[Concept - RMSNorm and LayerNorm]] — the normalization layer adaLN-Zero modulates per-block; DiT reuses LLM-standard normalization placement.
- [[Concept - Scaling Laws]] — the general phenomenon (predictable quality gains from compute) that Peebles & Xie showed also holds for diffusion transformers.
- [[Breakdown - Stable Diffusion]] — documents the concrete U-Net-to-MMDiT transition across SD1.x/SDXL/SD3.
- [[Gotchas - Diffusion Training and Sampling]] — the training-instability failure modes (including missing zero-init effects) that show up when this backbone is misconfigured.

## Sources
- Peebles, Xie (2023) — Scalable Diffusion Models with Transformers (DiT). Establishes the patchify-latent transformer backbone and the Gflops-vs-FID scaling result.
- Esser, Kulal, et al. (2024) — Scaling Rectified Flow Transformers for High-Resolution Image Synthesis (SD3). Introduces MMDiT's dual-stream joint attention.
