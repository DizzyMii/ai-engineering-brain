---
tags: [concept, domain/post-training, level/advanced]
aliases: [IPO, KTO, ORPO, SimPO, cDPO, DPO variants]
summary: "IPO, KTO, ORPO, and SimPO: what each post-DPO offline preference algorithm fixes, and the reference-model-memory tradeoffs each makes."
---

> **One-paragraph hook:** [[Concept - Direct Preference Optimization (DPO)]] shipped in 2023 with three specific weaknesses. It overfits on near-deterministic preference pairs, it needs paired comparisons when most products collect thumbs-up/down data, and it exploits length. IPO, KTO, ORPO and SimPO each patch one of those weaknesses. Read as a family, they're quick to choose between for a given data situation.

## The mechanism

### IPO: bounded loss against overfitting

IPO (Azar et al. 2023) fixes DPO's overfitting. DPO's log-sigmoid loss keeps pushing the implicit reward margin toward infinity on easily separable pairs. The gradient never fully vanishes, so probabilities get driven to extremes even on pairs the model already ranks correctly. IPO swaps the log-sigmoid for a bounded squared loss around a finite target margin $1/(2\tau)$:

$$\mathcal{L}_{IPO} = \Big(h_\theta(x, y_w, y_l) - \tfrac{1}{2\tau}\Big)^2, \qquad h_\theta = \log\frac{\pi_\theta(y_w|x)}{\pi_{ref}(y_w|x)} - \log\frac{\pi_\theta(y_l|x)}{\pi_{ref}(y_l|x)}$$

At the target margin the gradient is zero: less aggressiveness on easy pairs, more stability on near-deterministic preference data.

### KTO: unpaired binary feedback

KTO (Ethayarajh et al. 2024) fixes DPO's data-format requirement. DPO needs *paired* (chosen, rejected) comparisons for the same prompt. Most production feedback (thumbs up/down on single responses, accept/reject on one suggestion) is unpaired binary good/bad labels with no matched counterfactual. KTO recasts preference learning through Kahneman-Tversky prospect theory. Each example, desirable or undesirable, gets its own loss term pushing its implicit reward above or below a reference point. Separate weights $\lambda_D, \lambda_U$ for desirable and undesirable examples let you rebalance the loss when the data is skewed toward one class, as production logs usually are.

### ORPO: no reference model, one pass

ORPO (Hong et al. 2024) attacks DPO's two-stage cost (SFT, then a separate preference pass against a frozen reference) by removing the reference model entirely. It adds an odds-ratio penalty directly to the SFT loss on the chosen response:

$$\mathcal{L}_{ORPO} = \mathcal{L}_{SFT}(y_w) + \lambda \cdot \mathcal{L}_{OR}, \qquad \mathcal{L}_{OR} = -\log \sigma\Big(\log \frac{\text{odds}_\theta(y_w|x)}{\text{odds}_\theta(y_l|x)}\Big)$$

where $\text{odds}_\theta(y|x) = p_\theta(y|x) / (1 - p_\theta(y|x))$, taken from the policy's own average per-token likelihood. Both terms come from $\pi_\theta$ alone, so SFT and preference optimization merge into one training pass with one model in memory instead of two. The cost is losing the explicit KL anchor that DPO's reference provides.

### SimPO: length normalization

SimPO (Meng et al. 2024) also drops the reference model, but it goes after DPO's length bias. It replaces the reference-relative implicit reward with the sequence's own length-normalized average log-probability, plus a target margin $\gamma$:

$$\mathcal{L}_{SimPO} = -\log\sigma\Big(\frac{\beta}{|y_w|}\sum_t \log\pi_\theta(y_{w,t}|\cdot) \;-\; \frac{\beta}{|y_l|}\sum_t \log\pi_\theta(y_{l,t}|\cdot) \;-\; \gamma\Big)$$

Dividing by sequence length $|y|$ removes the mechanical edge a longer response gets from DPO's un-normalized sum of log-probabilities. Typical SimPO hyperparameters are $\beta \approx 2$–$2.5$ with $\gamma/\beta \approx 0.3$–$0.5$.

### cDPO: label smoothing

