---
tags: [moc, domain/multimodal, level/surface]
aliases: []
summary: "Map of Multimodal: vision-language alignment, VLM architectures, diffusion/flow image generation, and audio/speech models."
---

# MOC - Multimodal

This domain owns everything that takes a model past pure text: aligning images, audio and video with language in a shared representation space, building vision-language models that can see and reason, and generating pixels and waveforms as well as tokens. The frontier has moved from text-only chat to models that read screenshots, watch video, generate images and speech, and act as agents in visual environments. Each of those capabilities rests on specific mechanisms you can learn (contrastive alignment, cross-attention grafting, denoising diffusion, discrete audio codecs); none of them falls out of scale for free.

The notes run from the surface idea of a shared embedding space, through the core mechanics of ViTs, CLIP-style pretraining and VLM connectors, into advanced material (any-resolution encoding, latent diffusion, neural audio codecs), and out to frontier work on native any-to-any models and video diffusion. The unicorn tier covers modality-gap geometry and the Stable Diffusion release wars. Multimodal systems inherit every failure mode of their text-only cousins and add their own: vision towers blind to certain patterns, token budgets that blow up with resolution, audio codecs that leak speaker identity. So this domain treats perception and generation as engineering problems with their own numbers.

## Start here

- **Surface** → [[Concept - Cross-Modal Representation Alignment]]: the idea under everything else here, projecting images, audio and text into a shared or fused space so attention and comparison work across modalities.
- **Core** → [[Concept - CLIP and Contrastive Vision-Language Training]]: the dual-encoder contrastive recipe behind the zero-shot image-text embedding space most VLM vision towers descend from.
- **Advanced** → [[Deep Dive - Diffusion Models]]: the DDPM math, score matching, parameterizations and sampling machinery under every modern image and video generator.
- **Frontier** → [[Concept - Native and Any-to-Any Multimodal Models]]: the move from bolted-on encoders (projectors, cross-attention) to one transformer that natively processes and generates several modalities.
- **Unicorn** → [[Lore - The Stable Diffusion Release and Its Aftermath]]: the 2022-2024 war story of open text-to-image, from the SD1.4/1.5 release, LAION and the NovelAI leak to the SD3 license revolt and the lawsuits.

## Cross-modal foundations

- [[Concept - Cross-Modal Representation Alignment]]: how images, audio and text get projected into a shared or fused representation so attention works across modalities.
- [[Concept - Vision Transformers]]: an image as a sequence of patch tokens, run through a standard transformer in place of a CNN.
- [[Concept - CLIP and Contrastive Vision-Language Training]]: dual-encoder contrastive pretraining on image-text pairs, producing a shared embedding space usable zero-shot.
- [[Concept - SigLIP and the Sigmoid Contrastive Loss]]: the per-pair sigmoid loss that frees image-text pretraining from global batch size and became the default VLM vision tower.
- [[Concept - The Modality Gap in Contrastive Models]]: why CLIP image and text embeddings sit in two separate cones despite being trained to match, and what that breaks.
- [[Concept - Register Tokens and ViT Attention Artifacts]]: ViTs stash high-norm global features in junk background patches and wreck attention maps; register tokens give them a scratchpad.

## Vision-language models

- [[Concept - VLM Architectures]]: the three ways to get an image into an LLM (cross-attention, projector/prefix, native fusion) and the design axes that separate them.
- [[Concept - Vision-Language Connectors]]: the module that turns vision-encoder features into LLM tokens (MLP vs. resampler vs. pixel-shuffle) and the token-count/detail tradeoff it controls.
- [[Concept - Any-Resolution Vision Encoding]]: feeding arbitrary-size images to a fixed-grid ViT with AnyRes tiling, position interpolation, patch-packing and native dynamic resolution.
- [[Breakdown - LLaVA]]: the reproducible open VLM recipe. Frozen CLIP + a projector + Vicuna, trained in two stages on GPT-4-distilled instruction data.
- [[Breakdown - Flamingo]]: DeepMind's cross-attention VLM. Frozen NFNet and frozen Chinchilla joined by zero-init gated cross-attention for few-shot multimodality.
- [[Concept - Native and Any-to-Any Multimodal Models]]: one transformer that processes and generates several modalities with no bolted-on encoder, the step past projector/cross-attention VLMs.
- [[Gotchas - Vision-Language Models]]: recurring VLM failures (blind models, token-budget blowup, OCR failure, hallucination) with symptoms, causes, fixes and detection.
- [[Decision - Choosing a Vision Encoder for a VLM]]: picking a vision tower. SigLIP-So400m is the 2025 default, DINOv2 fusion helps grounding, and resolution vs. token budget is the core tradeoff.
- [[Playbook - Training a VLM from a Vision Encoder and an LLM]]: building a projector-style VLM from a pretrained vision encoder and LLM, with two-stage training, wire-checks and verification probes.
- [[Reference - Vision Encoders and Multimodal Models]]: lookup tables for vision encoders, VLMs, image/video generators and audio models: params, resolution, token counts, formulas.

