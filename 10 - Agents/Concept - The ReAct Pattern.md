---
tags: [concept, domain/agents, level/core]
aliases: [ReAct, Reasoning and Acting]
summary: "Interleaving Thought/Action/Observation in one generation stream so reasoning stays grounded in real tool feedback instead of hallucinating."
---
> **One-paragraph hook:** Ask an LLM to reason its way to an answer and it will confidently make facts up. Ask it to call tools with no reasoning and it flails without a plan. ReAct fixes both by making the model alternate: think a little, act a little, read what actually happened, repeat. That one interleaving is the ancestor of essentially every agent loop running in production today.

## The mechanism

ReAct (Yao et al. 2022, *ReAct: Synergizing Reasoning and Acting in Language Models*) has the model generate one stream of text broken into repeating triples:

```
Thought: <reasoning about what to do next, given everything so far>
Action: <a tool call — search[query], lookup[term], calculator[expr], ...>
Observation: <the real result returned by executing that action>
```

The loop runs until the model emits a final answer instead of another action. It works because the two failure modes it targets complement each other. Chain-of-thought-only prompting (see [[Concept - Chain-of-Thought and Why It Works]]) lets the model reason step by step, but every "fact" it uses along the way is generated, not retrieved. It hallucinates plausible intermediate facts and the chain drifts further from ground truth with each step. Act-only prompting (no Thought lines, just Action → Observation) grounds every step in a real observation, but the model has no scratchpad for *why* it's doing what it's doing, so it loses the plot on multi-step tasks.

With both interleaved, the Thought breaks down the task and tracks progress toward the goal, and the Action grounds the next step in something real instead of something misremembered. Each Observation feeds the *next* Thought, so grounding compounds instead of decaying.

## In practice

The paper's main contribution is its empirical contrast. On HotpotQA and FEVER (multi-hop QA and fact verification), ReAct beat CoT-only on hallucination rate because every intermediate claim could be checked against a real Wikipedia lookup. On ALFWorld and WebShop (interactive environments: a simulated household and a shopping site), ReAct beat act-only because the Thought traces let the model plan around a bad observation instead of reacting to it one step late.

One part of the original implementation is now a museum piece. It used a few hand-written few-shot exemplars with `Thought:`/`Action:`/`Observation:` as literal strings, and a text parser scraped the Action line to decide what to call. That parser was brittle; a stray colon or a slightly reformatted action string broke the loop. Modern practice keeps the *interleaving* and drops the *text parsing*. The Thought is still free text (often the model's native reasoning/thinking output), but the Action comes out as a native structured tool call via [[Concept - Tool Use and Function Calling]], so the harness doesn't have to regex it out. [[Deep Dive - The Agent Loop]] traces the evolution from text-parsed ReAct (2022) to native function calling, parallel tool calls, and interleaved extended thinking with tool use. Each step removed one class of parsing failure. [[Snippet - A Minimal ReAct Loop]] is the ~50-line runnable version of the modern form.

## Failure modes

- **Repeating the same failing action.** The Thought argues *why* the action should work instead of diagnosing why the last identical attempt didn't. Reasoning turns into post-hoc justification. Detection: log consecutive identical tool calls; more than 2-3 repeats is a strong loop signal.
- **Oscillating between two states.** The agent alternates between two actions that undo each other (open then close, search A then search B then back to A) and makes no net progress. Detection: hash the (action, observation) pairs and look for cycles as well as exact repeats.
- **Thoughts that entrench instead of diagnose.** The Thought comes from the same model that just took the wrong action. It's cheap and useful when it honestly diagnoses an observation, and just as able to argue that a bad path is still correct. This is the self-correction ceiling from [[Concept - Reflection and Self-Correction]]: reasoning about your own error without an external signal doesn't reliably fix it.

## The non-obvious

Thought tokens aren't free reasoning capacity. The property that makes ReAct work, a place for the model to reason about what to do next, also lets a stuck agent talk itself into staying stuck, because the model that made the bad plan is the same one judging whether the plan still makes sense. So production loop designs pair ReAct's interleaving with an external check when one exists (a test suite, a compiler, a retrieved fact) instead of trusting the Thought to self-correct. [[Concept - Reflection and Self-Correction]] carries the idea across episodes: Reflexion adds a verbal-feedback memory the agent writes after a failed episode and reads before the next try, pushing ReAct's within-episode grounding out to learning between episodes.

## Connections

- [[Deep Dive - The Agent Loop]] — ReAct is the specific reasoning-interleaving technique that the general observe-think-act loop scaffolding is built around.
- [[Concept - Tool Use and Function Calling]] — modern ReAct implementations emit the Action as a native structured tool call instead of parsed text.
- [[Concept - Chain-of-Thought and Why It Works]] — ReAct is CoT plus grounding; understanding why bare CoT hallucinates explains why the Observation step matters.
- [[Concept - Reflection and Self-Correction]] — Reflexion extends ReAct's within-episode Thought/Observation grounding into an inter-episode memory of what failed and why.
- [[Concept - Search and Backtracking in Agents]] — ReAct is a greedy, single-path version of the more expensive deliberate-search agents like Tree of Thoughts and LATS.
- [[Snippet - A Minimal ReAct Loop]] — the runnable ~50-line implementation of the modern (native-tool-call) form of this pattern.
- [[Concept - Task Decomposition and Planning]] — ReAct's interleaved regime is one pole of the plan-then-execute vs. interleaved-decision spectrum that note covers.
- [[Concept - What Is an LLM Agent]] — ReAct's Thought/Action/Observation loop is the concrete mechanism behind the generic "tool-use loop" rung of the autonomy ladder.
- [[Concept - Constrained Decoding]] — native Action emission relies on the same grammar-guided decoding that makes any structured tool call schema-valid.

## Sources
- Yao et al. (2022) — *ReAct: Synergizing Reasoning and Acting in Language Models.* Introduces the Thought/Action/Observation interleaving and the HotpotQA/FEVER/ALFWorld/WebShop comparisons against CoT-only and act-only baselines.
- Shinn et al. (2023) — *Reflexion: Language Agents with Verbal Reinforcement Learning.* Extends ReAct with an inter-episode self-reflection memory.
