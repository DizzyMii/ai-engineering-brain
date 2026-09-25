---
tags: [concept, domain/safety-interp, level/advanced]
aliases: [feature superposition, superposition hypothesis]
summary: "How a network represents more features than it has dimensions by packing them as near-orthogonal directions and tolerating sparse interference."
---
# Concept - Superposition

> **One-paragraph hook:** A transformer's [[Concept - Matrix Multiplication as the Atom of Deep Learning|residual stream]] has a few thousand dimensions, yet the model plausibly has to represent far more distinct concepts than that: every entity, syntactic role, factual association and stylistic register it has seen. Superposition resolves the contradiction. The network doesn't give each feature its own dimension. It packs many features into overlapping, near-orthogonal directions and accepts a little interference in exchange for representing far more than the dimension count would naively allow. It's the central idea in mechanistic interpretability. It explains *why* [[Concept - Why Neural Networks Are Hard to Interpret|neural networks resist being read directly]], and every downstream un-mixing technique exists to undo it.

## The mechanism

Anthropic's "Toy Models of Superposition" (Elhage et al. 2022) pins the claim down with a controlled experiment. Take a synthetic dataset of $n$ sparse features, each active with some small probability $p$ and otherwise zero. Train a minimal ReLU network, a down-projection $W \in \mathbb{R}^{d \times n}$ into $d < n$ dimensions and an up-projection back, to reconstruct the features under a mean-squared loss weighted by a per-feature importance term. With dense features (frequently co-active), the model does what classical compression theory predicts: it keeps the $d$ most important features and drops the rest. With **sparse** features, the behavior changes in kind. The model represents *more than $d$* features at once, giving each a direction in the $d$-dimensional space and accepting that non-orthogonal directions will sometimes interfere.

**Sparsity is what makes it work.** If two features rarely fire together, near-orthogonal directions are good enough; they don't have to be strictly orthogonal. The interference term in the loss only bites on the rare occasions both are present, so gradient descent trades a small expected reconstruction error for a large gain in capacity. Underneath is a Johnson–Lindenstrauss argument. The number of vectors you can pack into $\mathbb{R}^d$ while keeping pairwise dot products under a small threshold $\epsilon$ grows **exponentially** in $d$ (roughly $\exp(c\, d\, \epsilon^2)$ for a constant $c$), not linearly. A modest residual stream therefore has room for far more near-orthogonal "feature slots" than its raw dimension count suggests, as long as features are sparse enough that the near-orthogonality error rarely matters.

**Feature geometry.** Sweep sparsity up in the toy model and the learned directions don't land at random. They organize into polytopes: antipodal pairs first (two features sharing one dimension in opposite directions, "digons"), then triangles, pentagons and tetrahedra as more features compete for the space. The structure is a direct, visible signature of the packing problem the network is solving, and it shows up, messier, in real trained models.

**Superposition supports computation as well as storage.** The toy models show a network computing simple functions (absolute value, for instance) *on* superposed features without first un-mixing them into private dimensions. So the problem goes beyond a dense storage format: the computation itself runs on the packed representation. To untangle what a layer computes you have to untangle superposition first. Storage and computation aren't separable problems here.

## In practice

**Polysemanticity is the visible symptom.** A single neuron in a real model firing for unrelated concepts (one documented case responds to DNA sequences, HTTP request syntax and Korean text) is what you'd expect if that neuron's basis direction projects onto several superposed feature directions. It's why reading a raw neuron's top-activating examples is unreliable. The neuron was never assigned to "mean" one thing.

**Capability makes it worse.** The naive intuition says a bigger model has more dimensions and should need less packing. In practice the number of *useful* features a more capable model learns (rare facts, fine-grained entities, specific stylistic registers) typically grows at least as fast as its width, so the pressure toward superposition doesn't ease with scale. If anything, frontier models pack their long tail of rare features *more* densely. That's why interpretability at frontier scale (see [[Concept - Sparse Autoencoders]]) has needed correspondingly wider dictionaries, tens of millions of learned features, to make progress.

## Failure modes

- **Reading one neuron and concluding a feature is absent.** A feature lives in a direction, not a coordinate, so checking one neuron for evidence of a concept systematically undercounts. The feature can be present and doing real work while the neuron you looked at barely responds. Detection: probe with a direction (a linear combination across many neurons), not a single unit.
- **Interference-driven computation errors.** In the toy models, when two superposed features that interfere happen to co-activate, reconstruction (and any computation built on it) measurably degrades. It's a controlled analogue of real-model errors that only appear on rare co-occurring inputs and are hard to reproduce, because the trigger is a specific joint activation pattern and not a single feature.
- **Assuming wider layers fix interpretability.** Scaling $d$ without addressing sparsity only raises packing capacity, and the model fills it with more features instead of leaving it idle. Width doesn't cure superposition. The pressure that creates it (more useful features than budget) stays when the budget grows; the equilibrium just moves.

## The non-obvious

Superposition means there's **no privileged neuron basis to read in the first place.** The residual stream's standard-basis coordinates mean no more than any other orthonormal basis, because the model was never trained to align features with axes. That's why raw-weight inspection fails and why the field's central tool exists: [[Concept - Sparse Autoencoders|dictionary learning via sparse autoencoders]] searches for a *different*, wider basis aligned with the model's actual feature directions instead of its arbitrary coordinate axes, using the same sparsity assumption that produced superposition. The toy-models result is also a rare interpretability case where theory came first and predicted the finding. The geometric phase transitions (digons → triangles → higher polytopes) were predicted from the loss surface before they were confirmed as the learned structure.

## Connections
- [[Concept - Sparse Autoencoders]] — the primary technique built specifically to reverse superposition, exploiting the same sparsity structure this note describes.
- [[Concept - Why Neural Networks Are Hard to Interpret]] — the surface-level framing this note sits underneath; superposition is the mechanistic cause of the polysemanticity that note names as a symptom.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the residual-stream vectors and weight matrices that "directions" and "features" refer to concretely.
- [[Concept - Attention Sinks]] — another case where a model's real learned behavior (dumping attention mass on a fixed token) only makes sense once you stop assuming a clean one-purpose-per-unit structure, the same interpretive humility superposition demands.
- [[Deep Dive - Mechanistic Interpretability]] — the full research program that superposition motivates and that SAEs, patching, and attribution graphs are built to work around.
- [[Concept - Induction Heads]] — a rare case of a circuit that is *not* badly superposed and was cleanly reverse-engineered, useful as a contrast case for how much harder superposed computation is.
- [[Concept - Emergent Misalignment]] — a frontier finding where a narrow fine-tune shifts a broad, superposed cluster of safety-relevant features at once, a direct practical consequence of features sharing packed directions rather than sitting in isolated dimensions.
- [[Concept - The Geometry of High-Dimensional Spaces]] — the general high-dimensional geometry (near-orthogonality, concentration of measure) that the Johnson–Lindenstrauss capacity argument above draws on.

## Sources
- Elhage, N. et al. (2022) — "Toy Models of Superposition" (Anthropic). Establishes the sparsity-enables-packing mechanism, the feature-geometry phase transitions, and computation-in-superposition, all described above.
- Johnson, W. B. and Lindenstrauss, J. (1984) — the dimensionality-reduction lemma underlying the exponential near-orthogonal-vector capacity argument used to explain why superposition scales so far past the raw dimension count.
