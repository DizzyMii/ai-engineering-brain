# STANDARDS — The Constitution of This Brain

Every note in this vault is written against this document. Agents: read this file completely before writing anything. Deviation from these standards is a defect.

---

## 1. Prime Directive — The Quality Contract

This vault contains **real AI engineering knowledge**: mechanisms, numbers, failure modes, and tribal knowledge. It is written for someone building, training, serving, and debugging AI systems — not someone reading about them.

**The test for every note:** *Would a staff-level ML engineer at a frontier lab either learn something or nod in recognition? If the note could have been generated from a LinkedIn post or a "Top 10 Tips" listicle, it fails and must be rewritten.*

### Required in every note
- **Mechanism, not description.** Explain *why* something works or fails, down to the math, memory layout, or gradient flow where relevant. "FlashAttention is faster" is banned; "FlashAttention tiles the attention computation to keep the working set in SRAM, avoiding O(N²) HBM reads of the score matrix" is the floor.
- **Numbers.** Real constants, formulas, magnitudes: bytes per parameter, tokens per dollar, typical learning rates, memory formulas, latency budgets, dates. If a claim can be quantified, quantify it.
- **Failure modes.** What breaks, how it looks when it breaks, and how you'd detect it. Every mechanism note carries its pathology.
- **At least one non-obvious insight** — the thing practitioners learn the hard way. If you can't name one, you haven't gone deep enough.
- **Named sources.** Papers with first-author and year (e.g., "Chinchilla — Hoffmann et al. 2022"), real systems (vLLM, Megatron-LM), real incidents (OPT-175B logbook). No vague "studies show."

### Banned
- Listicle framing ("Top N ways to…"), engagement-bait headers, motivational filler.
- "In today's rapidly evolving AI landscape…" and every cousin of it.
- Unexplained superlatives ("powerful", "game-changing", "seamless").
- Vendor marketing claims repeated without mechanism or measurement.
- Hedging every sentence into mush. Take positions; mark genuine uncertainty explicitly ("open question:", "folklore, weakly sourced:").
- Padding. If a section has nothing real to say, delete the section.

### Temporal honesty
Knowledge is current as of **mid-2026**. Fast-moving claims (SOTA, pricing, "best model for X") must be date-stamped inline: *(as of 2026)*. Timeless mechanisms (backprop, roofline math) need no stamp.

---

## 2. The Ladder — Five Levels

Every note carries exactly one level tag. The vault must be traversable from any level to the adjacent ones via links.

| Level | Tag | Meaning |
|---|---|---|
| Surface | `level/surface` | What it is, why it exists. Entry point for a smart generalist. |
| Core | `level/core` | Working knowledge. What every practitioner must know to use it. |
| Advanced | `level/advanced` | Internals. What you need to debug, optimize, or implement it. |
| Frontier | `level/frontier` | Active research edge, recent techniques, open problems. |
| Unicorn | `level/unicorn` | Tribal knowledge, folklore, war stories, arcana almost nobody writes down. |

---

## 3. Content Types — One Format Per Kind of Knowledge

Each kind of knowledge has exactly one home format. **Choosing the type:**

| The knowledge is… | Type | Prefix |
|---|---|---|
| A mechanism or idea (atomic) | Concept | `Concept - ` |
| A mechanism too big for one Concept (system-level treatment) | Deep Dive | `Deep Dive - ` |
| A reusable engineering design you can apply to new systems | Pattern | `Pattern - ` |
| An end-to-end operational procedure (do X from start to finish) | Playbook | `Playbook - ` |
| A pre-flight verification list | Checklist | `Checklist - ` |
| Known pitfalls for a subsystem, aggregated | Gotchas | `Gotchas - ` |
| Runnable code demonstrating one technique | Snippet | `Snippet - ` |
| A lookup table, formula sheet, or comparison matrix | Reference | `Reference - ` |
| A choice between alternatives with real tradeoffs | Decision | `Decision - ` |
| How a real system/model/paper actually works, reverse-engineered | Breakdown | `Breakdown - ` |
| War stories, history, folklore, tribal narrative | Lore | `Lore - ` |
| A map of a domain's notes | MOC | `MOC - ` |
| A guided learning path through the vault | Ladder | `Ladder - ` |

### 3.1 Concept — the atomic unit
```markdown
# Concept - <Name>
> **One-paragraph hook:** what this is and why an engineer cares. No fluff.

## The mechanism
How it actually works. Math, pseudocode, memory layout, gradient flow — whatever the substrate is. This is the heart of the note.

## In practice
Concrete usage: real configs, real numbers, real systems that use it, typical values and why.

## Failure modes
What breaks, symptoms, detection, remedies.

## The non-obvious
≥1 insight practitioners learn the hard way.

## Connections
- [[Exact Note Title]] — one line on *why* this link matters.
(see §5 Linking Law for minimums)

## Sources
- Author et al. (Year) — Paper title. One line on what it contributes.
```

