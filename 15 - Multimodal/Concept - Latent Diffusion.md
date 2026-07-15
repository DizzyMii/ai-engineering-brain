---
tags: [concept, domain/multimodal, level/core]
aliases: [LDM, latent diffusion models]
summary: "Running diffusion in a compressed VAE latent space instead of pixels — the pattern behind every modern Stable Diffusion-family model."
---
> **One-paragraph hook:** [[Deep Dive - Diffusion Models]] work directly on pixels in their original formulation, and pixel-space diffusion at 512x512 is brutally expensive — every one of hundreds of denoising steps runs a full network forward pass over 262,144 pixel values. Latent diffusion (Rombach et al. 2022) fixes this with a blunt but effective trick: compress the image into a small learned latent with an autoencoder first, then run the entire diffusion process there instead. This single architectural decision is what turned text-to-image from a DeepMind/OpenAI-cluster problem into something you could train and run on a single consumer GPU, and it's why "Stable Diffusion" and "latent diffusion" are near-synonyms.

## The mechanism

Train an [[Concept - Encoder-Decoder and Decoder-Only Architectures]]-style autoencoder $\mathcal E, \mathcal D$ that compresses an image by a fixed spatial factor — the canonical Stable Diffusion setup takes a $512\times512\times3$ image down to a $64\times64\times4$ latent, an 8x downsample in each spatial dimension and therefore a **~48x reduction in the number of elements the network has to process** ($786{,}432 \to 16{,}384$). The forward and reverse diffusion process described in [[Deep Dive - Diffusion Models]] then runs entirely inside this latent grid: $z_t = \sqrt{\bar\alpha_t}\, z_0 + \sqrt{1-\bar\alpha_t}\,\epsilon$ where $z_0 = \mathcal E(x_0)$, and the trained denoiser predicts noise in latent space; a final decoder pass $\mathcal D(z_0)$ reconstructs pixels only once, at the end.

The autoencoder cannot be trained with plain pixel MSE — that yields blurry reconstructions that throw away exactly the high-frequency detail (skin texture, fine edges) that makes an image look real. Rombach et al. train it with a **perceptual loss (LPIPS)** plus an **adversarial patch-GAN discriminator**, so the latent is optimized to preserve what a human eye (and a trained discriminator) notices, not what minimizes squared pixel error. The bottleneck itself is regularized one of two ways: a small **KL penalty** toward a standard normal (KL-regularized, what Stable Diffusion uses) or a **vector-quantization** codebook (VQ-regularized, related to [[Concept - VQ-VAE and Discrete Visual Tokenization]]); either keeps the latent from having unbounded variance that would make the diffusion process poorly calibrated.

Text conditioning enters through cross-[[Concept - Attention Mechanism|attention]]: a frozen text encoder — [[Concept - CLIP and Contrastive Vision-Language Training|CLIP]]'s text tower in SD1.x, dual CLIP encoders in SDXL, CLIP+T5 in SD3 — produces a sequence of token embeddings that serve as the keys and values in cross-attention layers threaded through the denoising backbone; the latent's spatial features serve as queries. This is the same U-Net cross-attention wiring described in the diffusion deep dive, just operating on a $64\times64$ grid instead of a $512\times512$ one, which is also why it's cheap enough to run interactively.

One easy-to-miss detail: the latent is not used as $\mathcal E(x)$ directly. It's multiplied by a fixed **scaling constant** (0.18215 for SD1.x, 0.13025 for SDXL) chosen so the latent's empirical variance is approximately 1 — matching the assumption the diffusion noise schedule was designed around. This constant is baked into the checkpoint's expected usage, not learned or stored in the weights themselves.

## In practice

Essentially all mainstream image and video diffusion since 2022 is latent diffusion in this sense: SD1.5/2/SDXL run a U-Net in a 4-channel latent; SD3 and FLUX.1 moved to a **16-channel latent** with a [[Concept - Diffusion Transformers (DiT)|DiT/MMDiT]] backbone instead of a U-Net, trading some of the compute savings for more headroom to represent fine detail (more channels = less information lost per spatial compression), a direct response to the fidelity ceiling described below. The two-stage training split — first train the autoencoder to convergence on a large image corpus, freeze it, then train the diffusion model on the frozen latents — decouples perceptual-compression research from generative-modeling research and is why a single VAE (e.g., SDXL's) gets reused across model iterations with only the diffusion backbone changing. See [[Breakdown - Stable Diffusion]] for the exact per-version specs and [[Reference - Vision Encoders and Multimodal Models]] for the latent-channel and scaling-constant table.

## Failure modes

- **The VAE is a hard fidelity ceiling.** No matter how good the diffusion model gets, it can only generate what the frozen autoencoder can represent and reconstruct — fine text, small faces, and hands were notoriously bad in the 4-channel SD1.x/SDXL VAE because 8x spatial compression at only 4 channels loses exactly that kind of high-frequency detail. This is a primary motivation for SD3/FLUX's 16-channel latent.
- **Decode artifacts.** A degraded or precision-mismatched decoder produces visible grid/checkerboard patterns or subtle color shifts on decode, independent of whether the diffusion sampling itself was correct. Detection: run the same latent through decode twice at different precisions and diff the output.
- **Forgetting or mismatching the scaling constant.** Because the constant isn't learned, a bug that omits it (or uses the wrong model's constant) doesn't error — it silently feeds the diffusion model latents of the wrong variance, producing noisy or completely garbled output that looks like a training failure. See [[Gotchas - Diffusion Training and Sampling]] for the exact numbers per model.

## The non-obvious

*Folklore, weakly sourced:* running the Stable Diffusion VAE decoder in fp16 is a well-known trap in the open-source community — certain SD1.x VAE weights produce NaNs partway through decode in half precision on some GPUs, manifesting as solid black output images with a perfectly normal-looking latent and no error thrown. The fix that circulated was either decoding in fp32 or swapping in a numerically-patched VAE checkpoint. It's a good illustration of a broader lesson: the autoencoder's numerical behavior is a separate reliability surface from the diffusion model's, and "the model produced garbage" bug reports are frequently a VAE precision issue, not a sampler or prompt issue — check the decode step in isolation before debugging the diffusion loop.

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
