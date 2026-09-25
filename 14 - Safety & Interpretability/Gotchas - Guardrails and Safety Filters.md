---
tags: [gotchas, domain/safety-interp, level/advanced]
aliases: []
summary: "Eight pitfalls in building and operating LLM guardrails: jailbreakable guards, silent disable-under-load, injection blind spots, and more."
---
> **One-paragraph hook:** A [[Pattern - Guardrail Architecture|guardrail]] delivers a false sense of security faster than real security. Every team that wraps a model in an input/output classifier finds out, usually in production, that the guard has its own attack surface, latency budget, blind spots and drift. These pitfalls are ordered roughly by when they bite, from "the guard doesn't protect against what you think" to "the guard's labels stopped meaning what you think they mean."

## 1. A same-family classifier guard falls to the attack that broke the base model

**Symptom:** an output classifier built on the same model family (or training recipe) as the model it guards lets through content it should block, right after a jailbreak that also fooled the primary model. **Cause:** a prompt-based or same-architecture guard shares the base model's weaknesses. Encoding tricks, role-play framing and the rest of the [[Concept - Jailbreak Taxonomy]] transfer straight to it, because the guard is itself an LLM with the same [[Concept - Refusal Mechanics|shallow refusal structure]]. **Fix:** use a mechanistically different guard, a purpose-trained classifier (Llama Guard–style, [[Pattern - Guardrail Architecture]]) instead of asking the same model whether something is safe. Stack detection methods (regex/deterministic + classifier + model-based) so one bypass doesn't take out the whole layer. **Detection:** red-team the guard itself with the attack library you use on the base model.

## 2. Guardrails get silently disabled under load and nobody notices

**Symptom:** an incident review finds the input/output guard was timing out or being bypassed during peak traffic for hours before anyone flagged it. **Cause:** serial input and output guards roughly double or triple end-to-end latency, since each is close to another full forward pass. Under load, teams add a timeout-and-allow fallback to protect user-facing latency SLOs, and that reopens the hole the guard was there to close. **Fix:** make the guard fail closed for high-stakes actions and fail open only for low-stakes chat, as an explicit, documented policy decision and not a default that fell out of a timeout handler. **Detection:** alert on guard error/timeout rate as a primary SLO, and log every fail-open decision with enough context to audit later (see [[Concept - LLM Observability and Tracing]]).

## 3. The input guard never sees the attack because it arrives after the check

**Symptom:** the input classifier says "clean" on every request, and the model still executes an injected instruction. **Cause:** the guard scans the user's turn at request time, but the malicious instruction shows up later, inside a retrieved document, a tool result or a web page the model reads mid-task. That's [[Concept - Prompt Injection|indirect injection]], and a guard scoped to the user's message can't see it by design. **Fix:** scan every content source that enters the context, not only the initiating user turn. Retrieved documents, tool outputs and file contents need the same scrutiny as user input, ideally before they're concatenated into the trusted context. **Detection:** trace which context segment (system / user / retrieved / tool output) triggered a downstream harmful action, and confirm the guard covers every one of those segments.

## 4. The bot starts refusing "how do I kill a Python process" and users stop trusting it

**Symptom:** after a guardrail tightening, support tickets and abandonment spike on requests any human would see as benign. **Cause:** an aggressive input classifier keys on surface overlap with harm categories ("kill," "attack," "exploit") instead of intent, and blocks legitimate security, medical and coding questions. **Fix:** make false-refusal rate on a benign-but-scary-sounding benchmark (XSTest) a release gate weighted equally with attack-block rate. A guard that blocks everything isn't a working guard; it's a broken product. **Detection:** sample blocked requests weekly and hand-label true and false positives. A false-positive rate climbing over time means the threshold or training data needs another look.

## 5. Output filters can't catch data leaving as emoji, whitespace or an image URL

**Symptom:** a post-incident review finds sensitive data left the system while the output guard reported no violations. **Cause:** keyword and PII scanners look for the data in cleartext. Steganographic and structural channels (data encoded in emoji sequences, zero-width whitespace, or a query string on an auto-rendered markdown image URL, the classic ChatGPT-plugin exfil pattern) carry the same bytes past a scanner tuned for readable content. **Fix:** block or neutralize the exfiltration *channel* (turn off auto-fetched markdown images, strip unnecessary hyperlink rendering) instead of relying only on content inspection, and treat output-channel hardening as a control separate from content filtering. **Detection:** plant canary tokens (unique secret strings the model should never emit) in sensitive contexts. They catch exfiltration regardless of encoding, because you're watching for the canary anywhere in the output or outbound request, not parsing meaning.

## 6. A keyword blocklist fails as soon as the attacker changes the alphabet

**Symptom:** a blocked term shows up in outputs right after a jailbreak or injection attempt that uses homoglyphs, zero-width joiners or unusual Unicode. **Cause:** the filter and the model tokenize differently. A blocklist of literal substrings doesn't account for [[Concept - Byte-Pair Encoding|BPE]] splitting a word across token boundaries in a way the model still reads as the banned string and a naive string match doesn't, or for visually identical Unicode characters with different code points. **Fix:** normalize Unicode (NFKC), run the filter on decoded/detokenized text instead of raw bytes, and prefer semantic classifiers to literal blocklists for anything beyond a fixed set of known-bad strings. **Detection:** fuzz the filter with homoglyph and zero-width-character variants of every blocked term as part of the guardrail test suite.

## 7. PII-scrubbing regexes pass audit and still leak names, case numbers and employee IDs

**Symptom:** a compliance audit finds sensitive identifiers in logged or generated output despite an active PII-redaction layer. **Cause:** regex scrubbing reliably catches structured patterns (SSNs, emails, phone numbers) but misses context-dependent identifiers, like a rare surname, an internal case number or an employee ID, that have no fixed shape to key on. It can also corrupt legitimate content by over-matching. **Fix:** pair regex scrubbing with a named-entity or context-aware PII classifier for identifiers a fixed pattern can't catch, and treat regex coverage as a floor, not a guarantee (see [[Concept - Enterprise AI Security Exposure]]). **Detection:** run adversarial audits with realistic fake data (case numbers, uncommon names) built to fall outside the regex patterns.

## 8. The moderation API's "safe" category drifts away from what your policy means

**Symptom:** content that plainly violates internal policy keeps getting scored "safe" by a third-party moderation endpoint, and it didn't used to. **Cause:** the vendor's taxonomy and your internal policy diverge over time as either side updates definitions, and nobody is watching the confusion matrix. You trusted the label, not the definition behind it. **Fix:** keep your own labeled validation set mapped to your actual policy and re-run it against the vendor API on a schedule, not only at integration time. **Detection:** track agreement between the vendor's label and your internal review on a sampled stream. A slow downward drift is the signature of taxonomy divergence, as opposed to a sudden break.

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
