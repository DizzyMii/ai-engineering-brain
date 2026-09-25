---
tags: [concept, domain/retrieval-rag, level/frontier]
aliases: [active retrieval, adaptive retrieval, retrieve-on-demand, iterative RAG]
summary: "Retrieval driven by the model's own decisions — whether, what, and when to retrieve, and whether results suffice — instead of a fixed pipeline."
---
> **One-paragraph hook:** Classic RAG is a straight line: every query gets embedded, searched, stuffed and answered, whether or not it needed a lookup. Agentic retrieval gives that control flow to the LLM. The model decides *if* it needs external evidence, *what* to search for, *when* to search again, and whether what came back is good enough to answer from. It's the retrieval side of the move from pipelines to agents. It buys real accuracy on multi-hop and open-ended questions, and it costs latency, dollars, and a new class of failure (loops, over-retrieval, tool-choice errors) a static pipeline can't have.

## The mechanism

A static RAG pipeline runs retrieval on rails: `embed → search → rerank → generate`, unconditionally. Agentic retrieval replaces the fixed edges with decisions the LLM makes. Three research lineages define the design space, and they differ in *how much of the control logic is trained into the model versus prompted at inference*.

**Confidence-triggered retrieval: FLARE** (Jiang et al. 2023, *Forward-Looking Active REtrieval*). The model writes the answer one sentence at a time. Before committing a sentence it checks the token log-probabilities of the tentative continuation. If any token falls below a confidence threshold, generation pauses, the low-confidence span is masked out, the tentative sentence becomes a retrieval query, and generation restarts with the retrieved context. Retrieval fires *only where the model is unsure*.

**Trained reflection: Self-RAG** (Asai et al. 2023). The base model is fine-tuned to emit special *reflection tokens* inside normal text. A `Retrieve` token (yes / no / continue) gates search. `IsRel` / `IsSup` / `IsUse` tokens have the model critique each retrieved passage for relevance, for whether its own claim is *supported* by the passage, and for overall usefulness. The model generates the critique itself, so one forward pass both decides to retrieve and grades the groundedness of what it wrote. The labels are distilled from a stronger model into the target model's vocabulary during training.

**Evaluator-gated correction: CRAG** (Yan et al. 2024, *Corrective RAG*). A lightweight retrieval evaluator (a small fine-tuned scorer, separate from the generator) grades the retrieved set as `correct` / `ambiguous` / `incorrect`. `correct` triggers knowledge refinement: split passages into strips, keep the relevant ones, recompose. `incorrect` triggers a **web-search fallback** to get past a stale or thin corpus. `ambiguous` runs both and merges. The evaluator is a cheap gate deciding whether the expensive corrective path is worth running.

The fourth form, now dominant, is the least researchy: **retrieval-as-tool**. Search is exposed as a callable function, more and more often over the [[Concept - Model Context Protocol (MCP)|Model Context Protocol]], and the model calls it through [[Concept - Tool Use and Function Calling|function calling]] over several turns. It reformulates queries, hits several sources, and interleaves retrieval with reasoning the way [[Concept - Chain-of-Thought and Why It Works|chain-of-thought]] interleaves reasoning steps. Every "deep research" product runs on this. It reuses the generic [[Deep Dive - The Agent Loop|agent loop]] as-is; agentic retrieval is that loop with search as the main tool.

```
static RAG:      query ──> retrieve ──> generate                (one shot, always)

agentic:         query ──> [decide: retrieve?] ──no──> generate
                              │yes
                              v
                           retrieve ──> [evaluate: sufficient?] ──no──┐
                              ^                                        │
                              └──── reformulate / new source <─────────┘
                                            │yes
                                            v
                                         generate  (+ web fallback if corpus fails)
```

## In practice

In production *(as of 2026)*, **retrieval-as-tool beats trained reflection** for a mundane reason. You can't retrain a frozen API model to emit Self-RAG reflection tokens, but you can hand any function-calling model a search tool today. Self-RAG and CRAG are strongest when you own the weights, and FLARE needs token log-probs, which some APIs don't expose. So frontier labs build a tool-use agent that treats retrieval as one action among many, with the same hybrid-retrieve-then-rerank stack from [[Deep Dive - RAG Architectures]] behind its search tool. Static [[Concept - Query Transformation for Retrieval|query transformation]] rewrites or expands the query *once* before retrieval. The agent reformulates *adaptively* across rounds. One is a fixed pre-processing step, the other a feedback loop.

