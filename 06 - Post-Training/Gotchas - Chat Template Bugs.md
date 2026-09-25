---
tags: [gotchas, domain/post-training, level/unicorn]
aliases: [chat template bugs, prompt formatting bugs, template mismatch]
summary: "The silent, no-error-thrown bugs in chat-template application that quietly degrade a model — double BOS, template drift, and their kin."
---

# Gotchas - Chat Template Bugs

Chat template bugs fail **silently**. A serialization bug throws no exception, spikes no loss curve, and trips no assertion. The model just gets measurably worse, because it's seeing token sequences slightly outside the distribution it trained on. Everything here builds on [[Concept - Chat Templates and Special Tokens]], which covers what a template *is*: a Jinja string in `tokenizer_config.json` that maps `{role, content}` messages to one token sequence. Ordered by how much pain each causes in practice.

## 1. Train/serve template mismatch: the silent OOD killer

**Symptom:** A fine-tune that evaluated well in your training harness is visibly duller in production. Instruction-following is worse, formatting weaker, roles occasionally confused, and there's no error or obvious cause.
**Cause:** You fine-tuned with template A (say, a trailing newline after the role header, or `<|im_end|>\n`) and serve with template B (different whitespace, different role tags, a different system-prompt slot). Every served prompt is now a few tokens off from what the model saw during [[Concept - Supervised Fine-Tuning (SFT)]], so the model runs out-of-distribution on *every request*. Templates ship *with* the model so this can't happen, but people re-implement formatting by hand, upgrade a serving framework that changed its default, or copy a template from a sibling model.
**Fix:** Pin the exact `tokenizer_config.json` Jinja that trained the model and call `tokenizer.apply_chat_template` at *both* train and serve time. Never hand-roll the format string in the serving layer.
**Detection:** For the same messages, byte-diff the rendered prompt from your training pipeline against the one from your serving stack. They must be **byte-identical**. This one diff catches the majority of "why is my fine-tune worse in prod" tickets.

## 2. Double BOS

**Symptom:** A small but real quality drop (a few points on eval) the moment you switch tokenization paths. First-token logprobs look off.
**Cause:** The template already emits a beginning-of-sequence token, and then `tokenizer(...)` with `add_special_tokens=True` (the default) prepends *another*. The sequence starts with two BOS tokens: `<|begin_of_text|><|begin_of_text|>` on Llama-3, `<bos><bos>` on Gemma. It's the single most common chat-template bug in the wild, because the failure is subtle and each layer "looks correct" on its own. Position 0 is special to the model, and it never trained on two BOS.
**Fix:** When the chat template handles special tokens, call the tokenizer with `add_special_tokens=False`. Most `apply_chat_template` paths already do. The bug shows up when you tokenize the template's *output* a second time, or mix `apply_chat_template` with a manual `tokenizer(text)`.
**Detection:** `print(input_ids[:3])` and look for a repeated BOS id. Assert `input_ids.count(bos_id) <= 1` in a data-loader test. Same root as [[Concept - Loss Masking and Sequence Packing]], where BOS/EOS placement inside packed sequences is its own trap.

## 3. Forgotten `add_generation_prompt` at inference

**Symptom:** At inference the model completes the *user's* turn, keeps writing as the user, or prints its own role header (`<|im_start|>assistant`) as literal text before answering.
**Cause:** `add_generation_prompt=True` appends the opening assistant header (`<|start_header_id|>assistant<|end_header_id|>\n\n`), which tells the model it's *its* turn. Leave it out and the last thing in context is the user turn's closer. The model does the statistically natural thing and continues the conversation from wherever it stands, often as the wrong speaker.
**Fix:** Pass `add_generation_prompt=True` when tokenizing for generation, and *false* when tokenizing a complete labeled example for training.
**Detection:** Decode the exact prompt string sent to the model and confirm it ends with the assistant header, not the user turn's end token.

## 4. Role delimiters not registered as special tokens

**Symptom:** Even after training, the model never reliably emits or respects turn boundaries. It "forgets" to stop, blends roles, or treats `<|im_start|>` as ordinary text.
**Cause:** Role markers like `<|im_start|>`, `<|eot_id|>`, `[INST]` have to be **added-vocabulary tokens**, each a single atomic id. Unregistered, they get split by [[Concept - Byte-Pair Encoding]] into several sub-word pieces (`<`, `|`, `im`, `_`, `start`, `|`, `>`), and the model has to learn the boundary from a fragile multi-token pattern instead of one clean symbol.
**Fix:** Add the delimiters with `tokenizer.add_special_tokens(...)`, call `model.resize_token_embeddings(len(tokenizer))`, and *train*. The new rows start random.
**Detection:** `tokenizer.encode("<|im_start|>")` should return one id, not a list of pieces. Check that `len(tokenizer)` matches the model's embedding rows.

