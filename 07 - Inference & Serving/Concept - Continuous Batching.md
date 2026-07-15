---
tags: [concept, domain/inference-serving, level/core]
aliases: [iteration-level scheduling, in-flight batching, dynamic batching]
summary: "Iteration-level scheduling that re-forms the decode batch every step so short requests never idle a GPU slot waiting on a straggler."
---
# Concept - Continuous Batching
> **One-paragraph hook:** Static, request-level batching runs a fixed group of sequences until the longest one finishes — every short sequence in the batch sits there holding a GPU slot it isn't using. Continuous batching (also called iteration-level scheduling or in-flight batching) re-decides batch membership after every single decode step, evicting finished sequences and admitting queued ones immediately, which is the single change that took LLM serving throughput from "acceptable" to "production-grade."

## The mechanism
[[Concept - The Inference Request Lifecycle]] runs [[Concept - Prefill and Decode Phases]]: prefill is one parallel forward pass over the prompt, decode is a sequential loop, one token per step per sequence. The naive way to batch decode is request-level: pick N sequences, run the decode loop until all N hit EOS or `max_tokens`, then swap in the next N. The problem is output-length variance, which is universal — some sequences finish in 20 tokens, others run to 2000 — so for most of that window the batch is mostly idle sequences padded out to keep tensor shapes rectangular.

Orca (Yu et al., OSDI 2022) fixed this by moving the scheduling unit from "request" to "iteration." After every forward pass, the scheduler:

```
loop each iteration:
  finished = [seq for seq in batch if seq.hit_eos or seq.at_max_tokens]
  evict(finished)                      # free their KV blocks immediately
  free_slots = capacity - len(batch)
  admit(waiting_queue.pop(free_slots)) # pull in new/queued requests now
  run_one_forward_pass(batch)          # one token per active sequence
```

Static batching, timeline for 4 sequences of very different lengths:

```
seq A ████░░░░░░░░░░░░░░░░   (finishes early, then idles)
seq B ████████████░░░░░░░░
seq C ████████████████████   <- batch waits for this straggler
seq D ██░░░░░░░░░░░░░░░░░░
      |---- whole batch blocked on the longest sequence ----|
```

Continuous batching, same workload:

```
seq A ████                    E,F admitted the instant A,D free a slot
seq D ██
seq E   ██████████
seq F     ████████████████
seq B ████████████
seq C ████████████████████
      GPU never idles waiting on a straggler; slots refill every step
```

The reason this works mechanically is the asymmetry already established in [[Concept - Prefill and Decode Phases]]: decode is memory-bandwidth-bound, re-reading the full weight matrix from HBM every step regardless of batch size. Arithmetic intensity scales roughly with batch size $B$ (one MAC per weight per sequence in the batch), so raising the number of active sequences per step is almost free in latency until you approach the compute roof — you're amortizing a fixed HBM read across more useful work. Continuous batching is the scheduler that actually captures that amortization instead of leaving it on the table between static-batch boundaries.

## In practice
Continuous batching requires the ability to add a request's KV to the batch *mid-flight*, at an arbitrary point in time, without a contiguous pre-reserved buffer. That's exactly what [[Concept - PagedAttention]] provides, which is why the two ship together — Orca proved the scheduling idea, and vLLM's PagedAttention gave it a memory manager that could keep up. [[Breakdown - vLLM]] popularized the combination; TensorRT-LLM calls the same idea "in-flight batching"; TGI and SGLang implement equivalent iteration-level schedulers.

Reported gains are large because static batching's waste is large: Orca and the vLLM paper report roughly **2-23x throughput** over request-level static batching, with the low end on workloads with uniform output lengths (little waste to reclaim) and the high end on workloads with high output-length variance (chat, agents) where static batching was bleeding the most idle capacity.

The two knobs every deployment tunes: `max_num_seqs` (how many concurrent sequences the scheduler allows in a batch) and `max_num_batched_tokens` (the token budget per iteration, shared between prefill and decode work). Push `max_num_seqs` too high and you overcommit the KV cache, forcing preemption; too low and you cap achievable throughput below the hardware's actual capacity.