A fifth, smaller variant: conservative/robust DPO (cDPO) leaves the loss shape alone. It applies label smoothing with noise rate $\epsilon$ to the standard DPO loss, so that the fraction of flipped or mislabeled pairs you inevitably get at scale with human or [[Concept - Reward Models|RLAIF]] labeling can't dominate the gradient.

## In practice

ORPO and SimPO are attractive on memory grounds. [[Reference - Memory Math for Transformers]] shows why a resident reference model the size of the policy isn't a free line item. But the missing reference is also what removes the KL anchor that keeps the policy tied to a known-fluent distribution, so both are more exposed to the overoptimization dynamics that [[Concept - KL Control in RLHF]] manages in RLHF and DPO.

IPO trades some of DPO's raw effectiveness for stability. It underfits relative to DPO when the preference data is correctly near-deterministic, as opposed to noisy. KTO's advantage is purely about data availability: if all you have is unpaired binary feedback, KTO can use it and DPO can't, regardless of how the two compare on data both could consume.

[[Reference - Post-Training Methods Comparison]] puts these methods side by side on data format, reference-model requirement and typical hyperparameters. [[Decision - Choosing a Preference Optimization Algorithm]] turns that table into a decision procedure.

## Failure modes

**Reference-free drift.** ORPO and SimPO can drift further from fluent language than DPO for the same nominal training budget, because no $\pi_{ref}$ term penalizes it. It looks like [[Concept - Length Bias in Preference Optimization|degenerate or over-optimized outputs]] appearing earlier in training than a DPO run on the same data would show them.

**IPO under-commits.** The bounded loss can plateau before fully separating pairs that are distinguishable, especially with $\tau$ set too large. The model then under-commits to preferences the data supports.

**KTO weighting on skewed logs.** The desirable/undesirable weighting is easy to get wrong on imbalanced production logs (e.g., 95% thumbs-up, 5% thumbs-down). A bad $\lambda_D/\lambda_U$ ratio either lets the model ignore the sparse negative signal or makes it overreact.

**ORPO has no second pass.** With a single stage, a chosen response of poor SFT quality goes straight into the odds-ratio term and nothing later corrects it. DPO's separate stages at least give you sequencing flexibility.

## The non-obvious

None of the four is a universal winner, and that's the useful finding. Tulu 3's ablations (Lambert et al. 2024) show results are dataset- and $\beta$-sensitive enough that the specific loss matters less than whether the preference data gets refreshed on-policy between rounds. Hunting for the objectively best variant is usually optimizing the wrong axis. For any of them, iterating the data (sample fresh completions from the current policy, relabel, retrain) closes more of the gap to full RLHF than switching loss functions does.

## Connections

- [[Concept - Direct Preference Optimization (DPO)]] — the base method every variant here patches one specific weakness of.
- [[Concept - Reward Models]] — the Bradley-Terry preference model this whole family, including DPO, ultimately derives its loss from.
- [[Concept - Length Bias in Preference Optimization]] — the specific failure SimPO's length normalization directly targets.
- [[Reference - Post-Training Methods Comparison]] — the side-by-side table of data format, reference-model need, and hyperparameters across this family.
- [[Decision - Choosing a Preference Optimization Algorithm]] — turns this note's tradeoffs into a concrete choice given data and compute constraints.
- [[Concept - KL Control in RLHF]] — the anchor mechanism ORPO and SimPO give up by dropping the reference model.
- [[Concept - Softmax]] — the Bradley-Terry sigmoid underlying DPO, IPO, and ORPO's odds-ratio loss is built on the same two-class softmax.
- [[Reference - Memory Math for Transformers]] — quantifies the memory savings reference-free methods (ORPO, SimPO) are actually buying.

## Sources

- Azar et al. (2023) — "A General Theoretical Paradigm to Understand Learning from Human Preferences." Introduces IPO's bounded squared loss.
- Ethayarajh et al. (2024) — "KTO: Model Alignment as Prospect Theoretic Optimization." Unpaired binary preference learning via Kahneman-Tversky value functions.
- Hong et al. (2024) — "ORPO: Monolithic Preference Optimization without Reference Model." Odds-ratio penalty merged directly into the SFT loss.
- Meng et al. (2024) — "SimPO: Simple Preference Optimization with a Reference-Free Reward." Length-normalized implicit reward and target margin.
