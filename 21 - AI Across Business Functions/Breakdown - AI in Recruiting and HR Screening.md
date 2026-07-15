---
tags: [breakdown, domain/applied-business, level/advanced]
aliases: [AI hiring bias, resume screening AI, HireVue, algorithmic hiring]
summary: "HR & recruiting AI — where the field's oldest documented failure (algorithmic bias) meets active discrimination litigation and high-risk regulation."
---

# Breakdown - AI in Recruiting and HR Screening
> Resume screening, video-interview scoring, and candidate sourcing are the function where AI's oldest and best-documented failure — algorithmic bias — collides with active discrimination litigation and regulation that reclassifies the whole category as high-risk. Unlike medical scribes or legal copilots, this is a cautionary deployment: the flagship "wins" are the ones that got scrapped or sued. (Assessed as of 2026-07.)

## The headline numbers

| Item | Fact | Tier |
|---|---|---|
| Amazon recruiting tool | Built 2014-2017, scrapped 2018 for penalizing women | E3 (Reuters/Dastin, widely reported) |
| Mobley v. Workday | Collective action certified (ADEA), May 2025 | E2/E3 (N.D. Cal. filings) |
| Applications in Workday scope | ~1.1B rejected via its tools in the relevant period | E2 (Workday's own representation) |
| EU AI Act | Employment AI = high-risk (Annex III §4); obligations deferred to 2 Dec 2027 (Digital Omnibus, agreed June 2026; classification unchanged) | E3 (regulatory text) |
| NYC Local Law 144 | Annual independent bias audit, publicly posted | E3 (statute, in force since 2023) |

## How it actually works — and how it fails

The canonical failure is Amazon's. Between 2014 and 2017 it built a model to score applicants, trained on a decade of the company's own resumes — overwhelmingly from men in a male-skewed tech labor pool. The model learned to **penalize the token "women's"** (as in "women's chess club captain") and to downgrade graduates of two all-women's colleges, while rewarding masculine-coded verbs. Amazon patched the obvious terms in 2015, could not guarantee the model wouldn't find new proxies, and scrapped it in 2018 (E3, Reuters, 2018).

```mermaid
flowchart TD
    A[Historical hiring decisions<br/>decade of male-skewed data] --> B[Train supervised ranker<br/>label = 'was this person hired?']
    B --> C[Model learns the pattern faithfully]
    C --> D{Bias lives in the labels,<br/>not a code bug}
    D --> E[Penalizes 'women's', all-women colleges]
    D --> F[Remove protected attribute?]
    F --> G[Proxies remain: zip code, college,<br/>hobbies, name, gap years]
    G --> C
```

The mechanism is the whole lesson: **the model did not malfunction — it faithfully learned the historical pattern in the training data.** Bias was in the labels ("who did we hire before"), not a bug to patch. That is why HR is the permanent cautionary tale for supervised AI on human-outcome decisions: you are asking a model to reproduce a distribution that was itself discriminatory, and it obliges.

## The clever parts — i.e., why it keeps getting deployed anyway

- **Top-of-funnel volume is genuinely crushing.** A single posting can draw thousands of applicants; resume ranking, screening chatbots, and video-interview scoring (HireVue-style) exist because human review does not scale to that volume. The pull is real, which is why the category persists despite the risk.
- **The safe subset is large.** Administrative HR work — drafting job descriptions, interview scheduling, summarizing candidate notes, answering employee policy questions from an HR knowledge base — is low-stakes, reversible, human-reviewed, and productive. This is ordinary [[Concept - Copilot vs Autopilot Deployment Modes|copilot]] work with none of the litigation surface.
- The distinction that matters: **assisting HR staff is fine; ranking or rejecting humans is the regulated, litigable core.** The function splits cleanly into a safe copilot half and a high-risk decisioning half, and only the second half is the problem.

## What it got wrong / what's dated

The risk moved from PR embarrassment to **direct litigation**. In *Mobley v. Workday* (N.D. Cal.), plaintiff Derek Mobley — Black, over 40, over 100 applications rejected — sued Workday itself. In July 2024 Judge Rita Lin denied the motion to dismiss, holding Workday could be liable as an **"agent"** of the employers using its screening tools; in May 2025 she granted preliminary collective certification under the ADEA for applicants 40+ (E2/E3, court filings). Workday's own filing conceded ~1.1 billion applications were rejected via its tools in the relevant window, so the potential class is enormous. The novel legal theory — that the **AI vendor**, not just the employer, is directly liable — is what makes this the case the whole sector watches.

Regulation reclassifies the category. The EU AI Act designates employment and worker-management AI as **high-risk under Annex III §4**, imposing technical documentation, logging, risk management, bias testing, and human-oversight obligations; high-risk provisions were pushed from 2 Aug 2026 to 2 Dec 2027 by the EU Digital Omnibus (Council approved 29 June 2026), though the Annex III classification is settled law (E3). NYC **Local Law 144** (in force since 2023) already requires an annual independent **bias audit** of any automated employment decision tool, testing disparate impact across race/ethnicity/sex, publicly posted (E3). This is exactly the "regulated function drops down the automation list regardless of volume" rule from [[Decision - Which Business Function to Automate First]].

The non-obvious, hardest-earned point: **"debiasing" a screening model is not a solved technical fix.** Removing protected attributes (gender, race) leaves *proxies* — zip code, college, hobbies, name, employment gaps — that reconstruct the protected class statistically. You cannot scrub your way to fairness because the correlation lives in the joint distribution, not in one deletable column. The durable answer is **human-in-the-loop plus audit**, not a cleaner model — a governance answer, not a modeling one. This makes candidate ranking a worst-case instance of the [[Concept - The Capability-Reliability Gap|capability-reliability gap]] (domain 20): even a capable ranker cannot be trusted to be *fair* enough for an irreversible, protected-class decision.

## What to steal

- **Deploy AI to HR administration, gate it hard away from candidate decisioning.** Draft, schedule, summarize, answer policy questions — do not let it rank or reject.
- **If you must score candidates, instrument the human-in-the-loop and the audit first**, not as an afterthought; the audit is now a legal obligation, not a nicety ([[Pattern - Human-in-the-Loop Review Workflow]]).
- **Assume proxies survive attribute removal.** Test for disparate impact on outputs, not for the presence of protected fields in inputs.
- **Treat the vendor-liability theory of Mobley as live.** Building or buying screening AI now carries the employer's *and* potentially the vendor's discrimination exposure.

## Connections
- [[Concept - The Front-Office Back-Office Adoption Split]] — HR splits into safe back-office admin and high-liability candidate decisioning; only the latter is blocked.
- [[Concept - Copilot vs Autopilot Deployment Modes]] — the safe HR wins are copilot admin tasks; autopilot ranking of humans is the litigable core.
- [[Pattern - Human-in-the-Loop Review Workflow]] — the durable answer to bias is human review plus audit, not a cleaner model.
- [[Concept - AI in Finance Operations]] — the parallel back-office function where governance and data access, not model capability, are the binding constraint.
- [[Reference - AI Impact by Business Function]] — HR is the cautionary row of the cross-function matrix.
- [[Concept - Vertical AI Agents by Function]] — vertical HR agents face the same bias-plus-regulation ceiling that bounds full autonomy here.
- [[Decision - Which Business Function to Automate First]] — regulated human-outcome decisions drop to the bottom of the automation list regardless of volume.
- [[Lore - Hallucination Liability Incidents]] — the liability-from-AI-output pattern; here it is discrimination, not fabrication (domain 23).
- [[Reference - The EU AI Act for Operators]] — the high-risk classification and its obligations for employment AI (domain 23).
- [[Gotchas - Enterprise AI Adoption]] — bias, proxies, and audit obligations are recurring enterprise-deployment traps (domain 23).
- [[Concept - The Evaluation Gap]] — measuring fairness on outputs, not inputs, is a specialized eval problem most teams skip (domain 23).
- [[Concept - The Capability-Reliability Gap]] — a capable ranker still cannot be trusted fair enough for an irreversible protected-class decision (domain 20).

## Sources
- Dastin, J. (2018) — "Amazon scraps secret AI recruiting tool that showed bias against women," Reuters. The canonical failure, E3.
- Mobley v. Workday, Inc., N.D. Cal. (3:23-cv-00770) — motion-to-dismiss denial (Jul 2024, "agent" theory) and collective certification (May 2025). Court record, E2/E3.
- EU AI Act, Annex III §4 (employment/worker-management as high-risk); high-risk obligations deferred to 2026-12-02 by the Digital Omnibus. Regulatory text, E3.
- NYC Local Law 144 (2021, effective 2023) — mandatory annual bias audit for automated employment decision tools. Statute, E3.
