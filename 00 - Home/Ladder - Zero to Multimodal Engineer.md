---
tags: [ladder, domain/home, level/surface]
aliases: [Zero to Multimodal Engineer, multimodal engineer roadmap, VLM and diffusion learning path, vision-language and generative media ladder]
summary: "Surface-to-unicorn walk from attention and CNNs through ViT, CLIP, VLMs, and diffusion — how models see, generate images, and hear."
---

# Ladder - Zero to Multimodal Engineer

A guided walk through domain 15 (Multimodal), with the attention and vision prerequisites pulled from domain 03 (Architectures), built around one question: *how does a model built to predict the next token learn to see an image, generate one from a sentence, and hear and produce speech?* Twenty-two steps in story order. First the transformer and the pre-transformer vision lineage it absorbed. Then how images and text get pulled into a shared embedding space, how that space gets wired into an LLM to make a vision-language model, and how a text prompt becomes an image through diffusion. Then the same machinery extended to audio and video, and finally a geometry quirk and an open-source war story that count as this domain's tribal knowledge. Read each note for the one thing named under it. If you can answer the self-test, move on. The track assumes you can already trace a token through a transformer block. [[Deep Dive - The Transformer]] in step 1 is review and a source of exact links, not a first introduction; if it's new territory, budget more time for it than the pace below assumes. By the end you should be able to explain why a VLM answers from language priors instead of the pixels, why a diffusion model runs two forward passes per sampling step, and why no contrastive vision-language embedding space is actually unified. For the full 25-domain map, including the rest of the Engineering Wing this track sits inside, start at [[Home]].

---

## Act I — The lineage (attention and the vision prehistory it absorbed)

**1. [[Deep Dive - The Transformer]]**
The skeleton every later architecture in this ladder reuses unchanged: a stack of pre-norm residual blocks, `x = x + Sublayer(Norm(x))`, where attention and the FFN read from and write to one shared residual stream instead of forming a sequential pipeline. Use the parameter formula $N_{params} \approx 12 \cdot n_{layers} \cdot d_{model}^2$ for budgeting. Causal masking is what turns next-token training into one parallel forward pass instead of an RNN's token-by-token loop. Vision Transformers, VLM connectors and diffusion transformers are all this same block in a new context.
*Self-test:* Why does pre-norm keep the residual path a "clean gradient highway," and what breaks at depth if you use post-norm instead?

**2. [[Concept - Attention Mechanism]]**
Scaled dot-product attention, $A = \text{softmax}(QK^T/\sqrt{d_k})$, and *why* the $1/\sqrt{d_k}$ scaling exists. Without it, unscaled dot products grow with $d_k$ and push softmax into a near-one-hot regime that starves gradient flow to every position but one. Generalize the operation to two input streams and you get cross-attention, which lets a diffusion U-Net read a text prompt (step 15) and Flamingo read an image (step 11). Same formula, different sources for Q versus K/V.
*Self-test:* If you skip the $1/\sqrt{d_k}$ scaling entirely, what failure shows up in the softmax output, and why does it get worse as head dimension grows?

**3. [[Concept - Convolutional Neural Networks]]**
The vision lineage ViT replaced: weight sharing (`k·k·C_in·C_out` parameters instead of `H·W·C_in·C_out`), translation equivariance, and a receptive field that grows with depth. The non-obvious point to carry forward is that ResNet's skip connection `y = F(x) + x` solves the *degradation* problem. Deeper plain networks got measurably worse at training, and generalization wasn't the issue. That "make identity the cheap default" trick is the direct ancestor of the transformer's residual stream from step 1, even though CNNs have spatial structure transformers don't.
*Self-test:* A 56-layer plain CNN has higher training error than a 20-layer version of the same design. Why does that rule out "it's just overfitting," and what does ResNet change to fix it?

---

## Act II — Learning to see (vision transformers and cross-modal contrastive pretraining)

**4. [[Concept - Vision Transformers]]**
Patchify: a 224×224 image splits into 16×16 patches, giving $(224/16)^2=196$ tokens. Each is linearly projected (mechanically a strided convolution) and handed to the unmodified transformer block from step 1. The cost is quadratic. Doubling input resolution roughly quadruples patch count and multiplies attention FLOPs by roughly 16x. ViT's learned (not RoPE) position embeddings also have to be bicubically interpolated to run at an off-training resolution, which degrades output without any warning. ViT needs on the order of 100M+ training images to beat a similarly sized ResNet, because it has none of a CNN's locality prior built in. It pays in data for a global receptive field from layer one.
*Self-test:* Why does doubling a ViT's input resolution cost roughly 16x more attention compute and not 4x, and what does that force real systems to do instead of running one forward pass over a 4K image?

