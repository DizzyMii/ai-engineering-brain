---
tags: [concept, domain/prompting-context, level/core]
aliases: [context management]
summary: "The discipline of curating everything that occupies the finite context window, since irrelevant tokens measurably degrade output."
---
> **One-paragraph hook:** "Prompt engineering" assumes there's one prompt to write. Production systems, agentic ones especially, pour a system prompt, tool schemas, retrieved documents, conversation history and few-shot exemplars into the same finite window on every call, and all of those tokens compete for the model's attention. Context engineering is deciding, at each step, what gets a place in that window. Irrelevant tokens don't just fail to help; they measurably make the model worse.

## The mechanism

The rename from "prompt engineering" to "context engineering" caught on during 2025. The usage is credited to Andrej Karpathy and Shopify's Tobi Lütke, and Anthropic and LangChain picked it up in engineering writeups. It stuck because the work practitioners spend their time on had changed. For a multi-turn or agentic system, a single well-worded instruction was never the bottleneck. The bottleneck is that the context window is a fixed-size shared resource. The [[Concept - System Prompts]], tool schemas ([[Concept - Tool Use and Function Calling]]), the running conversation, documents pulled in by retrieval ([[Deep Dive - RAG Architectures]]), few-shot exemplars and the live query all draw from the same budget.

The competition is over attention as well as budget. Attention is a softmax over every position in the sequence, so each added token moves probability mass away from the tokens that matter. [[Concept - Context Rot]] is the empirical result: measured quality drops as irrelevant content lengthens the effective sequence, well inside the advertised window. Anthropic calls the target "the right altitude". Context should be specific enough to steer the model on the task at hand and general enough not to overfit to one example or one turn. A small, high-signal set of tokens reliably beats a dump of everything that might conceivably be relevant, which is the opposite of the instinct that more context is always safer.

## In practice

The levers are curation choices made each turn. Polishing prose isn't one of them.
- **Retrieve-then-pack vs. stuff-everything.** Select the k most relevant documents or results and insert only those; don't load full source material by default. It's the same instinct that motivates retrieval in the first place ([[Deep Dive - RAG Architectures]]).
- **Ordering.** Put static, shared content (system prompt, tool schemas, exemplars) first so it can sit in the cache-friendly prefix ([[Concept - Prompt Caching]]). State critical instructions at the very start of the window *and* again near the end, since the model uses middle positions least reliably.
- **Compression.** Summarize or roll up stale turns instead of carrying the full transcript forever. The mechanics (summarization, externalizing to files, sub-agent isolation) are in [[Concept - Context Compaction]].
- **Tool-result trimming.** Have tool calls return distilled, structured results, not raw verbose payloads. In agentic loops, tool output is usually the biggest single consumer of the budget, far larger than the user's actual instructions.
- **Just-in-time vs. upfront loading.** Fetch a document or memory record when the current step needs it, instead of front-loading everything the agent might need later.

You can't see any of this without instrumentation. [[Concept - LLM Observability and Tracing]] is how you find out what's in the window on a given call, with token counts by category and not only a total. Teams that skip tracing typically find context bloat only when it shows up as a cost or latency regression, long after it started hurting accuracy.

## Failure modes

- **Overflow silently truncates the system prompt.** Many client libraries truncate from the head when input exceeds the window, and the head is where the system prompt and its persona and rules live. No error. The model just stops following its own instructions.
- **Tool-schema bloat.** A big tool registry with verbose JSON schemas can use a meaningful share of the budget before any real conversation happens. You won't notice unless you measure schema token count directly.
- **Stale history poisons later turns.** An early wrong tool result or hallucinated fact stays in the transcript. Later turns condition on it as if it were verified, and the error spreads instead of correcting itself.
- **Retrieved documents contradict each other.** Two chunks that disagree leave the model to arbitrate with no signal about which one is authoritative, and it sometimes blends both into an incoherent answer.
- **From outside, all of these look the same.** Bloat, drift and contradiction all show up as a wrong or degraded answer until [[Concept - LLM Observability and Tracing]] shows what was in the window at the time.

## The non-obvious

When a model misses something, the reflex is nearly always to add context: paste in the extra document, extend the system prompt, include another exemplar just in case. That reflex is wrong often enough to be dangerous. Irrelevant but plausible content competes for attention better than pure noise does, so a marginally relevant document added to "help" can measurably lower accuracy on the task it was meant to fix ([[Concept - Context Rot]]). The right diagnostic move is usually to subtract, curating down to the smallest high-signal set.

The other surprise is where the budget goes. In most agentic systems, tool outputs and conversation history outweigh the user's instructions in token count, often by an order of magnitude. So context engineering is mostly tool-output and history design (trimming, summarizing, structuring what a tool returns), and wordsmithing the system prompt is a small part of it. A team polishing the system prompt while ignoring verbose, unstructured tool output is optimizing roughly the smallest slice of its context budget.

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
