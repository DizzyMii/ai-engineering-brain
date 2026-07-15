---
tags: [concept, domain/esoterica, level/advanced]
aliases: [delayed generalization, grokking phase transition]
summary: "A network hits 100% train accuracy while validation stays at chance for ~10^5 steps, then generalizes abruptly — delayed generalization."
---
> **One-paragraph hook:** Train a small transformer on modular arithmetic and something strange happens: it memorizes the training set almost immediately, sits at random-chance validation accuracy for tens of thousands of steps past that point, and then — with no change in hyperparameters, no new data, nothing visibly different in the loss curve except more time — validation accuracy snaps from chance to ~100% within a few hundred steps. Power et al. called this "grokking," and it is the cleanest existence proof in deep learning that train loss and true generalization can decouple for a very long time.

## The mechanism
Power et al. 2022 (OpenAI, "Grokking: Generalization Beyond Overfitting on Small Algorithmic Datasets") trained a small decoder-only transformer on binary operation tables — tasks like $a + b \bmod 97$ or $a / b \bmod p$ for prime $p$ — with a fixed train/validation split of the input pairs. The characteristic curve looks like this:

```
accuracy
100% |                                    ___________________  val (generalizes)
     |                                   /
     |                                  |
     |                                  |
  50% |                                  |
     |                                  |
     |     ___________________________ /
   0% |____/
     +------------------------------------------------------------> step
        ~10^3 steps                              ~10^5 steps
        (train acc → 100%)                    (val acc snaps to ~100%)
```

Train accuracy reaches ~100% within roughly $10^3$ steps — ordinary memorization. Validation accuracy then sits at chance for roughly two orders of magnitude longer in step count before jumping to near-100% around $10^5$ steps. Nothing in the loss curve announces this in advance from the outside; the transition looks discontinuous at the level of the metric everyone is watching.

