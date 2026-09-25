---
tags: [moc, domain/esoterica, level/surface]
aliases: []
summary: "Map of training-dynamics anomalies, attention/tokenizer pathologies, long-context extrapolation, and the field's open problems and folklore."
---

# MOC - Frontier & Esoterica

This domain collects the phenomena that don't fit any other domain's story. Training dynamics that break monotonic-loss intuition (grokking, double descent, the lottery ticket). Attention and softmax mechanics that misbehave at scale or over long context. Tokenization pathologies that damage a model's number sense and vocabulary. And the open problems and folklore the field runs on where theory hasn't caught up with practice. A staff engineer reaches for these notes when a model does something the textbook doesn't predict: a loss spike with no obvious cause, a context-extension trick that works without anyone fully knowing why, a token that makes the model hallucinate for no traceable reason. Much of it sits between established mechanism and open research, so several notes are frontier or unicorn tier: documented but not fully understood, or understood but rarely written down outside a lab's internal Slack. Use the domain as connective tissue. Its notes reach into architectures, training and post-training to explain why a phenomenon shows up where it does.

## Start here

- **Surface** → [[Lore - Machine Learning Is Alchemy]] — Rahimi's 2017 NeurIPS speech vs. LeCun's rebuttal, the debate behind why this domain runs on folklore as much as theory.
- **Core** → [[Concept - Double Descent]] — test error rises to a peak at the interpolation threshold, then falls again with more capacity, data, or epochs; breaks the classical bias-variance story.
- **Advanced** → [[Concept - Grokking]] — a network sits at 100% train accuracy and chance validation for ~10^5 steps, then generalizes abruptly; the clearest window into delayed generalization.
- **Frontier** → [[Reference - Open Problems in LLM Engineering]] — the standing unsolved problems in building and understanding LLMs, each with why it's hard and where the real work lives.
- **Unicorn** → [[Lore - Hyperparameter Folklore]] — the war stories and superstitions behind the magic hyperparameters everyone copies without deriving, and the invariances that make copying work anyway.

## Training dynamics and loss-landscape geometry

- [[Concept - Double Descent]] — test error rises to a peak where a model just barely fits its training set, then falls again as capacity, data, or epochs grow past that point.
- [[Concept - Grokking]] — 100% train accuracy while validation stays at chance for ~10^5 steps, then generalization arrives abruptly.
- [[Concept - The Lottery Ticket Hypothesis]] — a dense net's accuracy can be matched by a small subnetwork trained from its own init; most weights exist to make search work, not to fire.
- [[Concept - Mode Connectivity and Flat Minima]] — why independent SGD solutions are connected by low-loss paths, and why flat minima generalize better; the geometry behind model merging.
- [[Snippet - Reproducing Grokking on Modular Addition]] — runnable PyTorch reproduction of the grokking phase transition on (a+b) mod p, with the exact setup that makes it appear.

## Scaling behavior and emergence

- [[Concept - The Emergent Abilities Debate]] — whether LLM capability jumps at scale are real phase transitions or artifacts of discontinuous metrics. Unresolved and safety-relevant.
- [[Concept - Inverse Scaling and U-Shaped Scaling]] — tasks where bigger models get monotonically worse, and the cases where the largest models reverse the trend into a U-shape.

## Attention and softmax mechanics

- [[Concept - Attention Sinks]] — attention heads dump 30-80% of their mass on token 0 regardless of content: softmax's escape valve, and the key to streaming inference.
- [[Concept - Attention Entropy Collapse]] — training instability where attention softmaxes sharpen to one-hot, entropy crashes to zero, and loss diverges; fixed by QK-norm, σReparam, or logit soft-capping.
- [[Concept - The Softmax Bottleneck]] — a single softmax over H·Wᵀ caps expressible next-token distributions at rank d, a capacity ceiling independent of training quality.
- [[Snippet - Softmax-Off-By-One (Quiet Attention)]] — drop-in softmax_1 (+1 in the denominator) that lets attention heads attend to nothing, plus a demo of how it de-pressurizes sinks.

## Tokenization pathologies

