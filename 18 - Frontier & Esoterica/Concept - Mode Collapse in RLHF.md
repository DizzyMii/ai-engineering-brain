---
tags: [concept, domain/esoterica, level/frontier]
aliases: [diversity collapse, RLHF homogenization, GPT-isms, output diversity loss, alignment tax on diversity]
summary: "Preference optimization narrows the policy onto a few high-reward completions, trading diversity for reward — the source of GPT-isms."
---
> **One-paragraph hook:** Sample the same prompt from an SFT checkpoint at temperature 1.0 and you get a spread of different completions. Sample the RLHF'd version of the same model and the outputs collapse toward one or two "typical," safe, high-reward answers, and turning the temperature back up barely helps. This diversity collapse ("mode collapse") isn't a bug in some particular run. The KL-regularized preference objective produces it, and it's reward over-optimization seen from the distribution side. It's why best-of-$n$ gains erode after alignment, why synthetic-data generators are deliberately left un-aligned, and why every aligned model picks up the same lexical tics.

## The mechanism
Kirk et al. 2023 ("Understanding the Effects of RLHF on LLM Generalisation and Diversity") ran the controlled comparison. Relative to the SFT starting point, RLHF (PPO) *improves* out-of-distribution generalization but *sharply cuts* output diversity, both across samples (different seeds, same prompt) and per input. The finding that matters in practice: the collapse **persists at high sampling temperature**. You can't dial diversity back with temperature, because the modes were lost in the shape of the distribution, and temperature only changes how sharply you sample from it. Best-of-$n$ collapses diversity less than PPO; PPO is where it's worst.

The objective causes it. [[Deep Dive - RLHF End to End|RLHF]] maximizes a reward $r_\phi$ under a [[Concept - KL Divergence]] leash to the reference (SFT) policy:

$$\max_{\pi_\theta}\ \mathbb{E}_{x,\,y\sim\pi_\theta}\big[r_\phi(x,y)\big] \;-\; \beta\, D_{\mathrm{KL}}\!\big(\pi_\theta(\cdot\mid x)\,\|\,\pi_{\text{ref}}(\cdot\mid x)\big)$$

The reward term pays the policy to move probability mass onto whatever the [[Concept - Reward Models]] scores highly. The KL penalty and any entropy bonus are meant to keep the policy near the diverse reference. In practice the reward gradient wins and the distribution sharpens onto a narrow **"typical set"** of completions that maximize expected reward: polite, hedged, well-formatted, medium-length, predictable in structure. The reward model has its own biases (length, formatting, politeness, refusal reflexes), and RLHF copies them faithfully into the policy's *style*. The model ends up with the reward model's and the annotator pool's mannerisms.

Reward over-optimization is the same object. Gao et al. 2022 ("Scaling Laws for Reward Model Overoptimization") showed that as you optimize the proxy reward, the *gold* (true) reward rises and then falls, a Goodhart curve, and it follows a predictable concave function of $d = \sqrt{D_{\mathrm{KL}}(\pi_\theta \,\|\, \pi_{\text{ref}})}$ measured in nats. Proxy reward climbs monotonically while true quality peaks and declines. The KL distance at the peak is where you've spent your diversity to buy reward. Over-optimization is what happens to *quality* as $d$ grows; collapse is what happens to the *distribution's entropy* over the same $d$. [[Concept - Reward Hacking]] covers the extreme, where the policy exploits the reward model outright.

## In practice
A collapsed policy leaves recognizable fingerprints, the homogenization people call **GPT-isms**:
- Canned openers: "As an AI language model…", "I'd be happy to help", "It's important to note that…".
- Lexical tics: *delve*, *tapestry*, *boasts*, *underscores*, *a testament to*, *navigating the landscape*.
- List-and-bold formatting on prompts that never asked for structure.
- Near-identical samples across seeds, and a flat "corporate-neutral" register whatever the persona instruction says.

They're diagnostic. If fine-tuning on your own data reproduces these tics, your data was distilled from an aligned model and carries its collapse. An [[Concept - LLM-as-Judge]] tends to reward the same tics, so scoring or filtering data with a judge can reinforce the collapse it ought to catch.

DPO and other offline methods collapse too, sometimes worse. [[Concept - Direct Preference Optimization (DPO)]] optimizes a margin between chosen and rejected responses, and a well-documented dynamic is that it grows the margin partly by pushing *down* the shared probability mass of the pair. The *rejected* response's log-probability falls fast, and the *chosen* response's likelihood often falls too, so the policy sharpens onto a narrow mode that isn't even the preferred completion. [[Concept - Length Bias in Preference Optimization]] adds to it: length is the easiest signal to exploit, so collapsed policies also drift long.