**5. [[Concept - Cross-Modal Representation Alignment]]**
This is the fork the whole ladder hangs on. Contrastive alignment into a shared metric space has no decoder and is built for retrieval (the CLIP recipe). Fusion into a generative LM adds a decoder that can talk about the image (the VLM recipe). Real systems compose both: a CLIP-style tower supplies frozen features and a connector bridges into the LLM. The named failure mode to remember is **modality collapse**. An LLM fed unaligned vision features learns to ignore them and answers from language priors alone. You detect it with a counterfactual image swap.
*Self-test:* A retrieval system and a captioning system both need "cross-modal alignment." Why does only one of them need a decoder, and which paradigm does each map to?

**6. [[Concept - CLIP and Contrastive Vision-Language Training]]**
An image encoder and a text encoder map into a shared space, L2-normalized, trained on the $N \times N$ in-batch similarity matrix with symmetric InfoNCE cross-entropy (image→text and text→image averaged). One number explains CLIP's scaling story: batch size 32,768, chosen because harder in-batch negatives directly drive representation quality. That's the all-gather bottleneck SigLIP (step 7) was built to remove. The failure mode: CLIP behaves more like bag-of-words over captions than a compositional reasoner. It struggles to tell "a red cube on a blue sphere" from "a blue cube on a red sphere," because nothing in noisy alt-text ever forced it to bind attributes to objects.
*Self-test:* CLIP reaches roughly 75% zero-shot top-1 on ImageNet with zero labeled training examples. What mechanism turns "classification" into "retrieval," and why does that same mechanism fail by design at counting and spatial relations?

**7. [[Concept - SigLIP and the Sigmoid Contrastive Loss]]**
The fix: replace CLIP's softmax-over-the-whole-batch loss with an independent sigmoid binary classification per (image, text) pair, so every negative no longer has to be present for one shared normalization. SigLIP matches or beats CLIP quality at 16K batch size against CLIP's 32K. It initializes its bias term around $-10$ to counter the $N$-positives-versus-$N^2{-}N$-negatives class imbalance at batch construction. SigLIP-So400m's practical win is resolution as much as loss efficiency: it commonly runs at 384–448px against CLIP's typical 336px, and that's how it became the default 2024–25 open-VLM vision tower. The catch is that switching the loss doesn't close the modality gap (step 20). The gap comes from using two independent encoders under *any* contrastive loss; the normalization choice has nothing to do with it.
*Self-test:* SigLIP removes the global all-gather that CLIP's softmax loss requires. Mechanically, why does turning the loss into a sum of independent per-pair terms make that possible?

---

## Act III — Vision-language models (wiring the eyes into an LLM)

**8. [[Concept - VLM Architectures]]**
Every open VLM falls into one of three families. Cross-attention (Flamingo): frozen LLM, visual features as K/V. Projector/prefix (LLaVA): image tokens prepended into the LLM's own token stream. Early/native fusion (Fuyu, Chameleon): one transformer trained from scratch over mixed tokens. The cost number: one 336px CLIP ViT-L/14 image costs 576 tokens once it enters the stream in the projector family, and that's the main driver of KV-cache and latency cost. The history is less obvious. The field moved from Flamingo's cross-attention (2022) to LLaVA's simpler projector (2023–24) and *back* to cross-attention for Llama-3.2-Vision. Once an LLM is valuable and safety-tuned, leaving it un-fine-tuned is a governance feature as well as a compute saving.
*Self-test:* Llama-3.2-Vision went back to Flamingo-style cross-attention after the field had settled on LLaVA-style projectors. What changed about the calculus, and what does "the LLM stays frozen" buy you that has nothing to do with training cost?

**9. [[Concept - Vision-Language Connectors]]**
This one module controls the token-count/quality tradeoff. A linear/MLP projector keeps all 576 patch tokens (most detail, most cost). A Q-Former/Perceiver resampler compresses to a fixed 32–64 tokens: cheap, but an information bottleneck that costs OCR and small-object grounding. Pixel-shuffle merging (InternVL, Qwen2-VL) folds a 2×2 patch neighborhood into one token, a 4x reduction that loses less detail than a resampler at the same token count because it merges deterministically instead of learning a lossy compression. Two under-appreciated bugs. Reading the ViT's *final* layer instead of the *penultimate* one loses spatial detail to CLIP's own contrastive objective. And a mismatch between the chat template's placeholder-token count and the connector's actual output corrupts every downstream request without ever throwing an error.
*Self-test:* "Our VLM can't read receipts" almost never gets fixed by more instruction data. Which two components does the fix live in, and why does a fixed-size resampler make the problem worse by design than a linear projector?

