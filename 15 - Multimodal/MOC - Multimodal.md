---
tags: [moc, domain/multimodal, level/surface]
aliases: []
summary: "Map of Multimodal: vision-language alignment, VLM architectures, diffusion/flow image generation, and audio/speech models."
---

# MOC - Multimodal

This domain owns everything that gets a model past pure text: aligning images, audio, and video into a shared representation space with language, building vision-language models that can see and reason, and generating pixels and waveforms rather than just tokens. It matters because the frontier has moved from text-only chat to models that read screenshots, watch video, generate images and speech, and act as agents in visual environments — and each of those capabilities rests on specific, learnable mechanisms (contrastive alignment, cross-attention grafting, denoising diffusion, discrete audio codecs) rather than being a free side effect of scale. The notes here run from the surface idea of a shared embedding space, through the core mechanics of ViTs, CLIP-style pretraining, and VLM connectors, into advanced territory — any-resolution encoding, latent diffusion, neural audio codecs — and out to frontier work on native any-to-any models and video diffusion, plus unicorn folklore on modality-gap geometry and the Stable Diffusion release wars. Multimodal systems inherit every failure mode of their text-only cousins and add new ones — vision towers that are functionally blind to certain patterns, token budgets that blow up with resolution, audio codecs that leak speaker identity — so this domain treats perception and generation as engineering problems with their own numbers, not as a bullet point on a model card.

## Start here

- **Surface** → [[Concept - Cross-Modal Representation Alignment]] — the core idea underlying everything else in this domain: projecting images, audio, and text into a shared or fused space so attention and comparison can work across modalities.
- **Core** → [[Concept - CLIP and Contrastive Vision-Language Training]] — the dual-encoder contrastive recipe that produces the zero-shot image-text embedding space nearly every VLM vision tower descends from.
- **Advanced** → [[Deep Dive - Diffusion Models]] — the full DDPM math, score matching, parameterizations, and sampling machinery underneath every modern image and video generator.
- **Frontier** → [[Concept - Native and Any-to-Any Multimodal Models]] — the shift from bolted-on encoders (projectors, cross-attention) to a single transformer that natively processes and generates multiple modalities.
- **Unicorn** → [[Lore - The Stable Diffusion Release and Its Aftermath]] — the 2022-2024 war story of open text-to-image: the SD1.4/1.5 release, LAION, the NovelAI leak, the SD3 license revolt, and the lawsuits.

## Cross-modal foundations

- [[Concept - Cross-Modal Representation Alignment]] — how images, audio, and text get projected into a shared or fused representation so attention can work across modalities.
- [[Concept - Vision Transformers]] — treating an image as a sequence of patch tokens and running it through a standard transformer instead of a CNN.
- [[Concept - CLIP and Contrastive Vision-Language Training]] — dual-encoder contrastive pretraining on image-text pairs that produces a shared embedding space usable zero-shot.
- [[Concept - SigLIP and the Sigmoid Contrastive Loss]] — the per-pair sigmoid contrastive loss that decouples image-text pretraining from global batch size and became the default VLM vision tower.
- [[Concept - The Modality Gap in Contrastive Models]] — why CLIP image and text embeddings live in two separate cones despite being trained to match, and what that breaks.
- [[Concept - Register Tokens and ViT Attention Artifacts]] — ViTs stash high-norm global features in junk background patches, wrecking attention maps; register tokens give them a scratchpad instead.

## Vision-language models

- [[Concept - VLM Architectures]] — the three ways to get an image into an LLM — cross-attention, projector/prefix, and native fusion — and the design axes that separate them.
- [[Concept - Vision-Language Connectors]] — the module that turns vision-encoder features into LLM tokens — MLP vs resampler vs pixel-shuffle — and the token-count/detail tradeoff it controls.
- [[Concept - Any-Resolution Vision Encoding]] — feeding arbitrary-size images to a fixed-grid ViT: AnyRes tiling, position interpolation, patch-packing, and native dynamic resolution.
- [[Breakdown - LLaVA]] — the reproducible open VLM recipe: frozen CLIP + a projector + Vicuna, trained on GPT-4-distilled instruction data in two stages.
- [[Breakdown - Flamingo]] — DeepMind's cross-attention VLM: frozen NFNet + frozen Chinchilla grafted with zero-init gated cross-attention for few-shot multimodality.
- [[Concept - Native and Any-to-Any Multimodal Models]] — models that process and generate multiple modalities in one transformer with no bolted-on encoder — past projector/cross-attention VLMs.
- [[Gotchas - Vision-Language Models]] — recurring VLM failure modes — blind models, token-budget blowup, OCR failure, hallucination — symptoms, causes, fixes, detection.
- [[Decision - Choosing a Vision Encoder for a VLM]] — picking a VLM's vision tower: SigLIP-So400m is the 2025 default; DINOv2 fusion for grounding; resolution vs. token budget is the core tradeoff.
- [[Playbook - Training a VLM from a Vision Encoder and an LLM]] — recipe for building a projector-style VLM from a pretrained vision encoder and LLM: two-stage training, wire-checks, verification probes.
- [[Reference - Vision Encoders and Multimodal Models]] — lookup tables for vision encoders, VLMs, image/video generators, and audio models — params, resolution, token counts, and formulas.

