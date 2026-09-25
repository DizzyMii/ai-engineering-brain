---
tags: [concept, domain/adoption-blockers, level/core]
aliases: [data readiness, integration readiness, the boring 80%]
summary: "Siloed, stale, permission-gated data and legacy-system integration decide AI outcomes more than model choice — 60-80%+ of project effort."
---
# Concept - Data and Integration Readiness

> **One-paragraph hook:** Swap in a better model and a broken enterprise AI project usually stays broken. The model was never what blocked it. The blocker was data the system couldn't reach, couldn't trust or wasn't allowed to see, plus a legacy system it was never wired into. Data and integration readiness is the unglamorous, under-budgeted work that decides whether a pilot survives production.

## The mechanism

An LLM's output can't be better than what it's given. Retrieval, tool calls and context assembly all fail closed when the underlying data is wrong. "Data readiness" covers three separate failure surfaces.

**Access and freshness.** Enterprise data sits in silos (CRMs, ticketing systems, document stores, EHRs, ERPs), many without a clean API and many stale against the system of record. A [[Deep Dive - RAG Architectures]] pipeline is only as good as the corpus it indexes. If that corpus is a six-month-old export instead of a live sync, the model answers confidently from outdated facts and nothing signals the problem.

**Entitlement leakage.** A retrieval or agent system that indexes "everything" surfaces whatever best matches the query, whether or not the user may see it: HR files, salary bands, unannounced M&A documents. Document- or row-level access control has to be enforced *at retrieval time*, not bolted on later. Most proofs of concept skip it because it's invisible until a red-team query (or a real user) hits it (see [[Concept - Enterprise AI Security Exposure]]). It's harder than it looks. Every chunk in a vector index (see [[Concept - HNSW]] for the retrieval structure) needs entitlement metadata that survives chunking, embedding and reranking, and the serving layer has to filter *before* the LLM sees anything the user shouldn't.

**Legacy integration.** Systems of record (Epic in healthcare, SAP in operations, mainframes in banking) weren't built for API-first access. Connecting an AI system to them is often a multi-quarter integration project on its own, independent of the model. Agents raise the stakes. An agent that needs live tool access to a legacy system, not a periodic batch export, needs a protocol and a permission boundary for it. [[Concept - Model Context Protocol (MCP)]] is the emerging standard, and [[Deep Dive - Agentic Coding in Production]] shows what "the model can act, not just read" looks like when it works.

## In practice

The clearest documented case of integration failure, not model failure, killing a flagship deployment is IBM Watson for Oncology at MD Anderson Cancer Center. It began in 2012 as a fixed-fee $2.4M contract for a six-month leukemia-treatment advisory tool. The contract was extended twelve times. IBM's contracted fees alone reached $39.2M, with ~$23M more in PwC and other vendor costs, roughly $62M total, before the University of Texas System terminated the project in September 2016, four years in (E2/E3, University of Texas System audit report; contemporaneous reporting in Forbes, The Register, and IEEE Spectrum).

Two failures compounded. The pilot programs were built against MD Anderson's prior records system (ClinicStation) and never updated for the hospital's new Epic EHR, so the tool couldn't reach the live patient data it needed to be clinically useful. And a later STAT News investigation (2018) reported that some of its training relied on synthetic and hypothetical cases instead of real patient data, contributing to recommendations clinicians found unsafe or incorrect (E2, STAT News reporting). The audit put it bluntly: the system was "not ready for human investigational or clinical use." This isn't a healthcare-only lesson. [[Lore - Failed Enterprise AI Deployments]] has the fuller pattern across Watson, Zillow Offers and other named flops that fail the same way regardless of industry or era.

NANDA's and S&P's 2025 survey data (see [[Concept - The Pilot-to-Production Gap]]) both rank integration and data quality, not model capability, as the top blockers enterprises report (E2). Practitioner consensus, repeated across vendor and consultancy write-ups of failed deployments, puts data/integration/permissions work at commonly 60–80%+ of total effort on a real enterprise AI deployment (E1, diffuse practitioner/consultancy estimate, 2025; not a measured figure). That's the "boring" majority of the project, the part demos skip entirely and budgets routinely underweight.

## Failure modes

