---
tags: [concept, domain/multimodal, level/advanced]
aliases: [VQ-VAE, VQGAN, discrete visual tokens, vector quantization, FSQ, LFQ, straight-through estimator]
summary: "Turning images into discrete codebook tokens (VQ-VAE/VQGAN), codebook collapse and its fixes, and the FSQ/LFQ escape."
---
> **One-paragraph hook:** A transformer's native input is a sequence of discrete token IDs. Text already comes that way via [[Concept - Byte-Pair Encoding]]; images do not. VQ-VAE and its descendants close that gap by learning a finite codebook of visual "words" and mapping every image patch to the nearest one — turning a $256\times256$ image into, say, 256 integers you can feed straight into an autoregressive LM. This is the machinery behind Parti, MUSE, Image GPT, [[Concept - Native and Any-to-Any Multimodal Models|Chameleon]], and most neural audio codecs. It also carries a notorious tax — *codebook collapse* — and a decade of tribal fixes, which is the real reason this note exists.

## The mechanism

Start with a standard convolutional autoencoder $\mathcal E, \mathcal D$. The encoder maps an image to a grid of continuous feature vectors $z_e(x) \in \mathbb R^{h \times w \times d}$. VQ-VAE (van den Oord et al. 2017) inserts a **quantizer** between encoder and decoder: a learned codebook $\{e_1, \dots, e_K\} \subset \mathbb R^d$ of $K$ vectors. Each spatial feature is snapped to its nearest codebook entry,

$$ k = \arg\min_j \lVert z_e(x) - e_j \rVert_2, \qquad z_q(x) = e_k, $$

and the *token* for that position is simply the index $k \in \{1,\dots,K\}$. The decoder reconstructs from the quantized grid $z_q$. The whole latent is now a grid of integers — a discrete image.

```
   image x ──► Encoder ──► z_e  ──► [ nearest-neighbor  ] ──► z_q ──► Decoder ──► x̂
  (H×W×3)      (conv)    (h×w×d)   [ lookup in codebook ]  (h×w×d)   (conv)   (H×W×3)
                                    ┌─ e_1  e_2 ... e_K ─┐
                                    │   codebook (K×d)   │
                                    └────────────────────┘
   tokens = argmin indices (h×w integers in [1..K])
   gradient path:  ∂L/∂x̂ ──(straight-through: copy ∂L/∂z_q → ∂L/∂z_e)──► Encoder
```

The problem: $\arg\min$ has zero gradient almost everywhere, so backprop can't reach the encoder through the quantizer. VQ-VAE uses the **straight-through estimator (STE)**: on the forward pass use $z_q$, but on the backward pass copy the decoder's gradient straight past the quantizer as if $z_q = z_e$ (i.e. treat the quantization as an identity). In PyTorch this is the one-liner `z_q = z_e + (z_q - z_e).detach()`. See [[Concept - Backpropagation]] for why this biased-but-workable gradient is the crux of the whole design.

Because STE never actually trains the codebook (no gradient flows *to* $e_k$ from reconstruction), the loss adds two more terms:

$$ \mathcal L = \underbrace{\lVert x - \mathcal D(z_q) \rVert^2}_{\text{reconstruction}} + \underbrace{\lVert \operatorname{sg}[z_e] - e \rVert^2}_{\text{codebook loss}} + \beta \underbrace{\lVert z_e - \operatorname{sg}[e] \rVert^2}_{\text{commitment loss}}. $$

$\operatorname{sg}[\cdot]$ is stop-gradient. The codebook loss pulls the *chosen code* toward the encoder output (this is what actually moves $e_k$); the commitment loss pulls the *encoder output* toward its chosen code so the encoder can't grow its outputs without bound to dodge quantization. $\beta \approx 0.25$ is the classic default. The codebook itself is really a learned lookup table — mechanically identical to the token-embedding matrix in [[Concept - Embeddings as Learned Representations]], just consulted by nearest-neighbor instead of by index.

## In practice

Plain VQ-VAE reconstructions are blurry, because pixel-MSE reconstruction throws away high-frequency detail (the same reason discussed in [[Concept - Latent Diffusion]]). **VQGAN** (Esser et al. 2021, "Taming Transformers") is the fix that made discrete tokens usable at high resolution: replace pixel-MSE with an **LPIPS perceptual loss** plus a **patch-GAN discriminator**, so a compact codebook can produce sharp $256$–$1024\text{px}$ images. Its tokens then feed an autoregressive [[Deep Dive - The Transformer|transformer]] that models images as sequences — the template Parti, MUSE, and Chameleon all follow.

