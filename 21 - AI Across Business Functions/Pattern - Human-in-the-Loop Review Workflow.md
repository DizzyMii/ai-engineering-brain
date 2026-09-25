---
tags: [pattern, domain/applied-business, level/advanced]
aliases: [HITL, human-in-the-loop, draft-then-sign, review gate, MTPE workflow]
summary: "Model drafts, qualified human reviews and commits; edit-rate is the quality gate. The shape behind every high-stakes AI deployment."
---

# Pattern - Human-in-the-Loop Review Workflow

> **Problem:** AI output has real-world consequences (a signed clinical note, a filed brief, a client email), and the model isn't reliable enough to act unsupervised. **Solution shape:** the model produces a draft, a qualified human reviews and commits it, and the human's edits are instrumented as the main quality signal.

## Context & forces

Use this when three things hold at once: (1) the output touches a customer, patient, court or ledger, so an error propagates instead of being discarded; (2) the model is *capable* on the task (mostly correct drafts) but not *reliable* enough for autonomy, per [[Concept - The Capability-Reliability Gap]]; (3) a qualified human with the standing to be accountable (licensed clinician, attorney, professional translator, analyst) is already in the workflow.

The forces in tension:

- **Error cost vs. throughput.** A per-item human gate caps volume at human speed and pulls error cost down toward the human's baseline. Remove the gate and throughput explodes, but every model error ships.
- **Where liability sits.** Someone has to own the output legally and professionally. The pattern keeps ownership with the human; the AI is a drafting tool, not the actor of record. So it scales in regulated functions where autonomous action is a non-starter.
- **The reliability floor multiplies.** A "90% capable, 95% reliable" agent still gets it wrong roughly 1 in 20 times. For a consequential output that rules out autonomy, but it's fine for a *suggestion* a human vets: the same 5% shows up as edits, not incidents.

This is the assist/copilot half of the [[Concept - Copilot vs Autopilot Deployment Modes]] split, made concrete and measurable.

## The pattern

```
                     ┌─────────────────────────────────────┐
                     │  sources / context (retrieved docs,  │
                     │  transcript, ticket, contract)       │
                     └──────────────────┬───────────────────┘
                                        ▼
                            ┌───────────────────────┐
                            │  MODEL: generate draft │
                            │  + cite/ground claims  │
                            └───────────┬───────────┘
                                        ▼
        ┌────────────────────────────────────────────────────────┐
        │  HUMAN REVIEW (draft and source side-by-side)          │
        │  accept · edit · reject · escalate                     │
        └───────────┬───────────────────────────┬────────────────┘
                    │ commit                     │ edits logged
                    ▼                             ▼
        ┌───────────────────────┐    ┌──────────────────────────────┐
        │  COMMITTED OUTPUT      │    │  TELEMETRY: edit-rate,        │
        │  (human owns it)       │    │  override-rate, escalation-%  │
        └───────────────────────┘    │  → drift alarm + training      │
                                     │    signal + graduation gate    │
                                     └──────────────────────────────┘
```

Four steps. Teams skip the fourth.

1. **Generate with provenance.** The model drafts *and* attaches the sources it used: retrieved passages, transcript spans, cited authorities. Grounding makes review fast: the reviewer checks the draft against evidence instead of redoing the work. In legal and finance this is a [[Deep Dive - RAG Architectures]] retrieve-then-draft shape.
2. **Put draft and source side by side.** Review cost collapses when the reviewer isn't hunting for the source.
3. **Edit and commit.** The human fixes what's wrong and commits. The human, not the model, is now the author of record.
4. **Log the delta.** Capture every edit as telemetry and training signal. This turns the review gate into a *measurement instrument*, and everything else depends on it.

## Implementation notes

**Edit rate and override rate are your real quality metrics**, not benchmark accuracy: how much humans change the draft in production. A rising edit rate on a query type is the earliest sign of model or data drift, and it shows up *before* customers notice, because the human is absorbing the errors. Instrument it per query type, per document class, per clinician. Watch the distribution, not just the mean. A bimodal edit rate (most drafts untouched, a few rewritten wholesale) is a different failure from a uniform 20% edit rate and needs a different fix.

**Where the human sits sets the economics.** There are two placements:

- *Per-item review* (every scribe note signed, every legal memo read). Safe, caps throughput at human speed, pulls error rate to the human's baseline. Right for consequential, hard-to-reverse outputs.
- *Sampled review* (audit 5% of autopilot resolutions after they ship). Scales past human speed but accepts a known, non-zero error rate on the unaudited 95%. Right only when per-item errors are cheap and reversible.

Choosing between them *is* the copilot-vs-autopilot decision, made per query type instead of per function.

