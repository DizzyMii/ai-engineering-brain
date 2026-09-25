---
tags: [concept, domain/architectures, level/surface]
aliases: [CNN, ConvNet, convolutional network]
summary: "The convolution-based architecture family: weight sharing, receptive fields, and the ResNet skip connection the transformer residual stream inherits."
---
> **One-paragraph hook:** Before transformers, convolutional networks were the default for anything spatial: images, and for a while audio and even early text models. A CNN builds representations by sliding a small, shared kernel across the input, betting that a useful visual pattern (an edge, a texture) means the same thing wherever it appears. Two ideas from this lineage matter well beyond vision. One is the receptive-field-grows-with-depth math that every "local attention" pattern reuses. The other is the ResNet skip connection, the direct ancestor of [[Concept - The Residual Stream]] that every modern LLM is built on.

## The mechanism

A convolution computes local dot products between a small learned kernel and a sliding window over the input. For a 1D signal, `y[i] = Σ_k x[i+k] · w[k]`. In 2D, a `k×k` kernel slides over height and width, and a real network has `C_in → C_out` channel maps, so one conv layer applies `C_out` different `k×k×C_in` filters. The key property is **weight sharing**: the same kernel weights apply at every spatial location. That buys far fewer parameters than a dense layer over the same input (`k·k·C_in·C_out` versus `H·W·C_in·C_out` for a fully-connected layer), plus translation equivariance: shift the input and the output feature map shifts identically, since the same filter fires wherever its pattern occurs.

The **receptive field**, meaning how much of the input one output unit can "see," grows with depth, stride, and dilation. Two stacked `3×3` convolutions have the same receptive field as one `5×5` (`3+3-1=5`) with fewer parameters (`2·9=18` vs `25`) and an extra nonlinearity in between. That was the core of VGG's design (Simonyan & Zisserman 2014): go deep with small kernels instead of wide with large ones. Pooling (max or average) downsamples spatially, throwing away exact position but keeping presence information, and grows the receptive field cheaply. Dilated (atrous) convolutions space out the kernel taps, which widens the receptive field with no extra parameters and no downsampling; segmentation and other dense-prediction tasks use them heavily. [[Concept - Sparse and Sliding-Window Attention]] borrows the same depth-grows-receptive-field math when it stacks local-attention layers to reach past a single window.

With depth, a feature hierarchy shows up empirically. Early layers detect edges and simple gradients, middle layers combine them into textures and parts, late layers respond to whole objects. Nobody supervises this; it falls out of stacking convolution + nonlinearity + pooling.

```text
Input             Kernel (3x3)         Output feature map
[H x W x C_in] -- slides & dot-products --> [H' x W' x C_out]
   each output pixel = weighted sum of a local k×k×C_in patch
   same kernel weights reused at every spatial position
```

## In practice

The lineage:
- **LeNet-5** (LeCun et al. 1998) established convolution + pooling for digit recognition.
- **AlexNet** (Krizhevsky et al. 2012): 8 layers, ReLU activations, trained on two GPUs. It cut ImageNet top-5 error by roughly 10 points versus the prior best and is generally credited as the moment deep learning took over vision.
- **VGG** (Simonyan & Zisserman 2014) pushed depth to 16–19 layers with uniform stacks of `3×3` convolutions.
- **ResNet** (He et al. 2015) added skip connections, reached 152 layers, and won ILSVRC 2015.
- **EfficientNet** (Tan & Le 2019) introduced compound scaling: depth, width, and input resolution scaled jointly by a fixed ratio instead of tuned one at a time.

Efficiency tricks that persist: `1×1` convolutions do cheap channel mixing and dimensionality reduction (all over Inception, and as the "bottleneck" in ResNet blocks). Depthwise-separable convolutions (MobileNet, Howard et al. 2017) factor a standard `k×k` convolution into a per-channel spatial convolution plus a `1×1` pointwise mix. That cuts compute by roughly `1/C_out + 1/k²` relative to a standard conv, an 8-9x reduction for typical `3×3` kernels at reasonable channel counts, and it's why MobileNet-style blocks are the default for on-device vision.

Where CNNs still win as of 2026: small-data regimes, where the built-in translation-equivariance prior generalizes better than a data-hungry [[Concept - Vision Transformers]] trained from scratch; and edge or latency-constrained deployment (mobile, embedded, real-time video), where a well-optimized ConvNet's lower FLOP count and mature hardware support beat a ViT of comparable quality. CNN backbones (the U-Nets in [[Deep Dive - Diffusion Models]]) also remain the default spatial substrate in much of image generation, even after attention-heavy architectures took over language.

## Failure modes

- **The degradation problem.** Before ResNet, stacking more plain convolutional layers made optimization *harder*, beyond any overfitting effect. A 56-layer plain network had higher training *and* test error than a 20-layer version of the same design. It's an optimization pathology. The tell: more depth raises training loss, which overfitting can't explain.
- **Vanishing gradients through deep, non-skip stacks.** Backpropagating through many nonlinear conv layers with no residual path attenuates gradients toward the input. In training diagnostics, look for near-zero gradient norms in early layers relative to late ones.
- **Checkerboard artifacts.** Strided transposed convolutions used for upsampling in generative and segmentation models can leave visible grid/checkerboard patterns in the output, a direct result of uneven kernel overlap. Spot them by eye or in the spatial autocorrelation of output activations.
- **Overfitting on small datasets without regularization.** Weight sharing saves parameters, but a deep enough CNN without batch normalization, dropout, or augmentation still memorizes a small training set. Symptom: a large train/validation gap. Standard vision augmentation mitigates it.

## The non-obvious

ResNet's skip connection is usually explained as "fixing vanishing gradients." He et al. (2015) were explicit that the deeper problem was **degradation**. Even with batch normalization already taming gradient magnitudes, plain deep networks got measurably *worse* at optimization as depth grew. The network struggled to learn an identity mapping through a stack of nonlinear layers, though that solution trivially exists and could never hurt accuracy. The residual form `y = F(x) + x` makes identity the *default*. A layer only has to learn `F(x) ≈ 0` to be a no-op, a far easier target than learning `F(x) = x` through a nonlinear composition. Make the trivial solution cheap to reach, then let gradient descent add useful deviations on top: [[Concept - The Residual Stream]] inherits that idea in every modern transformer block, `x = x + f(norm(x))`, though transformers have no spatial structure at all. The skip connection did more than let CNNs go deep. It's the reason any of today's 100+ layer LLMs train at all.

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
