---
tags: [gotchas, domain/adoption-blockers, level/advanced]
aliases: [Enterprise AI Pitfalls, GenAI Deployment Gotchas]
summary: "Symptom-first pitfalls that kill enterprise AI deployments: demo-vs-prod, shelfware, entitlement leaks, injection, ROI collapse."
---

# Gotchas - Enterprise AI Adoption

Failures that show up *after* the demo impresses the steering committee and turn a green pilot into a stalled, unshippable or dangerous system. Ordered by money and reputation burned. Most are specific shapes of [[Concept - The Pilot-to-Production Gap]] on the ground.

## 1. The demo works, production doesn't, because a demo is a filtered sample

**Symptom:** Flawless in the sales/steering-committee demo; accuracy craters on the real inbound distribution. "It worked on everything we showed it."

**Cause:** Demos run on cherry-picked, in-distribution inputs. Production is the long tail: malformed records, adversarial phrasing, the ambiguous 8% nobody scripts. The demo measured the *head* of the distribution; you shipped against all of it. It's a cliff, not a slope. A system that's "90% there" in a demo is a 1-in-10-failure product, and the last few points of reliability cost more than the first ninety. See [[Concept - The Capability-Reliability Gap]].

**Fix:** Eval first. Build a labeled set of 50–500 *real* cases (edge and adversarial inputs included) before you build the system, and gate sign-off on it. No eval set, no launch. See [[Concept - The Evaluation Gap]] and [[Playbook - Crossing the Pilot-to-Production Gap]].

**Detection:** A representative real-case suite run *before* go/no-go, not a scripted walkthrough. A live demo alone is no evidence.

## 2. Seat licenses ≠ usage (shelfware)

**Symptom:** You bought ChatGPT Enterprise or Copilot for 5,000 people. Telemetry shows a few hundred weekly active users, mostly a handful of power users.

**Cause:** Procurement treated adoption as a purchase instead of a behavior change. Without enablement, worked examples and workflow redesign, usage stays shallow and the gap between power users and non-users on the same team is enormous. It's a change-management failure dressed up as a software license; see [[Concept - Organizational Resistance and Change Management]].

**Fix:** Executive sponsorship, embedded champions, and redesigning the task around the tool instead of bolting it on. Measure *active use on real tasks*, not licenses sold.

**Detection:** Active-use telemetry (weekly active users doing real work, not logins). Seats sold is a vanity metric. A good sanctioned tool also drains [[Concept - Shadow AI]], because people get an approved option as good as the consumer one.

## 3. Entitlement leakage in RAG and agents

**Symptom:** The assistant cheerfully shows salary bands, an M&A deck, or another team's HR file to a user who should never see it.

**Cause:** The retrieval layer indexed *everything* into one vector store with no document- or row-level access control. The model has no idea who's asking. Permissions belong at retrieval time, and most POCs skip them because entitlement-aware retrieval is the hard, boring part. See [[Concept - Data and Integration Readiness]] and [[Concept - Enterprise AI Security Exposure]].

**Fix:** Entitlement-aware retrieval. Filter the candidate set by the *requesting user's* permissions, mirroring the source system's ACLs, before anything reaches the model. A prompt instruction ("don't reveal confidential docs") is never an access control.

**Detection:** Red-team queries that deliberately fish for restricted content, run from a low-privilege test account, before and after every re-index.

## 4. Silent model-update regression

**Symptom:** "It worked last week." Nothing deployed on your side, but quality dropped, a tuned prompt misbehaves, or the output format drifted.

**Cause:** You pointed at a floating model alias and the provider updated the endpoint under you: an invisible dependency bump against a prompt overfit to the old checkpoint. See [[Concept - Vendor and Model Churn Risk]].

**Fix:** Pin dated model snapshots and run a gating eval on *every* model swap. "Upgrade to the new model" is a code change that has to pass the suite, never a free win.

**Detection:** A continuous regression eval on a fixed suite with alerts on score deltas, plus [[Concept - LLM Observability and Tracing]] to catch distribution drift in live traffic.

## 5. Prompt injection via ingested content

**Symptom:** An agent reads an email, webpage or document and then does something it shouldn't: exfiltrates data, calls a tool with attacker-chosen arguments, or emits attacker text.

**Cause:** The system treats retrieved or tool-accessed content as trusted instructions. Within a single context window there's no reliable in-band separation between "data to process" and "commands to obey". Simon Willison's *lethal trifecta* (private-data access + untrusted content + an external communication channel) is the recipe. Any agent holding all three can be exploited with no exploit code, just words (E2, practitioner framing, Willison 2025). See [[Concept - Prompt Injection]].

**Fix:** Least-privilege tool scoping, strict separation of instruction and data channels, and breaking the trifecta (e.g., remove the external egress path from any flow that touches untrusted content). Guardrails reduce this without eliminating it. See [[Concept - Enterprise AI Security Exposure]] and [[Deep Dive - RAG Architectures]].

