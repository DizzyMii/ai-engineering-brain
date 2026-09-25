---
tags: [deep-dive, domain/trajectory, level/advanced]
aliases: [AI Compute Buildout, Stargate, AI Data Center Buildout, Hyperscaler Capex]
summary: "The physical AI buildout: Stargate, hyperscaler capex, the power bottleneck, and whether it can be absorbed."
---

# Deep Dive - The AI Compute Buildout

> **One-paragraph hook:** The 2025-26 AI buildout is the largest infrastructure program in the history of computing, measured in gigawatts, poured concrete and grid interconnect queues as well as dollars. [[Deep Dive - Bubble or Boom]] asks whether the *money* pencils out. This note asks the physical one: can the electrons, land, high-bandwidth memory and permitting timelines deliver the compute the capital has already committed to? The limit isn't chips or money. It's power, and power runs on a clock the software industry has never had to respect.

## The mechanism: capex to compute to tokens

The buildout converts money to revenue in three stages, each with a very different time constant:

1. **Capital → facilities.** Committing money is fast (a press release). Pouring a GW-scale campus (land, substation, cooling, buildings) takes 18-36 months and waits on grid interconnection, which in the US routinely takes years.
2. **Facilities → compute.** Racking GPUs is fast *once power is live*. The gate is HBM and advanced-packaging (CoWoS) supply, not the logic die.
3. **Compute → revenue.** Tokens served have to make money. This is where the buildout meets [[Concept - Token Price Deflation]] and the demand question.

The mismatched time constants are the whole story: **money commits in quarters, power arrives in years, revenue arrives... when it arrives.** So the buildout *front-runs* demand by design: foundations poured now for compute landing in 2026-27, for demand projected into the late 2020s.

## Stargate and the numbers

**Stargate** is the flagship. Announced January 21 2025 (OpenAI, Oracle, SoftBank, MGX as equity funders; SoftBank the financial lead, OpenAI the operational lead), it targets **$500B over four years and up to 10GW** of capacity (E2, OpenAI + reporting; company-and-reported). By September 2025 the partners had announced five new sites; the flagship **Abilene, Texas** campus was live on Oracle Cloud Infrastructure, and Oracle began delivering the first **Nvidia GB200 (Blackwell) racks in June 2025**. By mid-2026 the program reported ~7GW planned and ~$400B committed over three years, with the partners claiming they were on track for the full 10GW / $500B by end of 2025 (E2). *(The roadmap points at next-generation Vera Rubin-class silicon for later phases, but as of mid-2026 the confirmed hardware on the ground is GB200. Treat "Rubin from 2026" as announced, not delivered, E1.)*

The whole industry:

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

**Scale of capex:** the top-4 US hyperscalers (Amazon, Microsoft, Alphabet, Meta) are on track for roughly **$650-700B combined capex in 2026**: Amazon ~$200B, Alphabet ~$175-185B, Meta ~$115-135B, Microsoft ~$120B+, with Oracle adding ~$50B, mostly AI-driven (E1/E2, analyst + company guidance, 2026). Combined hyperscaler capex rose from ~$256B (2024) to ~$443B (2025) to $600B+ (2026). No earlier infrastructure cycle matched that in absolute terms. Sizing of the demand it has to serve is tiered in [[Reference - AI Market Sizing Claims]].

## The clever and contested parts

**Power is the constraint, not chips (E2, reporting).** A single frontier training campus now draws about as much as a mid-size city, at GW scale. US grid interconnection queues run years, and new high-voltage transmission takes longer. Operators route around the grid with on-site natural-gas turbines, delayed coal-plant retirements and long-term nuclear power-purchase agreements (restarts and small-modular-reactor commitments included). So AI capability growth now depends partly on *energy policy and permitting*, fields with no Moore's-law equivalent. This constraint bounds the [[Concept - METR Time Horizons]] extrapolations most cleanly: a capability curve can't outrun the megawatts feeding it.

