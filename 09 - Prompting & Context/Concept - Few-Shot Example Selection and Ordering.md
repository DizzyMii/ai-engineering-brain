---
tags: [concept, domain/prompting-context, level/advanced]
aliases: [exemplar selection, demonstration ordering]
summary: "Which examples you pick and what order you use can swing few-shot accuracy from near-random to near-SOTA, with no universal best order."
---
> **One-paragraph hook:** Two calls to the same model, same task, same exemplars, with only the order of the exemplars changed, can land anywhere from near-random guessing to near state-of-the-art. [[Concept - In-Context Learning]] tells you *that* demonstrations steer behavior. It says nothing about *which* ones or in *what* order, and that turns out to matter as much as whether you include exemplars at all. You won't see most of this sensitivity unless you go looking for it.

## The mechanism

Each exemplar in a few-shot prompt is just more conditioning tokens. The model attends over the whole block when producing the next token, and how much weight any part gets depends on position and surface form, not logical role. Lu et al. (2022, "Fantastically Ordered Prompts and Where to Find Them") show this directly: keep the same k exemplars, permute only their order, and accuracy on the same task and model ranges from near-random to near-SOTA. No order is best everywhere; the optimal permutation depends on task and model. A good one is cheap to find, though. Score each candidate ordering on a small unlabeled probe set by the entropy of the model's predicted-label distribution. Low-entropy (confident) orderings correlate with high accuracy, so you can pick a strong order without spending any held-out labels.

A separate distortion comes from what the model brings to the exemplar block whatever its content. Zhao et al. (2021, "Calibrate Before Use") identify three systematic biases. Majority-label bias: the model over-predicts whichever label is most common among the shots. Recency bias: the last exemplar's label is disproportionately likely to be repeated. Common-token bias: labels that are common English words get an unearned prior boost. Their fix, contextual calibration, costs almost nothing. Keep the same exemplars, swap the real query for a content-free input (a placeholder like `"N/A"` or an empty string), and read off the label distribution $p_{cf}(y)$. With no real content to condition on, that distribution is pure bias. Real predictions are corrected by dividing it out:

$$\hat p(y \mid x) \;\propto\; \frac{p_\theta(y \mid x)}{p_{cf}(y)}$$

renormalized over the label set. One extra forward pass recovers accuracy that more exemplars wouldn't, because the problem is an uncorrected prior, not missing information.

## In practice

Choosing exemplars deliberately beats random sampling. Liu et al. (2021, "What Makes Good In-Context Examples for GPT-3?") retrieve exemplars by k-nearest-neighbor search in an embedding space ([[Concept - Embedding Models]]), picking the k labeled examples closest to the live query on each call. That consistently beats a fixed random or hand-picked set, since the demonstrations are relevant to *this* input instead of representative of the task in general. On multi-step reasoning, pure similarity retrieval can backfire. Near-duplicate exemplars encourage shallow pattern matching over learning the underlying strategy, so diversity- or coverage-based sampling tends to help more. The *quality of the reasoning inside each exemplar* also matters, beyond its final label ([[Concept - Chain-of-Thought and Why It Works]]). A demonstration with subtly wrong reasoning can pass that error into the live completion even when its stated answer is right.

Two more constraints matter. First, balance the label distribution across shots, and use the same delimiters, field names and formatting in the exemplar block and the live query. A formatting mismatch between shots and query kills accuracy silently: no error, nothing in the API response ([[Gotchas - Prompt Formatting and Tokenization]]). Second, exemplars cost tokens on every call. A six-shot chain-of-thought block at 200 tokens per example adds 1,200 tokens to every request ([[Concept - Cost Engineering for LLM Applications]]). A fixed exemplar set is identical across calls for a given prompt version, so put it at the front of the prompt, in the static prefix, where you pay for it once instead of per call ([[Concept - Prompt Caching]]).

## Failure modes

- **Reordering breaks things unpredictably.** The same exemplars in a different order can flip a task from working to broken with no error or warning. Detection: permutation-test a handful of candidate orderings on a small probe set before locking a prompt version.
- **Majority/recency bias skews predictions.** A lopsided shot distribution (e.g. four positive, one negative) pushes the model toward the majority label even on inputs that should be negative. Detection: run the content-free calibration probe and check $p_{cf}(y)$ for skew; raw accuracy on a small eval won't show it.
- **Format drift between shots and query.** A trailing colon, inconsistent casing, or quotes around a field in the exemplars but not in the live input teaches the model the wrong pattern to copy.
- **Over-similar exemplars cause shallow copying.** kNN-retrieved exemplars that nearly duplicate the query make the model echo surface features instead of applying the task logic. Accuracy looks fine on an eval set similar to the retrieval pool and collapses on a structurally different one.

## The non-obvious

Lu et al.'s result has an uncomfortable implication. A team that "found a great prompt" by trial and error was often permuting order as much as content without knowing it. Two prompt versions with identical exemplars can perform very differently just because someone pasted them in a different sequence. If your prompt eval harness never varies exemplar order, you're leaving accuracy on the table, and worse, you can't tell whether a "better prompt" win came from content or from a lucky ordering.

Calibration is the other underused lever. Teams chase accuracy by adding more or better exemplars when one extra forward pass on a content-free probe would remove a chunk of the error for free. It's cheaper than almost any other accuracy fix, and most teams never run it because it isn't the obvious first thing to try.

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
