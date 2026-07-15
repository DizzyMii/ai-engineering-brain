---
tags: [reference, domain/esoterica, level/frontier]
aliases: [Open Problems in LLMs, LLM Open Questions, Map of Ignorance]
summary: "Standing unsolved problems in building and understanding LLMs, each with why it's hard and where the real work lives."
---

> A map of ignorance, not a resolution. Each row is a launch point; the last column is where the deeper work lives. Everything here is deliberately unsettled and volatile — the frontier moves *(as of 2026)*.

## The catalog

| # | Open problem | Why it resists a clean answer | Best partial answer (2026) | Goes deeper |
|---|---|---|---|---|
| 1 | Why overparameterized nets generalize | No bound depends only on the hypothesis class once nets fit random labels | Implicit bias of SGD toward min-norm/max-margin interpolants; flat-minima ≈ low description length | [[Concept - Grokking]] |
| 2 | Why in-context learning works | Three mechanisms all have evidence; none covers every case | [[Concept - Induction Heads]] circuitry vs implicit gradient descent vs Bayesian task inference | [[Concept - In-Context Learning]] |
| 3 | Hallucination | Models are token-calibrated yet confidently wrong on facts | Incentive account (reward guessing over abstaining) + directional knowledge storage | [[Concept - The Reversal Curse]] |
| 4 | The interpretability ceiling | Features live in superposition; SAEs leave large unexplained residual | [[Concept - Sparse Autoencoders]] recover many monosemantic features; "dark matter" remains | [[Concept - Superposition]] |
| 5 | The end of scaling | High-quality tokens are finite; synthetic data risks collapse | Data-constrained scaling + test-time compute reopened an orthogonal axis | [[Concept - Scaling Laws]] |
| 6 | Continual learning without forgetting | Plasticity trades against stability; no clean frontier-scale recipe | EWC / replay / LoRA + RAG crutch; knowledge editing is brittle | [[Concept - Catastrophic Forgetting]] |
| 7 | The measurement problem | The metric can manufacture the capability; contamination and Goodhart corrupt scores | Statistical rigor, decontamination, private/dynamic evals — methodological, not solved | [[Concept - Statistical Rigor in Model Evaluation]] |

## 1. Why do massively overparameterized nets generalize?

Zhang et al. 2017 ("Understanding deep learning requires rethinking generalization") is the clean statement of the problem: a standard net will fit CIFAR-10 with *randomly permuted labels* to zero training error, so any generalization bound that depends only on the hypothesis class (VC dimension, Rademacher complexity of the architecture) is vacuous — the same architecture that generalizes on real labels also memorizes noise. [[Concept - Double Descent]] and grokking *describe* the empirical curves (test error non-monotone in capacity; generalization arriving long after train loss saturates), but neither *predicts* test error from architecture + data + optimizer.

Partial answers, all incomplete: (a) SGD has an *implicit bias* toward low-norm / max-margin interpolants (provable for linear/logistic; Soudry et al. 2018), (b) flatness of the found minimum correlates with generalization and ties to a minimum-description-length argument — see [[Concept - Mode Connectivity and Flat Minima]], (c) feature-learning vs kernel (NTK) regimes explain some but not the full picture. There is no theory that takes a `(model, dataset)` and returns a generalization gap.

## 2. Why does in-context learning work?

Three live hypotheses, each with real evidence and each incomplete:

- **Circuit account** — Olsson et al. 2022 ("In-context Learning and Induction Heads") tie the phase change in ICL ability to the formation of induction heads that do prefix-match-then-copy; the ICL loss drop and induction-head formation happen at the same training step.
- **Implicit optimization** — von Oswald et al. 2023 show a transformer forward pass can *implement* one or more steps of gradient descent on the in-context examples, so ICL would be learning-in-activations.
- **Bayesian inference** — Xie et al. 2021 frame ICL as implicit Bayesian inference: the prompt selects a latent concept the pretraining distribution already contains, so ICL is retrieval of a pretrained skill, not new learning.