### 3.2 Deep Dive — extended treatment
Same skeleton as Concept but with a mandatory **## Architecture / walkthrough** section (step-by-step trace through the full system, with a diagram — Mermaid or ASCII) and **## Evolution** (how the technique developed; what it replaced and what's replacing it). Length: whatever the mechanism demands; no padding.

### 3.3 Pattern — reusable design
```markdown
# Pattern - <Name>
> **Problem:** the recurring situation. **Solution shape:** one sentence.

## Context & forces
When this applies; the constraints in tension.

## The pattern
Structure, components, data flow. Diagram (Mermaid/ASCII) required.

## Implementation notes
Concrete guidance, key parameters, real systems using it.

## Tradeoffs & when NOT to use
Costs, alternatives, breakdown conditions.

## Known uses
≥2 real systems.

## Connections / ## Sources
```

### 3.4 Playbook — operational procedure
```markdown
# Playbook - <Name>
> **Goal / When to run this / Prerequisites** — three lines.

## Steps
Numbered, imperative, each with: action → expected observation → what deviation means.

## Verification
How you know it worked.

## When it goes wrong
Branch table: symptom → likely cause → jump to fix.

## Connections / ## Sources
```

### 3.5 Checklist — pre-flight
Flat `- [ ]` list grouped by stage. Each item is one atomic check, phrased so an agent or human can verify it objectively. End with **## Why these items** — one line per non-obvious item explaining the incident that put it on the list. Connections section required.

### 3.6 Gotchas — subsystem pitfalls
```markdown
# Gotchas - <Subsystem>
One `##` per gotcha, ordered by how much pain it causes:
## <N>. <Symptom-first title, e.g. "Loss spikes at exactly the LR warmup boundary">
**Symptom:** what you observe. **Cause:** the mechanism. **Fix:** the remedy. **Detection:** how to catch it early.

## Connections / ## Sources
```

### 3.7 Snippet — runnable code
One technique per snippet. Complete and runnable (imports included), minimal (no framework ceremony), commented only where the code can't speak. Header block states: what it does, dependencies + versions, expected output. Then the code. Then **## Why it's written this way** — the 2-4 decisions in the code that encode expertise. Connections section required.

### 3.8 Reference — lookup
Tables and formulas, front-loaded. No prose introductions — a Reference is opened mid-task. Every table column with a non-obvious unit gets a footnote. Date-stamp volatile data per table. Connections section required.

### 3.9 Decision — choice framework
```markdown
# Decision - <Choosing X>
> The decision in one sentence, and the default answer for the 80% case.

## Decision flow
Mermaid flowchart of the actual decision logic.

## Tradeoff matrix
Options × criteria table with real numbers where possible.

## The details that flip the decision
The edge cases where the default is wrong.

## Connections / ## Sources
```

### 3.10 Breakdown — reverse-engineered system
```markdown
# Breakdown - <System/Model/Paper>
> What it is, who built it, why it matters. Date-stamped.

## The headline numbers
Scale, cost, performance — the quantitative identity card.

## How it actually works
The full architecture/method walkthrough. Diagram required.

## The clever parts
The 3-6 decisions that make it interesting — each with the mechanism and why alternatives lost.

## What it got wrong / what's dated
Honest assessment.

## What to steal
What transfers to your own systems.

