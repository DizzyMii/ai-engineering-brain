---
tags: [concept, domain/trajectory, level/core]
aliases: [AGI Timelines, HLMI Timelines, When AGI, Transformative AI Timelines]
summary: "Credible AGI forecasts disagree by decades and use different definitions; the honest answer is a spread, not a date."
---

# Concept - The AGI Timeline Debate

> **One-paragraph hook:** Ask five credible sources "when is AGI?" and you get five different targets, since "AGI" doesn't mean one thing, measured five different ways, landing anywhere from 2027 to 2050+. Don't average that spread away. The range, and who's making which claim with what incentive, is the information. Anyone who hands you a single date has made an editorial choice you didn't see.

## The mechanism

The disagreement starts before any forecasting, at the definition. "AGI," "HLMI" (human-level machine intelligence), "transformative AI" and "superintelligence" name different targets and get swapped freely in public debate. OpenAI's charter language, Metaculus's operational resolution criteria for its AGI questions, and Morris et al.'s "Levels of AGI" framework (DeepMind, 2023) set meaningfully different bars: some need broad economic substitutability, some a specific battery of tasks, some self-directed goal pursuit. Much of the apparent timeline disagreement isn't about the trajectory at all. It's people answering different questions with the same word (E2, comparing named definitional sources directly).

Fix a definition and three different forecasting methods give three different kinds of number. None are measurements; all are E1-or-weaker estimates in different clothes:

