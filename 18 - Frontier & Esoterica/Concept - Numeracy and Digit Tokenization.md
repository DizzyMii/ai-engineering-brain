---
tags: [concept, domain/esoterica, level/unicorn]
aliases: [digit tokenization, numeracy, number tokenization, arithmetic tokenization, 9.11 vs 9.9]
summary: "How number tokenization sabotages arithmetic: non-compositional digit merges, the 9.11>9.9 bug, and the lab folklore fixes."
---
> **One-paragraph hook:** Ask a frontier model whether 9.11 or 9.9 is larger and a shocking fraction say 9.11. It looks like a reasoning failure, but it's a **tokenization** failure leaking up into what appears to be arithmetic. How a tokenizer chops numbers decides whether the model can even *see* the digit structure it needs to add, compare or count, and for arithmetic-heavy workloads the tokenizer's digit handling can matter more than parameter count. This note collects the folklore: why byte-pair encoding mangles numbers, what the labs did about it, and the failures that look like reasoning bugs but come from a merge table.

## The mechanism
Byte-level [[Concept - Byte-Pair Encoding]] builds its vocabulary by merging the most *frequent* adjacent substrings in the corpus. It has no idea digits form a positional, compositional system; frequency decides the merges. So `2017` (a common year) becomes one token, `2018` might be `201` + `8`, and `31415` might be `31` + `415` or `314` + `15`, depending only on which substrings the corpus made frequent. For numeracy that's brutal:
- **The same digit gets inconsistent, non-compositional representations.** The `7` in `7`, in `2017` and in `700000` may sit inside three different token ids, so the model can't reuse one "what a 7 in the units place does" circuit.
- **Carry and borrow structure disappears.** Addition means aligning digits by place value and propagating carries. If `456` and `789` are each one opaque token, there's no per-digit column for a carry to travel along, and the model has to memorize sums of token pairs instead of computing them.

