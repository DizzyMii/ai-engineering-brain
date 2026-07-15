---
tags: [decision, domain/ecosystem-history, level/advanced]
aliases: [model provider selection, foundation model vendor choice, which LLM ecosystem]
summary: "Choosing a foundation-model provider/family as an ecosystem bet — lock-in, longevity, licensing, geopolitics; default is closed API behind a gateway."
---

# Decision - Which Model Ecosystem to Bet On

> You are not picking a model, you are picking a **counterparty and a migration cost**. Default for the 80% case: build against a **closed frontier API behind a provider-agnostic gateway**, keep a private eval suite, and re-shop quarterly — because the "best model" changes and inference prices fall roughly 10x/year. Deviate from the default only when a hard constraint (regulated data, extreme volume, a specific licensing or geopolitical gate) forces you off it.

The mistake teams make is treating this as a capability question ("which model scores highest?") when it is a **strategy question** about what you can afford to be wrong about. The axes that actually matter: **open-weights self-host vs closed API**, **frontier capability vs cost vs control/privacy**, and **single-vendor vs abstraction layer** ([LiteLLM](https://) / OpenRouter). Capability is the axis that decays fastest and is therefore the *worst* thing to optimize a two-year commitment around.

## Decision flow

```mermaid
flowchart TD
    A[Standardizing a team on one model ecosystem] --> B{Regulated data, on-prem,<br/>or strict data-residency?}
    B -->|Yes| C[Open weights, self-hosted<br/>Llama / Qwen / Mistral / gpt-oss]
    B -->|No| D{Need the hardest<br/>frontier reasoning / agentic depth?}
    D -->|Yes| E[Closed frontier API<br/>OpenAI o-series / Claude / Gemini]
    D -->|No| F{High volume AND<br/>cost-dominated workload?}
    F -->|Yes| G[Cheap open weights self-host<br/>or a discounted / batch API tier]
    F -->|No| H[DEFAULT: closed API<br/>behind a gateway]
    C --> Z[Abstraction layer + private eval suite<br/>re-benchmark quarterly]
    E --> Z
    G --> Z
    H --> Z
    Z --> Y{Any licensing / geopolitical<br/>gate tripped?}
    Y -->|Yes| X[Re-run: eliminate the gated family,<br/>pick next-best on the same branch]
    Y -->|No| W[Commit — but keep the escape hatch warm]
```

The flow encodes one non-negotiable: whatever branch you land on, you land on it **behind an abstraction layer**. The branch is the *primary* bet; the gateway is the *hedge* that makes the primary bet reversible. The [[Decision - Fine-Tuning vs RAG vs Prompting]] question sits downstream of this one — decide the ecosystem first, because a fine-tune welds you to a base model in a way a RAG index never does.

## Tradeoff matrix

Ballpark figures *(as of 2026; volatile — see [[Concept - Cost Engineering for LLM Applications]] for the real per-workload math)*:

| Criterion | Closed frontier API | Open-weights major (self-host) | Chinese open weights | Abstraction layer over N providers |
|---|---|---|---|---|
| Frontier capability | Highest, day-one | 0–6 mo behind (weeks for reasoning since R1) | At/near frontier for reasoning | Whatever the underlying pick is |
| $ / 1M output tokens | ~$1–15 (flagship high) | <$0.50 amortized at high GPU utilization | Cheapest API tier + free weights | Inherited; gateway adds ~0 marginal |
| Control / privacy | Low (data leaves your VPC) | Highest (weights on your metal) | Highest if self-hosted | Depends on route |
| Lock-in surface | High (prompts, tools, tokenizer) | Medium (bound to base for fine-tunes) | Medium | **Lowest by design** |
| Licensing risk | ToS, output-usage clauses | Llama MAU cap, AUP, naming | MIT/Apache mostly clean | Aggregate of all routes |
| Counterparty / longevity | Deprecation churn | You own the weights forever | Procurement/ban risk | Diversified |
| Geopolitical / compliance | US-centric | Regional options | **High** (residency optics, bans) | Route around gated origins |

Two numbers anchor the whole table. First, **inference price deflation of ~10x/year** (the trend that makes any capability lead temporary and any long lock-in a liability). Second, **DeepSeek-V3's ~$5.6M final-run figure** and the ~17% (~$600B) single-day NVIDIA drop on 27 Jan 2025 — the market's recognition that efficiency, not just scale, now sets the open-weights frontier (see [[Breakdown - DeepSeek]]). Both push the same way: **do not overpay for a capability moat that erodes in months.**

For the players behind each column — funding, posture, who is likely to still exist in 18 months — read [[Reference - The AI Lab Landscape]]. For the exact grants and restrictions per license, read [[Reference - Open Weights Licensing]]. The strategic *why* labs even offer this choice (commoditize-your-complement, the distillation asymmetry) is [[Concept - The Open vs Closed Model Divide]].

## The details that flip the decision

**Lock-in vectors people underestimate.** The switching cost is rarely the model weights — it is everything welded to one model's quirks: prompts and few-shot exemplars tuned to a specific model's idiosyncrasies, fine-tunes bound to one base checkpoint, **differing tokenizers and chat templates** (a Llama chat template silently corrupts on a Qwen model), and **incompatible function-calling schemas** (OpenAI tool JSON ≠ Anthropic tool blocks ≠ open-model ad-hoc formats). A team that hand-tunes 40 prompts against GPT-4o's temperament has built a moat *around their own ankles*. This is the entire argument for an abstraction layer, and it's why [[Decision - Self-Hosting vs Managed LLM API]] should be answered with an eye on portability, not just $/token.

**Counterparty and longevity risk is the one nobody prices.** Will the lab — and the *specific model* — still exist and still be served when your product depends on it? Stability AI's near-collapse in 2024, Inflection's talent being reverse-acqui-hired into Microsoft, and aggressive deprecation timelines (a "GA" model sunset with 6 months' notice) are all live failure modes. **Read the deprecation policy before you commit**, not after the sunset email. Open weights invert this risk: once you hold the `.safetensors`, no vendor can deprecate them out from under you — you trade counterparty risk for ops burden.

**Licensing is a gating criterion, not a footnote.** The Llama Community License's **>700M-MAU clause** exists specifically to deny the largest competitors the grant — if your product could plausibly cross that line, the license is a time bomb. Output-usage clauses (can you train other models on the outputs?), field-of-use bans in the acceptable-use policy, and geographic limits can each disqualify an otherwise-perfect model. This is the first hard filter in the flow, and it is exactly why the [[Checklist - Vetting an Open-Weights Model for Production]] leads with license verification.

**Geopolitics flips excellent models to no-go.** DeepSeek and Qwen are genuinely at the open frontier, yet **data-residency optics, government procurement bans, and government-use restrictions** disqualify them in regulated sectors *even when the weights are the best available*. The weights being open does not make the origin acceptable to your compliance officer. Conversely, sovereign/regional models (Mistral in the EU, Falcon in the UAE) exist precisely to be the acceptable choice where US-origin closed APIs are politically or legally awkward.

**The capability-trajectory bet is the subtle one.** You are not betting on today's benchmark; you are betting on a *family's improvement rate* and on the migration cost when a better model appears elsewhere. Since a strictly-better model *will* appear on a competitor's branch within a year, the rational position is to minimize migration cost — which is the abstraction layer again. **The hedge is the answer:** build provider-agnostic, maintain a private eval suite that is the ground truth for "did the swap help," and re-benchmark quarterly. The teams that win aren't the ones who picked the right model in 2025; they're the ones who could swap it in an afternoon in 2026.

## Connections

- [[Reference - Open Weights Licensing]] — the license is the first hard gate in the flow; MAU caps and output clauses disqualify models before capability even matters.
- [[Concept - The Open vs Closed Model Divide]] — the strategic *why* behind the open/closed axis (commoditize-complements, distillation asymmetry) that shapes every column of the matrix.
- [[Reference - The AI Lab Landscape]] — the counterparty-longevity axis is a bet on *organizations*; this maps their funding, posture, and churn.
- [[Decision - Fine-Tuning vs RAG vs Prompting]] — the downstream adaptation choice; a fine-tune welds you to one base and raises the ecosystem-switching cost.
- [[Concept - Cost Engineering for LLM Applications]] — turns the matrix's ballpark $/token into real per-workload economics, the axis that deflates ~10x/year.
- [[Checklist - Vetting an Open-Weights Model for Production]] — the operational go/no-go once you've chosen the open-weights branch.
- [[Breakdown - DeepSeek]] — the concrete case that proved efficiency can break the compute-moat thesis and narrow the open-vs-frontier gap to weeks.
- [[Decision - Self-Hosting vs Managed LLM API]] — the serving-side sibling decision; portability and $/token trade off here once the ecosystem is chosen.

## Sources
- Spolsky, J. (2002) — *Strategy Letter V* ("commoditize your complement"). The framing for why an incumbent rationally open-sources a rival's moat.
- DeepSeek-AI (2025) — *DeepSeek-R1*. The open reasoning release that compressed the open-vs-frontier capability gap and reset the cost narrative.
- Meta (2024) — *Llama 3 / Llama Community License*. Source for the 700M-MAU clause and acceptable-use constraints that gate commercial adoption.
- Epoch AI / a16z compute-cost analyses (2024–2025) — the ~10x/year token-price-deflation trend (analyst estimate; directional, not audited).
