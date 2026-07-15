---
tags: [reference, domain/multimodal, level/core]
aliases: []
summary: "Lookup tables for vision encoders, VLMs, image/video generators, and audio models — params, resolution, token counts, and formulas."
---

# Reference - Vision Encoders and Multimodal Models

## Vision encoders

Patch size $P$ (see [[Concept - Vision Transformers]]) determines both native-resolution handling and the token-count formula below.

| Encoder | Params | Native res | Tokens/image | Objective | License |
|---|---|---|---|---|---|
| CLIP ViT-L/14-336 | 304M | 336px | 576 (24×24) | Contrastive, softmax InfoNCE | Open (OpenAI) |
| SigLIP-So400m/384 | 400M | 384px (up to 448 variants) | ~729 (27×27 grid, patch 14) | Contrastive, sigmoid pairwise | Open |
| DINOv2-L/14 | 300M | 224–518px | resolution-dependent | Self-supervised, no text | Open |
| EVA-CLIP-E | ~4.4B | 224–448px | resolution-dependent | Contrastive, scaled | Open |

*(as of 2026 — the encoder landscape moves; current workhorse default is SigLIP-So400m / SigLIP2)*

## VLMs

*Fusion family follows the [[Concept - VLM Architectures]] taxonomy: Projector, Cross-attention, or Native. Full lineage and derivation of these checkpoints: [[Reference - Model Genealogy]].*

| Model | LLM base | Encoder | Connector | Max image tokens | Fusion family |
|---|---|---|---|---|---|
| LLaVA-1.5/NeXT ([[Breakdown - LLaVA]]) | Vicuna-7B/13B | CLIP ViT-L/14-336 | Linear (1.5: MLP) | 576 (NeXT: up to ~2880 w/ tiling) | Projector |
| Qwen2-VL | Qwen2 | Native dynamic-res ViT | MLP merger (2×2) | variable (native res) | Projector |
| InternVL2 | InternLM/Qwen | InternViT | Pixel-shuffle MLP | variable (dynamic tiling) | Projector |
| Idefics2/3 | Mistral/Llama | SigLIP | Perceiver-style resampler | fixed budget | Projector |
| PaliGemma | Gemma-2B | SigLIP-So400m/224 | Linear | 256 | Projector |
| Flamingo ([[Breakdown - Flamingo]]) | Chinchilla (frozen) | NFNet | Perceiver resampler | 64 (fixed) | Cross-attention |
| Llama-3.2-Vision | Llama-3 (frozen-ish) | CLIP-derived | Cross-attention layers | variable | Cross-attention |

## Image/video generation

| Model | Params | Latent channels | Text encoder(s) | Backbone | Objective |
|---|---|---|---|---|---|
| SD1.5 | 860M (U-Net) | 4 | CLIP ViT-L (77-token cap) | U-Net | DDPM (epsilon-pred) |
| SDXL | 2.6B (U-Net) | 4 | CLIP-L + OpenCLIP-bigG | U-Net + refiner | DDPM (epsilon-pred) |
| SD3 | up to 8B | 16 | CLIP-L + CLIP-bigG + T5-XXL | MMDiT | Rectified flow |
| FLUX.1 | 12B | 16 | T5-XXL + CLIP | DiT | Flow matching |

*(as of 2026 — specs for closed models like DALL-E 3, Imagen, and Sora change without notice; see [[Breakdown - Stable Diffusion]] for the full version-by-version SD detail behind the rows above)*

## Audio models

| Model | Params | Key spec | Notes |
|---|---|---|---|
| Whisper ([[Breakdown - Whisper]]) tiny → large-v3 | 39M → 1.55B | 80 mel bins ([[Concept - Audio Spectrograms and Mel Features]]), 16kHz input | Encoder-decoder, multilingual |
| EnCodec | small | up to 32 RVQ codebooks, ~1.5–24kbps, ~75Hz frame rate | Neural audio codec ([[Concept - Neural Audio Codecs and Residual Vector Quantization]]) |
| DAC (Descript) | small | higher-fidelity RVQ codec, up to 44.1kHz | Common TTS/audio-LM tokenizer |
| VALL-E / XTTS / F5-TTS | varies | audio-token generation conditioned on a short reference clip | Voice-cloning TTS family ([[Concept - Neural Text-to-Speech and Audio Language Models]]) |

