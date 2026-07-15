---
tags: [concept, domain/architectures, level/surface]
aliases: [RNN, LSTM, GRU, recurrent neural network, long short-term memory, gated recurrent unit]
summary: "The pre-transformer sequence architecture: hidden-state recurrence, LSTM/GRU gating that fixes vanishing gradients, and why sequential compute lost to parallel attention."
---
> **One-paragraph hook:** For two decades before the transformer, recurrent networks were the default architecture for sequences: a hidden state updated one token at a time, carrying a compressed summary of everything seen so far. The LSTM's gating mechanism solved the vanishing-gradient problem that crippled vanilla RNNs on long sequences, and the attention mechanism that later became [[Concept - Attention Mechanism]] was invented as a patch for an RNN bottleneck — recurrent networks aren't a dead end, they're the architecture the transformer grew out of, and they're having a partial comeback via [[Concept - State Space Models and Mamba]].

## The mechanism

**Vanilla RNN.** At each timestep, a hidden state is updated as a function of the previous hidden state and the current input: `h_t = tanh(W_h h_{t-1} + W_x x_t + b)`. Training unrolls this recurrence across all timesteps into one long computational graph and backpropagates through it — backpropagation-through-time (BPTT). The gradient of the loss at the final step with respect to a hidden state `t` steps back involves a product of roughly `T - t` Jacobians, each bounded by `‖W_h‖ · max(tanh')  ≤ ‖W_h‖`. If the dominant eigenvalue of `W_h` is less than 1, this product shrinks exponentially with distance — **vanishing gradients**; if greater than 1, it grows exponentially — **exploding gradients** (Bengio et al. 1994; formalized further by Pascanu et al. 2013). In practice this bounds a vanilla RNN's effective memory to roughly 10-20 steps for most tasks, regardless of how large the hidden state is.

**LSTM (Hochreiter & Schmidhuber 1997).** The fix is a second, separately-updated state — the cell state `c_t` — combined with three sigmoid gates that control information flow:

$$
\begin{aligned}
f_t &= \sigma(W_f[h_{t-1}, x_t]) &\text{(forget gate)}\\
i_t &= \sigma(W_i[h_{t-1}, x_t]) &\text{(input gate)}\\
o_t &= \sigma(W_o[h_{t-1}, x_t]) &\text{(output gate)}\\
g_t &= \tanh(W_g[h_{t-1}, x_t]) &\text{(candidate update)}\\
c_t &= f_t \odot c_{t-1} + i_t \odot g_t &\text{(cell state update)}\\
h_t &= o_t \odot \tanh(c_t) &\text{(hidden state)}
\end{aligned}
$$

The critical move is that `c_t` is updated **additively** and gated **elementwise**, not passed through a repeated matrix multiplication. The gradient `∂c_t / ∂c_{t-1} = f_t` (elementwise), not a matrix power of `W_h`. When the forget gate learns `f_t ≈ 1` for a given channel, gradient flows through that channel essentially undamped across arbitrarily many timesteps — the forget gate is functionally a **residual/highway connection running through time**, decades before ResNet made the same trick spatial (see the non-obvious section of [[Concept - Convolutional Neural Networks]] for the parallel).

**GRU (Cho et al. 2014).** Merges the cell and hidden state into one and uses two gates instead of three — a reset gate `r_t` and an update gate `z_t`, with `h_t = (1 - z_t) ⊙ h_{t-1} + z_t ⊙ h̃_t`. Fewer parameters than an LSTM, comparable performance on most benchmarks, and faster to train — a common default when LSTM's extra gate wasn't earning its cost.

```text
LSTM cell at step t:
  h_{t-1}, x_t ──► [forget f_t] ──┐
                                  ×── c_{t-1}
  h_{t-1}, x_t ──► [input i_t]  ──┐        │
  h_{t-1}, x_t ──► [candidate g_t]┘   ×    │
                                    └──►(+)──► c_t
  h_{t-1}, x_t ──► [output o_t] ──►  ×tanh(c_t) ──► h_t
```

## In practice

**Seq2seq** (Sutskever et al. 2014) chained two RNNs: an encoder compresses the whole input into one fixed-size final hidden state, a decoder generates the output conditioned on that single vector — an obvious bottleneck for long inputs. **Bahdanau attention** (Bahdanau et al. 2014) fixed exactly this: instead of forcing the decoder through one compressed vector, let it compute a weighted sum over *all* encoder hidden states at every decoding step. This "attention over encoder states," invented as a patch for an RNN's fixed-vector bottleneck, is the direct conceptual ancestor of [[Concept - Attention Mechanism]] and eventually the transformer that dropped the recurrence entirely and kept only the attention.

Tribal training practice from the RNN era that's still relevant: **gradient clipping** (clip the global gradient norm to roughly 1.0–5.0) is close to mandatory — it controls the exploding-gradient half of the problem without touching the vanishing half. **Truncated BPTT** backpropagates only through a fixed window (e.g. 20-100 steps) instead of the full sequence, trading a small bias for tractable memory and compute. **Orthogonal or identity initialization** of the recurrent weight matrix (Le et al. 2015, the "IRNN" trick) keeps the Jacobian's spectral radius near 1 at the start of training, delaying the onset of vanishing/exploding gradients.

