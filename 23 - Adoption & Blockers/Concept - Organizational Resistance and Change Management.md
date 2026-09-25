---
tags: [concept, domain/adoption-blockers, level/core]
aliases: [change management for AI, AI adoption resistance, workforce resistance to AI]
summary: "Why accurate AI tools stall in enterprises anyway — trust, incentives, and workflow fit block adoption even when the model works."
---
# Concept - Organizational Resistance and Change Management

> **One-paragraph hook:** Ship a model that scores well on eval and the deployment can still die. The technology worked. The people who were supposed to use it didn't trust it, weren't shown how, or had every incentive to avoid it without saying so. Organizational resistance is the blocker left standing after [[Concept - The Evaluation Gap]] and [[Concept - Data and Integration Readiness]] are both solved, and enterprises consistently underbudget for it.

## The mechanism

MIT NANDA's *"The GenAI Divide: State of AI in Business 2025"* (Aug 2025), drawing on 52 structured interviews and 153 leader surveys across 300+ public AI initiatives, calls the dominant failure mode a "learning gap": deployed systems don't retain feedback, adapt to a team's actual workflow, or fit how work gets done (E2, single report; see [[Concept - The Pilot-to-Production Gap]] for the full framing and its critiques). A meaningful share of that gap is organizational, not technical. It breaks into four forces, and any one of them can kill adoption alone.

**Trust and verification friction.** Knowledge workers burned by a confident-but-wrong output stop trusting the tool by default and re-check everything it produces. That's a rational response to a system that fails silently, without calibrated confidence. The cost is big enough to get its own note, [[Concept - The Verification Tax]].

The sharpest evidence that this friction can outweigh the benefit is the METR RCT (Jul 2025). Experienced open-source developers worked 19% *slower* with early-2025 AI tools (Cursor Pro + Claude 3.5/3.7 Sonnet) on their own mature repositories. Beforehand they forecast a 24% speedup, and afterward they still perceived themselves as ~20% faster (single RCT, n=16, 246 tasks; E2; [[Breakdown - The METR Developer Slowdown RCT]]). The perception gap is itself a trust signal. Workers don't reliably know when review overhead is costing them time, and that same overhead is what erodes ROI at the org level.

**Incentive misalignment.** A team that suspects a tool is there to justify headcount cuts has every reason to under-report its value, avoid becoming the "AI replaced my role" reference case, or route around it. Adoption is fastest where the time savings go to the person doing the task (fewer late nights, less tedious drafting) and slowest where they go to the employer as a headcount cut the team can see coming. Practitioners give this as the standard explanation (E1, consultancy/practitioner framing, not a controlled study) for mandated tools with high license counts and low active use.

**Workflow disruption.** A tool that makes you leave the system of record (copy from Salesforce, paste into a separate AI tab, copy the answer back) adds steps and gets abandoned whatever the model quality. It's the [[Concept - Data and Integration Readiness]] failure seen from the user's side instead of the pipeline's. Readiness failures and workflow-fit failures are often the same integration gap, diagnosed from opposite ends.

**Enablement gap.** Without worked examples and prompt/tool training for the team's actual tasks, usage stays shallow. A few power users get real value while everyone else never gets past one unimpressive first try and drops it. The spread between power users and non-users on the same licensed tool is routinely enormous, and that spread is diagnostic: the blocker is enablement, not capability.

## In practice

Klarna's AI customer-service program is the highest-profile documented case of all four forces compounding (E2, company statements + Reuters/Bloomberg/Forbes reporting, 2024–2025; full breakdown in [[Breakdown - Klarna's AI Customer Service Bet]]). In February 2024 Klarna's CEO announced its OpenAI-built assistant was doing the work of ~700 full-time customer-service agents and handling roughly two-thirds of chats in its first month.

By spring 2025 Klarna was visibly backing off. CEO Sebastian Siemiatkowski said publicly, "we focused too much on efficiency and cost… the result was lower quality, and that's not sustainable." The company started rehiring human agents and moved to a hybrid: AI on routine, high-volume queries, humans on escalations and complex or high-value interactions (E2, company/press statements, 2025). Read as a change-management failure, the mechanism is workflow fit. Full autonomy was pushed onto a case mix that included escalations and high-stakes interactions where customers wanted a verification path the bot didn't offer. And the launch metric (chats handled, headcount displaced) didn't predict retained customer trust.

