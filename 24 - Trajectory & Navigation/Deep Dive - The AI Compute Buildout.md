---
tags: [deep-dive, domain/trajectory, level/advanced]
aliases: [AI Compute Buildout, Stargate, AI Data Center Buildout, Hyperscaler Capex]
summary: "The physical AI buildout: Stargate, hyperscaler capex, the power bottleneck, and whether it can be absorbed."
---

# Deep Dive - The AI Compute Buildout

> **One-paragraph hook:** The 2025-26 AI buildout is the largest infrastructure program in the history of computing — not measured in dollars alone but in gigawatts, in poured concrete, in grid interconnect queues. Where **[[Deep Dive - Bubble or Boom]]** asks whether the *money* pencils out, this note asks the physical question: can the electrons, the land, the high-bandwidth memory, and the permitting timelines actually deliver the compute the capital has already committed to? The binding constraint turns out not to be chips or money. It is power, and power moves on a clock the software industry has never had to respect.

## The mechanism — capex converts to compute converts to tokens

The buildout is a three-stage transduction with a very different time constant at each stage:

1. **Capital → facilities.** Committing money is fast (a press release). Pouring a GW-scale campus — land, substation, cooling, buildings — takes 18-36 months and is gated by grid interconnection, which in the US routinely runs multi-year.
2. **Facilities → compute.** Racking GPUs is fast *once power is live*; the gate is HBM and advanced-packaging (CoWoS) supply, not the logic die.
3. **Compute → revenue.** Tokens served must monetize. This is where the buildout meets **[[Concept - Token Price Deflation]]** and the demand question.

The mismatch in time constants is the whole story: **money commits in quarters, power arrives in years, revenue arrives... when it arrives.** The buildout therefore *front-runs* demand by design — foundations are poured now for compute that lands in 2026-27 for demand projected into the late 2020s.

## Architecture / walkthrough — Stargate and the numbers

**Stargate** is the flagship. Announced January 21 2025 (OpenAI, Oracle, SoftBank, MGX as equity funders; SoftBank financial lead, OpenAI operational lead), targeting **$500B over four years and up to 10GW** of capacity (E2, OpenAI + reporting — company-and-reported). By September 2025 the partners announced five new sites; the flagship **Abilene, Texas** campus was live on Oracle Cloud Infrastructure, and Oracle began delivering the first **Nvidia GB200 (Blackwell) racks in June 2025**. By mid-2026 the program reported ~7GW planned and ~$400B committed over three years, with the partners claiming they were on track for the full 10GW / $500B by end of 2025 (E2). *(Note: the roadmap points at next-generation Vera Rubin-class silicon for later phases, but as of mid-2026 the confirmed hardware on the ground is GB200 — treat "Rubin from 2026" as announced-not-delivered, E1.)*

Zoom out to the whole industry:

```
   CAPITAL                 PHYSICAL                    OUTPUT
   (quarters)              (years — the bottleneck)    (uncertain)
 ┌───────────┐   ~$650-    ┌────────────────────┐      ┌──────────┐
 │ Hyperscaler│──700B/yr──►│ Land + grid + power│─────►│ Tokens   │
 │ + Stargate │   2026     │ HBM/CoWoS + GPUs   │      │ served   │
 │ capex      │           │ cooling + buildings │      │ (~10x/yr?)│
 └───────────┘           └─────────┬──────────┘      └────┬─────┘
                                    │                       │
                          POWER = binding constraint    must monetize
                          (gas turbines, delayed coal    under deflation
                           retirements, nuclear PPAs)
```

**Scale of capex:** the top-4 US hyperscalers (Amazon, Microsoft, Alphabet, Meta) are on track for roughly **$650-700B combined capex in 2026** — Amazon ~$200B, Alphabet ~$175-185B, Meta ~$115-135B, Microsoft ~$120B+, with Oracle adding ~$50B — the majority AI-driven (E1/E2, analyst + company guidance, 2026). Combined hyperscaler capex rose from ~$256B (2024) to ~$443B (2025) to $600B+ (2026), a step-change no prior infrastructure cycle matched in absolute terms. Market-sizing of the demand this must serve is tiered per **[[Reference - AI Market Sizing Claims]]**.

