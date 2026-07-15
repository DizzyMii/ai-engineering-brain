---
tags: [playbook, domain/adoption-blockers, level/core]
aliases: [pilot to production, POC to production, taking a GenAI pilot live]
summary: "End-to-end procedure for taking a GenAI pilot to a governed production deployment without joining the ~95% that never get there."
---
# Playbook - Crossing the Pilot-to-Production Gap

> **Goal:** take a GenAI proof-of-concept to a governed, monitored production deployment that survives contact with real users and real data.
> **When to run this:** the moment a pilot shows promise and someone asks "can we ship this" — not after the demo has already been promised to a stakeholder.
> **Prerequisites:** an executive sponsor who owns the go/no-go decision, access to real (not synthetic) task examples, and the authority to say no to a use case that fails Step 0.

Most pilots never reach this point at all — see [[Concept - The Pilot-to-Production Gap]] for the base rate and why the failure is structural, not incidental. This playbook is the procedure for the minority that do.

## Steps

1. **Pick a survivable use case.** Action: score the candidate use case on value, error tolerance, and verification cost — reject anything that needs >99% autonomous accuracy with no human review path, and reject anything where you cannot state the acceptable error rate out loud. Expected observation: a use case with bounded scope, high value, and either a high error tolerance or a cheap way to verify output (link [[Playbook - Picking Profitable AI Use Cases]] for the selection framework; the underlying reliability math is in [[Concept - The Capability-Reliability Gap]]). **Deviation:** if nobody in the room can state the acceptable error rate, stop — you don't have a spec, you have a demo, and shipping now means discovering the error rate in production.

2. **Build the eval set before the system.** Action: assemble 50-500 labeled real cases, including adversarial and edge inputs, before writing production code. Expected observation: a labeled dataset that can quantify accuracy and detect regression on day one of the build, not day one of a complaint (mechanism and construction detail in [[Deep Dive - Designing an Eval Harness]]; why this specific gap kills pilots in [[Concept - The Evaluation Gap]]). **Deviation:** "we'll add evals later" is a decision to ship on cherry-picked demo cases and discover the failure tail from users instead of from your own test suite.

3. **Verify data and permissions readiness.** Action: connect the real systems of record, enforce document- or row-level entitlements on anything the system can retrieve, and confirm data freshness against the source of truth. Expected observation: a red-team query attempting to surface a restricted document returns nothing (mechanism in [[Concept - Data and Integration Readiness]]). **Deviation:** if a red-team query *does* surface a restricted document — HR records, salary data, M&A material — that is a launch blocker, not a bug ticket to file for later.