The practitioner literature (E1/E2, consultancy and case-study sourcing, not RCT-grade) converges on what works:

- executive sponsorship that lasts past the launch announcement;
- embedded champions inside the team, instead of a central AI office mandating from outside;
- redesigning the workflow around the tool, not bolting the tool onto the old one;
- measuring active use on real tasks, not seats provisioned or licenses sold.

Shelfware (bought, provisioned, unused) is the visible symptom. The disease underneath is that none of the four forces were dealt with before rollout.

## Failure modes

- **Shelfware.** Seat count high, active-use telemetry low. Detection: instrument usage per user per week on real tasks, not login counts. A tool nobody opens twice isn't adopted, however many licenses were bought.
- **Silent workaround.** The team routes around the sanctioned tool, back to manual process or to an unsanctioned consumer tool (see [[Concept - Shadow AI]]), because the sanctioned one is slower or fits their workflow worse than what they'd pick themselves.
- **Trust collapse after a visible miss.** One high-profile bad output (a wrong number, a fabricated policy) wipes out months of trust and pushes people back to checking everything. Net time savings disappear even if the underlying error rate is low. Incidents of this kind are catalogued in [[Lore - Hallucination Liability Incidents]].
- **Champion attrition.** The program rested on one or two embedded enthusiasts. When they leave or get reassigned, usage decays toward the pre-rollout baseline, because the enablement gap was never actually closed.
- **Metric mismatch at the top.** Leadership tracks deployment (licenses bought, press release issued) while the org needs an active-use and outcome metric. A Klarna-style reversal starts in the gap between those two.

## The non-obvious

Seats sold and value delivered can diverge for months before anyone notices. A rollout can look successful on everything leadership watches (licenses provisioned, a launch press release, a big headline productivity number) while task-level usage is a fraction of that, because nobody measures the number that would show the gap. Organizations that get through this count "active use on real, checkable tasks" as the only metric from week one. The same sanctioned, well-supported tool that fixes shelfware also starves [[Concept - Shadow AI]], since both share a root cause: employees use whatever tool best fits their actual workflow, sanctioned or not.

## Connections
- [[Concept - The Pilot-to-Production Gap]] — organizational resistance is a top contributor to NANDA's "learning gap," the umbrella framing for why pilots stall before production.
- [[Concept - Shadow AI]] — the same enablement failure that produces shelfware also produces shadow AI; a good sanctioned tool fixes both at once.
- [[Concept - The Verification Tax]] — trust/verification friction is the mechanism; the tax is its measurable cost.
- [[Concept - Data and Integration Readiness]] — workflow disruption and data/integration failure are the same seam viewed from the user side versus the pipeline side.
- [[Gotchas - Enterprise AI Adoption]] — shelfware and the demo-vs-production gap are catalogued there as symptom-first pitfalls.
- [[Breakdown - The METR Developer Slowdown RCT]] — the sharpest controlled evidence that perceived and measured productivity diverge, underpinning the trust-friction mechanism here.
- [[Breakdown - Klarna's AI Customer Service Bet]] — the fullest documented case of incentive, trust, and workflow-fit failure compounding in one deployment.
- [[Reference - AI Impact by Business Function]] — active-use rates and resistance patterns vary sharply by function; this reference tracks the spread.
- [[Concept - Support Deflection Economics]] — the economic frame Klarna's initial rollout optimized for, and what it left out.

## Sources
- MIT NANDA — *The GenAI Divide: State of AI in Business 2025* (Aug 2025) — the "learning gap" framing, 52 structured interviews and 153 leader surveys across 300+ public AI initiatives.
- METR — *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity* (Jul 2025, arXiv:2507.09089) — 19% measured slowdown vs. perceived speedup, n=16, 246 tasks.
- Klarna / Sebastian Siemiatkowski — public statements, Feb 2024 (launch claim, ~700 agents' worth of work) and spring 2025 (reversal, "we focused too much on efficiency and cost").
- Reuters, Bloomberg, Forbes — 2024–2025 reporting on Klarna's AI customer-service rollout and reversal.
