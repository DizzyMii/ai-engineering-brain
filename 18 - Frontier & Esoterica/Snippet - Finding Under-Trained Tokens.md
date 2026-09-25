---
tags: [snippet, domain/esoterica, level/unicorn]
aliases: [glitch token detection, Fishing for Magikarp, under-trained token scan, SolidGoldMagikarp detector]
summary: "Scan a model's vocabulary for glitch/under-trained tokens via unembedding statistics, reachability, and a behavioral repeat probe."
---

# Snippet - Finding Under-Trained Tokens

> **What it does:** ranks every vocabulary token by how likely it is to be an under-trained or unreachable "glitch" token (the [[Lore - Glitch Tokens|SolidGoldMagikarp]] class) using cheap unembedding statistics plus a tokenizer round-trip, then confirms the worst offenders behaviorally with a repeat probe. **Deps:** `torch>=2.0`, `transformers>=4.40` (`pip install torch transformers`). **Expected output:** on `gpt2` the tail of the ranking shows reserved byte tokens plus the canonical cluster (`' SolidGoldMagikarp'`, `' petertodd'`, `' TheNitromeFan'`, `'davidjl'`, `' externalToEVA'`, `' guiActiveUn'`). On large-vocab models (Llama, Mistral, Gemma) you get hundreds of candidates, mostly code and multilingual fragments, which is the count [[Checklist - Auditing a Tokenizer for Glitch Tokens|the auditing checklist]] tells you to expect.

```python
"""
Finding under-trained ("glitch") tokens in a causal LM.
Method after Land & Bartolo 2024, "Fishing for Magikarp".
Statistics-first (cheap, whole-vocab), behavior-second (expensive, top suspects only).
"""
import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "gpt2"                                    # any HF causal LM; swap for a large-vocab model to see more
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32).eval()

def z(x):                                         # standardize so heterogeneous signals are comparable
    return (x - x.mean()) / (x.std() + 1e-8)

# 1. OUTPUT SIDE. The unembedding (lm_head) row for a token that was almost
#    never a training target barely gets gradient: its row stays small in norm
#    and drifts toward the mean row -- the model's "unknown token" direction.
W_out = model.get_output_embeddings().weight.detach()          # [V, d]
row_norm = W_out.norm(dim=1)
cos_mean = F.cosine_similarity(W_out, W_out.mean(0, keepdim=True), dim=1)
score = -z(row_norm) + z(cos_mean)                # low norm + high cos-to-mean => suspect

# 2. INPUT SIDE. Only *independent* information when embeddings are untied.
#    GPT-2 and Gemma tie input==output (folding it in would double-count);
#    most Llama variants don't, so a small input-embedding norm is a real 2nd vote.
if not getattr(model.config, "tie_word_embeddings", False):
    W_in = model.get_input_embeddings().weight.detach()
    score = score - z(W_in.norm(dim=1))

# 3. REACHABILITY. A token whose decoded string does not re-encode back to its
#    own id can never be emitted by the tokenizer on any normal input -- a prime
#    glitch candidate, decided without ever running the model.
V = W_out.shape[0]
unreachable = torch.zeros(V, dtype=torch.bool)
for tid in range(V):
    ids = tok.encode(tok.decode([tid]), add_special_tokens=False)
    unreachable[tid] = not (len(ids) == 1 and ids[0] == tid)
score = score + unreachable.float() * 3.0         # unreachable dominates the ranking

# 4. RANK. One argsort over the whole vocab -- no forward pass yet.
worst = torch.argsort(score, descending=True)[:40]
print(f"{'tid':>6} {'score':>6} {'reach':>5}  repr")
for tid in worst.tolist():
    print(f"{tid:>6} {score[tid]:6.2f} {str(not bool(unreachable[tid])):>5}  {tok.decode([tid])!r}")

# 5. BEHAVIORAL CONFIRMATION. Statistics flag candidates; a glitch token is
#    *confirmed* when the model cannot even echo it verbatim (it substitutes,
#    deflects, or emits nonsense). Reserve this expensive step for the tail.
@torch.no_grad()
def can_echo(s):
    prompt = f'Repeat this exactly: "{s}"\nExactly: "'
    ids = tok(prompt, return_tensors="pt").input_ids
    out = model.generate(ids, max_new_tokens=10, do_sample=False,
                         pad_token_id=tok.eos_token_id)
    return s.strip() in tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True)

print("\nbehavioral probe on top reachable suspects:")
for tid in [t for t in worst.tolist() if not unreachable[t]][:8]:
    s = tok.decode([tid])
    print(f"{tid:>6}  echo_ok={can_echo(s)!s:>5}  {s!r}")
```

