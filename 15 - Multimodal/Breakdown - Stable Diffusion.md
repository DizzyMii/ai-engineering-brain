---
tags: [breakdown, domain/multimodal, level/advanced]
aliases: [SD, SD1.5, SD2, SDXL, SD3, Stable Diffusion]
summary: "The Stable Diffusion family (SD1.x-SD3/FLUX) as an engineered system: VAE, text encoders, U-Net vs MMDiT, across generations."
---
> **What it is:** Stable Diffusion is the open-weights text-to-image family built by CompVis, Stability AI and Runway on the [[Concept - Latent Diffusion|latent diffusion]] recipe, first released August 2022. It was the first high-quality text-to-image system that anyone outside a frontier lab could download, fine-tune and run on one consumer GPU, and every later open image-generation ecosystem (LoRA fine-tuning, ControlNet, Civitai) grew straight out of it. *(current as of 2026; FLUX.1 from Black Forest Labs, the SD3 spiritual successor built by ex-Stability researchers, is the open state of the art as of 2025)*

## The headline numbers

| Version | Year | Backbone | Params | Latent | Text encoder(s) | Resolution | Objective |
|---|---|---|---|---|---|---|---|
| SD1.x | 2022 | U-Net | 860M | 4-ch, 8x VAE (0.18215 scale) | CLIP ViT-L (77-token cap) | 512px | $\epsilon$-pred, linear schedule |
| SD2 | 2022 | U-Net | ~865M | 4-ch, 8x VAE | OpenCLIP-H | 768px | $\epsilon$/v-pred |
| SDXL | 2023 | U-Net | 2.6B | 4-ch, 8x VAE (0.13025 scale) | CLIP-L + OpenCLIP-bigG (concat) | 1024px | $\epsilon$-pred + refiner stage |
| SD3 | 2024 | MMDiT | 2B–8B (by size) | 16-ch VAE | CLIP-L + CLIP-bigG + T5-XXL | 1024px+ | rectified flow |
| FLUX.1 | 2024 | DiT | 12B | 16-ch VAE | CLIP + T5-XXL | 1024px+ | flow matching, guidance-distilled variants |

Training scale for the original release: SD1.4 trained on a LAION-2B-en aesthetic subset for approximately 150,000 A100-hours. *Folklore, weakly sourced:* on the order of $600K in compute, per [[Lore - The Stable Diffusion Release and Its Aftermath]].

## How it works

Every version splits into the same three pieces, first formalized in [[Concept - Latent Diffusion]]: an **autoencoder** that compresses pixels into a small latent, a **text conditioner** that turns the prompt into a sequence of embeddings, and a **denoiser** that runs [[Deep Dive - Diffusion Models|iterative denoising]] in latent space, steered by those embeddings.

```mermaid
flowchart LR
    P["Text prompt"] --> TE["Text encoder(s)\nCLIP / CLIP+T5"]
    TE --> CE["Conditioning embeddings"]
    N["Random noise latent"] --> D{"Denoiser loop\nN steps"}
    CE -->|"cross-attn (U-Net)\nor joint-attn (MMDiT)"| D
    D -->|"CFG: 2x forward per step"| D
    D --> Z["Final latent z0"]
    Z --> VAE["VAE decoder"]
    VAE --> IMG["Pixel image"]
```

In SD1.x/2/SDXL the denoiser is a convolutional U-Net. The CLIP text encoder's token embeddings are the keys/values in [[Concept - Attention Mechanism|cross-attention]] layers at every resolution level, as in the latent diffusion note. SDXL concatenates a second, larger text encoder (OpenCLIP-bigG) with the first for richer conditioning, and adds a separate **refiner** model that runs a few extra high-noise-avoiding steps to sharpen detail.

SD3 swaps the U-Net for an [[Concept - Diffusion Transformers (DiT)|MMDiT]] backbone, where text and image tokens keep separate weight streams but attend jointly. It also moves the objective to [[Concept - Flow Matching|rectified flow]] and adds T5-XXL as a third text encoder to fix legible-text rendering, which CLIP alone does badly.

