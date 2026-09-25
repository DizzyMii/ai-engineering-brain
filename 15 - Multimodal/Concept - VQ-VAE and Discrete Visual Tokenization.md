---
tags: [concept, domain/multimodal, level/advanced]
aliases: [VQ-VAE, VQGAN, discrete visual tokens, vector quantization, FSQ, LFQ, straight-through estimator]
summary: "Turning images into discrete codebook tokens (VQ-VAE/VQGAN), codebook collapse and its fixes, and the FSQ/LFQ escape."
---
> **One-paragraph hook:** A transformer's native input is a sequence of discrete token IDs. Text already arrives that way through [[Concept - Byte-Pair Encoding]]; images don't. VQ-VAE and its descendants learn a finite codebook of visual "words" and map every image patch to the nearest one, so a $256\times256$ image becomes, say, 256 integers you can feed straight into an autoregressive LM. Parti, MUSE, Image GPT, [[Concept - Native and Any-to-Any Multimodal Models|Chameleon]] and most neural audio codecs run on this machinery. It also carries a notorious tax, *codebook collapse*, and a decade of tribal fixes for it. Those fixes are why this note exists.

## The mechanism

Start with a standard convolutional autoencoder $\mathcal E, \mathcal D$. The encoder maps an image to a grid of continuous feature vectors $z_e(x) \in \mathbb R^{h \times w \times d}$. VQ-VAE (van den Oord et al. 2017) puts a **quantizer** between encoder and decoder: a learned codebook $\{e_1, \dots, e_K\} \subset \mathbb R^d$ of $K$ vectors. Each spatial feature snaps to its nearest codebook entry,

$$ k = \arg\min_j \lVert z_e(x) - e_j \rVert_2, \qquad z_q(x) = e_k, $$

and the *token* at that position is the index $k \in \{1,\dots,K\}$. The decoder reconstructs from the quantized grid $z_q$. The latent is now a grid of integers, a discrete image.

```
   image x ──► Encoder ──► z_e  ──► [ nearest-neighbor  ] ──► z_q ──► Decoder ──► x̂
  (H×W×3)      (conv)    (h×w×d)   [ lookup in codebook ]  (h×w×d)   (conv)   (H×W×3)
                                    ┌─ e_1  e_2 ... e_K ─┐
                                    │   codebook (K×d)   │
                                    └────────────────────┘
   tokens = argmin indices (h×w integers in [1..K])
   gradient path:  ∂L/∂x̂ ──(straight-through: copy ∂L/∂z_q → ∂L/∂z_e)──► Encoder
```

The catch: $\arg\min$ has zero gradient almost everywhere, so backprop can't get through the quantizer. VQ-VAE uses the **straight-through estimator (STE)**. The forward pass uses $z_q$; the backward pass copies the decoder's gradient straight past the quantizer as if $z_q = z_e$ (the quantizer is treated as an identity). In PyTorch that's the one-liner `z_q = z_e + (z_q - z_e).detach()`. [[Concept - Backpropagation]] explains why this biased-but-workable gradient is the crux of the design.

STE never actually trains the codebook (no reconstruction gradient flows *to* $e_k$), so the loss gets two more terms:

$$ \mathcal L = \underbrace{\lVert x - \mathcal D(z_q) \rVert^2}_{\text{reconstruction}} + \underbrace{\lVert \operatorname{sg}[z_e] - e \rVert^2}_{\text{codebook loss}} + \beta \underbrace{\lVert z_e - \operatorname{sg}[e] \rVert^2}_{\text{commitment loss}}. $$

$\operatorname{sg}[\cdot]$ is stop-gradient. The codebook loss pulls the *chosen code* toward the encoder output (this is what moves $e_k$). The commitment loss pulls the *encoder output* toward its chosen code so the encoder can't grow its outputs without bound to dodge quantization. $\beta \approx 0.25$ is the classic default. Mechanically the codebook is a learned lookup table, like the token-embedding matrix in [[Concept - Embeddings as Learned Representations]] but consulted by nearest neighbor instead of by index.

## In practice

Plain VQ-VAE reconstructions are blurry because pixel-MSE throws away high-frequency detail (the same problem [[Concept - Latent Diffusion]] discusses). **VQGAN** (Esser et al. 2021, "Taming Transformers") made discrete tokens usable at high resolution by swapping pixel-MSE for an **LPIPS perceptual loss** plus a **patch-GAN discriminator**, so a compact codebook can produce sharp $256$–$1024\text{px}$ images. Its tokens then feed an autoregressive [[Deep Dive - The Transformer|transformer]] that models images as sequences, the template Parti, MUSE and Chameleon all follow.

Numbers to anchor on:
- **Downsampling factor** $f=16$ is standard: a $256\times256$ image becomes a $16\times16=256$-token grid, while $f=8$ gives $32\times32=1024$ tokens. Halving $f$ quadruples the token count and the downstream quadratic attention cost.
- **Codebook size** $K$: the original VQ-VAE used 512, VQGAN commonly 1024–16384. A bigger codebook lowers reconstruction error but is harder to use fully and enlarges the transformer's output vocabulary.
- **Code dim** $d$: improved-VQGAN found that *lowering* $d$ (e.g. to 4–32) and **L2-normalizing** the codes improves utilization dramatically, because matching happens on direction instead of magnitude.