**10. [[Breakdown - LLaVA]]**
The recipe that made a competent VLM a reproducible weekend project. Frozen CLIP ViT-L/14 (576 tokens, penultimate layer) feeds a connector into Vicuna-7B/13B, trained in two stages. Stage 1 aligns only the connector on 558K caption pairs with both towers frozen; stage 2 unfreezes the LLM and instruction-tunes on 158K samples. The contribution was the data trick more than the architecture. Text-only GPT-4, given COCO captions and bounding boxes and never pixels, synthesized the multimodal instruction data: a teacher that never saw the modality it was teaching. The number that dates the recipe: SOTA on 11 of 12 benchmarks from only ~1.2M total public data points, on roughly one day of 8×A100 compute for the 7B model.
*Self-test:* GPT-4 never saw a single image while generating LLaVA's instruction-tuning data. What did it condition on instead, and why was that enough?

**11. [[Breakdown - Flamingo]]**
The stability trick that makes grafting new layers onto a frozen pretrained model safe. Gated cross-attention layers go between existing frozen Chinchilla blocks, and each gate's output is multiplied by $\tanh(\alpha)$ with $\alpha$ initialized to zero. At step zero the grafted model is mathematically identical to the original frozen LM, so training starts from a known-good state and avoids destructive early updates. The fixed-cost number: the Perceiver Resampler compresses any input (one image, five images, a video's worth of frames) to 64 tokens, the opposite design point from LLaVA-NeXT's linear-in-resolution tiling. The same zero-init gate shows up later in this domain under other names. ControlNet's zero convolutions and DiT's adaLN-zero conditioning are the identical trick.
*Self-test:* Why does initializing Flamingo's gate parameter to zero matter more than initializing it to a small random value? What training failure does it prevent?

**12. [[Playbook - Training a VLM from a Vision Encoder and an LLM]]**
The operational sequence that turns the LLaVA recipe into a repeatable procedure. Pick components and state the per-image token count *before* training starts. Freeze everything but the connector for stage 1. Run a wire-check that the connector's output token count equals the chat template's placeholder count. Then unfreeze the LLM for stage 2 instruction tuning at LR≈2e-5, with a text-only replay fraction to prevent language regression. The verification discipline is what you're here for: a counterfactual image-swap test and POPE-style adversarial-negative accuracy, not aggregate VQA score, confirm the model is conditioning on pixels and not language priors.
*Self-test:* The playbook says a NaN in stage 1 "almost always" traces to one specific cause other than the learning rate. What is it, and why would checking LR first waste your time?

---

## Act IV — Generating images (diffusion and latent generative models)

**13. [[Deep Dive - Diffusion Models]]**
The whole training loop fits in one line. Sample a real image, sample a timestep and noise, corrupt it to $x_t = \sqrt{\bar\alpha_t}x_0 + \sqrt{1-\bar\alpha_t}\epsilon$, and regress a network to predict the $\epsilon$ that was added: $L_{simple} = \mathbb{E}[\|\epsilon - \epsilon_\theta(x_t,t)\|^2]$. No adversarial discriminator, no mode collapse. The fact everything else rests on is the score-matching equivalence. $\epsilon$-prediction is equivalent to estimating $\nabla_x \log p(x_t)$, so deterministic ODE samplers like DDIM are correct, not a convenient hack: they solve a different equation with identical marginals. From here the ladder traces the evolution: DDPM to DDIM's 20–50-step deterministic sampling, to latent compression (step 14), to classifier-free guidance (step 15). Each swaps one piece and keeps the forward-corrupt/reverse-generate shell.
*Self-test:* Why is a deterministic DDIM sampler not "cheating" a stochastic process into determinism? What mathematical fact makes it equivalent, not merely approximately close?

**14. [[Concept - Latent Diffusion]]**
This trick moved text-to-image from a cluster problem to a consumer-GPU problem. First compress a 512×512×3 image to a 64×64×4 latent with a perceptually trained autoencoder (LPIPS plus adversarial, not pixel-MSE), a ~48x reduction in elements (786,432 → 16,384). Then run every diffusion step in that latent instead of pixel space. The easy-to-miss number: the latent is multiplied by a fixed scaling constant (0.18215 for SD1.x, 0.13025 for SDXL) so its variance matches what the noise schedule assumes. Get the constant wrong and nothing errors; the model just produces garbled noise. The frozen VAE is also a hard fidelity ceiling. No denoiser improvement recovers detail the 4-channel SD1.x/SDXL autoencoder can't represent, and that's why SD3/FLUX moved to 16 channels.
*Self-test:* A latent diffusion model produces uniformly garbled, noisy-looking output, but the training loss curve looked fine. What single silent bug should you check before assuming the sampler or the training run is broken?