**Graduate on data, not on the calendar.** Move a query type from per-item to sampled review (copilot → autopilot) only when its measured override rate falls below your error-cost threshold, i.e. the residual errors cost less than the review labor. [[Breakdown - Klarna's AI Customer Service Bet]] skipped this, expanded autonomy on a savings demo, and had to walk back (see [[Lore - The Klarna Reversal and Support Bot Walk-Backs]]).

**The trap nobody expects: review theater.** If the UI nudges reviewers toward "accept" (pre-checked boxes, one-click sign-off, no source shown), edit rate collapses toward zero because humans rubber-stamp, not because the model improved. Automation bias is real and measurable: reviewers under time pressure defer to a confident draft. A near-zero edit rate should raise suspicion. Check it with a periodic blind re-review where a second human grades a sample cold. The medical-scribe literature gives a concrete case: research on clinicians *modifying hedging language* in AI drafts shows the signed note really does diverge from the draft, so the edit is substantive, not cosmetic (E2, arXiv/medRxiv 2024–2026). Without a substantive delta, you have autopilot wearing a copilot's badge, and you own errors you don't know about.

## Tradeoffs & when NOT to use

- **Don't use it for low-stakes, reversible output.** For ad-copy variants, internal search summaries or brainstorm lists, mandatory review is pure overhead. Save the gate for consequential or regulated outputs where an error costs more than the review.
- **The gate is a throughput ceiling.** You can't go faster than human review. If volume has to scale past that, you either sample (and accept errors) or improve reliability until graduation is justified. There's no third option that keeps the per-item gate.
- **Reviewer skill decays.** When the model is right 95% of the time, reviewers lose the ability to catch the 5%. The skill that qualifies them to review atrophies because the tool works. Rotate reviewers through unaided work, or the accountable human quietly stops being competent to be accountable.
- **It moves the reliability problem; it doesn't remove it.** The pattern makes an unreliable model *deployable*, not reliable. If the underlying error rate is high, you've shifted the cost into human labor, which can make the AI deployment cost more than the manual process it replaced ([[Concept - The Evaluation Gap]], and Gartner's rising-cost warning).

## Known uses

Four independent functions arrived at the same shape, which is the strongest evidence it's a real pattern and not a vendor slogan:

- **Medical scribes (draft-then-sign).** Ambient AI drafts the clinical note; the clinician reviews, edits, signs and stays legally accountable. Kaiser Permanente / The Permanente Medical Group reported 15,791 documentation-hours saved across 7,260 physicians and ~2.5M patient encounters over Oct 2023–Dec 2024 (E2, single-system study, Tierney et al., NEJM Catalyst 2025). See [[Breakdown - AI Medical Scribes]].
- **Legal drafting (mandatory review).** [[Breakdown - Harvey and AI in Legal Work]] drafts research memos and contract redlines that a licensed lawyer reviews and owns. Review is non-negotiable because unreviewed legal output carries direct liability (the *Mata v. Avianca* fake-citation sanctions; see [[Lore - Hallucination Liability Incidents]]). Harvey reached an $11B valuation by March 2026 (E2) selling this contract.
- **Translation post-editing (MTPE).** The machine drafts and a professional translator edits; [[Concept - Machine Translation and the Localization Industry]] turned translators into post-editors instead of eliminating them.
- **Enterprise knowledge work.** JPMorgan's LLM Suite drafts and summarizes for 200,000+ employees who edit and own the output (E2, JPMorgan/CNBC 2025; see [[Concept - AI in Finance Operations]]). A finance firm won't let a model move money or send client mail on its own.

## Connections

- [[Concept - Copilot vs Autopilot Deployment Modes]] — this pattern is the copilot mode instrumented; the graduation criterion is how a slice crosses to autopilot.
- [[Concept - The Capability-Reliability Gap]] — the gap is *why* the human gate exists; capable-but-unreliable is exactly the regime this pattern deploys.
- [[Concept - Support Deflection Economics]] — the sampled-review economics is the support-automation cost model; edit/override-rate is the honest counterpart to deflection rate.
- [[Breakdown - AI Medical Scribes]] — the cleanest real-world instance: draft-then-sign with measured time-savings.
- [[Breakdown - Harvey and AI in Legal Work]] — mandatory-review instance where the liability makes the gate non-optional.
- [[Concept - Vertical AI Agents by Function]] — every "autonomous" vertical agent that actually works still has this review/escalation gate underneath the autonomy marketing.
- [[Lore - The Klarna Reversal and Support Bot Walk-Backs]] — the war story of expanding autonomy *without* the graduation discipline this pattern demands.
- [[Concept - The Evaluation Gap]] — edit-rate/override-rate telemetry is the in-production eval that the gap describes as usually missing.
- [[Gotchas - Enterprise AI Adoption]] — review-theater and reviewer skill-decay are recurring enterprise adoption traps.

## Sources

- Tierney et al. (2024–2025) — NEJM Catalyst, ambient AI documentation at The Permanente Medical Group. The strongest measured time-savings evidence for draft-then-sign (E2, single-system).
- arXiv / medRxiv (2024–2026) — studies on clinician editing of AI-drafted notes, including hedging-language modification. Evidence that the human edit is substantive, not cosmetic (E2).
- Harvey.ai / CNBC / Bloomberg (Mar 2026) — Harvey $11B valuation round. Evidence of scale for the mandatory-review legal deployment (E2, announced round).
- JPMorgan / CNBC (2025) — LLM Suite reaching 200,000+ employees as an internal review-and-edit copilot (E2, company-reported).
