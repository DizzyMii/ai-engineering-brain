---
tags: [concept, domain/prompting-context, level/advanced]
aliases: [exemplar selection, demonstration ordering]
summary: "Which examples you pick and what order you use can swing few-shot accuracy from near-random to near-SOTA, with no universal best order."
---
> **One-paragraph hook:** Two calls to the same model, on the same task, with the same exemplars — differing only in the order those exemplars appear — can swing accuracy from near-random guessing to near state-of-the-art. [[Concept - In-Context Learning]] tells you *that* demonstrations steer behavior; it says nothing about *which* demonstrations or in *what* order, and that gap turns out to matter as much as whether exemplars are present at all. Most of this sensitivity is invisible until someone deliberately goes looking for it.

## The mechanism

Every exemplar in a few-shot prompt is just more conditioning tokens; the model attends over the whole block when producing the next token, and how strongly it weighs any part of that block is shaped by position and surface form, not by logical role. Lu et al. (2022, "Fantastically Ordered Prompts and Where to Find Them") demonstrate this directly: holding the same k exemplars fixed and only permuting their order swings accuracy on the same task and model from near-random to near-SOTA. There is no universal best order — the optimal permutation is task- and model-specific — but a good one can be found cheaply: score each candidate ordering on a small unlabeled probing set by the entropy of the model's predicted-label distribution. Low-entropy (confident) orderings correlate with high accuracy, so you can select a strong order without spending any held-out labels on it.

A second, separate source of distortion is what the model brings to the exemplar block regardless of its content. Zhao et al. (2021, "Calibrate Before Use") identify three systematic biases: majority-label bias (the model over-predicts whichever label appears most among the shots), recency bias (the last exemplar's label is disproportionately likely to be repeated), and common-token bias (labels that are common English words get an unwarranted prior boost). Their fix, contextual calibration, is nearly free: feed the model a content-free input — a placeholder like `"N/A"` or an empty string — in place of the real query, keeping the same exemplars, and read off the resulting label distribution $p_{cf}(y)$. That distribution is pure bias, since there is no real content to condition on. Real predictions are then corrected by dividing it out:

$$\hat p(y \mid x) \;\propto\; \frac{p_\theta(y \mid x)}{p_{cf}(y)}$$

renormalized over the label set. One extra forward pass recovers accuracy points that adding more exemplars would not fix, because the failure is an uncorrected prior, not insufficient information.

## In practice

Selection strategy beats random sampling. Liu et al. (2021, "What Makes Good In-Context Examples for GPT-3?") show that retrieving exemplars via k-nearest-neighbor search over an embedding space ([[Concept - Embedding Models]]) — pick the k labeled examples most similar to the live query, per call — consistently outperforms a fixed random or hand-picked set, because the demonstrations are locally relevant to *this* input rather than globally representative of the task. For multi-step reasoning tasks, pure similarity retrieval can backfire: near-duplicate exemplars encourage shallow pattern matching instead of generalizing the underlying strategy, so diversity- or coverage-based sampling tends to help more there. This is also where the *quality of the reasoning inside each exemplar* matters, not just its final label ([[Concept - Chain-of-Thought and Why It Works]]) — a demonstration whose reasoning is subtly wrong can propagate that error into the live completion even when its stated answer happens to be correct.

Two more constraints are load-bearing. First, keep the label distribution balanced across shots and use identical delimiters, field names, and formatting between the exemplar block and the live query — mismatched formatting between shots and query is a silent accuracy killer that produces no error and shows up nowhere in the API response ([[Gotchas - Prompt Formatting and Tokenization]]). Second, exemplars are not free: they are recurring input tokens on every call, so a six-shot chain-of-thought block running 200 tokens per example adds 1,200 tokens to every single request ([[Concept - Cost Engineering for LLM Applications]]). Because a fixed exemplar set is identical across calls for a given prompt version, it belongs at the front of the prompt, in the static prefix, where it can be paid for once instead of on every call ([[Concept - Prompt Caching]]).

## Failure modes

- **Order swaps unpredictably.** The same exemplar set, reordered, can flip a task from working to broken with no error or warning. Detection: permutation-test a handful of candidate orderings against a small probe set before locking a prompt version.
- **Majority/recency bias silently distorts predictions.** A skewed shot distribution (e.g. four positive, one negative) biases the model toward the majority label even on inputs that should be negative. Detection: run the content-free calibration probe and check $p_{cf}(y)$ for skew, rather than trusting raw accuracy on a small eval.
- **Format drift between shots and query.** A trailing colon, inconsistent casing, or quotes present around one field and absent from another between the exemplar block and the live input teaches the model the wrong pattern to imitate.
- **Over-similar exemplars induce shallow copying.** kNN-retrieved exemplars that are near-duplicates of the query cause the model to echo surface features instead of applying task logic — accuracy looks fine on a retrieval-similar eval set and collapses on a structurally different one.

## The non-obvious

The uncomfortable implication of Lu et al.'s result is that a team that "discovered a great prompt" through trial and error was often permuting order as much as content, without ever realizing it — two prompt versions with identical exemplars can perform wildly differently purely because someone pasted them in a different sequence. If a prompt eval harness never varies exemplar order as part of its search space, real accuracy is being left on the table, and worse, there is no way to tell whether a "better prompt" win came from content or from a lucky ordering.

Calibration is the other underused lever. Teams chase accuracy by adding more or better exemplars when a single extra forward pass against a content-free probe would remove a chunk of the error for free — it is cheaper than nearly any other accuracy intervention available, and most teams never run it because it isn't the intuitive first thing to try.

## Connections
- [[Concept - In-Context Learning]] — the mechanism this note assumes: why exemplars steer behavior at all, before asking which ones and in what order.
- [[Concept - Chain-of-Thought and Why It Works]] — reasoning exemplars add a second axis of sensitivity: the quality of the demonstrated reasoning, not just the final label.
- [[Concept - Embedding Models]] — the retrieval substrate that makes kNN exemplar selection possible.
- [[Concept - Prompt Caching]] — a static, well-chosen exemplar block is exactly the content worth hoisting into the cached prefix.
- [[Concept - Cost Engineering for LLM Applications]] — exemplars are recurring input tokens on every call, not a one-time cost.
- [[Gotchas - Prompt Formatting and Tokenization]] — the format-consistency failure mode that silently undermines careful example selection.
- [[Concept - Prompt Formatting and Sensitivity]] — the broader research showing models are surprisingly fragile to superficial formatting, of which shot order and delimiter choice are special cases.
- [[Concept - Prompt Engineering]] — the parent discipline this note is one advanced lever within.

## Sources
- Lu et al. (2022) — "Fantastically Ordered Prompts and Where to Find Them." Establishes permutation sensitivity and an entropy-based method for selecting a good order without labeled validation data.
- Zhao et al. (2021) — "Calibrate Before Use: Improving Few-Shot Performance of Language Models." Identifies majority-label, recency, and common-token bias and introduces contextual calibration.
- Liu et al. (2021) — "What Makes Good In-Context Examples for GPT-3?" Establishes kNN retrieval of semantically similar exemplars as a strong selection strategy over random sampling.
