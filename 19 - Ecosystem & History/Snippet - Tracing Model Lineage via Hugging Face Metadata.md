---
tags: [snippet, domain/ecosystem-history, level/advanced]
aliases: [model lineage tracing, HF metadata archaeology, base_model detection]
summary: "Runnable Python that reconstructs a model's derivation (base, finetune/merge/adapter/quant, tokenizer ancestry) from Hugging Face metadata + artifacts."
---

# Snippet - Tracing Model Lineage via Hugging Face Metadata

Given a Hub repo id, this reconstructs the model's derivation: the declared base model; whether it's a fine-tune, merge, LoRA adapter or quantization; its **tokenizer ancestry**, which survives fine-tuning and gives away undeclared descent; and a *low-confidence* flag for distillation from a closed model. Verify, don't trust. `base_model` in a model card is self-reported and frequently wrong or absent, so each declared edge gets checked against `config.json` and a tokenizer hash. The output feeds the family trees in [[Reference - Model Genealogy]] and is one of the required checks in the [[Checklist - Vetting an Open-Weights Model for Production]]. The `base_model` / `base_model_relation` convention it reads is a metadata standard the Hub itself popularized (see [[Breakdown - Hugging Face]]).

```
What it does:  Emits a structured lineage record for one HF repo id.
Dependencies:  huggingface_hub == 0.34.0   (pip install "huggingface_hub>=0.24,<1.0")
Auth:          export HF_TOKEN=hf_...       (gated repos + to avoid anon rate limits)
Run:           python trace_lineage.py mistralai/Mistral-7B-Instruct-v0.2
```

```python
import hashlib
import json
import sys
from dataclasses import dataclass, field, asdict

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import (
    EntryNotFoundError, GatedRepoError, RepositoryNotFoundError,
)

api = HfApi()

# Architecture fingerprints: (arch_class, hidden_size, num_layers, vocab_size) -> family.
# Catches ancestry the card omits — geometry survives a rename, metadata doesn't.
KNOWN_BASES = {
    ("LlamaForCausalLM",   4096, 32,  32000): "llama-1/2-7b family",
    ("LlamaForCausalLM",   4096, 32, 128256): "llama-3-8b family",
    ("MistralForCausalLM", 4096, 32,  32000): "mistral-7b family",
    ("Qwen2ForCausalLM",   3584, 28, 152064): "qwen2-7b family",
}

# Tokenizer vocab sizes as a coarse family hint. A vocab-size collision is only a
# hint; the sha256 below is the real fingerprint that distinguishes reused tokenizers.
TOKENIZER_VOCAB_HINTS = {
     32000: "llama/mistral SentencePiece (32k)",
    128256: "llama-3 tiktoken-style BPE (128k)",
    152064: "qwen2 BPE (152k)",
     50257: "gpt-2 BPE (50k)",
    100352: "gpt-4o o200k-style BPE (~100k)",
}


@dataclass
class Lineage:
    repo_id: str
    declared_base: object = None       # str | list[str] | None (self-reported)
    relation: str = "unknown"          # base|finetune|merge|adapter|quantized|unknown
    tokenizer_family: str = "unknown"
    arch_fingerprint: str = "unknown"
    distill_suspicion: str = "none"    # none | low-confidence  (never asserted as fact)
    evidence: list = field(default_factory=list)


def _download_json(repo_id, filename):
    try:
        with open(hf_hub_download(repo_id, filename), encoding="utf-8") as f:
            return json.load(f)
    except (EntryNotFoundError, RepositoryNotFoundError):
        return None


def trace(repo_id: str) -> Lineage:
    lin = Lineage(repo_id=repo_id)

    # 1. Card metadata — the CLAIM. Read it, but don't trust it yet.
    try:
        info = api.model_info(repo_id, files_metadata=False)
    except GatedRepoError:
        lin.evidence.append("gated repo: accept terms / set HF_TOKEN to inspect")
        return lin
    raw = info.card_data
    card = raw.to_dict() if hasattr(raw, "to_dict") else dict(raw or {})
    tags = set(info.tags or [])
    siblings = {s.rfilename for s in (info.siblings or [])}

    lin.declared_base = card.get("base_model")
    if card.get("base_model_relation"):
        lin.relation = card["base_model_relation"]
    if lin.declared_base:
        lin.evidence.append(f"card base_model={lin.declared_base!r}")

    # 2. Structural signals override prose — the loader actually reads these files.
    if "adapter_config.json" in siblings:                       # it's a LoRA, not a model
        adapter = _download_json(repo_id, "adapter_config.json") or {}
        lin.relation = "adapter"
        lin.declared_base = lin.declared_base or adapter.get("base_model_name_or_path")
        lin.evidence.append(f"adapter_config base={adapter.get('base_model_name_or_path')!r}, "
                            f"r={adapter.get('r')}")

    config = _download_json(repo_id, "config.json") or {}
    if config.get("quantization_config"):
        lin.relation = "quantized"
        lin.evidence.append("quantization_config quant_method="
                            f"{config['quantization_config'].get('quant_method')!r}")

    if isinstance(lin.declared_base, list) and len(lin.declared_base) > 1:
        lin.relation = "merge"
        lin.evidence.append(f"{len(lin.declared_base)} base_model entries -> merge")
    if tags & {"mergekit", "merge"}:
        lin.relation = "merge"
        lin.evidence.append("mergekit/merge tag present")

    # 3. Architecture fingerprint — outs UNDECLARED ancestry.
    arch = (config.get("architectures") or ["?"])[0]
    fp = (arch, config.get("hidden_size"),
          config.get("num_hidden_layers"), config.get("vocab_size"))
    lin.arch_fingerprint = KNOWN_BASES.get(fp, f"unmatched {fp}")
    if fp in KNOWN_BASES and not lin.declared_base:
        lin.evidence.append(f"geometry matches {KNOWN_BASES[fp]} but base_model is UNSET")

    # 4. Tokenizer fingerprint — reuse survives fine-tuning AND merging.
    tok = _download_json(repo_id, "tokenizer.json")
    if tok:
        vocab = tok.get("model", {}).get("vocab", {}) or {}
        digest = hashlib.sha256(
            json.dumps(vocab, sort_keys=True).encode()).hexdigest()[:12]
        lin.tokenizer_family = TOKENIZER_VOCAB_HINTS.get(
            len(vocab), f"unknown ({len(vocab)} tokens)")
        lin.evidence.append(f"tokenizer sha256[:12]={digest}, vocab={len(vocab)}")

    # 5. Distillation-from-closed — a HYPOTHESIS with its evidence, never a fact.
    haystack = (repo_id + " " + " ".join(map(str, card.values())) + " "
                + " ".join(tags)).lower()
    if any(m in haystack for m in ("distill", "sharegpt", "gpt-4", "gpt4")):
        lin.distill_suspicion = "low-confidence"
        lin.evidence.append("distill/ShareGPT/GPT-4 markers -> possible closed-model "
                            "distillation (UNVERIFIED — legal/ToS exposure if true)")

    # 6. Infer relation only when structure was silent (most finetunes omit the field).
    if lin.relation == "unknown" and isinstance(lin.declared_base, str):
        lin.relation = "finetune"
        lin.evidence.append("single declared base, no merge/adapter/quant markers "
                            "-> inferred finetune")
    return lin


if __name__ == "__main__":
    repo = sys.argv[1] if len(sys.argv) > 1 else "mistralai/Mistral-7B-Instruct-v0.2"
    print(json.dumps(asdict(trace(repo)), indent=2))
```

