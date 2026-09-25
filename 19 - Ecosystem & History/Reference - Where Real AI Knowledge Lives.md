---
tags: [reference, domain/ecosystem-history, level/surface]
aliases: [Where to Learn Real AI Engineering, AI Knowledge Source Map]
summary: "Where genuine AI-engineering signal actually lives — papers, blogs, code, people, communities — and what to skip. (as of 2026)"
---

# Reference - Where Real AI Knowledge Lives

## Lab technical reports and papers (highest signal)

| Source | Organization | What it's good for | Signal note (as of 2026) |
|---|---|---|---|
| Llama technical reports | Meta AI/FAIR | Data mixture, training recipe, ablations | Unusually detailed vs. other frontier labs |
| DeepSeek papers (V2/V3/R1) | DeepSeek | [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)|MLA]], [[Concept - GRPO and RL with Verifiable Rewards|GRPO]], [[Concept - FP8 Training|FP8]] training, disclosed cost figures | Closest thing to an open lab notebook among frontier-class releases |
| Qwen / Gemma technical reports | Alibaba / Google | Architecture + eval detail for mid-size open models | Medium-high; good for reproducible config values |
| Anthropic / OpenAI system & model cards | Anthropic, OpenAI | Capability and safety evals | Capability-heavy, architecture-light. Post-GPT-4 the norm shifted to withholding parameter count and compute |

## Engineering blogs that teach mechanism

| Source | Specialty |
|---|---|
| vLLM blog | Serving internals: continuous batching, [[Concept - PagedAttention]] |
| EleutherAI blog | Open pretraining, interpretability |
| Hugging Face blog | Library internals, ecosystem tooling |
| PyTorch dev blog | Compiler (`torch.compile`), distributed internals |
| Character.AI engineering blog | KV-cache economics at extreme inference scale |
| Together AI / Modal blogs | Inference infrastructure, GPU cost math |
| Lilian Weng (independent, ex-OpenAI) | RLHF, agents, diffusion; widely cited synthesis posts |
| Chip Huyen (independent) | MLOps, evaluation, systems design |
| Sebastian Raschka (independent) | From-scratch implementations (LoRA, fine-tuning internals) |
| Jay Alammar (independent) | Illustrated Transformer / Illustrated GPT, visual mechanism explainers |
| Kipply (independent) | Inference math, kernel-level detail |
| Horace He (PyTorch) | Compiler and kernel performance ("Making Deep Learning Go Brrrr") |

## Discovery tools

| Tool | Use |
|---|---|
| arXiv `cs.CL` / `cs.LG` | First-release listings; new-paper cadence peaks Friday |
| Semantic Scholar / Connected Papers | Citation-graph navigation, finding a paper's intellectual ancestry |
| OpenReview | Actual peer reviews and author rebuttals (NeurIPS, ICLR) |
| Papers with Code | Benchmark-to-paper mapping; activity declining as of 2026 |

## Code as ground truth

| Source | What it teaches |
|---|---|
| nanoGPT (Karpathy) | A minimal, fully readable GPT pretraining loop |
| `transformers` / vLLM / SGLang source | How serving and training actually run, vs. what the paper describes |
| Megatron-LM | Reference implementation of [[Concept - Tensor and Pipeline Parallelism|3D parallelism]] |
| GPU MODE community, CUTLASS/Triton examples | Kernel-level ground truth for GPU performance work |

## Communities where tribal knowledge leaks

- EleutherAI Discord and Nous Research Discord: open pretraining and post-training war stories.
- r/LocalLLaMA: quantization, consumer-GPU inference, the "GPU-poor" scene.
- Curated X/Twitter lists of named practitioners (see below): pre-publication findings, and corrections to hyped claims.
- The llama.cpp / GGUF ecosystem. The fastest place to learn what breaks when a model meets consumer hardware.

## People mapped to specialty (as of 2026)

| Person | Known for |
|---|---|
| Tri Dao | Attention kernels, [[Deep Dive - FlashAttention|FlashAttention]] |
| Stas Bekman | Training-at-scale operations, public engineering chronicles |
| Noam Shazeer (and lineage) | MoE routing, multi-query attention, Transformer engineering |
| Jeremy Howard | fast.ai, practitioner-first pedagogy |

## Filtering heuristics

| Heuristic | Why |
|---|---|
| Prefer tech reports over press releases | Press releases carry zero mechanism; tech reports at least attempt one |
| Prefer ablations over headline numbers | Headline numbers are the benchmarks the lab chose to win (see [[Gotchas - Reading Model Announcements]]) |
| Prefer code over claims | Code can't lie about what executes |
| Treat benchmark-only announcements as marketing | No architecture, no ablation, no released weights: it's a press release wearing a paper's clothes |

## What's overrated (as of 2026)

Most Medium/LinkedIn "AI tutorials". Paid "prompt engineering" certificate courses. YouTube explainers that never open a config file or plot a loss curve. They aren't so much wrong as disconnected from the substrate. Use them for entry-level orientation at best, never as a primary source.

Sources rot fast here. Date-stamp any claim you pull from this list, and re-verify blogs and people every 12–18 months, because specialties and employers shift. The DeepSeek papers didn't exist as a top signal source before 2024, and Papers with Code's decline is itself a 2024–2026 development.

## Connections
- [[Concept - The Preprint and Social-Media Research Culture]] — explains *why* the field's knowledge lives in this scattered, fast-decaying form rather than in journals.
- [[Gotchas - Reading Model Announcements]] — the specific traps that make filtering announcements from measurement necessary.
- [[Reference - The AI Lab Landscape]] — who is publishing these reports and what strategic incentive shapes what they disclose.
- [[Deep Dive - The Transformer]] — the kind of mechanism-level content this note is pointing you toward, as a worked example of the target depth.
- [[Breakdown - vLLM]] — a concrete case of "code as ground truth" outranking the paper for understanding how serving actually behaves.
- [[Reference - Model Genealogy]] — the kind of derived, cross-referenced knowledge (lineage, ancestry) that these sources make possible to reconstruct.
- [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — a concrete example of the mechanism-level disclosure (MLA) that makes the DeepSeek papers unusually high-signal.
- [[Concept - GRPO and RL with Verifiable Rewards]] — another disclosed mechanism from the DeepSeek papers cited as a high-signal source.
- [[Concept - FP8 Training]] — the third disclosed mechanism that makes DeepSeek's technical reports read like an open lab notebook.
- [[Concept - PagedAttention]] — the kind of serving-internals mechanism the vLLM blog documents better than most papers do.
- [[Deep Dive - FlashAttention]] — the standard example of a kernel-level mechanism best learned from code and blog post rather than the paper alone.
- [[Concept - Tensor and Pipeline Parallelism]] — the kind of training-at-scale mechanism Megatron-LM's source code teaches more reliably than any single paper.
