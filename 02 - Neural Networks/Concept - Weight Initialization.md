---
tags: [concept, domain/neural-networks, level/advanced]
aliases: [Xavier init, Glorot init, He init, Kaiming init, variance-preserving initialization]
summary: "Initial weight scale decides whether a deep net trains at all: the variance-preservation math, the named schemes, and residual scaling."
---

# Concept - Weight Initialization

> **One-paragraph hook:** Before the first optimizer step, a network is just its initialization, and that starting scale decides whether gradients survive the trip through depth. Get the variance right and a 100-layer net trains. Get it wrong by a constant factor per layer and signals decay or blow up *exponentially* in depth and the model never leaves its init loss. Every named scheme (Xavier, He, orthogonal, GPT-2's residual scaling) is the same one-line derivation under a different architecture assumption.

## The mechanism

Take one linear layer $y = Wx$ with $W_{ij}$ i.i.d., zero-mean, variance $\sigma_W^2$, and inputs $x_j$ i.i.d. with variance $\sigma_x^2$. Each output coordinate sums `fan_in` independent products:

$$\mathrm{Var}(y_i) = \text{fan\_in} \cdot \sigma_W^2 \cdot \sigma_x^2$$

The forward signal keeps its scale iff $\text{fan\_in} \cdot \sigma_W^2 = 1$. The backward pass sends gradients through $W^\top$, so the same argument gives $\text{fan\_out} \cdot \sigma_W^2 = 1$ for gradients. You can't satisfy both unless `fan_in = fan_out`, hence the compromises below. The stakes are exponential: after $L$ layers the signal variance scales like $(\text{fan\_in}\,\sigma_W^2)^L$. A per-layer factor of $0.9$ gives $0.9^{100} \approx 2.7\times10^{-5}$ at depth 100; $1.1$ gives $\approx 1.4\times10^4$. Forward-pass twin of [[Concept - Vanishing and Exploding Gradients]].

Nonlinearities tax the variance. ReLU zeros the negative half of a symmetric distribution, so $\mathbb{E}[\mathrm{ReLU}(z)^2] = \mathrm{Var}(z)/2$, and the He factor of 2 is there only to refund that. [[Concept - Activation Functions]] lists each function's gain.

| Scheme | $\mathrm{Var}(W)$ | Derived for | Note |
|---|---|---|---|
| LeCun (1998) | $1/\text{fan\_in}$ | linear, SELU | required by self-normalizing nets |
| Xavier/Glorot (2010) | $2/(\text{fan\_in}+\text{fan\_out})$ | tanh, linear | harmonic-mean compromise of forward/backward |
| He/Kaiming (2015) | $2/\text{fan\_in}$ | ReLU family | factor 2 compensates ReLU halving variance |
| Orthogonal (Saxe et al. 2014) | $W^\top W = I$ | RNNs, deep linear-ish stacks | norm-preserving for every draw, not only in expectation |
| GPT-2 | $\mathcal{N}(0, 0.02^2)$, residual projections $\times\, 1/\sqrt{2N}$ | transformers | see below |

### Residual scaling

In a transformer, each of $N$ layers makes 2 additive writes (attention out-proj, MLP out-proj) into the residual stream of [[Concept - Residual Connections]]. Independent contributions add in variance, so the stream's variance grows linearly with depth ($2N$ writes) unless you shrink each write. GPT-2 scales the two output projections' init by $1/\sqrt{2N}$, which keeps the summed stream at $O(1)$ at any depth. Nearly every modern config of [[Deep Dive - The Transformer]] inherits this.

### Symmetry breaking

If every weight in a layer is identical (zeros, or any constant), every unit computes the same function, gets the same gradient and makes the same update. The symmetry *never* breaks, and a 4096-wide layer has effective width 1 forever. Randomness in $W$ breaks it, so bias can safely init to 0.

## In practice

- **Transformers:** truncated normal $\mathcal{N}(0, 0.02)$ for weights and [[Concept - Embeddings as Learned Representations]], zero biases, norm gains 1.0, plus the $1/\sqrt{2N}$ residual-projection scaling. The 0.02 is a hand-picked constant that happens to sit near $1/\sqrt{d}$ for GPT-2-era widths ($1/\sqrt{768} \approx 0.036$). It does *not* adapt to width. [[Concept - muP and Hyperparameter Transfer]] fixes that by making init (and LR) width-aware so hyperparameters transfer across scale.
- **PyTorch's default is not what you think.** `nn.Linear` initializes with `kaiming_uniform_(a=√5)`, a Torch7-era leftover that works out to $U(-1/\sqrt{\text{fan\_in}}, 1/\sqrt{\text{fan\_in}})$. That's closer to LeCun than to He. For anything deep and norm-free, set init explicitly.
- **Biases:** 0 everywhere, with one classic exception. The LSTM forget-gate bias inits to ~1.0 so the gate starts open and gradients flow through time from step one (popularized by Jozefowicz et al. 2015; see [[Concept - Recurrent Networks and the LSTM]]).
- **Orthogonal init** is worth the QR-decomposition cost for RNNs and very deep nets without normalization, since it preserves norms deterministically instead of in expectation.

## Failure modes

- **Too small:** activations shrink layer by layer; loss sits at its init value ($\ln C$ for $C$-way classification) and never moves. Detection: per-layer activation std at step 0 should be roughly flat across depth, not a geometric decay.
- **Too large:** pre-activations saturate or overflow. In fp16 the ceiling is 65504, so an exploding forward pass NaNs inside `exp`/softmax before the loss ever prints, one of the init-shaped failures covered in [[Concept - Floating Point for Deep Learning]].
- **Wrong fan mode for ReLU:** Xavier where He is needed loses a factor of 2 in variance per layer. He et al. (2015) showed the cliff: a 30-layer ReLU net stalls completely under Xavier but converges under He init. At 22 layers both work. Depth turns a constant-factor error into a hard failure.
- **Unbroken symmetry:** the net trains (loss falls some) but badly underfits. Detection: identical rows in a weight matrix after training.
- **Norm-free nets with sloppy init:** removing normalization removes the safety net. Fixup and [[Concept - Normalization-Free Networks]] only work because they bring back precise, depth-aware init (residual branches scaled toward zero).

## The non-obvious

Normalization partly substitutes for careful init, which is how modern practitioners got lazy about init and got away with it. [[Concept - RMSNorm and LayerNorm]] rescales whatever variance reaches it, so a transformer tolerates a 2–3× init error that would kill a plain CNN. What norm does *not* fix is the residual stream between norms. Variance still piles up across additive writes, so the $1/\sqrt{2N}$ scaling survives in every modern LLM config even with RMSNorm in every block. Flip side: strip normalization out (for throughput or simplicity) and init is the whole stability story again.

## Connections

- [[Concept - Vanishing and Exploding Gradients]] — init is the step-0 defense against the exponential Jacobian-product pathology this note's math previews.
- [[Concept - Activation Functions]] — each nonlinearity has a variance gain (ReLU's ½, tanh's ~1) that the init scheme must refund.
- [[Concept - Residual Connections]] — the additive stream's linear variance growth with depth is what residual-projection scaling controls.
- [[Concept - RMSNorm and LayerNorm]] — normalization partially substitutes for init, and understanding which jobs it does (and doesn't) take over is the practical crux.
- [[Concept - Normalization-Free Networks]] — the up-stack consequence: remove norm and precise init (Fixup, NF-Net) must return.
- [[Deep Dive - The Transformer]] — where the GPT-2 init recipe ($\mathcal{N}(0,0.02)$ + residual scaling) lives in a full architecture.
- [[Concept - muP and Hyperparameter Transfer]] — the width-aware reparameterization that fixes the "0.02 doesn't scale" defect and makes LR/init transfer across model sizes.
- [[Concept - Embeddings as Learned Representations]] — embedding rows get the same $\mathcal{N}(0,0.02)$ treatment, and undertrained rows that keep their init norm become glitch-token pathologies.
- [[Concept - Recurrent Networks and the LSTM]] — home of the forget-gate-bias-to-1.0 exception to "biases init to zero."
- [[Concept - Floating Point for Deep Learning]] — init errors surface first as overflow/underflow once activations leave fp16/bf16's representable range.

## Sources

- Glorot & Bengio (2010) — Understanding the difficulty of training deep feedforward neural networks. The Xavier derivation and the forward/backward compromise.
- He et al. (2015) — Delving Deep into Rectifiers. He init, the ReLU factor of 2, and the 30-layer Xavier-vs-He cliff.
- Saxe et al. (2014) — Exact solutions to the nonlinear dynamics of learning in deep linear networks. Orthogonal init's theoretical grounding.
- Radford et al. (2019) — Language Models are Unsupervised Multitask Learners (GPT-2). Source of the $\mathcal{N}(0,0.02)$ + $1/\sqrt{2N}$ residual-scaling recipe.
- Zhang et al. (2019) — Fixup Initialization. Training deep residual nets with no normalization via init alone.
- Jozefowicz et al. (2015) — An Empirical Exploration of Recurrent Network Architectures. The forget-gate bias ≈ 1.0 recommendation.
