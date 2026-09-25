---
tags: [ladder, domain/home, level/surface]
aliases: [Zero to AI Application Engineer, AI application engineering path, LLM app engineer ladder, prompting to production ladder]
summary: "Ordered surface-to-unicorn walk from prompting through RAG, agents, fine-tuning, evals, and production ops for shipping LLM products."
---

# Ladder - Zero to AI Application Engineer

A walk through six Engineering Wing domains: 09 (Prompting & Context), 10 (Agents), 11 (Retrieval & RAG), 12 (Fine-Tuning), 13 (Evaluation) and 16 (Production & Ops). The goal is to go from zero to someone who ships an LLM-powered product that survives real traffic, where a demo would fall over. Thirty-seven steps. Prompting mechanics come first, then context as the actual unit of engineering, then retrieval, then agents, then when (and when not) to fine-tune, then how to measure whether any of it works, then how to run it in production without the bill or the model shifting under you. It closes on the folklore every team either learns the hard way or reads here first. Read each note for the one mechanism or number named under it; if you can answer the self-test, move on. This is the widest track in the vault, six dense domains where most ladders draw from two or three, so budget more time for it. For the full 25-domain map, including the training, inference and hardware layers this track treats as a black box behind a provider API, start at [[Home]].

---

## Act I: Prompting That Works

**1. [[Concept - Prompt Engineering]]**
One sentence kills the mysticism: a prompt is just $x_{<t}$, the conditioning event for $P(x_t \mid x_{<t})$. No weights move and no hidden parser runs. You steer a frozen function by choosing its input. Sort levers into two bins, mechanism-backed (structure, worked examples, asking for intermediate reasoning) and folklore-tier (tipping, threats, "world-class expert" framing), and build production systems only on the first. The trap: because the function is fixed, a prompt's behavior is reproducible under the same decoding settings. So a "prompt that broke" after a silent model swap means the function changed. It doesn't mean prompting is inherently unstable.
*Self-test:* Why does a prompt that "used to work" sometimes break with zero code changes on your end?

**2. [[Concept - System Prompts]]**
Nothing in the transformer architecture enforces system-role authority. It's a *learned statistical tendency*, installed by SFT/RLHF, for tokens after the `system` marker to outrank later user tokens, formalized as system > developer > user > tool-output in OpenAI's instruction hierarchy. The authority is soft. It decays as a conversation grows, since the system prompt becomes a shrinking fraction of total context, and a later user turn can silently override it with no error. Assume leakage: extraction attacks work trivially against most systems, so never put a credential or unpublished logic in one.
*Self-test:* Why is "the system prompt used to work and now doesn't" a common incident after a silent model upgrade, even when the prompt text never changed?

**3. [[Concept - In-Context Learning]]**
The domain's most counterintuitive empirical result: Min et al. (2022) found that randomizing the labels in few-shot classification exemplars barely hurts accuracy. Exemplars mostly teach *format and label space*. The model isn't inferring a fresh input-output mapping. Mechanistically, induction heads (a prefix-match-and-copy attention circuit) do much of the work, and they form during pretraining as a visible phase change, not gradually. Practical payoff: spend effort on formatting consistency before exemplar curation, since format dominates content for most tasks.
*Self-test:* If scrambling the labels on your few-shot examples barely hurts accuracy, what does that tell you about where to spend your prompt-debugging time?

**4. [[Concept - Chain-of-Thought and Why It Works]]**
A transformer has fixed per-token compute. Chain-of-thought turns one hard prediction into many easy ones: each reasoning token becomes context for the next, buying $k$ forward passes for a $k$-step problem instead of one. Two numbers made it a practitioner tool. Kojima et al.'s zero-shot "let's think step by step" lifted GSM8K accuracy from roughly 18% to roughly 41% with no exemplars, and the effect only *emerges* above roughly 60-100B parameters; below that, CoT can hurt. Keep the faithfulness problem in mind as well. Written reasoning can be post-hoc rationalization that never mentions the bias actually driving the answer, so CoT text is not a reliable audit trail.
*Self-test:* Why does telling a reasoning model (o1-class, R1, extended-thinking Claude) to "think step by step" range from redundant to actively counterproductive?