The mechanism literature shows the same representation problem from inside. Wallace et al. 2019 ("Do NLP Models Know Numbers? Probing Numeracy in Embeddings") found that token/word [[Concept - Embeddings as Learned Representations|embeddings]] *do* capture rough magnitude (a probe can recover a number's approximate value) but the recovered values **extrapolate poorly beyond the training range**. Magnitude is encoded, just not in a form that composes or generalizes. When models do compute, they often add using **Fourier/trigonometric features on digit embeddings**, the mechanism reverse-engineered in [[Concept - Grokking]]'s modular-arithmetic circuit (Nanda et al. 2023). More recent work finds LLMs represent numbers on a helix and add via trig identities (Kantamneni & Tegmark 2024; *folklore-adjacent but real*, a specific, testable mechanistic claim). The model builds a value-aware internal geometry *despite* the tokenizer. The tokenizer's job is to not sabotage it.

## In practice
The labs settled on a few fixes, all [[Concept - Tokenizer Training]] decisions made before any weights exist, each aimed at the merge-table problem:
- **Single-digit tokenization.** PaLM and the LLaMA family tokenize each digit `0`–`9` separately, so *every* number is a compositional digit sequence and the per-place-value circuit gets reused. Blunt and reliable.
- **Fixed-size digit chunking.** Llama 3 groups digits into three-digit chunks; GPT-4's `cl100k_base` / `o200k` similarly reserve tokens for `000`–`999` and split longer numbers into groups of up to three digits. Chunking shortens sequences (fewer tokens per number) but brings back some non-compositionality at chunk boundaries.
- **Right-to-left grouping.** Split from the *units* end so the ones digit always lands at a fixed position relative to a chunk boundary. Place values then line up across numbers of different lengths, and **right-to-left grouping measurably improves addition accuracy** with no architecture change. (Some pipelines literally reverse the number before tokenizing for this reason.)

Past tokenization, **value-aware encodings** inject magnitude directly:
- **xVal** (Golkar et al. 2023) uses a single `[NUM]` token whose embedding is *scaled by the number's value*. That gives a continuous inductive bias, excellent for scientific and tabular data, with limited dynamic range as the cost.
- **Abacus embeddings** (McLeish et al. 2024, "Transformers Can Do Arithmetic with the Right Embeddings") add per-digit positional hints for each digit's place within its number. The result is dramatic **length generalization**: trained on addition of up to 20-digit numbers, the model handles ~100-digit addition, which vanilla positional schemes can't.

The operating rule: for arithmetic-heavy, code or finance workloads, **audit the tokenizer's digit handling before blaming the model**, and always test *off-distribution digit lengths*. [[Reference - Architecture Numerology]] shows where digit and vocab conventions sit among the other magic constants. Pair numeric prompts with [[Concept - Chain-of-Thought and Why It Works]] so the model can write out per-digit steps it can't do in one forward pass.

## Failure modes
- **`9.11 > 9.9`.** The canonical demo, with two causes working together. `9.11` and `9.9` tokenize differently (the fractional parts become different tokens with no shared place-value alignment). And the training data is full of contexts where "9.11" legitimately comes *after* "9.9": software versions, dates, Bible verses (chapter.verse), book sections. The model has learned an ordering in which 9.11 is "bigger," and tokenization strips out the digit-alignment signal that would override it. Detection: probe decimal comparisons across many pairs. Errors cluster where the shorter number has the larger tenths digit.
- **"How many R's in `strawberry`?"** Character-level questions are hard because BPE *hides the characters inside tokens*. The model sees the id for `straw` + `berry` (or similar), never the letters, so counting them means recovering information the input representation discarded. Same root cause: the tokenizer is an information bottleneck between the string and the model, a classic entry in [[Gotchas - Tokenizer Pathologies]].
- **Spooky per-value error patterns.** Chunk boundaries follow corpus frequency, so arithmetic accuracy is **non-monotone in the specific digits**. `2017 + x` can behave differently from `2018 + x` just because one addend is a single token and the other is two. The error maps look like reasoning inconsistencies and are pure tokenization artifacts, a real trap when debugging a "flaky" arithmetic capability. It's a cousin of the under-trained-id surprises in [[Lore - Glitch Tokens]].
- **Short-number accuracy over-promising.** A model that nails 3-digit addition can collapse on 12-digit addition because value encoding extrapolates poorly (Wallace et al.). Don't accept short-number benchmarks as evidence of numeric competence.

## The non-obvious
**Digit tokenization is a silent capability cliff that doesn't appear in the model card.** Two models with identical parameter count and training compute can differ enormously on arithmetic *purely* because one tokenizes digits singly and the other merges them by frequency. Nothing in the benchmark suite will show it unless the suite deliberately includes off-distribution digit lengths.

The corollary that catches teams: an arithmetic regression after swapping base models can be entirely a tokenizer change. The first move is to diff the two tokenizers on a batch of numbers, before any fine-tuning. More generally, the tokenizer is an **information bottleneck in front of the model**. Upstream of every parameter, it decides what compositional structure the network gets to see. Fixing numeracy is often a *pre-model* decision (single-digit or right-to-left tokenization, value-aware embeddings) that outweighs anything more scale can do, a rare case where the cheapest lever is also the strongest.

## Connections
- [[Concept - Byte-Pair Encoding]] — the down-link: BPE's frequency-driven merges are the direct cause of non-compositional digit tokens; this note is the numeracy-specific pathology of that algorithm.
- [[Concept - Grokking]] — the Fourier/trig circuit reverse-engineered for modular addition is the same internal mechanism models use to add digits, showing the value-geometry the tokenizer must not destroy.
- [[Gotchas - Tokenizer Pathologies]] — the aggregated pitfalls of tokenization; digit merges and the character-hiding bottleneck sit alongside the other traps there.
- [[Lore - Glitch Tokens]] — a sibling tokenizer-artifact story (under-trained token ids), reinforcing that the merge table has consequences far downstream of where it's built.
- [[Concept - Chain-of-Thought and Why It Works]] — externalizing per-digit steps compensates for the model's inability to align place values in a single forward pass; the practical mitigation for arithmetic prompts.
- [[Reference - Architecture Numerology]] — where digit/vocab conventions live among the other magic constants (vocab padding, head dims) an architect sets before training.
- [[Concept - Embeddings as Learned Representations]] — Wallace et al.'s probing result (embeddings encode magnitude but extrapolate poorly) and value-aware schemes like xVal/Abacus are statements about what the numeric embedding does and doesn't capture.
- [[Concept - Tokenizer Training]] — digit chunking (single-digit, three-digit, right-to-left) is a *tokenizer-training* decision made before any model weights exist, and the strongest lever on numeracy.

## Sources
- Wallace, Wang, Li, Singh & Gardner (2019) — "Do NLP Models Know Numbers? Probing Numeracy in Embeddings". Embeddings capture approximate magnitude but extrapolate poorly beyond the training range.
- Golkar, Pettee, Eickenberg, et al. (2023) — "xVal: A Continuous Number Encoding for Large Language Models". A single value-scaled `[NUM]` token as a continuous numeric inductive bias.
- McLeish, Bansal, Stein, ... & Goldstein (2024) — "Transformers Can Do Arithmetic with the Right Embeddings" (Abacus embeddings). Per-digit positional hints unlock length generalization from ~20-digit to ~100-digit addition.
- Nanda, Chan, Lieberum, Smith & Steinhardt (2023) — "Progress measures for grokking via mechanistic interpretability". The Fourier/trig addition circuit that reappears in how models represent numbers.
- Kantamneni & Tegmark (2024) — "Language Models Use Trigonometry to Do Addition". Models represent numbers on a helix and add via trig identities (recent, testable mechanistic claim).