## Formulas

- **Image tokens per tile:** $\text{tokens} = \left(\frac{H}{P}\right)\times\left(\frac{W}{P}\right) \div r^2$, where $P$ = patch size, $r$ = pixel-shuffle/unshuffle reduction factor ($r=1$ if none, $r=2$ for a 2×2 merge).
- **AnyRes/tiling total tokens:** $\text{tokens}_{\text{total}} = (\text{tiles} + 1_{\text{thumbnail}}) \times \text{tokens per tile}$ — e.g. 4 tiles + 1 thumbnail at 576 tokens/tile ≈ 2880 tokens for one image.
- **Audio token rate:** $\text{tokens/sec} = \text{frame\_rate} \times N_q$ (codebooks per frame) — e.g. a 75Hz frame rate with 8 codebooks ≈ 600 tokens/sec of audio.
- **VAE latent scaling constant:** latents are multiplied by a fixed constant before/after the diffusion model so their variance ≈ 1 — SD1.x/SDXL: 0.18215 / 0.13025 respectively. Forgetting this constant is a silent-corruption bug, not a crash — see [[Gotchas - Diffusion Training and Sampling]].
- **Latent channel counts**† : 4 for SD1.x/SDXL, 16 for SD3/FLUX — the jump to 16 channels is what fixed most SD1/SDXL fine-detail (text, hands) loss.
- Converting any of the above token counts into actual activation/KV-cache bytes needs [[Reference - Memory Math for Transformers]].

† footnote: "latent channels" are not RGB channels — they are a learned compressed representation with no direct pixel meaning.

## Connections
- [[Concept - VLM Architectures]] — the taxonomy (projector/cross-attention/native) that the VLM table's "fusion family" column encodes.
- [[Breakdown - Stable Diffusion]] — the full version-by-version detail behind the image-generation table's SD rows.
- [[Breakdown - Whisper]] — the full mechanism behind the audio table's Whisper row.
- [[Concept - Vision Transformers]] — the architecture underlying every row of the vision-encoders table; patch size $P$ drives the token-count formula.
- [[Reference - Memory Math for Transformers]] — the companion reference for converting these token counts into actual KV-cache and activation memory in bytes.
- [[Reference - Model Genealogy]] — where these specific checkpoints sit in the broader lineage of open and closed model releases.
- [[Concept - Audio Spectrograms and Mel Features]] — the input representation the Whisper row's "80 mel bins" spec refers to.
- [[Gotchas - Diffusion Training and Sampling]] — the latent-scaling-constant note above is the exact silent-corruption bug this gotchas note catalogs in more detail.
- [[Concept - Neural Audio Codecs and Residual Vector Quantization]] — the mechanism behind the EnCodec/DAC rows.
- [[Concept - Neural Text-to-Speech and Audio Language Models]] — the mechanism behind the VALL-E/XTTS/F5-TTS row.

## Sources
- Radford et al. (2021) — CLIP. Source of the CLIP encoder specs.
- Zhai et al. (2023) — SigLIP. Source of the SigLIP encoder specs.
- Rombach et al. (2022) — Latent Diffusion Models. Source of the SD1.x latent-scaling and channel-count numbers.
- Podell et al. (2023) — SDXL. Source of the SDXL dual-text-encoder and refiner spec.
- Esser et al. (2024) — Scaling Rectified Flow Transformers (SD3). Source of the SD3/MMDiT spec.
- Radford et al. (2022) — Whisper. Source of the Whisper size/mel-bin specs.