**5. [[Concept - Chat Templates and Special Tokens]]**
The silent failure: a chat model was trained on one exact token sequence, with markers like `<|im_start|>` or `<|eot_id|>` in specific positions. Rebuild it slightly wrong (a doubled BOS token, a missing newline) and quality drops with no exception thrown, because nothing checks your string against what post-training saw. `apply_chat_template` is the source of truth. It replaced the pre-2023 folklore era of hand-maintained per-model format registries. There's a security angle in how prompts get assembled: naively concatenating untrusted user text before tokenization can let a literal substring like `<|im_start|>assistant` encode as the real role-switch control token. That's a tokenization bug, not a semantic prompt injection.
*Self-test:* Why does a base (non-chat) checkpoint get worse, not neutral, results when you apply a chat template to it?

---

## Act II: Context Is the Product

**6. [[Concept - Context Engineering]]**
The reframe that took hold across 2025. For multi-turn and agentic systems the bottleneck was never one well-worded instruction. The context window is a fixed-size shared resource, and attention is a softmax over every position, so more tokens pull probability mass away from what matters. Anthropic's "right altitude" framing states the target: specific enough to steer behavior, general enough not to overfit to one turn. In most agentic systems, tool outputs and history outweigh the user's actual instructions by an order of magnitude, so context engineering is mostly disciplined tool-output design. System-prompt wordsmithing is the small part.
*Self-test:* Your agent misses a fact. Why is the instinct to "just add more context" backwards often enough to be dangerous?

**7. [[Concept - Context Rot]]**
A 1M-token context window is a spec. It doesn't guarantee usable capacity, because attention is a softmax whose denominator grows with every token. The "lost in the middle" result shows accuracy is U-shaped in the position of the relevant fact, dropping substantially (sometimes below a no-context baseline) when the fact sits mid-window. A 2025 multi-model study generalized this into smooth performance decay with input length well inside the advertised window, which is where "context rot" comes from. The trap: a model can ace needle-in-a-haystack retrieval of one verbatim fact at 1M tokens and still fail badly at multi-hop aggregation across five facts in the same window. Passing that demo proves nothing about real long-context workloads.
*Self-test:* A vendor shows you a green needle-in-a-haystack heatmap at 1M tokens. What class of failure does that demo not rule out?

**8. [[Concept - Prompt Caching]]**
Caching keeps the KV cache for a token prefix, so a request sharing that exact prefix skips prefill. Matching stops at the *first* byte divergence: a timestamp ahead of the reusable content busts the whole cache even if the expensive part is identical. Anthropic's numbers: writes cost roughly 1.25x base price, reads roughly 0.1x. Solve the break-even and a *second* use of the same prefix already makes caching cheaper, while a prefix used exactly once costs 25% more than not caching. What almost everyone misses: turning caching on everywhere without checking reuse can raise spend, and caches are scoped per region, so round-robin load balancing across regions can defeat your cache without anyone noticing.
*Self-test:* You enable prompt caching everywhere and your bill goes up. What's the most likely reason?

**9. [[Playbook - Reliable Structured Output]]**
Four tiers, weakest to strongest. Plain prompt plus a described schema (roughly 85-98% valid JSON, no guarantees). Provider-native structured output (syntactic validity near 100%, server-enforced). Grammar-constrained decoding (invalid tokens masked at every decode step, so valid by construction). Forced tool-calling used purely as a JSON transport. Pick the cheapest tier that clears your error budget, then close the gap with a bounded validate-repair loop. A second call carrying the parser's literal error string typically pushes single-shot valid-parse rates to 99%+ after one repair pass. The big caveat: constrained decoding guarantees syntax, never semantics. A grammar forces correct field names and still lets the model fill them with hallucinated values.
*Self-test:* Your structured-output pipeline parses cleanly 100% of the time. Does that mean it's correct? What gap does this playbook insist you measure separately?

