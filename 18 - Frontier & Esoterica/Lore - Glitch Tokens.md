---
tags: [lore, domain/esoterica, level/advanced]
aliases: [SolidGoldMagikarp, petertodd, Under-Trained Tokens, Unspeakable Tokens]
summary: "The SolidGoldMagikarp saga: under-trained vocabulary tokens that make LLMs hallucinate, evade, or break, and the tokenizer/corpus mismatch behind them."
---

## What happened

In February 2023, Jessica Rumbelow and Matthew Watkins (then at SERI-MATS) posted "SolidGoldMagikarp (plus, prompt generation)" on LessWrong. They had been probing GPT-2 and GPT-J token embeddings, clustering them and looking for tokens nearest the embedding-space centroid, which is where a rarely updated vector would sit. That turned up a list of anomalous strings: ` SolidGoldMagikarp`, ` petertodd`, ` TheNitromeFan`, `davidjl`, ` guiActiveUn`, ` externalToEVA`, and dozens more. They fed them to GPT-2, GPT-3 and GPT-J and watched the models come apart.

Asked simply to repeat ` SolidGoldMagikarp`, a model might say "distribute," or "You are a jerk," or spell out an unrelated word, refuse, or hallucinate a different string entirely. In the writeup's word, the tokens were *unspeakable*: the model couldn't echo them back. ` petertodd` became a micro-legend of its own for the surreal, sometimes menacing completions it produced. None of this was cherry-picked. The same class of failure reproduced across models and across many tokens, which is what made it more than a curiosity.

The cause is a **tokenizer/training-corpus mismatch**, and it's mundane once you see it. GPT-2's [[Concept - Byte-Pair Encoding]] tokenizer was trained on a corpus that included Reddit's r/counting (a subreddit where users post incrementing numbers, with heavy contributors like *TheNitromeFan* and *SolidGoldMagikarp*) and text from the Puzzle & Dragons game community. Those usernames and strings were frequent enough *in the tokenizer's corpus* to earn dedicated merges, i.e. single tokens. That Reddit data was later deduplicated and filtered out of the *model's* pretraining set, so the model rarely or literally never saw those token ids in training.

A token embedding is a row in a lookup matrix, and it only moves when a training example containing the token produces a gradient. At training-set frequency ≈ 0 the embedding stays near its random initialization (see [[Concept - Embeddings as Learned Representations]]). The forward pass reads a meaningless vector from a meaningless region of activation space, and the rest of the network does something undefined with it. Hence the unspeakable, evasive, hallucinated-substitution and persona-break behaviors. The deduplication that cleaned up the pretraining corpus (see [[Concept - Deduplication at Scale]]) is what orphaned these tokens, and the refusal/deflection outputs are the orphaned vector running into the model's [[Concept - Refusal Mechanics]].

A year later the anecdote became a method. Land & Bartolo 2024 ("Fishing for Magikarp: Automatically Detecting Under-trained Tokens in Large Language Models") built automated detectors from unembedding statistics and reachability tests and ran them across many open models (Llama, Mistral, Gemma and others). They found *hundreds* of under-trained or unreachable tokens per tokenizer, concentrated in multilingual and code ranges. The haunted GPT-2 curiosity turned out to be a systematic property of large vocabularies. The reusable detection recipe is in [[Snippet - Finding Under-Trained Tokens]], and the pre-flight version in [[Checklist - Auditing a Tokenizer for Glitch Tokens]].

## The lesson

**Design the tokenizer and the training corpus together.** Any token with near-zero training-set frequency is a latent glitch: its embedding never gets a gradient and stays wherever initialization put it. You can't fix that downstream at inference. It's baked in the moment you freeze a vocabulary against a corpus that doesn't exercise every token.

The counterintuitive corollary is that large multilingual vocabularies (100k–256k tokens, now standard) make glitch tokens *more* common. A bigger vocabulary gives dedicated tokens to rarer strings (obscure Unicode, niche code identifiers, fragments of low-resource languages), and those long-tail tokens are the ones most likely to be filtered, deduplicated or simply missing from the pretraining mix. More vocabulary, more chances for the corpus to miss some of it. If you ship a new tokenizer or an open-weights model, you can't assume the vocabulary is clean. Audit it, because the failure stays invisible until someone types the wrong string. The aggregated failures in [[Gotchas - Tokenizer Pathologies]] draw on this backstory, and the digit-handling problems in [[Concept - Numeracy and Digit Tokenization]] belong to the same family: in both, the tokenizer's view of text and the model's learned behavior diverge.

## Evidence status

**Verified.** The original LessWrong writeup (Rumbelow & Watkins, February 2023) is public. Community investigation confirmed the r/counting and Puzzle & Dragons corpus explanation, the behaviors reproduce on released GPT-2/GPT-J checkpoints, and the academic follow-up (Land & Bartolo 2024) is peer-reviewed and replicable across many open models. The ` petertodd` "menacing persona" story is based on real observed output but has picked up the usual online mythologizing. The *behavior* is verified; the narrative around any single token is folklore on top of a real, mechanical artifact.

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
