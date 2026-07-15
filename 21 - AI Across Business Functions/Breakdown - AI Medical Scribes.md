---
tags: [breakdown, domain/applied-business, level/core]
aliases: [ambient AI scribes, ambient clinical documentation, DAX, Dragon Copilot, Abridge, Nabla, Suki]
summary: "Ambient AI scribes that draft clinical notes for physician sign-off are the best-evidenced applied-AI deployment as of mid-2026."
---

# Breakdown - AI Medical Scribes
> Ambient documentation tools — Microsoft's DAX/Dragon Copilot, Abridge, Nabla, Suki — listen to a patient visit and draft the clinical note a physician reviews and signs. Built on speech recognition plus an LLM summarization layer, deployed across hundreds of health systems since 2023, this is the single best-measured clinical AI deployment as of mid-2026: a large-N, multi-year, peer-reviewed dataset in a domain that usually has none.

## The headline numbers
The Permanente Medical Group (Kaiser Permanente's Northern California physician group) ran a 63-week real-world evaluation from October 16, 2023 to December 28, 2024: 7,260 physicians used ambient AI scribes across 2,576,627 patient encounters, saving an estimated 15,791 hours of documentation time (E2, Tierney et al., "Ambient Artificial Intelligence Scribes: Learnings after 1 Year and over 2.5 Million Uses," NEJM Catalyst 2024–2025 — the initial October 2023 rollout targeted a system-wide cohort of up to 10,000 physicians; 7,260 is the evaluated-use figure). Secondary outcomes: reduced after-hours "pajama time" EHR work, less in-visit screen time, and a physician and patient survey majority reporting the physician spent more time actually talking with the patient (E2, same source).

Market scale, mid-2026: Microsoft's Dragon Copilot (built on its Nuance DAX ambient-listening technology) reported 3M+ ambient patient conversations per month across 600+ healthcare organizations (E2, Microsoft, March 2025). Abridge raised a $300M Series E led by a16z in June 2025 at a $5.3B valuation — nearly double its $2.75B valuation just four months earlier — bringing its total raised past $800M across rounds, and serves 150+ health systems (E2, TechCrunch/Fierce Healthcare, June 2025). Nabla raised a $70M Series C in June 2025 (total funding $120M), embedded in 130+ healthcare organizations (E2, STAT News/Fierce Healthcare, June 2025). Suki raised $70M in 2024 (E2, Fierce Healthcare).

## How it actually works
```
Patient visit (audio, ambient mic)
        │
        ▼
Speech-to-text (streaming ASR, speaker diarization:
distinguishes clinician / patient / others in room)
        │
        ▼
LLM summarization layer
  — structures transcript into SOAP/clinical note format
  — maps free speech to EHR-coded fields (ICD-10, CPT
    suggestions) where the vendor integrates coding
        │
        ▼
DRAFT note → physician's EHR inbox
        │
        ▼
Physician review: reads draft against memory of the
visit, edits, corrects, adds/removes detail
        │
        ▼
Physician signs → note becomes the legal medical record
(physician is the accountable author, not the AI)
```
The load-bearing design decision is where the pipeline stops: at a **draft**, not a filed note. The physician remains the legally and clinically accountable author. This is precisely why the deployment scaled where autonomous diagnosis has not — it automates the transcription-and-structuring labor around a clinical encounter without asking the model to make a clinical judgment. See [[Pattern - Human-in-the-Loop Review Workflow]] for the general shape this instantiates.

## The clever parts
1. **Choosing documentation, not diagnosis.** Documentation is high-burden (physicians report it as the single biggest driver of after-hours work) and low-decision-risk (a wrong draft sentence gets corrected before it matters) — the opposite of clinical decision support, where errors reach the patient. This task selection is the whole reason the deployment worked; a model with identical accuracy applied to differential diagnosis would face entirely different liability math (see [[Concept - The Front-Office Back-Office Adoption Split]]).
2. **Speaker diarization as a prerequisite, not a feature.** Ambient listening only works because the ASR layer can attribute utterances to clinician vs. patient vs. family member in the room — without this, the LLM summarizer has no reliable signal for who said what, and misattribution is one of the documented failure modes (below).
3. **Draft-then-sign as the accountability contract.** The physician's signature is the product's real quality gate, not a model confidence score. This let vendors ship without waiting for near-perfect accuracy — the human catches the residual error rate, and the error rate the human catches is instrumented as an edit-rate signal vendors can improve against.
4. **Measuring hours saved, not accuracy.** Every headline number in this space is a time or burnout metric, not an accuracy benchmark — a deliberate choice that sidesteps the much harder (and still largely unsolved) question of scoring clinical-note quality directly, deferring that judgment to the physician's edit.
5. **Selling into an existing EHR workflow rather than replacing it.** DAX, Abridge, and Nabla all integrate into Epic/other EHR inboxes rather than standing up a separate system — the note lands where the physician already works, which lowered the adoption barrier relative to a parallel tool.

## What it got wrong / what's dated
Quality is not free even in the copilot design. A validated evaluation found ambient-generated notes contain hallucinated content — plausible-sounding but fabricated detail not grounded in the encounter — at a meaningfully higher rate than physician-authored notes; reported hallucination rates range from about 1.5% to 7% depending on the study and note section, with the npj paper supporting the lower end of that range (E2, npj Digital Medicine 2025). A 2026 language-shift analysis of draft-vs-signed notes found systematic differences between the AI's draft phrasing and what clinicians finalize — the human edit is measurably load-bearing, not cosmetic rubber-stamping (arXiv:2606.00018, 2026, Zhou et al., "Examine Clinicians' Modification of Hedging Language in Ambient AI Documentation: A Comparative Study of AI Drafts and Final Notes" — single preprint, E2). One reported data point: Yale New Haven Health clinicians retained roughly 80% of an AI draft unedited, meaning roughly a fifth of every note is clinician-authored correction (E2, single-institution report) — high utility, but not "autonomous."

The economics also concentrate risk on the review step scaling: as note volume grows, the physician-review bottleneck doesn't disappear, it just moves — a scribe that saves 2 minutes per note but requires 30 seconds of extra scrutiny to catch a 5% hallucination rate is a different product than the "eliminates documentation burden" pitch implies. Valuations (Abridge at $5.3B) are pricing the workflow-integration and distribution position, not a solved-accuracy claim — the same investor-conviction-vs-realized-value gap that runs through [[Concept - Vertical AI Agents by Function]].

## What to steal
- Pick the task where a licensed, accountable human is *already* the reviewer of record — you inherit an existing liability structure instead of inventing a new one.
- Measure and publish time-saved-per-worker, not model accuracy — it's the metric your buyer actually cares about and the one you can measure cleanly at scale.
- Instrument edit rate as your real quality signal (see [[Pattern - Human-in-the-Loop Review Workflow]]) rather than relying on a static benchmark.
- Integrate into the existing system of record instead of building a parallel one; adoption friction kills more deployments than model quality does (see [[Concept - The Pilot-to-Production Gap]]).
- Don't let "the human reviews it" become an unexamined assumption — the 1.5–7% hallucination rate exists precisely because review is imperfect, and a growing note volume makes review fatigue a real failure mode to monitor, not a solved problem to assume away.

## Connections
- [[Concept - The Front-Office Back-Office Adoption Split]] — medical scribes are the domain's cleanest example of the low-liability, human-reviewed side of the split.
- [[Concept - Copilot vs Autopilot Deployment Modes]] — the draft-then-sign design is copilot mode in its purest form; there is no autopilot variant deployed at scale.
- [[Pattern - Human-in-the-Loop Review Workflow]] — the general pattern this deployment is the flagship instance of.
- [[Concept - Vertical AI Agents by Function]] — Abridge is a named example of the vertical-agent thesis applied to healthcare documentation.
- [[Reference - AI Impact by Business Function]] — the domain lookup table this Breakdown's numbers feed into the "healthcare documentation" row of.
- [[Concept - Support Deflection Economics]] — a structural parallel: both fields learned that the headline automation metric (deflection; hours saved) hides a contested measurement layer underneath.
- [[Breakdown - Harvey and AI in Legal Work]] — the closest cross-function analog: a licensed professional (lawyer, not physician) as the mandatory-review accountable party.
- [[Lore - Hallucination Liability Incidents]] — the domain-23 record of what happens when this review gate is skipped or fails, relevant to the hallucination-rate caveat above.
- [[Reference - The EU AI Act for Operators]] — clinical documentation AI sits adjacent to the Act's high-risk medical-device and health-data categories, worth checking before scaling in the EU.
- [[Concept - The Pilot-to-Production Gap]] — the EHR-integration point above is a direct instance of the data/integration-readiness failure mode this concept catalogs.
- [[Concept - Moats in the AI Application Layer]] — Abridge's valuation trajectory is a live test of whether workflow integration and clinical-data position outlast the underlying model becoming commoditized.

## Sources
- Tierney, A. et al. (2024–2025) — "Ambient Artificial Intelligence Scribes: Learnings after 1 Year and over 2.5 Million Uses," NEJM Catalyst. Single-system, peer-reviewed real-world evaluation (E2).
- Microsoft (March 2025) — Dragon Copilot / DAX launch announcement, 3M ambient conversations/month, 600+ organizations. Company-reported (E2).
- TechCrunch, Fierce Healthcare, MobiHealthNews (June 2025) — Abridge $300M Series E at $5.3B valuation. Multiply-reported funding announcement (E2).
- STAT News, Fierce Healthcare, PR Newswire (June 2025) — Nabla $70M Series C, $120M total funding, 130+ organizations. Company/press-reported (E2).
- npj Digital Medicine (2025) — "Beyond human ears: navigating the uncharted risks of AI scribes in clinical practice." Peer-reviewed risk analysis, hallucination and misattribution rates (E2).
- Zhou et al. — arXiv:2606.00018 (2026), "Examine Clinicians' Modification of Hedging Language in Ambient AI Documentation: A Comparative Study of AI Drafts and Final Notes." Single preprint study, not yet peer-reviewed (E2, single study).