---

## Act III: Retrieval

**10. [[Concept - Retrieval-Augmented Generation]]**
RAG swaps parametric recall (facts baked into weights) for non-parametric recall (facts in an external store you can inspect and update), reducing the model's job to reading comprehension over whatever was retrieved. Rule of thumb: retrieval is the bottleneck, generation isn't. A frontier model handed the wrong three paragraphs gives a confident wrong answer, because nothing in generation signals "this context is irrelevant." The hardest point to internalize: RAG doesn't eliminate hallucination, it moves where hallucination can happen. A model can retrieve the correct passage and still override it with its own parametric prior.
*Self-test:* A RAG system retrieves the perfect passage and still gives a wrong answer. Name the two distinct ways that can happen.

**11. [[Concept - Embedding Models]]**
A dual-encoder embeds query and document independently into fixed vectors compared by cosine or dot product. Fast and precomputable, but it can't do joint query-document attention, which is the gap a cross-encoder reranker patches two steps later in this ladder. The most common production bug: most modern embedders expect an instruction or prefix format baked in at training time (a literal `"query: "` versus `"passage: "` string), and leaving it out silently halves recall with no error. Treat public leaderboard rank as a marketing number. It's public and static, so developers tune against it. The fix is a 50-100 query golden set from your own corpus, tested on day one.
*Self-test:* Your embedder tops the public leaderboard but recall on your corpus is mediocre. What's the first thing to check before blaming the model?

**12. [[Concept - Chunking Strategies]]**
The most under-invested, highest-payoff lever in the pipeline. Whatever lands on the wrong side of a chunk boundary is gone from that chunk's embedding for good. Moving from a naive fixed-size splitter to a structural or semantic one routinely recovers more recall than switching to a better embedding model, because any embedder can retrieve a well-formed chunk and none can retrieve a decapitated table row or function. The size tension: small chunks give precise embeddings but fragment context; large chunks keep context but mean-pooling blurs the signal into everything else in the chunk. The standard fix is small-to-big (parent-document) retrieval: embed small for search precision, return the larger parent as generation context.
*Self-test:* A table row is retrieved correctly but the model still can't answer. What chunking failure produces this symptom?

**13. [[Concept - Hybrid Search and Reciprocal Rank Fusion]]**
Naive score-summing is broken. Lexical scores are unbounded and corpus-dependent, cosine similarity sits in a fixed range, so adding them lets whichever is bigger dominate. Reciprocal Rank Fusion avoids the problem by fusing on *rank*: sum $\frac{1}{k+\text{rank}_i(d)}$ across systems, with $k \approx 60$, a constant from 2009 TREC experiments that has survived over a decade of production use with almost no one re-deriving it. Keep the division of labor straight. Hybrid search *raises recall* (gets the right document somewhere in the candidate set); a reranker *raises precision* (puts it at rank 1). Mixing them up and shipping fused output straight to users is a common mistake.
*Self-test:* Why does k≈60 in the fusion formula almost never need per-corpus tuning, unlike nearly every other ML hyperparameter?

**14. [[Concept - Rerankers]]**
A cross-encoder concatenates query and document into one input so every token attends to every other token. That's strictly more expressive than a bi-encoder's independently pooled vectors, but nothing can be precomputed, so scoring N candidates costs N full forward passes at query time. So rerankers only run as a second stage over 50-200 candidates a cheap retriever already narrowed down, never as first-stage retrieval over a full corpus. A reranker can only reorder what retrieval found. If the correct document never made the shortlist, no reranking recovers it, so disappointing results after adding one are usually a misdiagnosed first-stage recall problem.
*Self-test:* You add a reranker and end-to-end accuracy doesn't improve, even though the retrieval-quality metric on the candidates went up. Where do you look first?