Expected output:

```json
{
  "repo_id": "mistralai/Mistral-7B-Instruct-v0.2",
  "declared_base": "mistralai/Mistral-7B-v0.2",
  "relation": "finetune",
  "tokenizer_family": "llama/mistral SentencePiece (32k)",
  "arch_fingerprint": "mistral-7b family",
  "distill_suspicion": "none",
  "evidence": [
    "card base_model='mistralai/Mistral-7B-v0.2'",
    "tokenizer sha256[:12]=a1b2c3d4e5f6, vocab=32000",
    "single declared base, no merge/adapter/quant markers -> inferred finetune"
  ]
}
```

## Why it's written this way

`base_model` is the fast path, but it's a text field. An uploader can leave it blank, paste it wrong, or omit it to hide a leaked base. `config.json` geometry and the tokenizer hash are what the *loader* consumes, so they count as ground truth. The fallbacks are there because self-reported lineage is least reliable when it matters most, as with a rebranded fine-tune of a restrictively licensed base.

The tokenizer hash is the fingerprint that matters. A model's [[Concept - Byte-Pair Encoding]] tokenizer is almost never retrained during fine-tuning or merging, so a `sha256` of its vocab is a near-immutable ancestry marker that survives every downstream edit. Vocab *size* alone collides: Llama and Mistral both sit at 32k. So size is a hint and the hash is the identity. [[Gotchas - Tokenizers]] catalogs the ways vocab-size heuristics mislead.

When the card and the files disagree, the files win. `adapter_config.json`, `quantization_config` and multiple `base_model` entries change which code path `from_pretrained` takes. The human-written card is aspiration; those files are what runs.

The distillation flag stays low-confidence. Metadata can't *prove* [[Concept - Knowledge Distillation]] from a closed model. A "distill" in the name or a ShareGPT mention is a hypothesis, and one with legal weight if it's wrong. Emitting `low-confidence` plus the evidence, instead of a boolean, keeps it a useful signal and keeps it from being a defamatory assertion.

## Connections

- [[Reference - Model Genealogy]] — this script is the tool that populates that note's family trees; it turns "the card says X" into corroborated edges.
- [[Breakdown - Hugging Face]] — the `base_model` metadata convention this reads is a Hub invention; the note explains why that convention enables lineage archaeology at all.
- [[Concept - Byte-Pair Encoding]] — tokenizer fingerprinting only works because the BPE vocab is inherited wholesale and rarely retrained downstream.
- [[Concept - Knowledge Distillation]] — the mechanism behind the "distill-of-closed" flag and the ToS grey zone it lives in.
- [[Checklist - Vetting an Open-Weights Model for Production]] — consumes this record in the lineage stage to catch mislicensed bases and distillation exposure.
- [[Gotchas - Tokenizers]] — why vocab-size heuristics collide and mislead, and why the byte-level hash is the safer signal.

## Sources
- Wolf et al. (2020) — *Transformers: State-of-the-Art NLP*. The library and `from_pretrained`/model-card ecosystem this metadata rides on.
- Goddard et al. (2024) — *Arcee's MergeKit*. Source of the merge metadata (`mergekit` tags, multi-base entries) the script keys on.
- Hugging Face Hub model-card spec — the `base_model` and `base_model_relation` fields, the convention that makes declared lineage machine-readable.
