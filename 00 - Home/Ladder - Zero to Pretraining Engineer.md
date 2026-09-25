---
tags: [ladder, domain/home, level/surface]
aliases: [Zero to Pretraining Engineer, pretraining engineer roadmap, LLM pretraining learning path, how to plan a pretraining run]
summary: "Ordered surface-to-unicorn walk through pretraining: math, training mechanics, the Transformer, scale, data, the cluster, and war stories."
---

# Ladder - Zero to Pretraining Engineer

A guided walk through the Engineering Wing for one question: *what do you need to know to plan, launch and babysit a large pretraining run?* Thirty-five steps in story order. The numerical and optimization substrate comes first, then the Transformer, then the systems and data engineering that scale it past one GPU, then the stability tricks and frontier techniques that keep a nine-figure run from diverging. It closes on the unicorn tier: the incidents every pretraining team eventually lives through. Read each note for the one mechanism or number named under it. If you can answer the self-test without re-reading, move on; if you can't, that's the note to sit with. Memorize the recurring numbers instead of looking them up mid-run: 6ND, 16-20 bytes/param, ~20 tokens/param and 40-55% MFU are the arithmetic a real pretraining plan is built from. The ladder draws on domains 01, 02, 03, 04, 05 and 08, plus one closing entry from 19. For the full 25-domain map, including the Applied Wing where these models eventually land and earn out, start at [[Home]].

---

## Act I — The Substrate (numerical and mathematical foundations)

**1. [[Concept - Entropy and Cross-Entropy]]**
This identity is what makes "the loss went from 2.11 to 2.07" mean something physical: cross-entropy = entropy + KL divergence. Training on cross-entropy loss literally minimizes the model's distance from the true data distribution, and the gradient of softmax-plus-cross-entropy is the clean $\text{softmax}(z) - \text{onehot}$ every framework relies on. Perplexity is the exponential of that loss, the model's effective branching factor. Chinchilla's fitted irreducible term, $E \approx 1.69$ nats/token, is the empirical floor loss curves flatten toward. The trap: perplexity is per token, so comparing it across two tokenizers is meaningless unless you renormalize to bits-per-byte first.
*Self-test:* A model's perplexity looks worse after you swap in a bigger-vocabulary tokenizer, even though its downstream benchmarks improved. What's going on?

**2. [[Concept - Floating Point for Deep Learning]]**
One tradeoff explains the modern precision stack. Exponent bits buy dynamic range, mantissa bits buy relative precision, and deep-learning gradients span ten orders of magnitude but tolerate rounding noise, so they want range over precision. bf16 therefore kept fp32's full 8-bit exponent (the same ~$10^{38}$ range) and cut the mantissa to 7 bits. fp16 has 10 mantissa bits but a 5-bit exponent (max value 65504), and that's why it needed a whole loss-scaling apparatus to survive training at all. Matmul accumulation error grows like $\sqrt{k}\,\varepsilon$, so tensor cores always accumulate dot products in fp32 whatever precision the inputs are stored in.
*Self-test:* Why does bf16 never need loss scaling the way fp16 does, even though bf16 has fewer mantissa bits?

**3. [[Concept - Matrix Multiplication as the Atom of Deep Learning]]**
Every compute budget in the field rests on this FLOP-counting rule. A dense layer costs $2mnk$ FLOPs, and backprop runs two GEMMs for every forward GEMM, so a transformer costs **~6 FLOPs per parameter per token** (2 forward, 4 backward). That gives the $C \approx 6ND$ identity under scaling laws. The second number: arithmetic intensity (FLOPs per byte moved) decides whether an operation is compute-bound or memory-bound. A batch-1 decode matmul runs at roughly **0.3% of peak FLOPs** on an H100 because of its shape. Same hardware, 300x apart, on shape alone.
*Self-test:* Why does cutting the FLOP count of a memory-bound matmul, like an LLM decode step, save nothing in wall-clock time?

---

## Act II — How a Network Learns (training mechanics)

