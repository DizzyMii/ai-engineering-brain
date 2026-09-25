---
tags: [concept, domain/esoterica, level/advanced]
aliases: [softmax bottleneck, Mixture of Softmaxes, MoS, stolen probability]
summary: "A single softmax over H·Wᵀ caps expressible next-token distributions at rank d — a capacity ceiling independent of training quality."
---
> **One-paragraph hook:** Every autoregressive language model computes its next-token distribution the same way: dot the final hidden state against an embedding matrix and softmax the result. That one design choice puts a hard mathematical ceiling on which conditional distributions the model can ever express, however well it's trained and however much data it sees. This is the softmax bottleneck. It's a rank limit in the output layer's linear algebra, training can't touch it, and it's why some tokens can never be generated at greedy decode whatever the model's quality.

## The mechanism
Yang et al. 2018, "Breaking the Softmax Bottleneck: A High-Rank RNN Language Model," made the argument precise. A language model's pre-[[Concept - Softmax]] logits are $L = H W^\top$, where $H \in \mathbb{R}^{n \times d}$ stacks the $n$ distinct context hidden states the model can produce and $W \in \mathbb{R}^{|V| \times d}$ is the output embedding matrix over a vocabulary of size $|V|$. The matrix of true log-probabilities the model has to represent (one row per context, one column per token) is a function of $L$. Since $L$ is a product of two matrices with inner dimension $d$, $\mathrm{rank}(L) \le d$.

Natural-language next-token log-probability matrices are empirically **high-rank**. Different contexts need distributions over the vocabulary that differ in shape, and those shapes can't be built as a low-dimensional linear combination of a shared basis. When $d \ll |V|$ (a hidden dimension of a few thousand against a vocabulary of tens of thousands, itself set by [[Concept - Byte-Pair Encoding]]'s vocabulary size), there provably exist context-conditional distributions the model **cannot represent for any setting of its weights**. That isn't underfitting. More data or more steps can't fix it, because the ceiling comes from the rank of the factorization, whatever factors you pick.

The paper's fix is **Mixture of Softmaxes (MoS)**. Compute $K$ context vectors from the hidden state, run a softmax over each, and mix:

$$P(y \mid c) = \sum_{k=1}^{K} \pi_k(c) \cdot \mathrm{softmax}(h_k(c)^\top w_y)$$

where $\pi_k(c)$ are context-dependent mixing weights. A single softmax is rank-$d$-limited; the **log of a mixture** of softmaxes isn't bounded the same way, because mixing in probability space (as opposed to logit space) escapes the linear-algebra constraint. MoS measurably improves perplexity on PTB and WikiText, at a real price: $K$ softmaxes per step is roughly $K$ times the output-layer compute of one. That's why it hasn't caught on in frontier-scale serving, where the output layer is already a meaningful share of decode cost.

A sharper and more practical corollary comes from Demeter et al. 2020, "Stolen Probability: A Structural Weakness of Neural Language Models." Logits are dot products between a hidden state and a *fixed* embedding per token. So a token whose output embedding sits strictly inside the convex hull of the other tokens' embeddings can **never be the single top logit for any hidden state**. Geometrically, its neighbors always "steal" its probability first. Some tokens simply can't be produced at greedy decode, as a consequence of embedding geometry and regardless of training quality. That shapes how [[Concept - Sampling and Decoding Parameters]] and greedy/beam decoding behave, and it's a standing contributor to the degenerate outputs studied in [[Concept - Neural Text Degeneration and Repetition Loops]].

## In practice
Modern frontier LLMs mostly dodge the worst of it by making $d$ large. Hidden dimensions of 4096–16384 are big relative to the effective rank most natural-language distributions need, so the ceiling rarely binds. Untied, large output heads also help: a separate unembedding matrix, learned independently of the input [[Concept - Embeddings as Learned Representations]], has more room to place token vectors usefully, since it doesn't have to double as the input embedding.

