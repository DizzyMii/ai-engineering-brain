---
tags: [lore, domain/trajectory, level/unicorn]
aliases: [Busted AI Predictions, AI Forecasting Failures, Radiologists Obsolete, Watson Health, Self-Driving Next Year]
summary: "War stories of confident AI predictions that busted — self-driving, radiologists, Watson, Klarna — and the two errors underneath them."
---

# Lore - Failed AI Predictions

> **Why this note exists (unicorn tier):** the vault's forecasting notes give you the calibration math ([[Reference - The AI Forecasting Track Record]]). This one gives you the graveyard — the specific, named, quotable predictions that blew up, because the *shape* of how they blew up is the tribal knowledge. Almost every bust is one of two errors wearing different clothes, and once you can see the error you can spot the next one live.

## What happened

**"Self-driving is a year away" — annually, since ~2015.** Elon Musk is the canonical offender, but the whole industry sang it. Musk promised full autonomy by 2018, "a million robotaxis on the road" by mid-2020 (Autonomy Day, April 2019), unsupervised consumer FSD by June 2025 — and in January 2026 moved the goalpost again, now saying Tesla needs ~10 billion miles of data first. On the Q1 2026 earnings call the date slid to "Q4 2026 at the earliest." As of mid-2026 **no Tesla has L4/L5 certification**; "FSD Supervised" explicitly keeps the human as fallback (well-documented, E3 — public earnings calls and filings). What *did* arrive is narrow: Waymo runs genuine driverless robotaxis in geofenced cities. The lesson isn't "self-driving is fake" — it's that the last 1% of reliability took a decade nobody budgeted for, and general L5 still isn't here.

**"Stop training radiologists" — Hinton, 2016.** Geoffrey Hinton, at a 2016 conference: "People should stop training radiologists now," it was "completely obvious" AI would outperform them within five years, ten at most. A decade later the field did the opposite. The Mayo Clinic now employs 400+ radiologists, **~55% more** than in 2016; the American College of Radiology projects the specialty's physician supply up **~26% over 30 years**; radiologist compensation runs to **~$571K** amid a documented shortage (well-documented, E2/E3 — Fortune May 2026, NYT). In a May 2026 NYT feature Hinton **acknowledged the miss**, pleading that he'd meant image *analysis* specifically and was "wrong on the timing, not the direction." That plea *is* the lesson: reading a scan is a task; being a radiologist is a job that turned out to be mostly everything else.

**IBM Watson Health — the $4B enterprise overpromise.** Marketed ~2013–2018 as a cancer-diagnosis revolution after its *Jeopardy!* win. The MD Anderson flagship (started 2012, ~$62M) was shelved in 2017; STAT later reported Watson had recommended **unsafe and incorrect** cancer treatments in testing — trained on Memorial Sloan Kettering hypotheticals, deployed into a different institution's vocabulary and workflow, confidently wrong. IBM sold Watson Health to Francisco Partners for **>$1B in 2022** and retired the name (rebranded Merative) (well-documented, E2 — Slate, STAT, HBS case). The template for every "our AI will transform [regulated high-stakes domain]" deck since.

**Klarna's 700 agents — claim, then correction, inside 15 months.** February 2024: Klarna and OpenAI announced the AI assistant handled **2.3M chats in one month, two-thirds of volume, the work of 700 full-time agents**, ~$40M profit impact. May 2025: Klarna started **rehiring humans**; CEO Siemiatkowski conceded cost-first automation produced "lower quality" and promised customers would "always [have] a human if you want" (E2, company-claimed then walked back — see [[Breakdown - Klarna's AI Customer Service Bet]]). Not a fabrication — a real deployment whose headline number outran the reliability on nuanced, emotional tickets.

**The bear side busts too.** Symmetry matters: "AI winter is coming" and "LLMs have plateaued" were declared confidently after GPT-3 and again after GPT-4, then falsified by reasoning models and agentic gains (folklore, weakly sourced on specific quotes, E1). Over-pessimism is the same forecasting failure as over-hype, pointed the other way.

## The lesson

Two mechanical errors generate almost the entire graveyard:

1. **Demo-to-deployment extrapolation.** A model that is 50%-reliable on a benchmark gets forecast as if it will be deployed. But real deployment in high-stakes work needs ~99.9%, and the gap between 50% and 99.9% is not a scaling detail — it's most of the remaining work (link [[Concept - METR Time Horizons]], [[Concept - The Capability-Reliability Gap]]). Self-driving, Watson, and Klarna all died in that gap.
2. **Task-vs-job confusion.** Automating a task ≠ eliminating a job. Radiology was the purest case: AI got good at reading images and radiologist demand *rose*, because the job is triage, integration, liability, and edge cases (link [[Deep Dive - AI and the Labor Market]]).

The durable directional finding, consistent with the scorecard: **capability curves get under-forecast; reliability and adoption timelines get over-forecast.** The people who are wrong about "how good" are usually wrong slow (pleasant surprise); the people wrong about "how soon it's *deployed*" are usually wrong fast (expensive surprise). Weight accordingly.

## Evidence status

Honestly tiered, because that's the point of the genre:
- **Well-documented (E2/E3):** Musk's dated promises (earnings calls, filings), Hinton's 2016 quote and 2026 NYT walk-back, the Watson/MD Anderson timeline and 2022 sale, the Klarna claim-and-reversal. These are on the record.
- **Folklore (E1):** the specific "AI winter"/"plateau" quotes — the *pattern* is real and repeated, but individual attributions are often paraphrase. Labeled as such, not laundered into fact.
- Note the survivorship trap: we remember busted predictions and forget the boring-correct ones, so this note is evidence about *error modes*, not a base rate for "AI predictions are usually wrong."

## Connections

- [[Reference - The AI Forecasting Track Record]] — the calibration scorecard; this note is its narrative, war-story companion.
- [[Concept - METR Time Horizons]] — the 50%-reliable-demo that forecasters wrongly extrapolate to deployment.
- [[Concept - The Capability-Reliability Gap]] — the gap every one of these predictions died in.
- [[Deep Dive - AI and the Labor Market]] — the task-vs-job confusion, with the measured evidence radiology got wrong.
- [[Breakdown - Klarna's AI Customer Service Bet]] — the full anatomy of the live claim-then-walk-back example.
- [[Lore - Hallucination Liability Incidents]] — sibling genre: confident-wrong AI output causing real-world damage.
- [[Concept - The AGI Timeline Debate]] — the current forecasts this graveyard should make you discount, in both directions.
- [[Deep Dive - Bubble or Boom]] — "bubble" is the current over-pessimist call; symmetry says weigh it as skeptically as the hype.
- [[Gotchas - Enterprise AI Adoption]] — Watson is the ur-example in that failure taxonomy.

## Sources

- Fortune (May 4, 2026) & New York Times (May 2026) — Hinton's radiologist prediction revisited; Mayo +55% staff, ACR +26%/30yr, ~$571K comp, Hinton's acknowledgment.
- Slate (Jan 2022), STAT News, HBS case "IBM Watson at MD Anderson" — Watson Health failure, unsafe recommendations, $62M project, >$1B Francisco Partners sale.
- OpenAI/Klarna (Feb 2024) and CX Dive / Fast Company (May 2025) — the 700-agent claim and the rehiring reversal.
- Tesla Q1 2026 earnings call, Autonomy Day (April 2019), Electrek (April 2026) — the serial self-driving date slips; no L4/L5 certification as of mid-2026.