**4. [[Concept - Backpropagation]]**
Deep learning is affordable because of a very favorable exchange rate. One backward pass differentiates a single scalar loss with respect to billions of parameters at a cost independent of parameter count, roughly 2x the forward pass, always. The hidden cost is memory, not FLOPs. Every forward activation has to stay alive until its gradient is consumed. Activation (gradient) checkpointing stores every $\sqrt{L}$-th layer and recomputes the rest, trading ~33% more compute for memory that drops from $O(L)$ to $O(\sqrt{L})$. FlashAttention later applies the same recompute-over-store logic to the attention matrix.
*Self-test:* Why is backprop's cost independent of how many parameters a model has, and what does that imply is the real limit at scale?

**5. [[Concept - The Training Loop]]**
Most "model" bugs violate this ordering: zero_grad → forward → backward → (unscale) → clip → step → scheduler.step(). Every permutation fails silently, with no error and no crash. The key fact is that backward *accumulates* gradients with `+=` by design. Forget `zero_grad` and the effective gradient norm grows every step until the run stalls or explodes, and that same mechanism is what [[Concept - Gradient Accumulation and Microbatching]] uses on purpose. Effective batch size is $B_\text{micro} \times N_\text{accum} \times W_\text{data-parallel}$. That's the quantity optimization responds to, however it's sharded across GPUs.
*Self-test:* A run's gradient norm grows monotonically every step until the loss explodes. What's the most likely ordering bug, and why does the framework never raise an error for it?

**6. [[Concept - Adam and AdamW]]**
"Adam+L2" and "AdamW" are different optimizers at matched hyperparameters. L2 regularization adds $\lambda\theta$ to the gradient, so under Adam it gets divided by $\sqrt{\hat v}$ and shrinks weights least where gradient history is largest, the opposite of what the regularizer is for. AdamW decouples decay from the adaptive machinery entirely. The memory number to internalize: Adam's fp32 moments cost **8 bytes/param** on top of weights and gradients. That makes optimizer state the largest pool in training memory and the first thing [[Concept - Data Parallelism and ZeRO|ZeRO]] shards. LLM pretraining almost universally uses $\beta_2 = 0.95$ instead of the textbook 0.999. At large batch the gradient estimate is already low-variance, and a shorter second-moment memory adapts to curvature shifts faster.
*Self-test:* Why does lowering AdamW's beta2 from 0.999 to 0.95 make a large training run less prone to loss spikes?

**7. [[Concept - RMSNorm and LayerNorm]]**
RMSNorm displaced LayerNorm almost everywhere by 2026. Dropping mean-centering and the bias term costs nothing in quality and buys a **7-64% op-level speedup** (Zhang & Sennrich 2019), because rescaling to unit RMS turns out to be the half of the operation that matters. The less obvious mechanical point: a norm layer's backward pass orthogonalizes the upstream gradient against the normalized activation direction, filtering out the component that would change magnitude. That's part of why norms fix vanishing and exploding gradients so well. One hard rule: the sum-of-squares reduction must run in **fp32**, never natively in bf16/fp16. Otherwise the variance computation silently corrupts and the run diverges thousands of steps later with no crash to point to.
*Self-test:* RMSNorm drops LayerNorm's mean-subtraction step entirely. What does the paper's own evidence say that step was buying you?

**8. [[Concept - Weight Initialization]]**
Every named init scheme comes from a one-line derivation. Forward signal variance is preserved only if $\text{fan\_in} \cdot \sigma_W^2 = 1$, and because that factor compounds across $L$ layers, a per-layer error of 10% is the difference between $0.9^{100} \approx 2.7\times10^{-5}$ (dead network) and $1.1^{100} \approx 1.4\times10^4$ (blown up). Transformers add a second, additive problem. Each of $N$ layers writes twice into the residual stream, so GPT-2's $1/\sqrt{2N}$ scaling on the residual-projection init exists only to stop that stream's variance from growing linearly with depth. Every modern LLM config still carries it, even though every block is now drenched in RMSNorm.
*Self-test:* Normalization can absorb a 2-3x initialization error in the forward pass. So why does the $1/\sqrt{2N}$ residual-projection scaling survive in every modern LLM config?

