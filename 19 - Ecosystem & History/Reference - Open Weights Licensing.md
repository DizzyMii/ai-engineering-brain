---
tags: [reference, domain/ecosystem-history, level/core]
aliases: [Model Licensing, OSAID, Open Source AI Definition, RAIL License, OpenRAIL]
summary: "What Apache 2.0, MIT, the Llama Community License, and RAIL/OpenRAIL actually permit and restrict for model weights."
---

# Reference - Open Weights Licensing

## License comparison matrix

| License | OSI-approved | Example models | Commercial use | Redistribution | Fine-tune / derivatives | Train other models on outputs | Notable restriction |
|---|---|---|---|---|---|---|---|
| Apache 2.0 | Yes | Mistral 7B, Mixtral 8x7B, Qwen 2.5/3, [[Breakdown - Hugging Face]]-hosted OLMo | Unrestricted | Unrestricted | Unrestricted | Unrestricted | Includes an explicit patent grant; no field-of-use clause at all |
| MIT | Yes | DeepSeek-R1 (Jan 2025), DeepSeek-V3 weights | Unrestricted | Unrestricted | Unrestricted | Unrestricted | No patent grant (unlike Apache 2.0); otherwise as permissive as it gets |
| Llama Community License | No | Llama 2 (Jul 2023), Llama 3/3.1 405B (2024), Llama 4 (2025) | Yes, until >700M monthly active users | Yes, with "Built with Llama" attribution | Yes | Llama 2's text explicitly barred using outputs to improve *non-Llama* LLMs; later versions loosened this but retain an Acceptable Use Policy | The >700M-MAU clause forces the largest hyperscalers to negotiate a separate deal with Meta: a moat dressed as a license |
| Gemma Terms of Use | No | Gemma 2, Gemma 3 (Google) | Yes | Yes | Yes | Restricted by a prohibited-use policy | Custom terms, revised across versions; naming and attribution requirements |
| BigScience OpenRAIL-M | No | BLOOM (Jul 2022) | Yes | Yes | Yes | Yes | Behavioral-use restrictions written into the license itself (no medical diagnosis without professional oversight, no law-enforcement facial recognition, etc.) |
| Falcon License (pre-2023) → Apache 2.0 (2023+) | No → Yes | Falcon 40B (original 10%-royalty-above-$1M-revenue term) → later Falcon releases | Restricted → Unrestricted | Restricted → Unrestricted | Restricted → Unrestricted | Restricted → Unrestricted | TII's move to Apache 2.0 is the field's clearest case of a lab abandoning a custom-restrictive license for true-open |

*Pin every row to an exact release.* Llama 2, 3, and 4 carry materially different terms under the same family name, so "Llama's license" isn't one thing.

## Open weights vs. open source vs. open data

| Term | What's actually released | Example |
|---|---|---|
| Open weights only | Model weights (+ a technical report) | Most Llama-family and Grok releases |
| "Open source" (loosely used) | Weights + inference/training code, but not the raw corpus | Most Hugging Face instruct releases that claim this label |
| Fully open | Weights + code + the training corpus and logs | OLMo ([[Reference - The AI Lab Landscape|AI2]]), Pythia (EleutherAI), BLOOM's ROOTS corpus (partial) |

These are independent axes, not a spectrum. A model can have maximally open weights (MIT) and disclose zero data (DeepSeek), or the reverse (a research release under a restrictive academic license with a fully public corpus).

## The OSAID fight

The Open Source Initiative's Open Source AI Definition (OSAID 1.0, Oct 2024) requires "sufficient" disclosure of training data composition (provenance, characteristics, and how to obtain or reconstruct it) before a model can be called open source. Meta disputes it because Llama meets none of it: no data disclosure, a behavioral Acceptable Use Policy, and the MAU clause. By OSAID's letter, *no major "open" LLM from a commercial lab currently qualifies as open source*. Only data-transparent research releases like OLMo and Pythia do. The definitional fight is active and unresolved as of 2026, and "open" on a model card and "open" per OSAID are different claims.

## Enforceability reality

A license is a promise you can enforce against a counterparty who signed up to it, usually a company with lawyers, revenue and a reputation. It does nothing against an anonymous BitTorrent seed. Once weights leak (see [[Lore - The LLaMA Leak]]), the license still governs *reputable* downstream commercial use, but the leaked copy can't be recalled or traced. So licenses work less as technical access control and more as a liability perimeter around companies willing to be sued.

## The checklist a lawyer actually runs

- Can you commercialize the model (sell a product built on it) without a separate agreement?
- Can you redistribute the weights, fine-tuned or not?
- Can you fine-tune, and does the license claim any rights over your fine-tuned derivative?
- Can you train *other* models on this model's outputs, or does the ToS forbid distillation?
- Is there a user-count cap (Llama's 700M MAU), a field-of-use restriction (RAIL's behavioral clauses), a geographic restriction, or a naming/attribution requirement?
- Which exact version and date does the license text apply to?

[[Checklist - Vetting an Open-Weights Model for Production]] has the full production go/no-go; licensing is one stage of it.

## Connections
- [[Concept - The Open vs Closed Model Divide]] — licensing is the legal instrument; this note's companion explains the strategic *why* labs choose one posture over another.
- [[Reference - Model Genealogy]] — license terms travel with lineage; a distilled or merged model can inherit restrictions from an ancestor.
- [[Lore - The LLaMA Leak]] — the canonical proof that license enforceability collapses once weights are public.
- [[Checklist - Vetting an Open-Weights Model for Production]] — licensing is stage one of the production adoption checklist this note feeds.
- [[Decision - Which Model Ecosystem to Bet On]] — licensing risk (MAU caps, geographic bans) is a direct input to the ecosystem-selection decision.
- [[Lore - The BLOOM Training Run]] — BLOOM is the flagship case of the RAIL license in the wild, including the governance process behind it.
- [[Concept - Copyright and Licensing of Training Data]] — a model's weight license and its underlying training-data copyright status are separate legal questions that get conflated in practice.
- [[Reference - AI Copyright Litigation Tracker]] — active lawsuits are testing exactly how far these licenses' protections actually extend against copyright claims.
- [[Reference - Where Real AI Knowledge Lives]] — start here for how to find primary license texts and legal analysis rather than secondhand summaries.
- [[Breakdown - Hugging Face]] — the Hub is where nearly every license in this table is actually read (or skipped) by practitioners downloading a model.
- [[Reference - The AI Lab Landscape]] — which lab released a model predicts its license posture more reliably than the model's technical merits do.

## Sources
- Open Source Initiative — Open Source AI Definition (OSAID) 1.0, October 2024.
- Meta — Llama 2, 3, and 4 Community License Agreements and Acceptable Use Policy (published license text per release).
- BigScience — The BigScience OpenRAIL-M License (2022), the behavioral-use-restriction license accompanying BLOOM.
- Widder, West, and Whittaker (2023) — "Open (For Business): Big Tech, Concentrated Power, and the Political Economy of Open AI," a critical analysis of what "open" buys commercial labs strategically.