At inference every version applies [[Concept - Classifier-Free Guidance]] (doubling per-step cost) and a [[Concept - Diffusion Samplers and Schedulers|sampler]] such as DPM-Solver++ to reach a finished latent in 20-50 steps (fewer for FLUX's guidance-distilled schnell variant), then decodes once through the VAE.

## The clever parts

1. **Latent compression makes the whole thing possible.** Diffusing at $64\times64\times4$ instead of $512\times512\times3$ cuts the elements processed per step by ~48x. That one decision is why SD1.5 trains and runs on a single consumer GPU and doesn't need a lab-scale cluster.
2. **Cross-attention text conditioning.** Feeding the text embedding into the U-Net as cross-attention keys/values at every spatial resolution lets the prompt steer both coarse composition and fine local detail. A single global style vector couldn't do that.
3. **SDXL's size/crop conditioning.** SD1.x trained on square-cropped images, so it learned that subjects are centered and cropped. You can see it in the ubiquitous "close-up cropped face" look of SD1.x outputs. SDXL feeds the *original image size and crop offset* in as an explicit input. The model learns what cropped and full compositions look like and can be asked for an uncropped one at inference. The data artifact becomes a controllable variable instead of something to scrub from the training set.
4. **SD3's dual-stream MMDiT plus T5.** Separate per-modality weight streams with joint attention, plus a real language-model text encoder (T5-XXL) next to CLIP, gave the first Stable Diffusion generation that could render short strings of legible text reliably. Every earlier version failed at this, embarrassingly.
5. **16-channel latents in SD3/FLUX.** Going from 4 to 16 latent channels (vs. SD1.x/SDXL) recovers detail like hands, small text and fine texture that the old 8x-compression-at-4-channels bottleneck couldn't represent at all. It goes straight at the fidelity ceiling described in [[Concept - Latent Diffusion]].
6. **Rectified flow as the objective.** Regressing on a straight-line velocity target ($x_1 - x_0$) is a simpler loss than DDPM's noise-schedule bookkeeping. Empirically it scales better and gives straighter ODE trajectories, and straighter paths integrate accurately in fewer steps. That's part of why FLUX's distilled variants look good at 1-4 steps.

## What it got wrong / what's dated

SD1.x's 4-channel, 8x-compressed VAE is a hard fidelity ceiling no denoiser improvement can fix. Hands, faces and small text were reliably broken until the 16-channel SD3/FLUX latent arrived. The CLIP text encoder's 77-token cap silently truncates long or detailed prompts.

Data provenance turned into a real liability. LAION-5B, the web-scraped dataset behind training, was pulled in 2023 after Stanford researchers found CSAM in it, and Getty Images v. Stability AI and Andersen v. Stability AI became the defining copyright test cases for the field. [[Lore - The Stable Diffusion Release and Its Aftermath]] has the full timeline. SD3's 2024 release also shipped with a restrictive commercial license, and the community backlash helped push open-model momentum toward FLUX.1, built by ex-Stability researchers at Black Forest Labs.

## What to steal

The VAE + conditioner + denoiser split is a reusable blueprint for *any* modality-conditioned generative system. It separates what compressed representation you generate in, how generation is steered, and what the generative process looks like, and you can upgrade each piece on its own (SD3 swapped the denoiser and kept the conditioning approach).

SDXL's size/crop conditioning is worth stealing by itself. When your training data has a systematic bias you can't fully remove, try conditioning on the bias explicitly so the model learns the biased and unbiased cases as separate, controllable modes.

SD3's multi-encoder text conditioning, a contrastive vision-language encoder concatenated with a real language model, is a good default when a system needs both semantic image-text alignment and actual language understanding (long prompts, legible text, complex instructions) that a CLIP-style encoder can't provide alone.

## Connections
- [[Concept - Latent Diffusion]] — the foundational architectural pattern (compressed autoencoder + diffusion in latent space) every Stable Diffusion version is an instance of.
- [[Deep Dive - Diffusion Models]] — the DDPM math SD1.x/2/SDXL train against before SD3 moves to flow matching.
- [[Concept - Diffusion Transformers (DiT)]] — the MMDiT backbone SD3 and FLUX adopt in place of the U-Net.
- [[Concept - Flow Matching]] — the rectified-flow training objective SD3 and FLUX use instead of DDPM's noise-prediction loss.
- [[Concept - CLIP and Contrastive Vision-Language Training]] — the text encoder family (CLIP-L, OpenCLIP-H/bigG) used across every SD version, later supplemented by T5 in SD3.
- [[Lore - The Stable Diffusion Release and Its Aftermath]] — the release history, LAION-5B/CSAM reckoning, and copyright litigation this breakdown treats as out of scope.
- [[Concept - Classifier-Free Guidance]] — the inference-time technique every version applies to trade diversity for prompt adherence.
- [[Reference - Vision Encoders and Multimodal Models]] — the lookup table with exact per-version parameter counts, latent channels, and scaling constants.
- [[Concept - Diffusion Samplers and Schedulers]] — the solver choice (DDIM, DPM-Solver++) applied at inference on top of any SD checkpoint.
- [[Gotchas - Diffusion Training and Sampling]] — the exact scaling-constant, fp16-VAE-NaN, and zero-terminal-SNR failure modes specific to this model family.
- [[Deep Dive - LoRA]] — the dominant lightweight customization method the open-source SD ecosystem standardized on for style and subject fine-tuning.
- [[Concept - Attention Mechanism]] — the cross-attention operation that injects text conditioning into the U-Net, and the joint attention MMDiT generalizes it to.

## Sources
- Rombach, Blattmann, Lorenz, Esser, Ommer (2022) — High-Resolution Image Synthesis with Latent Diffusion Models. The architecture behind SD1.x.
- Podell et al. (2023) — SDXL: Improving Latent Diffusion Models for High-Resolution Image Synthesis. Dual text encoders, size/crop conditioning, refiner.
- Esser, Kulal, et al. (2024) — Scaling Rectified Flow Transformers for High-Resolution Image Synthesis (SD3). MMDiT and rectified flow.
- Black Forest Labs (2024) — FLUX.1 model release. DiT + flow matching successor built by ex-Stability researchers.
