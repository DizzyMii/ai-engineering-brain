---
tags: [concept, domain/multimodal, level/core]
aliases: [LDM, latent diffusion models]
summary: "Running diffusion in a compressed VAE latent space instead of pixels — the pattern behind every modern Stable Diffusion-family model."
---
> **One-paragraph hook:** In their original formulation [[Deep Dive - Diffusion Models]] work directly on pixels, and pixel-space diffusion at 512x512 is brutally expensive: each of hundreds of denoising steps is a full forward pass over 262,144 pixel values. Latent diffusion (Rombach et al. 2022) fixes this with a blunt trick that works. Compress the image into a small learned latent with an autoencoder, then run the whole diffusion process there. That one decision moved text-to-image from a DeepMind/OpenAI-cluster problem to something you could train and run on a single consumer GPU, and it's why "Stable Diffusion" and "latent diffusion" are near-synonyms.

## The mechanism

Train an [[Concept - Encoder-Decoder and Decoder-Only Architectures]]-style autoencoder $\mathcal E, \mathcal D$ that compresses an image by a fixed spatial factor. The standard Stable Diffusion setup takes a $512\times512\times3$ image to a $64\times64\times4$ latent: 8x downsampling in each spatial dimension, so a **~48x cut in the number of elements the network processes** ($786{,}432 \to 16{,}384$). The forward and reverse diffusion from [[Deep Dive - Diffusion Models]] then runs entirely inside that latent grid, $z_t = \sqrt{\bar\alpha_t}\, z_0 + \sqrt{1-\bar\alpha_t}\,\epsilon$ with $z_0 = \mathcal E(x_0)$, and the denoiser predicts noise in latent space. A single decoder pass $\mathcal D(z_0)$ at the end reconstructs pixels.

Plain pixel MSE won't do for the autoencoder. It gives blurry reconstructions that lose the high-frequency detail (skin texture, fine edges) that makes an image look real. Rombach et al. train it with a **perceptual loss (LPIPS)** plus an **adversarial patch-GAN discriminator**, so the latent keeps what a human eye (and a trained discriminator) notices instead of whatever minimizes squared pixel error. The bottleneck is regularized one of two ways: a small **KL penalty** toward a standard normal (KL-regularized, which Stable Diffusion uses) or a **vector-quantization** codebook (VQ-regularized, related to [[Concept - VQ-VAE and Discrete Visual Tokenization]]). Both stop the latent from having unbounded variance, which would leave the diffusion process poorly calibrated.

Text conditioning comes in through cross-[[Concept - Attention Mechanism|attention]]. A frozen text encoder ([[Concept - CLIP and Contrastive Vision-Language Training|CLIP]]'s text tower in SD1.x, dual CLIP encoders in SDXL, CLIP+T5 in SD3) produces token embeddings that act as keys and values in cross-attention layers throughout the denoising backbone, with the latent's spatial features as queries. It's the same U-Net cross-attention wiring as in the diffusion deep dive, on a $64\times64$ grid instead of $512\times512$, which is also why it's cheap enough to run interactively.

One detail people miss: the latent isn't used as $\mathcal E(x)$ directly. It's multiplied by a fixed **scaling constant** (0.18215 for SD1.x, 0.13025 for SDXL) chosen so the latent's empirical variance is about 1, which is what the diffusion noise schedule assumes. The constant is part of the checkpoint's expected usage. It isn't learned or stored in the weights.

## In practice

Essentially all mainstream image and video diffusion since 2022 is latent diffusion in this sense. SD1.5/2/SDXL run a U-Net in a 4-channel latent. SD3 and FLUX.1 moved to a **16-channel latent** and a [[Concept - Diffusion Transformers (DiT)|DiT/MMDiT]] backbone, giving up some compute savings for more room to represent fine detail (more channels means less information lost per spatial compression). That was a direct response to the fidelity ceiling described below.

Training happens in two stages. First the autoencoder trains to convergence on a large image corpus and gets frozen; then the diffusion model trains on the frozen latents. This separates perceptual-compression research from generative-modeling research, and it's how a single VAE (e.g., SDXL's) gets reused across model iterations while only the diffusion backbone changes. [[Breakdown - Stable Diffusion]] has the per-version specs, and [[Reference - Vision Encoders and Multimodal Models]] has the latent-channel and scaling-constant table.