## Why it's written this way

### Statistics first, behavior second
The screen is free and the probe isn't. The whole-vocab score is one norm, one cosine and one argsort over the `[V, d]` unembedding: O(V·d) with *zero* forward passes, so it ranks a 256k-token vocabulary in milliseconds. Only step 5 runs the model, and only on the few dozen worst tokens. That ordering is the whole idea of Land & Bartolo's "Fishing for Magikarp." You can't afford a generative probe on 256k tokens, but you can afford a matmul-free statistic on all of them and a `generate()` on the tail.

### Three signals that fail differently
The unembedding norm and cosine-to-mean catch tokens the model *never learned to predict*. Reachability catches tokens the *tokenizer can never emit*. The behavioral probe catches tokens whose embedding sits in a meaningless region of activation space. A token can trip one and not the others (a rare but fine Unicode glyph has a small unembedding norm and echoes perfectly), so no single signal is trusted alone.

### The tie caveat matters
With `tie_word_embeddings=True` (GPT-2, Gemma), `get_input_embeddings()` and `get_output_embeddings()` return the *same tensor*. Adding the input norm to the score would double-weight one signal and manufacture false confidence. The config-flag guard is the difference between two independent votes and one vote counted twice, and it's the kind of thing that silently corrupts a homegrown detector.

### The stronger, costlier alternative
Land & Bartolo's most discriminative indicator is a token's *maximum predicted probability across a set of eliciting contexts*: a [[Concept - Softmax|softmax over the vocabulary]] at many positions, then the per-token max. It separates under-trained tokens more cleanly than row norms but needs many forward passes. The row statistic here is the cheap proxy that gets you ~90% of the way. Swap it in when a checkpoint's tail is ambiguous.

### Caveats before you act on the list
Legitimately rare tokens (obscure Unicode, deliberately reserved slots, padding rows added after pretraining) look under-trained without being harmful. Thresholds are model-specific; there's no universal cutoff. On large-vocab tokenizers the candidates are dominated by multilingual and code ranges, the same ranges where a [[Concept - Byte-Pair Encoding|BPE]] tokenizer trained on one corpus and deployed on another leaves the most orphaned merges.

## Connections

- [[Lore - Glitch Tokens]] — the discovery story (SolidGoldMagikarp, 2023) this code turns into a repeatable scan; read it for *why* under-trained embeddings misbehave.
- [[Checklist - Auditing a Tokenizer for Glitch Tokens]] — the pre-flight list this snippet is the executable core of; the checklist frames when to run it and what else to verify.
- [[Gotchas - Tokenizer Pathologies]] — glitch tokens are one entry in the broader catalog of failures traceable to tokenization; that note ranks them by how often they bite.
- [[Concept - Byte-Pair Encoding]] — the tokenizer/corpus-frequency mismatch in BPE merges is the root cause of orphaned tokens; a different domain (04) owns the algorithm.
- [[Concept - Softmax]] — the max-predicted-probability refinement is a softmax over the vocabulary; the operator note (domain 02) explains the normalization these tokens sit at the bottom of.

## Sources

- Land & Bartolo (2024) — *Fishing for Magikarp: Automatically Detecting Under-trained Tokens in LLMs.* The method implemented here; found hundreds of under-trained tokens per tokenizer across Llama, Mistral, and Gemma.
- Rumbelow & Watkins (2023) — *SolidGoldMagikarp (plus, prompt generation)*, LessWrong. The original discovery that under-trained GPT-2/3/J tokens produce unspeakable, evasive, and hallucinated outputs.
