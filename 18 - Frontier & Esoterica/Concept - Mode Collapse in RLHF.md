---
tags: [concept, domain/esoterica, level/frontier]
aliases: [diversity collapse, RLHF homogenization, GPT-isms, output diversity loss, alignment tax on diversity]
summary: "Preference optimization narrows the policy onto a few high-reward completions, trading diversity for reward — the source of GPT-isms."
---
> **One-paragraph hook:** Run the same prompt through an SFT checkpoint at temperature 1.0 and you get a spread of genuinely different completions. Run it through the RLHF'd version of the same model and the samples collapse toward one or two "typical," safe, high-reward answers — and cranking the temperature back up barely helps. This diversity collapse ("mode collapse") is not a bug in a particular run; it is what the KL-regularized preference objective *does*, and it is the same phenomenon as reward over-optimization viewed from the distribution side. It is why best-of-$n$ gains erode after alignment, why synthetic-data generators are kept un-aligned on purpose, and why every aligned model develops the same lexical tics.

## The mechanism
Kirk et al. 2023 ("Understanding the Effects of RLHF on LLM Generalisation and Diversity") ran the controlled comparison: relative to the SFT starting point, RLHF (PPO) *improves* out-of-distribution generalization but *sharply reduces* output diversity — both across-sample diversity (different seeds, same prompt) and per-input diversity. The critical finding for practitioners is that the collapse **persists at high sampling temperature**: you cannot dial diversity back with temperature because the loss of modes happened in the shape of the distribution, not in how sharply you sample from it. Best-of-$n$ collapses diversity less than PPO, but PPO is where the effect is worst.

The mechanism is the objective itself. [[Deep Dive - RLHF End to End|RLHF]] maximizes a reward $r_\phi$ under a [[Concept - KL Divergence]] leash to the reference (SFT) policy:

$$\max_{\pi_\theta}\ \mathbb{E}_{x,\,y\sim\pi_\theta}\big[r_\phi(x,y)\big] \;-\; \beta\, D_{\mathrm{KL}}\!\big(\pi_\theta(\cdot\mid x)\,\|\,\pi_{\text{ref}}(\cdot\mid x)\big)$$

The reward term rewards the policy for moving probability mass onto the region the [[Concept - Reward Models]] scores highly. The KL penalty and any entropy bonus are supposed to hold the policy near the diverse reference — but in practice the reward gradient wins, and the distribution sharpens onto a narrow **"typical set"** of completions that maximize expected reward: polite, hedged, well-formatted, medium-length, structurally predictable. The reward model has its own biases (length, formatting, politeness, refusal reflexes), and RLHF faithfully copies them into the policy's *style*. That is the real content of the phenomenon: the model's mannerisms become the reward model's and the annotator pool's mannerisms.

This is the same object as **reward over-optimization**. Gao et al. 2022 ("Scaling Laws for Reward Model Overoptimization") showed that as you optimize the proxy reward, the *gold* (true) reward rises then falls — a Goodhart curve — and it does so as a predictable concave function of $d = \sqrt{D_{\mathrm{KL}}(\pi_\theta \,\|\, \pi_{\text{ref}})}$ measured in nats. The proxy reward climbs monotonically while true quality peaks and declines; the KL distance at which it peaks is where you have spent your diversity to buy reward. Mode collapse and over-optimization are the same coin: over-optimization is what happens to *quality* as $d$ grows, collapse is what happens to the *distribution's entropy* over the same $d$. See [[Concept - Reward Hacking]] for the failure at the extreme, where the policy exploits the reward model outright.

## In practice
The observable fingerprints of a collapsed policy — the homogenization practitioners call **GPT-isms**:
- Canned openers: "As an AI language model…", "I'd be happy to help", "It's important to note that…".
- Lexical tics: *delve*, *tapestry*, *boasts*, *underscores*, *a testament to*, *navigating the landscape*.
- List-and-bold formatting reflexes on prompts that never asked for structure.
- Near-identical samples across seeds; flattened, "corporate-neutral" register regardless of persona instruction.

These are diagnostic: if fine-tuning on your own data reproduces these exact tics, your data was distilled from an aligned model and carries its collapse. The same tics are what an [[Concept - LLM-as-Judge]] tends to reward, so scoring or filtering data with a judge can quietly reinforce the very collapse it should be catching.

**DPO and offline methods collapse too — sometimes worse.** [[Concept - Direct Preference Optimization (DPO)]] optimizes a margin between chosen and rejected responses, but a well-documented dynamic is that DPO drives up the margin partly by pushing *down* the shared probability mass of the chosen–rejected pair: the log-probability of the *rejected* response falls fast, and the *chosen* response's likelihood often falls too, so the policy sharpens onto a narrow mode that isn't even the preferred completion. [[Concept - Length Bias in Preference Optimization]] compounds it — length is the easiest signal to exploit, so collapsed policies also drift long.

Mitigations, all of which trade against reward:
- Lower the KL target / raise $\beta$ (stay closer to the diverse reference — costs alignment strength).
- Entropy targeting during RL (hold a floor on policy entropy — see [[Concept - Entropy Collapse and Exploration in RL Fine-Tuning]]).
- Periodic **SFT re-anchoring** (interleave supervised steps to pull the policy back toward the diverse manifold).
- Keep a *separate, less-aligned or higher-temperature generator* checkpoint for synthetic-data generation and best-of-$n$, and serve the aligned one only at the final hop.

## Failure modes
- **Best-of-$n$ silently stops working.** After RLHF the $n$ samples are near-duplicates, so you pay $n\times$ compute for roughly one effective sample and the reranked quality gain flattens. Detection: measure distinct-$n$ or self-BLEU across the $n$ candidates before and after alignment; if candidate diversity cratered, your BoN budget is being wasted.
- **Synthetic data inherits the collapse.** Generating training data from a collapsed model produces a low-diversity corpus that narrows the *next* model further — a homogenization ratchet across model generations.
- **Creative and brainstorming tasks degrade** even as benchmark scores rise; the model gives the same three ideas every time. Detection: human diversity rating or embedding-space spread of sampled outputs.
- **Temperature is a false remedy.** Raising temperature broadens sampling *around the same narrow attractor* — it adds noise, not lost modes. If diversity doesn't recover by ~temperature 1.2, the modes are gone, not hidden.

## The non-obvious
The mistake teams make is treating diversity loss as a *sampling* problem fixable at inference time. It is a **distributional** problem baked in at training time: RLHF deletes modes from the policy, and no temperature setting can resample a mode that has zero mass. The practical consequence is architectural, not tactical — if you need diversity (BoN reranking, RL data generation, synthetic corpora, creative product surfaces), you must **preserve a diverse checkpoint upstream** (a lightly-aligned or SFT-only generator) and reserve the fully-aligned model for the final, user-facing response. Diversity is a resource you spend during alignment; you cannot mint it back at decode time. This is also why it feeds directly into [[Concept - Neural Text Degeneration and Repetition Loops]]: a collapsed, narrowed distribution has a deeper repetition attractor, so aligned models loop more readily under greedy or low-temperature decode than their SFT ancestors did.

**Open question:** how much of the collapse is *intrinsic* to alignment (any strong preference signal must reduce entropy) versus an artifact of *narrow reward models and homogeneous annotator pools*. If it is mostly the latter, more diverse preference data and reward-model ensembles should recover diversity at fixed alignment strength; if it is the former, there is a hard Pareto frontier between how aligned and how diverse a single policy can be.

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