**9. [[Concept - Vanishing and Exploding Gradients]]**
The mechanism is multiplicative. Backprop's gradient at layer 0 is a product of per-layer Jacobians, so a per-layer spectral norm of just 0.9 or 1.1 compounds to $2.7\times10^{-5}$ or $1.4\times10^4$ by depth 100. No single layer is wrong; the pathology comes from the product. Residual connections are the strongest fix because they turn each factor into $I + F'$, an additive identity term the product can't kill. The transformer-specific point: exploding gradients usually enter through **attention logits**, not the FFN stack classical theory worries about. So the fixes that work are logit-level (QK-norm, z-loss), not another init tweak.
*Self-test:* A 30-layer transformer NaNs at step 8,000, right at the end of warmup. Classical theory says check the init constants. Where should you look first, and why?

---

## Act III — The Architecture

**10. [[Deep Dive - The Transformer]]**
The skeleton every frontier LLM shares: a stack of identical pre-norm residual blocks, each reading from and writing additively to a shared `d_model`-wide **residual stream**. Attention and the FFN are read/write operations on a bus, not sequential transformations. The parameter-count approximation $N_{\text{params}} \approx 12 \cdot n_{\text{layers}} \cdot d_{\text{model}}^2$ falls straight out of `d_ff = 4*d_model` and four attention projections. It matched GPT-3's 175B closely, but it's 30-90% off for any GQA or MoE model. The efficiency property that let transformers beat RNNs: causal masking computes the whole sequence's next-token loss in **one parallel forward pass**, with no sequential dependency during training.
*Self-test:* The `12*n_layers*d_model^2` formula matches GPT-3 almost perfectly. Why does it fail badly the moment you apply it to a GQA or MoE model?

**11. [[Concept - Feed-Forward Networks and GLU Variants]]**
For budgeting: the FFN sublayer holds roughly **two-thirds** of a transformer block's parameters and FLOPs, which is why [[Concept - Mixture of Experts Architecture]] sparsifies the FFN and never the attention sublayer. SwiGLU and its GLU-family relatives add a third weight matrix, an elementwise gate, and consistently beat plain GELU/ReLU FFNs at matched compute. To keep parameter count comparable to a vanilla 4x FFN, LLaMA shrinks $d_{ff}$ to roughly $\tfrac{8}{3} d_{model}$. Remember the honest caveat: Shazeer's own 2020 paper offers **no theoretical explanation** for why SwiGLU wins. A one-page empirical ablation became the default in nearly every open-weight model since.
*Self-test:* You're porting inference code for a LLaMA-family checkpoint and hardcode the vanilla `d_ff = 4*d_model` convention. What kind of failure do you get, loud or silent?

**12. [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]]**
This one placement choice decides whether a deep transformer trains at all. Post-norm (`Norm(x + Sublayer(x))`) renormalizes every layer's output but forces gradients back through every intervening norm, and it goes unstable past roughly 20-30 layers without careful warmup. Pre-norm (`x + Sublayer(Norm(x))`) gives gradients a clean, unnormalized highway to early layers, but the residual stream's variance grows without bound as depth increases, causing late-layer **representation collapse** (Liu et al. 2020). DeepNorm upscales the residual by $\alpha > 1$ and downscales sublayer init by $\beta < 1$, and it trained a 1000-layer transformer where neither vanilla version could. The field hasn't fully converged. Gemma 2's 2024 return to sandwich norm plus QK-norm is a scale-tested admission that calling pure pre-norm "case closed" was premature.
*Self-test:* Pre-norm transformers train more stably than post-norm ones at depth. So why did Gemma 2 partly move back toward post-norm-style sandwich normalization in 2024?

---

## Act IV — Scale (why one GPU isn't enough, and what replaces it)