**15. [[Concept - Classifier-Free Guidance]]**
What the "CFG scale" slider does. Train one model for both conditional and unconditional generation by dropping the condition to a null token about 10% of the time at random. At sampling time, run the model twice per step and extrapolate: $\hat\epsilon = \epsilon_\theta(x_t,\varnothing) + w(\epsilon_\theta(x_t,c) - \epsilon_\theta(x_t,\varnothing))$. At $w>1$ you're deliberately sampling off the model's learned data manifold, which is more than "listening to the prompt more." The operational cost is double the forward passes per step, and guidance-distilled checkpoints (FLUX-schnell, SDXL-Turbo) exist to avoid it. Guidance scale is a per-checkpoint hyperparameter with no universal value. Copying "CFG 7.5" from an SD1.5 workflow into SDXL or a flow-matching model routinely makes results worse.
*Self-test:* Why does turning the guidance scale up past a certain point produce oversaturated, "deep-fried" images and not "more accurate" ones?

**16. [[Breakdown - Stable Diffusion]]**
Every SD release is the same VAE + text conditioner + denoiser decomposition, with each piece upgraded independently. SD1.x/2/SDXL run a U-Net denoiser on a 4-channel latent, conditioned on CLIP text embeddings via cross-attention. SD3/FLUX swap in an MMDiT backbone and a 16-channel latent, and add T5-XXL to fix legible-text rendering, which CLIP alone handled poorly. SDXL's size/crop conditioning is the reusable pattern. Square-cropped training data bakes in an "everything looks centrally cropped" bias; instead of fighting it, SDXL feeds the original size and crop offset as explicit conditioning, turning a data artifact into a controllable variable. The training-cost figure, with its evidence tier: SD1.4 trained for roughly 150,000 A100-hours (~$600K, Mostaque's own unaudited claim) on a LAION-2B aesthetic subset. That number made "download and fine-tune a real text-to-image model on one GPU" possible for the first time.
*Self-test:* SDXL conditions the model explicitly on crop offset and original image size. What training-data bias is that fixing, and why is "condition on the bias" a better fix than "remove the bias from the data"?

---

## Act V — Audio and video (the same machinery, two more modalities)

**17. [[Concept - Audio Spectrograms and Mel Features]]**
Four steps turn a waveform into something a transformer can eat. Frame into 25ms windows with a 10ms hop (so 100 frames/second), FFT each frame, warp the linear-Hz magnitude spectrum through a mel filterbank matmul ($m = 2595\log_{10}(1+f/700)$) down to 80–128 bins, then log-compress. It's a fixed, non-learned, decades-old feature extractor, and Whisper (step 18) still chose it over a learned front end in 2022, because the mel warp already encodes a perceptual prior a learned frontend would have to rediscover from data. The failure mode that eats the most debugging time: phase is discarded at the FFT step, so reconstruction is inherently lossy. And a silent sample-rate mismatch (44.1kHz audio into a 16kHz-trained model) doesn't error. It just maps every mel bin to the wrong physical frequency.
*Self-test:* Why can't you losslessly reconstruct audio from a log-mel spectrogram no matter how good your model is, and how does a production TTS pipeline work around that?

**18. [[Breakdown - Whisper]]**
The architecture is a stock encoder-decoder transformer, so the contribution is the data: 680,000 hours of noisy, weakly labeled web audio across 96 languages, filtered by heuristics instead of hand-annotated, on the bet that scale plus noise beats small clean data for robustness. Multitasking works through special prefix tokens (`<|transcribe|>`, `<|translate|>`, a language-ID token) that select the task for one shared decoder. It's effectively a chat template for audio, and it puts transcription, translation and language ID into one set of weights. The named failure mode: silence or non-speech input gives the encoder a weak conditioning signal, and the decoder, which is a real language model underneath, falls back on its LM prior and hallucinates fluent, fabricated text instead of outputting nothing. Production systems therefore put voice-activity detection in front of the model.
*Self-test:* Whisper hallucinating fluent text on silent audio isn't really a bug in the traditional sense. What is the decoder doing when that happens, and what's the standard production fix?

