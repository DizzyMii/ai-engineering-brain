---
tags: [lore, domain/trajectory, level/unicorn]
aliases: [Busted AI Predictions, AI Forecasting Failures, Radiologists Obsolete, Watson Health, Self-Driving Next Year]
summary: "War stories of confident AI predictions that busted — self-driving, radiologists, Watson, Klarna — and the two errors underneath them."
---

# Lore - Failed AI Predictions

> **Why this note exists (unicorn tier):** the vault's forecasting notes give you the calibration math ([[Reference - The AI Forecasting Track Record]]). This one is the graveyard of specific, named, quotable predictions that blew up, and *how* they blew up is the tribal knowledge. Nearly every bust is one of two errors in different clothes, and once you see it you can spot the next one live.

## What happened

### "Self-driving is a year away," annually since ~2015

Elon Musk is the canonical offender; the whole industry sang along. Musk promised full autonomy by 2018, "a million robotaxis on the road" by mid-2020 (Autonomy Day, April 2019), and unsupervised consumer FSD by June 2025. In January 2026 he moved the goalpost again: Tesla first needs ~10 billion miles of data. On the Q1 2026 earnings call the date slid to "Q4 2026 at the earliest." As of mid-2026 **no Tesla has L4/L5 certification**, and "FSD Supervised" explicitly keeps the human as fallback (well-documented, E3; public earnings calls and filings). What *did* arrive is narrow: Waymo runs real driverless robotaxis in geofenced cities. The last 1% of reliability took a decade nobody budgeted for, and general L5 still isn't here.

### "Stop training radiologists": Hinton, 2016

At a 2016 conference Geoffrey Hinton said "people should stop training radiologists now," and that it was "completely obvious" AI would outperform them within five years, ten at most. The field went the other way. The Mayo Clinic now employs 400+ radiologists, **~55% more** than in 2016. The American College of Radiology projects the specialty's physician supply up **~26% over 30 years**. Radiologist compensation runs to **~$571K** amid a documented shortage (well-documented, E2/E3; Fortune May 2026, NYT). In a May 2026 NYT feature Hinton **acknowledged the miss**, saying he'd meant image *analysis* specifically and was "wrong on the timing, not the direction." That defense is the lesson: reading a scan is a task. Being a radiologist is a job that turned out to be mostly everything else.

### IBM Watson Health: the $4B enterprise overpromise

After its *Jeopardy!* win, Watson was marketed ~2013–2018 as a cancer-diagnosis revolution. The MD Anderson flagship (started 2012, ~$62M) was shelved in 2017. STAT later reported that Watson had recommended **unsafe and incorrect** cancer treatments in testing. Trained on Memorial Sloan Kettering hypotheticals and deployed into a different institution's vocabulary and workflow, it was confidently wrong. IBM sold Watson Health to Francisco Partners for **>$1B in 2022** and retired the name (rebranded Merative) (well-documented, E2; Slate, STAT, HBS case). It's the template for every "our AI will transform [regulated high-stakes domain]" deck since.

### Klarna's 700 agents: claim, then correction, inside 15 months

February 2024: Klarna and OpenAI announced the AI assistant had handled **2.3M chats in one month, two-thirds of volume, the work of 700 full-time agents**, with ~$40M profit impact. May 2025: Klarna started **rehiring humans**. CEO Siemiatkowski conceded that cost-first automation produced "lower quality" and promised customers would "always [have] a human if you want" (E2, company-claimed then walked back; see [[Breakdown - Klarna's AI Customer Service Bet]]). A real deployment, whose headline number outran its reliability on nuanced, emotional tickets.

### The bear side busts too

"AI winter is coming" and "LLMs have plateaued" were declared confidently after GPT-3 and again after GPT-4, then falsified by reasoning models and agentic gains (folklore, weakly sourced on specific quotes, E1). Over-pessimism is the same forecasting failure as over-hype, pointed the other way.

## The lesson

Two mechanical errors produce almost the entire graveyard:

1. **Demo-to-deployment extrapolation.** A model that's 50%-reliable on a benchmark gets forecast as though it will be deployed. Real deployment in high-stakes work needs ~99.9%, and the distance from 50% to 99.9% is most of the remaining work, not a scaling detail ([[Concept - METR Time Horizons]], [[Concept - The Capability-Reliability Gap]]). Self-driving, Watson and Klarna all died there.
2. **Task-vs-job confusion.** Automating a task ≠ eliminating a job. Radiology is the purest case: AI got good at reading images and radiologist demand *rose*, because the job is triage, integration, liability and edge cases ([[Deep Dive - AI and the Labor Market]]).

The directional finding that holds up, consistent with the scorecard: **capability curves get under-forecast; reliability and adoption timelines get over-forecast.** People wrong about "how good" usually guessed too slow (a pleasant surprise); people wrong about "how soon it's *deployed*" usually guessed too fast (an expensive one). Weight accordingly.

## Evidence status

Tiered honestly, since that's the point of the genre:
- **Well-documented (E2/E3):** Musk's dated promises (earnings calls, filings), Hinton's 2016 quote and 2026 NYT walk-back, the Watson/MD Anderson timeline and 2022 sale, the Klarna claim and reversal. All on the record.
- **Folklore (E1):** the specific "AI winter"/"plateau" quotes. The *pattern* is real and repeated, but individual attributions are often paraphrase. Labeled as such, not laundered into fact.
- Watch the survivorship trap. We remember busted predictions and forget the boring correct ones, so this note is evidence about *error modes*, not a base rate for "AI predictions are usually wrong."

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
