---
tags: [concept, domain/multimodal, level/surface]
aliases: [mel spectrogram, log-mel spectrogram, log-mel features, STFT features, mel filterbank]
summary: "How raw audio becomes a log-mel spectrogram via STFT and mel filterbanks — the default ASR/TTS front-end, and why it's now half-obsolete."
---

# Concept - Audio Spectrograms and Mel Features

> **One-paragraph hook:** A raw waveform is a wall of numbers — one second of 16kHz speech is 16,000 floats with almost no structure a convolution or attention layer can exploit directly. The log-mel spectrogram is the decades-old fix: turn the 1D waveform into a 2D time-by-frequency "image" using a perceptually-motivated frequency warp, and suddenly you have something that looks like a picture a CNN or transformer already knows how to eat. Every classic ASR/TTS model — and [[Breakdown - Whisper]] specifically — runs on this representation; understanding it is the price of admission before anything else in audio modeling makes sense.

## The mechanism

Four steps turn a waveform into a spectrogram, each with a real formula and a real failure mode.

**1. Framing.** Slide a short window over the waveform — typically 25ms — with a hop of 10ms between windows (i.e., consecutive frames overlap by 15ms). A 10ms hop means the frame rate is fixed at 100 frames/second regardless of sample rate. The window (usually Hann) tapers the frame edges to zero to control spectral leakage before the FFT.

**2. STFT.** Take the FFT of each windowed frame — the Short-Time Fourier Transform. This produces a complex-valued spectrum per frame: magnitude (energy per frequency bin) and phase. Stacking magnitude spectra across frames gives a spectrogram: a time × frequency matrix.

**3. Mel warping.** Human pitch perception is roughly linear below 1kHz and logarithmic above it. The mel scale approximates this:

$$m = 2595 \log_{10}\left(1 + \frac{f}{700}\right)$$

A bank of triangular filters spaced evenly on the mel scale (not the linear Hz scale) is applied to the magnitude spectrum — literally a matrix multiply that collapses hundreds of linear FFT bins down to 80 (or 128) mel bins, each filter summing up energy in its band. This is the "mel filterbank."

**4. Log compression.** Loudness is perceived logarithmically too, so take $\log(\text{mel} + \epsilon)$. This compresses dynamic range (a factor-of-10 change in energy becomes an additive shift, not a multiplicative blowout) and stabilizes gradients during training — training directly on linear-magnitude mel energies is noticeably harder to optimize.

```
waveform (16kHz, 1D) 
  -> frame (25ms window, 10ms hop) -> 100 frames/sec
  -> FFT per frame -> magnitude spectrum
  -> mel filterbank matmul (linear Hz bins -> 80/128 mel bins)
  -> log(. + eps)
  -> log-mel spectrogram (time x mel_bins)
```

Note what's discarded at step 2: phase. The spectrogram keeps only magnitude, which is why it isn't losslessly invertible — more on this below.

## In practice

Whisper's front end is the canonical modern instance: 80 log-mel bins for tiny through large-v2, bumped to 128 for large-v3; 25ms window, 10ms hop; audio is processed in fixed 30-second chunks, giving 3,000 mel frames per chunk, which a convolutional stem then downsamples by 2× to 1,500 encoder positions. The mel-bin count is itself a capacity knob — more bins resolve finer harmonic structure, at linearly higher input dimensionality.

Standard practice is to mean/variance-normalize log-mel features (per-utterance or with dataset statistics) before feeding them to the model — skipping this, or normalizing with statistics computed differently between training and inference, is a classic silent-degradation bug.

Sample rate matters and doesn't get renegotiated automatically: speech models overwhelmingly standardize on 16kHz (the Nyquist limit of 8kHz covers essentially all speech-relevant frequency content), while music models commonly use 44.1kHz or 48kHz to capture content up past 15-20kHz. Feeding 44.1kHz audio into a 16kHz-trained model without resampling doesn't error — it just silently produces garbage features, because every mel bin now maps to the wrong physical frequency.

**SpecAugment** (Park et al. 2019) is the standard augmentation on top of log-mel features: randomly mask contiguous blocks of time frames and frequency bins (setting them to zero or the mean) during training. It's cheap, architecture-agnostic, and one of the few augmentations that reliably improves ASR word error rate across model families — the audio equivalent of Cutout/random erasing for vision.

