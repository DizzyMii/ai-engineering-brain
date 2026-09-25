---
tags: [lore, domain/production-ops, level/unicorn]
aliases: [model drift, silent model updates, GPT-4 got worse, provider deprecation]
summary: "War stories of provider model drift, silent alias updates, and deprecations breaking production — and the lesson each one teaches."
---

# Lore - When the Model Changed Under You

> Your app depends on a model you don't control, can't version and can't roll back. Sometimes it changes without telling you.

## What happened

**The "GPT-4 got worse" saga (mid-2023).** In summer 2023 the developer forums filled with people sure GPT-4 had been nerfed: lazier, more refusals, worse reasoning. OpenAI denied changing the model. Then Chen, Zaharia & Zou (2023, Stanford/Berkeley) published *How Is ChatGPT's Behavior Changing over Time?*, comparing the March-2023 and June-2023 snapshots of GPT-4 and GPT-3.5 on fixed tasks. The headline was startling. On an "is this number prime?" task, GPT-4's accuracy reportedly fell from ~97.6% in March to ~2.4% in June, while GPT-3.5 moved the other way. Chain-of-thought compliance and code formatting shifted too.

The paper was contested right away, and correctly. Critics, Narayanan and Willison among them, pointed out that the prime task used only actual primes. A model that had simply started answering "composite" by default, or stopped emitting the step-by-step reasoning the grader keyed on, would score near zero with no change in underlying capability. So the specific *magnitude* was a measurement artifact of instruction-following and formatting drift. It wasn't a raw reasoning collapse. The deeper claim survived the critique: **the thing behind a stable-looking name had measurably changed, and downstream systems felt it.**

**Silent alias repointing.** The quieter, more common version hits everyone who pins to a floating alias. `gpt-3.5-turbo` and `gpt-4-turbo` resolved to a "latest" snapshot that OpenAI advanced on its own schedule. Teams calling the bare alias woke up to different default verbosity, JSON formatting and refusal behavior, with **no deploy on their side**. Regex parsers that assumed a leading ```` ```json ```` fence broke, and few-shot prompts tuned to the old formatting degraded. [[Concept - Prompt Formatting and Sensitivity|Prompt formatting sensitivity]] ties a model's behavior to surface details, so a minor snapshot bump lands as a functional regression in the app even when benchmark scores are flat.

**Deprecation and sunset chaos.** The flip side of pinning: dated snapshots don't live forever. Providers publish deprecation notices and retirement dates (OpenAI's months-to-a-year sunset windows, Azure's GA/retirement calendar), and when a snapshot is retired you *have* to migrate, eval budget or not. Worst case is a fine-tune whose **base model is being sunset**. Re-pointing won't do. You have to re-tune, on the provider's clock and not yours.

**Persona and parameter drift.** Subtler still: provider-side changes to the hidden system prompt or default sampling parameters shift a model's persona, verbosity or willingness with no version bump at all. The model id stays the same and the vibe changes. This class is the hardest to prove and the easiest to talk yourself out of. That's why it goes in the same bucket as the reproducible cases: without a golden set you can't tell it from your imagination, or from ordinary [[Concept - Nondeterminism in Production LLM Serving|serving nondeterminism]].

## The lesson

Mechanically: **treat the model as an unstable third-party dependency, not a constant.** Everything in [[Concept - Model Lifecycle and Versioning|model lifecycle and versioning]] follows from that:

- **Pin dated snapshots** (`gpt-4o-2024-08-06`, not `gpt-4o`). A floating alias is a dependency with no lockfile.
- **Keep a golden canary set** and run it on a schedule against the live endpoint, diffing outputs by embedding similarity and judge score. That's the core loop of [[Concept - Production Monitoring and Drift Detection|drift detection]], and the only instrument that catches persona drift when the model id is pinned.
- **Diff continuously.** One run tells you nothing under nondeterminism; you're watching for a distribution shift over a window.
- **Budget engineering time for forced migrations.** Deprecation is a certainty, so put it on the roadmap. When the golden set flags a change, the [[Playbook - Incident Response for LLM Systems|incident runbook]] should already have a rollback-to-N-1 or model-swap lever wired up.

The question that matters in a war room: is this **nondeterminism** (per-request variance, benign), a **deploy on your side** (prompt/config change), or the **model changing under you** (provider-side)? Only a pinned snapshot plus a stored baseline lets you tell them apart. Without them every complaint turns into unfalsifiable folklore.

## Evidence status

- **Well-sourced, methodologically debated:** the Stanford/Berkeley "behavior change over time" paper is real and peer-discussed. Its specific accuracy numbers (the ~97.6% → ~2.4% prime figure) are a measured but contested artifact of formatting/instruction drift. Cite them *with* that caveat, never as clean evidence of capability collapse.
- **Well-documented, widely reproduced folklore:** alias-repointing breakage and deprecation-forced migrations show up in countless changelogs, provider deprecation pages and postmortems. Verified as a class, even where any single anecdote is second-hand.
- **Hardest to verify:** silent persona/parameter drift with no version bump. Real and frequently reported, but rarely provable without a pre-registered golden set, which is the tooling lesson above.

## Connections
- [[Concept - Model Lifecycle and Versioning]] — the discipline (pinning, registries, rollback) that this lore exists to motivate; the down-link into the how-to.
- [[Concept - Production Monitoring and Drift Detection]] — the canary-probe machinery that catches a silent model change in the act.
- [[Concept - Nondeterminism in Production LLM Serving]] — the benign per-request variance you must rule out before blaming a provider change.
- [[Playbook - Incident Response for LLM Systems]] — the runbook whose "quality regression" branch starts with a golden-set diff against a pinned snapshot.
- [[Concept - Prompt Formatting and Sensitivity]] — why a "minor" provider snapshot bump lands as a functional regression in prompt-tuned apps.
- [[Reference - Model Genealogy]] — the lineage/snapshot map that tells you what a floating alias currently resolves to, and what replaced a retired model.
- [[Lore - The OPT-175B Logbook]] — the training-side cousin: a raw record of a model changing under its own operators, day by day.
