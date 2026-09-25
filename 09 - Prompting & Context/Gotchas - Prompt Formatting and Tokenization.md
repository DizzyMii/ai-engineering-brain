---
tags: [gotchas, domain/prompting-context, level/advanced]
aliases: []
summary: "Token- and format-level prompting bugs: template mismatches, double BOS, whitespace shifts, cache-busting, with fixes and detection."
---
# Gotchas - Prompt Formatting and Tokenization

These bugs live below "what should I write in the prompt". They happen when your prompt gets turned into token IDs, and they're nasty because nothing raises: no exception, no stack trace, no lint error. The model just does something worse, and everyone blames the model instead of the pipeline. Roughly ordered by how much production pain they cause.

## 1. Chat template mismatch after a model swap silently tanks quality
**Symptom:** You replace a Llama-3-Instruct deployment with a fine-tuned Mistral checkpoint (or point the same serving code at a new model version), and eval scores drop 10-30 points with no errors, exceptions or warnings anywhere in the stack.
**Cause:** Every instruction-tuned model is trained on one exact literal layout, its [[Concept - Chat Templates and Special Tokens]]: ChatML's `<|im_start|>system...<|im_end|>`, Llama-2's `[INST] <<SYS>>...<</SYS>>...[/INST]`, Llama-3's `<|start_header_id|>`. If serving code hardcodes one template (or keeps the previous model's) instead of resolving the new checkpoint's own, the string is out of distribution but still perfectly parseable text. Nothing errors because there's no parser, only an autoregressive model continuing whatever it's given.
**Fix:** Resolve the template from the model's own tokenizer config (`AutoTokenizer.apply_chat_template`) every time. Treat the template as a versioned artifact tied to the checkpoint and never cache it separately.
**Detection:** Gate every model swap on the full eval suite (see [[Concept - Prompt Evaluation and Versioning]]) before rollout. A template mismatch looks like an unexplained, fleet-wide accuracy drop that lines up with a model change and nothing else.

## 2. A double BOS token degrades every request
**Symptom:** Outputs are slightly worse across the board (a bit less coherent, sometimes repetitive) with no obvious single cause, and it persists through prompt-content changes.
**Cause:** Most chat templates prepend a beginning-of-sequence token automatically. If serving code also prepends `<s>` by hand, or a tokenizer call after `apply_chat_template` runs with `add_special_tokens=True` again, the model sees two BOS tokens in a row. It essentially never saw that during training, where BOS appears once, at position 0.
**Fix:** Let the chat template own all special-token insertion. Any raw tokenizer call after templating passes `add_special_tokens=False`.
**Detection:** Decode the actual `input_ids` sent to the model (not the source string) and confirm BOS appears once, at index 0. The bug doesn't show in the rendered prompt text, only at the token-ID level.

## 3. Control-token strings inside user text break turn structure
**Symptom:** A user pastes text containing something like `<|im_end|>` into a chat field, and the model seems to end its turn early or treats the pasted string as an unintended role boundary.
**Cause:** Special/control tokens are single vocabulary IDs, not ordinary character sequences. If prompt assembly concatenates strings naively instead of inserting control-token IDs directly, a user substring matching a control token's literal text can get BPE-merged into that same token ID at encode time. The model can't tell it from a real, system-inserted boundary. It's close to the pathology in [[Lore - Glitch Tokens]], where rarely or never trained vocabulary entries cause erratic completions when sampled or injected.
**Fix:** Sanitize or escape literal control-token substrings in any untrusted input. More robust: assemble prompts at the token-ID level so a fake control token can never collide with the real one's ID.
**Detection:** Fuzz the input pipeline with literal control-token strings taken from the tokenizer vocabulary and check that turn and role boundaries survive.

## 4. Prompt-cache busting from prefix instability
**Symptom:** [[Concept - Prompt Caching]] hit rate is far below what you expected. You pay close to full prefill per request although the system prompt, few-shot block and RAG context are identical from call to call.
**Cause:** Cache matching is exact and positional, starting at token 0 of the prefix. A timestamp, request ID, UUID, or JSON object with unfixed key order changes one early token, and everything after it counts as new, however little the meaning changed.
**Fix:** Order the prompt so every static element (system prompt, tool schemas, few-shot exemplars) comes first, and push anything variable (the current date if you really need it, the user turn, retrieved-doc IDs) to the end. Serialize JSON with a fixed key order.
**Detection:** Monitor the provider's reported cache-read token count per call (Anthropic and OpenAI both expose it) and alert when hit rate falls below the endpoint's expected baseline.

