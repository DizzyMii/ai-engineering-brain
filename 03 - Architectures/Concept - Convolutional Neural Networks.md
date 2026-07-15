---
tags: [concept, domain/architectures, level/surface]
aliases: [CNN, ConvNet, convolutional network]
summary: "The convolution-based architecture family: weight sharing, receptive fields, and the ResNet skip connection the transformer residual stream inherits."
---
> **One-paragraph hook:** Before transformers, convolutional networks were the default architecture for anything spatial — images, and for a while audio and even early text models. A CNN builds representations by sliding a small, shared kernel across the input, exploiting the fact that a useful visual pattern (an edge, a texture) means the same thing wherever it appears. Two ideas from this lineage matter well beyond vision: the receptive-field-grows-with-depth math that every "local attention" pattern reuses, and the ResNet skip connection, which is the direct architectural ancestor of [[Concept - The Residual Stream]] that every modern LLM is built on.

## The mechanism

A convolution computes local dot products between a small learned kernel and a sliding window over the input: for a 1D signal, `y[i] = Σ_k x[i+k] · w[k]`; in 2D, a `k×k` kernel slides over height and width, and in a real network there are `C_in → C_out` channel maps, so a single conv layer applies `C_out` different `k×k×C_in` filters. The critical property is **weight sharing**: the same kernel weights are applied at every spatial location, which gives two things at once — **far fewer parameters** than a dense layer over the same input (`k·k·C_in·C_out` versus `H·W·C_in·C_out` for a fully-connected layer), and **translation equivariance**: shift the input and the output feature map shifts identically, because the same filter fires wherever the pattern it detects occurs.

**Receptive field** — how much of the input a given output unit can "see" — grows with depth, stride, and dilation. Stacking two `3×3` convolutions gives the same receptive field as one `5×5` convolution (`3+3-1=5`) but with fewer parameters (`2·9=18` vs `25`) and an extra nonlinearity in between, the core insight behind VGG's design (Simonyan & Zisserman 2014): go deeper with small kernels rather than wide with large ones. Pooling (max or average) downsamples spatially, discarding exact position while keeping presence information and cheaply growing the receptive field further. Dilated (atrous) convolutions space out the kernel taps, expanding receptive field without adding parameters or downsampling — used heavily in dense-prediction tasks like segmentation. This whole depth-grows-receptive-field mechanism is the same math [[Concept - Sparse and Sliding-Window Attention]] borrows when it stacks local-attention layers to reach beyond a single window.

Depth-wise, a feature hierarchy emerges empirically: early layers detect edges and simple gradients, middle layers combine those into textures and parts, and late layers respond to whole objects — a consequence of the compositional structure convolution + nonlinearity + pooling naturally builds, not something explicitly supervised.

```text
Input             Kernel (3x3)         Output feature map
[H x W x C_in] -- slides & dot-products --> [H' x W' x C_out]
   each output pixel = weighted sum of a local k×k×C_in patch
   same kernel weights reused at every spatial position
```

## In practice

The canonical lineage: **LeNet-5** (LeCun et al. 1998) established convolution + pooling for digit recognition. **AlexNet** (Krizhevsky et al. 2012) — 8 layers, ReLU activations, trained on two GPUs — cut ImageNet top-5 error by roughly 10 points versus the prior best and is generally credited as the moment deep learning became the dominant paradigm in vision. **VGG** (Simonyan & Zisserman 2014) pushed depth to 16–19 layers using uniform stacks of `3×3` convolutions. **ResNet** (He et al. 2015) added skip connections and reached 152 layers, winning ILSVRC 2015. **EfficientNet** (Tan & Le 2019) introduced compound scaling — jointly scaling depth, width, and input resolution by a fixed ratio rather than tuning each independently.

Efficiency tricks that persist in modern architectures: `1×1` convolutions for cheap channel mixing and dimensionality reduction (used throughout Inception and as the "bottleneck" in ResNet blocks); depthwise-separable convolutions (MobileNet, Howard et al. 2017) factor a standard `k×k` convolution into a per-channel spatial convolution plus a `1×1` pointwise mix, cutting compute by roughly `1/C_out + 1/k²` relative to a standard conv — an 8-9x reduction for typical `3×3` kernels at reasonable channel counts, which is why MobileNet-style blocks are the default for on-device vision.

