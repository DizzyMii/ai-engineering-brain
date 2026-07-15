---
tags: [pattern, domain/applied-business, level/advanced]
aliases: [HITL, human-in-the-loop, draft-then-sign, review gate, MTPE workflow]
summary: "Model drafts, qualified human reviews and commits; edit-rate is the quality gate. The shape behind every high-stakes AI deployment."
---

# Pattern - Human-in-the-Loop Review Workflow

> **Problem:** AI output has real-world consequences (a signed clinical note, a filed brief, a client email) but the model is not reliable enough to act unsupervised. **Solution shape:** the model produces a draft, a qualified human reviews and commits it, and the human's edits are instrumented as the primary quality signal.

## Context & forces

Apply this when three things are true at once: (1) the output touches a customer, patient, court, or ledger — an error propagates instead of being silently discarded; (2) the model is *capable* on the task (produces mostly-correct drafts) but not *reliable* enough for autonomy — the [[Concept - The Capability-Reliability Gap]]; and (3) a qualified human already exists in the workflow with the standing to be accountable (a licensed clinician, an attorney, a professional translator, an analyst).

The forces in tension:

- **Error cost vs. throughput.** A per-item human gate caps volume at human speed but drives error cost toward the human's baseline. Remove the gate and throughput explodes but every model error ships.
- **Liability location.** Someone must own the output legally and professionally. The pattern deliberately keeps ownership on the human — the AI is a drafting tool, not the actor of record. This is why it scales in regulated functions where autonomous action is a non-starter.
- **The reliability floor is multiplicative, not additive.** A "90% capable, 95% reliable" agent still emits a wrong result roughly 1 in 20 times. For a consequential output that rate is disqualifying for autonomy but perfectly fine as a *suggestion* a human vets — the same 5% surfaces as edits, not incidents.

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

Four steps, and the fourth is the one teams skip:

1. **Generate with provenance.** The model drafts *and* attaches the sources it used (retrieved passages, transcript spans, cited authorities). Grounding is what makes review fast — the reviewer checks the draft against evidence rather than re-doing the work. In legal and finance this is a [[Deep Dive - RAG Architectures]] retrieve-then-draft shape.
2. **Review with draft and source co-located.** The human sees the draft next to what it was built from. Review cost collapses when the reviewer isn't hunting for the source themselves.
3. **Edit and commit.** The human changes what's wrong and commits. The human — not the model — is now the author of record.
4. **Log the delta.** Every edit is captured as telemetry and as training signal. This is the load-bearing step: it turns the review gate into a *measurement instrument*.

## Implementation notes

**Edit-rate / override-rate is your real quality metric.** Not benchmark accuracy — how much humans actually change the draft in production. A rising edit-rate on a query type is the earliest signal of model or data drift, and it fires *before* customers notice, because the human is absorbing the errors. Instrument it per query type, per document class, per clinician. Watch the distribution, not just the mean — a bimodal edit-rate (most drafts untouched, a few rewritten wholesale) is a different failure than a uniform 20% edit-rate and needs different fixes.

**Where the human sits sets the economics.** Two placements:

- *Per-item review* (every scribe note signed, every legal memo read): safe, caps throughput at human speed, drives error rate to the human's baseline. This is correct for consequential, hard-to-reverse outputs.
- *Sampled review* (audit 5% of already-shipped autopilot resolutions): scales past human speed but accepts a known, non-zero error rate on the unaudited 95%. Correct only when per-item errors are cheap and reversible.

The choice between them *is* the copilot-vs-autopilot decision, made per query type rather than per function.

**Graduation is data-driven, not calendar-driven.** Move a query type from per-item to sampled (copilot → autopilot) only when its measured override-rate falls below your error-cost threshold — i.e., when the residual errors on that slice cost less than the review labor. This is the discipline [[Breakdown - Klarna's AI Customer Service Bet]] skipped: it expanded autonomy on a savings demo instead of on measured override-rate, and had to walk back (see [[Lore - The Klarna Reversal and Support Bot Walk-Backs]]).

**The non-obvious trap: review theater.** If the UI nudges the reviewer to click "accept" — pre-checked boxes, one-click sign-off, no source shown — edit-rate collapses toward zero not because the model got better but because humans rubber-stamp. Automation bias is real and measurable: reviewers under time pressure defer to a confident draft. A near-zero edit-rate should trigger suspicion, not celebration; sanity-check it against a periodic blind re-review where a second human grades a sample cold. The medical-scribe literature makes this concrete — research on clinicians *modifying hedging language* in AI drafts shows the signed note genuinely diverges from the draft, i.e., the edit is substantive, not cosmetic (E2, arXiv/medRxiv 2024–2026). When you can't demonstrate a substantive delta, you have autopilot wearing a copilot's badge, and you own the errors without knowing it.

## Tradeoffs & when NOT to use

- **Do not use for low-stakes, reversible output.** Draft ad-copy variants, internal search summaries, brainstorm lists — mandatory review here is pure overhead that destroys the throughput advantage. Reserve the gate for consequential or regulated outputs where an error costs more than the review.
- **The gate is a throughput ceiling.** You cannot exceed human review speed. If volume must scale past that, you must either sample (accept error) or improve reliability until graduation is justified — there is no third option that keeps the per-item gate.
- **Reviewer skill decay.** When the model is right 95% of the time, reviewers lose the muscle to catch the 5% — the skill that qualifies them to review atrophies precisely because the tool works. Rotate reviewers through unaided work, or the accountable human quietly stops being competent to be accountable.
- **It transfers, not eliminates, the reliability problem.** The pattern makes an unreliable model *deployable*; it does not make it reliable. If the underlying error rate is high, you've just moved the cost into human labor — which can make the AI deployment more expensive than the manual process it replaced (the [[Concept - The Evaluation Gap]] and Gartner's rising-cost warning).

## Known uses

Four independent functions converged on the identical shape, which is the strongest evidence it's a real pattern and not a vendor slogan:

- **Medical scribes (draft-then-sign).** Ambient AI drafts the clinical note; the clinician reviews, edits, signs, and remains legally accountable. Kaiser Permanente / The Permanente Medical Group reported 15,791 documentation-hours saved across 7,260 physicians and ~2.5M patient encounters over Oct 2023–Dec 2024 (E2, single-system study, Tierney et al., NEJM Catalyst 2025). See [[Breakdown - AI Medical Scribes]].
- **Legal drafting (mandatory review).** [[Breakdown - Harvey and AI in Legal Work]] drafts research memos and contract redlines that a licensed lawyer reviews and owns — non-negotiable because unreviewed legal output carries direct liability (the *Mata v. Avianca* fake-citation sanctions; see [[Lore - Hallucination Liability Incidents]]). Harvey reached an $11B valuation by March 2026 (E2) selling exactly this contract.
- **Translation post-editing (MTPE).** The machine drafts, a professional translator edits — the [[Concept - Machine Translation and the Localization Industry]] restructured translators into post-editors rather than eliminating them.
- **Enterprise knowledge work.** JPMorgan's LLM Suite drafts and summarizes for 200,000+ employees to edit and own (E2, JPMorgan/CNBC 2025) — see [[Concept - AI in Finance Operations]]; a finance firm will not let a model autonomously move money or send client mail.

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