1. **Expert surveys** aggregate stated beliefs from AI researchers. They move fast, track recent headlines more than any stable model, and depend on who responds.
2. **Aggregator markets** (Metaculus, prediction markets) aggregate a self-selected forecasting community's continuously updated probabilities. They react faster than surveys and carry the biases of whoever chooses to bet.
3. **Model-based methods** (Cotra's biological-anchors approach) build an explicit probabilistic model, here of how much compute might be needed to match brain-scale computation, and propagate uncertainty through it. They're the most transparent about their assumptions and, by their authors' own admission, the most fragile to small input changes.

## In practice

**Expert surveys.** Grace et al.'s AI Impacts survey of thousands of published AI researchers found the aggregate 50%-chance-of-HLMI date moved from 2060 (2022 survey) to 2047 (2023 survey), a 13-year jump in one year (E2, Grace et al./AI Impacts 2023, n≈2,778 published researchers, single survey series with known response and selection bias). Earlier rounds (Müller & Bostrom 2016, Grace et al. 2018) put the median around 2061, so 2023 is a break in the series, not a steady drift. Read it as evidence that survey point estimates anchor hard on recent capability jumps (GPT-4 shipped between the 2022 and 2023 rounds) instead of tracking a stable underlying model.

**Aggregator markets.** Metaculus's "weakly general AI" question (#3479) is still open as of 2026, with a community median around June 2028 (range roughly Nov 2026 to Mar 2032), down from ~2042 in early 2022. Its strict resolution criteria, including an adversarial Turing-test element, aren't yet judged met, so "weakly general" hasn't formally resolved even though the bar is far below what most people mean by "AGI." Metaculus's harder, separate "AGI" question (#5121, requiring a Turing test, robotic manipulation and benchmark thresholds) sat at a community median around 2033 as of its February 2026 update (~25% by 2029, ~50% by 2033) (E2, prediction market, self-selected forecasting community, moving target; date-stamp any number quoted from it).

**Model-based.** Cotra's biological-anchors report (Open Philanthropy, 2020) anchored compute requirements for transformative AI to estimates of the human brain's computation, with 20+ orders of magnitude of uncertainty in its inputs. The original model put a 50% chance of transformative AI around 2050-2052. Cotra's "Two-Year Update" (2022) pulled the median to 2040 (15% by 2030, 35% by 2036, 60% by 2050), citing faster-than-expected scaling (E1, model; both versions are author-labeled "fragile to parameter choices," the report's own caveat, not outside criticism).

**The camps, named and unaveraged, per STANDARDS §8:**
- *Short:* Dario Amodei's "Machines of Loving Grace" (Oct 2024) argued "powerful AI" (able to prove unsolved theorems, write difficult codebases from scratch, and act with broad autonomy) could arrive "as early as 2026." Anthropic's OSTP submission (March 2025) narrowed that to "late 2026 or early 2027" (E2, company-affiliated forecast). Amodei runs a lab that raises capital partly on this narrative, and that conflict deserves naming; [[Deep Dive - Circular Financing in the AI Buildout]] works out how the fundraising narrative and capex commitments feed each other. Kokotajlo et al.'s *AI-2027* scenario made a similarly aggressive case, then walked its headline milestone back to the early 2030s in a December 2025 revision. [[Concept - Automated AI Research and Takeoff]] has the walk-back in full. It belongs here too, as direct evidence of how the short camp's specific dates have held up.
- *Long / skeptic:* Yann LeCun argues LLMs are an architectural off-ramp. They're useful but lack the world-model and planning capacity general intelligence needs, which calls for a different paradigm, not more scale on this one. Gary Marcus argues current systems hit a reliability ceiling (hallucination, brittle generalization) that scaling alone won't fix, closely related to [[Concept - The Capability-Reliability Gap]]. Neither publishes a competing date. Both say the short camp's timeline needs an architectural breakthrough that hasn't happened, which is a claim about mechanism, not a mood.

**Why the medians compressed.** GPT-4-class systems, reasoning models and the [[Concept - METR Time Horizons|METR horizon trend]] pulled estimates in across nearly every method between 2022 and 2026. Even so, survey and bio-anchors medians still land about two decades out (2040-2047). "AGI imminent" (under 5 years) is a minority, front-running view concentrated among lab-affiliated forecasters and aggressive scenario authors, not the center of the credible distribution (E1, synthesis across the sources above).

## Failure modes

**Averaging the spread into a mean.** STANDARDS §8 bans it, and for a concrete reason. Averaging a 2027 lab forecast with a 2047 survey median gives ~2037, a number no source holds, and it hides that the two inputs disagree about mechanism as well as magnitude. Report the range and who holds each end.

**Ignoring provenance and incentive.** A forecast from a lab raising capital on an AGI-soon narrative and one from an academic survey respondent with no financial stake aren't interchangeable, even at equal stated confidence. Samotsvety Forecasting, a superforecaster group selected partly for engagement with AI, put roughly 28% on AGI by 2030 in a January 2026 update (E1, small forecaster panel, n=8). That's noticeably shorter than generic superforecasters, for a stated reason (direct experience with frontier systems), and that kind of provenance detail should travel with the number.

**Treating "AGI" as one target across sources.** Comparing Metaculus's "weakly general AI" resolution date, Amodei's "powerful AI" and Cotra's "transformative AI" threshold as if they were one forecast is an apples-to-oranges error made before any real disagreement about capability trajectories enters.

## The non-obvious

The most informative fact here isn't a date. The loudest short-timeline claims cluster inside organizations with fundraising and competitive incentives to say "soon." Forecasters who engage deeply with AI without that incentive (Samotsvety) run shorter than generic superforecasters but still noticeably longer than lab-affiliated public statements. And academic survey medians sit two decades out even after their largest-ever single-year compression. Provenance is doing as much work as evidence.

The useful move is to build for the range instead of picking a winner. For a multi-year infrastructure or hiring bet, the honest input is "somewhere between 2029 and 2050, with real disagreement about mechanism, not just speed," not whichever number was last in a headline. [[Reference - The AI Forecasting Track Record]] tells you how much to discount any single number in that range, and [[Reference - The Open Questions Ledger]] tracks this as one of several unresolved trajectory questions.

The evidence at both ends is weaker than it looks up close. Short-timeline arguments lean partly on [[Concept - Benchmark Saturation|climbing benchmark scores]], which that note shows are largely noise once a benchmark saturates. They also lean on whether capability jumps are real phase transitions or measurement artifacts, the question [[Concept - The Emergent Abilities Debate]] asks of individual benchmarks, applied here to whole trajectories. [[Reference - Model Genealogy]] has the raw lab-to-lab capability record several forecasts extrapolate from. [[Concept - Scaling Laws]] is the empirical relationship the short camp extrapolates and the long camp says will bend, and [[Concept - The Data Wall]] is a named mechanism that could push timelines past the compressed 2040s medians.

A real capex bubble says nothing about whether the technology is transformative, so [[Deep Dive - Bubble or Boom]] is a parallel but separate debate. Don't let "the market looks overheated" stand in for "AGI is far away," or the reverse. And [[Lore - Failed AI Predictions]] is the reminder that over-optimistic and over-pessimistic timing calls have both busted before. That's the base rate to read this whole debate against.

## Connections
- [[Concept - METR Time Horizons]] — the concrete capability curve that both compressed timeline estimates over 2022-2026 and that short-timeline extrapolations lean on most heavily.
- [[Concept - Automated AI Research and Takeoff]] — the specific mechanism (AI automating AI R&D) the short camp's fastest scenarios depend on, including AI-2027's own walked-back dates.
- [[Reference - The AI Forecasting Track Record]] — the calibration scorecard for weighing which of the methods described here to trust more.
- [[Concept - Benchmark Saturation]] — one of the (weak) evidentiary inputs some short-timeline arguments lean on; saturated scores are less informative than they look.
- [[Deep Dive - Bubble or Boom]] — a parallel debate (is the capex justified) that's often conflated with this one but is analytically separate — bubble and imminent-AGI are independent questions.
- [[Concept - The Data Wall]] — a candidate mechanism that could push timelines later if pretraining scaling has less room left than the compressed medians assume.
- [[Lore - Failed AI Predictions]] — the historical base rate for how confident capability-timing forecasts have performed, in both directions.
- [[Reference - The Open Questions Ledger]] — this debate is one of the live, tracked, unresolved trajectory questions there.
- [[Concept - Scaling Laws]] — the underlying empirical relationship that both the short camp (extrapolate it) and the long camp (argue it will bend) are arguing about.
- [[Concept - The Emergent Abilities Debate]] — a related dispute about whether capability jumps are real phase transitions or measurement artifacts, which feeds directly into how much weight short-timeline forecasters put on recent jumps.
- [[Reference - Model Genealogy]] — grounding for how fast frontier capability has actually moved lab-to-lab, the raw material several of these forecasts are extrapolating from.
- [[Deep Dive - Circular Financing in the AI Buildout]] — the fundraising incentive behind lab-affiliated short timelines is not just rhetorical; this is the capital mechanism it feeds (cross-domain: economics).

## Sources
- Grace, Stein-Perlman, et al. / AI Impacts (2023) — *Thousands of AI Authors on the Future of AI*. The 2060→2047 median jump; n≈2,778 published researchers.
- Morris et al. / DeepMind (2023) — *Levels of AGI*. A competing operational definition, evidence that "AGI" is contested before any date is attached.
- Cotra / Open Philanthropy (2020, updated 2022) — *Forecasting Transformative AI from Biological Anchors* and *Two-Year Update on My Personal AI Timelines*. Median moved 2050-2052 → 2040; author-flagged fragility.
- Amodei (Oct 2024) — *Machines of Loving Grace*; Anthropic OSTP submission (March 2025). The "late 2026/early 2027" powerful-AI claim, company-affiliated.
- Kokotajlo, Lifland, Larsen, Dean, Alexander / AI Futures Project (April 2025, revised Dec 2025) — *AI 2027* and its walk-back.
- Metaculus — community "weakly general AI" and follow-on AGI questions, ongoing aggregator data, medians as of 2026.
- Samotsvety Forecasting (Jan 2026 update) — ~28% AGI-by-2030, n=8 superforecasters selected for AI engagement.
