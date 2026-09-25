---
tags: [concept, domain/architectures, level/surface]
aliases: [RNN, LSTM, GRU, recurrent neural network, long short-term memory, gated recurrent unit]
summary: "The pre-transformer sequence architecture: hidden-state recurrence, LSTM/GRU gating that fixes vanishing gradients, and why sequential compute lost to parallel attention."
---
> **One-paragraph hook:** For two decades before the transformer, recurrent networks were the default for sequences. A hidden state updates one token at a time and carries a compressed summary of everything seen so far. The LSTM's gating solved the vanishing-gradient problem that crippled vanilla RNNs on long sequences, and the attention mechanism that later became [[Concept - Attention Mechanism]] started life as a patch for an RNN bottleneck. So recurrent networks are the architecture the transformer grew out of, and they're having a partial comeback via [[Concept - State Space Models and Mamba]].

## The mechanism

**Vanilla RNN.** Each timestep updates the hidden state from the previous hidden state and the current input: `h_t = tanh(W_h h_{t-1} + W_x x_t + b)`. Training unrolls the recurrence across all timesteps into one long computational graph and backpropagates through it (backpropagation-through-time, BPTT). The gradient of the final-step loss with respect to a hidden state `t` steps back involves a product of roughly `T - t` Jacobians, each bounded by `‖W_h‖ · max(tanh')  ≤ ‖W_h‖`. If the dominant eigenvalue of `W_h` is below 1, that product shrinks exponentially with distance: **vanishing gradients**. Above 1, it grows exponentially: **exploding gradients** (Bengio et al. 1994; formalized further by Pascanu et al. 2013). In practice this caps a vanilla RNN's effective memory at roughly 10-20 steps for most tasks, however large the hidden state is.

**LSTM (Hochreiter & Schmidhuber 1997).** The fix adds a second, separately updated state, the cell state `c_t`, plus three sigmoid gates that control information flow:

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

`c_t` is updated **additively** and gated **elementwise**. There's no repeated matrix multiplication, so the gradient `∂c_t / ∂c_{t-1} = f_t` (elementwise) instead of a matrix power of `W_h`. When the forget gate learns `f_t ≈ 1` for a channel, gradient flows through that channel essentially undamped across arbitrarily many timesteps. The forget gate works as a **residual/highway connection running through time**, decades before ResNet made the same trick spatial (the non-obvious section of [[Concept - Convolutional Neural Networks]] draws the parallel).

**GRU (Cho et al. 2014).** Merges cell and hidden state into one and uses two gates: a reset gate `r_t` and an update gate `z_t`, with `h_t = (1 - z_t) ⊙ h_{t-1} + z_t ⊙ h̃_t`. It has fewer parameters than an LSTM, performs comparably on most benchmarks and trains faster. People picked it by default when the LSTM's extra gate wasn't earning its cost.

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

**Seq2seq** (Sutskever et al. 2014) chained two RNNs. An encoder compresses the whole input into one fixed-size final hidden state, and a decoder generates the output conditioned on that single vector, which is an obvious bottleneck for long inputs. **Bahdanau attention** (Bahdanau et al. 2014) removed it by letting the decoder compute a weighted sum over *all* encoder hidden states at every decoding step. That "attention over encoder states" patch is the direct conceptual ancestor of [[Concept - Attention Mechanism]], and of the transformer, which dropped the recurrence and kept only the attention.

Some RNN-era training practice is still relevant. **Gradient clipping** (clip the global gradient norm to roughly 1.0–5.0) is close to mandatory; it handles the exploding half of the problem and does nothing for the vanishing half. **Truncated BPTT** backpropagates through a fixed window (e.g. 20-100 steps) instead of the full sequence, accepting a small bias for tractable memory and compute. **Orthogonal or identity initialization** of the recurrent weight matrix (Le et al. 2015, the "IRNN" trick) keeps the Jacobian's spectral radius near 1 at the start of training, which delays the onset of vanishing/exploding gradients.

RNNs lost to transformers for large language models mainly over hardware utilization. Capacity was a secondary issue. Computing `h_t` needs `h_{t-1}`, a sequential dependency along the time axis, so a GPU with thousands of cores sits mostly idle processing one token at a time. A transformer computes attention and FFN for all `N` positions as dense parallel matrix multiplies, enforces autoregressive structure with the causal mask in place of a sequential loop, and gets dramatically higher GPU utilization at the same FLOP count. Training-time parallelism, and no intrinsic modeling advantage, is the decisive reason [[Deep Dive - The Transformer]] displaced the LSTM for large-scale language modeling.

## Failure modes

- **Vanishing gradients in vanilla RNNs.** The model can't learn dependencies beyond roughly 10-20 tokens no matter how you tune it. To detect it, sweep the distance between a signal and the token that depends on it and watch performance fall off a cliff.
- **Exploding gradients.** Loss goes to NaN/Inf mid-training with no warning. Gradient-norm spikes show up before the loss blows up, so monitor those; gradient clipping fixes it.
- **Soft vanishing even with gating.** LSTMs and GRUs push the practical memory horizon from ~20 steps out to hundreds or low thousands, but the problem remains. If a channel's forget gate stays below 1, information in it still decays geometrically over very long sequences, just far more slowly than in a vanilla RNN.
- **Sequential decode bottleneck at inference.** Generating token `t+1` requires `h_t` already computed. A transformer's prefill runs in parallel; RNN generation parallelizes only across the batch dimension, never across time. That caps serving throughput on modern accelerators however much spare compute they have.

## The non-obvious

In 1997 the LSTM's forget gate solved essentially the same math problem that ResNet's skip connection solved in 2015, and that the transformer's [[Concept - The Residual Stream]] runs on today. Replace a repeated multiplicative composition, which geometrically attenuates or amplifies signal, with an additive gated update, and a "do nothing" pass-through becomes cheap for the network to learn. Hochreiter diagnosed the vanishing-gradient problem with the same Jacobian-product argument Bengio et al. (1994) later formalized, nearly two decades before the CNN degradation problem and the transformer training-stability literature. Folklore, weakly sourced: practitioners meeting pre-norm residual streams or highway networks for the first time often treat "make gradients flow additively" as a modern insight. The LSTM had already shipped the identical fix, in time instead of depth, before most of today's LLM engineers were writing code.

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