## Connections / ## Sources
```

### 3.11 Lore — narrative knowledge
War stories, folklore, history. Format: **## What happened** (the story, told properly — narrative is the format here), **## The lesson** (what it teaches, mechanically), **## Evidence status** (verified / well-sourced folklore / unverifiable legend — be honest). Connections section required.

### 3.12 MOC — map of content
One per domain folder. Lists **every** note in the domain, grouped by sub-topic, each entry with a one-line hook. Opens with a 3-5 sentence orientation to the domain and a **"Start here"** pointer per level (surface → unicorn). Links to adjacent domain MOCs.

### 3.13 Ladder — learning path
An ordered walk through existing notes from surface to unicorn for one track (e.g., "Ladder - Zero to Inference Engineer"). Each step: the note link + what to extract from it + a self-test question. Ladders link only to existing notes; they create no new content.

---

## 4. Frontmatter

Every note begins with exactly this shape:

```yaml
---
tags: [<type>, domain/<domain-slug>, level/<level>]
aliases: [<common alternative names, acronyms>]
summary: "<one line, ≤140 chars — used for search and hover previews>"
---
```

- `<type>` is the bare type name: `concept`, `deep-dive`, `pattern`, `playbook`, `checklist`, `gotchas`, `snippet`, `reference`, `decision`, `breakdown`, `lore`, `moc`, `ladder`.
- Domain slugs: `foundations`, `neural-networks`, `architectures`, `training-at-scale`, `data-engineering`, `post-training`, `inference-serving`, `hardware-systems`, `prompting-context`, `agents`, `retrieval-rag`, `fine-tuning`, `evaluation`, `safety-interp`, `multimodal`, `production-ops`, `classical-ml`, `esoterica`, `ecosystem-history`, `applied-software`, `applied-business`, `ai-economics`, `adoption-blockers`, `trajectory`, `home`.
- Aliases: include acronyms and paper nicknames (`aliases: [GQA, grouped-query attention]`) so search hits.

---

## 5. Linking Law — Everything That Can Connect, Must Connect

Connectivity is the point of this vault. A note that doesn't link is a defect, and a *possible* link left unmade is a defect.

1. **Exact-title links only.** Every `[[wikilink]]` must exactly match a title in `_SYSTEM/NOTE_REGISTRY.md`. Never invent a title. Never link to a note that isn't in the registry.
2. **Inline-link on first mention.** The first time a note mentions another registry topic, link it inline right there: "the [[Concept - KV Cache]] grows linearly with…".
3. **Connections section is mandatory** in every note (except it's implicit in MOC/Ladder). Every entry gets a one-line *why*. A bare link list is a defect.
4. **Minimum outgoing links** (registry-resolving, counting inline + Connections, deduplicated):

| Type | Min links |
|---|---|
| Deep Dive | 12 |
| Breakdown | 10 |
| Concept | 8 |
| Pattern, Playbook, Decision, Gotchas | 6 |
| Checklist, Snippet, Reference, Lore | 4 |

5. **The ladder rule.** Every note links **down** to ≥1 prerequisite (lower level) and, unless nothing deeper exists, **up** to ≥1 deeper note. Surface notes need no down-link; unicorn notes need no up-link.
6. **The lateral rule.** Every note links to notes in **≥2 other domains**. Cross-domain connections are the highest-value links in the vault — favor them over easy same-domain links.
7. **No orphans.** Every note must be linked from its domain MOC (guaranteed in Phase 4) and *should* be linked from ≥1 non-MOC note.
8. **Link the seams.** Where a topic touches its neighbors (quantization ↔ GPU memory ↔ serving cost; RLHF ↔ reward hacking ↔ evals), the notes on both sides link each other with the *why* stated. One-directional awareness is a defect.

---

## 6. Naming

- Filename = note title = `<Type Prefix> - <Name>.md`. Unique across the whole vault.
- Names use the term of art, not a description: `Concept - Speculative Decoding`, not `Concept - Making Inference Faster With Draft Models`.
- Acronyms expanded in the title if obscure, in aliases if common: `Concept - Grouped-Query Attention` with alias `GQA`.

---

## 7. Style

- **Voice:** direct, technical, opinionated where evidence supports it. Written by an engineer for an engineer.
- **Math:** LaTeX (`$...$` inline, `$$...$$` display) when it clarifies; define symbols on first use.
- **Code:** fenced blocks with language tags. Pseudocode is fine when real code would be ceremony.
- **Diagrams:** Mermaid fenced blocks (Obsidian renders them) or tight ASCII. Required where noted in type formats.
- **Length:** as long as the mechanism demands, no longer. A Concept is typically 400–1200 words of substance; a Deep Dive 1200–3000. Hitting minimum length is never a goal.
- **Tables** for enumerable facts; prose for reasoning. Never a table of vague adjectives.

---

## 8. The Applied Wing — Evidence Law (domains 20–24)

Domains 20–24 record where AI has actually been deployed, what it measurably did, what it costs, what blocks it, and where it is headed. The §1 quality test adapts: *would a sharp operator, investor, or staff engineer deciding where to deploy AI either learn something or nod in recognition?* Everything else in this constitution still applies; these rules are additive.

**Every empirical claim** (a $ figure, %, headcount, adoption rate, outcome) **carries an evidence tier, a named source, and a date:**

| Tier | Meaning | Handling |
|---|---|---|
| E3 | Independently verified — RCT/controlled study, court or regulatory record, audited filing, or multiple independent sources | State as fact, cite |
| E2 | Single credible primary source — a company's own claim, one study, one reporter | State with an explicit "(company-claimed)" / "(single study)" marker |
| E1 | Analyst estimate or extrapolation — consultancy projections, market sizing, modeled ROI | Attribute to the estimator; never launder into fact |
| E0 | Speculation, vibes, unsourced folklore | Only as a labeled open question or scenario; never load-bearing |

- Inline form: `saved ~$40M/yr (E2, Klarna's own claim, 2024 — later softened, see below)`.
- **Contested claims name the counter-evidence in the same breath.** A walked-back, disputed, or failed-replication claim presented clean is a defect.
- **Forecasts are E1 at best.** Name the forecaster, their date, and their track record where known. Divergent credible forecasts are presented as a spread, never averaged into mush.
- **Vendor and consultancy numbers never appear untiered.** "McKinsey says $4.4T" is E1 and says so.
- Per §1 Temporal honesty, in this wing essentially every number is fast-moving: date-stamp it.
- **No invented case studies.** If a deployment can't be tied to a named company, product, or study, it does not go in a Breakdown or Lore note. Composite or hypothetical examples are banned in this wing.