**GPU depreciation is the accounting fault line (E1, contested).** Whether the buildout is *profitable* depends on useful life. Book schedules of 5-6 years vs Michael Burry's argued 2-3 year real economic life (obsolescence per Nvidia generation + thermal wear at high utilization) swing reported margins by tens of billions a year. It's the crux shared with [[Deep Dive - Bubble or Boom]]; [[Concept - GPU Depreciation and Compute Capex Accounting]] develops it. If real life is shorter than book life, the buildout's reported returns are partly a depreciation-policy artifact.

**What has to be true to absorb it (E1).** The buildout bets that tokens served keep ~10×-ing and that deflation grows demand faster than it erodes per-unit revenue: a Jevons bet. Deflation is *both* the demand engine and the pressure on unit revenue, so absorption cuts two ways. If Jevons holds, the compute fills. If demand saturates, the same fixed costs sit idle at ~2-3yr obsolescence. Per-token economics are in [[Concept - Unit Economics of LLM Products]] and the operational discipline in [[Concept - Cost Engineering for LLM Applications]].

**Constraints that could bend the curve (E1/E2):**
- Multi-year power and permitting timelines (above).
- HBM and CoWoS advanced-packaging supply. The real chip bottleneck is memory and packaging, not logic, which is where [[Reference - Memory Math for Transformers]] and [[Concept - GPU Memory Hierarchy]] meet macroeconomics.
- [[Concept - The Data Wall]] moving spend from pretraining toward inference and RL compute, which changes *what kind* of compute the buildout has to serve as well as how much.

## Failure modes

- **The demand air pocket.** Capital runs years ahead of demand, so a 12-18 month shortfall in monetized demand doesn't disprove the thesis but can set off a *financial* unwind (impairments, halted projects). Timing risk, not thesis risk; see [[Deep Dive - Bubble or Boom]].
- **Stranded power commitments.** Long-dated gas/nuclear PPAs signed against a demand curve that flattens leave operators paying for electrons they can't monetize.
- **Depreciation surprise.** A forced move to realistic (2-3yr) useful lives would mark reported hyperscaler AI margins down across the board.
- **Packaging/HBM shortfall.** If CoWoS capacity lags, GPUs can't be assembled to fill live-power sites, and capital and power both sit waiting on memory.

## The non-obvious

The buildout runs *years* ahead of demand: foundations poured in 2025 for compute landing 2026-27 against demand projected into the late 2020s. So the biggest near-term risk is **timing, not the underlying thesis**. A demand air pocket sets off a financial unwind (the market punishes the front-running) and says nothing about whether AI eventually absorbs the capacity. It's the fiber-overbuild dynamic again, where the capacity was real, eventually got used, and bankrupted its financiers first.

At enterprise scale that air pocket is the failure [[Concept - The Pilot-to-Production Gap]] describes: compute sits idle when pilots don't convert into funded production deployments at the volume the buildout was sized for. Treating "the buildout had an unwind" as "the compute wasn't needed" repeats the dot-com mistake. Watch the *ratio* (usage growth vs capex) and the *power delivery schedule*, not the equity-market reaction.

## Evolution

The buildout grew by an order of magnitude in two years, from single-digit-billion training runs (2022-23) to GW-scale, half-trillion-dollar multi-year programs (Stargate, Jan 2025). The compute mix is shifting too: [[Concept - The Data Wall]] and the rise of RL from verifiable rewards are moving marginal spend from pretraining toward inference-time and RL compute, which changes the memory/interconnect profile the next generation of sites has to optimize for. Next comes either absorption (usage compounds, sites fill, the buildout becomes ordinary infrastructure) or correction (a demand air pocket forces impairments and consolidation), the fork tracked in [[Reference - The Open Questions Ledger]]. The payoff the whole program capitalizes is the [[Concept - Scaling Laws]] premise that more compute keeps buying more capability.

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