**Why RNNs lost to transformers for large language models** is not primarily a capacity argument — it's a hardware-utilization argument. Computing `h_t` requires `h_{t-1}`, an inherently sequential dependency across the time axis: a GPU with thousands of cores sits mostly idle processing one token at a time. A transformer computes all `N` positions' attention and FFN as dense matrix multiplies in parallel, using the causal mask (rather than a sequential loop) to enforce autoregressive structure, and achieves dramatically higher GPU utilization at the same FLOP count. Training-time parallelism, not any intrinsic modeling advantage, is the decisive reason [[Deep Dive - The Transformer]] displaced the LSTM for large-scale language modeling.

## Failure modes

- **Vanishing gradients in vanilla RNNs.** Symptom: the model cannot learn dependencies beyond roughly 10-20 tokens no matter how it's tuned; detect by sweeping the distance between a signal and the token that depends on it and watching performance fall off a cliff.
- **Exploding gradients.** Loss goes to NaN/Inf mid-training with no warning; caught by monitoring gradient-norm spikes before the loss itself blows up; fixed with gradient clipping.
- **Soft vanishing even with gating.** LSTMs and GRUs push the practical memory horizon out from ~20 steps to hundreds or low thousands, but they don't eliminate the problem — if the forget gate is persistently below 1 for a channel, information still decays geometrically over very long sequences, just far more slowly than the vanilla-RNN case.
- **Sequential decode bottleneck at inference.** Generating token `t+1` requires having already computed `h_t`, so — unlike a transformer's parallel prefill — batch throughput for RNN generation does not parallelize across the time dimension, only across the batch dimension, which caps serving throughput on modern accelerators regardless of how much spare compute they have.

## The non-obvious

The LSTM's forget gate solved, in 1997, essentially the same mathematical problem that ResNet's skip connection solved in 2015 and that the transformer's [[Concept - The Residual Stream]] runs on today: replace a repeated multiplicative composition (which geometrically attenuates or amplifies signal) with an additive, gated update, so that a "do nothing" pass-through is cheap for the network to learn. Hochreiter's diagnosis of the vanishing-gradient problem — via the same Jacobian-product argument later formalized by Bengio et al. (1994) — predates both the CNN degradation problem and the transformer training-stability literature by nearly two decades. Folklore, weakly sourced: it's common for practitioners encountering pre-norm residual streams or highway networks for the first time to treat "make gradients flow additively" as a modern architectural insight, when the LSTM had already implemented and shipped the identical fix — in time rather than in depth — before most of today's LLM engineers were writing code.

## Connections
- [[Concept - State Space Models and Mamba]] — the modern revival of the recurrence idea: a linear state update that's parallelizable at train time, effectively "RNNs done right" for the GPU era.
- [[Concept - Linear Attention]] — reformulated as a recurrence with a matrix-valued hidden state, making it mathematically a fast-weight RNN in disguise.
- [[Concept - Attention Mechanism]] — grew directly out of Bahdanau's fix for the seq2seq encoder bottleneck; this note is the historical prerequisite for that one.
- [[Concept - Backpropagation]] — BPTT is backpropagation applied to an unrolled recurrent graph; the vanishing/exploding gradient analysis depends on the same chain-rule mechanics.
- [[Deep Dive - The Transformer]] — the architecture that replaced RNNs for LLMs specifically because it parallelizes training across the sequence dimension.
- [[Reference - Model Genealogy]] — situates RNN/LSTM/GRU on the same timeline as CNNs and transformers.
- [[Concept - Adam and AdamW]] — the optimizer family that, alongside gradient clipping, made training deep recurrent (and later, deep transformer) networks practically tractable.
- [[Concept - Vanishing and Exploding Gradients]] — the general phenomenon this note's core mechanism section derives in the recurrent-in-time case specifically.

## Sources
- Hochreiter, Schmidhuber (1997) — "Long Short-Term Memory." Introduces the gated cell-state architecture that fixes vanishing gradients over long sequences.
- Bengio, Simard, Frasconi (1994) — "Learning Long-Term Dependencies with Gradient Descent is Difficult." Formal diagnosis of the vanishing/exploding gradient problem in recurrent networks.
- Cho et al. (2014) — "Learning Phrase Representations using RNN Encoder-Decoder for Statistical Machine Translation." Introduces the GRU.
- Sutskever, Vinyals, Le (2014) — "Sequence to Sequence Learning with Neural Networks." The encoder-decoder RNN architecture and its fixed-vector bottleneck.
- Bahdanau, Cho, Bengio (2014) — "Neural Machine Translation by Jointly Learning to Align and Translate." Introduces attention as a fix for the seq2seq bottleneck.
- Pascanu, Mikolov, Bengio (2013) — "On the Difficulty of Training Recurrent Neural Networks." Formalizes gradient clipping as the practical fix for exploding gradients.
