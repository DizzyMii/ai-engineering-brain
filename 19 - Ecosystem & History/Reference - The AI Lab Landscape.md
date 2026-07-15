---
tags: [reference, domain/ecosystem-history, level/core]
aliases: [AI Lab Landscape, Frontier Labs, Foundation Model Providers]
summary: "The organizations building frontier and open models — funding, focus, and strategic posture, as of 2026."
---

# Reference - The AI Lab Landscape

## Frontier-closed labs

| Lab | Backing | Flagship / focus | Posture |
|---|---|---|---|
| OpenAI | Microsoft, ~$13B invested (as of 2026) | GPT/o-series, API platform | Platform-API |
| Anthropic | Amazon + Google backing | Claude, safety-differentiated | Safety-brand |
| Google DeepMind | Alphabet (2023 merger of Google Brain + DeepMind) | Gemini; owns its own TPU silicon | Vertically integrated |

## Open-weight majors

| Lab | Origin / notes | Flagship | Posture |
|---|---|---|---|
| Meta AI / FAIR | Yann LeCun as chief AI scientist | Llama | Commoditize-the-complement |
| Mistral | French, founded 2023 | Apache 2.0-licensed models | Sovereign/regional (EU) |
| xAI | Elon Musk, founded 2023 | Grok; Colossus cluster (100k+ H100s, Memphis) | Aggressive frontier-chaser |

## Chinese labs

| Lab | Notes |
|---|---|
| DeepSeek | Spun out of High-Flyer, a quantitative hedge fund (see [[Breakdown - DeepSeek]]) |
| Alibaba Qwen | Major open-weights contributor across sizes |
| Zhipu / GLM | |
| Moonshot / Kimi | |
| 01.AI (Yi) | |
| Baidu Ernie | |
| MiniMax | |

As a group, Chinese labs are increasingly setting the open-weights capability frontier rather than trailing it (as of 2026).

## Research and fully-open

| Org | Notes |
|---|---|
| EleutherAI | Nonprofit; GPT-Neo, Pythia |
| Allen Institute for AI (AI2) | OLMo — fully open data, code, and training logs |
| BigScience | BLOOM; the collaboration itself is defunct post-release (see [[Lore - The BLOOM Training Run]]) |

## Enterprise and niche

| Org | Focus |
|---|---|
| Cohere | RAG/enterprise |
| AI21 | |
| Databricks / Mosaic | DBRX |
| Stability AI | Image generation; near-collapse in 2024 |
| Reka | |
| Together / Fireworks | Inference-as-a-service |

## The acqui-hire / reverse-acquisition pattern

| Target | Acquirer | Year |
|---|---|---|
| Inflection | Microsoft | 2024 |
| Character.AI | Google | 2024 |
| Adept | Amazon | — |
| Windsurf | (contested/licensing saga) | — |

This structure — licensing the technology and hiring the core team rather than a straightforward acquisition — has recurred often enough as of 2026 to be read as a deliberate pattern for dodging antitrust review; the talent, not the corporate shell, is the asset being acquired.

## Strategic postures as the organizing lens

| Posture | Exemplar | Logic |
|---|---|---|
| Platform-API | OpenAI | Monetize the API layer directly |
| Safety-brand | Anthropic | Differentiate on trust and alignment |
| Commoditize-the-complement | Meta | Open weights devalue rivals' model moat while Meta monetizes the layer above (ads, apps) |
| Sovereign/regional | Mistral, Falcon (UAE) | Soft power and strategic independence from US/Chinese models |
| Efficiency-challenger | DeepSeek | Undercut incumbents on training/inference cost rather than compete on raw scale |

## Compute as the barrier to entry

Frontier-lab viability increasingly tracks compute access more than research headcount — the GPU-rich/GPU-poor divide (see [[Reference - The AI Hardware Market]]) determines who can even attempt a frontier pretraining run, which is why hyperscaler-backed or hyperscaler-owned labs (OpenAI/Microsoft, Anthropic/Amazon+Google, Google DeepMind's own TPUs) dominate the closed tier while independently financed labs cluster around efficiency plays or open release strategies that trade compute for community leverage.

Date-stamp everything on this page: the roster, funding figures, and postures listed here churn on a roughly quarterly cadence (as of 2026).

## Connections
- [[Reference - Model Genealogy]] — the model lineages each of these organizations actually produces.
- [[Concept - The Open vs Closed Model Divide]] — the strategic logic behind why a given lab in this table chose an open or closed release posture.
- [[Reference - The AI Hardware Market]] — the compute-supply side that gates which of these labs can run a frontier pretraining job at all.
- [[Breakdown - DeepSeek]] — a detailed case study of the efficiency-challenger posture and the market shock it produced.
- [[Breakdown - Hugging Face]] — the neutral distribution layer that every lab in this table, regardless of posture, ends up shipping through.
- [[Reference - Where Real AI Knowledge Lives]] — how to read what each of these labs actually publishes versus what they announce.
- [[Reference - AI Venture Funding Patterns]] — the capital dynamics behind the funding figures in the tables above.
- [[Breakdown - Frontier Lab Economics]] — the unit economics that explain why some postures (platform-API, safety-brand) are financially viable and others are not.
- [[Breakdown - The Google TPU]] — the concrete case of a lab (Google DeepMind) whose posture is enabled by owning its own accelerator silicon rather than depending on the merchant GPU market.
- [[Lore - The BLOOM Training Run]] — the counter-example: a fully-open lineage (BigScience/BLOOM) built outside any of the labs in this table, on grant-funded public compute.
