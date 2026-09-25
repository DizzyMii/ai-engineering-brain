---
tags: [concept, domain/multimodal, level/surface]
aliases: [mel spectrogram, log-mel spectrogram, log-mel features, STFT features, mel filterbank]
summary: "How raw audio becomes a log-mel spectrogram via STFT and mel filterbanks — the default ASR/TTS front-end, and why it's now half-obsolete."
---

# Concept - Audio Spectrograms and Mel Features

> **One-paragraph hook:** A raw waveform is a wall of numbers. One second of 16kHz speech is 16,000 floats with almost no structure a convolution or attention layer can use directly. The log-mel spectrogram is the decades-old fix: warp frequency the way hearing does, turn the 1D waveform into a 2D time-by-frequency "image", and you have something a CNN or transformer already knows how to eat. Every classic ASR/TTS model runs on this representation, [[Breakdown - Whisper]] included. You need it before anything else in audio modeling makes sense.

## The mechanism

Four steps turn a waveform into a spectrogram. Each has a real formula and a real failure mode.

**1. Framing.** Slide a short window over the waveform, typically 25ms, with a 10ms hop between windows (so consecutive frames overlap by 15ms). A 10ms hop fixes the frame rate at 100 frames/second whatever the sample rate. The window (usually Hann) tapers frame edges to zero to limit spectral leakage before the FFT.

**2. STFT.** FFT each windowed frame; that's the Short-Time Fourier Transform. You get a complex spectrum per frame: magnitude (energy per frequency bin) and phase. Stack the magnitude spectra across frames and you have a spectrogram, a time × frequency matrix.

**3. Mel warping.** People hear pitch roughly linearly below 1kHz and logarithmically above it. The mel scale approximates that:

$$m = 2595 \log_{10}\left(1 + \frac{f}{700}\right)$$

A bank of triangular filters, spaced evenly on the mel scale instead of linear Hz, is applied to the magnitude spectrum. It's a matrix multiply that collapses hundreds of linear FFT bins into 80 (or 128) mel bins, each filter summing the energy in its band. That's the "mel filterbank."

**4. Log compression.** Loudness is perceived logarithmically too, so take $\log(\text{mel} + \epsilon)$. This compresses dynamic range (a factor-of-10 energy change becomes an additive shift instead of a multiplicative blowout) and stabilizes gradients. Linear-magnitude mel energies are noticeably harder to optimize on.

```
waveform (16kHz, 1D) 
  -> frame (25ms window, 10ms hop) -> 100 frames/sec
  -> FFT per frame -> magnitude spectrum
  -> mel filterbank matmul (linear Hz bins -> 80/128 mel bins)
  -> log(. + eps)
  -> log-mel spectrogram (time x mel_bins)
```

Step 2 throws away phase. The spectrogram keeps magnitude only, so it can't be inverted losslessly. More on that below.

## In practice

Whisper's front end is the standard modern example: 80 log-mel bins for tiny through large-v2, 128 for large-v3; 25ms window, 10ms hop. Audio goes in as fixed 30-second chunks, 3,000 mel frames each, and a convolutional stem downsamples that 2× to 1,500 encoder positions. The mel-bin count is a capacity knob: more bins resolve finer harmonic structure at linearly higher input dimensionality.

Mean/variance-normalize log-mel features (per utterance or with dataset statistics) before they reach the model. Skipping it, or computing the statistics differently in training and inference, is a classic silent-degradation bug.

Sample rate matters, and nothing renegotiates it for you. Speech models overwhelmingly standardize on 16kHz (the 8kHz Nyquist limit covers essentially all speech-relevant frequencies). Music models commonly use 44.1kHz or 48kHz to capture content up past 15-20kHz. Feed 44.1kHz audio to a 16kHz-trained model without resampling and nothing errors. You get garbage features, because every mel bin now maps to the wrong physical frequency.

**SpecAugment** (Park et al. 2019) is the standard augmentation on log-mel features. During training it masks random contiguous blocks of time frames and frequency bins (to zero or the mean). It's cheap, works with any architecture, and is one of the few augmentations that reliably improves ASR word error rate across model families. It is the audio counterpart of Cutout/random erasing in vision.

## Failure modes

- **Phase is gone, so reconstruction is lossy.** With magnitude only, getting audio back from a log-mel spectrogram takes either phase estimation (Griffin-Lim iterative reconstruction, cheap but with audible artifacts) or a learned neural vocoder (HiFi-GAN and similar) trained to hallucinate plausible phase. Every mel-based generation pipeline pays this architectural tax (see [[Concept - Neural Text-to-Speech and Audio Language Models]]).
- **Window/hop trades time resolution for frequency resolution.** A longer window gives finer frequency resolution and coarser time resolution, and vice versa. It's a hard uncertainty-principle-style tradeoff you can't tune away. 25ms/10ms is a compromise tuned for speech; music and other domains sometimes use different values.
- **Silent sample-rate mismatch.** A resampling error or wrong assumed sample rate doesn't crash anything. It misaligns what every mel bin means physically, and the features look normal while carrying no useful signal. Check this first when a pretrained model does mysteriously badly on new audio.
- **Train/inference feature-normalization mismatch** degrades quality silently, the same way mismatched BatchNorm statistics do in vision models.

## The non-obvious

Mechanically, STFT-then-filterbank is a fixed, non-learned two-stage convolution. Framing plus FFT is a strided linear transform, and the mel filterbank is a fixed matrix, [[Concept - Matrix Multiplication as the Atom of Deep Learning|literally a matmul]] on every frame. It's the kind of hand-engineered feature extraction [[Concept - Convolutional Neural Networks|CNNs]] were supposed to retire by learning filters end to end. In audio that did happen: wav2vec 2.0 and neural-codec front ends (see [[Concept - Neural Audio Codecs and Residual Vector Quantization]]) learn their frontend straight from the waveform and drop the mel filterbank entirely.

Log-mel survives anyway, decades after CNNs killed hand-crafted vision features, mostly because it's cheap, deterministic and "good enough". Whisper, released in 2022 as a from-scratch bet on data scale over architecture, still picked the boring 80-bin log-mel front end over a learned one. Hand-engineered features hold on where the engineering (mel-scale perceptual warping) already encodes something a learned frontend would have to rediscover from data anyway.

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
