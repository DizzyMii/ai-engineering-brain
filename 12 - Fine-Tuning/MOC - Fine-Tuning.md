---
tags: [moc, domain/fine-tuning, level/surface]
aliases: []
summary: "Map of Fine-Tuning: full FT, the LoRA/PEFT family, adapters, dataset prep, evaluation, and hyperparameters for adapting a base model."
---

# MOC - Fine-Tuning

This domain covers adapting a pretrained model's weights (or, in the newest methods, its activations) to a specific task, domain or behavior after prompting and retrieval have run out of road. That means full fine-tuning, the parameter-efficient family that grew out of LoRA, and the practical machinery of dataset prep, hyperparameters and evaluation that decides whether a fine-tune works. Fine-tuning is the right tool for changing *how* a model behaves (format, tone, refusal policy, latency), though [[Concept - What Fine-Tuning Can and Cannot Teach|it cannot reliably teach the model new facts]]; that's retrieval's job. And [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]] turned a job that once needed a multi-GPU node into a weekend run on a single consumer GPU. The notes go from the surface case for fine-tuning at all, through the core PEFT-vs-full-FT and dataset-prep decisions every practitioner faces, into advanced LoRA/QLoRA internals and the pre-LoRA adapter lineage they replaced, then out to frontier rank-and-initialization work (DoRA, rsLoRA, ReFT) still closing the LoRA-vs-full-FT gap. The unicorn layer is the mechanistic account of *why* that gap exists, plus the folklore of defaults the community arrived at the hard way. Every method here trades quality for cost somewhere, and the core discipline of the domain is measuring that trade honestly instead of trusting one flattering eval number.

## Start here

- **Surface** → [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]] — the core idea: freeze the pretrained weights, train a tiny added parameter set, and cut optimizer memory by orders of magnitude.
- **Core** → [[Decision - Full Fine-Tuning vs PEFT]] — the default 80%-case call (LoRA or QLoRA) and the conditions under which full fine-tuning earns its cost.
- **Advanced** → [[Deep Dive - LoRA]] — the low-rank update mechanism (ΔW = BA) under most of this domain, and why it merges back for zero added inference cost.
- **Frontier** → [[Concept - DoRA]] — decomposing weights into magnitude and direction to close part of the LoRA-vs-full-FT quality gap, one of several active rank/init refinements.
- **Unicorn** → [[Lore - LoRA Folklore and Hard-Won Defaults]] — the defaults, superstitions and hard-way fixes the open-model community accumulated between 2021 and 2025.

## Foundations and decisions

- [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]] — freeze the pretrained weights and train a tiny added parameter set, cutting optimizer memory from tens of GB to megabytes.
- [[Concept - What Fine-Tuning Can and Cannot Teach]] — fine-tuning reliably reshapes behavior, format and style; it's a slow, unreliable way to inject new facts.
- [[Decision - Fine-Tuning vs RAG vs Prompting]] — prompt first, escalate to RAG for missing knowledge, fine-tune only for behavior, format, or latency prompting can't fix.
- [[Decision - Full Fine-Tuning vs PEFT]] — default to LoRA/QLoRA; use full fine-tuning only with a large domain shift, the hardware, and one model needing max quality.

## LoRA and the low-rank adaptation family

- [[Deep Dive - LoRA]] — freezes W and learns a low-rank correction ΔW = BA injected as a parallel branch, cutting optimizer memory by two orders of magnitude.
- [[Concept - QLoRA]] — 4-bit NF4 base quantization plus bf16 LoRA adapters and paged optimizers, letting a 65B model fine-tune on one GPU.
- [[Concept - DoRA]] — decomposes weights into magnitude and direction, fine-tuning magnitude fully and reserving the LoRA update for direction, beating plain LoRA at equal parameter count.
- [[Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)]] — SVD, QR, and quantization-aware starting points that replace LoRA's zero-init and change convergence speed and final quality.
- [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]] — the standard alpha/r scaling caps usable rank; rank-stabilized LoRA's alpha/sqrt(r) fix makes high rank usable without instability.
- [[Concept - Why LoRA Underperforms Full Fine-Tuning]] — the mechanistic account of when and why constraining the update to a low-rank subspace costs quality, and when the gap disappears.

## Pre-LoRA and alternative PEFT mechanisms

- [[Concept - Adapter Layers]] — bottleneck adapters, IA3 and BitFit: the pre-LoRA PEFT lineage whose in-series design is what LoRA reversed to win.
- [[Concept - Prompt Tuning and Prefix Tuning]] — learnable soft-prompt and prefix vectors that steer a frozen model through attention without touching a single weight.
- [[Concept - Representation Fine-Tuning (ReFT)]] — freezes every weight and learns a low-rank intervention on hidden activations, matching LoRA with 10-50x fewer trainable parameters.

## Forgetting and evaluation

- [[Concept - Catastrophic Forgetting]] — fine-tuning on narrow data erodes broad pretrained capability unless you defend against it; gradient descent won't protect it for you.
- [[Playbook - Evaluating a Fine-Tune]] — how to verify a fine-tune is a net win (task gain minus capability regression minus diversity loss) before it ships.

## Reference tables

- [[Reference - PEFT Method Comparison]] — lookup matrix of PEFT methods by parameter count, family, mergeability, inference cost, and quality versus full fine-tuning.
- [[Reference - Fine-Tuning Hyperparameters]] — typical LoRA/QLoRA/full-FT defaults for learning rate, epochs, rank, alpha, warmup, schedule, and precision, with rationale.

## Data preparation

- [[Playbook - Preparing a Fine-Tuning Dataset]] — end-to-end procedure for sourcing, sizing, formatting, and validating a training set before a training job starts.
- [[Gotchas - Fine-Tuning Data and Chat Templates]] — seven data- and formatting-side pitfalls (wrong chat templates, unmasked prompts, tokenizer drift) that silently wreck a fine-tune.

## Implementation gotchas and code

- [[Gotchas - LoRA Fine-Tuning]] — seven pitfalls that quietly wreck LoRA/QLoRA training, saving, and merging, symptom-first, target-module coverage foremost.
- [[Snippet - LoRA Linear Layer from Scratch]] — a minimal PyTorch LoRA-wrapped Linear showing the zero-init identity start, alpha/r scaling, and a free-inference merge.
- [[Snippet - QLoRA Fine-Tune Configuration]] — a runnable QLoRA setup (transformers + bitsandbytes + peft + TRL) with every 4-bit and LoRA flag that matters annotated.

## Systems and folklore

- [[Breakdown - Unsloth]] — open-source patches to Hugging Face's forward/backward that make single-GPU LoRA/QLoRA roughly 2x faster and 50-80% lighter with numerically identical loss curves.
- [[Lore - LoRA Folklore and Hard-Won Defaults]] — the defaults everyone converged on in LoRA fine-tuning and the incidents behind them, each labeled by evidence status.

## Adjacent domains

- [[MOC - Post-Training]] — SFT and preference optimization are where LoRA and the rest of this domain's methods get applied; the pipeline lives there, the parameter efficiency here.
- [[MOC - Retrieval & RAG]] — the other fix for a frozen model's knowledge gap; [[Decision - Fine-Tuning vs RAG vs Prompting]] is this domain's half of that shared decision.
- [[MOC - Evaluation]] — general eval methodology (judges, held-out sets, statistical rigor) that [[Playbook - Evaluating a Fine-Tune]] applies to the specific case of a fine-tuned checkpoint.
- [[MOC - Hardware & Systems]] — the GPU memory math (optimizer states, quantization, paged optimizers) that decides whether a fine-tune fits on one card; this domain's PEFT methods are built around it.
