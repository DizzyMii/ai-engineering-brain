---
tags: [decision, domain/fine-tuning, level/core]
aliases: []
summary: "Prompt first, RAG if the gap is knowledge, fine-tune if the gap is behavior/format/latency — most teams over-jump straight to fine-tuning."
---

# Decision - Fine-Tuning vs RAG vs Prompting

> Default for the 80% case: **start with prompting, escalate to RAG if the failure is missing knowledge, escalate to fine-tuning only if the failure is behavior, format, or per-call cost/latency that prompting can't fix.** Most teams reach for fine-tuning first and pay for it in engineering time and forgone iteration speed.

## Decision flow

```mermaid
flowchart TD
    A[Task underperforming] --> B{Is the failure missing/wrong\nknowledge, or wrong\nbehavior-format-latency?}
    B -->|Missing knowledge| C{Does the knowledge\nchange often?}
    C -->|Yes, frequently| D[RAG]
    C -->|No, mostly static and small| E{Fits comfortably\nin context?}
    E -->|Yes| F[Long-context prompting\n+ prompt caching]
    E -->|No| D
    B -->|Wrong behavior, tone,\nformat, or latency too high| G{>=~500 good\nlabeled examples?}
    G -->|No| H[Prompting / few-shot\n+ structured output]
    G -->|Yes| I{High call volume AND\nstrict schema, or prompt\ntokens dominate cost/latency?}
    I -->|Yes| J[Fine-tune\nsee Decision - Full Fine-Tuning vs PEFT]
    I -->|No| H
    D --> K{Also need a fixed\ncitation/answer format?}
    K -->|Yes| L[RAG + fine-tune the\nformat/citation behavior]
    K -->|No| D
```

The deciding question is almost always: **is the gap knowledge, or is it behavior?** If the model doesn't know something, no amount of gradient updates reliably fixes that cheaply or safely — see [[Concept - What Fine-Tuning Can and Cannot Teach]] — so route to [[Deep Dive - RAG Architectures|RAG]]. If the model knows enough but responds in the wrong shape, at the wrong length, in the wrong tone, or too slowly because the prompt is huge, that's a behavior/format/latency gap, and fine-tuning is the tool built for it.

## Tradeoff matrix

| Approach | Engineering cost | Per-call cost | Latency | Update speed | Best for |
|---|---|---|---|---|---|
| Prompting / few-shot | ~$0, minutes to iterate | High — long prompts repeat every call | Extra prefill time for long prompts, mitigated by [[Concept - Prompt Caching]] | Instant | Low volume, fast iteration, exploratory tasks |
| RAG | Retrieval infra + indexing pipeline (days-weeks) | Retrieval cost + moderate prompt | + retrieval latency, tens to low-hundreds of ms | Near-instant — re-index and it's live | Facts that exist outside the model, especially ones that change |
| Fine-tuning (PEFT) | Data curation + a training run (hours, tens-hundreds of $ in compute) | Low — prompt shrinks once the behavior is baked in | No extra latency once the adapter is merged | Slow — requires a new training run | Stable behavior/format at scale, high call volume |
| Fine-tuning (full) | Data curation + a larger training run (GPU-days, hundreds-thousands of $) | Lowest per call | None | Slow and expensive | Large behavior/domain shift, single deployed model, need max quality |

The one-time training cost for fine-tuning ranges from tens of dollars (a small PEFT run on a rented GPU) to several thousand (larger full fine-tunes), but it buys a *permanently* shorter prompt — the savings compound at high call volume in a way prompting and RAG's per-call costs never do.

Combining approaches is common and often the right answer, not a compromise: fine-tune the citation/output-format behavior while RAG supplies the facts, so the model reliably wraps retrieved content in the right structure instead of improvising. Fine-tuning is also used to bake repeated few-shot exemplars directly into the weights, permanently cutting the tokens spent re-sending the same examples on every call — a different lever from [[Concept - Prompt Caching]], which speeds up a repeated prefix but still pays to transmit and prefill it once per session.

## The details that flip the decision

- **Strict output schema at high call volume flips to fine-tuning.** If every request needs perfectly formed structured output and the alternative is fighting [[Playbook - Reliable Structured Output|prompted structured output]] reliability at scale, baking the schema into weights via fine-tuning removes an entire class of parsing failures and stops paying token cost for repeated formatting instructions.
- **Rapidly changing data should never be fine-tuned.** If the source of truth updates daily or per-user, RAG's near-instant re-index beats a retraining cycle every time; fine-tuning frozen facts that are stale by ship time is a recurring, avoidable cost.
- **Fewer than ~500 good examples usually means prompting or RAG wins.** Below that, a fine-tune either underfits or overfits to idiosyncrasies of a small set, and a well-built prompt with a handful of few-shot examples (see [[Concept - Chain-of-Thought and Why It Works]] for structuring the reasoning that goes into them) captures most of the same behavior for a fraction of the cost.
- **The single most common wasted fine-tuning project is "fine-tune the model on our documentation" to teach it facts.** This is a knowledge gap wearing a fine-tuning-shaped disguise; see [[Concept - What Fine-Tuning Can and Cannot Teach]] before committing budget to it.
- **Cost engineering considerations can flip either way.** Once you're optimizing [[Concept - Cost Engineering for LLM Applications|per-token spend]] at scale, both a fine-tune-shortened prompt and [[Concept - Semantic Caching]] on repeated near-duplicate queries can dominate the decision independent of the underlying knowledge/behavior question — model the actual call-volume economics before committing to a training run.

## Connections
- [[Concept - What Fine-Tuning Can and Cannot Teach]] — the mechanistic reason knowledge gaps route to RAG, not fine-tuning.
- [[Decision - Full Fine-Tuning vs PEFT]] — the next decision once this one lands on "fine-tune."
- [[Deep Dive - RAG Architectures]] — the mechanism behind the RAG branch of this decision.
- [[Concept - Prompt Caching]] — mitigates the prompting branch's per-call token cost without a training run.
- [[Playbook - Reliable Structured Output]] — the prompted alternative to fine-tuning a fixed output schema, and the fallback if it isn't reliable enough.
- [[Concept - Chain-of-Thought and Why It Works]] — relevant to what a good prompt-first attempt looks like before escalating.
- [[Concept - Cost Engineering for LLM Applications]] — the framework for turning this decision's cost row into real dollar figures at your call volume.
- [[Concept - Semantic Caching]] — another lever that can close the cost gap prompting has against fine-tuning, without training anything.

## Sources
This is a distilled practitioner decision framework rather than a single citable result; the mechanisms behind each branch are cited in their own linked notes (RAG mechanics in [[Deep Dive - RAG Architectures]], the knowledge/behavior distinction in [[Concept - What Fine-Tuning Can and Cannot Teach]]).
