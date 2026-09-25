---
tags: [concept, domain/production-ops, level/advanced]
aliases: [PII scrubbing, ZDR, DPA, data residency]
summary: "Where PII leaks through an LLM stack, how redaction/pseudonymization work, and why deletion must propagate to caches and vector stores."
---

> **One-paragraph hook:** Every hop a prompt takes through an LLM stack (a trace store, a semantic cache, a third-party model provider, a vector index) is a place personally identifiable information can leak, get logged indefinitely, or become undeletable in practice after a user asks for it to be gone. PII redaction and data retention means drawing a redaction boundary in the pipeline and making deletion reach every store a copy could have landed in, including the ones you forgot.

## The mechanism

PII enters an LLM stack wherever text does, and fans out from there. There are four surfaces:

1. [[Concept - LLM Observability and Tracing]] itself. Full prompt and completion payloads get copied verbatim into a trace store by default.
2. [[Concept - Semantic Caching]]. A cached (prompt, response) pair keeps the original content indefinitely unless it's explicitly scoped and expired.
3. Upstream: the raw payload sent to a third-party model provider.
4. The vector store behind retrieval, which teams miss most often. Embeddings from an [[Concept - Embedding Models]]-based encoder aren't anonymous because they're floating-point vectors. Embedding-inversion techniques can recover a lot about the source text from the vector alone, so an index holding embeddings of PII-bearing documents holds PII, with the same deletion obligations as the source text.

Detection splits in two. Structured PII (SSNs, credit-card numbers, phone numbers, emails) is caught by high-precision regex. Unstructured PII (names, addresses, organizations) needs a named-entity-recognition model. Common tools are Microsoft Presidio (an analyzer plus anonymizer pipeline combining both), spaCy NER, or a cloud DLP API.

There are two redaction modes. Irreversible masking replaces the span with `[REDACTED_NAME]`, which is fine for anything you'll never need to reconstruct. Reversible pseudonymization swaps the value for a token backed by a vault mapping token → value. A downstream process, including the response shown to the user, can rehydrate the real value on demand, and nothing sensitive persists in logs, caches or third-party payloads. The reversible approach dominates in practice because most production debugging needs the real value at some point. Put the redaction boundary at the *persistence* layer, before anything is written to a log or cache or sent upstream, and don't bake it irretrievably into the data at generation time.

Once a payload leaves your infrastructure, what happens to it is a matter of contract. Zero Data Retention (ZDR) endpoints or agreements mean the provider doesn't keep the payload past serving the request. Enterprise terms with a signed Data Processing Agreement (DPA) typically add no-training-by-default guarantees. Without ZDR, a roughly 30-day default retention window for abuse monitoring is typical. HIPAA-covered workloads need a signed Business Associate Agreement (BAA), and GDPR data-residency requirements push toward EU regional endpoints so payloads never leave the jurisdiction. Data residency and on-prem control are also two of the strongest arguments for self-hosting in [[Decision - Self-Hosting vs Managed LLM API]]. When a DPA and a ZDR endpoint aren't enough, keeping weights and data on infrastructure you control removes the question.

## In practice

A TTL on the trace store is the easy 80% of retention. Most observability backends, including those behind [[Concept - LLM Observability and Tracing]], support a configurable retention window natively. The hard 20% is deletion. A data-subject deletion request has to reach *every* derived store that could hold a copy: the primary trace/log store, the semantic cache and the vector index. A common implementation deletes from the trace database and stops, leaving a queryable copy in the cache or RAG index, and nothing reports the failure. Prove propagation with an audit log of what was requested, when, and which stores were touched. For compliance purposes, deletion you can't demonstrate is the same as no deletion.

Content capture should default to off. The emerging [[Reference - OpenTelemetry GenAI Semantic Conventions]] make full prompt/completion capture opt-in because that payload becomes a PII liability the moment a user pastes something sensitive into a prompt. Beyond technical controls, compliance means SOC2/ISO27001 access-logging and encryption controls, a published sub-processor list naming every downstream vendor that touches data, a documented data-flow map, and, for teams in or serving the EU, the operator obligations summarized in [[Reference - The EU AI Act for Operators]]. The compliance group of [[Checklist - Production LLM Launch Readiness]] is there to confirm all of this is wired before shipping.

## Failure modes

**PII in the cache key.** Hash a raw prompt containing a name or email into the semantic-cache key and the key, which appears in logs, metrics labels and cache-inspection tools, carries the PII even after the cached value is redacted. Key on a redacted or template-normalized form of the prompt.

**Embeddings treated as anonymous.** Leaving the vector store out of a deletion sweep because "it's just numbers" is the single most common miss in practice, for the reason above.

**Partial deletion propagation.** Deletion reaches the primary log store but not the semantic cache or vector index, so a supposedly deleted record is still retrievable with a similar query.

**Full-payload logging by default.** Capturing everything for debuggability with no redaction pass makes the observability stack a standing liability the first time a user pastes a document with sensitive data in it.

**Un-redacted upstream sends without a DPA/ZDR agreement.** Sending PII to a third-party provider without contractual data-handling terms moves liability outside your control, however well your own logging behaves.

A related but separate problem: an attacker using [[Concept - Prompt Injection]] to get a model to echo back another user's cached context or a system prompt. That's adversarial exfiltration, not a data-handling default. The two compound (weak redaction defaults make a successful injection worse) but they need separate defenses.

## The non-obvious

Reversible tokenization (mask on the way in, log only the token, rehydrate the real value on the way back to the user) usually beats blind irreversible redaction. It resolves a tension that looks unsolvable at first: debugging needs the real value to understand what happened, but the logging, caching and provider path never needs to store it. With the redaction boundary at the persistence layer, the vault holding the token↔value mapping becomes the most security-critical service in the stack. It's smaller and less visible than model serving, yet a compromise there defeats every other redaction control at once. Components like that get under-resourced because they don't look like the "real" infrastructure.

## Connections

- [[Concept - LLM Observability and Tracing]] — the primary leak surface: full prompt/completion payloads land here by default unless redaction runs first.
- [[Concept - Semantic Caching]] — a second persistent copy of original content that needs its own TTL and deletion-propagation path.
- [[Concept - Embedding Models]] — the reason vector-store embeddings must be treated as PII rather than anonymous numeric data.
- [[Concept - Prompt Injection]] — the adjacent adversarial exfiltration path that compounds with, but is distinct from, this note's data-handling defaults.
- [[Reference - OpenTelemetry GenAI Semantic Conventions]] — sets the opt-in-by-default posture for prompt/completion content capture that this note's redaction discipline builds on.
- [[Checklist - Production LLM Launch Readiness]] — the pre-flight check that verifies redaction, retention, and DPA/ZDR terms are actually wired before launch.
- [[Decision - Self-Hosting vs Managed LLM API]] — data residency and on-prem control are two of the strongest self-hosting arguments when contractual terms alone aren't sufficient.
- [[Reference - The EU AI Act for Operators]] — the regulatory obligations that shape the compliance layer this note's retention and deletion mechanics have to satisfy for EU-facing operators.

## Sources

- Microsoft Presidio — open-source PII detection and anonymization toolkit (regex + NER analyzer/anonymizer pipeline) referenced above.
- GDPR (Regulation (EU) 2016/679), Article 17 — the right-to-erasure obligation that drives the cross-store deletion-propagation requirement described above.
- OpenAI and Anthropic published enterprise data-handling terms (Zero Data Retention / no-training-by-default policies, as of 2026) — the provider-side contractual mechanisms this note relies on.
