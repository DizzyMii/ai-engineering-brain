---
tags: [decision, domain/inference-serving, level/core]
aliases: [LLM serving engine selection, inference engine comparison]
summary: "How to pick among vLLM, SGLang, TensorRT-LLM, llama.cpp, and TGI for a given hardware and workload; vLLM is the default."
---

# Decision - Choosing an Inference Serving Framework

> **The decision:** which engine runs your model (vLLM, SGLang, TensorRT-LLM, llama.cpp/Ollama, TGI, or MLC-LLM), given your hardware, workload shape, and latency/throughput SLO. **Default for the 80% case:** vLLM on NVIDIA GPUs. It has the broadest model and hardware coverage, the fastest day-0 support for new open-weight releases, an OpenAI-compatible server, and a mature ecosystem ([[Concept - Continuous Batching]], quantization, LoRA, speculative decoding, P/D disaggregation). Pick it unless a specific workload trait pulls you elsewhere.

## Decision flow

```mermaid
flowchart TD
    A[Choose a serving framework] --> B{Hardware?}
    B -->|Local box, CPU, Apple silicon, edge| C["llama.cpp / Ollama / LM Studio<br/>(GGUF k-quants, unified memory)"]
    B -->|WebGPU / mobile| D[MLC-LLM]
    B -->|NVIDIA GPU fleet| E{Workload shape?}
    E -->|Shared-prefix heavy: agents, RAG,<br/>few-shot, long chat history| F["SGLang<br/>(RadixAttention, fast structured output)"]
    E -->|Frozen model, strict p99 SLO,<br/>will pay build/compile cost| G["TensorRT-LLM<br/>(max NVIDIA throughput/latency)"]
    E -->|Already deep in the<br/>Hugging Face stack| H[TGI]
    E -->|New model on release day,<br/>general-purpose default| I["vLLM<br/>(broadest support, fastest iteration)"]
```

## Tradeoff matrix

| Framework | Best hardware | Ideal workload | Quant formats | Multi-LoRA | Iteration speed | Notable weakness |
|---|---|---|---|---|---|---|
| **vLLM** | NVIDIA (also AMD ROCm, TPU) | General GPU serving, new-model day-0 | AWQ, GPTQ, fp8, GGUF (partial), bnb | Strong ([[Concept - Multi-LoRA Serving]] origin ecosystem) | Fastest; new models land in days | Not the raw-speed ceiling on a fixed, frozen model |
| **SGLang** | NVIDIA, AMD | Shared-prefix / agentic / RAG workloads, DeepSeek MLA+MoE | fp8, AWQ, GPTQ | Good | Fast | Smaller ecosystem than vLLM for less common models |
| **TensorRT-LLM** | NVIDIA only | Fixed model, max throughput/latency at fleet scale | fp8, fp4 (Blackwell), int4/int8, custom kernels | Weaker | Slowest: requires engine (re)compilation per model/shape change | Ergonomics cost; brittle to model/config changes |
| **llama.cpp / Ollama / LM Studio** | CPU, Apple silicon (unified memory), consumer GPU | Local, edge, single-user | GGUF k-quants and i-quants (widest quant zoo) | Limited | Fast for new GGUF conversions | Not built for high-concurrency fleet serving |
| **MLC-LLM** | WebGPU, mobile | Browser / on-device inference | Its own compiled quant formats | Limited | Moderate | Narrow deployment target |
| **TGI** | NVIDIA | Teams standardized on the Hugging Face stack | AWQ, GPTQ, bnb, fp8 | Moderate | Moderate | Feature lag vs vLLM/SGLang on the newest techniques |

## The details that flip the decision

- **Single-user local box** → llama.cpp, even if you'd otherwise default to vLLM. With one user there's no batching benefit to amortize, and vLLM's memory and ops overhead buys nothing.
- **Strict p99 latency SLO at fleet scale, model frozen for months** → TensorRT-LLM. You pay the compile cost once and collect on tail latency and NVIDIA tensor-core utilization for a long time, especially on [[Concept - FP8 and Low-Precision Inference]] paths.
- **Brand-new open-weight model on release day** → vLLM or SGLang. TensorRT-LLM's engine-build step means it typically trails day-0 support by days to weeks.
- **Thousands of fine-tuned adapters over one base model** → lean toward whichever engine has the strongest [[Concept - Multi-LoRA Serving]] path (batched heterogeneous-adapter kernels, adapter paging). Naive per-adapter serving has a completely different cost model.
- **Heavy structured/JSON output, or the same system-prompt-plus-tools scaffold on every request** → SGLang. RadixAttention and compressed-FSM jump-forward decoding give it a real edge over generic [[Concept - Automatic Prefix Caching]] plus grammar masking.
- **DeepSeek-scale MoE with MLA** → SGLang has historically had the fastest, most complete support for that combination ([[Concept - MoE Inference and Expert Parallelism]]). Check current support before committing; this moves quickly (as of 2026).
- **AMD ROCm or TPU hardware** → the field narrows immediately. vLLM has the broadest non-NVIDIA support of the mainstream engines, and TensorRT-LLM is NVIDIA-only by construction.

## Connections

- [[Breakdown - vLLM]] — the internals (PagedAttention, V1 scheduler) behind the default recommendation.
- [[Breakdown - SGLang and RadixAttention]] — the mechanism behind the shared-prefix-heavy recommendation.
- [[Breakdown - TensorRT-LLM]] — the compilation model and kernel strategy behind the max-throughput recommendation.
- [[Concept - Multi-LoRA Serving]] — the criterion that flips the decision when serving many adapters over one base.
- [[Concept - Continuous Batching]] — the scheduling capability every one of these engines implements differently; it's a large share of why they perform differently on the same hardware.
- [[Reference - Inference Performance Math]] — the formulas to actually benchmark candidates against before committing.
- [[Playbook - Tuning an LLM Serving Deployment]] — what happens after you've picked an engine: turning it into a tuned deployment.
- [[Concept - LLM Observability and Tracing]] — production operability (tracing, metrics) differs across these engines and should factor into the choice, not just raw throughput.
- [[Decision - Selecting GPUs for Training and Inference]] — the hardware decision this one is downstream of; framework choice narrows sharply once the GPU vendor is fixed.
- [[Concept - The Inference Request Lifecycle]] — the request path every one of these frameworks implements; understanding it is the prerequisite for evaluating any of them.
- [[Concept - FP8 and Low-Precision Inference]] — the precision path that makes TensorRT-LLM's max-throughput case strongest on Hopper/Blackwell.
- [[Concept - Automatic Prefix Caching]] — the generic version of the shared-prefix optimization that SGLang's RadixAttention specializes and outperforms on.
- [[Concept - MoE Inference and Expert Parallelism]] — why DeepSeek-scale MoE+MLA serving is called out as a separate criterion in this decision.

## Sources

- Kwon et al. (2023) — "Efficient Memory Management for Large Language Model Serving with PagedAttention" (SOSP). The vLLM paper; establishes the memory-management baseline every later engine is compared against.
- Zheng et al. (2024) — "SGLang: Efficient Execution of Structured Language Model Programs." Introduces RadixAttention, the mechanism behind SGLang's shared-prefix advantage.
- NVIDIA — TensorRT-LLM documentation and release notes (ongoing). The authoritative source for current NVIDIA-specific kernel and precision support; check dates, this is a fast-moving target (as of 2026).