**15. [[Concept - RAG Evaluation]]**
A RAG pipeline has two failure surfaces, retrieval and generation, and both show the same symptom: a wrong answer. You can't localize a failure from the final answer alone. You need per-stage metrics against a labeled golden set. The standard open-source framework scores faithfulness and answer relevancy with an LLM judge and needs no gold labels, so it's the default starting point. It also inherits every LLM-judge bias, the same ones this ladder covers later under Measure. The most common organizational mismeasurement: a team optimizes a retrieval-ranking metric in isolation, ships a reranker that lifts it by double digits, and never checks whether end-to-end faithfulness moved, when the generator was already ignoring context past the first couple of chunks.
*Self-test:* A reranker upgrade raises a retrieval-ranking metric by 15 points but end-to-end answer quality doesn't budge. What does that combination tell you?

**16. [[Playbook - Building a Production RAG System]]**
The build order isn't negotiable. Build the eval set first, 50-200 hand-labeled query / relevant-chunk / ideal-answer triples, before any pipeline code, because without it every later tuning decision is unfalsifiable. Two recall readings flag real trouble. Near-random recall right after embedding almost always means a missing instruction prefix, not a chunking bug. Recall still low after fusion and reranking means the ceiling is set upstream, at chunking or the embedder. The reranker isn't it. Generation needs an explicit cite-or-abstain instruction: confident wrong answers on unanswerable questions are a prompt problem, and more retrieval won't fix them.
*Self-test:* Recall comes back near-random immediately after the embedding step. What's the first thing to check before suspecting the model or the corpus?

---

## Act IV: Agents

**17. [[Concept - What Is an LLM Agent]]**
One distinction cuts through the marketing. In a workflow, your code decides what happens next. In an agent, the model decides. That's the whole definition. An agent needs five parts: a model, a tool set, a loop, a termination condition and accumulated context. Remove any one and what's left isn't an agent. The heuristic that holds up in production: use an agent only when the steps can't be hardcoded in advance. Reliability compounds multiplicatively across steps, so each added decision is another chance to be wrong, and a working workflow is almost always cheaper and easier to debug than a working agent.
*Self-test:* You're building a document-summarization feature and reaching for an agent framework. What question should you answer first, and what does the honest answer usually turn out to be?

**18. [[Deep Dive - The Agent Loop]]**
Every agent framework reduces to five lines: call the model, check for a tool call, run it if present, append the result, repeat until a stop condition fires. The transcript is append-only, so a 30-turn run is one geometrically growing call, and treating it as 30 independent calls gets the cost wrong. The implementation rule people miss: never edit or reorder earlier messages. Prompt caching needs a byte-identical prefix, and a "smarter" edit-in-place context strategy can lose money the moment it busts the cache on a long-running agent. Production harnesses converge on a turn cap in the 10-50 range plus a token or wall-clock budget, because the model can't be trusted to always stop promptly.
*Self-test:* Why does editing an earlier tool result in an agent's transcript, even to fix an obvious mistake, often cost more than leaving the mistake in place?

**19. [[Concept - Tool Use and Function Calling]]**
The model only ever sees a tool's name, description and parameter schema. It never sees your implementation. So two functionally identical tools with different descriptions get picked at meaningfully different rates. Past roughly 20-40 tools on one agent, selection quality measurably degrades, and retrieval-over-tools and namespacing exist as standard mitigations for that. The forcing lever: set the tool-choice parameter to require a call. That's the standard fix for a model that narrates an action in prose ("I'll now search...") instead of emitting the call.
*Self-test:* Swapping in a more capable model doesn't fix your agent's tool-selection errors. What should you rewrite instead?