## The clever/contested parts

**Power is the binding constraint, not chips (E2, reporting).** A single frontier training campus now draws on the order of a mid-size city — GW-scale. US grid interconnection queues stretch years; new high-voltage transmission takes longer still. Operators route around the grid: on-site natural-gas turbines, delayed coal-plant retirements, and long-term nuclear power-purchase agreements (including restarts and small-modular-reactor commitments). The consequence is that AI capability growth is now partly a function of *energy policy and permitting*, domains with no Moore's-law analog. This is the constraint that most cleanly bounds the **[[Concept - METR Time Horizons]]** extrapolations — a capability curve cannot outrun the megawatts feeding it.

**GPU depreciation is the accounting fault line (E1, contested).** Whether the buildout is *profitable* hinges on useful life. Book schedules of 5-6 years vs Michael Burry's argued 2-3 year real economic life (obsolescence per Nvidia generation + thermal wear at high utilization) swing reported margins by tens of billions per year. This is the shared crux with **[[Deep Dive - Bubble or Boom]]** and is developed as its own mechanism in **[[Concept - GPU Depreciation and Compute Capex Accounting]]**. If real life is shorter than book life, the buildout's reported returns are partly a depreciation-policy artifact.

**What must be true to absorb it (E1).** The buildout is a bet that tokens served keep ~10×-ing and that deflation drives demand faster than it erodes per-unit revenue — a Jevons bet. Deflation is *both* the demand engine and the pressure on unit revenue, which is why the absorption question is genuinely two-sided. If Jevons holds, the compute fills; if demand saturates, the same fixed costs sit idle at ~2-3yr obsolescence. The per-token economics live in **[[Concept - Unit Economics of LLM Products]]** and the operational discipline in **[[Concept - Cost Engineering for LLM Applications]]**.

**Constraints that could bend the curve (E1/E2):**
- Multi-year power and permitting timelines (above).
- HBM and CoWoS advanced-packaging supply — the true chip bottleneck is memory and packaging, not logic; this is where **[[Reference - Memory Math for Transformers]]** and **[[Concept - GPU Memory Hierarchy]]** meet macroeconomics.
- The **[[Concept - The Data Wall]]** shifting spend from pretraining toward inference and RL compute — changing *what kind* of compute the buildout needs to serve, not just how much.

## Failure modes

- **The demand air-pocket.** Because capital front-runs demand by years, a 12-18 month shortfall in monetized demand does not disprove the thesis but can trigger a *financial* unwind (impairments, halted projects) — timing risk, not thesis risk. This is the seam back to **[[Deep Dive - Bubble or Boom]]**.
- **Stranded power commitments.** Long-dated gas/nuclear PPAs signed against a demand curve that flattens leave operators paying for electrons they cannot monetize.
- **Depreciation surprise.** A forced move to realistic (2-3yr) useful lives would re-rate reported hyperscaler AI margins downward across the board.
- **Packaging/HBM shortfall.** If CoWoS capacity lags, GPUs cannot be assembled to fill live-power sites — capital and power both stranded waiting on memory.

## The non-obvious

The buildout front-runs demand by *years* — foundations poured in 2025 for compute landing 2026-27 against demand projected into the late 2020s. That temporal gap is the load-bearing insight: it means the buildout's biggest near-term risk is **timing, not the underlying thesis**. A demand air-pocket triggers a financial unwind (the market punishes the front-running) without saying anything about whether AI ultimately absorbs the capacity — exactly the fiber-overbuild dynamic, where the capacity was real, eventually used, and bankrupted its financiers first. At enterprise scale, that demand air-pocket is the same failure [[Concept - The Pilot-to-Production Gap]] names: compute sits idle exactly when pilots don't convert to funded production deployments at the volume the buildout was sized for. Practitioners who conflate "the buildout had an unwind" with "the compute wasn't needed" repeat the dot-com mistake. Watch the *ratio* (usage growth vs capex) and the *power delivery schedule*, not the equity-market reaction.