## Diffusion and image generation

- [[Deep Dive - Diffusion Models]]: how diffusion models learn to reverse a noising process. DDPM math, score matching, parameterizations, schedules, sampling.
- [[Concept - Latent Diffusion]]: diffusion in a compressed VAE latent space instead of pixels, the pattern behind every modern Stable Diffusion-family model.
- [[Concept - Classifier-Free Guidance]]: the inference-time trick that trades diversity for prompt adherence by extrapolating away from the unconditional prediction.
- [[Concept - Flow Matching]]: the continuous-time ODE framework that generalizes diffusion with a simpler regression target and straighter sampling paths. SD3 and FLUX use it.
- [[Concept - Diffusion Samplers and Schedulers]]: the solvers and noise schedules that turn a trained diffusion model into an image in N steps, and why N drives latency.
- [[Concept - Diffusion Transformers (DiT)]]: a plain transformer over latent patches in place of the diffusion U-Net, the backbone swap behind SD3, FLUX and Sora.
- [[Concept - ControlNet and Spatial Conditioning for Diffusion]]: structural control (edges, pose, depth) bolted onto a frozen diffusion model through a trainable copy and zero-init convolutions.
- [[Concept - VQ-VAE and Discrete Visual Tokenization]]: images as discrete codebook tokens (VQ-VAE/VQGAN), codebook collapse and its fixes, and the FSQ/LFQ escape.
- [[Breakdown - Stable Diffusion]]: the Stable Diffusion family (SD1.x-SD3/FLUX) as an engineered system. VAE, text encoders, U-Net vs. MMDiT, across generations.
- [[Gotchas - Diffusion Training and Sampling]]: arcane failure modes and folklore fixes for diffusion training and sampling, including SNR bugs, scaling constants, EMA and fp16 traps.
- [[Snippet - DDPM Training and Sampling Loop]]: minimal runnable PyTorch DDPM with schedule buffers, the L_simple training step and a deterministic DDIM sampler on toy 2D data.
- [[Lore - The Stable Diffusion Release and Its Aftermath]]: open text-to-image 2022-2024, covering the SD1.4/1.5 release, LAION, the NovelAI leak, the SD3 license revolt and the lawsuits.

## Audio and speech

- [[Concept - Audio Spectrograms and Mel Features]]: how raw audio becomes a log-mel spectrogram via STFT and mel filterbanks, the default ASR/TTS front end, and why it's now half-obsolete.
- [[Concept - Neural Audio Codecs and Residual Vector Quantization]]: learned codecs compress audio into discrete RVQ tokens, the vocabulary audio language models like VALL-E and MusicGen predict.
- [[Breakdown - Whisper]]: OpenAI's encoder-decoder ASR transformer, trained on 680k hours of weakly supervised web audio and unified through multitask prompt tokens.
- [[Concept - Neural Text-to-Speech and Audio Language Models]]: modern speech synthesis, where codec-token language models (VALL-E) and flow-matching TTS replaced the acoustic-model-plus-vocoder pipeline.

## Video

- [[Concept - Video Generation]]: how video diffusion transformers denoise spacetime latent patches, with factorized attention keeping the quadratic cost affordable.

## Adjacent domains

- [[MOC - Architectures]]: Vision Transformers and Diffusion Transformers are variants of the transformer backbone covered there; this domain specializes it to non-text modalities.
- [[MOC - Safety & Interpretability]]: VLMs open new attack surfaces (image-based prompt injection, adversarial patches) and interpretability questions this domain doesn't cover itself.
- [[MOC - Production & Ops]]: serving vision encoders and diffusion models has different latency, batching and cost profiles from text-only LLMs. That domain owns the deployment mechanics.
