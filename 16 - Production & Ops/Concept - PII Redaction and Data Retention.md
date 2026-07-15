---
tags: [concept, domain/production-ops, level/advanced]
aliases: [PII scrubbing, ZDR, DPA, data residency]
summary: "Where PII leaks through an LLM stack, how redaction/pseudonymization work, and why deletion must propagate to caches and vector stores."
---

> **One-paragraph hook:** Every hop a prompt takes through an LLM stack — into a trace store, into a semantic cache, out to a third-party model provider, into a vector index — is a place personally identifiable information can leak, get logged indefinitely, or become undeletable in practice even after a user asks for it to be gone. PII redaction and data retention is the discipline of drawing a redaction boundary in the pipeline and making deletion actually propagate to every store a copy could have landed in, not just the one you remembered.

## The mechanism

PII enters an LLM stack wherever text does, and it fans out from there. The most obvious surface is [[Concept - LLM Observability and Tracing]] itself: full prompt and completion payloads copied verbatim into a trace store by default. The second is [[Concept - Semantic Caching]] — a cached (prompt, response) pair persists the original content indefinitely unless explicitly scoped and expired. The third is upstream: the raw payload sent to a third-party model provider. The fourth, and the one teams most often miss, is the vector store behind retrieval: embeddings produced by an [[Concept - Embedding Models]]-based encoder are not anonymous just because they're floating-point vectors rather than text — embedding-inversion techniques can recover substantial information about the source text from the vector alone, so a vector index holding embeddings of PII-bearing documents has to be treated as holding PII, with the same deletion obligations as the source text.

Detection splits into structured PII (SSNs, credit-card numbers, phone numbers, emails — high-precision regex) and unstructured PII (names, addresses, organizations — requiring a named-entity-recognition model), commonly via Microsoft Presidio (an analyzer plus anonymizer pipeline combining both approaches), spaCy NER, or a cloud DLP API. Two redaction modes exist: irreversible masking (replace the span with `[REDACTED_NAME]`, fine for anything you never need to reconstruct) and reversible pseudonymization (swap the value for a token backed by a vault mapping token → value, so a downstream process — including the response shown back to the user — can rehydrate the real value on demand while nothing sensitive persists in logs, caches, or third-party payloads). The reversible approach dominates in practice because most production debugging genuinely needs to see the real value at some point, and the redaction boundary belongs at the *persistence* layer — before something is written to a log, cache, or sent upstream — not baked irretrievably into the data at generation time.

What happens to a payload once it leaves your infrastructure is a matter of contract, not code: Zero Data Retention (ZDR) endpoints or agreements mean the provider doesn't retain the payload past serving the request; enterprise terms with a signed Data Processing Agreement (DPA) typically layer on no-training-by-default guarantees; absent ZDR, a roughly 30-day default retention window for abuse monitoring is typical; HIPAA-covered workloads require a signed Business Associate Agreement (BAA); and GDPR data-residency requirements push toward EU regional endpoints so payloads never leave the jurisdiction. Data residency and on-prem control are also two of the strongest arguments for the self-hosting side of [[Decision - Self-Hosting vs Managed LLM API]] — when a DPA and a ZDR endpoint aren't enough, keeping weights and data on infrastructure you control removes the question entirely.

## In practice

A TTL on the trace store is the easy 80% of retention — most observability backends, including the ones behind [[Concept - LLM Observability and Tracing]], support a configurable retention window natively. The hard 20% is deletion: a data-subject deletion request has to propagate to *every* derived store that could hold a copy — the primary trace/log store, the semantic cache, and the vector index — and a common, quietly-failing implementation deletes from the trace database and stops there, leaving a still-queryable copy sitting in the cache or the RAG index. Prove propagation with an audit log recording what was requested, when, and which stores were actually touched; deletion that can't be demonstrated is functionally the same as no deletion for compliance purposes.

The default posture for content capture should be off, not on: the emerging [[Reference - OpenTelemetry GenAI Semantic Conventions]] treat full prompt/completion capture as opt-in rather than default-on, precisely because that payload is a PII liability the moment a user pastes something sensitive into a prompt. On top of technical controls, compliance context includes SOC2/ISO27001 access-logging and encryption controls, a published sub-processor list naming every downstream vendor that touches data, a documented data-flow map, and — for teams operating in or serving the EU — the operator obligations summarized in [[Reference - The EU AI Act for Operators]]. Verifying all of this is wired correctly before shipping is exactly what the compliance group of [[Checklist - Production LLM Launch Readiness]] exists to catch.

## Failure modes

**PII baked into the cache key itself.** Hashing a raw prompt containing a name or email into the semantic-cache key means the key — which shows up in logs, metrics labels, and cache-inspection tools — carries the PII even after the cached value is redacted; the fix is keying on a redacted or template-normalized form, not the raw prompt.

**Embeddings treated as anonymous.** A vector store excluded from a data-deletion sweep because "it's just numbers" is the single most common miss in practice, per the mechanism above.

**Partial deletion propagation.** Deletion reaches the primary log store but not the semantic cache or vector index, so a supposedly-deleted record remains retrievable via a similar query.

**Full-payload logging by default.** Capturing everything for debuggability, with no redaction pass, turns the observability stack into a standing liability the first time a user pastes a document containing sensitive data.

**Un-redacted upstream sends without a DPA/ZDR agreement.** Sending PII to a third-party model provider without the contractual data-handling terms in place moves liability outside your control regardless of what your own logging does correctly.

Adjacent but distinct: an attacker using [[Concept - Prompt Injection]] to coax a model into echoing back another user's cached context or a system prompt is an adversarial exfiltration path, not a data-handling default — the two failure classes compound (weak redaction defaults make a successful injection worse) but need separate defenses.

## The non-obvious

The reversible-tokenization design — mask on the way in, log only the token, rehydrate the real value on the way back out to the user — usually beats blind irreversible redaction, because it resolves a tension that looks unsolvable at first: production debugging genuinely needs the real value to understand what happened, but the logging, caching, and model-provider path never needs to store it. Putting the redaction boundary at the persistence layer rather than at generation time means the vault holding the token↔value mapping becomes the single most security-critical service in the whole stack — smaller and less visible than the model-serving layer, but a compromise there defeats every other redaction control at once, which is exactly the kind of component that gets under-resourced because it doesn't look like the "real" infrastructure.

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