## Evolution

The buildout scaled by an order of magnitude in two years: from single-digit-billion training runs (2022-23) to GW-scale, half-trillion-dollar multi-year programs (Stargate, Jan 2025). The compute mix is itself shifting: the **[[Concept - The Data Wall]]** and the rise of RL-from-verifiable-rewards are moving marginal spend from pretraining toward inference-time and RL compute, which changes the memory/interconnect profile the next generation of sites must optimize for. What replaces the current phase is either absorption (usage compounds, sites fill, the buildout becomes ordinary infrastructure) or a correction (a demand air-pocket forces impairments and consolidation) — the fork tracked in **[[Reference - The Open Questions Ledger]]**. The capability payoff the whole program capitalizes is the **[[Concept - Scaling Laws]]** premise that more compute keeps buying more capability.

## Connections
- [[Deep Dive - Bubble or Boom]] — the financial twin of this note; the depreciation and revenue/capex questions this buildout physically instantiates.
- [[Concept - Token Price Deflation]] — the deflation curve that is both the demand engine and the unit-revenue pressure the buildout bets on.
- [[Breakdown - Frontier Lab Economics]] — the lab P&L that the compute commitments (Stargate) have to service.
- [[Concept - The Data Wall]] — shifts marginal compute from pretraining to inference/RL, changing what the buildout must serve.
- [[Concept - GPU Depreciation and Compute Capex Accounting]] — the 2-3 vs 5-6 year fault line that decides whether the buildout is profitable.
- [[Concept - METR Time Horizons]] — the capability extrapolation that the power/HBM constraints physically bound.
- [[Reference - The AI Forecasting Track Record]] — how to weight the extrapolations that justify the spend.
- [[Concept - The AGI Timeline Debate]] — the capability-timeline stakes that the buildout is a bet on.
- [[Concept - Automated AI Research and Takeoff]] — the fast-timeline case whose compute demand this buildout would have to feed.
- [[Reference - AI Market Sizing Claims]] — the demand-side TAM numbers the ~$650-700B capex is underwritten against.
- [[Concept - Unit Economics of LLM Products]] — whether tokens served clear a margin, the microfoundation of absorption.
- [[Reference - The 2026 Navigation Cheatsheet]] — the operator's compressed read on the cost curve and reliability frontier.
- [[Reference - The Open Questions Ledger]] — "can the buildout be absorbed?" tracked as a live, unresolved question.
- [[Concept - GPU Memory Hierarchy]] — the HBM/packaging bottleneck that gates facilities→compute, the true chip constraint.
- [[Reference - Memory Math for Transformers]] — the memory-per-model arithmetic that sizes how much HBM the buildout actually needs.
- [[Concept - Scaling Laws]] — the technical premise (capability rises with compute) the entire capex program capitalizes.
- [[Concept - Cost Engineering for LLM Applications]] — how the deflating cost curve is converted to real margin at the application layer.
- [[Concept - The Pilot-to-Production Gap]] — the buildout's absorption bet depends on enterprise AI demand actually crossing from pilot to funded production at the projected volume; a demand air-pocket is this gap expressed at compute-fleet scale (cross-domain: adoption).

## Sources
- OpenAI (Jan 2025) — "Announcing The Stargate Project"; (Sep 2025) five-new-sites announcement. $500B/10GW, Abilene, GB200 racks (E2, company).
- Hyperscaler FY2026 capex guidance + analyst compilations (Futurum, MUFG, 2026) — ~$650-700B combined 2026 capex; $256B→$443B→$600B+ trajectory (E1/E2).
- Reporting on grid/power constraints (2025-26) — gas turbines, delayed coal retirements, nuclear PPAs for GW-scale campuses (E2).
- Burry, M. / Scion disclosures (2025) — GPU depreciation 2-3 vs 5-6 yr, ~$176B earnings overstatement 2026-28 (E1, disclosed short).
- a16z (2024-25) — "LLMflation," ~10x/yr inference cost decline underpinning the Jevons absorption case (E2).