## Failure modes
**Newly admitted requests need a prefill**, and a full prefill forward pass injected into the middle of an otherwise decode-only iteration monopolizes that step's compute, spiking the inter-token latency (TPOT) of every sequence already decoding. This shows up as periodic latency jitter correlated with new-request arrival rate — the exact interference that [[Concept - Chunked Prefill]] and [[Concept - Prefill-Decode Disaggregation]] exist to remove.

**Preemption thrashing:** if `max_num_seqs` is set above what the KV budget can sustain, the scheduler is forced to evict and later recompute sequences mid-generation to free memory. Symptom: throughput craters and TPOT spikes precisely as load rises, which looks like a capacity cliff rather than a graceful degradation — detectable by watching KV utilization and preemption count, not just raw QPS.

**Silent underutilization** is the opposite failure: a conservative `max_num_seqs`/`max_num_batched_tokens` leaves throughput on the table with no error signal at all — the only way to catch it is benchmarking at the knee (see [[Playbook - Tuning an LLM Serving Deployment]]), because nothing about a too-low limit looks broken from the outside.

## The non-obvious
The benefit of continuous batching is bounded by where the decode step crosses from memory-bound to compute-bound on the [[Concept - The Roofline Model]] — past that crossover, adding more concurrent sequences no longer buys throughput, it only degrades everyone's TPOT for zero gain. Practitioners who treat "more batching is always better" learn this the hard way: the right target isn't maximum `max_num_seqs`, it's the concurrency at the knee of the latency-throughput curve, which is a property of the specific GPU, model, and context length, not a universal constant. This is also why raw throughput is the wrong top-line metric to chase — see [[Concept - Latency, Throughput, and Cost in LLM Serving]] on why goodput (throughput *subject to* an SLO) is what capacity planning should actually optimize, and why [[Concept - LLM Load Testing and Capacity Planning]] treats "find the knee" as the core exercise rather than "maximize tokens/sec."

## Connections
- [[Concept - PagedAttention]] — the non-contiguous KV allocator that makes mid-flight admission of new requests physically possible.
- [[Concept - Chunked Prefill]] — solves the exact interference failure mode (big prefill stalling in-flight decodes) that raw continuous batching introduces.
- [[Concept - Prefill and Decode Phases]] — the memory-bound-decode asymmetry that is the mechanistic reason batching amortizes cost at near-zero marginal latency.
- [[Concept - Prefill-Decode Disaggregation]] — the alternative fix for prefill/decode interference: separate the phases onto different hardware instead of interleaving them.
- [[Breakdown - vLLM]] — the system that shipped continuous batching + PagedAttention together and made it the industry default.
- [[Reference - Inference Performance Math]] — the formulas (decode step time, max concurrent tokens) that determine where a given deployment's knee actually sits.
- [[Concept - Latency, Throughput, and Cost in LLM Serving]] — continuous batching is the mechanism; this note is the economics of the tradeoff it creates.
- [[Concept - LLM Load Testing and Capacity Planning]] — the operational discipline of finding the concurrency knee that continuous batching makes possible to exploit.
- [[Concept - The Inference Request Lifecycle]] — the baseline single-request path that continuous batching interleaves across many concurrent requests.
- [[Concept - The Roofline Model]] — explains why raising batch size is nearly free until the decode step crosses from memory-bound to compute-bound.
- [[Playbook - Tuning an LLM Serving Deployment]] — the procedure for finding the concurrency knee (`max_num_seqs`, `max_num_batched_tokens`) in a real deployment.

## Sources
- Yu et al. (2022) — *Orca: A Distributed Serving System for Transformer-Based Generative Models* (OSDI). Introduced iteration-level scheduling, the mechanism this note describes.
- Kwon et al. (2023) — *Efficient Memory Management for Large Language Model Serving with PagedAttention* (SOSP). The vLLM paper; paired continuous batching with a paging KV allocator and reported the throughput gains cited above.