**19. [[Concept - Video Generation]]**
Naive frame-by-frame diffusion fails with flicker, morphing and lost identity. The fix: compress video with a causal 3D VAE (~8x8 spatial, ~4x temporal; "causal" means it only looks backward, so a clip can be extended without re-encoding everything already generated), patchify the spacetime latent, and use *factorized* spatial-plus-temporal attention instead of full 3D attention. The FLOPs: at $t{=}32, h{=}w{=}32$ full attention costs $N^2 \approx 1.07 \times 10^9$ pairwise interactions per layer, and factorized attention cuts that to roughly $3.5\times10^7$, about 30x cheaper. So every production video model interleaves spatial and temporal attention blocks instead of joint 3D attention. A debugging habit worth stealing: separate VAE reconstruction error from diffusion sampling error first. If a held-out clip flickers after a plain encode-decode roundtrip with no diffusion involved, retraining the diffusion transformer won't fix it.
*Self-test:* A generated clip's colors and identity drift the longer it runs. Name two different causes, and say which one you'd rule out first by testing the VAE alone.

---

## The unicorn tier — where multimodal still breaks

**20. [[Concept - The Modality Gap in Contrastive Models]]**
This should recalibrate every intuition from Act II. CLIP's image and text embeddings never merge into one space. They sit in two separate cones with a persistent offset, and matched-pair cosine similarity is typically only ~0.2–0.3, far below the ~0.5–0.9 you see within one modality. The mechanism: a randomly initialized network maps *any* input into a narrow cone (the "cone effect"), so the image and text towers land in *different* cones before a single gradient step. InfoNCE only enforces *relative* ordering within a batch. Translating the whole text cone rigidly changes nothing about which pair ranks highest, so there's zero gradient pressure to close the gap. In practice that means a VLM connector has to learn a real bridge between cones, not a resize, and swapping CLIP for SigLIP (step 7) doesn't help. Two independent encoders under any contrastive loss produce the gap; normalization doesn't.
*Self-test:* CLIP can hit state-of-the-art zero-shot retrieval accuracy while its image and text embeddings never spatially overlap. How is that possible, and what does it say about what the contrastive loss optimizes?

**21. [[Gotchas - Vision-Language Models]]**
The ranked failure catalog you ship against. The blind VLM: answers don't change when you swap the image. Object hallucination, measured by POPE's random/popular/adversarial split; a big adversarial-versus-random gap is the fingerprint of prior-driven confabulation. Image-token budget blowup: 4 tiles plus a thumbnail at 576 tokens/tile is ~2,880 tokens for one image. And the placeholder/chat-template mismatch that desyncs positions with no crash and no error, only silent quality collapse. The deepest one is the frozen-encoder ceiling. If the vision encoder never unfreezes, its features, including the high-norm outlier tokens from register-token artifacts, cap perception for the whole system, and no amount of LLM-side SFT pushes fine-grained perception past that.
*Self-test:* A team spends months tuning SFT data to fix a VLM's OCR problem with no improvement. Per this catalog, which two components should they have checked first, and why would more instruction data never have fixed it?

**22. [[Lore - The Stable Diffusion Release and Its Aftermath]]**
The flywheel: open weights (August 2022, ~150,000 A100-hours), a cheap composable customization method (DreamBooth, then LoRA at a few megabytes per style) and a distribution hub (Civitai) built an ecosystem no single company could steer. Once Stability had handed out the weights, it couldn't pull the loop closed again. When SD3's 2024 restrictive license drew backlash, the community and the original CompVis researchers regrouped as Black Forest Labs and shipped FLUX.1. The second lesson outlasts the drama: your training data's provenance is a permanent inherited liability. LAION-5B made Stable Diffusion possible. Then, when Stanford researchers found CSAM in it in December 2023, it made every model trained on it a legal exposure, on top of the still-unresolved Getty and Andersen copyright suits.
*Self-test:* Stability released SD3 under a more restrictive license in 2024 and the ecosystem didn't shrink to comply; it moved to FLUX.1. What does that say about where the value sat: the model weights, or something else?

---

**Where next:** [[MOC - Multimodal]] maps every note in domain 15, including the ones this path skipped: flow matching, diffusion transformers (DiT), VQ-VAE, neural audio codecs, neural TTS, native any-to-any fusion, register tokens, diffusion training/sampling gotchas. [[MOC - Architectures]] covers the rest of domain 03's sequence mixers and attention variants beyond the two prerequisites this ladder pulled in at steps 1 and 2.