## Failure modes

- **The VAE is a hard fidelity ceiling.** However good the diffusion model gets, it can only generate what the frozen autoencoder can represent and reconstruct. Fine text, small faces and hands were notoriously bad in the 4-channel SD1.x/SDXL VAE because 8x spatial compression at only 4 channels loses that kind of high-frequency detail. This is a main reason SD3/FLUX went to a 16-channel latent.
- **Decode artifacts.** A degraded or precision-mismatched decoder gives visible grid/checkerboard patterns or subtle color shifts on decode, whether or not the diffusion sampling was correct. To detect it, decode the same latent twice at different precisions and diff the outputs.
- **Forgetting or mismatching the scaling constant.** The constant isn't learned, so a bug that leaves it out (or uses another model's constant) raises no error. It silently feeds the diffusion model latents with the wrong variance, and the noisy or garbled output looks like a training failure. [[Gotchas - Diffusion Training and Sampling]] lists the numbers per model.

## The non-obvious

*Folklore, weakly sourced:* running the Stable Diffusion VAE decoder in fp16 is a well-known trap in the open-source community. Some SD1.x VAE weights produce NaNs partway through decode in half precision on some GPUs. You get a solid black image, a perfectly normal-looking latent, and no error. The fix that circulated was to decode in fp32 or swap in a numerically patched VAE checkpoint.

The broader lesson is that the autoencoder's numerical behavior can fail independently of the diffusion model. "The model produced garbage" bug reports are frequently a VAE precision issue, not a sampler or prompt issue. Check the decode step in isolation before you debug the diffusion loop.

## Connections
- [[Deep Dive - Diffusion Models]] — the base forward/reverse noising math that latent diffusion runs unchanged, just on compressed latents instead of pixels.
- [[Breakdown - Stable Diffusion]] — the system-level history of this pattern across SD1.x/SDXL/SD3/FLUX, including exact channel counts and scaling constants.
- [[Concept - VQ-VAE and Discrete Visual Tokenization]] — the alternative, discrete-codebook regularization for the same autoencoder bottleneck.
- [[Concept - Classifier-Free Guidance]] — the inference-time technique applied on top of the latent-space denoiser to sharpen text adherence.
- [[Concept - Attention Mechanism]] — the cross-attention mechanism that injects text conditioning into the latent denoising network.
- [[Concept - CLIP and Contrastive Vision-Language Training]] — the standard frozen text encoder whose embeddings condition the cross-attention layers.
- [[Gotchas - Diffusion Training and Sampling]] — catalogs the scaling-constant and precision failure modes described above with exact numbers.
- [[Concept - Diffusion Samplers and Schedulers]] — the numerical solvers that turn the trained latent denoiser into a finished latent in few steps, before the one final VAE decode.
- [[Concept - Encoder-Decoder and Decoder-Only Architectures]] — the general encoder-decoder pattern the autoencoder is an instance of.
- [[Concept - Mixed Precision Training]] — relevant both for training the autoencoder/denoiser and for the fp16 VAE-decode instability noted above.
- [[Concept - Diffusion Transformers (DiT)]] — SD3/FLUX pair the 16-channel latent-diffusion pattern with a DiT/MMDiT backbone in place of the U-Net described here.
- [[Reference - Vision Encoders and Multimodal Models]] — the lookup table for exact latent channel counts and scaling constants (0.18215, 0.13025) across SD1/SDXL/SD3/FLUX referenced throughout this note.

## Sources
- Rombach, Blattmann, Lorenz, Esser, Ommer (2022) — High-Resolution Image Synthesis with Latent Diffusion Models. Introduces the perceptual-autoencoder + latent-diffusion pattern (the paper behind Stable Diffusion).
- Esser, Kulal, et al. (2024) — Scaling Rectified Flow Transformers for High-Resolution Image Synthesis (SD3). Moves latent diffusion to a 16-channel latent and MMDiT backbone.
