# AI Engineering Brain

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

An Obsidian vault of **~660 interlinked notes on AI engineering**, covering the stack from the math substrate up to frontier deployment economics. Every domain is laddered **surface → core → advanced → frontier → unicorn**, from "what it is and why it exists" out to the tribal knowledge almost nobody writes down.

It's one connected graph with enforced structure. Every note meets its link minimums, every link resolves, and every empirical claim in the applied domains carries an evidence tier, a named source and a date.

## What's inside

**The Engineering Wing (domains 01–19):** the mechanisms, architectures, training runs and infrastructure that make models work.

| # | Domain | Scope |
|---|--------|-------|
| 01 | Foundations | Linear algebra, probability, floating point: the substrate every other domain assumes |
| 02 | Neural Networks | Forward pass, loss, backprop, optimization |
| 03 | Architectures | Attention, MoE, positional encoding, sequence mixers |
| 04 | Training at Scale | Parallelism, precision, multi-thousand-GPU mechanics |
| 05 | Data Engineering | Sourcing, filtering, deduplicating, and mixing the corpus |
| 06 | Post-Training | SFT, RLHF, DPO/GRPO: raw predictor to deployed assistant |
| 07 | Inference & Serving | KV cache, batching, quantization, speculative decoding |
| 08 | Hardware & Systems | GPU/TPU internals, kernels, cluster networking |
| 09 | Prompting & Context | Context-window engineering and why it swings quality double digits |
| 10 | Agents | The control loop, tool use, planning, memory |
| 11 | Retrieval & RAG | Turning documents into retrievable facts |
| 12 | Fine-Tuning | Full FT through the LoRA/PEFT family, and when not to |
| 13 | Evaluation | Trustworthy measurement and how benchmarks break without anyone noticing |
| 14 | Safety & Interpretability | Manipulation resistance and model internals |
| 15 | Multimodal | VLMs, diffusion, audio: how models see, hear and generate |
| 16 | Production & Ops | Deploying, observing, and costing LLM systems under real traffic |
| 17 | Classical ML | Tree ensembles, boosting, calibration: what still runs production tabular |
| 18 | Frontier & Esoterica | Training-dynamics anomalies and open problems |
| 19 | Ecosystem & History | Labs, model lineage, licensing, and the field's war stories |

**The Applied Wing (domains 20–24):** where those models actually landed, and what that's worth.

| # | Domain | Scope |
|---|--------|-------|
| 20 | AI in Software Engineering | What coding tools measurably do; where the RCTs agree and contradict |
| 21 | AI Across Business Functions | Where GenAI shipped across support, legal, health, finance, and what happened |
| 22 | AI Economics | Value capture, unit economics, pricing, moats |
| 23 | Adoption & Blockers | Why ~95% of enterprise pilots never reach production, mechanism by mechanism |
| 24 | Trajectory & Navigation | Capability and cost trajectories separated from vendor forecasting |

## The quality system

A written constitution (`_SYSTEM/STANDARDS.md`) governs the vault, and tooling enforces it:

- **13 note types with fixed skeletons:** MOC, Ladder, Concept, Deep Dive, Breakdown, Pattern, Playbook, Decision, Gotchas, Checklist, Snippet, Reference, Lore. A note's type tells you its shape before you open it.
- **The Linking Law:** every note carries a minimum number of resolved links (12 for a Deep Dive, 8 for a Concept, down to 4 for a Reference), links into at least two other domains, and links up and down its ladder. `_SYSTEM/tools/linkcheck.py` checks the whole graph: zero broken links, zero orphans, zero violations.
- **The Evidence Law (domains 20–24):** every empirical claim carries a tier (E3 independently verified → E0 speculation), a named source and a date. Vendor numbers are flagged as vendor numbers. No invented case studies.
- **Temporal honesty:** fast-moving claims are date-stamped *(as of YYYY)*. Vault knowledge is current as of **mid-2026**. The notes that age fastest say so, and expect to be wrong within 6–12 months on cost and reliability figures. Check dates before quoting.
- **Banned:** listicle framing, motivational filler, unexplained superlatives, untiered vendor numbers, padding. A section has mechanism, numbers, failure modes and named sources, or it gets deleted.

## Getting started

```
git clone <this-repo>
```

Open the folder as a vault in [Obsidian](https://obsidian.md) (free, no plugins required). Start at `00 - Home/Home.md`, then browse by domain MOC or take one of the guided ladders:

- **Ladder: Zero to Inference Engineer.** Matmul arithmetic to tuning production LLM serving.
- **Ladder: Zero to Pretraining Engineer.** Backprop to babysitting a multi-thousand-GPU run.
- **Ladder: Zero to Post-Training Engineer.** KL divergence to catching reward hacking before it ships.
- **Ladder: Zero to AI Application Engineer.** Prompting to shipping LLM products that survive real traffic.
- **Ladder: Zero to Interpretability Engineer.** The residual stream to SAEs and activation patching.
- **Ladder: Zero to Multimodal Engineer.** ViT and CLIP through VLMs, diffusion and audio.
- **Ladder: Navigating the AI Economy.** A nineteen-step walk through what AI is actually worth.

The notes are plain Markdown, so everything reads fine on GitHub. But `[[wikilinks]]` only resolve inside Obsidian (a link target is always a note's filename), and the graph view is half the point. Use Obsidian if you can.

## Repository layout

```
00 - Home/            Entry point, orientation, and the guided ladders
01–19 …/              Engineering Wing domains
20–24 …/              Applied Wing domains
_SYSTEM/
  STANDARDS.md        The constitution: note types, linking law, style, evidence law
  NOTE_REGISTRY.md    The link contract — every valid wikilink target, by domain
  RESEARCH_PLAN.md    Domain ownership boundaries (one topic, one owning domain)
  PROGRESS.md         Build history and current state
  inventories/        Frozen per-domain note specs the vault was built from
  tools/linkcheck.py  Graph verifier — run after any note change, expect all zeros
```

## Contributing

Issues and PRs are welcome. The constitution sets the bar: a new or changed note must follow its type's skeleton in `_SYSTEM/STANDARDS.md`, be registered in `_SYSTEM/NOTE_REGISTRY.md`, be linked from its domain MOC plus at least one non-MOC note, and leave `python _SYSTEM/tools/linkcheck.py` reporting all zeros. Empirical claims in domains 20–24 need a tier, a named source and a date.

## License: free to learn from, not to sell

Copyright © 2026 Kade Heglin.

This entire repository (the notes, the system files and the tooling) is licensed under **[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-nc-sa/4.0/)** (CC BY-NC-SA 4.0). Full legal text in [LICENSE](LICENSE).

**You may**, without asking:
- Read, clone, and share the vault
- Adapt it, translate it, build your own vault on top of it, for **non-commercial** purposes
- …provided you give attribution (name + link back to this repository) and release any adaptation under this same license

**You may not**, without separate written permission:
- Sell access to this vault or any derivative of it
- Repackage the content into paid courses, books, newsletters, subscription products, or paid apps
- Bundle it into a commercial product or service, or otherwise use it commercially

ShareAlike means the non-commercial restriction travels with every fork and adaptation. You can't relicense a derivative to strip it. For commercial licensing, open an issue on this repository.
