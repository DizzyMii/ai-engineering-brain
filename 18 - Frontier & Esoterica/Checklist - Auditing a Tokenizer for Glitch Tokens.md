---
tags: [checklist, domain/esoterica, level/advanced]
aliases: [glitch token audit, tokenizer audit checklist]
summary: "Pre-flight checks to catch under-trained, unreachable, and pathological tokens before trusting a tokenizer in training or production."
---

# Checklist - Auditing a Tokenizer for Glitch Tokens

Run every item before you trust a new or third-party tokenizer: at pretraining time, before fine-tuning on someone else's checkpoint, or before shipping a vocabulary change. A tokenizer that passes round-trip tests can still hide hundreds of under-trained tokens waiting to hallucinate, evade or break when a user hits them.

## Reachability

- [ ] Every token id in the vocabulary can be produced by encoding some real string. Decode each id, re-encode the result, and confirm the id comes back. Ids that never round-trip are unreachable and prime glitch candidates.
- [ ] Round-trip integrity also holds on a real corpus sample: encode then decode a large held-out text sample and assert byte-exact reconstruction, not just matching token counts.
- [ ] Unicode normalization surprises are checked explicitly. Encode the same visual string in two normalization forms (NFC vs. NFKC) and confirm the tokenizer handles both consistently, or that the inconsistency is documented.

## Embedding statistics

- [ ] For every token, compute a cheap statistic (the unembedding row's L2 norm, or the max predicted probability for that token across a batch of diverse prompts) and flag the bottom percentile as under-trained candidates.
- [ ] Cross-check against input-embedding statistics. Tokens whose input embedding sits near the vocabulary centroid or has an anomalously small norm are candidates independently of the output-side signal; combining both cuts false positives.
- [ ] The candidate list comes from one matmul over the full vocabulary, not a per-token generative pass, so a 100K-256K token vocabulary is screened in one cheap sweep before any expensive probing.

## Behavioral verification

- [ ] The top statistical candidates (a few hundred, not the whole flagged list) are probed behaviorally. Prompt the model to repeat each token verbatim and record failure, deflection, substitution or nonsense as a confirmed glitch.
- [ ] A handful of statistically clean, high-frequency tokens go through the same repeat probe as a negative control, confirming the probe doesn't produce false positives on ordinary tokens.

## Special-token hygiene

- [ ] Exactly one BOS token is added per sequence, verified end to end through the actual serving path. The raw tokenizer and the [[Concept - Chat Templates and Special Tokens|chat template]] can each add one on their own.
- [ ] EOS, PAD and UNK ids are distinct, correctly mapped, and match what the training pipeline used. A silent PAD/EOS collision is a common source of downstream generation bugs.
- [ ] Any added or reserved special tokens have trained embeddings, not freshly initialized random rows appended after pretraining finished.

## Digit and whitespace behavior

- [ ] Integers and decimals of varying length are tokenized and inspected directly, not inferred, to confirm whether digits are merged, grouped or split individually, and whether the same number tokenizes the same way in different surrounding contexts. [[Concept - Numeracy and Digit Tokenization]] explains why this matters.
- [ ] Leading- and trailing-space sensitivity is tested explicitly. Confirm `"word"` and `" word"` tokenize differently as expected, and that prompt-construction code never emits a trailing space right before a generation call.

## Multilingual and code coverage

- [ ] Tokens-per-word (or tokens-per-byte) is measured for every target language and for code, against English on equivalent content.
- [ ] Any language or code range above roughly 3-4x the English tokens-per-word rate is flagged, both as a cost/latency problem and as a range where under-trained tokens statistically cluster.

## Why these items

- **Reachability and round-trip checks** come from SolidGoldMagikarp. [[Lore - Glitch Tokens]] traces GPT-2/3/J tokens like `SolidGoldMagikarp` and `petertodd` to a tokenizer trained on a corpus (Reddit's r/counting, a Puzzle & Dragons subreddit) that was later deduplicated out of the actual training set. The tokens existed and were reachable, but their embeddings were never meaningfully updated.
- **Statistics as one matmul, not per-token generation,** because Land & Bartolo's "Fishing for Magikarp" (2024) found hundreds of under-trained tokens per open model (Llama, Mistral, Gemma). A per-token generative probe over a 100K+ vocabulary is too slow to run on every release. Going statistics-first is what keeps this check alive on a real schedule.
- **"Verified end to end through the serving path"** for special tokens, because double-BOS (the tokenizer adds one, the chat template adds another) is a recurring, easy-to-introduce bug. Many models tolerate it poorly, since [[Concept - Attention Sinks|the attention sink]] expects exactly one stable anchor position.
- **The behavioral negative control**, because an aggressive statistical threshold flags legitimately rare but fine tokens (rare Unicode, reserved slots) as glitches. Without a control you can't tell a real glitch token from an overzealous cutoff.

## Connections
- [[Snippet - Finding Under-Trained Tokens]] — the runnable implementation of the embedding-statistics and repeat-probe checks in this list; an up-link to the code that operationalizes this checklist.
- [[Lore - Glitch Tokens]] — the SolidGoldMagikarp history that motivates the reachability and embedding-statistic sections.
- [[Gotchas - Tokenizer Pathologies]] — the broader failure catalogue this checklist exists to catch before it ships; a down-link to the prerequisite pitfall survey.
- [[Concept - Byte-Pair Encoding]] — the merge algorithm whose corpus-frequency dependence is the root cause every item here is checking for symptoms of; a down-link to the mechanism prerequisite.
- [[Concept - Numeracy and Digit Tokenization]] — the deeper mechanism behind the digit-consistency checks.
- [[Concept - Chat Templates and Special Tokens]] — the other half of the BOS/EOS bookkeeping the special-token-hygiene section checks against.

## Sources
- Rumbelow & Watkins (2023) — "SolidGoldMagikarp (plus, prompt generation)" (LessWrong/SERI-MATS). The original discovery of under-trained glitch tokens.
- Land & Bartolo (2024) — "Fishing for Magikarp: Automatically Detecting Under-trained Tokens in Large Language Models." The systematic detection method this checklist operationalizes.
