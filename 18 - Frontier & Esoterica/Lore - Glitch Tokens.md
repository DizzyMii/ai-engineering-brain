---
tags: [lore, domain/esoterica, level/advanced]
aliases: [SolidGoldMagikarp, petertodd, Under-Trained Tokens, Unspeakable Tokens]
summary: "The SolidGoldMagikarp saga: under-trained vocabulary tokens that make LLMs hallucinate, evade, or break, and the tokenizer/corpus mismatch behind them."
---

## What happened

In February 2023, Jessica Rumbelow and Matthew Watkins (then at SERI-MATS) posted "SolidGoldMagikarp (plus, prompt generation)" on LessWrong. They had been probing GPT-2 and GPT-J token embeddings — clustering them and searching for tokens nearest the embedding-space centroid, the region where a rarely-moved vector would sit — and surfaced a list of anomalous strings: ` SolidGoldMagikarp`, ` petertodd`, ` TheNitromeFan`, `davidjl`, ` guiActiveUn`, ` externalToEVA`, and dozens more. Then they fed them to GPT-2, GPT-3, and GPT-J and watched the models come apart.

Asked to simply repeat ` SolidGoldMagikarp`, models would say "distribute," or "You are a jerk," or spell out an unrelated word, or refuse, or hallucinate a completely different string. The tokens were, in the writeup's word, *unspeakable* — the model could not echo them back. ` petertodd` became its own micro-legend for the surreal, sometimes menacing completions it produced. These were not cherry-picked one-offs; the same class of failure reproduced across models and across many tokens, which is what made it interesting rather than a curiosity.

The root cause is a **tokenizer/training-corpus mismatch**, and it is entirely mundane once you see it. GPT-2's [[Concept - Byte-Pair Encoding]] tokenizer was trained on a corpus that included Reddit's r/counting (a subreddit where users post incrementing numbers, with heavy contributors like *TheNitromeFan* and *SolidGoldMagikarp*) and text from the Puzzle & Dragons game community. Those usernames and strings appeared often enough *in the tokenizer's training corpus* to earn their own dedicated merges — single tokens. But that same Reddit data was later deduplicated and filtered out of the *model's* pretraining set. So the model almost never — or literally never — saw those token ids during training.

A token embedding is a lookup row in a matrix; it only moves when a training example containing that token produces a gradient. A token with training-set frequency ≈ 0 keeps its embedding near random initialization (see [[Concept - Embeddings as Learned Representations]]). The forward pass then reads a meaningless vector out of a meaningless region of activation space, and the rest of the network does something undefined with it — hence "unspeakable," evasive, hallucinated-substitution, and persona-break behaviors. The deduplication that made the pretraining corpus cleaner (see [[Concept - Deduplication at Scale]]) is exactly what orphaned these tokens, and the refusal/deflection outputs are that orphaned vector colliding with the model's [[Concept - Refusal Mechanics]].

The anecdote became method a year later. Land & Bartolo 2024 ("Fishing for Magikarp: Automatically Detecting Under-trained Tokens in Large Language Models") built automated detectors — using unembedding statistics and reachability tests — and ran them across many open models (Llama, Mistral, Gemma, and others), finding *hundreds* of under-trained or unreachable tokens per tokenizer, concentrated in multilingual and code token ranges. What looked like a haunted GPT-2 curiosity turned out to be a systematic property of large vocabularies. The reusable detection recipe lives in [[Snippet - Finding Under-Trained Tokens]], and the pre-flight version in [[Checklist - Auditing a Tokenizer for Glitch Tokens]].

## The lesson

Mechanically: **the tokenizer and the training corpus must be co-designed.** Any token whose training-set frequency is near zero is a latent glitch, because its embedding never receives a gradient and stays wherever initialization put it. This is not a bug you fix downstream at inference; it is baked in the moment you freeze a vocabulary against a corpus that does not exercise every token.

The counterintuitive corollary: large multilingual vocabularies (100k–256k tokens, now standard) make glitch tokens *more* common, not less. A bigger vocabulary earns dedicated tokens for rarer strings — obscure Unicode, niche code identifiers, low-resource-language fragments — and precisely those long-tail tokens are the ones most likely to be filtered, deduplicated, or simply absent from the pretraining mix. More vocabulary means more opportunities for the corpus to fail to cover it. The practical consequence for anyone shipping a new tokenizer or an open-weights model is that you cannot assume the vocabulary is clean; you audit it, because the failure is invisible until someone types the wrong string. This is the backstory the aggregated failures in [[Gotchas - Tokenizer Pathologies]] draw on, and it is why the digit-handling problems in [[Concept - Numeracy and Digit Tokenization]] belong to the same family — both are cases where the tokenizer's view of text and the model's learned behavior diverge.

## Evidence status

**Verified.** The original LessWrong writeup (Rumbelow & Watkins, February 2023) is public, the r/counting and Puzzle & Dragons corpus explanation was confirmed by community investigation, the behaviors reproduce on released GPT-2/GPT-J checkpoints, and the academic follow-up (Land & Bartolo 2024) is peer-reviewed and replicable across many open models. The ` petertodd` "menacing persona" framing is genuine observed output but has accumulated the usual online mythologizing — the *behavior* is verified; the narrative around any single token is folklore layered on top of a real, mechanical artifact.

## Connections
- [[Concept - Byte-Pair Encoding]] — the merge algorithm that mints a dedicated token for a frequent string, setting up the mismatch.
- [[Concept - Embeddings as Learned Representations]] — a token's embedding only moves under gradients; zero frequency means a frozen, near-random row.
- [[Concept - Deduplication at Scale]] — the corpus-cleaning step that orphaned the tokens by removing the data that would have trained them.
- [[Concept - Refusal Mechanics]] — the deflection/refusal outputs are the untrained vector colliding with refusal behavior.
- [[Concept - Numeracy and Digit Tokenization]] — a sibling tokenizer pathology where the tokenizer's and model's views of text diverge.
- [[Gotchas - Tokenizer Pathologies]] — the aggregated, symptom-first failure catalog this story feeds.
- [[Snippet - Finding Under-Trained Tokens]] — the statistical + behavioral detection recipe that turns this anecdote into an audit.
- [[Checklist - Auditing a Tokenizer for Glitch Tokens]] — the pre-flight list to catch these before you trust a tokenizer.

## Sources
- Rumbelow & Watkins (2023, LessWrong) — *SolidGoldMagikarp (plus, prompt generation)*. The original discovery and behavioral taxonomy.
- Land & Bartolo (2024) — *Fishing for Magikarp: Automatically Detecting Under-trained Tokens in LLMs*. Systematic detection across open models; hundreds per tokenizer.