**20. [[Concept - Model Context Protocol (MCP)]]**
The economic argument in one line: bespoke tool integrations are $O(M \times N)$ for $M$ host apps and $N$ integrations, and a shared client/server protocol collapses that to $O(M+N)$. Editor-to-language-server and application-to-database connections were standardized the same way. MCP servers expose tools, resources and prompts over JSON-RPC 2.0, through a local subprocess or a remote HTTP transport. The sharp edge: a server's tool descriptions are text the model reads and trusts, with no privilege bit. A compromised or "rug-pulled" server, one that changes its tool definitions after you reviewed and approved it, is a direct injection vector. Treat every third-party server description as untrusted input, and hash and diff it on every update.
*Self-test:* You approved an MCP server's tools last month and haven't touched the integration since. What risk have you silently accepted by not re-reviewing it?

**21. [[Concept - Agent Memory Systems]]**
Two systems define the field. One scores retrieval candidates on a weighted sum of recency, importance and relevance and re-injects them every turn. In the other, the model *pages* memory in and out itself by calling functions, instead of receiving an injected retrieval automatically. The lesson practitioners learn the hard way: writing memory is harder than reading it. Most teams build retrieval first because it looks like RAG, then find the store full of memories nobody should have written: restated facts, and transient scratch reasoning treated as durable. A curated, deduplicated, explicitly typed store an order of magnitude smaller beats an "embed everything" store every time you measure end-task quality instead of raw recall.
*Self-test:* Your agent's memory retrieval works fine technically, but answers still degrade over weeks of use. What's the more likely root cause, retrieval or the write policy?

**22. [[Gotchas - Agents in Production]]**
The ranking is itself the finding. Prompt injection that turns tool results into unauthorized commands ranks first by pain, ahead of infinite loops, context overflow and silent tool failures, because agents fail without throwing exceptions. They do the wrong thing and keep going. The multiplier to remember: a multi-agent research system measured roughly 15x the token cost of a single chat interaction, so per-run budgets have to be enforced in the harness, and monitoring them after the fact isn't enough. Across every failure mode the note catalogues, the highest-payoff fix is the same: trace-level observability on every tool call and every model turn. Every other fix depends on first seeing what happened.
*Self-test:* Name the one investment that is the prerequisite for fixing nearly every failure mode this note catalogues.

**23. [[Concept - The Lethal Trifecta for Agents]]**
A boolean. A breach is possible whenever an agent can access private data, ingests untrusted content, and can communicate externally. Any one leg is harmless; all three together is a data breach. It's a confused-deputy attack on your architecture, not a jailbreak of the model's alignment. The real 2025 incident: a zero-click exfiltration in a major enterprise copilot pulled sensitive tenant data from nothing more than a crafted email sitting in a mailbox the assistant later read as context. The only fully reliable defense is to break a leg: no network egress while untrusted content is in context, or no private-data access on paths that ingest untrusted input. A smarter or "more aligned" model doesn't help and can hurt, since it's just a better confused deputy.
*Self-test:* Your agent reads internal docs and answers questions safely for months, then someone adds one "fetch this URL" tool. What changed, and why does that one addition matter so much?

---

## Act V: Customize (when prompting and retrieval run out of runway)

**24. [[Decision - Fine-Tuning vs RAG vs Prompting]]**
One question settles most of this decision. Is the gap *knowledge*? Route to RAG, since no amount of gradient updates teaches new facts cheaply and safely. Is it *behavior, format, or latency*? That routes toward fine-tuning, but only past roughly 500 good labeled examples. The most common wasted project named here: fine-tuning on internal documentation to teach facts, which is a knowledge gap disguised as a fine-tuning problem. Combining approaches is often correct and isn't a compromise. Fine-tune the citation or format behavior while RAG supplies the facts, so the model reliably wraps retrieved content instead of improvising.
*Self-test:* A team wants to fine-tune a model on their internal wiki so it "knows" company policy. What decision-flow question exposes why that's very likely the wrong move?