**Why weight decay is close to necessary.** Grokking is slow or absent without L2 regularization ([[Concept - Adam and AdamW]]'s weight-decay term, i.e. AdamW). The explanation is a competition between two solutions that both fit the training data: a **memorizing circuit** (high weight norm, essentially a lookup table with no compositional structure) and a **generalizing circuit** (an actual algorithm for the operation, implemented with lower weight norm). Once training accuracy hits 100%, gradient descent keeps optimizing — and with weight decay pulling toward the loss-minimizing point among all zero-train-loss solutions, the *lower-norm* generalizing circuit eventually becomes preferred purely because it is a smaller-norm way to fit the same training points. This is "circuit efficiency": the generalizing solution wins not because SGD suddenly discovers it, but because it was forming gradually the whole time and eventually crosses over the memorizing solution in loss-plus-decay terms.

**What the generalizing circuit actually is.** Nanda et al. 2023 ("Progress measures for grokking via mechanistic interpretability") reverse-engineered the trained network on modular addition and found it implements a genuine algorithm: it embeds $a$ and $b$ using trigonometric/Fourier features at specific frequencies, computes the sum via trig angle-addition identities (rotate to frequency space, effectively $\cos(\omega(a+b)) = \cos(\omega a)\cos(\omega b) - \sin(\omega a)\sin(\omega b)$), and reads off the argmax. Crucially, Nanda's **progress measures** — "restricted loss" (loss using only the Fourier-relevant components) and "excluded loss" (loss with those components ablated) — show the circuit forming smoothly and continuously *well before* validation accuracy visibly moves. The apparent discontinuity in the accuracy metric is hiding a gradual internal construction process; grokking is where "sudden metric" and "gradual mechanism" pull apart the same way they do in the mirage side of the [[Concept - The Emergent Abilities Debate]] — except here, mechanistic interpretability closes the loop and shows the underlying continuity directly, rather than just via a smoother metric.

**Generality beyond arithmetic.** Liu et al. ("Omnigrok: Grokking Beyond Algorithmic Data") reframed grokking as a property of motion on the loss landscape driven by weight norm, not an arithmetic-specific curiosity: artificially inflating the initialization scale *induces* grokking-like delayed generalization on tasks that don't normally show it, and deflating the initialization removes the delay. Grokking is a generic phenomenon of the geometry (weight norm relative to a generalizing-solution manifold), which is why weight decay — the thing that steers weight norm — is the operative lever.

**Architecture changes the circuit.** Zhong et al. ("The Clock and the Pizza") found that the specific algorithm learned depends on architecture and width: some configurations land on a "clock" algorithm (angles progress like clock hands), others on a "pizza" algorithm (a different geometric arrangement of the same trig structure) for the *same task*. There is no single "true" circuit a network converges to — a caution against assuming mechanistic interpretability findings on one architecture transfer unchanged to another.

## In practice
The canonical demonstration is fully reproducible on a single GPU in minutes — see [[Snippet - Reproducing Grokking on Modular Addition]] for a runnable version. The relevant knobs, in order of how much they matter: weight decay (near-necessary, typically 1.0 in the original setup — much higher than a normal LLM's ~0.1), the train/validation split fraction (too little training data and the network never has enough signal to prefer the generalizing circuit at all), learning rate, and total training budget (you must run **far** past the point where train loss looks converged — the whole phenomenon is invisible if you stop early). The connection to epoch-wise [[Concept - Double Descent]] is direct: both are examples of test error moving substantially after train loss has saturated, and Thilak et al.'s "slingshot mechanism" describes a related late-training oscillatory dynamic that can precede grokking-like transitions.

## Failure modes
- **Early stopping on validation loss kills the run right before the transition.** If your stopping criterion is "validation hasn't improved in N steps," and N is smaller than the grokking delay (which can be 10-100x the memorization time), you will stop the run in the flat, chance-accuracy region and conclude the model "can't learn this" — when it was about to.
- **No weight decay → no grokking, or grokking that never arrives in a practical budget.** If you're benchmarking a claim about grokking and forgot AdamW's weight decay, you're not testing the phenomenon.
- **Too little training data.** Below some threshold train-set fraction, there isn't enough constraint to make the generalizing circuit lower-loss than clever memorization schemes, and the network memorizes indefinitely without ever grokking. Detection: sweep data fraction and watch for a critical point below which val accuracy never leaves chance even at 10x the normal step budget.
- **Assuming one universal circuit.** Per "The Clock and the Pizza," interpretability conclusions drawn from one grokked model (a specific circuit shape) do not automatically generalize to a different width or architecture solving the same task — verify, don't assume, when porting an interpretability finding.

## The non-obvious
The practically dangerous read of grokking isn't "cute arithmetic curiosity," it's a direct warning about validation-based decision-making at any scale: **the absence of visible progress on your tracked metric is not evidence of the absence of internal progress.** Nanda's progress measures show the network was doing real, monotonic work the entire "flat" period — you just weren't measuring the right thing. For LLM pretraining and fine-tuning, this reframes what a plateaued eval curve means: it might be memorization saturating while a more useful circuit is still under construction beneath a metric that can't see it yet, and the only way to know is to have (or build) a progress measure more sensitive than end-task accuracy — which is exactly what mechanistic interpretability tooling is for.

## Connections
- [[Concept - Double Descent]] — both are cases of validation/test performance moving long after training loss has saturated; grokking is the extreme, delayed-then-discontinuous end of the same family.
- [[Concept - The Emergent Abilities Debate]] — grokking is the strongest existence proof that genuine internal phase transitions occur, the fact that keeps the "emergence is entirely a metric mirage" position from being total.
- [[Snippet - Reproducing Grokking on Modular Addition]] — the runnable reproduction of the phenomenon described here.
- [[Concept - Adam and AdamW]] — weight decay, specifically AdamW's decoupled decay term, is the near-necessary condition that makes grokking happen in a practical step budget.
- [[Concept - Induction Heads]] — another case where a discrete, interpretable circuit forms inside a transformer through training, studied with the same mechanistic-interpretability toolkit.
- [[Concept - Mode Connectivity and Flat Minima]] — the weight-norm/loss-landscape geometry that Omnigrok invokes to explain grokking as landscape motion rather than an arithmetic-specific quirk.
- [[Concept - Numeracy and Digit Tokenization]] — the same Fourier/trig-feature mechanism Nanda found for modular addition shows up again in how models internally represent numbers for arithmetic more broadly.
- [[Reference - Open Problems in LLM Engineering]] — grokking is cited there as one of the few partial windows into the still-unsolved question of why overparameterized networks generalize at all.

## Sources
- Power, Burda, Edwards, Babuschkin & Sutskever (2022) — "Grokking: Generalization Beyond Overfitting on Small Algorithmic Datasets". Establishes the phenomenon on modular arithmetic tasks.
- Nanda, Chan, Lieberum, Smith & Steinhardt (2023) — "Progress measures for grokking via mechanistic interpretability". Reverse-engineers the Fourier/trig circuit and shows gradual formation via restricted/excluded loss.
- Liu, Michaud & Tegmark — "Omnigrok: Grokking Beyond Algorithmic Data". Reframes grokking as weight-norm-driven landscape motion, inducible on non-arithmetic tasks.
- Zhong, Liu, Chan & Steinhardt — "The Clock and the Pizza: Two Stories in Mechanistic Explanation of Neural Networks". Shows architecture/width determine which of several distinct circuits a grokked network lands on.
- Thilak et al. — work on the "slingshot mechanism", a related late-training oscillatory dynamic connected to epoch-wise double descent and grokking.