- [[Concept - Numeracy and Digit Tokenization]] — how number tokenization sabotages arithmetic: non-compositional digit merges, the 9.11>9.9 bug, and the lab folklore fixes.
- [[Gotchas - Tokenizer Pathologies]] — aggregated failure modes that trace back to tokenization, ordered by how often they bite: boundary merges, double-BOS, digit inconsistency, glitch tokens.
- [[Lore - Glitch Tokens]] — the SolidGoldMagikarp saga: under-trained vocabulary tokens that make LLMs hallucinate, evade, or break, and the tokenizer/corpus mismatch behind them.
- [[Checklist - Auditing a Tokenizer for Glitch Tokens]] — pre-flight checks to catch under-trained, unreachable, and pathological tokens before trusting a tokenizer in training or production.
- [[Snippet - Finding Under-Trained Tokens]] — scan a model's vocabulary for glitch/under-trained tokens via unembedding statistics, reachability, and a behavioral repeat probe.

## Long context and position encoding

- [[Concept - RoPE Extrapolation and Context Extension]] — why RoPE rotation angles beyond the trained context length are out-of-distribution, and the interpolation/NTK/theta tricks that fix it.
- [[Concept - Ring Attention and Extreme Context]] — sharding attention across a device ring so context length scales with GPU count, no device ever materializing the full KV cache.
- [[Breakdown - YaRN]] — the RoPE context-extension method that became the community default: wavelength-aware (NTK-by-parts) interpolation plus a closed-form attention-temperature correction.
- [[Decision - Choosing a Context Extension Method]] — pick among Position Interpolation, NTK scaling, YaRN, LongRoPE, and native long-context pretraining by target length and budget.
- [[Playbook - Extending a Model's Context Window]] — end-to-end procedure to extend a RoPE model's context window without wrecking short-context quality or blowing the serving budget.
- [[Gotchas - Long-Context Failure Modes]] — how million-token context windows fail silently: lost-in-the-middle, fake NIAH passes, RoPE drift, dilution, KV-quant, cost cliffs.

## Generation and alignment pathologies

- [[Concept - Neural Text Degeneration and Repetition Loops]] — why maximization decoding drives well-trained LLMs into self-reinforcing repetitive loops, and why nucleus sampling became the default fix.
- [[Concept - Mode Collapse in RLHF]] — preference optimization narrows the policy onto a few high-reward completions, trading diversity for reward; the source of GPT-isms.
- [[Concept - The Reversal Curse]] — LLMs trained on "A is B" fail to infer "B is A": directional fact storage in weights and its knowledge-editing consequences.

## Efficiency at the extreme edge

- [[Breakdown - BitNet b1.58]] — Microsoft's ternary-weight LLM: weights in {−1,0,+1} at ~1.58 bits, matmuls become add/subtract, trained QAT-from-scratch; parity claims strongest at small-to-mid scale.
- [[Concept - Massive Activations and Outlier Features]] — a few hidden-state dims carry activations 20-1000x the rest, act as a learned bias the model depends on, and wreck naive quantization.

## Field folklore and open problems

- [[Reference - Architecture Numerology]] — lookup table of the magic constants in transformer design (FFN ratios, head dims, vocab padding, RoPE bases, Adam betas, divisibility rules) and the mechanical reason for each.
- [[Reference - Open Problems in LLM Engineering]] — standing unsolved problems in building and understanding LLMs, each with why it's hard and where the real work lives.
- [[Lore - Hyperparameter Folklore]] — the war stories and superstitions behind the magic hyperparameters everyone copies without deriving, and the invariances that make copying work.
- [[Lore - Machine Learning Is Alchemy]] — Rahimi's 2017 "ML is alchemy" NeurIPS speech and LeCun's rebuttal frame why this domain runs on folklore, not theory.

## Adjacent domains

- [[MOC - Architectures]] — attention sinks, RoPE extrapolation, and ring attention all extend architecture primitives (attention, position encoding) defined there.
- [[MOC - Post-Training]] — mode collapse in RLHF and the reversal curse are failure modes of the alignment and fine-tuning techniques covered there.
- [[MOC - Training at Scale]] — grokking, double descent, and the lottery ticket hypothesis are training-dynamics phenomena that surface at the scale that domain covers.
