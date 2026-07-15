---
tags: [concept, domain/adoption-blockers, level/core]
aliases: [data readiness, integration readiness, the boring 80%]
summary: "Siloed, stale, permission-gated data and legacy-system integration decide AI outcomes more than model choice — 60-80%+ of project effort."
---
# Concept - Data and Integration Readiness

> **One-paragraph hook:** Swap in a better model and a broken enterprise AI project usually stays broken, because the thing that was actually blocking it was never the model — it was data the system couldn't reach, couldn't trust, or wasn't allowed to see, and a legacy system it was never wired into. Data and integration readiness is the unglamorous, budget-underweighted work that decides whether a pilot survives contact with production.

## The mechanism

An LLM's output quality is bounded above by the quality and completeness of what it's given — retrieval, tool calls, and context assembly all fail closed if the underlying data is wrong. Three distinct failure surfaces sit under the single label "data readiness":

**Access and freshness.** Enterprise data lives in silos — CRMs, ticketing systems, document stores, EHRs, ERPs — many without a clean API, many stale relative to the system of record. A [[Deep Dive - RAG Architectures]] pipeline is only as good as the corpus it indexes: if that corpus is a six-month-old export rather than a live sync, the model will confidently answer from outdated facts with no signal that anything is wrong.

**Entitlement leakage.** A retrieval or agent system that indexes "everything" will surface whatever the query best matches, regardless of whether the requesting user is authorized to see it — HR files, salary bands, unannounced M&A documents. Document- or row-level access control has to be enforced *at retrieval time*, not bolted on afterward, and most proof-of-concepts skip it because it's invisible until a red-team query (or a real user) finds it (see [[Concept - Enterprise AI Security Exposure]]). This is a harder engineering problem than it looks: it means every chunk in a vector index (see [[Concept - HNSW]] for the underlying retrieval structure) needs entitlement metadata that survives chunking, embedding, and reranking, and the serving layer needs to filter *before* the LLM sees anything the user shouldn't.

**Legacy integration.** Enterprise systems of record — Epic in healthcare, SAP in operations, mainframes in banking — were not built with API-first access in mind, and connecting an AI system to them is frequently a multi-quarter integration project in its own right, independent of anything about the model. Agentic systems raise the stakes further: an agent that needs live tool access to a legacy system (rather than a periodic batch export) needs a protocol and permission boundary for that access — see [[Concept - Model Context Protocol (MCP)]] for the emerging standard, and [[Deep Dive - Agentic Coding in Production]] for what "the model can act, not just read" looks like when it works.

## In practice

The clearest documented case where integration failure, not model failure, killed a flagship deployment is IBM Watson for Oncology at MD Anderson Cancer Center. The collaboration began in 2012 with a fixed-fee contract of $2.4M for a six-month leukemia-treatment advisory tool; it was extended twelve times, and IBM's contracted fees alone reached $39.2M, with ~$23M in further PwC and other vendor costs — roughly $62M total — before the University of Texas System terminated the project in September 2016, four years in (E2/E3, University of Texas System audit report; contemporaneous reporting in Forbes, The Register, and IEEE Spectrum). Two structural failures compounded: the pilot programs were built against MD Anderson's prior records system (ClinicStation) and were never updated to integrate with the hospital's new Epic EHR, so the tool that existed could not reach the live patient data it needed to be clinically useful; and a later STAT News investigation (2018) reported that some of the tool's underlying training relied on synthetic and hypothetical cases rather than real patient data, contributing to recommendations clinicians found unsafe or incorrect (E2, STAT News reporting). The audit's own language was blunt: the system was "not ready for human investigational or clinical use." The lesson generalizes past healthcare — see [[Lore - Failed Enterprise AI Deployments]] for the fuller pattern across Watson, Zillow Offers, and other named flops that fail the same structural way regardless of industry or era.

NANDA's and S&P's 2025 survey data (see [[Concept - The Pilot-to-Production Gap]]) both cite integration and data quality — not model capability — as the top-ranked blockers enterprises report (E2). Practitioner consensus, echoed across vendor and consultancy write-ups of failed deployments, puts the data/integration/permissions work at commonly 60–80%+ of total project effort (E1, diffuse practitioner/consultancy estimate, 2025 — not a measured figure) on a real enterprise AI deployment — the "boring" majority of the project that demos skip entirely and budgets routinely underweight.

## Failure modes

- **Index-everything RAG.** No document-level ACL means the assistant will happily surface a restricted file to an unauthorized user the first time a query matches it — detected only by deliberate red-team queries against known-restricted content (see [[Gotchas - Enterprise AI Adoption]]).
- **Stale-corpus drift.** A RAG index that isn't kept in sync with the source system degrades silently — the failure looks like a hallucination but is actually a freshness bug, and standard eval sets built once at launch won't catch drift that accumulates after (see [[Concept - The Evaluation Gap]]).
- **Legacy system as hard stop.** No amount of prompt engineering fixes a system that literally cannot reach the data it needs, as at MD Anderson — the failure is architectural, not the model's.
- **Underestimated integration timeline.** Teams scope an AI project on model-selection and prompt-design time and treat data/connector work as an afterthought, then blow the budget or timeline on exactly the work they didn't scope.

## The non-obvious

A better model rarely fixes a readiness failure, and this is the single most counterintuitive fact for teams coming from a model-centric mental model of AI progress: the leverage in a real deployment lives in entitlements, connectors, and freshness pipelines, not in swapping GPT-4-class for a newer frontier model. This is exactly why vendor tools that ship with pre-built connectors and entitlement handling for specific systems of record (Salesforce, ServiceNow, Epic) outperform internal builds on the same task — the vendor has already paid the integration tax once and amortizes it across customers, while an internal team pays it fresh (see [[Decision - Build vs Buy vs Wrap]]). It also means the unit economics of a "successful" pilot can be misleading: a small pilot on a clean, hand-picked data subset has none of the entitlement or freshness cost that the full production dataset will impose, so pilot-stage cost and quality numbers routinely fail to predict production numbers (see [[Concept - Unit Economics of LLM Products]]).

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
