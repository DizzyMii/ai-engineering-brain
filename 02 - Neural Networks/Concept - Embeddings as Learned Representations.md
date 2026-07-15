---
tags: [concept, domain/neural-networks, level/core]
aliases: [embedding layer, token embeddings, lookup embeddings, distributed representations]
summary: "Embedding layers as learned lookup tables: sparse row gradients, weight tying, init folklore, and the geometry of meaning-as-direction."
---

# Concept - Embeddings as Learned Representations

> **One-paragraph hook:** An embedding layer converts a discrete symbol — a token ID, a category, a user ID — into a dense vector the network can do calculus on. It is nothing more exotic than a learned lookup table, but it is where a language model's entire interface with the discrete world lives: the first thing gradients touch on the way in, and (via weight tying) the last thing logits touch on the way out. Half of the weird pathologies in production LLMs — glitch tokens, undertrained rows, anomalous norms — live in this one matrix.

## The mechanism

An embedding layer is a matrix $E \in \mathbb{R}^{V \times d}$ — vocabulary size $V$ rows, model dimension $d$ columns. A lookup for token $i$ is mathematically a one-hot [[Concept - Matrix Multiplication as the Atom of Deep Learning|matrix multiplication]]:

$$h = \text{onehot}(i)^\top E = E_{i,:}$$

No implementation actually materializes the one-hot; it's an indexed row fetch. But the matmul view tells you exactly what [[Concept - Backpropagation]] does here: the gradient $\partial L / \partial E = \text{onehot}(i)\, \bar h^\top$ is zero everywhere except the rows of tokens that actually appeared in the batch. Embedding gradients are **sparse by construction** — a batch touching 10k unique tokens of a 128k vocabulary leaves ~92% of $E$'s gradient exactly zero.

This sparsity is why embeddings need optimizer care. PyTorch's `nn.Embedding(sparse=True)` emits genuinely sparse gradients, but only `SGD` and `SparseAdam` accept them. With ordinary dense gradients and Adam, there's a subtler effect: rows whose gradient is zero this step *still get updated*, because Adam's momentum $m$ is nonzero for a few steps after a token last appeared, and weight decay shrinks every row every step. Absent tokens drift.

The second structural fact: **weight tying** (Press & Wolf 2017; Inan et al. 2016). The output projection that produces logits is a $d \times V$ matrix — the same shape as $E^\top$. Tying them ($W_{\text{out}} = E^\top$) saves $V \cdot d$ parameters (for GPT-2: $50257 \times 768 \approx 38.6\text{M}$, roughly 31% of the 124M model) and *usually improves perplexity*, because input and output token geometry are forced to agree. GPT-2 ties; many modern large models untie because at 100B+ scale the parameter savings are negligible and untied heads give a bit more flexibility.

Under tying, the LM head becomes literal dot-product retrieval: $\text{logit}_j = h \cdot E_{j,:}$. The model predicts the next token by asking which embedding row points most in the direction of the current hidden state — the same operation an [[Concept - Embedding Models|embedding model]] performs against a document index.

## In practice

- **What gets embedded:** subword tokens from a [[Concept - Byte-Pair Encoding]] vocabulary; positions (either learned absolute vectors or, in modern LLMs, no position embedding matrix at all — [[Concept - Rotary Position Embeddings (RoPE)]] rotates Q/K instead); categorical features in recommender systems, where embedding tables reach billions of rows and dominate model size.
- **Init folklore:** GPT-family models init embeddings $\sim \mathcal{N}(0, 0.02)$. The original Transformer (Vaswani et al. 2017) instead multiplied embeddings by $\sqrt{d}$ on lookup so their magnitude matched the sinusoidal positional encodings being added to them — a detail that survives vestigially in several codebases and silently changes effective learning rate on the embedding if you copy configs across lineages.
- **Geometry:** meaning lives in *directions* of the space, not in individual coordinates. The famous approximate linear structure — $\vec{\text{king}} - \vec{\text{man}} + \vec{\text{woman}} \approx \vec{\text{queen}}$ — was demonstrated for [[Concept - Word2Vec and the Embedding Lineage|word2vec]] (Mikolov et al. 2013) and persists, noisily, in transformer token embeddings. Semantic clusters, morphological offsets, and language subspaces are all measurably there; the fine structure of that geometry is its own rabbit hole ([[Concept - Embedding Space Geometry]]).

## Failure modes

- **Undertrained / glitch token rows.** A token that appears rarely (or never — reserved tokens, junk from tokenizer training data) keeps a near-init row: tiny norm, random direction. At inference, the model has no learned behavior for it, and hidden states near it produce degenerate output. This is the mechanism behind `SolidGoldMagikarp` and friends ([[Lore - Glitch Tokens]]). **Detection:** histogram embedding row norms; undertrained rows cluster far below the bulk. Rows within noise of $0.02\sqrt{d}$-scale init norms are suspects.
- **Embedding norm divergence.** Frequent tokens' rows grow steadily while rare ones don't, so the norm distribution becomes heavy-tailed over training; combined with weight tying this skews the logit scale per token. Watch max/median row-norm ratio.
- **Sparse-gradient optimizer mismatch.** `sparse=True` with a dense-only optimizer throws immediately (loud), but the reverse — dense gradients with aggressive weight decay on the embedding — silently decays rare-token rows toward zero. This is one reason the standard param-group split excludes embeddings from weight decay.

## The non-obvious

Individual embedding *dimensions* are almost never interpretable, and this isn't a bug — the model stores more features than it has dimensions by packing them into non-orthogonal directions ([[Concept - Superposition]]). Probing "dimension 173" tells you nothing; probing directions found by decomposition methods does. The practical corollary: any pipeline that ablates, quantizes, or prunes embeddings coordinate-wise is operating on the wrong basis, and per-channel damage estimates will mislead you.

## Connections

- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the lookup is a degenerate matmul; seeing it that way makes the sparse-gradient structure obvious.
- [[Concept - Backpropagation]] — the sparse row gradient is a direct consequence of how the backward pass composes; prerequisite mechanics.
- [[Concept - Byte-Pair Encoding]] — decides what the rows *are*; tokenizer/embedding co-design is where glitch tokens are born.
- [[Concept - Rotary Position Embeddings (RoPE)]] — the modern answer to position: rotate Q/K rather than add a learned position row.
- [[Concept - Embedding Models]] — dedicated retrieval embedders are this same idea trained contrastively at the sequence level; the LM head under tying is already doing dot-product retrieval.
- [[Concept - Word2Vec and the Embedding Lineage]] — where distributed lexical representations and the linear-analogy result came from.
- [[Concept - Embedding Space Geometry]] — the deeper dive into anisotropy, clustering, and what the space actually looks like.
- [[Concept - Superposition]] — why per-dimension interpretation of $E$ fails: features outnumber dimensions.
- [[Lore - Glitch Tokens]] — the war stories of undertrained rows (SolidGoldMagikarp) and how they were found.

## Sources

- Mikolov et al. (2013) — Efficient Estimation of Word Representations in Vector Space. The word2vec linear-analogy result; established meaning-as-direction.
- Press & Wolf (2017) — Using the Output Embedding to Improve Language Models. Weight tying: fewer params, better perplexity.
- Inan et al. (2016) — Tying Word Vectors and Word Classifiers. The parallel derivation of tying as a loss-framework result.
- Vaswani et al. (2017) — Attention Is All You Need. Source of the $\sqrt{d}$ embedding-scaling convention.
- Rumbelow & Watkins (2023) — SolidGoldMagikarp (LessWrong). The empirical discovery of glitch tokens via embedding-space clustering.