Where CNNs still win as of 2026: small-data regimes, where the built-in translation-equivariance prior gives better generalization than a data-hungry [[Concept - Vision Transformers]] trained from scratch; and edge/latency-constrained deployment (mobile, embedded, real-time video), where a well-optimized ConvNet's lower FLOP count and mature hardware support beat a ViT of comparable quality. CNN backbones (via [[Deep Dive - Diffusion Models]] U-Nets) also remain the default spatial substrate in much of image generation, even after attention-heavy architectures took over language.

## Failure modes

- **The degradation problem.** Before ResNet, simply stacking more plain convolutional layers made optimization *harder*, not just more prone to overfitting: a 56-layer plain network had both higher training *and* test error than a 20-layer version of the same design. This is a genuine optimization pathology, not overfitting — symptom: adding depth increases training loss, which overfitting alone cannot explain.
- **Vanishing gradients through deep, non-skip stacks.** Backpropagating through many nonlinear conv layers without a residual path attenuates gradients toward the input; detect via near-zero gradient norms in early layers relative to late layers during training diagnostics.
- **Checkerboard artifacts.** Strided transposed convolutions used for upsampling in generative and segmentation models can produce visible grid/checkerboard patterns in output, a direct consequence of uneven kernel overlap; detectable visually or by inspecting the spatial autocorrelation of output activations.
- **Overfitting on small datasets without regularization.** The parameter savings from weight sharing help, but a sufficiently deep CNN without batch normalization, dropout, or augmentation still memorizes small training sets — symptom: large train/validation gap, mitigated by standard vision-specific augmentation.

## The non-obvious

ResNet's skip connection is usually explained as "fixing vanishing gradients," but He et al. (2015) were explicit that the deeper problem is the **degradation problem**: even with batch normalization already taming gradient magnitudes, plain deep networks got measurably *worse* at optimization as depth increased, which means the network was struggling to learn something as simple as an identity mapping through a stack of nonlinear layers — even though an identity solution trivially exists and would never hurt accuracy. The residual reformulation `y = F(x) + x` sidesteps this by making identity the *default*: a layer only needs to learn `F(x) ≈ 0` to be a no-op, which is a far easier optimization target than learning `F(x) = x` through a nonlinear composition. That exact insight — make the trivial solution cheap to reach, then let gradient descent add useful deviations on top — is precisely what [[Concept - The Residual Stream]] inherits in every modern transformer block, `x = x + f(norm(x))`, despite transformers having no spatial structure whatsoever. The skip connection didn't just help CNNs go deep; it's the reason any of today's 100+ layer LLMs train at all.

## Connections
- [[Concept - The Residual Stream]] — the transformer's additive skip-connection bus is the direct architectural descendant of ResNet's identity shortcut.
- [[Concept - Vision Transformers]] — the architecture that replaced CNNs' fixed local inductive bias with learned global attention for large-data vision regimes.
- [[Concept - Attention Mechanism]] — a convolution is, structurally, attention with a fixed local kernel instead of learned, content-based weights; useful mental bridge between the two families.
- [[Concept - Backpropagation]] — the gradient-flow mechanics that the degradation problem and vanishing gradients both play out inside, and that skip connections directly improve.
- [[Deep Dive - Diffusion Models]] — the U-Net backbone used by most image diffusion models is a CNN with skip connections between encoder and decoder stages, a direct descendant of this lineage.
- [[Concept - Recurrent Networks and the LSTM]] — the other pre-transformer architecture family, solving an analogous depth-in-time gradient problem with gating instead of skip connections.
- [[Reference - Model Genealogy]] — places CNNs, RNNs, and transformers on one timeline for cross-architecture comparison.
- [[Concept - Vanishing and Exploding Gradients]] — the general gradient-flow pathology that both deep plain CNNs and vanilla RNNs suffer from, and that skip/gate mechanisms independently solve.

## Sources
- LeCun, Bottou, Bengio, Haffner (1998) — "Gradient-Based Learning Applied to Document Recognition." LeNet-5, the founding CNN architecture.
- Krizhevsky, Sutskever, Hinton (2012) — "ImageNet Classification with Deep Convolutional Neural Networks." AlexNet, the GPU-training moment that made deep learning dominant in vision.
- Simonyan, Zisserman (2014) — "Very Deep Convolutional Networks for Large-Scale Image Recognition." VGG, establishing stacked-3×3 depth as a design principle.
- He, Zhang, Ren, Sun (2015) — "Deep Residual Learning for Image Recognition." ResNet; identifies the degradation problem and introduces skip connections.
- Howard et al. (2017) — "MobileNets: Efficient Convolutional Neural Networks for Mobile Vision Applications." Depthwise-separable convolutions.
- Tan, Le (2019) — "EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks." Compound scaling of depth/width/resolution.
