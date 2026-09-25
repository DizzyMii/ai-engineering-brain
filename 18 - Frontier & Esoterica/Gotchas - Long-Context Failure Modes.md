---
tags: [gotchas, domain/esoterica, level/advanced]
aliases: []
summary: "How million-token context windows fail silently: lost-in-the-middle, fake NIAH passes, RoPE drift, dilution, KV-quant, cost cliffs."
---

# Gotchas - Long-Context Failure Modes

A model card that says "1M-token context" tells you what fits in a request. It doesn't tell you what the model can use, what you can afford, or what it retrieves reliably at that length. Each gotcha below is a case where "the window is big enough" was the wrong question: the window is a serving spec and an architecture claim, and it promises nothing about effective capability. Ordered roughly by how much production pain each causes.

## 1. Lost-in-the-middle: buried facts get ignored

**Symptom:** A fact or instruction near the middle of a long prompt is missed or misapplied far more often than the same content at the very start or end, even well inside the stated context window.

**Cause:** Liu et al. 2023 ("Lost in the Middle: How Language Models Use Long Contexts") measured multi-document QA and key-value retrieval accuracy against where the relevant fact sits and got a U-shaped curve. Primacy and recency dominate, and mid-context accuracy can drop to or below a closed-book (no-context) baseline. It appears across differently trained model families, which points to how causal attention spreads effective weight over positions. [[Concept - Context Rot]] gives the softmax-dilution account of the same curve.

```
accuracy
100% |*                                           *
     | *                                         *
     |   *                                      *
  50% |      *                              *
     |          *                       *
     |              * * * * * * * *
   0% +---------------------------------------------> depth of fact in context
      0%           25%           50%           75%          100%
```

**Fix:** For anything decision-critical, state the key instruction or fact twice: once near the top of the prompt and once right before the query. Don't count on "it's in there somewhere."

**Detection:** Run a positional sweep. Fix total context length, vary only the depth of the target fact, and plot accuracy against depth. Flat is healthy; a dip in the middle band is the signature.

## 2. Passing needle-in-a-haystack doesn't mean the model can use the window

**Symptom:** A model scores 99%+ on a public needle-in-a-haystack (NIAH) benchmark, ships on that number for a long-context RAG feature, and production complaints arrive about missed cross-document facts and wrong aggregations.

**Cause:** NIAH is the easiest long-context task there is: verbatim retrieval of one lexically distinct sentence buried in filler. It says nothing about multi-hop reasoning, aggregating evidence scattered over many chunks, or reconciling conflicting numbers, and all of those degrade with length much faster than single-fact retrieval. RULER (Hsieh et al. 2024) and multi-needle variants show the gap directly. A checkpoint that aces single-needle NIAH at some length can score dramatically lower on multi-needle or aggregation variants at that same length.

**Fix:** Build or borrow an eval shaped like the real task (multi-hop QA, counting, cross-reference). Treat any NIAH score as necessary, not sufficient.

**Detection:** Run RULER or an equivalent multi-needle suite at the target length before trusting a vendor's advertised "effective context length."

## 3. RoPE positions past the trained range are out-of-distribution

**Symptom:** A model "extended" with a naive scale factor shows fine aggregate perplexity up to the new limit but silently fails mid-context recall, and its short-context quality has quietly regressed as well.

**Cause:** [[Concept - Rotary Position Embeddings (RoPE)]] rotates each query/key pair by an angle proportional to position. Past the trained range, no learned attention pattern has ever seen those angles; [[Concept - RoPE Extrapolation and Context Extension]] covers the workarounds. A badly chosen scale factor also compresses or distorts the angles for *in-range* positions, so the fix for long positions can blunt the short ones it should have left alone.

**Fix:** A single "does it run at 128K" smoke test proves nothing. Evaluate the specific extension method (see [[Decision - Choosing a Context Extension Method]]) at both the target length and the original trained length before shipping.

**Detection:** The classic signature is perplexity flat to the extension boundary and then cliffing past it. Pair it with a positional-sweep NIAH to catch mid-context recall collapse, which aggregate perplexity hides completely.

## 4. Attention dilution: more tokens, less signal per token

**Symptom:** Retrieval signal-to-noise degrades smoothly as total context grows, wherever the target fact sits. More filler makes the model slightly worse at using any single relevant token.