**13. [[Concept - Why Models Don't Fit on One GPU]]**
The sizing mistake that catches every junior engineer. Training memory has four pools: parameters (2 bytes bf16), gradients (2-4 bytes), Adam optimizer state (12 bytes fp32) and activations. The first three sum to roughly **16-20 bytes per parameter** before a single activation is stored, so a 7B model needs 112-140GB, already past an 80GB H100 with zero activations counted. The practical single-GPU ceiling without sharding is roughly **3-6B dense parameters**. Past that you shard state (ZeRO/FSDP) or the model itself (tensor/pipeline parallelism). No clever kernel makes 70B+ dense pretraining fit on one device.
*Self-test:* A 7B model's bf16 weights are only 14GB. Why does the training job need well over 100GB before storing a single activation?

**14. [[Concept - Scaling Laws]]**
The correction that reset the field. Kaplan et al. (2020) said to scale parameters faster than data. Hoffmann et al.'s Chinchilla (2022) re-ran the fit with IsoFLOP profiles and found the earlier conclusion was a methodology artifact (an under-tuned LR schedule). The corrected compute-optimal ratio is **roughly 20 tokens per parameter**, and a 4x-smaller Chinchilla beat 4x-larger Gopher at equal compute. The frontier has since moved past pure compute-optimality to deliberate **inference-optimal overtraining**. Llama-3 8B trained on ~15T tokens, roughly 1875 tokens/parameter, nearly 100x past Chinchilla-optimal, because serving cost tracks parameter count and not training tokens.
*Self-test:* Two models have identical pretraining loss. What does this note say you still can't conclude about how they'll compare on any single downstream benchmark?

**15. [[Concept - Data Parallelism and ZeRO]]**
ZeRO starts from this observation. Plain data parallelism replicates the full model on every rank, which buys throughput but no extra capacity. A 70B model that doesn't fit on one GPU still doesn't fit under DDP however many GPUs you add, because every rank pays the full 16-bytes/param bill regardless of world size. ZeRO shards that redundant state in three stages: optimizer states (ZeRO-1), plus gradients (ZeRO-2), plus parameters (ZeRO-3, which all-gathers each layer just in time and costs ~1.5x DDP's communication volume). A 70B model's 1.12TB Adam footprint shards to **~18GB/GPU** across 64 ranks under ZeRO-3. The trap is reaching for ZeRO-3 reflexively at the first OOM, when ZeRO-1 often already fits the model at a fraction of the communication cost.
*Self-test:* A team hits an OOM and jumps straight to ZeRO-3, and throughput drops. What's the most likely diagnostic mistake?

**16. [[Concept - Tensor and Pipeline Parallelism]]**
There are two orthogonal ways to split a model too big for state-sharding alone. Tensor parallelism cuts individual matmuls across GPUs. Megatron's column-parallel-then-row-parallel split needs **4 all-reduces per transformer layer**, so it has to stay inside a single NVLink domain; it can't tolerate inter-node bandwidth at that frequency. Pipeline parallelism puts different *layers* on different GPUs and pays an idle **bubble** of $(p-1)/(m+p-1)$. At $p=8$ stages and only $m=8$ microbatches that's a 47% idle fraction, hence the rule of thumb $m \geq 4p$. Production layouts commonly run **TP=8** (one full node) composed with **PP=8-16** across nodes, with DP/ZeRO as the outermost dimension.
*Self-test:* Why must tensor parallelism stay inside a single node's NVLink domain, while pipeline parallelism can safely cross nodes?

**17. [[Concept - Mixed Precision Training]]**
Master weights keep bf16 training correct. bf16 never overflows the way fp16 does, but a relative update smaller than about **0.8%** of a weight's magnitude rounds to zero if applied directly in bf16. Late in training, with a decayed LR, per-step updates routinely fall below that threshold. So the optimizer keeps an **fp32 master copy** and only rounds to bf16 for the next forward pass. A short fixed list stays in fp32 whatever the model dtype: the loss, softmax, norm statistics and the gradient all-reduce. The asymmetry is dangerous. fp16 failure announces itself (a shrinking loss-scale factor, skipped steps). bf16 divergence looks like a run that's fine for 40,000 steps and then starts producing slightly-too-high loss, with no single event to root-cause.
*Self-test:* A bf16 run has gone 40,000 steps and looks healthy, but the loss curve now sits a hair above an fp32 reference run. What class of bug should you suspect before touching hyperparameters?

**18. [[Concept - Learning Rate Schedules for Pretraining]]**
Warmup exists for a mechanical reason. Adam's second-moment estimate $\hat v$ starts at zero and stays uncalibrated for the first thousands of steps, so jumping straight to peak LR can spike a run before curvature is characterized. Cosine decay anneals to ~10% of peak over the *entire planned token budget*. That means $T$ has to be fixed in advance, and stopping early leaves you at an artificially high LR with no way to recover the lost decay. **Warmup-stable-decay (WSD)** avoids that commitment with a long constant-LR plateau you can branch a checkpoint from at any point. Its advantage is optionality; the final loss isn't better.
*Self-test:* A cosine-scheduled run gets cut short at 70% of its planned token budget. Why is the checkpoint's loss artificially inflated relative to what more training would have bought, in a way a WSD checkpoint's wouldn't be?

**19. [[Concept - Tokenizer Training]]**
This decision is frozen for the model's whole life the moment pretraining starts. Nearly every frontier model trains its tokenizer with greedy [[Concept - Byte-Pair Encoding]], repeatedly merging the most frequent adjacent symbol pair. That's frequency-greedy, not likelihood-optimal, unlike SentencePiece's EM-pruned unigram-LM alternative. Vocabulary size is a real tradeoff. Common operating points run from 32k (Llama-2) to 256k (Gemma), and a tokenizer trained mostly on English imposes a **2-4x token tax** (fertility) on other languages because the merge statistics never saw them in proportion. It can't be undone. The embedding matrix's row count is fixed, so there's no "add more vocabulary later," and a tokenizer bug caught after a multi-million-dollar run has started means living with it or restarting.
*Self-test:* Why can't you add 10,000 new vocabulary entries to a model's tokenizer partway through pretraining the way you could add more training data?

**20. [[Deep Dive - Anatomy of a Pretraining Run]]**
The wiring diagram for the whole domain. A compute budget $C$ solves $6ND = C$ for parameter count and token count, which fixes the parallelism layout needed to hit the field's target **40-55% MFU** band. Llama-3 405B's reported 54-day/16k-H100 run backs out to roughly **49% MFU**, a handy sanity check that a claimed run is physically plausible. More important than the ML recipe: at 10,000+ GPU scale, **hardware failure is the steady state, not a contingency**. Elastic restart from checkpoint is part of the normal operating loop, and most engineering hours go to checkpoint cadence, straggler detection and data-pipeline resumability, not architecture or hyperparameters.
*Self-test:* A lab reports a headline MFU number for its pretraining run. What does the denominator typically NOT include, and why does that make true "useful compute per wall-clock hour" look better than it is?

---

## Act V — Data (the pipeline that feeds the run)

**21. [[Deep Dive - The Pretraining Data Pipeline]]**
The pipeline's order is its cost strategy. Language ID runs first, since filters are language-specific. **Deduplication runs before quality scoring**, because scoring is the expensive stage and a 30-50%-duplicate raw pool means paying classifier cost on the same page ten times over. Decontamination runs last, against a benchmark list that keeps growing. End-to-end survival (final tokens over raw input tokens) typically lands at **1-15%**; FineWeb kept 15T final tokens out of 96 processed Common Crawl dumps. The competitive point: the transformer architecture and training loop are public and reproducible from papers. Exact filter thresholds, dedup granularity and mixture weights are what frontier labs say least about, because that part isn't public.
*Self-test:* Two labs start from the same raw Common Crawl dumps and end up with measurably different models. According to this note, where was that difference most likely made?

**22. [[Concept - Deduplication at Scale]]**
MinHash-LSH turns an $O(n^2)$ similarity problem into fixed-size fingerprint comparisons. Shingle each document and keep the minimum hash under $k$ permutations as a signature (the fraction of matching coordinates estimates Jaccard similarity). Then band the signature so candidate pairs emerge above a similarity threshold set by $(b,r)$. The number: SlimPajama's dedup of RedPajama cut **1.2T tokens down to 627B, 49.6% removed**, so half a raw web corpus is duplicate content by volume. The sharpest finding came from FineWeb: **global cross-dump dedup can make a corpus worse**. High-quality content gets re-syndicated and mirrored more, not less, so the fix was to dedup within each dump instead of across all of them.
*Self-test:* FineWeb found that deduplicating more aggressively across dumps hurt corpus quality. Why doesn't "more duplication removed" mean "better corpus" here?

**23. [[Concept - Data Mixtures]]**
What "the model saw Wikipedia N times" means mechanically: a source's sampling weight combined with its raw size sets its effective-epoch count. A small high-quality domain like Wikipedia gets deliberately upsampled to 2-5x effective epochs, while the much larger, noisier web crawl is downsampled below one pass. The most counterintuitive measured effect: **adding source code to the mix improves non-code reasoning**, a real cross-domain transfer, so labs add code even when they don't want a coding model. Mixture weights also change over training. The final 10-20% typically runs an **annealing/cooldown phase** that shifts toward the highest-quality, code and synthetic data, timed against the LR decay.
*Self-test:* Why does adding source code to a pretraining mixture measurably improve performance on reasoning benchmarks that have nothing to do with code?

**24. [[Concept - Quality Filtering for Pretraining Data]]**
Three paradigms, rising in cost. Cheap heuristic rules (length, symbol-to-word ratio) catch the easy half of the junk almost for free. Perplexity filters score documents against a reference language model. Classifier/LLM-annotator filters go furthest: FineWeb-Edu prompts Llama-3-70B-Instruct to rate educational value, distills that into a cheap linear classifier, and got a measured **5-7 point jump on MMLU and ARC** at matched token count. Survival rate is the health signal. Above ~50% your filters are too weak; well under 0.5% you're throwing away usable text. The canonical failure is [[Lore - The C4 Blocklist Incident]]: a lexical "bad words" blocklist disproportionately deleted LGBTQ+ content and African-American-aligned English while unrelated harmful content survived. Every filter is a value judgment, not a neutral sieve.
*Self-test:* A quality filter's survival rate is 80%. Is that more likely a healthy pipeline or a broken one, and why?

---

## Act VI — The Cluster (the physical machine underneath)

**25. [[Concept - Anatomy of an AI Training Cluster]]**
A bandwidth cliff shapes every distributed training decision. Inside an 8-GPU node, NVSwitch gives every GPU **~900 GB/s** to every other GPU, all-to-all. Leave the node and InfiniBand/RoCE drops that to **~50 GB/s per GPU**. That 10-18x cliff is why tensor parallelism stays pinned inside one node while data/pipeline parallelism goes across the slower fabric. Scale as of 2026: production clusters run to roughly 100,000 GPUs, and power and cooling limit them more than floor space. NVIDIA's rack-scale GB200 systems push **~120kW/rack**, forcing a wholesale move to liquid cooling.
*Self-test:* Why is tensor parallelism confined to a single node's NVLink domain while data parallelism routinely spans the entire cluster?

**26. [[Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)]]**
The three bandwidth tiers in real numbers. NVLink4 gives ~900 GB/s aggregate per GPU inside a node via NVSwitch. PCIe Gen5 tops out around **64 GB/s, 14x slower**, and traffic falls onto it without NVSwitch or during host-staged transfers. InfiniBand NDR or RoCEv2 deliver roughly 50 GB/s per GPU node-to-node. GPUDirect RDMA is what makes either scale-out fabric fast at all, letting the NIC read and write GPU HBM directly instead of bouncing through host memory. Know RoCE's failure mode by name. Without correctly tuned Priority Flow Control and ECN, an incast pattern (common in MoE all-to-all dispatch) triggers a **PFC pause-storm** that cascades backward and can stall an entire rail.
*Self-test:* A single-pair NCCL micro-benchmark between two GPUs shows near-peak bandwidth, but the production 512-GPU run is badly communication-bound. Why doesn't the micro-benchmark catch this?

**27. [[Concept - All-Reduce and Collective Operations]]**
Every distributed step pays $T \approx \alpha \cdot \text{steps} + \text{bytes}/\text{bandwidth}$. Ring all-reduce is bandwidth-optimal: it moves roughly $2\times$ the data **independent of GPU count $N$**. Its $2(N-1)$-step latency term is easy to write off at scale, and that's a mistake. At 8 GPUs those 14 steps are noise; at 512 GPUs the 1022 steps can dwarf the bandwidth term, so production frameworks switch to tree or hierarchical collectives past a certain size. Hierarchical collectives use the two-tier interconnect directly: reduce inside the fast NVLink domain first, then run one slow cross-node collective between node representatives. All-to-all, the collective behind MoE expert dispatch, is the one practitioners fear most, because its cost is sensitive to load imbalance across experts.
*Self-test:* Ring all-reduce is "bandwidth-optimal, independent of N." In what sense does its cost still grow as you add GPUs to the ring?

**28. [[Concept - Model FLOPs Utilization (MFU)]]**
Infrastructure teams treat MFU as a KPI worth dedicated headcount. Two teams with identical clusters training the same model can differ 2x in wall-clock time on engineering quality alone, because $\text{MFU} = \text{achieved model FLOP/s} / \text{peak hardware FLOP/s}$ converts directly into cost. Going from 40% to 55% MFU cuts training cost by roughly **27% with zero change to the model**. PaLM's **46.2% MFU** on TPU v4 pods is the reference benchmark; well-tuned H100 runs reach 50-60%. Watch the denominator. MFU and HFU differ in whether activation-recomputation FLOPs count as "useful," and vendor peak-FLOPs numbers are sometimes quoted at sparsity-inflated or boost-clock rates.
*Self-test:* Two labs both report "MFU of 50%" for similar runs. Name one reason the two numbers might not be comparable.

---

## Act VII — Stability and the Frontier (keeping a nine-figure run alive)

**29. [[Concept - Training Stability and Loss Spikes]]**
A spike follows a chain. Attention logits grow, softmax saturates toward near-one-hot, and its gradient becomes a delta function that backprops into a large correlated update. Adam's second-moment estimate $\hat v$ lags a sudden jump in gradient magnitude by design, so it briefly under-normalizes that update instead of damping it. Each named stabilizer attacks one link. QK-norm caps attention-logit growth directly, z-loss keeps the output softmax normalizer from drifting, and beta2=0.95 shortens how long $\hat v$ stays stale. PaLM's sharpest finding: rewinding to before a spike and **replaying the identical data did not reproduce it**. The spike comes from an interaction between optimizer state and data *ordering*; the data alone doesn't cause it.
*Self-test:* PaLM's team found that replaying the same data after a rewind did NOT reproduce a loss spike, but skipping the batches around it and continuing did. What does that rule out as the cause?

**30. [[Concept - muP and Hyperparameter Transfer]]**
The problem muP solves is expensive to get wrong. Under standard parametrization the optimal learning rate keeps shrinking as a transformer gets wider. Wide-enough networks drift toward the NTK/lazy-training limit, where only a fixed random feature map effectively learns, so every new model size has traditionally needed its own multi-million-dollar sweep. muP's per-layer-type init and LR multipliers keep every layer in the maximal-feature-learning regime, which makes **muTransfer** possible. Yang et al. swept hyperparameters on a 40M-parameter proxy and transferred them unchanged to a 6.7B target, near-optimally. The trap: a partially correct muP implementation doesn't crash. It trains to a plausible-looking loss curve at a suboptimal transferred LR, indistinguishable from an unlucky large-scale run unless you run the **coordinate check** first.
*Self-test:* A team implements muP's init-variance rules but forgets the matching per-layer LR multipliers. What happens when they train, and how would they catch the bug?

**31. [[Concept - FP8 Training]]**
Before DeepSeek-V3, fp8 pretraining spent years as "theoretically attractive, practically unstable" folklore. fp8's dynamic range is tiny (roughly $2^{-9}$ to 448 for E4M3) next to bf16's ~$10^{\pm38}$, so *scaling*, the per-tensor multiplier that maps real values into that range, becomes the whole problem. The 8-bit format itself was never the issue. DeepSeek-V3's fix was **fine-grained scaling**: a separate scale per 1×128 tile for activations and per 128×128 block for weights. One outlier near an attention or MoE-router logit then blows the scale only for its own small tile instead of degrading the whole tensor. They also promoted fp8 matmul partial sums to fp32 accumulation. The proof point: 671B total parameters, ~2.788M H800 GPU-hours, the first production-scale fp8-pretrained frontier model, at quality close to a bf16 baseline.
*Self-test:* Early fp8 pretraining attempts failed even though the E4M3/E5M2 formats were well-specified. What was the problem, if not the format?

**32. [[Concept - Critical Batch Size]]**
This threshold separates "more GPUs helps" from "more GPUs burns compute." The gradient noise scale $B_\text{noise} \approx \text{tr}(H\Sigma)/g^\top H g$ marks the batch size below which doubling the batch linearly halves the steps to converge, and above which returns diminish sharply. $B_\text{noise}$ **grows as the loss falls**, so frontier labs treat batch size as a schedule, not a constant. GPT-3 ramped from 32k to **3.2M tokens** over training, tracking the rising threshold instead of picking one compromise value. The organizational trap: a large cluster reserved regardless of model size creates pressure to run above critical batch just to keep every GPU busy. The run shows excellent MFU and converges no faster in wall-clock terms than a smaller batch would have.
*Self-test:* A run shows near-peak MFU and every GPU looks fully utilized. What additional evidence would tell you the batch size is wasting compute above the critical batch?

---

## The unicorn tier — the war stories

**33. [[Lore - The Loss Spike Chronicles]]**
This note dramatizes the mechanism note, with one framing the other lacks: every stabilizer in a modern pretraining recipe (QK-norm, z-loss, beta2=0.95, bf16 over fp16) is **scar tissue** from one of four publicly documented 2022 runs. OPT-175B fought fp16 loss-scale collapse with pure manual triage: rewind, lower LR, resume. PaLM documented ~20 spikes and found that replaying identical data after a rewind did not reproduce one, but skipping the surrounding batches did. GLM-130B traced spikes to embedding-gradient growth. BLOOM switched to bf16 to dodge the crisis OPT had just lived through. A fifth actor hides in all of these logs: a single-rank NaN that looks like an optimization spike is often [[Lore - Silent Data Corruption at Scale|silent data corruption]] on one GPU. That's the first fork in any real triage session.
*Self-test:* PaLM's team couldn't get a loss spike to recur by replaying the same data. What does that rule in as the real cause, mechanically, in terms of Adam's internal state?

**34. [[Lore - Silent Data Corruption at Scale]]**
This failure fires no alarm at all. "Mercurial cores" silently compute wrong answers on specific operand patterns, with no crash, no ECC event and no exception. Meta (Dixit et al. 2021) and Google (Hochschild et al. 2021) found them independently at a rate of **a few bad cores per several thousand machines**. For a pretraining run this is concrete. It shows up as a loss spike that reproduces on one specific rank and vanishes when the job moves to other hardware. Or worse, as gradient corruption that never trips a NaN check and poisons a checkpoint you keep training from. Detecting it means dropping the assumption that hardware is a trustworthy oracle: deterministic replay on a second GPU, per-rank grad-norm outlier monitoring, and checksums around collectives. The fuller [[Gotchas - Hardware Failures at Scale|hardware-failure taxonomy]] ranks SDC as its most dangerous entry because nothing fires.
*Self-test:* A loss spike disappears when you move the job to different hardware, with data and code unchanged. What does that tell you about the cause?

**35. [[Lore - The OPT-175B Logbook]]**
The closing case study. In May 2022 Meta published OPT-175B's weights and also its `chronicles` logbook: the daily, unsanitized record of training a 175B model on 992 A100s over two months. It includes dozens of checkpoint rollbacks, most triggered by **hardware** and not the model (dead GPUs, uncorrectable ECC errors, NCCL hangs), plus a running fight against fp16 loss-scale collapse. The main engineering lesson fits in a formula: work lost per failure equals steps since the last checkpoint, which makes **checkpoint cadence the cost dial** for the whole operation. The second-order lesson is transparency as infrastructure. Publishing the logbook turned private tribal knowledge into a shared baseline, and BLOOM formalized the same firefighting two months later, switching to bf16 to escape the fp16 crisis OPT had just lived through.
*Self-test:* Susan Zhang's team restarted OPT-175B's training dozens of times. What fraction of the causes were about the model or optimizer, versus something else entirely, and what does that imply about where pretraining engineering effort should go?

---

**Where next:** this ladder takes the essential path through a much larger domain. [[MOC - Training at Scale]] holds the rest of the scale-and-stability picture; [[MOC - Data Engineering]] holds the rest of the data side. Give both a full pass once every self-test above lands clean.
