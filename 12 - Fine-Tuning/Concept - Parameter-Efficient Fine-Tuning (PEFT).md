---
tags: [concept, domain/fine-tuning, level/surface]
aliases: [PEFT]
summary: "Freeze the pretrained weights, train a tiny added parameter set instead — optimizer memory drops from tens of GB to megabytes."
---

# Concept - Parameter-Efficient Fine-Tuning (PEFT)

> **One-paragraph hook:** Full fine-tuning updates every weight in a model and pays for it in optimizer memory — for a 7B model that's the difference between one consumer GPU and a multi-GPU node with offload. PEFT methods freeze the pretrained weights $W$ and train a small new or selected parameter set $\theta$ instead, with $|\theta| \ll |W|$, typically 0.01-1% of the base. The model still gets most of what full fine-tuning buys for behavior and format adaptation; the difference shows up in your GPU bill, not usually in your eval scores.

## The mechanism

The unifying idea across every PEFT method: keep $W$ (the billions of pretrained parameters) fixed, and route the adaptation through a much smaller $\theta$. Because gradients, optimizer state, and (for most methods) activation checkpoints scale with the number of *trainable* parameters, not the number of parameters the forward pass touches, memory collapses even though the model's capacity at inference time is basically unchanged.

Ding et al. 2022 (the "Delta Tuning" survey) organized the resulting zoo into three families:

| Family | Mechanism | Example methods | Typical trainable % |
|---|---|---|---|
| Additive | Insert new modules into the frozen network and train only those | [[Concept - Adapter Layers]], [[Concept - Prompt Tuning and Prefix Tuning]] | 0.1-8% |
| Selective | Train an existing subset of the model's own parameters, freeze the rest | BitFit (biases only, ~0.08%) | ~0.08% |
| Reparameterization | Represent the weight *update* in a constrained low-rank form and train only its factors | [[Deep Dive - LoRA]] | 0.1-1% |

Why memory is the real win, concretely: [[Concept - Adam and AdamW]] under [[Concept - Mixed Precision Training]] stores, per trainable parameter, a bf16 weight and gradient (2+2 bytes) plus an fp32 master weight and two fp32 moment buffers (4+4+4 bytes) — roughly 16 bytes/parameter total (see [[Reference - Memory Math for Transformers]]). For a 7B model in bf16, the frozen weights alone cost ~14GB. Full fine-tuning adds gradients plus the fp32 master-and-moments state on top — together on the order of ~84GB — pushing total memory near 100GB, which is why full FT of a 7B model needs an 80GB A100 with offload or several GPUs. PEFT changes this arithmetic categorically rather than incrementally: since only $\theta$ receives gradients, the optimizer state, gradient buffers, and master copy shrink from gigabytes to megabytes. A rank-16 LoRA applied to all linear layers of a 7B model adds roughly 40M trainable parameters (~0.6% of the base) — its AdamW state is a few hundred MB, not tens of gigabytes.

## In practice

The Hugging Face `peft` library (`LoraConfig`, `get_peft_model`) is the de-facto implementation and the reason PEFT went from a research curiosity to a default: it wraps any `transformers` model, freezes the base, and injects the trainable parameters with a few lines of config. Crucially, PEFT is a *parameterization* choice, orthogonal to the training *objective* — you can run [[Concept - Supervised Fine-Tuning (SFT)]], DPO, or RLVR through a LoRA adapter exactly as you would through full fine-tuning; the objective and the parameter-efficiency strategy are independent axes that live in different parts of the stack (objectives are domain 06's territory).

Quality-wise, PEFT roughly matches full fine-tuning for instruction-following, tone, and style adaptation — the kind of change that nudges an existing capability into a canonical shape rather than adding a new one. It measurably lags full FT when the target involves a large distribution shift from pretraining, such as new code idioms or mathematical domains, because the trainable subspace is too small to represent the needed update (see [[Concept - Why LoRA Underperforms Full Fine-Tuning]] for the mechanistic account).

The other practical payoff PEFT unlocks is at serving time: because the base weights never change, one frozen base model can host many small, swappable adapters, letting a single GPU serve dozens of fine-tuned "variants" by hot-swapping a few megabytes of adapter weights per request instead of deploying a full copy of the model per task ([[Concept - Multi-LoRA Serving]] owns the serving-side mechanics).

## Failure modes

The most common failure is a category error: using PEFT (or any fine-tuning) to inject large amounts of new factual knowledge. A handful of megabytes of trainable parameters is nowhere near enough capacity to store a corpus, and the training signal for "what fact goes with what entity" is weak compared to the signal for "what format/tone to imitate" — the model learns to sound confident long before it learns to be correct. This failure mode, and the right tool for knowledge instead, is covered in [[Concept - What Fine-Tuning Can and Cannot Teach]].

A second failure is under-coverage: restricting the trainable parameters to too narrow a slice of the network (e.g., attention projections only) starves the update of capacity, and the fine-tune underfits even though loss curves look reasonable — the fix is broader parameter coverage, not more data.

## The non-obvious

The three PEFT families are not interchangeable in what they trade away. Additive methods (adapters, soft prompts) insert modules *sequentially* into the forward pass — they cannot be algebraically folded back into $W$, so they carry a small but permanent extra inference latency at serving time. Reparameterization methods (the LoRA family) express the update as $W + \Delta W$, and $\Delta W$ can be added directly into $W$ after training — zero inference overhead once merged. This mergeability difference, more than any quality gap, is why reparameterization eclipsed additive adapters for large-scale LLM serving even though Houlsby-style adapters were historically quite competitive on quality.

## Connections
- [[Deep Dive - LoRA]] — the dominant reparameterization method and the full mechanism behind the family that eclipsed the rest.
- [[Concept - QLoRA]] — combines PEFT with 4-bit base quantization to push memory savings even further.
- [[Concept - Adapter Layers]] — the additive family this note's taxonomy references, including why they don't merge.
- [[Concept - Prompt Tuning and Prefix Tuning]] — the soft-prompt branch of the additive family.
- [[Reference - PEFT Method Comparison]] — the lookup table comparing every method's params, mergeability, and quality.
- [[Concept - Mixed Precision Training]] — the training regime whose byte-per-parameter costs make PEFT's memory win concrete.
- [[Concept - Adam and AdamW]] — the optimizer whose per-parameter state is what PEFT shrinks.
- [[Reference - Memory Math for Transformers]] — the formulas behind the 16-bytes/parameter estimate used above.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the objective PEFT is most commonly paired with, and orthogonal to it.
- [[Concept - Why LoRA Underperforms Full Fine-Tuning]] — the mechanistic account of where PEFT's quality gap actually comes from.
- [[Concept - Multi-LoRA Serving]] — the serving-side payoff of a frozen base plus swappable adapters.
- [[Concept - What Fine-Tuning Can and Cannot Teach]] — the companion note on PEFT's most common failure mode: mistaking it for a knowledge-injection tool.

## Sources
- Ding et al. 2022 — "Delta Tuning: A Comprehensive Study of Parameter Efficient Methods for Pre-trained Language Models." The additive/selective/reparameterization taxonomy used throughout this note.
- Houlsby et al. 2019 — "Parameter-Efficient Transfer Learning for NLP." Origin of the additive/bottleneck-adapter family.
- Ben-Zaken et al. 2021 — "BitFit: Simple Parameter-efficient Fine-tuning for Transformer-based Masked Language-models." The minimal selective-family baseline.
- Hu et al. 2021 — "LoRA: Low-Rank Adaptation of Large Language Models." The reparameterization method that became the field's default (full mechanism in [[Deep Dive - LoRA]]).