## Failure modes

- **Phase is gone, and reconstruction is lossy.** Because the spectrogram keeps magnitude only, turning a log-mel spectrogram back into audio requires either phase estimation (Griffin-Lim iterative reconstruction — cheap but produces audible artifacts) or a learned neural vocoder (HiFi-GAN and similar) trained specifically to hallucinate plausible phase. This is a real architectural tax on any mel-based generation pipeline (see [[Concept - Neural Text-to-Speech and Audio Language Models]]).
- **Window/hop is a time-frequency resolution tradeoff, not a free parameter.** A longer window gives finer frequency resolution but coarser time resolution (and vice versa) — this is a hard uncertainty-principle-style tradeoff, not a bug to tune away. 25ms/10ms is a speech-tuned compromise; music and other domains sometimes use different values.
- **Silent sample-rate mismatch.** Resampling errors or a wrong assumed sample rate don't crash — they just misalign every mel bin's physical meaning, producing features that look normal but carry no useful signal. This is a common first debugging step when a pretrained model performs mysteriously badly on new audio.
- **Feature-normalization mismatch between train and inference** silently degrades quality the same way BatchNorm statistics mismatches do in vision models.

## The non-obvious

The STFT-then-filterbank pipeline is, mechanically, a fixed (non-learned) two-stage convolution: framing-and-FFT is a strided linear transform, and the mel filterbank is a fixed matrix multiply — [[Concept - Matrix Multiplication as the Atom of Deep Learning|literally a matmul]] applied to every frame. It's hand-engineered feature extraction of exactly the kind [[Concept - Convolutional Neural Networks|CNNs]] were supposed to make obsolete by learning filters end-to-end — and indeed, that's exactly what happened to audio too: wav2vec 2.0 and neural-codec front ends (see [[Concept - Neural Audio Codecs and Residual Vector Quantization]]) learn their own frontend directly from waveform, discarding the hand-designed mel filterbank entirely. Log-mel survives anyway, decades after CNNs made hand-crafted vision features obsolete, mostly because it's cheap, deterministic, and "good enough" — Whisper, released in 2022 with a from-scratch weakly-supervised training bet on data scale rather than architecture, still chose the boring 80-bin log-mel front end over a learned one. The lesson: hand-engineered features aren't dead where the engineering (mel-scale perceptual warping) already encodes something learning a frontend from scratch would have to rediscover from data anyway.

## Connections
- [[Breakdown - Whisper]] — Whisper's entire input pipeline is exactly this: 80/128-bin log-mel over 30-second chunks feeding a conv stem into a transformer encoder.
- [[Concept - Neural Audio Codecs and Residual Vector Quantization]] — the learned alternative to hand-designed mel features: codecs compress waveform into discrete tokens instead of a fixed spectrogram.
- [[Concept - Neural Text-to-Speech and Audio Language Models]] — TTS acoustic models historically predicted mel spectrograms as an intermediate target before a vocoder reconstructed the phase-free signal into waveform.
- [[Concept - Vision Transformers]] — the framing-and-FFT step is structurally the same "slice into fixed patches, linearly project" move a ViT applies to pixels; a spectrogram is literally an image once computed.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the mel filterbank application is a plain matmul collapsing linear FFT bins into mel bins.
- [[Concept - Convolutional Neural Networks]] — mel features are the hand-engineered analogue of what a learned conv frontend would otherwise have to discover from raw waveform.
- [[Concept - Embeddings as Learned Representations]] — log-mel is a fixed, non-learned representation, a useful contrast case against the learned-embedding paradigm dominant elsewhere in deep learning.
- [[Concept - Byte-Pair Encoding]] — both are fixed, hand-designed front-end tokenization/featurization schemes that discretize or compress a raw signal before a learned model ever sees it.

## Sources
- Park et al. (2019) — "SpecAugment: A Simple Data Augmentation Method for Automatic Speech Recognition" — time/frequency masking as the standard ASR regularizer.
- Radford et al. (2022) — "Robust Speech Recognition via Large-Scale Weak Supervision" (Whisper) — the reference log-mel front-end configuration (80 bins, 25ms/10ms framing, 30s chunks) used throughout this note's "In practice" numbers.
