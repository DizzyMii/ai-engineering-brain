---
tags: [lore, domain/agents, level/unicorn]
aliases: [AutoGPT, Auto-GPT, BabyAGI, ChaosGPT]
summary: "The spring-2023 AutoGPT/BabyAGI mania and why the first autonomous-agent wave failed: per-step reliability too low for the horizon."
---

# Lore - The AutoGPT Explosion

> **The story:** weeks after GPT-4 shipped, a wrapper that let it call itself in a loop and pursue a goal unsupervised became one of the fastest-growing repositories in GitHub history — and then, mostly, it didn't work. The gap between "fully autonomous AI agent" and what the 2023 models could actually sustain is the founding lesson of the entire agent field.

## What happened

GPT-4 was released on **March 14, 2023**. Sixteen days later, on **March 30**, a developer working under the handle Significant Gravitas (Toran Bruce Richards) published **Auto-GPT**: a Python script that wrapped GPT-4 in a loop, gave it a goal in natural language, and let it plan, call tools (web search, file read/write, code execution), store notes in a vector database, and decide its own next action — with no human in the loop. Days later, on **April 3**, Yohei Nakajima released **BabyAGI**, a ~140-line task-management agent that generated new subtasks from completed ones and re-prioritized a task list. Both were, structurally, the [[Deep Dive - The Agent Loop|agent loop]] before anyone had standardized the term.

The reaction was a mania. Auto-GPT rocketed past 100k+ GitHub stars faster than almost any project before it — outpacing the star-growth of long-established frameworks in a matter of weeks — and dominated tech Twitter for a month. The framing did the marketing: this was supposedly the [[Concept - What Is an LLM Agent|autonomous agent]], AGI-in-a-loop, a system you could point at "grow my business" and walk away from. A stunt account called **ChaosGPT** — Auto-GPT prompted to "destroy humanity" — went viral and poured accelerant on the hype, turning an engineering curiosity into a culture-war artifact. The lineage of what these agents were actually wrapping (GPT-4, and soon the leaked LLaMA weights that spawned open clones) is in [[Reference - Model Genealogy]].

Then people ran them. And the agents got stuck. They fell into **infinite loops**, repeating the same failing action while narrating confident progress. They **hallucinated task completion**, declaring a goal achieved that they had not touched. They lost the thread on anything requiring more than a handful of steps. Their "memory" — dump every thought into a vector store, embed the goal, retrieve the nearest neighbors — surfaced low-signal, off-topic fragments as often as useful ones, because embedding-and-retrieving everything is not a [[Concept - Agent Memory Systems|memory policy]], it is a landfill. And because every loop iteration was a real GPT-4 API call, a stuck agent **burned real money** — people posted screenshots of $10, $50, dollar-a-minute runs that produced nothing. Within a couple of months the star curve flattened and the discourse turned from "AGI is here" to "why doesn't this work?"

## The lesson

The failure was not a bug in the scaffolding. It was mechanical, and it is the founding result of the field: **autonomy needs a per-step reliability the 2023 base models did not have.** Model the run as $n$ steps each succeeding independently with probability $p$; the whole task succeeds with roughly $p^n$ — the compounding covered in full in [[Concept - Long-Horizon Agency and Error Compounding]]. With GPT-4's early-2023 per-step reliability on open-ended tool use — generously, $p \approx 0.9$ — a 50-step task lands at $0.9^{50} \approx 0.005$. Half a percent. Users were casually asking for tasks with dozens of steps; the math guaranteed they would fail, and no amount of prompt cleverness in the harness changes $p$. **Scaffolding cannot rescue a model whose step-error is too high** — the loop faithfully executes the model's mistakes.

Two corollaries stuck. First, **memory needs a write and retrieval policy**, not an embedding dump: what to store, what to deduplicate, what to discard, how to reconcile contradictions — the naive "vectorize everything" approach was actively harmful because it drowned signal in noise. Second, **the demo-to-reality gap on agents is enormous**, a pattern that would repeat a year later almost exactly with the Devin launch.

But the most important part of the lesson is the vindication. The architecture wasn't wrong — it was *early*. The same observe-think-act loop, pointed at 2025–26 models, works far better, because per-step $p$ rose and the models learned to notice and recover from being off-track, breaking the naive $p^n$ decay. That is precisely the [[Concept - Trained vs Prompted Agents|trained-vs-prompted]] story: AutoGPT tried to scaffold agentic behavior into a model that didn't have it in its weights; two years of training put it there. AutoGPT was a bet placed on capability that hadn't arrived yet — and it seeded the entire agent-framework wave that was waiting for it to. (The one cost that never went away is the token bill; a modern agent stuck in a loop still burns money, just faster — which is why per-run [[Concept - Cost Engineering for LLM Applications|cost budgets]] are table stakes.)

## Evidence status

- **Verified:** the projects, authors, and dates (Auto-GPT / Toran Bruce Richards / March 30, 2023; BabyAGI / Yohei Nakajima / April 3, 2023), the ChaosGPT stunt, and the extraordinary star-growth are all public in GitHub history, the repos' own READMEs, and contemporaneous coverage.
- **Well-documented and reproducible:** the failure modes — infinite loops, hallucinated completion, poor vector-dump recall, runaway API cost — were reported across thousands of user issues and blog posts, and reproduce trivially if you run the period code on a period-capable model.
- **Interpretation, well-supported:** the $p^n$ framing is the field's now-standard explanation and fits the evidence cleanly, but the specific per-step $p$ for 2023 GPT-4 was never measured rigorously on these tasks — treat the $0.9$ in the worked example as illustrative, not a benchmarked constant.

## Connections
- [[Concept - Long-Horizon Agency and Error Compounding]] — the $p^n$ mechanism this whole episode is the canonical demonstration of.
- [[Deep Dive - The Agent Loop]] — AutoGPT and BabyAGI were the observe-think-act loop before it had a standard name or a stop-condition design.
- [[Concept - Agent Memory Systems]] — the "embed everything into a vector store" anti-pattern that taught the field memory needs a real write/retrieval policy.
- [[Concept - What Is an LLM Agent]] — AutoGPT is the historical archetype that the definition of an autonomous agent is written against.
- [[Concept - Trained vs Prompted Agents]] — the partial vindication: the architecture works on 2025–26 models because per-step reliability was trained in, not scaffolded on.
- [[Reference - Model Genealogy]] — the GPT-4 and leaked-LLaMA lineage these first agents and their clones were built on.
- [[Concept - Cost Engineering for LLM Applications]] — the runaway-API-bill failure mode, the one cost that survived into the modern agent era.
