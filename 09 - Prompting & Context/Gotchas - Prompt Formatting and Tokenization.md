---
tags: [gotchas, domain/prompting-context, level/advanced]
aliases: []
summary: "Token- and format-level prompting bugs: template mismatches, double BOS, whitespace shifts, cache-busting, with fixes and detection."
---
# Gotchas - Prompt Formatting and Tokenization

These are the pitfalls that live below the level of "what should I write in the prompt" — they're bugs in how your prompt gets turned into token IDs, and they're insidious precisely because there's no exception, no stack trace, no lint error. The model just quietly does something worse, and everyone blames the model instead of the pipeline. Ordered roughly by how much production pain they cause.

## 1. Chat template mismatch after a model swap silently tanks quality
**Symptom:** You swap a Llama-3-Instruct deployment for a fine-tuned Mistral checkpoint (or point the same serving code at a new model version) and eval scores drop 10-30 points with zero errors, exceptions, or warnings anywhere in the stack.
**Cause:** Every instruction-tuned model is trained against one exact literal string layout — the [[Concept - Chat Templates and Special Tokens]] — whether that's ChatML's `<|im_start|>system...<|im_end|>`, Llama-2's `[INST] <<SYS>>...<</SYS>>...[/INST]`, or Llama-3's `<|start_header_id|>`. If serving code hardcodes one template (or reuses the previous model's) instead of resolving the new checkpoint's own template, the resulting string is out-of-distribution but still perfectly parseable text — there's no error because there's no parser, just an autoregressive model continuing whatever it's handed.
**Fix:** Resolve the template from the model's own tokenizer config (`AutoTokenizer.apply_chat_template`) every time, and treat the template as a versioned artifact bound to the checkpoint, never cached independently of it.
**Detection:** Gate every model swap behind the full eval suite (see [[Concept - Prompt Evaluation and Versioning]]) before rollout — a template mismatch shows up as an unexplained, fleet-wide accuracy regression correlated with a model change and nothing else.

## 2. Double BOS token quietly degrades every request
**Symptom:** Outputs are subtly worse across the board — slightly less coherent, occasionally repetitive — with no obvious single cause, and it survives prompt-content changes.
**Cause:** Most chat templates prepend a beginning-of-sequence token automatically. If serving code also manually prepends `<s>`, or a tokenizer call downstream of `apply_chat_template` runs with `add_special_tokens=True` again, the model sees two BOS tokens back-to-back — a sequence shape it essentially never saw during training, since BOS ordinarily occurs exactly once, at position 0.
**Fix:** Let the chat template own all special-token insertion; any raw tokenizer call applied after templating must pass `add_special_tokens=False`.
**Detection:** Decode the actual `input_ids` sent to the model (not the source string) and confirm BOS appears exactly once, at index 0 — this bug is invisible in the rendered prompt text and only shows up at the token-ID level.

## 3. Control-token strings inside user text break turn structure
**Symptom:** A user pastes text containing something like `<|im_end|>` into a chat field, and the model appears to end its turn early, or treats the pasted string as a role boundary that was never intended.
**Cause:** Special/control tokens are single vocabulary IDs, not ordinary character sequences. If prompt assembly does naive string concatenation instead of inserting control-token IDs directly, a user-supplied substring that matches a control token's literal text can get BPE-merged into that exact same token ID at encode time — indistinguishable to the model from a "real," system-inserted boundary. This sits adjacent to the pathology cataloged in [[Lore - Glitch Tokens]], where rarely- or never-trained vocabulary entries produce erratic completions whenever they get sampled or injected.
**Fix:** Sanitize or escape literal control-token substrings in any untrusted input segment, or — more robust — assemble prompts at the token-ID level so a "fake" control token can never collide with the real one's ID.
**Detection:** Fuzz the input pipeline with literal control-token strings pulled from the tokenizer vocabulary and confirm turn/role boundaries survive intact.

## 4. Prompt-cache busting from prefix instability
**Symptom:** [[Concept - Prompt Caching]] hit rate is far below expectation — you pay near-full per-request prefill cost even though the system prompt, few-shot block, and RAG context are identical call to call.
**Cause:** Cache matching is exact and positional, starting at token 0 of the prefix. A timestamp, request ID, UUID, or a JSON object whose key order isn't fixed changes even one early token, and everything downstream of that point is treated as new — regardless of how much of the actual meaning is unchanged.
**Fix:** Order the prompt so every static element (system prompt, tool schemas, few-shot exemplars) comes first, and push anything variable — the current date if truly required, the user turn, retrieved-doc IDs — to the very end. Serialize JSON with a fixed key order.
**Detection:** Monitor the provider's reported cache-read token count per call (Anthropic and OpenAI both surface it) and alert when hit rate drops below the endpoint's expected baseline.

## 5. Trailing whitespace shifts the model onto a different token boundary
**Symptom:** A prompt edit that looks purely cosmetic — adding or removing a trailing newline or space — changes the completion: an extra leading space, a broken word start, an unexpected first token.
**Cause:** [[Concept - Byte-Pair Encoding]] tokenizes `" word"` and `"word"` as two different token IDs in most modern byte-level BPE schemes, because the leading space is folded into the token itself. A trailing space or newline at the end of a prompt changes which token ID the model actually conditions on for its first generated token, since generation resumes from wherever the prefix's tokenization landed, not from the character boundary a human reads.
**Fix:** Strip trailing whitespace deterministically before sending, and standardize newline counts between every prompt section.
**Detection:** Inspect the last few token IDs of the encoded prompt (not the raw string) in a debugging harness whenever completion quality looks suspicious for no content reason.

## 6. Few-shot exemplars formatted differently from the live query teach the wrong pattern
**Symptom:** Adding few-shot examples makes accuracy worse than zero-shot, or the model copies an exemplar's formatting quirk — an odd delimiter, a wrong field name — into its answer for the live input.
**Cause:** In-context learning is highly sensitive to surface form. If exemplars use `Q:`/`A:` and the live query uses `Question:`/`Answer:`, or exemplars use JSON without trailing commas that the live prompt happens to include, the model treats the live turn as a distributional break rather than "one more of the same" and imitates whatever pattern is most locally salient instead of the intended task.
**Fix:** Route exemplars and the live query through the exact same formatting function; never hand-format one and generate the other programmatically.
**Detection:** Diff the rendered exemplar block against the rendered live-query block, ignoring content, to confirm structural identity.

## 7. "Do not X" negations underperform positive instructions
**Symptom:** A system prompt says "do not use bullet points" or "do not mention pricing," and the model does it anyway, more often than when the same constraint is phrased positively.
**Cause:** Negation is weakly and inconsistently represented in autoregressive language models — the token sequence "do not use bullet points" still shares heavy surface and semantic overlap with "use bullet points," and next-token prediction has no hard logical negation operator; it's a soft distributional nudge, not an enforced rule. This tracks the broader instruction-sensitivity picture in [[Concept - Prompt Formatting and Sensitivity]] rather than resting on one specific paper.
**Fix:** State the desired positive behavior directly ("write your answer as 2-3 prose paragraphs" rather than "don't use bullet points"), and reserve hard negatives for structural sections you can also validate programmatically.
**Detection:** A/B the positive vs. negative phrasing on your eval set ([[Concept - Prompt Evaluation and Versioning]]) — the failure-rate gap is usually large enough to see on a few hundred examples.

## 8. Markdown code fences around JSON break naive parsers
**Symptom:** `json.loads()` (or a schema validator) throws on a response that visually looks like valid JSON.
**Cause:** Instruction-tuned models default to wrapping code-shaped output in triple-backtick fences (` ```json ... ``` `) because that's the dominant training-data convention for presenting code and JSON in chat UIs — a strong stylistic prior, not a model bug, but it breaks any parser expecting bare JSON.
**Fix:** Instruct explicitly to output raw JSON with no markdown fences, and defensively strip leading/trailing triple-backtick blocks in the parsing layer regardless (see [[Playbook - Reliable Structured Output]]) — the instruction alone is not 100% reliable, so treat stripping as mandatory, not an edge case.
**Detection:** Track parse-failure rate as a first-class metric rather than an exception you catch and ignore; a nonzero baseline of fence-wrapped responses is normal and should be handled by default.

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
