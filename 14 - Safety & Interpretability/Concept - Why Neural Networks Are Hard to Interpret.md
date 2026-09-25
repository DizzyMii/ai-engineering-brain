---
tags: [concept, domain/safety-interp, level/surface]
aliases: [black-box problem, neural network interpretability]
summary: "Why you cannot just read a transformer's weights: distributed representation, scale, and the absence of ground-truth feature labels."
---
> **One-paragraph hook:** Open a [[Concept - Decision Trees|decision tree]] and you can read the decision logic off the splits. Open a transformer's weight matrices and you see unlabeled numbers spread across thousands of dimensions, in a network too large for anyone to read end to end. "Interpretability is hard" isn't a complaint about tooling. It names specific mechanistic obstacles: representations are distributed instead of local, the scale is beyond manual inspection, there's no dictionary of "true" features to check against, and behavior can look right on every test you think of while an untested mechanism does the work underneath. This note is the surface entry to the interpretability side of the domain. The techniques that make progress against these obstacles are in [[Deep Dive - Mechanistic Interpretability]] and its component notes.

## The mechanism

**Distributed representation.** In a classical symbolic system or a shallow decision tree, one unit of structure maps to one human concept. In a neural network, information about a single concept is smeared across many dimensions of the [[Concept - Matrix Multiplication as the Atom of Deep Learning|activation vectors]], and a single dimension usually carries pieces of many unrelated concepts at once. You can't point to a neuron and say "this is the network's representation of X," because X is a direction in a high-dimensional space, not a coordinate axis. [[Concept - Backpropagation]] never optimizes for locality or readability. It optimizes loss, and loss doesn't care whether the representation is legible.

**Scale.** Ignore representation structure and the size alone makes manual reading hopeless. GPT-3 has 175B parameters across 96 layers with `d_model` = 12,288. One MLP layer in that model is a 12,288 × 49,152 matrix, roughly 600M numbers with no axis labels and no key. Reading it entry by entry tells you nothing. You need indirection first: project through the model's own output space, compare activations across controlled inputs, or fit an auxiliary model. Tools like the logit lens and activation patching exist for that reason. They're indirection strategies, not weight-reading.

**Polysemanticity**, the visible symptom of a deeper cause called [[Concept - Superposition]], makes both problems worse. A single neuron in a real model is documented firing for unrelated concepts (DNA sequences, HTTP request syntax and Korean text all activating the *same* unit), because the network packs more features than it has dimensions and accepts the interference. You can't give one neuron one meaning even in principle, since the network deliberately doesn't organize itself that way. Sparse feature activation makes packing many concepts into few dimensions cheap in expectation, so gradient descent takes the trade.

**No ground truth.** Supervised probing has labels to check a probe against. Interpretability has no ground-truth dictionary of the features a model actually uses. You don't know the list you're trying to recover, so you can't easily measure whether you recovered it. That's the field's "streetlight problem": researchers drift toward studying what's easy to measure (does a simple probe get high accuracy? does the logit lens produce coherent tokens?) over what's true, because nothing external checks the latter.

## In practice

The field splits into two complementary approaches with different standards of evidence:

- **Behavioral (black-box) interpretability**: evals, red-teaming, probing outputs under controlled input changes. It treats the model as a function you characterize from outside. This is the domain-13 toolkit, and it answers "what does it do."
- **Mechanistic interpretability**: reverse-engineering the computation itself (circuits, features, attention patterns). It treats the model as a program you decompile. This is [[Deep Dive - Mechanistic Interpretability]], and it answers "how does it do it."

The gap between them matters in practice. Behavioral testing can pass cleanly on every benchmark you run while a backdoor or deceptive circuit sits dormant inside, waiting for a trigger the eval never included. [[Breakdown - Sleeper Agents]] shows this directly: backdoored models survived standard safety fine-tuning and behavioral red-teaming because the trigger wasn't in the test distribution. You can't test your way to trust when the worry is conditional on inputs you didn't think to try. Only opening up the mechanism gives you a chance to find it whether or not you triggered it.

## Failure modes

- **Trusting attention weights as explanations.** Newcomers reach for attention weights first. They're a distribution over input tokens, so they look like "what the model is paying attention to." Jain and Wallace (2019, "Attention Is Not Explanation") showed you can build very different attention distributions that produce nearly identical outputs, so attention weight alone isn't a faithful account of what drove a prediction. Detection: never present attention maps as the mechanism without a causal check (patching, ablation) confirming the attended positions matter.
- **Reading one neuron's top activations and declaring a "concept neuron."** Because of polysemanticity, a neuron's top-activating examples are often a plausible but incomplete or misleading summary. It may fire just as strongly for an unrelated concept you didn't sample. Detection: check activation on a broad, deliberately diverse held-out set, not a curated list.
- **Assuming behavioral testing establishes safety.** As with Sleeper Agents, passing evals is evidence of absence only inside the tested distribution. Detection: pair behavioral evals with mechanistic audits (feature/circuit-level checks) before high-stakes deployment decisions.

## The non-obvious

The deepest reason this is hard isn't brute-force size. The optimization process has no pressure toward a human-legible basis, and its incentives (parameter efficiency under [[Concept - Superposition]]) push toward a *less* legible one as capability grows. Bigger models are harder to interpret for more reasons than parameter count. Superposition gets *more* attractive as the ratio of potentially useful features to available dimensions rises, so packing, and the polysemanticity that comes with it, tends to intensify with capability. Interpretability is working against an optimization pressure that runs the other way.

## Connections
- [[Concept - Superposition]] — the mechanistic cause of polysemanticity: why the network deliberately packs more features than it has dimensions.
- [[Concept - Sparse Autoencoders]] — the primary technique for un-mixing superposed activations into something closer to monosemantic features.
- [[Deep Dive - Mechanistic Interpretability]] — the full research program and toolkit this note sits above.
- [[Concept - Backpropagation]] — the optimization process that produces distributed representations with no pressure toward legibility.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the substrate (activation vectors, weight matrices) that "distributed representation" refers to concretely.
- [[Breakdown - Sleeper Agents]] — the concrete case proving behavioral testing alone cannot establish trust.
- [[Concept - The Emergent Abilities Debate]] — related uncertainty about what's actually happening inside models as capability scales, from the behavioral side.
- [[Concept - Decision Trees]] — the contrasting case of a genuinely interpretable model, used above to make "distributed representation" concrete.

## Sources
- Jain, S. and Wallace, B. C. (2019) — "Attention Is Not Explanation." Shows attention weights can vary drastically without changing model output, undermining their use as an explanation.
- Elhage et al. (2022) — "Toy Models of Superposition" (Anthropic). Establishes the superposition framing referenced above; full treatment in [[Concept - Superposition]].
