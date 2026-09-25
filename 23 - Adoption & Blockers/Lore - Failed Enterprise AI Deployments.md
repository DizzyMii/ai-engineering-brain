---
tags: [lore, domain/adoption-blockers, level/unicorn]
aliases: [AI failure graveyard, enterprise AI flops, Watson for Oncology, Zillow Offers, McDonald's drive-thru AI]
summary: "The graveyard of named, documented enterprise AI flops — Watson, Zillow, McDonald's — and why you believe the write-down, not the launch."
---

# Lore - Failed Enterprise AI Deployments

> War stories from the enterprise AI graveyard. Three flagship flops, each launched with executive fanfare and a big number, each buried without much noise. They span pre-LLM and LLM-era AI and fail the same way, which is the point.

## What happened

### IBM Watson for Oncology at MD Anderson (2012–2016)

In June 2012 the University of Texas MD Anderson Cancer Center partnered with IBM to build an "Oncology Expert Advisor" that would recommend cancer treatments. Four years and **at least $62M** later (a University of Texas internal audit put spend at roughly $39M to IBM plus ~$23M in related PwC and other costs), the project was benched in September 2016. It never treated a single patient outside the pilot (E2/E3, University of Texas audit via *Forbes*/*IEEE Spectrum*, Feb 2017).

Two things killed it. First, integration: the pilots ran on the *old* records system (ClinicStation) and were never updated for MD Anderson's new **Epic** EHR; the audit noted the tool "has not been updated to integrate with the current system." The plumbing was the bottleneck. Second, training data: a *STAT* investigation (Sep 2018) reported Watson gave "unsafe and incorrect" treatment recommendations in internal testing, having been trained heavily on a small number of *synthetic* cases hand-crafted by Memorial Sloan Kettering physicians instead of a large corpus of real patient outcomes (IBM contested the characterization). Overpromise, hollow training data, no integration.

### Zillow Offers (2018–2021)

Zillow's iBuying arm used an algorithmic pricing model (the "Zestimate" lineage) to make instant cash offers on homes, buy and flip them. The forecasts were wrong in the most expensive direction: in a turning 2021 market the model systematically **overpaid**. On 2 Nov 2021 Zillow announced it was shutting the program, taking an inventory write-down of **more than $500M**, and laying off about **25% of staff, roughly 2,000 people** (E3, Zillow Q3 2021 earnings / 10-Q, investor call). CEO Rich Barton's own post-mortem: *"the unpredictability in forecasting home prices far exceeds what we anticipated."*

The Homes segment lost **$422M** in Q3 2021 alone (E3, Q3 2021 8-K), and the overpayment was systematic enough that Zillow held ~9,800 homes it could only sell at a loss. The company with the most-trafficked real-estate data in the US couldn't out-forecast a moving market with the model it spent billions buying houses on.

### McDonald's × IBM drive-thru voice AI (2021–2024)

From October 2021 McDonald's tested an IBM-built voice "Automated Order Taker" at about **100 US restaurants**. A 2022 BTIG survey clocked order accuracy in the **low 80s%**, against the **95%+** bar McDonald's had set before any broad rollout. It never got there, and the gap went viral: TikToks of the bot piling **260 Chicken McNuggets** onto an order and adding bacon to ice cream. In June 2024 McDonald's told franchisees it was ending the IBM partnership, with the system off by 26 July (E2, CNBC/Restaurant Dive/NRN, Jun 2024). A noisy real-time environment (engine noise, accents, cross-talk, menu edge cases) is the long tail where the last ten points of accuracy live.

## The lesson

A decade of model progress and the LLM boundary separate these three. They still rhyme:

- **A capability demo isn't production reliability.** Watson demoed brilliantly on Jeopardy and curated cases; McDonald's bot worked in quiet tests. Both died in the messy tail. That's [[Concept - The Pilot-to-Production Gap]] and [[Concept - The Capability-Reliability Gap]] in the wild: a 90% demo is a 10%-failure product, and reality lives in the missing points.
- **Data and integration are the real work.** Watson never touched Epic and trained on synthetic cases. Zillow's inputs couldn't track a regime change. The constraint was [[Concept - Data and Integration Readiness]], never the model.
- **The eval that mattered was the one they didn't trust.** McDonald's had the 95% bar, saw the low-80s reality, and still ran three years. Each flop had a measurable signal that lost out to the launch narrative, which is [[Concept - The Evaluation Gap]].
- **Believe the write-down, not the launch.** Each opened with executive fanfare and a headline number ($62M ambition, $20B/yr projection, national rollout) and ended in a low-key write-down or franchisee memo. Launches are loud and burials are silent, so the field looks far more successful than its base rate. That survivorship bias sits behind the MIT NANDA ~95%-of-pilots-show-no-P&L-impact finding (E2, *The GenAI Divide*, Aug 2025) and the framing in [[Deep Dive - Bubble or Boom]].
- **Vendor incentives shape the wreck.** The consultancy/systems-integrator megaproject (Watson + PwC) optimizes for contract size over shipped value. The durable operator move is "buy from specialists and integrate small" over "moonshot with a systems integrator". That's the conclusion of [[Decision - Build vs Buy vs Wrap]], and it fits NANDA's finding that vendor-partnered tools reach production ~67% of the time while internal builds succeed about a third as often.

[[Lore - Hallucination Liability Incidents]] is a different file: a *working-enough* bot saying something that created legal liability. The deployments here never reliably worked at all. Different failure, same root: the messy real world breaks brittle systems, and model capability doesn't substitute for readiness.

## Evidence status

All three are real, named and dated. No composites (STANDARDS §8).
- **Watson/MD Anderson:** richly documented: University of Texas internal audit, *Forbes* (Feb 2017), *IEEE Spectrum* (2019), *STAT* (Sep 2018). The $62M is audited (E3). The "unsafe recommendations" characterization is *STAT*'s reporting, contested by IBM (E2).
- **Zillow Offers:** the best-sourced: public earnings release, 10-Q and investor call, Nov 2021 (E3). The write-down, headcount and Barton quote are all in filings.
- **McDonald's/IBM:** well-reported press (CNBC, Restaurant Dive, NRN, Jun 2024). The low-80s% accuracy is a 2022 BTIG survey figure and the 95% target is McDonald's-stated (E2). The viral "260 nuggets" clip is real but anecdotal.

One legend to flag: the "$4 billion Watson failure" figure online mixes MD Anderson's ~$62M project with IBM's *total* Watson Health acquisition-and-buildout spend across many programs. For this deployment, $62M is the defensible figure. Treat the $4B as an E1 aggregate about IBM's Watson Health bet, not this project.

## Connections

- [[Concept - The Pilot-to-Production Gap]] — the headline pattern every case here instantiates: demos cross, deployments don't.
- [[Concept - Data and Integration Readiness]] — Watson's Epic-integration failure and Zillow's stale inputs are this blocker, named.
- [[Concept - The Evaluation Gap]] — each flop had a measurable signal (accuracy bar, forecast error) that lost to the launch narrative.
- [[Lore - Hallucination Liability Incidents]] — the sibling graveyard: bots that worked enough to talk and created liability, versus these that never reliably worked.
- [[Deep Dive - Bubble or Boom]] — survivorship bias here (loud launches, quiet write-downs) is core evidence for the bubble question.
- [[Decision - Build vs Buy vs Wrap]] — Watson is the case against the systems-integrator moonshot; "buy specialist, integrate small" wins.
- [[Reference - AI Market Sizing Claims]] — the big projected numbers ($20B/yr, national rollout) that these failures should discount.
- [[Reference - Where Real AI Knowledge Lives]] — post-mortems, audits, and filings (not vendor decks) are where the durable lessons are recorded.

## Sources

- Herper, M. (2017) — *MD Anderson Benches IBM Watson* (Forbes, Feb 2017). The $62M and the Epic-integration audit finding.
- Ross, C. & Swetlitz, I. (2018) — *IBM's Watson recommended unsafe and incorrect cancer treatments* (STAT, Sep 2018) and Strickland (2019) *How IBM Watson Overpromised and Underdelivered* (IEEE Spectrum). Synthetic-case training and unsafe-recommendation reporting.
- Zillow Group (2021) — Q3 2021 earnings release / 10-Q and shareholder letter, 2 Nov 2021. >$500M write-down, ~25% (~2,000) layoffs, Barton quote.
- CNBC / Restaurant Dive / NRN (Jun 2024) — McDonald's ends IBM AOT test; ~100 locations, low-80s% accuracy vs 95% target, off by 26 Jul 2024.
- MIT NANDA (2025) — *The GenAI Divide: State of AI in Business 2025*. The ~95%-no-P&L base rate and the ~67% vendor-vs-internal production asymmetry (E2, single report).