4. **Design human-in-the-loop for the actual error profile.** Action: match the review mode to what Step 1 established about error tolerance — full autonomy only where verification is cheap (tests, citations, structured checks), assist/approve modes everywhere else — and price the review time into the ROI model, not just the generation savings. Expected observation: a documented review workflow with a named cost per reviewed output (mechanism and the cost it's pricing in: [[Concept - The Verification Tax]]). **Deviation:** an ROI case that only counts generation time saved and never counts reviewer time is optimistic by construction and will not survive scale.

5. **Put guardrails and security controls in front of the system.** Action: add input/output filtering, PII handling and minimization, and — for any system with tool access or that ingests external content — instruction/data separation and least-privilege tool scoping to defend against [[Concept - Prompt Injection]]. Expected observation: an injection test corpus (planted malicious instructions in retrieved documents, emails, or web content) that the system does not act on (full exposure surface in [[Concept - Enterprise AI Security Exposure]]; if the system takes autonomous actions rather than just generating text, also run [[Gotchas - Agents in Production]] before this step). **Deviation:** a system that reads untrusted content and has any tool access is exploitable by definition until this step is verified, not assumed.

6. **Roll out in stages, gated on the eval suite.** Action: ship shadow mode (system runs, output isn't acted on) -> canary (a small live percentage) -> full rollout, re-running the Step 2 eval suite and checking live metrics before advancing each stage; keep a kill switch and a working non-AI fallback path available at every stage. Expected observation: quality, cost-per-task, and latency stay within the bounds the eval suite established at each stage before you advance to the next. **Deviation:** advancing a stage because "it seems fine" without re-running the eval suite is how a shadow-mode success becomes a canary-stage incident.

7. **Monitor continuously and re-baseline on every model swap.** Action: instrument quality, cost/token, latency, and adoption in production (mechanism in [[Concept - LLM Observability and Tracing]]), and re-run the full eval suite any time the underlying model changes — forced by a provider deprecation or chosen for cost/quality reasons (why this is a recurring, not one-time, cost: [[Concept - Vendor and Model Churn Risk]]). Expected observation: a dashboard that would catch a silent regression within a monitoring cycle, not from a user complaint weeks later. **Deviation:** treating a model swap as a config change instead of a re-qualification is exactly how "it worked last week" incidents happen.

## Verification

A deployment is done, not merely launched, only when both of the following are true simultaneously: **(a)** the Step 2 eval suite passes at the current model and configuration, **and** **(b)** a real adoption or ROI metric has moved — active use on real tasks, deflected volume, cycle-time reduction, whatever Step 1 defined as the value case. Either alone is insufficient: an eval suite that passes but no one uses the system is [[Concept - Organizational Resistance and Change Management]]'s shelfware problem; an adoption number that's rising without a passing eval suite means you're accumulating undetected regression debt, not delivering verified value.

## When it goes wrong

| Symptom | Likely cause | Jump to fix |
|---|---|---|
| Demo was great, production output is bad | No representative eval set — Step 2 was skipped or built from cherry-picked cases | [[Concept - The Evaluation Gap]] — rebuild the eval set from real, not curated, cases before shipping further |
| The assistant surfaces a document the user shouldn't see | Entitlements were never enforced at the retrieval layer — Step 3 skipped | [[Concept - Data and Integration Readiness]] — add document/row-level access control before any further rollout |
| Licenses are provisioned but nobody actually uses it | No change management — the tool doesn't fit the workflow or nobody was enabled to use it | [[Concept - Organizational Resistance and Change Management]] — instrument active use, assign champions, redesign around the workflow |
| Quality or latency regressed with no code change on your side | Silent model-update regression, or an unpinned floating model alias | [[Concept - Vendor and Model Churn Risk]] — pin dated snapshots and gate every swap on the Step 2 eval suite |
| Cost or reviewer time blew out at scale despite a good pilot | The verification tax and fully-loaded cost per successful task were never priced in Step 4 | [[Concept - The Verification Tax]] — recompute ROI with reviewer time included, and revisit whether Step 1's error tolerance was realistic |
| An agent with tool access did something it shouldn't have | Untrusted content treated as trusted input, or excess tool privilege | [[Concept - Prompt Injection]] and [[Gotchas - Agents in Production]] — apply instruction/data separation and least-privilege scoping, then re-run Step 5's injection test corpus |
| A pattern of pitfalls keeps recurring across deployments, not just this one | The org hasn't built institutional memory of prior failures | [[Gotchas - Enterprise AI Adoption]] — the aggregated, symptom-first list of what bites real deployments |

## Connections
- [[Concept - The Pilot-to-Production Gap]] — this playbook is the operational answer to the base-rate failure that note documents.
- [[Concept - The Evaluation Gap]] — Step 2's eval-first discipline is the direct fix for the gap this note names.
- [[Concept - Data and Integration Readiness]] — Step 3's entitlement and freshness checks operationalize this note's "plumbing is the real work" claim.
- [[Concept - The Verification Tax]] — Step 4's review-cost pricing and the "cost blowout" failure branch both trace back to this mechanism.
- [[Concept - Enterprise AI Security Exposure]] — Step 5's guardrail and injection-defense requirements are scoped from this note's full exposure map.
- [[Concept - Vendor and Model Churn Risk]] — Step 7's re-baseline-on-swap requirement exists because of the churn dynamics this note documents.
- [[Gotchas - Enterprise AI Adoption]] — the aggregated pitfall list that backs every row of the failure-branch table above.
- [[Playbook - Picking Profitable AI Use Cases]] — Step 0/1's use-case screen delegates to this playbook's selection criteria.
- [[Concept - The Capability-Reliability Gap]] — the reliability math (why demo accuracy != production accuracy) underlying Step 1's rejection criterion.
- [[Deep Dive - Designing an Eval Harness]] — the construction methodology behind Step 2's eval set.
- [[Concept - Prompt Injection]] — the specific attack class Step 5's injection test corpus is built to catch.
- [[Concept - LLM Observability and Tracing]] — the instrumentation layer Step 7's monitoring step requires.
- [[Gotchas - Agents in Production]] — required reading before Step 5 for any system with autonomous tool access, not just text generation.

## Sources
- MIT NANDA — *The GenAI Divide: State of AI in Business 2025* (Aug 2025) — the base-rate failure this playbook is built against; see [[Concept - The Pilot-to-Production Gap]] for full sourcing and critique.
- METR — *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity* (Jul 2025, arXiv:2507.09089) — evidence for the verification-tax mechanism behind Step 4.
- Practitioner/operator convention, staged-rollout pattern (shadow -> canary -> full) as used broadly across ML deployment practice — standard MLOps practice, not a single citable source.
