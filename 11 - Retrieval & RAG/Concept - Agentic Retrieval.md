---
tags: [concept, domain/retrieval-rag, level/frontier]
aliases: [active retrieval, adaptive retrieval, retrieve-on-demand, iterative RAG]
summary: "Retrieval driven by the model's own decisions — whether, what, and when to retrieve, and whether results suffice — instead of a fixed pipeline."
---
> **One-paragraph hook:** Classic RAG is a straight line: every query gets embedded, retrieved against, stuffed, and answered, whether or not it needed a lookup. Agentic retrieval hands that control flow to the LLM itself — the model decides *if* it needs external evidence, *what* to search for, *when* to search again, and whether what came back is good enough to answer from. It is the retrieval-side of the shift from pipelines to agents, and it buys real accuracy on multi-hop and open-ended questions at the cost of latency, dollars, and a new class of failure (loops, over-retrieval, tool-choice errors) that a static pipeline simply cannot have.

## The mechanism

A static RAG pipeline has retrieval on rails: `embed → search → rerank → generate`, run unconditionally. Agentic retrieval replaces the fixed edges with LLM-issued decisions. Three research lineages define the design space, and they differ in *how much of the control logic is trained into the model versus prompted at inference*.

**Confidence-triggered retrieval — FLARE** (Jiang et al. 2023, *Forward-Looking Active REtrieval*). The model generates the answer one sentence at a time. Before committing a sentence, it inspects the token log-probabilities of the tentative continuation; if any token falls below a confidence threshold, generation pauses, the low-confidence span is masked out, the tentative sentence becomes a retrieval query, and generation restarts with the retrieved context. Retrieval fires *only where the model is unsure* — retrieve-on-demand rather than retrieve-always.

**Trained reflection — Self-RAG** (Asai et al. 2023). The base model is fine-tuned to emit special *reflection tokens* interleaved with normal text: a `Retrieve` token (yes / no / continue) gates whether to search, and `IsRel` / `IsSup` / `IsUse` tokens make the model critique each retrieved passage for relevance, whether its own claim is *supported* by that passage, and overall usefulness. The critique is generated, not external, so a single forward pass both decides to retrieve and grades the groundedness of what it wrote. The labels are distilled from a stronger model into the target model's vocabulary during training.

**Evaluator-gated correction — CRAG** (Yan et al. 2024, *Corrective RAG*). A lightweight retrieval evaluator (a small fine-tuned scorer, not the generator) grades the retrieved set as `correct` / `ambiguous` / `incorrect`. `correct` triggers a knowledge-refinement step (decompose passages into strips, keep the relevant ones, recompose); `incorrect` triggers a **web-search fallback** to escape a stale or thin corpus; `ambiguous` runs both and merges. The evaluator is the cheap gate that decides whether the expensive corrective path is worth it.

The fourth and now-dominant form is the least "researchy": **retrieval-as-tool**. Search is exposed as a callable function — increasingly over the [[Concept - Model Context Protocol (MCP)|Model Context Protocol]] — and the model invokes it through [[Concept - Tool Use and Function Calling|function calling]] across multiple turns, reformulating queries and hitting multiple sources, interleaving retrieval with reasoning the way [[Concept - Chain-of-Thought and Why It Works|chain-of-thought]] interleaves reasoning steps. This is the mechanism underneath every "deep research" product. It reuses the generic [[Deep Dive - The Agent Loop|agent loop]] wholesale; agentic retrieval is that loop with search as the primary tool.

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

The production reality (as of 2026) is that **retrieval-as-tool wins over trained reflection**, for a mundane reason: you cannot retrain a frozen API model to emit Self-RAG reflection tokens, but any function-calling model can be handed a search tool today. Self-RAG and CRAG are strongest when you own the weights; FLARE needs token log-probs, which some APIs don't expose. So the frontier-lab pattern is a tool-use agent that decides retrieval as one action among many, sitting on top of the same hybrid-retrieve-then-rerank stack from [[Deep Dive - RAG Architectures]] as its search tool. Where static [[Concept - Query Transformation for Retrieval|query transformation]] rewrites or expands the query *once* before retrieval, the agent reformulates *adaptively* across rounds — the difference between a fixed pre-processing step and a feedback loop.

Where agentic retrieval earns its cost: multi-hop questions ("which of the founders also sat on the board of the acquirer?") that require chaining lookups; open-ended sensemaking; and — underrated — knowing when to *abstain or not retrieve at all*. Where it doesn't: single-fact lookups and latency-sensitive paths, where the extra round-trips are pure tax. Each iteration is an LLM call plus a retrieval round-trip, so a 3-round agentic answer is seconds of latency and several times the token cost of one static pass.

## Failure modes

- **Retrieval loops / non-convergence.** The model keeps deciding to retrieve and never commits to an answer. *Detection:* count retrieval rounds per query; alarm on the tail. *Fix:* hard-cap iterations and force an answer-or-abstain at the cap.
- **Over-retrieval noise.** More rounds inject more passages, and past a point the distractors *lower* accuracy — the same over-retrieval pathology catalogued in [[Gotchas - RAG Pipelines]], now self-inflicted by the agent. *Detection:* context-utilization metrics; ablate rounds against an eval set.
- **Miscalibrated confidence (FLARE-class).** Log-prob confidence is a weak proxy for factual correctness; a confidently wrong model never triggers the retrieval it needs. *Detection:* correlate trigger events against known-hard queries.
- **Wrong-tool / wrong-source selection.** With multiple indexes or a web-search fallback, the agent routes to the wrong one. *Detection:* log the tool-call distribution per query class.
- **Evaluating retrieval quality is itself hard** — see [[Concept - RAG Evaluation]]; you now have to score the *decisions*, not just the final answer, or you can't tell a good trajectory from a lucky one.

## The non-obvious

The headline feature of agentic retrieval is not the iteration machinery — it is the **decision to *not* retrieve**. Static RAG injects context into every query, including ones that need none (chit-chat, pure reasoning, arithmetic), and that unnecessary context is not free: it dilutes the prompt with distractors and measurably degrades answers. In many production systems the single highest-ROI "agentic" move is the cheapest one — a routing gate that classifies whether retrieval is warranted at all — and it beats the elaborate self-critique loops it's usually sold alongside. The elaborate part (FLARE-style confidence gating, Self-RAG reflection tokens) has a worse cost/benefit ratio than the boring part (a one-line "should I search?" classifier) on the majority of real traffic.

The second hard-won lesson is a security one: the moment retrieval becomes a tool the model can aim — especially with a **web-search fallback** that pulls untrusted content into the context of an agent that also has private data and a way to act — you have assembled the [[Concept - The Lethal Trifecta for Agents|lethal trifecta]]. CRAG's "escape to the open web when the corpus fails" is exactly the move that turns a benign retriever into a prompt-injection surface. Agentic retrieval and agent security are the same problem viewed from two sides.

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
