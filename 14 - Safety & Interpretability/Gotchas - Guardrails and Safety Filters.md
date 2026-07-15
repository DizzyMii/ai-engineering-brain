---
tags: [gotchas, domain/safety-interp, level/advanced]
aliases: []
summary: "Eight pitfalls in building and operating LLM guardrails: jailbreakable guards, silent disable-under-load, injection blind spots, and more."
---
> **One-paragraph hook:** A [[Pattern - Guardrail Architecture|guardrail]] gives a false sense of security faster than it gives real security — every team that wraps a model in an input/output classifier discovers, usually in production, that the guard has its own attack surface, its own latency budget, its own blind spots, and its own drift. This note collects the pitfalls in the order they tend to bite: from "the guard doesn't actually protect against what you think it does" down to "the guard's labels quietly stopped meaning what you think they mean."

## 1. A same-family classifier guard falls to the exact attack that broke the base model

**Symptom:** an output classifier built on the same base model family (or the same training recipe) as the model it's guarding passes content it should have blocked, right after a jailbreak that also fooled the primary model. **Cause:** a prompt-based or same-architecture guard shares the base model's weaknesses — encoding tricks, role-play framing, and other entries in the [[Concept - Jailbreak Taxonomy]] transfer directly to it, because the guard is itself an LLM with the same [[Concept - Refusal Mechanics|shallow refusal structure]]. **Fix:** use a mechanistically different guard — a purpose-trained classifier (Llama Guard–style, [[Pattern - Guardrail Architecture]]) rather than "ask the same model if this is safe," and stack detection methods (regex/deterministic + classifier + model-based) so one bypass doesn't defeat the whole layer. **Detection:** red-team the guard itself with the same attack library used on the base model, not just the base model in isolation.

## 2. Guardrails get silently disabled under load and nobody notices

**Symptom:** an incident review finds the input/output guard was returning timeouts or was bypassed under peak traffic for hours before anyone flagged it. **Cause:** serial input and output guards roughly double or triple end-to-end latency (each is close to another full forward pass); under load, teams add a timeout-and-allow fallback to protect user-facing latency SLOs, which quietly reopens the hole the guard existed to close. **Fix:** make guard failure fail-closed for high-stakes actions and fail-open only for genuinely low-stakes chat, as an explicit, documented policy decision — not a default born from a timeout handler. **Detection:** alert on guard error/timeout rate as a first-class SLO, and log every fail-open decision with enough context to audit it after the fact (see [[Concept - LLM Observability and Tracing]]).

## 3. The input guard never sees the attack because it arrives after the check

**Symptom:** an input classifier reports "clean" on every request, yet the model still executes an injected instruction. **Cause:** the guard scans the user's turn at request time, but the malicious instruction arrives later — inside a retrieved document, a tool result, or a web page the model reads mid-task. This is [[Concept - Prompt Injection|indirect injection]], and a guard scoped to "the user's message" structurally cannot see it. **Fix:** scan every content source that enters the context, not just the initiating user turn — retrieved documents, tool outputs, and file contents all need the same scrutiny as user input, ideally before they're concatenated into the trusted context. **Detection:** trace which context segment (system / user / retrieved / tool-output) triggered a downstream harmful action, and confirm the guard's coverage matches every one of those segments.

## 4. The bot starts refusing "how do I kill a Python process" and users stop trusting it

**Symptom:** support tickets and abandonment spike after a guardrail tightening, on requests that are obviously benign to a human. **Cause:** an aggressive input classifier keys on surface lexical overlap with harm categories ("kill," "attack," "exploit") rather than actual intent, and blocks legitimate security, medical, and coding questions. **Fix:** track false-refusal rate on a benign-but-scary-sounding benchmark (XSTest) as a release gate with equal weight to attack-block rate — a guard that blocks everything is not a working guard, it's a broken product. **Detection:** sample blocked requests weekly and hand-label true/false positives; a false-positive rate climbing over time means the classifier threshold or training data needs revisiting.

## 5. Output filters cannot catch data leaving encoded in emoji, whitespace, or an image URL

**Symptom:** a post-incident review finds sensitive data left the system despite an output guard reporting no violations. **Cause:** keyword and PII scanners look for the data in cleartext; steganographic and structural exfiltration channels — data encoded into emoji sequences, zero-width whitespace, or a query string appended to an auto-rendered markdown image URL (the classic ChatGPT-plugin exfil pattern) — carry the same bytes past a scanner tuned for readable content. **Fix:** block or neutralize the exfiltration *channel* itself (disable auto-fetching markdown images, strip unnecessary hyperlink rendering) rather than relying solely on content inspection; treat output-channel hardening as a separate control from content filtering. **Detection:** canary tokens (unique secret strings the model should never emit) planted in sensitive contexts catch exfiltration attempts regardless of encoding, because you're watching for the canary's presence anywhere in the output or outbound request, not parsing its meaning.