Numbers to anchor on:
- **Downsampling factor** $f=16$ is standard: a $256\times256$ image becomes a $16\times16=256$-token grid; $f=8$ gives $32\times32=1024$ tokens. Halving $f$ quadruples token count and quadratic attention cost downstream.
- **Codebook size** $K$: original VQ-VAE used 512; VQGAN commonly 1024–16384; the trade is that a bigger codebook lowers reconstruction error but is harder to fully utilize and enlarges the transformer's output vocabulary.
- **Code dim** $d$: improved-VQGAN found *lowering* $d$ (e.g. to 4–32) and **L2-normalizing** the codes dramatically improves utilization — you match on direction, not magnitude.

The modern escape hatch is to delete the codebook entirely. **FSQ** (Finite Scalar Quantization, Mentzer et al. 2023) projects the encoder output down to a handful of dimensions and rounds each to a small fixed set of levels — e.g. levels $[8,8,8,5,5,5]$ gives an implicit vocabulary of $8^3\cdot 5^3 = 64{,}000$ with **no codebook, no commitment loss, and near-100% utilization** because every grid cell is reachable by construction. **LFQ** (lookup-free quantization, MagViT-2, Yu et al. 2023) takes each latent dimension to a binary $\pm 1$, yielding an enormous vocabulary (up to $2^{18}=262{,}144$) that empirically improves generation quality precisely because the vocabulary is huge and fully used. The residual-VQ variant used by audio codecs stacks quantizers to claw back fidelity — see [[Concept - Neural Audio Codecs and Residual Vector Quantization]].

Why go discrete at all, given [[Deep Dive - Diffusion Models|diffusion]] on continuous latents produces higher-fidelity images? Because discreteness buys you a *single vocabulary*: images, text, and audio become tokens in one sequence that one decoder-only transformer models with one cross-entropy loss, which is exactly what enables autoregressive and any-to-any generation. The images-as-tokens tokens can even reuse a [[Concept - Vision Transformers|ViT]]-style encoder. The cost is fidelity — quantization is lossy in a way continuous latents are not — and that fidelity-vs-unification tension is the central design fork in multimodal generation.

## Failure modes

- **Codebook collapse.** The signature failure: after a while only a small fraction of the $K$ codes are ever selected ("dead codes"), so effective vocabulary — and reconstruction quality — is far below what $K$ suggests. Detection: log per-step codebook **perplexity** / active-code count; a codebook of 8192 using 300 codes is collapsing. Fixes below.
- **Blurry or artifacted reconstruction at high compression.** Push $f$ too high (too few tokens) and the decoder can't restore detail; small text and faces smear. This is a hard ceiling on any downstream generator, identical in spirit to the VAE ceiling in latent diffusion.
- **Discriminator instability.** The patch-GAN in VQGAN can diverge or dominate; practitioners delay the discriminator (start it after N steps) and cap its loss weight.
- **Vocabulary-vs-utilization trap.** Naively growing $K$ to reduce reconstruction error usually *worsens* utilization (more codes to keep alive) — you pay in a bigger vocabulary for codes the model never learns to use.

## The non-obvious

Codebook collapse is the piece of tribal knowledge that separates a working tokenizer from a broken one, and the accumulated fixes are almost folklore: **EMA codebook updates** (update each code as a running mean of the encoder outputs assigned to it, from VQ-VAE-2, Razavi et al. 2019, instead of learning codes by gradient), **dead-code reinitialization** (every K steps, reset codes with near-zero usage to a random encoder output from the current batch), **low-dimensional L2-normalized codes** (improved VQGAN), and careful **commitment-weight** tuning. The deeper punchline arrived with FSQ: much of a decade of anti-collapse engineering was *working around the codebook itself*. Once you replace learned vector quantization with fixed scalar quantization, collapse simply cannot happen — there is nothing to collapse — and you match or beat VQGAN with a simpler objective. The lesson that generalizes: when a component needs an ever-growing pile of stabilization tricks, the component, not the tricks, is often the bug. This is the same realization that later reshaped audio codecs and native multimodal tokenizers.

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