Agentic retrieval pays for itself on multi-hop questions that chain lookups ("which of the founders also sat on the board of the acquirer?"), on open-ended sensemaking, and, underrated, on knowing when to *abstain or skip retrieval*. It doesn't pay on single-fact lookups or latency-sensitive paths, where the extra round-trips are pure tax. Each iteration is an LLM call plus a retrieval round-trip, so a 3-round agentic answer costs seconds of latency and several times the tokens of one static pass.

## Failure modes

- **Retrieval loops / non-convergence.** The model keeps choosing to retrieve and never commits to an answer. *Detection:* count retrieval rounds per query and alarm on the tail. *Fix:* hard-cap iterations and force answer-or-abstain at the cap.
- **Over-retrieval noise.** More rounds bring more passages, and past a point the distractors *lower* accuracy. It's the over-retrieval pathology from [[Gotchas - RAG Pipelines]], self-inflicted by the agent this time. *Detection:* context-utilization metrics; ablate rounds against an eval set.
- **Miscalibrated confidence (FLARE-class).** Log-prob confidence is a weak proxy for factual correctness, and a confidently wrong model never triggers the retrieval it needs. *Detection:* correlate trigger events with known-hard queries.
- **Wrong-tool / wrong-source selection.** With several indexes or a web-search fallback, the agent routes to the wrong one. *Detection:* log the tool-call distribution per query class.
- **Scoring retrieval quality is hard in itself** (see [[Concept - RAG Evaluation]]). You now have to score the *decisions* as well as the final answer, or you can't tell a good trajectory from a lucky one.

## The non-obvious

The most valuable feature of agentic retrieval is the **decision *not* to retrieve**. The iteration machinery gets the attention. Static RAG injects context into every query, including ones that need none (chit-chat, pure reasoning, arithmetic), and that context isn't free: it dilutes the prompt with distractors and measurably degrades answers. In many production systems the highest-ROI "agentic" move is the cheapest one, a routing gate that classifies whether retrieval is warranted, and it beats the elaborate self-critique loops it's usually sold with. On most real traffic, FLARE-style confidence gating and Self-RAG reflection tokens have a worse cost/benefit ratio than a one-line "should I search?" classifier.

The second lesson is about security. Once retrieval is a tool the model can aim, especially with a **web-search fallback** that pulls untrusted content into an agent that also holds private data and can act, you've built the [[Concept - The Lethal Trifecta for Agents|lethal trifecta]]. CRAG's "fall back to the open web when the corpus fails" is the move that turns a benign retriever into a prompt-injection surface. Agentic retrieval and agent security are one problem seen from two sides.

## Connections

- [[Deep Dive - The Agent Loop]] — agentic retrieval is that loop with search as the primary tool; the control logic is inherited, not reinvented.
- [[Concept - Tool Use and Function Calling]] — the mechanism by which a frozen model actually invokes retrieval as an action.
- [[Concept - Model Context Protocol (MCP)]] — the emerging standard for exposing search (and other) tools to the model uniformly.
- [[Deep Dive - RAG Architectures]] — places agentic retrieval at the end of the naive → advanced → modular → agentic progression, and supplies the retrieval stack it calls.
- [[Concept - Query Transformation for Retrieval]] — the *static* precursor: rewriting/expanding queries once, before the model gets to decide adaptively.
- [[Concept - Chain-of-Thought and Why It Works]] — agentic retrieval interleaves retrieval with the same step-by-step reasoning CoT unlocks.
- [[Concept - RAG Evaluation]] — you must now evaluate retrieval *decisions and trajectories*, not just final answers.
- [[Gotchas - RAG Pipelines]] — the over-retrieval and lost-in-the-middle failures agentic loops can amplify.
- [[Concept - The Lethal Trifecta for Agents]] — why a web-search fallback plus private data plus action capability is a prompt-injection exposure, not just a recall feature.

## Sources

- Jiang et al. (2023) — *Active Retrieval Augmented Generation* (FLARE). Retrieve-on-demand gated by next-token confidence.
- Asai et al. (2023) — *Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection*. Trained reflection tokens that gate retrieval and self-grade groundedness.
- Yan et al. (2024) — *Corrective Retrieval Augmented Generation* (CRAG). A lightweight evaluator that triggers knowledge refinement or web-search fallback.
