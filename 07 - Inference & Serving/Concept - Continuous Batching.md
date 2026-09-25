---
tags: [concept, domain/inference-serving, level/core]
aliases: [iteration-level scheduling, in-flight batching, dynamic batching]
summary: "Iteration-level scheduling that re-forms the decode batch every step so short requests never idle a GPU slot waiting on a straggler."
---
# Concept - Continuous Batching
> **One-paragraph hook:** Static, request-level batching runs a fixed group of sequences until the longest one finishes, and every short sequence sits there holding a GPU slot it isn't using. Continuous batching (also called iteration-level scheduling or in-flight batching) re-decides batch membership after every decode step: finished sequences leave, queued ones join immediately. That one change took LLM serving throughput from "acceptable" to "production-grade."

## The mechanism
[[Concept - The Inference Request Lifecycle]] runs [[Concept - Prefill and Decode Phases]]. Prefill is one parallel forward pass over the prompt; decode is a sequential loop, one token per step per sequence. The naive way to batch decode is per request: pick N sequences, run decode until all N hit EOS or `max_tokens`, then swap in the next N. Output length varies everywhere (some sequences finish in 20 tokens, others run to 2000), so for most of that window the batch is mostly idle sequences padded out to keep tensor shapes rectangular.

Orca (Yu et al., OSDI 2022) fixed this by making the iteration the scheduling unit instead of the request. After every forward pass, the scheduler:

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

It works because of the asymmetry from [[Concept - Prefill and Decode Phases]]: decode is memory-bandwidth-bound and re-reads the full weight matrix from HBM every step, whatever the batch size. Arithmetic intensity scales roughly with batch size $B$ (one MAC per weight per sequence in the batch), so adding active sequences per step costs almost nothing in latency until you approach the compute roof. You're spreading a fixed HBM read over more useful work. Continuous batching is the scheduler that actually collects that saving, where static batching wastes it between batch boundaries.

## In practice
Continuous batching needs to add a request's KV to the batch *mid-flight*, at an arbitrary moment, without a contiguous pre-reserved buffer. [[Concept - PagedAttention]] provides that, so the two ship together. Orca proved the scheduling idea and vLLM's PagedAttention gave it a memory manager that could keep up. [[Breakdown - vLLM]] popularized the combination, TensorRT-LLM calls the same idea "in-flight batching", and TGI and SGLang implement equivalent iteration-level schedulers.

The reported gains are large because static batching wastes a lot. Orca and the vLLM paper report roughly **2-23x throughput** over request-level static batching. The low end is workloads with uniform output lengths (little waste to reclaim); the high end is high output-length variance (chat, agents), where static batching was losing the most idle capacity.

Every deployment tunes two knobs: `max_num_seqs` (how many concurrent sequences the scheduler allows in a batch) and `max_num_batched_tokens` (the per-iteration token budget, shared between prefill and decode). Set `max_num_seqs` too high and you overcommit the KV cache and force preemption. Too low and throughput is capped below what the hardware can do.

## Failure modes
**Newly admitted requests need a prefill.** A full prefill pass dropped into an otherwise decode-only iteration takes that step's compute and spikes the inter-token latency (TPOT) of every sequence already decoding. You see periodic latency jitter that tracks the new-request arrival rate. [[Concept - Chunked Prefill]] and [[Concept - Prefill-Decode Disaggregation]] exist to remove that interference.

**Preemption thrashing:** with `max_num_seqs` above what the KV budget can sustain, the scheduler has to evict sequences mid-generation and recompute them later to free memory. Throughput craters and TPOT spikes right as load rises. It looks like a capacity cliff, not graceful degradation. Watch KV utilization and preemption count, not just raw QPS.

**Silent underutilization** is the opposite. Conservative `max_num_seqs`/`max_num_batched_tokens` values leave throughput on the table with no error signal. Nothing about a too-low limit looks broken from outside, so the only way to catch it is benchmarking at the knee (see [[Playbook - Tuning an LLM Serving Deployment]]).

## The non-obvious
The benefit stops where the decode step crosses from memory-bound to compute-bound on [[Concept - The Roofline Model]]. Past that point, more concurrent sequences buy no throughput and only worsen everyone's TPOT. People who assume more batching is always better learn this the hard way. The target is the concurrency at the knee of the latency-throughput curve, not maximum `max_num_seqs`, and the knee depends on the specific GPU, model, and context length. It isn't a universal constant. For the same reason raw throughput is the wrong top-line metric: [[Concept - Latency, Throughput, and Cost in LLM Serving]] explains why capacity planning should optimize goodput (throughput *subject to* an SLO), and [[Concept - LLM Load Testing and Capacity Planning]] treats "find the knee" as the core exercise instead of "maximize tokens/sec."

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
