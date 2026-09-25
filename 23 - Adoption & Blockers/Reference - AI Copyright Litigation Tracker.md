---
tags: [reference, domain/adoption-blockers, level/advanced]
aliases: [AI copyright cases, AI training lawsuits, fair use AI tracker, Bartz Anthropic settlement]
summary: "Date-stamped table of the major AI-training copyright cases: holdings, status, and what each means for deployers."
---
# Reference - AI Copyright Litigation Tracker

*All entries current as of mid-2026 (2026-07). Litigation is volatile; verify docket status before relying on any entry.*

## Case table

| Case | Court / Judge | Key ruling | Date | Status (mid-2026) | Tier |
|---|---|---|---|---|---|
| **Bartz v. Anthropic** | N.D. Cal. / Alsup | Training on *lawfully acquired* books = fair use; using *pirated* copies (LibGen/PiLiMi) = **not** fair use | Order 23 Jun 2025 | Class certified Aug 2025; **$1.5B settlement**, prelim. approval 25 Sep 2025; final-approval hearing 2026 | E3 |
| **Thomson Reuters v. Ross Intelligence** | D. Del. / Bibas¹ | **First** US ruling **rejecting** a fair-use defense for AI training data; 2,243 Westlaw headnotes infringed | 11 Feb 2025 | Headed toward damages/appeal; expressly limited to **non-generative** AI | E3 |
| **NYT v. OpenAI & Microsoft** | S.D.N.Y. / Stein | Motions to dismiss **largely denied**: core copyright claims survive; most DMCA claims dismissed | MTD 26 Mar 2025 | Active discovery; contested ChatGPT-log production²; SJ briefing to close ~2 Apr 2026; **no trial date** | E3 |
| **Kadrey v. Meta** | N.D. Cal. / Chhabria | Summary judgment **for Meta** on fair use, but on **narrow** grounds (plaintiffs failed to prove market harm/dilution) | 25 Jun 2025 | Explicitly **not** a blanket blessing; dicta invite a stronger "market dilution" record next time | E3 |
| **Getty Images v. Stability AI (UK)** | UK High Court | Core copyright **training claims rejected/abandoned**³; model weights held **not a "copy"**; narrow trademark win for Getty | 4 Nov 2025 | Getty granted leave to appeal (Dec 2025); US case separately narrowed | E3 |
| **Andersen v. Stability AI** | N.D. Cal. / Orrick | Core copyright claims **survived** dismissal; "model theory," distribution, and trade-dress theories held plausible | MTD ruling Aug 2024 | Ongoing in discovery; testing **output-similarity** theories vs Stability/Midjourney/DeviantArt | E3 |

¹ Judge Stephanos Bibas, a Third Circuit judge sitting by designation on the district court.
² Magistrate ordered production of a 20-million-conversation ChatGPT log sample (Nov 2025); the district judge affirmed 5 Jan 2026 over OpenAI's objection. A preservation order briefly required OpenAI to retain billions of user conversations.
³ Getty dropped its primary UK training claim on **territorial** grounds: it couldn't establish that reproduction/storage happened *in the UK*. So the court never decided whether training on protected images infringes as a matter of law. Jurisdiction, not merits.

## The fault line: provenance vs output