## 5. Trailing whitespace moves the model onto a different token boundary
**Symptom:** A purely cosmetic-looking edit, adding or removing a trailing newline or space, changes the completion: an extra leading space, a broken word start, an unexpected first token.
**Cause:** In most modern byte-level BPE schemes, [[Concept - Byte-Pair Encoding]] turns `" word"` and `"word"` into different token IDs, because the leading space is folded into the token. A trailing space or newline at the end of the prompt changes which token ID the model conditions on for its first generated token. Generation resumes from wherever the prefix's tokenization landed, not from the character boundary a human sees.
**Fix:** Strip trailing whitespace deterministically before sending, and standardize newline counts between prompt sections.
**Detection:** When completion quality looks off for no content reason, inspect the last few token IDs of the encoded prompt (not the raw string) in a debugging harness.

## 6. Few-shot exemplars formatted differently from the live query teach the wrong pattern
**Symptom:** Adding few-shot examples makes accuracy worse than zero-shot, or the model copies an exemplar's formatting quirk (an odd delimiter, a wrong field name) into its answer for the live input.
**Cause:** In-context learning is very sensitive to surface form. If exemplars use `Q:`/`A:` and the live query uses `Question:`/`Answer:`, or the exemplars' JSON has no trailing commas and the live prompt does, the model sees the live turn as a distributional break instead of one more of the same. It then imitates whatever pattern is most locally salient instead of doing the task.
**Fix:** Send exemplars and the live query through the same formatting function. Never hand-format one and generate the other.
**Detection:** Diff the rendered exemplar block against the rendered live-query block, ignoring content, to confirm the structure matches.

## 7. "Do not X" negations underperform positive instructions
**Symptom:** The system prompt says "do not use bullet points" or "do not mention pricing", and the model does it anyway, more often than when the same constraint is phrased positively.
**Cause:** Negation is weakly and inconsistently represented in autoregressive language models. "do not use bullet points" still overlaps heavily, on the surface and semantically, with "use bullet points", and next-token prediction has no hard logical negation operator. The instruction is a soft distributional nudge, not an enforced rule. This follows the broader instruction-sensitivity picture in [[Concept - Prompt Formatting and Sensitivity]]; no single paper establishes it.
**Fix:** State the behavior you want directly ("write your answer as 2-3 prose paragraphs", not "don't use bullet points"), and keep hard negatives for things you can also check in code.
**Detection:** A/B positive vs. negative phrasing on your eval set ([[Concept - Prompt Evaluation and Versioning]]). The failure-rate gap is usually big enough to see on a few hundred examples.

## 8. Markdown code fences around JSON break naive parsers
**Symptom:** `json.loads()` (or a schema validator) throws on a response that looks like valid JSON.
**Cause:** Instruction-tuned models default to wrapping code-shaped output in triple-backtick fences (` ```json ... ``` `), since that's the dominant training-data convention for showing code and JSON in chat UIs. It's a strong stylistic prior, not a model bug, and it breaks any parser that expects bare JSON.
**Fix:** Tell the model explicitly to output raw JSON without markdown fences, and strip leading/trailing triple-backtick blocks in the parsing layer anyway (see [[Playbook - Reliable Structured Output]]). The instruction alone isn't 100% reliable, so stripping is mandatory.
**Detection:** Track parse-failure rate as a real metric, not an exception you catch and ignore. A nonzero baseline of fence-wrapped responses is normal and should be handled by default.

## Connections
- [[Concept - Byte-Pair Encoding]] — the tokenizer boundary mechanics behind the whitespace and control-token gotchas.
- [[Concept - Chat Templates and Special Tokens]] — the source of truth this entire list exists to protect you from getting wrong.
- [[Lore - Glitch Tokens]] — the deeper pathology when rare or control tokens get sampled or injected unexpectedly.
- [[Playbook - Reliable Structured Output]] — the defensive parsing and repair loop that catches several of these gotchas downstream.
- [[Concept - Prompt Caching]] — the economics that prefix-instability bugs quietly destroy.
- [[Concept - Prompt Formatting and Sensitivity]] — the research-level framing of why "trivial" formatting choices move accuracy this much.
- [[Concept - Prompt Evaluation and Versioning]] — the regression gate that catches template mismatches and negation-phrasing bugs before they reach production.

## Sources
- Sclar et al. (2023) — "Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design" (FormatSpread): the empirical backdrop for why format-level bugs like these move accuracy far more than intuition suggests.
- Hugging Face `transformers` documentation — `apply_chat_template`: the canonical fix for template-mismatch bugs.
- Folklore, weakly sourced: double-BOS degradation and control-token injection quirks are widely reported across Llama/Mistral open-weights deployment threads without a single controlled study behind them; treat as engineering lore worth guarding against, not a benchmarked effect size.