## Diffusion and image generation

- [[Deep Dive - Diffusion Models]] — how diffusion models learn to reverse a noising process: DDPM math, score matching, parameterizations, schedules, and sampling.
- [[Concept - Latent Diffusion]] — running diffusion in a compressed VAE latent space instead of pixels — the pattern behind every modern Stable Diffusion-family model.
- [[Concept - Classifier-Free Guidance]] — the inference-time trick that trades sample diversity for prompt adherence by extrapolating away from the unconditional prediction.
- [[Concept - Flow Matching]] — the continuous-time ODE framework that generalizes diffusion with a simpler regression target and straighter sampling paths — powers SD3 and FLUX.
- [[Concept - Diffusion Samplers and Schedulers]] — the solvers and noise schedules that turn a trained diffusion model into an image in N steps, and why N drives latency.
- [[Concept - Diffusion Transformers (DiT)]] — replacing the diffusion U-Net with a plain transformer over latent patches — the backbone swap behind SD3, FLUX, and Sora.
- [[Concept - ControlNet and Spatial Conditioning for Diffusion]] — bolting structural control (edges, pose, depth) onto a frozen diffusion model via a trainable copy and zero-init convolutions.
- [[Concept - VQ-VAE and Discrete Visual Tokenization]] — turning images into discrete codebook tokens (VQ-VAE/VQGAN), codebook collapse and its fixes, and the FSQ/LFQ escape.
- [[Breakdown - Stable Diffusion]] — the Stable Diffusion family (SD1.x-SD3/FLUX) as an engineered system: VAE, text encoders, U-Net vs MMDiT, across generations.
- [[Gotchas - Diffusion Training and Sampling]] — arcane failure modes and folklore fixes for training and sampling diffusion models — SNR bugs, scaling constants, EMA, fp16 traps.
- [[Snippet - DDPM Training and Sampling Loop]] — minimal runnable PyTorch DDPM: schedule buffers, the L_simple training step, and a deterministic DDIM sampler on toy 2D data.
- [[Lore - The Stable Diffusion Release and Its Aftermath]] — the war story of open text-to-image 2022-2024: the SD1.4/1.5 release, LAION, the NovelAI leak, the SD3 license revolt, and the lawsuits.

## Audio and speech

- [[Concept - Audio Spectrograms and Mel Features]] — how raw audio becomes a log-mel spectrogram via STFT and mel filterbanks — the default ASR/TTS front-end, and why it's now half-obsolete.
- [[Concept - Neural Audio Codecs and Residual Vector Quantization]] — learned codecs compress audio into discrete RVQ tokens — the vocabulary that audio language models like VALL-E and MusicGen predict.
- [[Breakdown - Whisper]] — OpenAI's encoder-decoder ASR transformer, trained on 680k hours of weakly-supervised web audio, unified via multitask prompt tokens.
- [[Concept - Neural Text-to-Speech and Audio Language Models]] — modern speech synthesis: codec-token language models (VALL-E) and flow-matching TTS replaced the old acoustic-model-plus-vocoder pipeline.

## Video

- [[Concept - Video Generation]] — how video diffusion transformers denoise spacetime latent patches, using factorized attention to keep the quadratic cost tractable.

## Adjacent domains

- [[MOC - Architectures]] — Vision Transformers and Diffusion Transformers are architectural variants of the same transformer backbone covered there; this domain specializes it to non-text modalities.
- [[MOC - Safety & Interpretability]] — VLMs open new attack surfaces (image-based prompt injection, adversarial patches) and interpretability questions this domain doesn't cover on its own.
- [[MOC - Production & Ops]] — serving vision encoders and diffusion models has different latency, batching, and cost profiles than serving text-only LLMs; that domain owns the deployment mechanics.