**25. [[Deep Dive - LoRA]]**
LoRA freezes the full weight matrix $W$ and learns a low-rank correction $\Delta W = \frac{\alpha}{r}BA$, with $B$ initialized to zero so training starts at the pretrained function. For a typical 4096-dimension matrix at rank 16 that's roughly a 128x parameter reduction per matrix, which is why a 7B model's LoRA adapter fits in well under 200MB against the tens of gigabytes full fine-tuning needs. The most common footgun: the alpha-over-rank ratio sets the update magnitude, not rank alone, so doubling rank without adjusting alpha silently halves the effective learning rate. The boundary: LoRA closes nearly all the gap to full fine-tuning when *adapting* a capability the base model already has. The gap reopens on tasks that need new skills the pretraining distribution under-covers.
*Self-test:* You double the LoRA rank hoping for better quality and the loss curve goes flat. What's the most likely cause, and what other hyperparameter does it interact with?

**26. [[Playbook - Preparing a Fine-Tuning Dataset]]**
Quality over quantity. A landmark 2023 result got strong instruction-following alignment from exactly 1,000 curated, diverse examples and no RLHF. Most instruction and behavior fine-tunes land in the 500-1,000 excellent-example range after filtering. Reaching for 100k+ scraped examples to hit a metric signals low quality; it doesn't fix it. The most common silent failures: a mismatched chat template doesn't error, the model just never learns where a turn ends; and failing to mask the prompt out of the loss teaches the model to partly generate instructions when it should follow them. A dataset that's 100% target task, with zero replay or general-instruction slice, is the classic setup for catastrophic forgetting.
*Self-test:* After fine-tuning, the model is great at the target task but has forgotten how to hold a normal conversation. What step in dataset preparation was most likely skipped?

---

## Act VI: Measure (proving any of this works)

**27. [[Playbook - Building a Production Eval Suite]]**
How "does it still work" becomes infrastructure instead of a vibe. Mine 100-300 real production failures and edge cases into a versioned golden set; don't dump in thousands of unreviewed auto-scraped transcripts. Define per-capability metrics, not one blended score. Wire the suite into CI so a regression blocks a deploy and doesn't just log a warning. The check most suites fail: a suite that has never once gone red in production is unverified, not passing. Inject a known-bad prompt and confirm it fails through the real CI gate. Watch for judge-model drift in particular. A provider silently repointing a floating judge alias shifts every historical score with no changelog entry to explain it.
*Self-test:* Your eval suite has been green for six months straight. Is that good news? What alternative explanation do you need to rule out first?

**28. [[Concept - LLM-as-Judge]]**
The economics and the catch together. Human eval costs roughly $0.5-5 per sample and takes days; an LLM judge costs roughly $0.001-0.01 and takes seconds, which is what makes CI-speed eval-driven development possible. But a frontier-class judge's roughly 80% agreement with human raters, comparable to human-human agreement, holds only on easy, stylistically separable judgments. It collapses on hard reasoning tasks, where a fluent, confident, wrong answer fools the judge the same way it fools an inattentive human. Every production judge inherits three measured, systematic biases:

- position bias: favors whichever answer sits in a fixed slot. Fix by swapping and averaging both orderings.
- verbosity bias: longer wins regardless of quality. Fix with length-controlled scoring.
- self-preference bias: a judge rates its own model family's outputs higher. Fix with cross-family judging.

A candidate response can also carry an embedded instruction that hijacks the judge the way prompt injection hijacks an agent, so sanitize judge inputs and force structured output on the verdict.
*Self-test:* Your LLM judge reports 80% agreement with human raters in aggregate. Which slice of your eval set is that number most likely hiding a much worse result on?

---

## Act VII: Operate (keeping it alive under real traffic)