The tension: learning a genuinely novel function in-context (evidence for optimization) vs selecting a pretrained skill (evidence for Bayesian retrieval) are hard to separate empirically. This is entangled with [[Concept - The Emergent Abilities Debate]] — whether ICL "emerges" is partly a measurement question.

## 3. Is hallucination fixable in-parameter, or does it require retrieval?

Models are reasonably *calibrated at the token level* — their next-token probabilities track empirical frequencies — yet emit confident false *facts*. Kalai et al. 2025 ("Why Language Models Hallucinate") argue a large part is an incentive artifact: pretraining and most benchmarks reward a confident guess over an "I don't know," so the loss-minimizing policy bluffs on the tail of rare facts. That is a training/eval-design lever, not a mystery — but it does not tell you whether factuality can be made reliable *in the weights*.

The structural obstacle is that parametric knowledge is stored directionally and lossily (the reversal curse: trained on "A is B," the model may not know "B is A"), so some facts are simply not extractable even when "present." That is a standing argument for why retrieval is load-bearing rather than a temporary crutch. Open: whether a scaling or training recipe closes the factuality gap in-parameter, or whether grounding is permanently required.

## 4. The interpretability ceiling: superposition and "dark matter"

Networks pack more features than they have neurons by storing them as near-orthogonal directions that are only separable when active features are sparse (Elhage et al. 2022, "Toy Models of Superposition"). Sparse autoencoders trained on the residual stream (Bricken et al. 2023; Templeton et al. 2024, "Scaling Monosemanticity" on Claude 3 Sonnet) recover thousands-to-millions of monosemantic features — real progress — but a large fraction of activation variance is unexplained SAE "dark matter," and *enumerative safety* (list every feature, verify none is dangerous) is unproven at scale. Open question, and a genuinely load-bearing one for safety: is full mechanistic interpretability even tractable, or is there an irreducible residual that no dictionary recovers? Practitioners doing this work hit a long list of practical pitfalls well before they ever reach the dark-matter question — see [[Gotchas - Interpreting Model Internals]].

## 5. Where does scaling end?

Chinchilla-optimal training wants roughly 20 tokens per parameter, and frontier runs are token-hungry against a finite supply of high-quality web text. Muennighoff et al. 2023 ("Scaling Data-Constrained Language Models") measured the returns to *repeating* data: up to ~4 epochs is nearly as good as fresh tokens, then value decays sharply — you can trade compute for data only so far. Manufacturing data instead risks [[Concept - Model Collapse from Synthetic Data]]: Shumailov et al. 2024 (Nature, "AI models collapse when trained on recursively generated data") show recursive training on model output degrades the distribution tails generation by generation. Meanwhile test-time compute (the o-series reasoning wave, 2024–2025; see [[Concept - Reasoning Training and Long Chain-of-Thought]]) reopened a scaling axis orthogonal to pretraining FLOPs. Open: whether the pretraining curve bends before the tokens run out — the practical framing lives in [[Concept - The Data Wall]] and [[Concept - Data-Constrained Scaling Laws]].

## 6. Continual learning without catastrophic forgetting

No production recipe lets a deployed frontier model absorb new facts *online* without a full (re)train or a retrieval crutch. Naive fine-tuning on new data induces catastrophic forgetting (McCloskey & Cohen 1989; French 1999): the new gradient overwrites the weights that encoded old skills. Mitigations — Elastic Weight Consolidation (Kirkpatrick et al. 2017), experience replay, adapter/LoRA isolation — each trade plasticity against stability and none is clean at frontier scale. Targeted knowledge editing (ROME, MEMIT) writes single facts but is brittle and directional (again the reversal curse). This is why "just fine-tune it on the new docs" is rarely the right answer and RAG persists.

## 7. The measurement problem

