---
tags: [snippet, domain/post-training, level/core]
aliases: [chat loss masking, -100 masking, assistant-only loss]
summary: "Tokenizes a multi-turn chat example and builds a label mask so cross-entropy loss lands only on assistant tokens and EOS."
---

## What it does
Tokenizes a multi-turn conversation with a model's [[Concept - Chat Templates and Special Tokens|chat template]] and builds `input_ids`/`labels`. Every non-assistant token (system, user, role headers, padding) gets PyTorch's `-100` ignore index; only assistant content and its terminal token carry loss. It tokenizes **per turn** instead of tokenizing the whole concatenated string, because BPE merges can cross a turn boundary and silently move where the assistant span starts.

**Dependencies:** `transformers>=4.44` (for tokenizers that ship `return_assistant_tokens_mask`; the manual fallback below works with any version), `torch>=2.0`.

**Expected output:** a printed table of `(token, label)` pairs, with `-100` on system/user tokens and the real token id on assistant tokens, plus an assertion that at least one token is unmasked.

```python
import torch
from transformers import AutoTokenizer

IGNORE_INDEX = -100  # torch.nn.CrossEntropyLoss default ignore_index

MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"  # any model with a chat template

conversation = [
    {"role": "system", "content": "You are a concise assistant."},
    {"role": "user", "content": "What is the capital of France?"},
    {"role": "assistant", "content": "Paris."},
    {"role": "user", "content": "And Germany?"},
    {"role": "assistant", "content": "Berlin."},
]


def build_labels_per_turn(tokenizer, messages: list[dict]) -> tuple[list[int], list[int]]:
    """Tokenize incrementally, turn by turn, and mask every non-assistant span.

    Re-tokenizing messages[:k] at each step (rather than tokenizing each turn's
    text in isolation) keeps every prefix consistent with how the tokenizer
    would encode it in context, which is what avoids boundary re-merge bugs.
    """
    input_ids: list[int] = []
    labels: list[int] = []
    prev_len = 0

    for i in range(1, len(messages) + 1):
        # add_generation_prompt=False: we want the raw turn boundary, not an
        # appended assistant header, at every intermediate step.
        prefix_ids = tokenizer.apply_chat_template(
            messages[:i], tokenize=True, add_generation_prompt=False
        )
        new_ids = prefix_ids[prev_len:]
        input_ids.extend(new_ids)

        if messages[i - 1]["role"] == "assistant":
            labels.extend(new_ids)  # unmasked: this span carries loss
        else:
            labels.extend([IGNORE_INDEX] * len(new_ids))

        prev_len = len(prefix_ids)

    return input_ids, labels


def sanity_check(tokenizer, input_ids: list[int], labels: list[int]) -> None:
    n_unmasked = sum(1 for l in labels if l != IGNORE_INDEX)
    assert n_unmasked > 0, "all labels are -100 — no assistant turns were unmasked"
    assert len(input_ids) == len(labels)

    print(f"{'token':>16} | label")
    print("-" * 28)
    for tok_id, lab in zip(input_ids, labels):
        tok_str = tokenizer.decode([tok_id]).replace("\n", "\\n")
        print(f"{tok_str!r:>16} | {lab if lab == IGNORE_INDEX else tok_id}")
    print(f"\n{n_unmasked}/{len(labels)} tokens carry loss "
          f"({n_unmasked / len(labels):.1%})")


if __name__ == "__main__":
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    ids, labels = build_labels_per_turn(tokenizer, conversation)
    sanity_check(tokenizer, ids, labels)

    input_ids_t = torch.tensor([ids])
    labels_t = torch.tensor([labels])
    # feed straight into model(input_ids=input_ids_t, labels=labels_t) —
    # HF's forward pass shifts labels internally and applies CrossEntropyLoss
    # with ignore_index=-100 by default.
```

## Why it's written this way
- **Per-turn re-tokenization, not string concatenation plus offset search.** Tokenizing `messages[:i]` at every step and diffing against the previous prefix length costs a bit more than tokenizing the full string once and searching the decoded text for turn boundaries. But it's exact. [[Concept - Byte-Pair Encoding|BPE]] can merge the last token of a user turn with the first token of the next role header, and a naive string split then silently puts that merged token's loss on the wrong side of the boundary.
- **Why `-100` and not `0` or a padding token id.** `-100` is the default `ignore_index` of `torch.nn.CrossEntropyLoss`. Any real token id would either compute a spurious loss against that id or force you to pass a non-default `ignore_index` everywhere downstream, which breaks the first time someone refactors the training loop.
- **EOS/eot stays unmasked because it ends the assistant turn.** The chat template puts it inside the assistant span (e.g. Llama-3's `<|eot_id|>`), so the per-turn loop includes it in the unmasked range automatically. If a custom masking scheme trims the last token off each assistant span "to be safe," the model never learns to stop and runs to `max_new_tokens` at inference (see [[Gotchas - Chat Template Bugs]]).
- **Keep the hard assertion (`n_unmasked > 0`).** A silently all-masked batch (a role-name typo, say, or a template that doesn't tell `assistant` from `user`) trains at loss ≈ 0 with a gradient of zero and no error. It's the most expensive class of SFT bug to debug after the fact, because the loss curve looks like a normal run.

## Connections

- [[Concept - Loss Masking and Sequence Packing]] — the mechanism note this snippet implements; covers why masking matters and how it interacts with packing across multiple examples.
- [[Concept - Chat Templates and Special Tokens]] — the template format (`apply_chat_template`, role delimiters, `add_generation_prompt`) this snippet depends on for correctness (domain 09, cross-domain).
- [[Concept - Supervised Fine-Tuning (SFT)]] — the training stage this label construction feeds; SFT loss is computed exactly on the unmasked spans this snippet produces.
- [[Concept - The Training Loop]] — where `input_ids`/`labels` produced here are consumed by the forward/backward pass (domain 02, cross-domain).
- [[Concept - Byte-Pair Encoding]] — the tokenization mechanism whose merge behavior across turn boundaries is the reason per-turn tokenization is necessary here (domain 04, cross-domain).
- [[Gotchas - Chat Template Bugs]] — the failure catalog (missing EOS, double-BOS, role mismatches) that this snippet's sanity check is designed to catch early.
