---
tags: [concept, domain/safety-interp, level/surface]
aliases: [black-box problem, neural network interpretability]
summary: "Why you cannot just read a transformer's weights: distributed representation, scale, and the absence of ground-truth feature labels."
---
> **One-paragraph hook:** Open a [[Concept - Decision Trees|decision tree]] and you can read the decision logic off the splits. Open a transformer's weight matrices and you see numbers with no labels, spread across thousands of dimensions, in a network too large for any human to read end to end. "Interpretability is hard" is not a complaint about tooling — it names a specific, mechanistic set of obstacles: the representations are distributed rather than local, the scale is beyond manual inspection, there is no dictionary of "true" features to check against, and behavior can look correct in every test you think to run while a mechanism you didn't test for is doing the work underneath. This note is the surface entry to the interpretability wing of the domain; the actual techniques that make progress against these obstacles live in [[Deep Dive - Mechanistic Interpretability]] and its component notes.

## The mechanism

**Distributed representation.** In a classical symbolic system or a shallow decision tree, one unit of structure maps to one human concept. In a neural network, information about a single concept is smeared across many dimensions of the [[Concept - Matrix Multiplication as the Atom of Deep Learning|activation vectors]], and — critically — a single dimension typically carries pieces of many unrelated concepts at once. There is no neuron you can point to and say "this is the network's representation of X," because X's representation is a direction in a high-dimensional space, not a coordinate axis. [[Concept - Backpropagation]] never optimizes for locality or human-readability; it optimizes for loss, and loss is agnostic to whether the resulting representation is legible.

**Scale.** Even setting representation structure aside, the sheer size makes manual reading hopeless. GPT-3 has 175B parameters across 96 layers with `d_model` = 12,288 — a single MLP layer in that model is a 12,288 × 49,152 matrix (roughly 600M numbers) with no axis labels and no accompanying key. Reading that matrix directly, entry by entry, tells you nothing; you need indirection (projecting through the model's own output space, comparing activations across controlled inputs, or fitting an auxiliary model) before any of it becomes legible. This is exactly why tools like the logit lens and activation patching exist — they are indirection strategies, not literal weight-reading.

**Polysemanticity**, the observable symptom of a deeper cause called [[Concept - Superposition]], compounds both problems: a single neuron in a real model is documented to activate for entirely unrelated concepts — DNA sequences, HTTP request syntax, and Korean text firing the *same* unit — because the network is packing more features than it has dimensions and accepting interference as the price. You cannot assign one neuron one meaning even in principle, because the network deliberately doesn't organize itself that way; sparsity in feature activation makes packing many concepts into few dimensions cheap in expectation, so gradient descent takes the trade.

**No ground truth.** In supervised probing you have labels to check a probe against. In interpretability there is no ground-truth dictionary of "the true features this model uses" — you don't know the list you're trying to recover, so you can't straightforwardly measure whether you've recovered it. This is the field's "streetlight problem": researchers are pulled toward studying what is easy to measure (does a simple probe achieve high accuracy? does the logit lens produce coherent tokens?) rather than what is true, because there's no external check on the latter.

## In practice

The field splits into two complementary approaches with different evidentiary standards:

- **Behavioral (black-box) interpretability**: evals, red-teaming, probing outputs under controlled input variation — treats the model as a function you characterize from outside. This is the domain-13 toolkit and answers "what does it do."
- **Mechanistic interpretability**: reverse-engineering the actual computation — circuits, features, attention patterns — treats the model as a program you decompile. This is [[Deep Dive - Mechanistic Interpretability]] and answers "how does it do it."

The gap between these matters operationally: behavioral testing can pass cleanly on every benchmark you run while a backdoor or deceptive circuit sits dormant inside, waiting for a trigger the eval never happened to include. [[Breakdown - Sleeper Agents]] demonstrates this directly — models trained with a backdoor survived standard safety fine-tuning and behavioral red-teaming, because the trigger condition simply wasn't in the test distribution. You cannot test your way to trust when the thing you're worried about is conditional on inputs you didn't think to try; only opening up the mechanism gives you a chance to find it regardless of whether you triggered it.

## Failure modes

- **Trusting attention weights as explanations.** Attention weights are the first thing a newcomer reaches for — they're literally a distribution over input tokens, so they look like "what the model is paying attention to." Jain and Wallace (2019, "Attention Is Not Explanation") showed you can construct wildly different attention distributions that produce nearly identical model outputs, meaning attention weight alone is not a faithful account of what drove the prediction. Detection: never present attention maps as the mechanism without a causal check (patching, ablation) confirming the attended positions actually matter.
- **Reading a single neuron's top activations and declaring a "concept neuron."** Because of polysemanticity, the top-activating examples for a neuron are frequently a plausible-looking but incomplete or misleading summary — the neuron may fire just as strongly for an unrelated concept you didn't happen to sample. Detection: check activation on a broad, deliberately diverse held-out set, not a curated example list.
- **Assuming behavioral testing establishes safety.** As above with Sleeper Agents — passing evals is evidence of absence only within the tested distribution. Detection: pair behavioral evals with mechanistic audits (feature/circuit-level checks) before high-stakes deployment decisions.

## The non-obvious

The deepest reason this is hard is not that networks are "too big" in a brute-force sense — it's that the optimization process has no pressure toward a human-legible basis at all, and every incentive (parameter efficiency under [[Concept - Superposition]]) pushes toward a *less* legible one as capability increases. Bigger, more capable models are not just harder to interpret because they have more parameters to read; they are harder to interpret because superposition gets *more* attractive as the ratio of possible-useful-features to available dimensions grows, so the packing (and the resulting polysemanticity) tends to intensify with capability, not diminish. Interpretability is fighting an optimization pressure that runs the opposite direction from readability.

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
