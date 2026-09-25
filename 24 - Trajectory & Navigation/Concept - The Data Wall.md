---
tags: [concept, domain/trajectory, level/core]
aliases: [Data Exhaustion, Training Data Scarcity, Peak Data]
summary: "High-quality text for pretraining is projected to run out ~2026-2032; the field is already routing around it via RL and synthetic data."
---

# Concept - The Data Wall

> **One-paragraph hook:** Scaling laws say bigger models need proportionally more training tokens. The data wall is the observation that the supply of tokens worth training on (deduplicated, quality-filtered, useful human text, not raw bytes) is finite and being consumed fast enough to run out this decade. Nobody has hit it yet. By 2026 it looks less like a hard stop than an economic pressure that pushed labs toward synthetic data, RL and other levers years before the stock would literally run out.

## The mechanism

[[Concept - Scaling Laws|Compute-optimal scaling]] sets a ratio between model parameters and training tokens for a fixed compute budget. Frontier labs draw that many tokens from a large but finite pool of public human-generated text: web crawls, books, code, forums. Epoch AI's modeling puts the effective stock, after quality filtering and repetition adjustment, at roughly 300 trillion tokens (E1/E2, Villalobos et al., "Will We Run Out of Data?", 2022, revised 2024). At compute-optimal consumption, that stock runs out somewhere between 2026 and 2032 (Epoch's 80% confidence interval). The point estimate for compute-optimal exhaustion (a training run needing ~5×10^28 FLOP) lands around 2028 in Epoch's latest revision (E1, a model-based estimate, not a measurement). The number has already moved once: from a 2022 estimate of ~2024 exhaustion to the current ~2028, after Epoch found web data filters better than assumed and revised the usable stock up 5x.

It's a quality wall, not a byte wall. The raw byte count of text online is enormous and growing. What runs low is the *usable* fraction left after [[Concept - Deduplication at Scale|deduplication]] and quality filtering strip spam, boilerplate, near-duplicates and low-information text. The exhaustion estimate is about the high-quality fraction already being tapped: curated web text, books, code, well-formed long-form writing. So "more internet gets created every day" doesn't rebut the data wall. Most of that new volume fails the quality filter behind the original 300T-token estimate.

Overtraining speeds it up. Chinchilla-optimal scaling minimizes loss for a fixed compute budget, but production models are more and more often trained past that point on purpose, because a smaller model trained on far more tokens is cheaper to serve even though it costs more to train. The Llama-3 family is the visible example. Overtraining uses up the token stock faster than compute-optimal scaling would for the same final capability, pulling the exhaustion date earlier than a naive Chinchilla-ratio projection (E2, Epoch AI analysis tying overtraining trends to stock depletion).

## In practice

**The escape routes, and where they honestly stand in 2026:**

- **Synthetic data** ([[Concept - Synthetic Training Data]]): generating training text with existing models instead of sourcing it from humans. It works in domains with checkable ground truth (math, code), where a model can generate and verify. In open-ended domains with no verifier, errors compound across generations and model collapse is a real risk. Status as of 2026: it carries a lot of the math/code capability gains and is still risky as a wholesale replacement for a pretraining corpus.
- **Multimodal data:** image, video and audio tokens add raw volume, but their value per token for language capability is unproven. Multimodal pretraining mostly buys multimodal capability, not a clean substitute for exhausted text.
- **RLVR / reasoning training** ([[Concept - GRPO and RL with Verifiable Rewards]]): arguably the most consequential response, and more a bottleneck shift than a fix. The constraint moves from human-written *text* to the number of verifiable *environments and tasks* an RL loop can run against. That's a large part of why 2024-2026 frontier gains visibly moved from "more pretraining" to "more post-training RL". Reasoning models (o1/o3-class, Claude's extended-thinking line) get much of their improvement from RL on verifiable problems, not from a bigger pretraining corpus.

**Why it's contested.** Villalobos and Epoch hold that better filtering and synthetic/RL routes have shifted the *timeline* without resolving the underlying scarcity: the wall is still there, later and less binding than the 2022 estimate implied. Skeptics of its near-term relevance point out that essentially all visible 2024-2026 frontier gains came from post-training and RL, not bigger pretraining runs. To them that means the field is already routing around the wall, which makes the pretraining exhaustion date less decision-relevant than it looked in 2022-2023 (E1, both positions; name the disagreement, don't resolve it artificially).

## Failure modes

**Treating "300 trillion tokens" as a hard, measured number.** It's Epoch's model output, built on assumptions about what counts as quality text and how aggressively it can be deduplicated. The estimate already moved 5x between the 2022 and 2024/2026 revisions from a filtering-methodology change alone. Any date derived from it (2026, 2028, 2032) needs the same "model, not measurement" caveat, per STANDARDS §8's E1 handling.

**Conflating the data wall with a capability wall.** Running out of cheap pretraining tokens doesn't stop capability improving. It removes the *cheapest* lever (add more of the same data) and pushes spend toward synthetic pipelines, RL environments and multimodal data, each harder and more expensive to scale than crawling more web text. The 2024-2026 shift toward RL-heavy training shows the field found other levers. It doesn't show the wall was fictional.

