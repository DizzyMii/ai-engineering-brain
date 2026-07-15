---
tags: [concept, domain/post-training, level/advanced]
aliases: [IPO, KTO, ORPO, SimPO, cDPO, DPO variants]
summary: "IPO, KTO, ORPO, and SimPO: what each post-DPO offline preference algorithm fixes, and the reference-model-memory tradeoffs each makes."
---

> **One-paragraph hook:** [[Concept - Direct Preference Optimization (DPO)]] shipped in 2023 with three specific weaknesses — it overfits on near-deterministic preference pairs, it requires paired comparisons rather than the thumbs-up/down data most products actually collect, and it exploits length. IPO, KTO, ORPO, and SimPO are not competing reinventions of DPO; each is a targeted patch for exactly one of those weaknesses, and reading them as a family rather than four unrelated papers is the fastest way to pick the right one for a given data situation.

## The mechanism

**IPO** (Azar et al. 2023) fixes DPO's overfitting failure mode. DPO's log-sigmoid loss keeps pushing the implicit reward margin toward infinity whenever a pair is easily separable — the gradient never fully vanishes, so probabilities get driven to extremes even on pairs the model already ranks correctly. IPO replaces the log-sigmoid with a bounded squared loss around a finite target margin $1/(2\tau)$:

$$\mathcal{L}_{IPO} = \Big(h_\theta(x, y_w, y_l) - \tfrac{1}{2\tau}\Big)^2, \qquad h_\theta = \log\frac{\pi_\theta(y_w|x)}{\pi_{ref}(y_w|x)} - \log\frac{\pi_\theta(y_l|x)}{\pi_{ref}(y_l|x)}$$

Once the margin reaches the target, the gradient is zero rather than still pushing outward — trading some of DPO's aggressiveness on easy pairs for stability on near-deterministic preference data.

**KTO** (Ethayarajh et al. 2024) fixes DPO's data-format requirement. DPO needs *paired* (chosen, rejected) comparisons for the same prompt; most production feedback — thumbs up/down on individual responses, accept/reject on a single suggestion — is unpaired binary good/bad labels with no matched counterfactual. KTO reframes preference learning through Kahneman-Tversky prospect theory: each example, desirable or undesirable, gets its own loss term pushing its implicit reward above or below a reference point, with separate weights $\lambda_D, \lambda_U$ for desirable and undesirable examples so the loss can be rebalanced when the data (as production logs usually are) is skewed toward one class.

**ORPO** (Hong et al. 2024) fixes the two-stage cost of DPO — SFT followed by a separate preference-optimization pass against a frozen reference — by removing the reference model entirely. It adds an odds-ratio penalty directly to the SFT loss on the chosen response:

$$\mathcal{L}_{ORPO} = \mathcal{L}_{SFT}(y_w) + \lambda \cdot \mathcal{L}_{OR}, \qquad \mathcal{L}_{OR} = -\log \sigma\Big(\log \frac{\text{odds}_\theta(y_w|x)}{\text{odds}_\theta(y_l|x)}\Big)$$

where $\text{odds}_\theta(y|x) = p_\theta(y|x) / (1 - p_\theta(y|x))$ from the policy's own average per-token likelihood. Because both terms are computed from $\pi_\theta$ alone, ORPO merges SFT and preference optimization into a single training pass with no resident reference model — one model in memory instead of two, at the cost of losing the explicit KL anchor DPO's reference provides.

**SimPO** (Meng et al. 2024) also drops the reference model, but targets DPO's length bias directly. It replaces DPO's reference-relative implicit reward with the length-normalized average log-probability of the sequence itself, plus a target margin $\gamma$:

$$\mathcal{L}_{SimPO} = -\log\sigma\Big(\frac{\beta}{|y_w|}\sum_t \log\pi_\theta(y_{w,t}|\cdot) \;-\; \frac{\beta}{|y_l|}\sum_t \log\pi_\theta(y_{l,t}|\cdot) \;-\; \gamma\Big)$$

Dividing by sequence length $|y|$ removes the mechanical advantage a longer response gets from DPO's un-normalized sum of log-probabilities (more tokens summed is not the same as higher per-token quality); typical SimPO hyperparameters run $\beta \approx 2$–$2.5$ with $\gamma/\beta \approx 0.3$–$0.5$.

A fifth, smaller variant worth naming: conservative/robust DPO (cDPO) doesn't change the loss shape at all, it applies label smoothing with a noise rate $\epsilon$ to the standard DPO loss so that a fraction of flipped or mislabeled preference pairs — inevitable at scale with human or [[Concept - Reward Models|RLAIF]] labeling — don't dominate the gradient.

## In practice

The reference-free methods (ORPO, SimPO) are attractive on memory grounds — see [[Reference - Memory Math for Transformers]] for why a resident reference model at the same parameter count as the policy is not a free line item — but that same missing reference is exactly what removes the KL anchor keeping the policy tethered to a known-fluent distribution, so both are more exposed to the same overoptimization dynamics that [[Concept - KL Control in RLHF]] exists to manage in RLHF and DPO. IPO trades some of DPO's raw effectiveness for stability, which shows up as underfitting relative to DPO on preference data that is genuinely, correctly near-deterministic rather than noisy. KTO's advantage is entirely about data availability: if the only signal available is unpaired binary feedback, it is usable where DPO simply is not, independent of any quality comparison on data both methods could consume. [[Reference - Post-Training Methods Comparison]] tabulates these methods side by side on data format, reference-model requirement, and typical hyperparameters, and [[Decision - Choosing a Preference Optimization Algorithm]] turns that table into a decision procedure.

## Failure modes

Reference-free training (ORPO, SimPO) can drift further from fluent language than DPO would for the same nominal training budget, precisely because there is no $\pi_{ref}$ term penalizing that drift — the failure looks like [[Concept - Length Bias in Preference Optimization|degenerate or over-optimized outputs]] appearing earlier in training than a DPO run on the same data would show them. IPO's bounded loss can plateau before fully separating genuinely distinguishable pairs, especially with $\tau$ set too large, producing a model that under-commits to preferences the data actually supports. KTO's separate desirable/undesirable weighting is easy to get wrong on imbalanced production logs (e.g., 95% thumbs-up, 5% thumbs-down): a poorly chosen $\lambda_D/\lambda_U$ ratio either lets the model ignore the sparse negative signal entirely or overreacts to it. ORPO's single-stage design means a bad SFT-quality chosen response propagates directly into the odds-ratio term with no later pass to correct it, whereas DPO's separate stages at least offer sequencing flexibility.

## The non-obvious

There is no universal winner among these four, and that is itself the useful finding: Tulu 3's ablations (Lambert et al. 2024) show results are dataset- and $\beta$-sensitive enough that the specific loss function matters less than whether the preference data is refreshed on-policy between rounds. Teams that spend their engineering budget hunting for the objectively-best variant among IPO/KTO/ORPO/SimPO are usually optimizing the wrong axis — iterating the data (sampling fresh completions from the current policy, relabeling, retraining) closes more of the quality gap to full RLHF than switching loss functions does, for any of them.

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
