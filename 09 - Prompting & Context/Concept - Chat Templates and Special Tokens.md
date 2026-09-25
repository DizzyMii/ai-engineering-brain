---
tags: [concept, domain/prompting-context, level/core]
aliases: [ChatML, control tokens, conversation templates, apply_chat_template]
summary: "The literal token sequence a model was trained on for chat — get the template wrong and quality tanks silently, with no error."
---
> **One-paragraph hook:** A chat model was trained on one specific string of tokens with specific markers in specific positions, not on the abstract idea of "system message, then user, then assistant". The chat template is the code that rebuilds that string from a `{role, content}` list. Get it right and the model behaves as tested. Get it slightly wrong (a missing newline, a doubled BOS token, another model's format) and the model degrades with no error message, because nothing checks that your string matches what post-training saw.

## The mechanism

A chat template serializes a list of role-tagged messages into the literal token sequence the model saw during [[Concept - Supervised Fine-Tuning (SFT)]]. Every major model family has its own, and you can't swap them:

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

Markers like `<|im_end|>`, `[INST]` and `<|eot_id|>` are **special/control tokens**, each a single vocabulary entry via [[Concept - Byte-Pair Encoding]], not the literal characters. That matters because the tokenizer's encode path, depending on its configuration, either maps a matching substring in raw input to the single control-token ID or splits it into ordinary sub-word tokens. Hugging Face's `apply_chat_template` (a Jinja template shipped with the tokenizer) is the source of truth for building the string. Call it with `add_generation_prompt=True` to append the assistant's opening header, which puts the model in role to write a response instead of continuing the user's turn.

BOS/EOS handling is where most silent bugs live. Many templates prepend a beginning-of-sequence token themselves. If your code *also* prepends one, you get a double BOS, a sequence the model never saw in training, and output quality drops measurably with no exception. The fix is procedural: the template owns all special tokens, and you never hand-add BOS/EOS around `apply_chat_template` output.

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

Before Jinja templates were standardized in the tokenizer config (roughly 2023-2024), the ecosystem relied on `lm-sys`'s FastChat `conversation.py` registry (the project behind Vicuna and Chatbot Arena, documented in Zheng et al. 2023). It was a hand-maintained Python dictionary from model name to hardcoded format string, since every new model shipped its own incompatible convention and nothing else recorded them. `apply_chat_template` replaced that with a machine-readable spec shipped with the weights. The underlying problem, a different template per model family, is still there. It moved from "everyone maintains their own registry" to "read the field from the tokenizer config."

Base checkpoints are different. A base model was never trained to read `<|im_start|>` as structure, so a chat template doesn't trigger chat behavior. It just adds tokens the model treats as arbitrary text, and the completion is usually worse than a plain few-shot prompt would give. Only instruct/chat checkpoints have template semantics trained in.

Leaving the assistant turn open, with no closing EOS, lets you seed the reply. [[Snippet - Prefilling the Assistant Turn]] shows how to force a JSON object open or skip a "Sure, here is..." preamble by continuation instead of instruction.

## Failure modes

- **Template mismatch after a model swap.** Serving a new model with the old model's template (or none) gives no error, only silently worse output. Detection: gate every model change on an eval regression. Nothing else will catch it.
- **Double BOS.** Template adds one, caller adds another. Detection: decode the final token IDs and check the leading tokens; a string that looks right proves nothing.
- **Whitespace/newline drift.** Missing or extra blank lines compared with the training format (Llama 3's header format is newline-sensitive) push the sequence off-distribution. You can't see it in rendered text, but it's obvious in the token IDs.
- **EOS never emitted.** If the template or a fine-tune broke the model's link between "done" and the end-of-sequence token, generation runs to `max_tokens` every time. Every response hitting the length cap is easy to detect and worth alerting on; more in [[Gotchas - Chat Template Bugs]].
- **Stripped system role.** Some providers and older templates silently fold the system message into the first user turn. If your prompt relies on the system/user split for precedence (see [[Concept - System Prompts]]), that split can disappear without any sign.

## The non-obvious

The dangerous case sits between "special token" and "arbitrary user text". Tokenizers find control-token strings by exact match during encoding. Say a pipeline builds the prompt by concatenating a system message with raw, untrusted user input and hands the result to a plain tokenizer with special-token parsing still on. A user message containing the literal substring `<|im_start|>assistant` then gets encoded as the *actual* role-switch control token. That's role injection through tokenization, a bug unrelated to semantic prompt injection. The fix is procedural: build prompts through the structured `{role, content}` message-list API and let the template and tokenizer own special-token boundaries. Never concatenate untrusted content into a raw string. [[Gotchas - Prompt Formatting and Tokenization]] covers the same discipline for sanitizing control-token strings in user input.

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