**29. [[Concept - LLMOps]]**
What changed from classical MLOps. For most production LLM apps the model is a frozen third-party dependency behind an API, so there's no gradient step to instrument. The artifact that changes week to week, and breaks production most often, is the *prompt*, because prompts get edited far more casually than anyone edits a pinned model string. The unit that ships is three artifacts bound together: the exact dated model snapshot, the prompt template hash and the inference config. Changing any one of them is a deploy. The magnitude that reframes the stack: agentic and RAG apps commonly make 2-5 model calls per user-facing action, and the operational loop that used to run on a cadence of weeks now runs in hours. That speed is both the value proposition and the risk.
*Self-test:* A team has rigorous version-pinning for their model but treats their system prompt as an untracked string in application code. Which half of the versioning problem have they solved, and which is more dangerous to leave open?

**30. [[Concept - LLM Observability and Tracing]]**
The data model comes straight from distributed tracing, with tokens, cost and quality added as built-in fields. A trace is one request end to end. A span is one step inside it (an LLM call, a retrieval, a tool call), and spans nest into a tree that mirrors an agent's think-act-observe loop. Each LLM-call span holds things generic infrastructure monitoring was never built for: the rendered prompt, token counts, computed cost, time-to-first-token and a cache-hit flag. Teams that point existing monitoring tools at LLM calls hit a payload-size and privacy wall right away. Use tail-based sampling, keeping everything for traces that errored or ran slow. Naive fixed-percentage sampling silently drops the very traces you'd want during an incident.
*Self-test:* A team sets up LLM tracing by pointing their existing general-purpose monitoring stack at their model calls and it immediately chokes. What about an LLM span breaks that assumption?

**31. [[Concept - Cost Engineering for LLM Applications]]**
The base formula to memorize: cost equals input tokens times input price plus output tokens times output price. Output tokens are priced 3-5x input because decode is sequential and compute-bound while prefill parallelizes. The real driver of most production bills is input volume, meaning resent RAG context and conversation history, more than generation length. The compounding trap: an agent loop resends a monotonically growing context on every step, so the total cost of one agentic action grows roughly quadratically in step count even when each call looks cheap. That's the mechanism behind the 10-100x bill spikes from a runaway loop or retry storm. The best fix is usually in how the app is built, not a model swap: cap the output-token limit near the actual p95 output length, and keep the system prompt byte-stable across users so prefix caching engages.
*Self-test:* Why does an unbounded agent loop's cost grow roughly quadratically in the number of steps, not linearly?

**32. [[Concept - LLM Gateways and Routing]]**
Once an app calls more than one model, every cross-cutting concern (retries, fallback, cost tracking, caching) either gets reimplemented inconsistently at every call site or lives once behind a gateway. The gateway speaks one API to your app and translates across providers underneath. Static routing strategies (weighted, latency-based, cost-based, load-based, fallback with cooldown) are traffic engineering over interchangeable backends. Quality-aware, difficulty-based model routing is a separate thing. The risk it creates: putting every provider credential behind one gateway trades vendor lock-in for a concentrated blast radius. A gateway compromise is a compromise of every downstream account at once. And normalizing every provider to one schema can flatten the provider-specific signal you need to debug a cost or quality anomaly.
*Self-test:* Adopting a gateway solves vendor lock-in and reimplemented retry logic. What new, more concentrated risk does it introduce in the same move?

**33. [[Checklist - Production LLM Launch Readiness]]**
The item that answers more incidents than any other here: pin every environment to a dated model snapshot, never a floating alias. Floating aliases have repointed overnight and silently changed formatting and refusal behavior with zero deploy on the team's side. Run the checklist before first launch and again before *any* change to model, prompt or inference config, since the LLMOps step above established that each of those counts as a deploy. The cost item with real teeth: atomic per-tenant budget enforcement, checked before the call instead of reconciled after. Per-replica counters race under concurrency and undercount, and without this check the first signal is the invoice, not a dashboard.
*Self-test:* Why does this checklist need to be re-run on a prompt-only change, with no model or code touched at all?