## 5. Untrained special tokens behave like glitch tokens

**Symptom:** New special tokens (roles, tool markers, `<think>`) produce wild, high-variance outputs wherever they appear. Sometimes garbage, sometimes derailment.
**Cause:** A freshly added token's embedding row is random-initialized with a large norm relative to trained embeddings. Until it's trained enough, it injects a huge, meaningless vector into the residual stream. That's the same mechanism as [[Lore - Glitch Tokens]] (under-trained tokens that trigger bizarre behavior).
**Fix:** Initialize new-token embeddings to the mean of existing embeddings, not random, and make sure they appear often enough in training to be learned. Add a token you barely train and you should expect glitchy behavior.
**Detection:** Compare the L2 norm of new special-token embeddings against the median embedding norm. An outlier norm flags an under-trained token.

## 6. System prompt silently dropped, duplicated, or default-injected

**Symptom:** Your system prompt seems ignored, a persona or behavior you never set leaks in, or the system content shows up twice.
**Cause:** Templates handle the system prompt differently. Some fold it into the first user turn, some have a dedicated slot, some **inject a default system prompt** if you pass none (older Llama-2 chat), and some silently drop the `system` role entirely. Get it wrong and the model isn't being steered the way you think.
**Fix:** Read the actual Jinja and confirm where the system role lands. Pass system content the way *this* template expects, and don't assume a dedicated slot exists.
**Detection:** Render the full prompt with your system message and eyeball where it went: folded, slotted, or gone.

## 7. Whitespace and newline sensitivity

**Symptom:** Intermittent, hard-to-reproduce quality wobble tied to how you built the prompt.
**Cause:** A stray trailing space, a missing newline after a header, or `\r\n` vs `\n` shifts BPE tokenization away from what training saw. ` assistant` (leading space) and `assistant` are different tokens. Templates are whitespace-exact and casual string concatenation isn't.
**Fix:** Build prompts only through `apply_chat_template`, never `f"{role}: {content}\n"` by hand. This interacts with [[Concept - Sampling and Decoding Parameters]], since the mis-tokenized prefix conditions everything the sampler does next.
**Detection:** Byte-diff (as in #1) and inspect the token ids around every header and turn boundary.

## 8. Tool-call and multimodal template mis-serialization

**Symptom:** Function calling degrades (malformed JSON, ignored schemas) or multimodal placeholders land in the wrong position. Again, no error.
**Cause:** Tool/function-call and vision templates add structure (tool tokens, JSON tool schemas, `<image>` placeholders) that a generic chat template won't emit correctly. Serialize [[Concept - Tool Use and Function Calling]] payloads by hand, or through a template that doesn't know about tools, and the special tokens the model was trained to key on end up in the wrong place.
**Fix:** Use the model's *tool-aware* chat template (pass `tools=...` to `apply_chat_template` where supported). Confirm image placeholders and tool-result tokens are identical to the training format.
**Detection:** Decode a rendered tool-call prompt and check that tool tokens, schema, and any image placeholders are byte-for-byte what the model card specifies.

## Connections
- [[Concept - Chat Templates and Special Tokens]] — the concept these bugs are the pathology of; read it first for what a template is and does.
- [[Concept - Loss Masking and Sequence Packing]] — shares the BOS/EOS and special-token handling surface; masking bugs and template bugs compound.
- [[Concept - Byte-Pair Encoding]] — why unregistered delimiters get split into fragile pieces (#4) and why whitespace shifts tokenization (#7).
- [[Lore - Glitch Tokens]] — the mechanism behind under-trained special tokens behaving erratically (#5).
- [[Concept - Supervised Fine-Tuning (SFT)]] — the stage where the training-side template is set; train/serve drift (#1) is measured against it.
- [[Concept - Tool Use and Function Calling]] — the payloads whose tool-aware serialization is easy to break (#8).
- [[Concept - Sampling and Decoding Parameters]] — a mis-tokenized prefix conditions every downstream sampling decision.

## Sources
- HuggingFace Transformers docs — *Chat Templates* and `apply_chat_template` (`add_generation_prompt`, `add_special_tokens`, `tools=`). The canonical mechanism reference.
- Unsloth / community bug reports (2024) — documented double-BOS quality regressions on Llama-3 and Gemma when template BOS and tokenizer BOS stack.
- Model cards (Llama-3, Mistral, Gemma, ChatML/Qwen) — the authoritative per-model delimiter, BOS/EOS, and system-slot specifications to pin against.