**Cause:** Softmax normalizes attention weights to sum to 1 over every visible key. With hundreds of thousands of keys, the signal for one relevant token competes for probability mass with orders of magnitude more distractors, and with the fixed [[Concept - Attention Sinks|attention-sink]] mass that heads dump on early tokens regardless of content (empirically 30-80% of a sink head's weight, per Xiao et al. 2023). Attention is computing what softmax says it should. Effective retrieval SNR still falls with length, simply because more competitors share the same normalized budget.

**Fix:** Use retrieval and reranking to cut the context down to the highest-signal chunks. Stuffing everything into one enormous prompt "to be safe" makes this worse; see the distractor-degradation finding in [[Concept - Context Rot]].

**Detection:** Hold the target fact's position fixed and sweep total length upward with added filler. A steady accuracy decline at a fixed position separates dilution from the position effect in gotcha #1.

## 5. KV-cache quantization hits long-context recall specifically

**Symptom:** A quantized deployment (INT4/FP8 KV cache) looks fine on short-prompt evals, but long-context task accuracy is measurably below the unquantized model at the same length, and perplexity alone doesn't show it.

**Cause:** [[Concept - Massive Activations and Outlier Features|Outlier channels]] and sink-token activations need dynamic range that a naive per-tensor scale can't cover alongside the bulk of normal activations. Error per cached token is small, but it compounds over the tens or hundreds of thousands of positions a long-context query attends over. Noise that's invisible at 2K tokens becomes the dominant source at 200K.

**Fix:** Use a [[Concept - Post-Training Quantization Formats|quantization scheme]] that protects outlier channels and sink positions (mixed precision for those columns, or leave them unquantized) in place of a uniform per-tensor scale.

**Detection:** Compare long-context *task* accuracy, not only perplexity, between fp16 and quantized KV cache at the target length. Perplexity can look nearly identical while accuracy on buried facts diverges sharply.

## 6. The cost/latency cliff nobody budgeted for

**Symptom:** A feature spec'd against "the model supports 1M tokens" turns out unaffordable or too slow the moment someone tries to fill the window.

**Cause:** Prefill compute grows roughly quadratically with sequence length before any sparsity, and [[Concept - KV Cache|KV-cache]] memory grows linearly: $\text{bytes} = 2 \times n_\text{layers} \times n_\text{kv\_heads} \times d_\text{head} \times \text{seq\_len} \times \text{bytes\_per\_elem}$. For Llama-3-70B (80 layers, 8 KV heads via GQA, head_dim 128, fp16) that's 327,680 bytes/token (~0.31 MB). One 1M-token sequence costs roughly 328 GB of KV cache alone, before the activations needed to produce it. "Supports 1M tokens" is a serving-memory and architecture spec. It doesn't mean you can afford to fill it for one request, let alone many at once.

**Fix:** Budget prefill latency and KV memory at the target length as part of the design, up front. If the target really needs it, use [[Concept - Ring Attention and Extreme Context|ring/context-parallel attention]] to spread memory across devices, and check whether retrieval into a shorter context beats brute-force long context for the actual task.

**Detection:** Measure prefill time-to-first-token and peak KV memory at the target length on real serving hardware before the number goes into a spec. "It loaded a 1M-token prompt in a demo" is not a capacity plan.

## Connections
- [[Concept - RoPE Extrapolation and Context Extension]] — the mechanism behind gotcha #3's out-of-distribution rotation angles, and the family of fixes it surveys.
- [[Concept - Ring Attention and Extreme Context]] — the primitive that makes the memory side of gotcha #6 tractable by spreading KV memory across devices; an up-link to the frontier technique this gotcha catalog assumes exists.
- [[Concept - Context Rot]] — the domain-09 framing (softmax dilution, distractor sensitivity) that gotchas #1 and #4 are architecture-facing instances of.
- [[Concept - KV Cache]] — the data structure whose linear memory growth and quantization sensitivity drive gotchas #5 and #6; a down-link to the serving prerequisite.
- [[Concept - Attention Sinks]] — the fixed attention-mass sink that competes with genuine signal in gotcha #4 and complicates KV quantization in gotcha #5.
- [[Playbook - Extending a Model's Context Window]] — the operational procedure whose dual-regime evaluation step exists specifically to catch these failures before they reach production.
- [[Concept - Post-Training Quantization Formats]] — the general quantization mechanics that gotcha #5's KV-cache-specific failure is a special case of; a down-link to the serving prerequisite.

## Sources
- Liu et al. (2023) — "Lost in the Middle: How Language Models Use Long Contexts." The U-shaped position-accuracy curve behind gotcha #1.
- Hsieh et al. (2024) — "RULER: What's the Real Context Size of Your Long-Context Language Models?" The multi-needle/aggregation benchmark exposing NIAH's insufficiency in gotcha #2.
- Xiao et al. (2023) — "Efficient Streaming Language Models with Attention Sinks." The sink-mass mechanism behind gotchas #4 and #5.
