---
tags: [concept, domain/prompting-context, level/core]
aliases: [ChatML, control tokens, conversation templates, apply_chat_template]
summary: "The literal token sequence a model was trained on for chat — get the template wrong and quality tanks silently, with no error."
---
> **One-paragraph hook:** A chat model was never trained on "a system message, then a user message, then an assistant message" as an abstract concept — it was trained on one exact string of tokens with specific markers in specific positions. The chat template is the code that reconstructs that exact string from a `{role, content}` list. Get the template right and the model behaves as tested; get it subtly wrong — a missing newline, a doubled BOS token, the wrong model's format — and the model degrades with zero error message, because there is no validator checking that your string matches what post-training actually saw.

## The mechanism

A chat template serializes a list of role-tagged messages into the literal token sequence the model saw during [[Concept - Supervised Fine-Tuning (SFT)]]. Every major model family has its own, and they are not interchangeable:

```text
# ChatML (OpenAI-style; also Qwen, many open models)
<|im_start|>system
You are a helpful assistant.<|im_end|>
<|im_start|>user
What's 2+2?<|im_end|>
<|im_start|>assistant

# Llama 2
[INST] <<SYS>>
You are a helpful assistant.
<</SYS>>

What's 2+2? [/INST]

# Llama 3
<|start_header_id|>system<|end_header_id|>

You are a helpful assistant.<|eot_id|><|start_header_id|>user<|end_header_id|>

What's 2+2?<|eot_id|><|start_header_id|>assistant<|end_header_id|>

```

The markers — `<|im_end|>`, `[INST]`, `<|eot_id|>` — are **special/control tokens**: single entries in the vocabulary via [[Concept - Byte-Pair Encoding]], not the literal characters. This distinction matters because a tokenizer's encode path decides, based on its configuration, whether a matching substring in raw input gets mapped to that single control-token ID or split into ordinary sub-word tokens. Hugging Face's `apply_chat_template` (a Jinja template shipped with the tokenizer) is the source of truth for constructing this string correctly — call it with `add_generation_prompt=True` to append the assistant's opening header, which puts the model in-role and ready to decode a response rather than continuing the user's turn.

BOS/EOS handling is the most common silent bug surface: many templates prepend a beginning-of-sequence token themselves, and if your calling code *also* prepends one, you get a double BOS — a token sequence the model never saw in training, which measurably degrades output quality with no exception thrown. The fix is procedural, not technical: let the template own all special tokens, and never hand-add BOS/EOS around output from `apply_chat_template`.

## In practice

```python
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")
messages = [
    {"role": "system", "content": "You are terse."},
    {"role": "user", "content": "2+2?"},
]
prompt = tok.apply_chat_template(
    messages, tokenize=False, add_generation_prompt=True
)
```

Before Jinja-based templates were standardized in the tokenizer config (roughly 2023-2024), the ecosystem's tribal solution was `lm-sys`'s FastChat `conversation.py` registry (the project behind Vicuna and Chatbot Arena, documented in Zheng et al. 2023) — a hand-maintained Python dictionary mapping model name to hardcoded format string, because every new model shipped its own incompatible convention and there was no other source of truth. `apply_chat_template` replaced that folklore with a machine-readable spec shipped alongside the weights, but the underlying problem — one wrong template per model family — never went away, it just moved from "everyone maintains their own registry" to "read the field from the tokenizer config."

Base checkpoints need different handling entirely: a base model was never trained to interpret `<|im_start|>` as structure, so applying a chat template to it doesn't invoke chat behavior — it just adds tokens the model treats as arbitrary text, usually producing a worse completion than a plain few-shot prompt would. Only instruct/chat checkpoints have the template semantics trained in.

Leaving the assistant's turn open with no closing EOS lets you seed the reply directly — see [[Snippet - Prefilling the Assistant Turn]] for the mechanics of forcing a JSON object open or skipping a "Sure, here is..." preamble by continuation rather than instruction.

## Failure modes

- **Template mismatch after a model swap.** Serving a new model with the old model's template (or with none) produces no error — just silently degraded output. Detection: gate every model change on an eval regression, because nothing else will catch it.
- **Double BOS.** Template adds one, caller adds another. Detection: decode the final token IDs and check the literal leading tokens rather than trusting the string looks right.
- **Whitespace/newline drift.** Missing or extra blank lines relative to the exact training format (Llama 3's header format is newline-sensitive) push the token sequence off-distribution in ways that are invisible when eyeballing rendered text but very visible in the token IDs.
- **EOS never emitted.** If the template or a fine-tune corrupted the model's association between "done" and the end-of-sequence token, generation runs to `max_tokens` every time instead of stopping naturally — a detectable pattern (every response hits the length cap) worth alerting on, aggregated further in [[Gotchas - Chat Template Bugs]].
- **Stripped system role.** Some providers or older templates silently fold the system message into the first user turn; if your prompt depends on the system/user distinction for precedence (see [[Concept - System Prompts]]), that distinction can vanish without any indication.

## The non-obvious

The dangerous edge case is at the boundary between "special token" and "arbitrary user text": because tokenizers look up control-token strings by exact match during encoding, a pipeline that builds a prompt by naively concatenating a system message with raw, untrusted user input — then hands the whole string to a plain tokenizer without disabling special-token parsing — can let a user's message containing the literal substring `<|im_start|>assistant` get encoded into the *actual* role-switch control token, not an inert string. That's a structural role-injection vector that has nothing to do with semantic prompt injection; it's a tokenization bug. The fix is procedural: always build prompts through the structured `{role, content}` message-list API and let the template/tokenizer own special-token boundaries, never through raw string concatenation of untrusted content — the same discipline [[Gotchas - Prompt Formatting and Tokenization]] catalogs for sanitizing control-token strings in user input.

## Connections
- [[Concept - Byte-Pair Encoding]] — special tokens are single vocab IDs from this tokenizer, not literal characters, which is the root of both the template mechanism and its injection failure mode.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the training stage where a model actually learns to interpret template markers as structure; base models never see this step.
- [[Concept - System Prompts]] — the semantic content carried inside the template's system role marker; this note covers the token-level container, that one covers what goes in it.
- [[Snippet - Prefilling the Assistant Turn]] — exploits the open assistant header this note describes to seed and constrain generation.
- [[Gotchas - Prompt Formatting and Tokenization]] — the aggregated pitfall list (double BOS, whitespace drift, control-token injection) this note's failure modes feed into.
- [[Lore - Glitch Tokens]] — the pathological extreme of tokenizer/vocab mismatches, relevant when special or under-trained tokens behave unpredictably.
- [[Playbook - Reliable Structured Output]] — depends on correct template handling (assistant prefill, generation-prompt placement) as a prerequisite step.
- [[Gotchas - Chat Template Bugs]] — the deeper, unicorn-tier catalog of exactly how template handling breaks in real fine-tuning and serving pipelines.

## Sources
- Touvron et al. (2023) — "Llama 2: Open Foundation and Fine-Tuned Chat Models." Defines the `[INST]`/`<<SYS>>` template format.
- Dubey et al. (2024) — "The Llama 3 Herd of Models." Defines the `<|start_header_id|>`/`<|eot_id|>` header-based template format.
- Zheng et al. (2023) — "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena." The FastChat/`lm-sys` project behind this paper maintained the pre-standardization, per-model conversation-template registry that `apply_chat_template` later replaced.