## 6. A keyword blocklist fails the moment the attacker resizes the alphabet

**Symptom:** a blocked term reappears in outputs immediately after a jailbreak or injection attempt uses homoglyphs, zero-width joiners, or unusual Unicode. **Cause:** the filter and the model tokenize differently — a blocklist built on literal substrings does not account for [[Concept - Byte-Pair Encoding|BPE]] splitting a word across token boundaries in a way that still reconstructs the banned string for the model but not for a naive string-match filter, or for visually-identical Unicode characters mapping to different code points. **Fix:** normalize Unicode (NFKC) and operate the filter on decoded/detokenized text, not raw bytes, and prefer semantic classifiers over literal blocklists for anything beyond a fixed, known-bad string set. **Detection:** fuzz the filter with homoglyph and zero-width-character variants of every blocked term as part of the guardrail test suite, not just the literal string.

## 7. PII scrubbing regexes pass audit and still leak names, case numbers, employee IDs

**Symptom:** a compliance audit finds sensitive identifiers in logged or generated output despite an active PII-redaction layer. **Cause:** regex-based scrubbing catches structured patterns (SSNs, emails, phone numbers) reliably but misses context-dependent identifiers — a rare surname, an internal case number, an employee ID — that have no fixed shape a regex can key on; scrubbing can also corrupt legitimate content by over-matching. **Fix:** pair regex scrubbing with a named-entity or context-aware PII classifier for the identifiers a fixed pattern can't catch, and treat regex coverage as a floor, not a guarantee (see [[Concept - Enterprise AI Security Exposure]]). **Detection:** run adversarial audits with real-world-shaped fake data (case numbers, uncommon names) specifically designed to fall outside regex patterns.

## 8. The moderation API's "safe" category quietly stops meaning what your policy means

**Symptom:** content that clearly violates internal policy is repeatedly scored "safe" by a third-party moderation endpoint, and it wasn't always this way. **Cause:** the vendor's classification taxonomy and your internal policy diverge over time as either side updates definitions, and nobody is watching the confusion matrix — you trusted the label, not the definition behind it. **Fix:** maintain your own labeled validation set mapped to your actual policy, and re-run it against the vendor API on a schedule, not just at integration time. **Detection:** track agreement rate between the vendor's label and your internal review on a sampled stream; a slow drift downward is the signature of taxonomy divergence, not a sudden break.

## Connections
- [[Pattern - Guardrail Architecture]] — the design this note's pitfalls apply to: input/output/action guards, fail-open vs fail-closed, and the latency/cost budget referenced in gotcha 2.
- [[Concept - Prompt Injection]] — the mechanism behind the indirect-injection blind spot in gotcha 3.
- [[Concept - Refusal Mechanics]] — why a same-family guard shares the base model's shallow, linearly-attackable refusal structure in gotcha 1.
- [[Concept - Byte-Pair Encoding]] — the tokenization mismatch between filter and model that enables the blocklist evasion in gotcha 6.
- [[Gotchas - Agents in Production]] — the sibling pitfalls list for agentic systems, where guardrail failures compound with tool-use and excessive-agency risk.
- [[Concept - LLM Observability and Tracing]] — the tracing infrastructure needed to detect fail-open events, context-source coverage gaps, and moderation-taxonomy drift.
- [[Concept - Enterprise AI Security Exposure]] — the broader organizational risk surface that regex PII false confidence and exfiltration blind spots feed into.
- [[Concept - Many-Shot Jailbreaking]] — a frontier example of gotcha 1 at scale: a guard built on ordinary in-context robustness is defeated by the same long-context mechanism that defeats the base model's safety training.

## Sources
- Zou et al. (2023) and the broader GCG lineage — the perplexity-detectable attack pattern behind guard bypass discussions.
- Röttger et al. (2023) — "XSTest: A Test Suite for Identifying Exaggerated Safety Behaviours in Large Language Models," the benchmark behind the over-refusal gotcha.
- Willison (2023) — public write-ups on markdown-image exfiltration and the lethal-trifecta framing referenced in the exfiltration gotcha.
