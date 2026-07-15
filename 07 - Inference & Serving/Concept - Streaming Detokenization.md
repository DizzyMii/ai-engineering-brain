---
tags: [concept, domain/inference-serving, level/core]
aliases: [incremental detokenization, token streaming]
summary: "Reassembling correct UTF-8 text from a streamed token-ID sequence, where multi-byte characters and stop strings straddle token boundaries."
---

# Concept - Streaming Detokenization

> **One-paragraph hook:** Every serving stack emits one token ID per decode step, but the client wants readable text — and "token" and "character" are not the same unit. Streaming detokenization is the unglamorous logic that reassembles correct UTF-8 text, chunk by chunk, from an autoregressive stream of IDs, and it is where a surprising share of "model bugs" actually live: mojibake emoji, doubled spaces, leaked stop tokens, and tool-call syntax bleeding into a chat UI are almost always detokenizer bugs, not [[Concept - Sampling and Decoding Parameters]] or model bugs.

## The mechanism

Byte-level BPE (the GPT-2 lineage, Radford et al. 2019) doesn't tokenize characters — it tokenizes byte sequences, remapped through a byte-to-printable-unicode table so [[Concept - Byte-Pair Encoding]] merges can operate over a clean alphabet. A UTF-8 emoji (4 bytes) or a CJK glyph (3 bytes) can straddle 2–4 separate tokens. Decode any one of those tokens in isolation and you're UTF-8-decoding a partial byte sequence: the result is a `U+FFFD` replacement character or a hard decode exception, not the intended glyph.

The correct approach keeps a running byte buffer instead of a running string buffer:

```python
buffer = bytearray()
for token_id in token_stream:
    buffer += vocab.id_to_bytes(token_id)
    text, n_consumed = decode_maximal_valid_utf8_prefix(buffer)
    if text:
        yield text
    buffer = buffer[n_consumed:]      # keep the incomplete tail
```

`decode_maximal_valid_utf8_prefix` scans from the end of the buffer for a lead byte that promises more continuation bytes than are currently present, and holds that tail back until the next token supplies the missing bytes. Get this wrong — decode each token independently and concatenate — and multi-byte glyphs flicker or corrupt mid-stream.

SentencePiece (Kudo & Richardson 2018) adds a second wrinkle: it encodes a leading space as a meta-space marker, `▁` (U+2581), prepended to the token that starts a new word. An incremental decoder has to decide, per chunk, whether that marker corresponds to a real space to emit now or was already accounted for by the previous chunk's trailing whitespace — get the reconciliation wrong and streamed output has systematically doubled or missing spaces that the non-streamed decode of the identical generation does not.

Stop strings compound the problem because they're matched against the **detokenized text**, not the token IDs — a pattern like `"\n\n"` or an agent's `"</tool>"` tag has no guarantee of aligning to a token boundary; the BPE merge table was optimized for compression, not for keeping semantically meaningful strings atomic. So the server must keep a small trailing look-back buffer of already-detokenized text, check on every new chunk whether the tail matches or partially matches a configured stop string, hold back a partial match in case the next token completes it, and — on a full match — trim the emitted stream back to the position before the stop string and terminate. An off-by-one in that trim either leaks a stop-string fragment into visible output or truncates one legitimate character too early.

Finally, special and added tokens — BOS, EOS, tool-call tags, `<think>...</think>` reasoning delimiters — must never reach the user-visible string but must survive for whatever code parses tool calls or strips reasoning traces. `skip_special_tokens=True`-style flags handle registered special tokens; a custom tag added only at the chat-template level, without being registered in the tokenizer's special-token set, sails straight through that filter.

## In practice

Hugging Face `tokenizers`' `decode_stream` implements the byte-buffer approach directly. vLLM's OpenAI-compatible server runs an incremental detokenizer per request that does buffered byte decode plus tail matching against `stop`/`stop_token_ids`. llama.cpp's HTTP server has shipped multiple fixes specifically for partial multi-byte token flushing in its streaming path. The relevant server-side knobs across frameworks are `skip_special_tokens`, `stop` / `stop_token_ids`, and (in some engines) `include_stop_str_in_output` — a chat app that wants to show a live "thinking" indicator has to *not* strip `<think>` at the raw-token level and instead parse and filter it in application code, and conflating those two layers is a common source of leaked control tokens.

## Failure modes

- **Flickering replacement glyphs / mojibake on emoji and CJK text** — decoding tokens independently instead of buffering bytes; detect by round-tripping known multi-byte strings through the streaming path and diffing against a non-streamed decode of the same generation.
- **Stop sequence visible in output, or the last character truncated** — missing or mis-sized look-back buffer, or an off-by-one trim; catch it with a smoke test whose stop string is deliberately chosen to straddle a token boundary.
- **Doubled or missing spaces after streaming that aren't present in the non-streamed decode** — mishandled SentencePiece meta-space reconciliation at chunk boundaries.
- **Tool-call delimiters or reasoning tags shown raw to end users** — a template-level tag that was never registered as a special token, so `skip_special_tokens` doesn't touch it.
- Test suites that only exercise short ASCII generations with no stop strings will pass while every one of these ships to production silently — the failure surface is specifically long streams with multi-byte content and boundary-straddling stops, exactly the traffic dev testing tends to skip.

## The non-obvious

None of these are model bugs, and none of them are visible to an eval that scores only the final, fully-materialized text — they exist exclusively in the byte-by-byte streaming path. A serving stack can pass every batch/offline eval and still be silently broken for every real chat user, because production traffic streams and most eval harnesses don't. The cheap, durable fix: treat the non-streaming decode of a generation as the correctness oracle and assert the streamed output is byte-identical to it in CI, on inputs chosen to straddle multi-byte characters and stop strings on purpose.

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
