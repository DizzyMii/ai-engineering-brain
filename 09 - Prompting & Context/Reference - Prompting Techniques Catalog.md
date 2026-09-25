---
tags: [reference, domain/prompting-context, level/advanced]
aliases: [prompt technique cheat sheet, prompting techniques taxonomy]
summary: "Sourced lookup table of single-caller prompting techniques: what each does, when it helps, extra cost, and evidence status as of 2026."
---
# Reference - Prompting Techniques Catalog

Main source: Schulhoff et al. (2024) "The Prompt Report", a systematic survey and taxonomy of 58 text-based prompting techniques. This table covers only techniques a *single caller* controls entirely, within one prompt or a small fixed number of calls. Multi-step search and tool loops (ReAct, Tree-of-Thoughts, Reflexion) are agent architectures. They belong to [[Deep Dive - The Agent Loop]] in domain 10 and get a pointer here, not a row.

| Technique | What it does | When it helps | Extra cost (calls × tokens) | Source | Status (as of 2026) |
|---|---|---|---|---|---|
| Zero-shot | Direct instruction, no examples | Well-specified tasks on any instruction-tuned model; the default starting point | 1× calls, no extra tokens | — (baseline) | Proven; still the default first attempt |
| Few-shot | k labeled demonstrations in the prompt ([[Concept - In-Context Learning]]) | Format-transfer and classification tasks where the desired shape is easier to show than describe | 1× calls, + demonstration tokens (recurring every call) | Brown et al. (2020) | Proven, but often superseded by schema/tool-calling for pure format control; can *hurt* on reasoning models |
| Zero-shot CoT | Appends "let's think step by step," no exemplars ([[Concept - Chain-of-Thought and Why It Works]]) | Multi-step arithmetic/logic on a non-reasoning instruct model | 1× calls, + output tokens for the reasoning trace | Kojima et al. (2022) | Proven (GSM8K ~18%→~41% on GPT-3); redundant or harmful on reasoning models |
| Few-shot CoT | Exemplars that include worked reasoning as well as final answers | Same as zero-shot CoT, when a worked example clarifies the reasoning *format* | 1× calls, + exemplar tokens + output tokens | Wei et al. (2022) | Proven; emerges above ~60-100B params, can hurt below that threshold |
| Self-consistency | Sample k independent CoT paths at nonzero temperature, majority-vote the final answer | Maximum accuracy on math/logic when k× compute budget is available | k× calls | Wang et al. (2022) | Proven, +10-18 points on GSM8K-class tasks; costly, increasingly displaced by reasoning models |
| Least-to-most | Decompose into ordered subproblems, solve sequentially, each conditioned on prior answers | Compositional generalization — problems that get easier once broken into stages | 1 call but multi-turn (n subproblem turns) | Zhou et al. (2022) | Proven on compositional benchmarks; niche outside that class |
| Plan-and-solve | Draft an explicit plan, then execute it, in one pass | Reduces the "missing step" error that vanilla CoT alone leaves | 1× calls, + output tokens | Wang et al. (2023) | Proven modest improvement over zero-shot CoT |
| Step-back prompting | Ask a higher-abstraction question first, then answer the specific one | Knowledge-intensive/reasoning tasks where a general principle makes the specific case easier | 2× calls (abstraction pass + answer pass) | Zheng et al. (2023) | Proven on the benchmarks tested; less broadly validated |
| Self-refine | Generate, critique own output, revise, iterate | Polishing tasks (writing, code) where a critique pass catches errors the first pass missed | n× calls (iterative) | Madaan et al. (2023) | Proven gains, but self-critique is unreliable at catching the model's own factual errors; diminishing returns past 1-2 iterations |
| Generated knowledge | Generate relevant facts first, then answer conditioned on them | Commonsense/knowledge-intensive QA without a real retrieval system available | 2× calls (generate, then answer) | Liu et al. (2021) | Proven pre-retrieval-era technique; largely superseded when a real knowledge base and retrieval pipeline exist |
| Self-ask | Model explicitly poses and answers its own sub-questions before the final answer | Multi-hop QA | 1 call, + output tokens | Press et al. (2022) | Proven on multi-hop QA; commonly paired with search as an agent pattern, out of scope here |
| Emotion/role priming ("you are an expert," urgency framing) | Persona/urgency framing with no explicit reasoning scaffold | Marginal, model- and version-dependent | 1× calls, negligible extra tokens | Li et al. (2023), "EmotionPrompt" | Folklore-adjacent; small and inconsistent effects, largely faded on frontier instruction-tuned and reasoning models. See [[Lore - Let's Think Step by Step]] for the wider folklore taxonomy |

**On cost:** self-consistency and self-refine multiply calls (k-times or iterative). When a [[Concept - Prompting Reasoning Models|reasoning model]] is available, one call to it is frequently cheaper and more accurate than k non-reasoning calls trying to approximate it. In 2026-era reasoning models, much of what the CoT and self-consistency rows buy through explicit multi-call prompting is trained straight into the policy via [[Concept - GRPO and RL with Verifiable Rewards]]. Before reaching for the heavier rows, check that you aren't paying prompt-engineering cost to reproduce something the model already does natively.

**Reading the table:** "proven" means the cited paper's benchmark result was reproduced elsewhere. It doesn't guarantee the effect on your task and model. Measure anything flagged folklore-adjacent on your own eval set before trusting it in production; never assume it transfers.

## Connections
- [[Concept - Chain-of-Thought and Why It Works]] — the mechanism behind the CoT and self-consistency rows; read it before deciding those rows are worth their cost.
- [[Concept - In-Context Learning]] — the mechanism behind the few-shot row and why it can misbehave (label randomization, format sensitivity).
- [[Deep Dive - The Agent Loop]] — where ReAct, Tree-of-Thoughts, and Reflexion actually live; this catalog stops at single-caller techniques deliberately.
- [[Concept - Prompting Reasoning Models]] — why several rows in this table (few-shot, explicit CoT) actively hurt once you're calling a reasoning model instead of a plain instruct model.
- [[Concept - GRPO and RL with Verifiable Rewards]] — the RL training method that moved much of what CoT/self-consistency buy from prompt-time into the trained policy itself.
- [[Lore - Let's Think Step by Step]] — the fuller history and evidence status of the trigger-phrase and emotion-priming folklore in the last table row.

## Sources
- Schulhoff, S. et al. (2024) — "The Prompt Report: A Systematic Survey of Prompting Techniques" — the taxonomy and survey this table's spine is drawn from.
- Individual technique papers cited per row above (Brown 2020, Kojima 2022, Wei 2022, Wang 2022, Zhou 2022, Wang 2023, Zheng 2023, Madaan 2023, Liu 2021, Press 2022, Li 2023).
