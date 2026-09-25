---
tags: [concept, domain/esoterica, level/advanced]
aliases: [delayed generalization, grokking phase transition]
summary: "A network hits 100% train accuracy while validation stays at chance for ~10^5 steps, then generalizes abruptly — delayed generalization."
---
> **One-paragraph hook:** Train a small transformer on modular arithmetic and it memorizes the training set almost immediately, then sits at chance validation accuracy for tens of thousands of steps. Then, with no change in hyperparameters, no new data and nothing different in the loss curve except elapsed time, validation accuracy jumps from chance to ~100% within a few hundred steps. Power et al. called this "grokking." It's the cleanest existence proof in deep learning that train loss and real generalization can decouple for a very long time.

## The mechanism
Power et al. 2022 (OpenAI, "Grokking: Generalization Beyond Overfitting on Small Algorithmic Datasets") trained a small decoder-only transformer on binary operation tables, tasks like $a + b \bmod 97$ or $a / b \bmod p$ for prime $p$, with a fixed train/validation split of the input pairs. The curve looks like this:

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

Train accuracy hits ~100% within roughly $10^3$ steps, which is ordinary memorization. Validation accuracy stays at chance for about two orders of magnitude more steps, then jumps to near-100% around $10^5$. From the outside, nothing in the loss curve warns you. On the metric everyone watches, the transition looks discontinuous.

### Weight decay is close to necessary
Without L2 regularization ([[Concept - Adam and AdamW]]'s weight-decay term, i.e. AdamW), grokking is slow or doesn't happen. Two solutions fit the training data and compete. A **memorizing circuit** has high weight norm and is basically a lookup table with no compositional structure. A **generalizing circuit** implements the actual operation at lower weight norm. After training accuracy hits 100%, gradient descent keeps going, and weight decay pulls toward the lowest-norm point among the zero-train-loss solutions. The generalizing circuit eventually wins because it fits the same points with a smaller norm. This is "circuit efficiency." SGD doesn't suddenly discover the generalizing solution; it was forming gradually all along and eventually overtakes the memorizing one on loss plus decay.

### What the generalizing circuit is
Nanda et al. 2023 ("Progress measures for grokking via mechanistic interpretability") reverse-engineered the network trained on modular addition. It embeds $a$ and $b$ as trigonometric/Fourier features at specific frequencies, computes the sum with the angle-addition identities (effectively $\cos(\omega(a+b)) = \cos(\omega a)\cos(\omega b) - \sin(\omega a)\sin(\omega b)$), and reads off the argmax. Their **progress measures**, "restricted loss" (loss using only the Fourier-relevant components) and "excluded loss" (loss with those components ablated), show the circuit forming smoothly and continuously *well before* validation accuracy moves. The jump in the accuracy metric hides a gradual internal build. Metric and mechanism pull apart here the same way they do in the mirage side of [[Concept - The Emergent Abilities Debate]], except that here mechanistic interpretability shows the underlying continuity directly instead of inferring it from a smoother metric.

### It isn't specific to arithmetic
Liu et al. ("Omnigrok: Grokking Beyond Algorithmic Data") recast grokking as motion on the loss landscape driven by weight norm. Inflating the initialization scale *induces* grokking-like delayed generalization on tasks that don't normally show it; deflating it removes the delay. So the phenomenon comes from geometry (weight norm relative to a manifold of generalizing solutions), and weight decay, which controls weight norm, is the lever that matters.

### Architecture changes the circuit
Zhong et al. ("The Clock and the Pizza") found that the learned algorithm depends on architecture and width. On the *same task*, some configurations learn a "clock" algorithm (angles advance like clock hands) and others a "pizza" algorithm (a different geometric arrangement of the same trig structure). No single "true" circuit exists for a network to converge to, so don't assume an interpretability finding on one architecture carries over unchanged to another.

## In practice
The canonical demo reproduces on a single GPU in minutes; [[Snippet - Reproducing Grokking on Modular Addition]] has a runnable version. The knobs, in order of impact:

1. Weight decay. Near-necessary, 1.0 in the original setup, far above a typical LLM's ~0.1.
2. Train/validation split fraction. With too little training data there isn't enough signal for the generalizing circuit to ever win.
3. Learning rate.
4. Total training budget. You have to run **far** past where train loss looks converged. Stop early and you never see it.

The link to epoch-wise [[Concept - Double Descent]] is direct: in both, test error moves a lot after train loss has saturated. Thilak et al.'s "slingshot mechanism" describes a related late-training oscillation that can precede grokking-like transitions.

## Failure modes
- **Early stopping on validation loss ends the run just before the transition.** If the rule is "stop when validation hasn't improved in N steps" and N is smaller than the grokking delay (which can be 10-100x the memorization time), you'll stop in the flat chance-accuracy region and conclude the model "can't learn this" when it was about to.
- **No weight decay.** Then no grokking, or grokking that never arrives within a practical budget. If you're testing a grokking claim without AdamW's weight decay, you aren't testing the phenomenon.
- **Too little training data.** Below some training fraction, the generalizing circuit never becomes lower-loss than clever memorization, and the network memorizes forever. Detection: sweep data fraction and look for a critical point below which val accuracy never leaves chance, even at 10x the normal step budget.
- **Assuming one universal circuit.** Per "The Clock and the Pizza," a circuit found in one grokked model doesn't automatically hold for a different width or architecture on the same task. Check before porting an interpretability result.

## The non-obvious
Grokking is more than an arithmetic curiosity. It's a warning about validation-based decisions at any scale: **no visible progress on your tracked metric is not evidence of no internal progress.** Nanda's progress measures show the network doing real, monotonic work through the whole "flat" stretch; nobody was measuring the right thing. For LLM pretraining and fine-tuning, a plateaued eval curve might be memorization saturating while a more useful circuit is still being built under a metric that can't see it yet. The only way to tell is a progress measure more sensitive than end-task accuracy, which is what mechanistic interpretability tooling is for.

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