The bottleneck comes back where it's easy to forget. Small models (edge/mobile LLMs with $d$ in the low hundreds). Aggressive tying of input and output embeddings, which is common where you're saving parameters, which is also where $d$ is already tightest. And any deliberately low-rank output projection added to save memory or compute.

## Failure modes
- **Over-smoothing in small or heavily tied models.** The model can't sharply separate near-synonyms or closely related candidates; probability smears across a cluster of plausible tokens instead of committing. With $d$ small relative to $|V|$, the achievable logit matrix is too low-rank to give every context that needs one a sharp peak. Detection: probe minimal pairs (near-identical prompts that should produce very different sharp distributions) and check whether top-token probabilities are suspiciously flat across them.
- **Greedy decode silently skipping disadvantaged tokens.** Some vocabulary tokens almost never come out as the argmax, even where they're clearly the best answer, because stolen-probability geometry puts their embedding inside the convex hull of competitors. More training on the same architecture won't fix it. The levers are sampling-based decoding, larger untied output heads, or changes to embedding geometry.
- **Interaction with final-layer normalization and temperature.** How sharp the output can get depends on logit temperature and the final [[Concept - Softmax]] call. Tuning temperature to "fix" a flat-looking distribution can hide a real rank limit without resolving it.

## The non-obvious
The useful takeaway isn't "add Mixture of Softmaxes." MoS costs too much for almost anyone to ship at frontier scale, and large hidden dimensions already make the rank ceiling a non-issue for most contexts. What holds at any scale is the stolen-probability corollary. Because output logits are dot products against fixed embeddings, which tokens can win at greedy decode is a **permanent geometric property that training doesn't change**, unrelated to how well the model understands the context. So when a model assigns token X near-zero probability, be more suspicious than usual if X's embedding might just be geometrically disadvantaged. The fix there is in decoding strategy or embedding-space design, and more training won't help.

## Connections
- [[Concept - Softmax]] — the softmax bottleneck is a rank limitation on what a single softmax's logit-generating matrix factorization can express, not a property of the softmax nonlinearity itself.
- [[Concept - Sampling and Decoding Parameters]] — greedy and low-temperature decoding are exactly where the stolen-probability corollary bites hardest; sampling strategies are one of the few practical mitigations.
- [[Concept - Byte-Pair Encoding]] — vocabulary size $|V|$ set by the tokenizer directly determines how binding the $d \ll |V|$ constraint is; larger vocabularies make the bottleneck more likely to matter.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the entire argument rests on the rank properties of a matrix product, $H W^\top$, the same primitive operation underlying every layer in the network.
- [[Concept - Neural Text Degeneration and Repetition Loops]] — over-smoothing and structurally disadvantaged tokens are contributing structural factors in the broader family of degenerate-decoding pathologies.
- [[Concept - Embeddings as Learned Representations]] — weight tying between input and output embeddings is exactly the design choice that makes the bottleneck bind hardest, since it removes the extra flexibility an untied output head provides.
- [[Concept - Mode Collapse in RLHF]] — both phenomena manifest as reduced effective diversity of the output distribution, though from different mechanisms: one is an architectural capacity ceiling, the other a training-induced narrowing of an already-expressible distribution.
- [[Reference - Open Problems in LLM Engineering]] — the softmax bottleneck is a rare case of a *provable* capacity limitation in an otherwise empirically-driven field, cataloged there alongside the field's more open, unresolved questions.

## Sources
- Yang, Dai, Salakhutdinov & Cohen (2018) — "Breaking the Softmax Bottleneck: A High-Rank RNN Language Model." Proves the rank-$d$ limitation on softmax output layers and introduces Mixture of Softmaxes as a fix.
- Demeter, Kimmel & Downey (2020) — "Stolen Probability: A Structural Weakness of Neural Language Models." Shows tokens whose embeddings lie in the convex hull of their neighbors can never be the greedy-decode argmax, independent of training.