**Detection:** An injection test corpus (documents/emails seeded with adversarial instructions) run against the agent in CI.

## 6. A hallucination becomes a binding representation

**Symptom:** The customer-facing bot invents a refund policy, a discount or a legal fact, and the company is held to it.

**Cause:** A deployed model's outputs are the company's *representations*. There's no disclaimer-shielded third party. In *Moffatt v. Air Canada* (BC Civil Resolution Tribunal, Feb 2024, E3), the tribunal flatly rejected Air Canada's argument that its chatbot was "a separate legal entity" and held the airline liable for a bereavement-fare policy the bot made up (~CAD 812 awarded). Disclaimers didn't help. See [[Lore - Hallucination Liability Incidents]].

**Fix:** Ground outputs in retrieved facts, cite sources, and constrain scope so the model answers from a controlled knowledge base instead of free-associating. Customer-facing text with tool/data access is *also* an injection liability surface (gotcha 5).

**Detection:** Grounding/faithfulness checks that confirm each claim is supported by a retrieved source, flagging unsupported assertions before they reach the user.

## 7. POC ROI evaporates at scale

**Symptom:** The pilot's economics looked great. At production volume the P&L is flat or negative.

**Cause:** Two costs that round to zero in a pilot dominate at volume: **token cost** (linear in traffic) and the **verification tax**, the human review and correction time on every output. ROI models routinely count generation savings and leave out review, overstating net value. When checking an output costs nearly as much as producing it yourself, AI loses money. See [[Concept - The Verification Tax]] and [[Concept - Unit Economics of LLM Products]]. The METR RCT is the sharpest warning: experienced developers were measured ~19% *slower* with AI while believing they were faster (E2, single RCT, n=16, 2025). Self-reported speedups are unreliable ROI inputs; see [[Reference - Developer Productivity Studies]].

**Fix:** Model *fully-loaded cost per successful task* (tokens + human review + rework), not raw generation speed. Auto-route only high-confidence cases and keep humans on the tail where verification is expensive.

**Detection:** Compare production cost per accepted output to the fully-loaded human baseline. If you can't state the acceptable error rate for the use case, you can't price the review tax.

**Bonus gotcha: vendor mortality and lock-in.** A core workflow built on a Series-A wrapper is a continuity risk, and proprietary features (tool-call formats, structured outputs, prompt caching) add switching costs. Run a "can we swap providers in a week?" drill and keep a model-agnostic abstraction where portability matters. See [[Concept - Vendor and Model Churn Risk]].

## Connections
- [[Concept - The Pilot-to-Production Gap]] — the parent phenomenon; every gotcha here is a concrete shape the pilot-to-prod cliff takes.
- [[Concept - The Evaluation Gap]] — the root cause behind gotchas 1 and 7; no eval set means you can't see any of these failing.
- [[Concept - Enterprise AI Security Exposure]] — the security-side treatment of entitlement leakage (gotcha 3) and injection (gotcha 5).
- [[Concept - Data and Integration Readiness]] — entitlement leakage and index hygiene are readiness failures, not model failures.
- [[Concept - Organizational Resistance and Change Management]] — shelfware (gotcha 2) is a change-management failure, not a licensing one.
- [[Concept - Vendor and Model Churn Risk]] — silent regression (gotcha 4) and the lock-in bonus gotcha.
- [[Lore - Hallucination Liability Incidents]] — the case law behind gotcha 6 (Air Canada et al.).
- [[Concept - The Verification Tax]] — the mechanism behind ROI evaporation (gotcha 7).
- [[Playbook - Crossing the Pilot-to-Production Gap]] — the procedure that pre-empts every gotcha on this list.
- [[Concept - Unit Economics of LLM Products]] — the token-and-review cost math that makes scale bite.
- [[Reference - Developer Productivity Studies]] — the measured-vs-perceived productivity evidence behind the ROI gotcha.
- [[Concept - Prompt Injection]] — the attack mechanism behind gotcha 5.
- [[Deep Dive - RAG Architectures]] — where entitlement-aware retrieval and grounding are actually engineered.
- [[Concept - LLM Observability and Tracing]] — the detection substrate for silent regression and cost blowout.

## Sources
- Moffatt v. Air Canada, BC Civil Resolution Tribunal, 2024 CRT — chatbot misrepresentation held binding on the operator (E3, tribunal decision).
- Willison, S. (2025) — "The lethal trifecta for AI agents: private data, untrusted content, external communication" (E2, practitioner framing).
- Becker et al. / METR (2025) — "Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity": measured −19% vs perceived +20% (E2, single RCT, n=16, 246 tasks).
- MIT NANDA, "The GenAI Divide: State of AI in Business 2025" (Aug 2025) — ~95% of enterprise GenAI pilots show no measurable P&L impact (E2, single report; see Pilot-to-Production Gap for the critique).