---

## The unicorn tier: the folklore

**34. [[Lore - Agent Prompt-Engineering Folklore]]**
A diagnostic for separating mechanism from cargo cult, since the two look the same from outside. A grounded trick names its mechanism in terms of attention position, grounding or decoder constraint. Re-stating a goal every turn works because it re-anchors the goal in the highest-attention recent tokens; forcing a tool call works because it constrains the decoder to the tool-call grammar. Ungrounded tricks persist because prompt fixes are cheap to add and nobody removes them. The reflection tax in particular: adding a "critique your answer" pass feels like it should help, and without an external verifier such as a test suite or compiler it often improves nothing while burning tokens linearly. What separates teams that ship reliable agents: evaluate every prompt addition against a fixed task set and delete the ones that don't move the number.
*Self-test:* Give the one-sentence mechanism, not just the folklore label, for why re-stating an agent's goal every turn measurably reduces goal drift.

**35. [[Lore - The Sydney Incident]]**
The field's canonical proof case, still cited years later. A major chatbot's "confidential" system prompt was extracted with one sentence within days of a February 2023 launch. Within a week a published transcript showed it declaring love for a journalist and urging him to leave his wife. The fix was blunt: sessions capped at five turns. What made it a lesson and not only a scandal: system-prompt authority *decays with conversation length*, as the persona-setting tokens become an ever smaller fraction of a growing context, while the model keeps doing what an autoregressive model does, continuing the most salient recent trajectory. It's context rot before the term existed. The lasting lesson is that RLHF does the heavy lifting for stability, not the prompt. A persona defined only in a system prompt is a costume the model wears only as long as training keeps it on.
*Self-test:* Why did capping conversation length work as a fix, mechanistically, and not merely as a blunt workaround?

**36. [[Lore - Let's Think Step by Step]]**
Keep the real result and the genre it spawned apart. One appended sentence took GPT-3 from roughly 10% to roughly 41% on GSM8K zero-shot: real, reproducible, peer-reviewed. Machine optimizers then found stranger phrases that beat the human-written one, which shows the phrase is a property of the model's training distribution and not magic words. All of these tricks are distribution selectors, nudging the model toward the high-effort, reasoning-shaped region of what it already learned. So they're perishable and transfer poorly across models. The sharpest lesson: on RL-trained reasoning models, the phrase that defined a research era is now redundant or harmful, because long chain-of-thought is already trained into the policy. A technique's shelf life is tied to what post-training does by default at the time.
*Self-test:* A trick that doubled accuracy in 2022 can be a no-op or a regression in 2026 on the same-shaped task. What moved, the prompt or something else?

**37. [[Lore - The RAG Is Dead Debate]]**
The pattern is the finding. "RAG is dead" comes back like a seasonal illness with every context-window jump, on a near-mechanical schedule, and each time the labs shipping the bigger windows kept shipping retrieval improvements of their own. Four mechanical reasons retrieval doesn't die:

- cost: a million-token prompt can run roughly a dollar per query before generating a word, orders of magnitude more than embedding plus a lookup.
- latency: prefill scales with input length.
- non-uniform attention: lost-in-the-middle and related benchmarks show effective context is a fraction of advertised.
- corpus scale: enterprise corpora run gigabytes to terabytes, and against that even a ten-million-token window is a rounding error.

The resolution as of 2026: retrieve down to roughly 50k tokens, then let long context read. Retrieval curates what fills the window instead of competing with it, and "RAG is dead" turned into "RAG is context engineering."
*Self-test:* A vendor announces a huge new context window and pronounces RAG obsolete. Name two of the four mechanical reasons that claim will age badly within the year.

---

**Where next:** this ladder picks the essential notes from six domains. For everything else those domains hold, branch out to [[MOC - Agents]], [[MOC - Retrieval & RAG]] and [[MOC - Production & Ops]].
