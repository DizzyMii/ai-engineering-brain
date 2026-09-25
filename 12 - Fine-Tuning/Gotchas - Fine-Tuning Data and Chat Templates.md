---
tags: [gotchas, domain/fine-tuning, level/core]
aliases: []
summary: "Seven data- and formatting-side pitfalls — template mismatches, masking bugs, tokenizer drift — that silently wreck a fine-tune."
---

## 1. Wrong chat template for the base model: it never learns to stop
**Symptom:** after fine-tuning, the model runs past where a turn should end, hallucinates a fake "user" turn and answers it, or otherwise garbles turn structure. **Cause:** every base model expects its own role tags, delimiters and special tokens. ChatML's `<|im_start|>`/`<|im_end|>` isn't Llama-3's `<|start_header_id|>`/`<|eot_id|>`, and neither is Mistral's `[INST]` format (mechanics in [[Concept - Chat Templates and Special Tokens]]). Data rendered in the wrong template teaches a turn-boundary convention the tokenizer and base weights don't share. **Fix:** render training examples through the target base model's own `apply_chat_template` (or its documented format). Never use a hardcoded string copied from another model family's example script. **Detection:** this is the number-one silent failure in fine-tuning. Before launching a full run, diff one rendered training example token by token against a known-good example from the base model's own model card.

## 2. Prompt not masked out of the loss: the model learns to emit instructions
**Symptom:** at inference the fine-tuned model paraphrases or repeats the system prompt / instructions back to the user instead of answering. **Cause:** if loss is computed over the full sequence (prompt plus completion) instead of only the completion tokens, cross-entropy also pushes the model to predict the prompt. It partly learns to generate instructions as well as follow them (mechanics in [[Concept - Loss Masking and Sequence Packing]]). **Fix:** mask every token outside the target completion (set its label to the ignore-index, e.g. -100) before computing loss. **Detection:** print the loss-mask array for a handful of samples and confirm the unmasked region starts where the assistant's answer starts, not one token earlier or later.

## 3. Missing or duplicated EOS token: the model never stops, or stops early
**Symptom:** generation runs to the max-token limit every time with no natural stop, or cuts answers off mid-sentence. **Cause:** for the model to learn where to stop, the end-of-sequence marker has to appear once, in the right place, in every training example. A formatting script that forgets to append EOS, or appends it twice (once via a template helper, once by hand), teaches an inconsistent stopping signal. **Fix:** check that every tokenized example ends with exactly one instance of the correct EOS token for that base model. **Detection:** decode the raw token ids (not the rendered text) of 20-30 samples and count EOS per example. It should always be one, at the end.

## 4. Tokenizer mismatch between data prep and training
**Symptom:** training loss looks fine but output is subtly wrong: words fused oddly, or specific tokens (especially near added special tokens, see [[Concept - Byte-Pair Encoding]]) come out corrupted. **Cause:** if the tokenizer that pre-tokenized the dataset is a different revision from the one loaded at train time (added tokens, a changed vocab size, a retrained merge table), token ids silently point to different subwords than the ones the model learned. The loss curve can't show it, because the model dutifully learns whatever ids it gets; the bug only appears at decode time. **Fix:** pin the tokenizer to the same revision/hash as the model checkpoint, load it once, and reuse that object for data prep and training. Don't re-instantiate "the same" tokenizer by name in two places. **Detection:** compare hashes of the tokenizer's vocab file (or `len(tokenizer)` plus a fixed test string's token ids) between the data-prep and training scripts.

## 5. Padding side and attention-mask mistakes: training on pad tokens
**Symptom:** short examples in a batch train noticeably worse than long ones, or the model drifts toward truncated-looking answers. **Cause:** causal LMs need padding excluded from the loss via the attention mask (and typically left-padding for generation, right-padding for training, depending on the framework). If the mask isn't wired through, the model computes gradient on pad tokens as if they were content. An all-one-length batching scheme can also bake in a length/format bias where every example looks truncated at the same point. **Fix:** confirm the attention mask (and label mask) excludes pad positions from both the effective context and the loss, and mix example lengths within a batch instead of bucketing by identical length. **Detection:** compute per-example loss and check it doesn't correlate suspiciously with sequence length; spot-check that pad positions have their label set to the ignore-index.

## 6. Dataset too small or repetitive: memorization instead of generalization
**Symptom:** the model reproduces training examples near-verbatim on inputs only superficially different from the training data; eval loss rises while train loss keeps falling. **Cause:** a small or low-diversity dataset gives the optimizer too few directions to generalize along. Memorizing the finite example set is cheaper for gradient descent than learning the underlying pattern, especially over multiple epochs. **Fix:** widen sourcing diversity, cut epochs (one epoch is often enough on larger sets), and near-dedup the training pool itself, not only train against eval. **Detection:** the classic signature is eval loss curving up while train loss keeps dropping. That divergence point is roughly where training should have stopped or more data should have gone in.

## 7. Eval-set contamination in training data: inflated metrics that don't hold in production
**Symptom:** the held-out eval score looks excellent, and production behavior on novel inputs is mediocre. **Cause:** if any training example is a near-duplicate of an eval example (or of a public benchmark you report against), the "held-out" metric is partly measuring memorization (general mechanism in [[Concept - Benchmark Contamination]]). **Fix:** near-dedup the training set against the eval set (and any benchmark suite) before training, with the same technique as general dataset dedup. **Detection:** run a similarity search of every eval example against the full training set. Any near-duplicate above a similarity threshold is contamination, and it's what the ship-gate step in [[Playbook - Evaluating a Fine-Tune]] is designed to catch before release.

## Connections
- [[Playbook - Preparing a Fine-Tuning Dataset]] — the procedure whose steps 5, 6, 8, and 9 exist specifically to avoid these seven gotchas.
- [[Playbook - Evaluating a Fine-Tune]] — detects gotchas 6 and 7 via the eval-loss/train-loss divergence and contamination checks.
- [[Gotchas - LoRA Fine-Tuning]] — the companion catalog for adapter-side (rather than data-side) pitfalls.
- [[Concept - Chat Templates and Special Tokens]] — owns the template mechanics behind gotcha 1.
- [[Concept - Loss Masking and Sequence Packing]] — owns the masking mechanics behind gotcha 2.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the training process all seven gotchas ultimately corrupt.
- [[Concept - Benchmark Contamination]] — owns the general mechanism behind gotcha 7.
- [[Concept - Byte-Pair Encoding]] — owns the tokenizer mechanics behind gotchas 3 and 4.

## Sources
- These are field-accumulated pitfalls rather than results from a single paper; the primary mechanism citations live on the linked Concept notes above (chat templates, loss masking, contamination, and tokenization).
