---
tags: [concept, domain/inference-serving, level/core]
aliases: [incremental detokenization, token streaming]
summary: "Reassembling correct UTF-8 text from a streamed token-ID sequence, where multi-byte characters and stop strings straddle token boundaries."
---

# Concept - Streaming Detokenization

> **One-paragraph hook:** A serving stack emits one token ID per decode step. The client wants readable text, and a token isn't a character. Streaming detokenization is the unglamorous code that rebuilds correct UTF-8, chunk by chunk, from an autoregressive stream of IDs. A surprising share of "model bugs" live here: mojibake emoji, doubled spaces, leaked stop tokens, tool-call syntax bleeding into a chat UI. Those are almost always detokenizer bugs, not [[Concept - Sampling and Decoding Parameters]] or model bugs.

## The mechanism

Byte-level BPE (the GPT-2 lineage, Radford et al. 2019) tokenizes byte sequences, not characters. The bytes are remapped through a byte-to-printable-unicode table so [[Concept - Byte-Pair Encoding]] merges can work over a clean alphabet. A UTF-8 emoji (4 bytes) or a CJK glyph (3 bytes) can straddle 2–4 separate tokens. Decode one of those tokens alone and you're UTF-8-decoding a partial byte sequence, which gives you a `U+FFFD` replacement character or a hard decode exception instead of the glyph.

The fix is to keep a running byte buffer instead of a running string buffer:

```python
buffer = bytearray()
for token_id in token_stream:
    buffer += vocab.id_to_bytes(token_id)
    text, n_consumed = decode_maximal_valid_utf8_prefix(buffer)
    if text:
        yield text
    buffer = buffer[n_consumed:]      # keep the incomplete tail
```

`decode_maximal_valid_utf8_prefix` scans back from the end of the buffer for a lead byte that promises more continuation bytes than are present, and holds that tail until the next token brings the missing bytes. Decode each token independently and concatenate, and multi-byte glyphs flicker or corrupt mid-stream.

SentencePiece (Kudo & Richardson 2018) adds a second wrinkle. It encodes a leading space as a meta-space marker, `▁` (U+2581), on the token that starts a new word. An incremental decoder has to decide per chunk whether that marker is a real space to emit now or one the previous chunk's trailing whitespace already covered. Reconcile it wrong and the streamed output has doubled or missing spaces that the non-streamed decode of the same generation doesn't.

Stop strings make it worse, because they're matched against **detokenized text**, not token IDs. Nothing guarantees that `"\n\n"` or an agent's `"</tool>"` tag lines up with a token boundary; the BPE merge table was built for compression and doesn't keep meaningful strings atomic. So the server keeps a small look-back buffer of already-detokenized text. On every new chunk it checks whether the tail matches or partially matches a configured stop string, holds back a partial match in case the next token completes it, and on a full match trims the emitted stream back to just before the stop string and terminates. An off-by-one in that trim either leaks a fragment of the stop string or cuts one legitimate character too early.

Special and added tokens (BOS, EOS, tool-call tags, `<think>...</think>` reasoning delimiters) must never reach the user-visible string, but they have to survive for whatever code parses tool calls or strips reasoning traces. `skip_special_tokens=True`-style flags handle registered special tokens. A custom tag added only in the chat template, never registered in the tokenizer's special-token set, goes straight past that filter.

## In practice

Hugging Face `tokenizers` implements the byte-buffer approach directly in `decode_stream`. vLLM's OpenAI-compatible server runs an incremental detokenizer per request that does buffered byte decode plus tail matching against `stop`/`stop_token_ids`. llama.cpp's HTTP server has shipped several fixes for partial multi-byte token flushing in its streaming path.

The server-side knobs across frameworks are `skip_special_tokens`, `stop` / `stop_token_ids`, and in some engines `include_stop_str_in_output`. A chat app that wants a live "thinking" indicator must *not* strip `<think>` at the raw-token level; it has to parse and filter it in application code. Mixing up those two layers is a common source of leaked control tokens.

## Failure modes

- **Flickering replacement glyphs / mojibake on emoji and CJK text.** Tokens decoded independently instead of buffering bytes. Round-trip known multi-byte strings through the streaming path and diff against a non-streamed decode of the same generation.
- **Stop sequence visible in output, or the last character truncated.** The look-back buffer is missing or mis-sized, or the trim is off by one. Catch it with a smoke test whose stop string deliberately straddles a token boundary.
- **Doubled or missing spaces after streaming** that the non-streamed decode doesn't have. SentencePiece meta-space reconciliation is broken at chunk boundaries.
- **Tool-call delimiters or reasoning tags shown raw to users.** A template-level tag was never registered as a special token, so `skip_special_tokens` ignores it.
- Test suites that only run short ASCII generations with no stop strings will pass while every one of these ships silently. The failure surface is long streams with multi-byte content and stops that straddle boundaries, which is the traffic dev testing tends to skip.

## The non-obvious

None of these are model bugs, and an eval that scores only the final, fully materialized text can't see them. They exist only in the byte-by-byte streaming path. A serving stack can pass every batch or offline eval and still be broken for every real chat user, because production traffic streams and most eval harnesses don't. The cheap fix that lasts: use the non-streaming decode of a generation as the correctness oracle, and assert in CI that the streamed output is byte-identical to it, on inputs picked to straddle multi-byte characters and stop strings.

## Connections

- [[Concept - Byte-Pair Encoding]] — the merge rules that decide token boundaries are exactly why multi-byte characters and stop strings can straddle a token.
- [[Concept - Sampling and Decoding Parameters]] — detokenization runs one step behind the sampler in the same decode loop; the loop only advances once both have executed.
- [[Concept - The Inference Request Lifecycle]] — streaming detokenization is the last stage before the client, sitting between the sampler and the SSE/streaming transport.
- [[Gotchas - LLM Serving in Production]] — streaming corruption and stop-handling bugs are named pitfalls collected there.
- [[Concept - Token Healing]] — the mirror-image problem on the way in: token-boundary mismatch at the prompt edge rather than the generation edge.
- [[Concept - Constrained Decoding]] — grammar-constrained generation hits the same token/character alignment problem, enforced forward instead of detected backward.
- [[Concept - Tool Use and Function Calling]] — tool-call syntax is exactly the special-token content that must be parsed but never shown raw.
- [[Playbook - Reliable Structured Output]] — structured-output pipelines depend on correct incremental parsing of a streamed, detokenized string.

## Sources

- Radford et al. (2019) — "Language Models are Unsupervised Multitask Learners" (GPT-2). Introduced byte-level BPE, the vocabulary scheme whose byte/character mismatch is the root cause here.
- Kudo & Richardson (2018) — "SentencePiece: A simple and language independent subword tokenizer." Introduced the meta-space marker convention that incremental decoders must reconcile across streamed chunks.