- **Index-everything RAG.** Without document-level ACLs, the assistant will happily surface a restricted file to an unauthorized user the first time a query matches it. Only deliberate red-team queries against known-restricted content catch it (see [[Gotchas - Enterprise AI Adoption]]).
- **Stale-corpus drift.** A RAG index that falls out of sync with the source system degrades silently. It looks like hallucination but it's a freshness bug, and eval sets built once at launch won't catch drift that accumulates afterward (see [[Concept - The Evaluation Gap]]).
- **Legacy system as hard stop.** No prompt engineering fixes a system that can't reach the data it needs, as at MD Anderson. The failure is in the architecture, not the model.
- **Underestimated integration timeline.** Teams scope an AI project on model selection and prompt design, treat data/connector work as an afterthought, then blow the budget or timeline on the work they didn't scope.

## The non-obvious

A better model rarely fixes a readiness failure. For teams used to thinking of AI progress as model progress, that's the most counterintuitive fact here: in a real deployment the payoff is in entitlements, connectors and freshness pipelines, not in swapping a GPT-4-class model for a newer frontier one. It explains why vendor tools that ship with pre-built connectors and entitlement handling for specific systems of record (Salesforce, ServiceNow, Epic) outperform internal builds on the same task. The vendor paid the integration tax once and spreads it across customers; an internal team pays it fresh (see [[Decision - Build vs Buy vs Wrap]]).

It also makes "successful" pilot economics misleading. A small pilot on a clean, hand-picked data subset carries none of the entitlement or freshness cost the full production dataset will, so pilot-stage cost and quality numbers routinely fail to predict production (see [[Concept - Unit Economics of LLM Products]]).

## Connections
- [[Concept - The Pilot-to-Production Gap]] — data/integration readiness is the concrete work NANDA's survey data identifies as the top blocker, ahead of model quality.
- [[Concept - The Evaluation Gap]] — stale or entitlement-broken data produces failures that look like model errors and are only distinguishable with a proper eval set.
- [[Gotchas - Enterprise AI Adoption]] — entitlement leakage in RAG is one of the highest-damage, most common pitfalls this concept explains mechanically.
- [[Playbook - Crossing the Pilot-to-Production Gap]] — Step 2 of the crossing procedure is exactly this: connect systems of record, enforce entitlements, verify freshness, before launch.
- [[Concept - Enterprise AI Security Exposure]] — entitlement leakage is a security failure as much as a data-quality one; both stem from indexing without access control.
- [[Lore - Failed Enterprise AI Deployments]] — MD Anderson Watson for Oncology is the named, documented case this concept's central example draws on.
- [[Decision - Build vs Buy vs Wrap]] — vendor tools amortize integration cost across customers, which is the concrete mechanism behind the buy-vs-build success asymmetry.
- [[Concept - Unit Economics of LLM Products]] — pilot-stage economics on clean data don't predict production economics once real entitlement and freshness costs appear.
- [[Deep Dive - Agentic Coding in Production]] — the sharpest current example of "the model needs live, permissioned access to a real system," not just a static corpus.
- [[Deep Dive - RAG Architectures]] — the pipeline whose output quality is bounded by exactly the readiness factors this concept covers.
- [[Concept - Model Context Protocol (MCP)]] — the emerging standard for giving models permissioned, live access to legacy and modern systems alike.
- [[Concept - HNSW]] — the retrieval index structure that entitlement metadata has to survive intact through chunking and embedding.

## Sources
- University of Texas System — internal audit report on the MD Anderson–IBM Watson for Oncology collaboration (surfaced Feb 2017); terms, cost figures ($39.2M IBM, ~$23M PwC), and the "not ready for clinical use" finding.
- Forbes — Matthew Herper, "MD Anderson Benches IBM Watson In Setback For Artificial Intelligence In Medicine" (19 Feb 2017).
- The Register — "Watson can't cure cancer ... or all the stuff that breaks IT projects" (20 Feb 2017) — audit findings and ClinicStation/Epic integration gap.
- IEEE Spectrum — "How IBM Watson Overpromised and Underdelivered on AI Health Care" — retrospective on the project's structural failures.
- STAT News (2018) — investigation reporting on synthetic-case training data and unsafe/incorrect recommendation concerns.
