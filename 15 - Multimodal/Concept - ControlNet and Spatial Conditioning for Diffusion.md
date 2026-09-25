---
tags: [concept, domain/multimodal, level/advanced]
aliases: [ControlNet, T2I-Adapter, IP-Adapter, spatial conditioning, zero convolutions]
summary: "Bolting structural control (edges, pose, depth) onto a frozen diffusion model via a trainable copy and zero-init convolutions."
---
> **One-paragraph hook:** A text prompt is a terrible way to say "the character's arm is bent like this reference photo" or "the building has this exact shape". [[Concept - Classifier-Free Guidance|Text conditioning]] steers the *content* of a generation and gives almost no control over precise *layout*. ControlNet (Zhang, Rao, Agrawala 2023) fixes this without retraining the base model. It clones part of the network, feeds the clone a control signal (a Canny edge map, a depth map, a pose skeleton), and merges the clone's output back into the frozen original through connections that start out contributing nothing. Training begins "identical to the unmodified model" and learns to steer gradually.

## The mechanism

Take a pretrained, frozen [[Breakdown - Stable Diffusion|Stable Diffusion]] U-Net (or the matching block set in a [[Concept - Diffusion Transformers (DiT)|DiT]] backbone) and clone its encoder half into a second, trainable copy. The copy takes the control image (edges, depth, pose, segmentation map) as input in place of the noisy latent. Its intermediate outputs are added into the *frozen* base network's decoder skip connections, but only through **zero-initialized 1×1 convolutions** ("zero convs"):

$$y = F_{\text{base}}(x) + Z\big(F_{\text{copy}}(x, Z(c))\big)$$

$c$ is the control signal and $Z(\cdot)$ is a zero-initialized convolution (weights and bias both start at zero). At initialization $Z(\cdot) \equiv 0$ for any input, so $y = F_{\text{base}}(x)$: the ControlNet adds nothing at step 0 and the base model's outputs don't change. Gradients still flow *through* the zero convs (a zero-weight linear layer has a well-defined, nonzero gradient with respect to its input and weights), so the copy and the zero convs learn together and the connection's contribution grows smoothly from zero. [[Concept - Diffusion Transformers (DiT)]]'s adaLN-Zero gate and [[Breakdown - Flamingo]]'s tanh-gated cross-attention use the same construction. It's the general way to graft new conditioning capacity onto a trained network without a destructive first gradient step.

The base model is frozen, and only the (roughly half-sized) copy and the light zero convs train. So each ControlNet needs only modest per-condition data and far less compute than the base model did. That's how the open-source community could train and share dozens of them on their own (Canny, depth, OpenPose, scribble, segmentation and more).

## In practice

At inference a ControlNet runs with a **control scale** in $[0, 1]$ that sets how hard the injected signal overrides the base model's own generation. Near 0 it behaves like plain text-to-image; near 1 structure locks tightly to the control image. Production pipelines commonly stack **multiple ControlNets** at once (e.g., depth + pose) with separate per-condition scales. Tools use this to keep characters pose-consistent across a shot sequence, or to hold a fixed camera layout in product photography while swapping product and background.

Two lighter relatives take other routes. **T2I-Adapter** (Mou et al. 2023) uses a much smaller side network in place of a full encoder clone, cheaper to train and run but less expressive. **IP-Adapter** (Ye et al. 2023) works on a different axis. It takes a *reference image*, not spatial structure, and injects its embedding through **decoupled cross-attention**: new K/V projections next to the text cross-attention, so the model attends to "what this reference image looks like" as a soft, non-spatial condition. Style-transfer and face-consistency tools run on this, which is a separate thing from ControlNet's pixel-aligned structural control.

## Failure modes

- **Control vs. prompt conflict.** When the control image's geometry contradicts the prompt (a depth map of a standing figure, a prompt about someone sitting), you get visible artifacts or a compromise that satisfies neither. Detection is usually visual inspection; consistently degraded outputs on one control type are the tell.
- **"Nothing is happening" early in training is expected.** Zero convs guarantee zero contribution at initialization, so the first many steps of a ControlNet run look identical to the unconditioned base model. This has repeatedly cost people debugging time on runs that were working fine.
- **Over-strong conditioning drowns out the prompt.** Push the control scale too high (or stack several strong controls) and the model can ignore text conditioning almost completely, which defeats the point of a text-to-image model.
- **Control/latent resolution mismatch.** The control image has to sit on the same spatial grid as the latent being denoised. A resolution or aspect-ratio mismatch causes spatial misalignment and no error, so it can slip silently into a bad result.

## The non-obvious

The zero-init gate shows up at least three times near here: [[Breakdown - Flamingo]]'s tanh gating, [[Concept - Diffusion Transformers (DiT)]]'s adaLN-Zero and ControlNet's zero convolutions. Three architecturally different systems, built independently, solving one problem: add new conditioning capacity to a frozen or pretrained network without a destabilizing first step. It's close to a universal pattern for "module surgery" on frozen backbones, and I'd reach for it by default whenever I bolt a new conditioning pathway onto something that already works.

*Folklore, weakly sourced:* because zero convs make the first steps of training look exactly like no ControlNet at all, more than a few practitioners have spent hours sure their training script was broken before the connection weights grew big enough to show an effect. Waiting out the "silent" phase is part of the tribal knowledge.

## Connections
- [[Concept - Latent Diffusion]] — ControlNet's control signal is injected into the same latent-space U-Net/DiT that latent diffusion runs; the spatial alignment only makes sense because everything operates on the same compressed grid.
- [[Deep Dive - Diffusion Models]] — the base forward/reverse process ControlNet leaves entirely untouched; it only adds a conditioning pathway on top.
- [[Concept - Classifier-Free Guidance]] — the existing text-conditioning mechanism ControlNet's spatial control composes with (and sometimes conflicts with) at inference time.
- [[Breakdown - Stable Diffusion]] — the concrete base model family ControlNet, T2I-Adapter, and IP-Adapter were built against and are still most commonly applied to.
- [[Deep Dive - LoRA]] — the other dominant lightweight customization method for diffusion models; LoRA adapts *style/subject* by modifying weights, ControlNet adds *spatial structure* by adding a parallel network — complementary, often stacked together.
- [[Concept - Attention Mechanism]] — the underlying operation IP-Adapter's decoupled cross-attention extends with a second set of K/V projections for the reference image.
- [[Breakdown - Flamingo]] — the earlier system using the identical zero-init-gate trick (there, tanh-gated cross-attention) to graft new modules onto a frozen network.
- [[Concept - Diffusion Transformers (DiT)]] — uses the same zero-init-gate principle (adaLN-Zero) for conditioning injection, and is the backbone ControlNet-style spatial control is increasingly being adapted to (e.g., FLUX ControlNets).

## Sources
- Zhang, Rao, Agrawala (2023) — Adding Conditional Control to Text-to-Image Diffusion Models (ControlNet). The trainable-copy + zero-convolution architecture.
- Mou et al. (2023) — T2I-Adapter: Learning Adapters to Dig out More Controllable Ability for Text-to-Image Diffusion Models.
- Ye et al. (2023) — IP-Adapter: Text Compatible Image Prompt Adapter for Text-to-Image Diffusion Models.
