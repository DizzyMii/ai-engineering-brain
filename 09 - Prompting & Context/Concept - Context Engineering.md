---
tags: [concept, domain/prompting-context, level/core]
aliases: [context management]
summary: "The discipline of curating everything that occupies the finite context window, since irrelevant tokens measurably degrade output."
---
> **One-paragraph hook:** "Prompt engineering" implicitly assumes there is one prompt to craft. Real production systems — especially agentic ones — pour a system prompt, tool schemas, retrieved documents, conversation history, and few-shot exemplars into the same finite window on every single call, and every one of those tokens competes for the model's attention. Context engineering is the discipline of deciding, at each step, exactly what earns a place in that window — because the model doesn't just fail to benefit from irrelevant tokens, it measurably gets worse because of them.

## The mechanism

The rename from "prompt engineering" to "context engineering" took hold across 2025 — usage is credited to Andrej Karpathy and to Shopify's Tobi Lütke, and it was picked up in engineering writeups from Anthropic and LangChain — precisely because the thing practitioners actually spend their time on shifted. A single well-worded instruction was never the bottleneck for a multi-turn or agentic system; the bottleneck is that the context window is a fixed-size, shared resource, and every category of content — the [[Concept - System Prompts]], tool schemas ([[Concept - Tool Use and Function Calling]]), the running conversation, documents pulled in by retrieval ([[Deep Dive - RAG Architectures]]), few-shot exemplars, and the live query — draws from the same budget.

That competition is not just a bookkeeping problem, it's an attention problem: attention is a softmax over every position in the sequence, so adding tokens doesn't just cost budget, it redistributes probability mass away from the tokens that actually matter. [[Concept - Context Rot]] is the direct empirical consequence — measured quality degrades as irrelevant content grows the effective sequence, well inside the advertised context window. Anthropic's framing for the discipline is "the right altitude": context should be specific enough to actually steer the model's behavior for the task at hand, but general enough that it doesn't overfit to one example or one turn. A minimal, high-signal set of tokens reliably beats a kitchen-sink dump of everything that might conceivably be relevant — which inverts the naive instinct that more context is strictly safer.

## In practice

The concrete levers are curation choices made at each turn, not prose to polish:
- **Retrieve-then-pack vs. stuff-everything** — select the k most relevant documents or results and insert only those, instead of loading full source material by default; this is the same instinct that motivates retrieval in the first place ([[Deep Dive - RAG Architectures]]).
- **Ordering** — put static, shared content (system prompt, tool schemas, exemplars) first so it can sit in the cache-friendly prefix ([[Concept - Prompt Caching]]), and place critical instructions at both the very start of the window *and* restate them near the end, since middle positions are used least reliably.
- **Compression** — summarize or roll up stale conversation turns instead of carrying the full transcript forever; the mechanics of this — summarization, externalization to files, sub-agent isolation — belong to [[Concept - Context Compaction]].
- **Tool-result trimming** — return distilled, structured results from tool calls rather than raw verbose payloads. In agentic loops, tool output volume is usually the single largest consumer of the budget, dwarfing the user's actual instructions.
- **Just-in-time vs. upfront loading** — fetch a document or memory record only when the current step actually needs it, instead of always front-loading everything the agent might conceivably need later.

None of this is visible without instrumentation: [[Concept - LLM Observability and Tracing]] is how you actually see what's occupying the window on a given call — token counts by category, not just a total — and teams that skip tracing typically discover context bloat only once it shows up as a cost or latency regression, well after it started degrading accuracy.

## Failure modes

- **Context overflow silently truncates the system prompt.** Many client libraries truncate from the head of the sequence when input exceeds the window, which is exactly where the system prompt and its persona/rules live — the failure produces no error, just a model that quietly stops following its own instructions.
- **Tool-schema bloat.** A large tool registry with verbose JSON schemas for each tool can consume a meaningful share of the budget before a single turn of real conversation happens; invisible unless schema token count is measured directly.
- **Stale history poisoning later turns.** An early wrong tool result or hallucinated fact persists in the transcript and compounds — later turns condition on it as if it were verified, and the error propagates instead of self-correcting.
- **Retrieved-document contradictions.** Two retrieved chunks that disagree force the model to arbitrate with no signal for which is authoritative, sometimes silently blending both into an incoherent answer.
- **All of the above look identical from the outside.** Context bloat, drift, and contradiction all present as one thing — a wrong or degraded answer — until [[Concept - LLM Observability and Tracing]] shows what was actually in the window when it happened.

## The non-obvious

The instinct when a model misses something is almost always to add more context — paste in the extra document, extend the system prompt, include another exemplar "just in case." That instinct is backwards often enough to be dangerous: irrelevant-but-plausible content competes for attention mass more effectively than pure noise does, so adding a marginally-relevant document to "help" can measurably lower accuracy on the exact task it was meant to fix ([[Concept - Context Rot]]). The correct diagnostic move is usually subtractive — curate down to the smallest high-signal set — not additive.

The second non-obvious point is where the budget actually goes in practice: in most agentic systems, tool outputs and conversation history dwarf the user's actual instructions in token count, often by an order of magnitude. Context engineering is therefore mostly an exercise in disciplined tool-output and history design — trimming, summarizing, structuring what a tool returns — rather than wordsmithing the system prompt. Teams that spend their optimization effort polishing the system prompt while ignoring verbose, unstructured tool outputs are optimizing roughly the smallest fraction of their actual context budget.

## Connections
- [[Concept - Context Rot]] — the direct mechanistic consequence of poor context curation: quality degrades as irrelevant content grows, which is the reason this discipline exists.
- [[Concept - Context Compaction]] — the concrete techniques (summarization, externalization, sub-agent isolation) for keeping long-running context within budget.
- [[Deep Dive - RAG Architectures]] — the retrieval layer that decides what documents even become candidates for the context window.
- [[Concept - Tool Use and Function Calling]] — tool schemas and tool outputs are frequently the largest and least-curated consumer of the context budget.
- [[Concept - Agent Memory Systems]] — durable memory that lives outside the context window is the complementary strategy to curating what's inside it.
- [[Concept - LLM Observability and Tracing]] — the instrumentation required to see what is actually occupying the window on any given call.
- [[Concept - Prompt Caching]] — ordering the context for cache-friendliness (static-first) is one of the concrete curation levers this discipline applies.
- [[Concept - System Prompts]] — one of the fixed, usually-static components that permanently occupies a share of the same context budget.
- [[Concept - Prompt Engineering]] — the earlier, narrower discipline (wording a single instruction) that context engineering supersedes as the primary design surface for multi-turn and agentic systems.

## Sources
- Karpathy, A. (2025) — social-media commentary popularizing "context engineering" as the more accurate successor term to "prompt engineering." Framing source, not a peer-reviewed paper.
- Lütke, T. (2025) — Shopify CEO's public framing of context engineering as the discipline of providing all the context needed for a task to be plausibly solvable. Independently converged on the same term.
- Anthropic (2025) — "Effective context engineering for AI agents," engineering blog. Source for the "right altitude" framing and the curation-lever guidance above.
- Liu et al. (2023) — "Lost in the Middle: How Language Models Use Long Contexts." Empirical anchor for why position within the context window affects how reliably content is used, motivating the ordering lever above.