**Assuming synthetic data is a free substitute.** Synthetic data from a model trained on the same underlying distribution can amplify that model's errors and biases instead of adding information, the failure mode the literature on repeated synthetic-data training loops calls model collapse. It works in verifiable domains and is a real risk elsewhere. The mistake is treating it as an unlimited free replacement for human text, not using it.

## The non-obvious

By 2026 the data wall bites economically, not physically. Training doesn't stop. The cheapest scaling lever ("just add more of the data you already have") goes away, and the marginal capability dollar moves to costlier, harder-to-scale alternatives: [[Deep Dive - The AI Compute Buildout|compute]], synthetic-data pipelines that need careful quality control, and RL environments that each have to be designed and verified. That reallocation is a large part of why frontier lab spend and the infrastructure buildout accelerated when they did. The buildout partly bets that compute and RL/synthetic-data engineering can replace the token supply that used to come free with a bigger web crawl ([[Breakdown - Frontier Lab Economics]] shows what that costs). Reading "data wall" as "AI progress will plateau" misses that the field priced this in years before the literal exhaustion date and moved its spending. The wall changed *where the money goes*, not whether progress continues.

It also makes proprietary data, anything outside Epoch's public 300T-token stock, more valuable as the public commons thins. That's why it appears as a durable moat in [[Concept - What Stays Valuable Through Any Scenario]]. The same proprietary data is the asset [[Concept - Data and Integration Readiness]] treats as a precondition for enterprise deployment, so the data wall is one more reason an enterprise's own clean, integrated data keeps gaining value.

This is one of several mechanisms, not the only one, that could bend the trajectory everyone else is extrapolating. The [[Concept - The AGI Timeline Debate|long/skeptic camp]] names it as a reason to doubt continued scaling-driven compression. It's a live input to whether current infrastructure capex is justified in [[Deep Dive - Bubble or Boom]]. And it could bend the agentic-capability curve in [[Concept - METR Time Horizons]] if RL and synthetic data don't fully substitute for pretraining scale. Epoch's own estimate moving from ~2024 to ~2028 between revisions says something about how fast model-based projections like this move ([[Reference - The AI Forecasting Track Record]] covers how much to discount it), and "does the data wall bind?" stays an open, tracked question in [[Reference - The Open Questions Ledger]].

## Connections
- [[Concept - METR Time Horizons]] — one of the trajectory signals whose forward extrapolation could bend if the data wall (rather than RL/synthetic routing around it) turns out to bind.
- [[Deep Dive - The AI Compute Buildout]] — the physical buildout is partly a hedge against the data wall: substituting compute and RL-environment engineering for the cheap-data lever that's running out.
- [[Deep Dive - Bubble or Boom]] — the data wall is one of the structural questions bearing on whether current capex is justified by continued capability gains.
- [[Concept - The AGI Timeline Debate]] — a candidate mechanism (per the long/skeptic camp) for why scaling-driven timeline compression might not continue linearly.
- [[Breakdown - Frontier Lab Economics]] — where the reallocation from "buy more data" to "buy more compute and RL engineering" shows up in actual lab spend.
- [[Reference - The Open Questions Ledger]] — "does the data wall bind" is tracked there as one of the live, unresolved trajectory questions.
- [[Concept - What Stays Valuable Through Any Scenario]] — proprietary data is named there as a durable moat precisely because the public data wall makes it scarcer and more valuable by contrast.
- [[Reference - The AI Forecasting Track Record]] — Epoch's own revision of its exhaustion date (2024 estimate → 2028 estimate) is itself a data point on how fast these model-based projections move.
- [[Concept - Scaling Laws]] — the compute-optimal token/parameter ratio that defines how fast a training run consumes the token stock in the first place.
- [[Concept - Synthetic Training Data]] — the primary proposed escape route, with its own collapse risk.
- [[Concept - Deduplication at Scale]] — the filtering step that turns "raw internet bytes" (effectively unlimited) into "usable high-quality tokens" (the actually scarce quantity this note is about).
- [[Concept - GRPO and RL with Verifiable Rewards]] — the mechanism that shifted the bottleneck from pretraining-text volume to verifiable-environment supply, arguably the most consequential real-world response to the wall as of 2026.
- [[Concept - Data and Integration Readiness]] — the proprietary-data moat this note flags as increasingly valuable is exactly the enterprise data asset that concept treats as a deployment precondition (cross-domain: adoption).

## Sources
- Villalobos, Sevilla, et al. / Epoch AI (2022, revised 2024) — *Will We Run Out of Data? Limits of LLM Scaling Based on Human-Generated Data*. The ~300T-token stock estimate and the 2026-2032 exhaustion window (80% CI), revised from an earlier ~2024 estimate.
- Epoch AI — ongoing tracking of compute-optimal training-run FLOP and the implied exhaustion date (~2028 point estimate as of the most recent revision).
- Hoffmann et al. (2022) — *Training Compute-Optimal Large Language Models* (Chinchilla). The parameter/token ratio the data wall's consumption-rate math is built on.
