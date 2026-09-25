---
tags: [concept, domain/fine-tuning, level/surface]
aliases: [PEFT]
summary: "Freeze the pretrained weights, train a tiny added parameter set instead — optimizer memory drops from tens of GB to megabytes."
---

# Concept - Parameter-Efficient Fine-Tuning (PEFT)

> **One-paragraph hook:** full fine-tuning updates every weight and pays for it in optimizer memory. For a 7B model that's the difference between one consumer GPU and a multi-GPU node with offload. PEFT methods freeze the pretrained weights $W$ and train a small new or selected parameter set $\theta$, with $|\theta| \ll |W|$, typically 0.01-1% of the base. For behavior and format adaptation the model still gets most of what full fine-tuning buys. The difference usually shows up in your GPU bill, not your eval scores.

## The mechanism

Every PEFT method does the same basic thing: keep $W$ (the billions of pretrained parameters) fixed and route the adaptation through a much smaller $\theta$. Gradients, optimizer state and (for most methods) activation checkpoints scale with the number of *trainable* parameters, not the number the forward pass touches. So memory collapses while the model's inference-time capacity stays basically the same.

Ding et al. 2022 (the "Delta Tuning" survey) sorted the resulting zoo into three families:

| Family | Mechanism | Example methods | Typical trainable % |
|---|---|---|---|
| Additive | Insert new modules into the frozen network and train only those | [[Concept - Adapter Layers]], [[Concept - Prompt Tuning and Prefix Tuning]] | 0.1-8% |
| Selective | Train an existing subset of the model's own parameters, freeze the rest | BitFit (biases only, ~0.08%) | ~0.08% |
| Reparameterization | Represent the weight *update* in a constrained low-rank form and train only its factors | [[Deep Dive - LoRA]] | 0.1-1% |

The win is memory. [[Concept - Adam and AdamW]] under [[Concept - Mixed Precision Training]] stores, per trainable parameter, a bf16 weight and gradient (2+2 bytes) plus an fp32 master weight and two fp32 moment buffers (4+4+4 bytes), roughly 16 bytes/parameter (see [[Reference - Memory Math for Transformers]]). For a 7B model in bf16 the frozen weights alone cost ~14GB. Full fine-tuning adds gradients plus the fp32 master-and-moments state, on the order of ~84GB together, pushing the total near 100GB. That's why full FT of a 7B model needs an 80GB A100 with offload or several GPUs. PEFT changes the arithmetic by category, not by degree: only $\theta$ gets gradients, so the optimizer state, gradient buffers and master copy shrink from gigabytes to megabytes. A rank-16 LoRA on all linear layers of a 7B model adds roughly 40M trainable parameters (~0.6% of the base), and its AdamW state is a few hundred MB.

## In practice

The Hugging Face `peft` library (`LoraConfig`, `get_peft_model`) is the de facto implementation, and it's why PEFT went from research curiosity to default. It wraps any `transformers` model, freezes the base and injects the trainable parameters with a few lines of config. PEFT is a *parameterization* choice, independent of the training *objective*. You can run [[Concept - Supervised Fine-Tuning (SFT)]], DPO or RLVR through a LoRA adapter the same way you would through full fine-tuning. The objective and the parameter-efficiency strategy live in different parts of the stack (objectives are domain 06's territory).

On quality, PEFT roughly matches full fine-tuning for instruction-following, tone and style: changes that push an existing capability into a canonical shape without adding a new one. It measurably lags full FT when the target is a large distribution shift from pretraining, like new code idioms or mathematical domains, because the trainable subspace is too small to represent the update ([[Concept - Why LoRA Underperforms Full Fine-Tuning]] has the mechanistic account).

The other payoff comes at serving time. The base weights never change, so one frozen base can host many small, swappable adapters. A single GPU can serve dozens of fine-tuned "variants" by hot-swapping a few megabytes of adapter weights per request, with no full model copy per task ([[Concept - Multi-LoRA Serving]] covers the serving mechanics).

## Failure modes

The most common failure is a category error: using PEFT (or any fine-tuning) to inject large amounts of new factual knowledge. A few megabytes of trainable parameters can't store a corpus, and the training signal for "which fact goes with which entity" is weak next to the signal for "which format/tone to imitate." The model learns to sound confident long before it learns to be correct. [[Concept - What Fine-Tuning Can and Cannot Teach]] covers this failure and the right tool for knowledge.

The second is under-coverage. Restrict the trainable parameters to too narrow a slice of the network (e.g., attention projections only) and the update is starved of capacity; the fine-tune underfits even though the loss curves look reasonable. The fix is broader parameter coverage, not more data.

## The non-obvious

The three families give up different things. Additive methods (adapters, soft prompts) insert modules *sequentially* into the forward pass. They can't be algebraically folded back into $W$, so they carry a small but permanent extra inference latency. Reparameterization methods (the LoRA family) express the update as $W + \Delta W$, and $\Delta W$ can be added straight into $W$ after training, with zero inference overhead once merged. That mergeability difference, more than any quality gap, is why reparameterization overtook additive adapters for large-scale LLM serving, even though Houlsby-style adapters were historically quite competitive on quality.

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