We cannot cleanly state what a model can do — and this is arguably the most operationally damaging open problem, because every other claim rests on it. Three compounding failures: (a) the *metric* can manufacture the capability curve — Schaeffer et al. 2023 showed exact-match/multiple-choice thresholds create apparent emergence that vanishes under smooth metrics; (b) [[Concept - Benchmark Contamination]] leaks test items into pretraining and inflates scores; (c) [[Concept - Goodhart's Law in Model Evaluation]] guarantees any headline benchmark gets gamed once it matters commercially. Methodologically this is owned by evaluation (domain 13); in practice it stays unsolved, which is why "SOTA on X" should be read with the harness, the contamination controls, and the confidence interval attached.

---

This reference is intentionally a map, refreshed as the frontier moves. For where the actual research surfaces — the papers, lab blogs, and threads that update these rows — see [[Reference - Where Real AI Knowledge Lives]].

## Connections
- [[Concept - Grokking]] — cleanest existence proof that train loss and true generalization decouple; anchors problem 1.
- [[Concept - Double Descent]] — the non-monotone capacity/error curve that any generalization theory must explain.
- [[Concept - Mode Connectivity and Flat Minima]] — the flat-minima ↔ generalization link, one of the few partial answers to problem 1.
- [[Concept - Induction Heads]] — the circuit-level candidate mechanism for in-context learning.
- [[Concept - In-Context Learning]] — the phenomenon problem 2 is trying to explain.
- [[Concept - The Emergent Abilities Debate]] — whether capabilities emerge is entangled with both ICL and the measurement problem.
- [[Concept - The Reversal Curse]] — directional knowledge storage is why hallucination may be structurally un-fixable in-parameter.
- [[Concept - Superposition]] — the reason interpretability has a ceiling; features exceed neurons.
- [[Concept - Sparse Autoencoders]] — the leading tool for recovering features and the source of the "dark matter" gap.
- [[Concept - Scaling Laws]] — the curve whose ending problem 5 is about.
- [[Concept - Data-Constrained Scaling Laws]] — quantifies the returns to repeating data as tokens run out.
- [[Concept - The Data Wall]] — the operator-facing framing of the token-supply limit.
- [[Concept - Model Collapse from Synthetic Data]] — why synthetic data is not a free escape from the data wall.
- [[Concept - Reasoning Training and Long Chain-of-Thought]] — test-time compute as the axis that reopened scaling.
- [[Concept - Catastrophic Forgetting]] — the mechanism blocking online continual learning.
- [[Concept - Statistical Rigor in Model Evaluation]] — the discipline that would make the measurement problem tractable.
- [[Concept - Benchmark Contamination]] — a concrete corrupter of the measurements everything else rests on.
- [[Concept - Goodhart's Law in Model Evaluation]] — why any load-bearing benchmark decays once it matters.
- [[Reference - Where Real AI Knowledge Lives]] — where these rows get updated as the frontier moves.
- [[Gotchas - Interpreting Model Internals]] — the up-link into the tribal-knowledge-level pitfalls of interpretability work that sit beneath the frontier-level superposition/SAE framing in problem 4.

## Sources
- Zhang, Bengio, Hardt, Recht, Vinyals (2017) — *Understanding deep learning requires rethinking generalization*. Nets fit random labels; classical bounds are vacuous.
- Olsson et al. (2022) — *In-Context Learning and Induction Heads*. ICL ability co-forms with induction-head circuits.
- von Oswald et al. (2023) — *Transformers Learn In-Context by Gradient Descent*. Forward pass can implement GD steps.
- Xie et al. (2021) — *An Explanation of In-Context Learning as Implicit Bayesian Inference*. ICL as latent-concept selection.
- Kalai, Nachum, Vempala, Zhang (2025) — *Why Language Models Hallucinate*. Hallucination as a training/eval incentive.
- Elhage et al. (2022) — *Toy Models of Superposition*. Features stored as near-orthogonal directions under sparsity.
- Templeton et al. (2024) — *Scaling Monosemanticity*. SAE features on Claude 3 Sonnet; leaves unexplained residual.
- Muennighoff et al. (2023) — *Scaling Data-Constrained Language Models*. ~4 epochs of repeat ≈ fresh tokens, then decay.
- Shumailov et al. (2024, Nature) — recursive training on generated data collapses distribution tails.
- Kirkpatrick et al. (2017) — *Overcoming catastrophic forgetting* (EWC). Anchor-important-weights mitigation.
- Schaeffer, Miranda, Koyejo (2023) — *Are Emergent Abilities a Mirage?* Metric choice manufactures the curve.