The modern escape hatch deletes the codebook. **FSQ** (Finite Scalar Quantization, Mentzer et al. 2023) projects the encoder output to a handful of dimensions and rounds each one to a small fixed set of levels. Levels $[8,8,8,5,5,5]$, for example, give an implicit vocabulary of $8^3\cdot 5^3 = 64{,}000$ with **no codebook, no commitment loss and near-100% utilization**, since every grid cell is reachable by construction. **LFQ** (lookup-free quantization, MagViT-2, Yu et al. 2023) maps each latent dimension to a binary $\pm 1$. The vocabulary gets enormous (up to $2^{18}=262{,}144$), and empirically generation quality improves because that huge vocabulary is fully used. Audio codecs use a residual-VQ variant that stacks quantizers to win back fidelity; see [[Concept - Neural Audio Codecs and Residual Vector Quantization]].

Why go discrete at all, when [[Deep Dive - Diffusion Models|diffusion]] on continuous latents gives higher-fidelity images? Discreteness buys a *single vocabulary*. Images, text and audio become tokens in one sequence that one decoder-only transformer models with one cross-entropy loss, and that's what makes autoregressive and any-to-any generation possible. The image tokens can even come from a [[Concept - Vision Transformers|ViT]]-style encoder. You pay in fidelity, since quantization is lossy where continuous latents aren't, and that fidelity-vs-unification tension is the central design fork in multimodal generation.

## Failure modes

- **Codebook collapse.** The signature failure. After a while only a small fraction of the $K$ codes ever get selected ("dead codes"), so the effective vocabulary, and with it reconstruction quality, falls far below what $K$ suggests. Detection: log per-step codebook **perplexity** / active-code count. A codebook of 8192 using 300 codes is collapsing. Fixes below.
- **Blurry or artifacted reconstruction at high compression.** Push $f$ too high (too few tokens) and the decoder can't restore detail; small text and faces smear. It's a hard ceiling on any downstream generator, the same idea as the VAE ceiling in latent diffusion.
- **Discriminator instability.** VQGAN's patch-GAN can diverge or take over. Practitioners delay the discriminator (turn it on after N steps) and cap its loss weight.
- **Vocabulary-vs-utilization trap.** Growing $K$ naively to cut reconstruction error usually *worsens* utilization (more codes to keep alive). You pay for a bigger vocabulary full of codes the model never learns to use.

## The non-obvious

Codebook collapse is the tribal knowledge that separates a working tokenizer from a broken one, and the fixes that piled up are close to folklore. **EMA codebook updates**: update each code as a running mean of the encoder outputs assigned to it, instead of learning codes by gradient (from VQ-VAE-2, Razavi et al. 2019). **Dead-code reinitialization**: every K steps, reset codes with near-zero usage to a random encoder output from the current batch. **Low-dimensional L2-normalized codes** (improved VQGAN). And careful **commitment-weight** tuning.

FSQ delivered the deeper punchline: much of a decade of anti-collapse engineering was *working around the codebook itself*. Replace learned vector quantization with fixed scalar quantization and collapse can't happen, because there's nothing to collapse, and you match or beat VQGAN with a simpler objective. The general lesson: when a component needs an ever-growing pile of stabilization tricks, the bug is often the component. Audio codecs and native multimodal tokenizers were later reshaped by the same realization.

## Connections
- [[Concept - Latent Diffusion]] — the continuous (KL-regularized) sibling of the VQ-regularized autoencoder bottleneck; the fidelity-vs-unification fork starts here.
- [[Concept - Native and Any-to-Any Multimodal Models]] — the payoff: discrete image tokens live in one transformer vocabulary alongside text, enabling autoregressive image output (Chameleon).
- [[Concept - Neural Audio Codecs and Residual Vector Quantization]] — RVQ generalizes VQ-VAE to audio by stacking quantizers on residuals; inherits the same collapse pathology and DAC's L2-normalized-code fix.
- [[Concept - Backpropagation]] — the straight-through estimator is the biased gradient that makes training through a non-differentiable $\arg\min$ possible at all.
- [[Concept - Byte-Pair Encoding]] — the text analog: both turn a raw signal into a fixed discrete vocabulary a transformer can model; images just have to *learn* their vocabulary.
- [[Concept - Vision Transformers]] — ViT-VQGAN uses a transformer encoder to produce the features that get quantized; the token grid mirrors ViT's patch grid.
- [[Deep Dive - Diffusion Models]] — the continuous-latent alternative that wins on fidelity, defining the tradeoff discrete tokenization is on the other side of.
- [[Concept - Embeddings as Learned Representations]] — a codebook is a learned embedding table consulted by nearest-neighbor rather than by index.
- [[Deep Dive - The Transformer]] — the autoregressive model that consumes VQGAN tokens (Taming Transformers, Parti) and does the actual generation.

## Sources
- van den Oord, Vinyals, Kavukcuoglu (2017) — Neural Discrete Representation Learning. Introduces VQ-VAE, the straight-through estimator, and the commitment loss.
- Esser, Rombach, Ommer (2021) — Taming Transformers for High-Resolution Image Synthesis (VQGAN). Adds perceptual + adversarial losses so a compact codebook feeds an autoregressive transformer.
- Razavi, van den Oord, Vinyals (2019) — Generating Diverse High-Fidelity Images with VQ-VAE-2. Hierarchical codes and EMA codebook updates.
- Mentzer, Minnen, Agustsson, Tschannen (2023) — Finite Scalar Quantization: VQ-VAE Made Simple. Replaces the codebook with fixed scalar levels, eliminating collapse.
- Yu et al. (2023) — Language Model Beats Diffusion: Tokenizer is Key to Visual Generation (MagViT-2 / LFQ). Lookup-free binary quantization with a very large, fully-used vocabulary.