| Risk axis | What loses | What (so far) survives |
|---|---|---|
| **Data provenance** | Training on **pirated** corpora (shadow libraries); Bartz drew the line here and it cost $1.5B | Training on **lawfully acquired / licensed** copies |
| **Use character** | Building a tool that **directly substitutes** for the source's market; Ross competed with Westlaw | Uses held **transformative** where no market substitution was proven (Kadrey, Bartz-on-lawful-copies) |
| **Output** | Generations that **reproduce** a recognizable source (the live NYT theory; Andersen's output-similarity claims) | Abstract statistical learning that emits no recognizable expression |
| **Jurisdiction** | US courts increasingly reach the merits | UK court declined on territoriality; venue changes the answer |

## Operator implications (date-stamped mid-2026)

- **Provenance is the fault line.** Piracy loses even where training wins, so [[Concept - The Pilot-to-Production Gap|deployment]] on a model trained on shadow-library data inherits legal risk. Ask vendors how their training corpus was *acquired* as well as what it contains. The provenance discipline [[Concept - Deduplication at Scale|corpus curation]] applies for quality now applies for liability too.
- **For deployers, output reproduction is the live risk, more than training.** Your exposure is less "the model was trained on X" than "the model *emitted* a near-verbatim X to my customer." Grounding, retrieval-with-citation and output filtering reduce it, the same controls that limit [[Lore - Hallucination Liability Incidents|hallucination liability]].
- **Vendor indemnification is now a standard procurement ask.** Microsoft (Copilot Copyright Commitment), Google, Anthropic and OpenAI offer copyright indemnities in varying forms with varying carve-outs (generally excluding cases where *you* disable guardrails or knowingly infringe). Read the carve-outs. They're a core input to [[Decision - Build vs Buy vs Wrap|build-vs-buy]].
- **[[Concept - Synthetic Training Data|Synthetic data]] and licensed data are the industry's answer.** Less dependence on scraped corpora is now a legal strategy as well as a data-wall strategy.
- **The EU uses a different lever:** GPAI training-data-summary and copyright-policy obligations instead of case law. See [[Reference - The EU AI Act for Operators]].

## Connections
- [[Reference - The EU AI Act for Operators]] — the EU regulates AI-training copyright via GPAI transparency duties, a parallel track to this US/UK case law.
- [[Lore - Hallucination Liability Incidents]] — the output-reproduction risk here is the same controllability problem as confident-error liability.
- [[Gotchas - Enterprise AI Adoption]] — inherited provenance risk is a real deployment pitfall, not an abstraction.
- [[Concept - The Pilot-to-Production Gap]] — legal review is a production-gating step pilots routinely skip.
- [[Lore - Failed Enterprise AI Deployments]] — legal/provenance blowups belong in the same graveyard of operator lessons.
- [[Decision - Build vs Buy vs Wrap]] — indemnity terms and provenance shift the build-vs-buy calculus directly.
- [[Reference - The 2026 Navigation Cheatsheet]] — the fast operator lookup this tracker feeds.
- [[Concept - Deduplication at Scale]] — corpus-curation discipline is now a liability control, not only a quality one.
- [[Concept - Synthetic Training Data]] — the structural workaround for scraped-corpus legal exposure.
- [[Reference - Where Real AI Knowledge Lives]] — where to track these dockets as they move.

## Sources
- *Bartz v. Anthropic*, N.D. Cal. — Alsup order (23 Jun 2025); settlement preliminary approval (25 Sep 2025); Authors Alliance / Authors Guild settlement analyses.
- *Thomson Reuters Enterprise Centre GmbH v. Ross Intelligence Inc.*, No. 1:20-cv-613 (D. Del. 11 Feb 2025) — Bibas opinion; Davis Wright Tremaine, Perkins Coie analyses.
- *NYT v. Microsoft & OpenAI*, No. 1:23-cv-11195 (S.D.N.Y.) — MTD order 26 Mar 2025; log-production orders Nov 2025 / affirmed 5 Jan 2026; Wikipedia docket summary, McKool Smith updates.
- *Kadrey v. Meta Platforms*, N.D. Cal. — Chhabria SJ order 25 Jun 2025; Goodwin, Perkins Coie client alerts.
- *Getty Images v. Stability AI*, UK High Court, 4 Nov 2025 — Mayer Brown, Bird & Bird, DLA Piper analyses; Getty statement.
- *Andersen v. Stability AI*, N.D. Cal. — Orrick MTD ruling Aug 2024; Copyright Alliance, Loeb & Loeb summaries.