Every mitigation trades against reward:
- Lower the KL target / raise $\beta$, staying closer to the diverse reference at a cost in alignment strength.
- Entropy targeting during RL, holding a floor on policy entropy (see [[Concept - Entropy Collapse and Exploration in RL Fine-Tuning]]).
- Periodic **SFT re-anchoring**: interleave supervised steps to pull the policy back toward the diverse manifold.
- Keep a *separate, less-aligned or higher-temperature generator* checkpoint for synthetic data and best-of-$n$, and serve the aligned one only at the final hop.

## Failure modes
- **Best-of-$n$ silently stops working.** After RLHF the $n$ samples are near-duplicates, so you pay $n\times$ compute for about one effective sample and the reranking gain flattens. Detection: compare distinct-$n$ or self-BLEU across the $n$ candidates before and after alignment. If candidate diversity cratered, the BoN budget is wasted.
- **Synthetic data inherits the collapse.** Data generated by a collapsed model is low-diversity and narrows the *next* model further, a homogenization ratchet across model generations.
- **Creative and brainstorming tasks degrade** while benchmark scores rise. The model gives the same three ideas every time. Detection: human diversity ratings or embedding-space spread of sampled outputs.
- **Temperature is a false remedy.** Higher temperature broadens sampling *around the same narrow attractor*. It adds noise and brings back no lost modes. If diversity hasn't recovered by ~temperature 1.2, the modes are gone, not hidden.

## The non-obvious
Teams treat diversity loss as a *sampling* problem to fix at inference. It's a **distributional** problem baked in during training: RLHF deletes modes from the policy, and no temperature can resample a mode with zero mass. So the fix is a pipeline decision. If you need diversity (BoN reranking, RL data generation, synthetic corpora, creative product surfaces), **keep a diverse checkpoint upstream** (lightly aligned or SFT-only) and use the fully aligned model only for the final user-facing response. You spend diversity during alignment and can't mint it back at decode time. It also feeds [[Concept - Neural Text Degeneration and Repetition Loops]]: a narrowed distribution has a deeper repetition attractor, so aligned models loop more readily under greedy or low-temperature decoding than their SFT ancestors.

**Open question:** how much of the collapse is *intrinsic* to alignment (any strong preference signal must reduce entropy), and how much is an artifact of *narrow reward models and homogeneous annotator pools*? If mostly the latter, more diverse preference data and reward-model ensembles should recover diversity at fixed alignment strength. If the former, there's a hard Pareto frontier between how aligned and how diverse a single policy can be.

## Connections
- [[Deep Dive - RLHF End to End]] — the full pipeline this note describes a pathology of; read it for the PPO/reference-KL machinery that produces the collapse.
- [[Concept - Reward Hacking]] — the extreme of over-optimization: where the collapsed policy exploits the reward model outright rather than merely narrowing.
- [[Concept - Reward Models]] — the down-link: the RM's own biases (length, format, politeness) are exactly what get copied into the policy's collapsed style.
- [[Concept - Direct Preference Optimization (DPO)]] — offline preference optimization collapses too, and its likelihood-suppression dynamic can be worse than PPO's.
- [[Concept - Neural Text Degeneration and Repetition Loops]] — a narrowed post-RLHF distribution has a deeper repetition attractor; the two failures compound at decode time.
- [[Concept - KL Divergence]] — the leash in the RLHF objective and the axis ($\sqrt{\mathrm{KL}}$) along which Gao et al. measure over-optimization; the quantity you trade for reward.
- [[Concept - LLM-as-Judge]] — collapsed models exhibit the format/length tics that judge models reward, closing a homogenization loop when a judge is used to score or filter outputs.
- [[Concept - Length Bias in Preference Optimization]] — the up-link: the single easiest reward signal to exploit, which compounds collapse by pushing the policy long.
- [[Concept - Entropy Collapse and Exploration in RL Fine-Tuning]] — the RL-training view of the same entropy loss, and the entropy-targeting mitigation that fights it.

## Sources
- Kirk, Mediratta, Nalmpantis, Luketina, Grefenstette, Rocktäschel & others (2023) — "Understanding the Effects of RLHF on LLM Generalisation and Diversity". Shows RLHF improves OOD generalization but reduces per-input and across-sample diversity, and that temperature does not recover it.
- Gao, Schulman & Hilton (2022) — "Scaling Laws for Reward Model Overoptimization". Gold reward is a concave function of $\sqrt{\mathrm{KL}}$; proxy reward keeps rising as true quality falls (Goodhart).
- Rafailov, Sharma, Mitchell, Ermon, Manning & Finn (2023) — "Direct Preference Optimization". The margin objective whose likelihood-suppression dynamic drives offline collapse.
