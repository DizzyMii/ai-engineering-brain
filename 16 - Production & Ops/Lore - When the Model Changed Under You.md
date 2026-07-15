---
tags: [lore, domain/production-ops, level/unicorn]
aliases: [model drift, silent model updates, GPT-4 got worse, provider deprecation]
summary: "War stories of provider model drift, silent alias updates, and deprecations breaking production — and the lesson each one teaches."
---

# Lore - When the Model Changed Under You

> The load-bearing dependency of your app is a model you don't control, can't version, and can't roll back. Sometimes it changes without telling you.

## What happened

**The "GPT-4 got worse" saga (mid-2023).** In the summer of 2023 the developer forums filled with people insisting GPT-4 had been quietly nerfed — it had gotten lazier, refused more, reasoned worse. OpenAI denied changing the model. Then Chen, Zaharia & Zou (2023, Stanford/Berkeley) published *How Is ChatGPT's Behavior Changing over Time?*, comparing the March-2023 and June-2023 snapshots of GPT-4 and GPT-3.5 on fixed tasks. The headline result was startling: on a "is this number prime?" task, GPT-4's accuracy reportedly collapsed from ~97.6% in March to ~2.4% in June, while GPT-3.5 moved the opposite way. Chain-of-thought compliance and code formatting shifted too.

The paper was immediately, and correctly, contested. Critics (notably Narayanan and Willison) pointed out the prime task used only actual primes, so a model that had merely started answering "composite" by default — or stopped emitting the step-by-step reasoning the grader keyed on — would score near zero without its underlying capability changing at all. So the specific *magnitude* was a measurement artifact of instruction-following and formatting drift, not a raw reasoning collapse. But the deeper claim survived the critique intact: **the thing behind a stable-looking name had measurably changed, and downstream systems felt it.**

**Silent alias repointing.** The quieter, more common version happens to everyone who pins to a floating alias. `gpt-3.5-turbo` and `gpt-4-turbo` resolved to a "latest" snapshot that OpenAI advanced on their own schedule. Teams calling the bare alias woke up to changed default verbosity, changed JSON formatting, and changed refusal behavior — with **no deploy on their side**. Regex parsers that assumed a leading ```` ```json ```` fence broke; few-shot prompts tuned against the old formatting degraded. Because [[Concept - Prompt Formatting and Sensitivity|prompt formatting sensitivity]] means a model's behavior is entangled with surface details, a minor snapshot bump lands as a functional regression in the app even when the benchmark scores are flat.

**Deprecation and sunset chaos.** The flip side of pinning is that dated snapshots don't live forever. Providers publish deprecation notices and retirement dates (OpenAI's months-to-a-year sunset windows; Azure's GA/retirement calendar), and when a snapshot is retired you are *forced* to migrate whether or not you have the eval budget. The worst version: a fine-tune whose **base model is being sunset**, so re-tuning — not just re-pointing — is the only path forward, on the provider's clock, not yours.

**Persona and parameter drift.** Subtler still are provider-side changes to the hidden system prompt or default sampling parameters that shift a model's persona, verbosity, or willingness — with no version bump at all. Nothing in the model id changes; the vibe does. This is the hardest class to prove and the easiest to gaslight yourself out of, which is exactly why it belongs in the same bucket as the reproducible cases: without a golden set you cannot tell it apart from your own imagination, or from ordinary [[Concept - Nondeterminism in Production LLM Serving|serving nondeterminism]].

## The lesson

Mechanically: **treat the model as an unstable third-party dependency, not a constant.** Everything in [[Concept - Model Lifecycle and Versioning|model lifecycle and versioning]] follows from this single reframing:

- **Pin dated snapshots** (`gpt-4o-2024-08-06`, not `gpt-4o`). A floating alias is a dependency with no lockfile.
- **Keep a golden canary set** and run it on a schedule against the live endpoint, diffing outputs by embedding similarity and judge score — this is the core loop of [[Concept - Production Monitoring and Drift Detection|drift detection]], and it's the only instrument that catches persona drift even when the model id is pinned.
- **Diff continuously, not once.** A single run tells you nothing given nondeterminism; you're watching for a distribution shift over a window.
- **Budget engineering time for forced migrations.** Deprecation is a certainty, not a risk — put it in the roadmap. When the golden set flags a change, the [[Playbook - Incident Response for LLM Systems|incident runbook]] should already have a rollback-to-N-1 or model-swap lever pre-wired.

The distinction that matters in a war room: is this **nondeterminism** (per-request variance, benign), a **deploy on your side** (prompt/config change), or the **model changing under you** (provider-side)? Only a pinned snapshot plus a stored baseline lets you tell them apart — otherwise every complaint dissolves into unfalsifiable folklore.

## Evidence status

- **Well-sourced, methodologically debated:** the Stanford/Berkeley "behavior change over time" paper is real and peer-discussed; its specific accuracy numbers (the ~97.6% → ~2.4% prime figure) are a measured-but-contested artifact of formatting/instruction drift, and should be cited *with* that caveat, never as clean evidence of capability collapse.
- **Well-documented, widely-reproduced folklore:** alias-repointing breakage and deprecation-forced migrations are logged in countless changelogs, provider deprecation pages, and postmortems — verified as a class, even where any single anecdote is second-hand.
- **Hardest to verify:** silent persona/parameter drift with no version bump. Real, frequently reported, but rarely provable without a pre-registered golden set — which is precisely the tooling lesson above.

## Connections
- [[Concept - Model Lifecycle and Versioning]] — the discipline (pinning, registries, rollback) that this lore exists to motivate; the down-link into the how-to.
- [[Concept - Production Monitoring and Drift Detection]] — the canary-probe machinery that catches a silent model change in the act.
- [[Concept - Nondeterminism in Production LLM Serving]] — the benign per-request variance you must rule out before blaming a provider change.
- [[Playbook - Incident Response for LLM Systems]] — the runbook whose "quality regression" branch starts with a golden-set diff against a pinned snapshot.
- [[Concept - Prompt Formatting and Sensitivity]] — why a "minor" provider snapshot bump lands as a functional regression in prompt-tuned apps.
- [[Reference - Model Genealogy]] — the lineage/snapshot map that tells you what a floating alias currently resolves to, and what replaced a retired model.
- [[Lore - The OPT-175B Logbook]] — the training-side cousin: a raw record of a model changing under its own operators, day by day.
