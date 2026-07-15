---
tags: [checklist, domain/ecosystem-history, level/core]
aliases: [open-weights due diligence, model vetting checklist, go/no-go for open models]
summary: "Pre-adoption go/no-go for open-weights models: license, provenance/supply-chain, lineage, real capability, format fit, safety, and ops."
---

# Checklist - Vetting an Open-Weights Model for Production

Run this before an open-weights model touches production traffic. It covers the checks that are *unique to this domain* — provenance, licensing, lineage, ecosystem fit — not general serving or eval engineering (those live in domains 07/08/13). Do this **after** you've chosen a branch in [[Decision - Which Model Ecosystem to Bet On]] and **before** you wire the model into anything. Every unchecked box is a known way teams have been burned; the incidents behind the non-obvious ones are in *Why these items*.

## License

- [ ] Confirmed the exact license file **for this revision**, not the family — [[Reference - Open Weights Licensing]] shows Llama 2 ≠ 3 ≠ 4 and Falcon/Qwen changed licenses mid-lineage.
- [ ] Verified the four grants you actually need: **commercialize**, **redistribute**, **fine-tune/derive**, and **train other models on outputs**.
- [ ] Checked the caps: Llama's **>700M-MAU** clause, field-of-use bans in the acceptable-use policy, geographic/export limits, and any "Built with X" naming/attribution requirement.
- [ ] For Apache 2.0 / MIT, confirmed the patent grant (Apache) and that no RAIL/Gemma behavioral rider silently attaches downstream.

## Provenance & supply chain

- [ ] Confirmed the publisher org is the authentic one — checked for typosquatted repo names (`meta-llaama`, `Qw3n`) and unofficial mirrors.
- [ ] Preferred **safetensors** over `pickle`/`.bin`/`.pt`; if only pickle exists, loaded it in a sandbox first — pickle deserialization is arbitrary code execution on `torch.load`.
- [ ] Ran a malware/secret scan (HF's scanner flags dangerous pickle imports like `os.system`, `posix.system`, `eval`).
- [ ] Pinned the download to a **specific commit revision hash**, not `main`, and verified the SHA256 of each weight shard.

## Lineage

- [ ] Identified the **true base model** with [[Snippet - Tracing Model Lineage via Hugging Face Metadata]] — a "new" model is often a merge or LoRA on a base whose license actually governs you.
- [ ] Flagged distill-of-closed exposure: outputs distilled from GPT-4/Claude carry ToS/legal risk regardless of the wrapper's permissive license.
- [ ] For merges, sanity-checked that the merge did not silently break the chat template or swap the tokenizer.

## Real capability

- [ ] Reproduced **at least one headline benchmark independently** — model-card numbers are claims, not measurements.
- [ ] Cross-checked an independent arena/leaderboard rank (LMArena) *not* controlled by the publisher, and cross-referenced trustworthy sources per [[Reference - Where Real AI Knowledge Lives]].
- [ ] Ran **your own private eval set** — the one corpus [[Concept - Benchmark Contamination]] cannot have leaked into.

## Format & tokenizer fit

- [ ] Confirmed the exact chat template and special tokens (BOS/EOS/pad/system) — a wrong template degrades quality silently, with no error.
- [ ] Measured **real usable context**, not the advertised max ("up to 128k" routinely rots far earlier).

## Safety & compliance

- [ ] Distinguished **base vs instruct** — a base checkpoint has no refusals and will complete anything, including your abuse cases.
- [ ] Probed the refusal profile and known jailbreaks against *your* risk surface, and checked for watermarking.
- [ ] Obtained a geopolitical/data-residency sign-off for foreign-origin weights (DeepSeek/Qwen face procurement bans in some sectors even when excellent).

## Operational

- [ ] Confirmed a serving path exists: vLLM/SGLang support, and a [[Concept - Post-Training Quantization Formats]] build (GGUF/AWQ/GPTQ) if you need one.
- [ ] Did the VRAM math with [[Reference - Memory Math for Transformers]]: params×bytes + KV cache — does it fit your GPU at your batch size and context?
- [ ] Checked a maintenance signal: repo commit activity, issue responsiveness, and deprecation risk before standardizing on it.

## Why these items

- **Load pickle in a sandbox:** real malicious models on the Hub have shipped weights that execute code on `torch.load`; `safetensors` (memory-mapped, code-free) exists *specifically* to close this arbitrary-code-execution hole.
- **Pin the revision hash:** weights get silently re-uploaded under the same name (quantized, re-merged, or "fixed"); an unpinned `main` pull changes the model under you between deploys.
- **Identify the true base:** the "GPT-4 in a trench coat" pattern — instruct models that are ShareGPT/GPT-4 distills on an undeclared base — means the base's license *and* the distillation's ToS both bind you, and neither is on the shiny model card.
- **Run your own private evals:** open models chasing the Open LLM Leaderboard trained on test sets; a whole cohort of top-ranked models had card numbers that were fiction under [[Concept - Benchmark Contamination]].
- **The 700M-MAU clause:** it exists to deny hyperscaler competitors the grant; a startup that succeeds *into* that user count loses the license it launched on.
- **Geopolitical sign-off:** the weights being open does not make the origin acceptable to compliance — Chinese-origin model procurement bans are real in government and some enterprise contexts as of 2026.
- **Confirm the chat template:** a mismatched template is the single most common cause of "the model got noticeably dumber after we deployed it" — no exception is thrown, the quality just quietly drops.

## Connections

- [[Reference - Open Weights Licensing]] — the per-license grant/restriction matrix this checklist's license stage operationalizes.
- [[Snippet - Tracing Model Lineage via Hugging Face Metadata]] — the tool that executes the lineage stage and surfaces undeclared bases and distills.
- [[Decision - Which Model Ecosystem to Bet On]] — the upstream strategy call; this checklist is the go/no-go once you've chosen the open-weights branch.
- [[Concept - Benchmark Contamination]] — why model-card numbers are untrustworthy and a private eval set is mandatory, not optional.
- [[Concept - Post-Training Quantization Formats]] — the operational availability of GGUF/AWQ/GPTQ builds that determine whether the model is actually servable on your hardware.
- [[Reference - Memory Math for Transformers]] — the VRAM/KV-cache arithmetic behind the "does it fit" operational check.
- [[Reference - Where Real AI Knowledge Lives]] — where to find the *independent* benchmark and arena signal the capability stage demands.
