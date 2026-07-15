---
tags: [gotchas, domain/esoterica, level/advanced]
aliases: []
summary: "How million-token context windows fail silently: lost-in-the-middle, fake NIAH passes, RoPE drift, dilution, KV-quant, cost cliffs."
---

# Gotchas - Long-Context Failure Modes

A model card that says "1M-token context" is describing what fits in a request, not what the model can actually use, afford, or retrieve reliably at that length. Every gotcha below is a way "the window is big enough" turns out to be the wrong question — the window is a serving spec and an architecture claim, not a promise about effective capability. Ordered roughly by how much production pain each one causes.

## 1. Lost-in-the-middle: buried facts get ignored

**Symptom:** A fact or instruction placed near the middle of a long prompt is missed or misapplied far more often than the identical content placed at the very start or very end — even well inside the model's stated context window.

**Cause:** Liu et al. 2023 ("Lost in the Middle: How Language Models Use Long Contexts") measured multi-document QA and key-value retrieval accuracy as a function of where the relevant fact sits and found a U-shaped curve: primacy and recency dominate, and mid-context accuracy can fall to or below a closed-book (no-context) baseline. This shows up across differently trained model families, which points to something structural about how causal attention allocates effective weight across position — see [[Concept - Context Rot]] for the softmax-dilution account of the same curve.

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

**Fix:** Restate the load-bearing instruction or fact twice — once near the top of the prompt, once immediately before the query — instead of relying on "it's in there somewhere" placement for anything decision-critical.

**Detection:** Run a positional-sweep eval: fix the total context length, vary only the depth at which the target fact sits, and plot accuracy against depth. A flat line is healthy; a dip in the middle band is the signature.

## 2. Needle-in-a-haystack passing does not mean the model can use the window

**Symptom:** A model scores 99%+ on a public needle-in-a-haystack (NIAH) benchmark, gets shipped on the strength of that number for a long-context RAG feature, and production complaints roll in about missed cross-document facts and wrong aggregations.

**Cause:** NIAH tests the easiest possible long-context task — verbatim retrieval of one lexically distinct sentence buried in filler. It says nothing about multi-hop reasoning, aggregating scattered evidence across many chunks, or reconciling conflicting numbers, all of which degrade with length far faster than single-fact retrieval. RULER (Hsieh et al. 2024) and multi-needle variants expose the gap directly: the same checkpoint that aces single-needle NIAH at a given length can score dramatically lower on multi-needle or aggregation variants at the identical length.

**Fix:** Build or borrow an eval that matches the real task shape — multi-hop QA, counting, cross-reference — and treat any NIAH score as necessary, not sufficient.

**Detection:** Run RULER or an equivalent multi-needle suite at the target length before trusting a vendor's advertised "effective context length."

## 3. RoPE positions past the trained range are out-of-distribution

**Symptom:** A model "extended" to a longer context via a naive scale factor shows fine aggregate perplexity up to the new limit, but silently fails mid-context recall — and its short-context quality has quietly regressed too.

**Cause:** [[Concept - Rotary Position Embeddings (RoPE)]] rotates each query/key pair by an angle proportional to position; at positions beyond the trained range those rotation angles are unseen by every learned attention pattern, which is exactly the failure [[Concept - RoPE Extrapolation and Context Extension]] exists to route around. A poorly chosen scale factor compresses or distorts the angles for *in-range* positions too — the mechanism meant to fix long positions can blunt the short ones it was supposed to leave alone.

**Fix:** Never trust a single "does it run at 128K" smoke test. Evaluate the specific extension method (see [[Decision - Choosing a Context Extension Method]]) at both the target length and the original trained length before shipping.

**Detection:** A perplexity curve flat to the extension boundary then cliffing sharply past it is the classic signature; pair it with a positional-sweep NIAH to catch mid-context-specific recall collapse that aggregate perplexity hides entirely.

## 4. Attention dilution: more tokens means less signal per token, even when nothing else changes

**Symptom:** Retrieval signal-to-noise degrades smoothly as total context grows, independent of where the target fact sits — more filler in the prompt makes the model slightly worse at using any single relevant token.

**Cause:** Softmax normalizes attention weights to sum to 1 across every visible key. As the key count climbs into the hundreds of thousands, genuine signal for any one relevant token competes for probability mass against orders of magnitude more distractors — and against the fixed [[Concept - Attention Sinks|attention-sink]] mass that heads dump onto early tokens regardless of content (empirically 30-80% of a sink head's weight, per Xiao et al. 2023). The mechanism is "correct" — attention is doing exactly what softmax computes — but effective retrieval SNR falls with length purely from having more competitors for the same normalized budget.

**Fix:** Prefer retrieval and reranking to cut context down to the highest-signal chunks over stuffing everything into one enormous prompt "to be safe" — see the distractor-degradation finding in [[Concept - Context Rot]].

**Detection:** Hold the target fact's position fixed and sweep total context length upward with added filler; a monotonic accuracy decline at a fixed position isolates dilution from the position effect in gotcha #1.

## 5. KV-cache quantization craters long-context recall specifically

**Symptom:** A quantized deployment (INT4/FP8 KV cache) looks fine on short-prompt evals, but long-context task accuracy is measurably worse than the unquantized model at the same length — and perplexity alone doesn't show it.

**Cause:** [[Concept - Massive Activations and Outlier Features|Outlier channels]] and sink-token activations carry dynamic range that a naive per-tensor quantization scale can't represent alongside the bulk of "normal" activations. The quantization error per cached token is small, but it compounds across the tens or hundreds of thousands of positions a long-context query actually attends over — an error invisible at 2K tokens becomes the dominant noise source at 200K.

**Fix:** Use a [[Concept - Post-Training Quantization Formats|quantization scheme]] that protects outlier channels and sink positions specifically (mixed precision for those columns, or leave them unquantized) rather than a uniform per-tensor scale.

**Detection:** Compare long-context *task* accuracy (not just perplexity) between fp16 and quantized KV cache at the target length; perplexity can look nearly identical while accuracy on buried facts diverges sharply.

## 6. The cost/latency cliff nobody budgeted for

**Symptom:** A feature spec'd against "the model supports 1M tokens" turns out to be unaffordable or too slow to ship the moment someone actually tries to fill the window.

**Cause:** Prefill compute scales roughly quadratically with sequence length before any sparsity is applied, while [[Concept - KV Cache|KV-cache]] memory scales linearly: $\text{bytes} = 2 \times n_\text{layers} \times n_\text{kv\_heads} \times d_\text{head} \times \text{seq\_len} \times \text{bytes\_per\_elem}$. For Llama-3-70B (80 layers, 8 KV heads via GQA, head_dim 128, fp16) that's 327,680 bytes/token (~0.31 MB); a single 1M-token sequence costs roughly 328 GB of KV cache alone, before the activations needed to produce it. "Supports 1M tokens" is a serving-memory and architecture spec, not a promise you can afford to fill it for one request, let alone concurrently for many.

**Fix:** Budget prefill latency and KV memory at the target length as part of the design, not after the fact. Use [[Concept - Ring Attention and Extreme Context|ring/context-parallel attention]] to spread the memory across devices if the target genuinely requires it, and weigh whether retrieval-augmented shorter context beats brute-force long context for the actual task.

**Detection:** Measure prefill time-to-first-token and peak KV memory at the target length on real serving hardware before the number goes into a spec document — "it loaded a 1M-token prompt in a demo" is not a capacity plan.

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
