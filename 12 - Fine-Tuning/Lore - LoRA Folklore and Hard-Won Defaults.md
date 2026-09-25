---
tags: [lore, domain/fine-tuning, level/unicorn]
aliases: [LoRA folklore, LoRA defaults]
summary: "The defaults everyone quietly converged on in LoRA fine-tuning and the incidents behind them, each labeled by evidence status."
---
# Lore - LoRA Folklore and Hard-Won Defaults

The clean mechanism of [[Deep Dive - LoRA]] fits on a page. What doesn't is the pile of defaults, superstitions and rediscovered-the-hard-way fixes the open-model community accumulated between 2021 and 2025, most of it in Reddit threads, blog experiments and Discord logs (the kind of primary sources catalogued in [[Reference - Where Real AI Knowledge Lives]]) and not in papers. Here's that folklore, each item labeled by how far to trust it.

## What happened

### "Apply LoRA to all the linear layers"

The original paper (Hu et al. 2021) adapted only the attention `q` and `v` projections and said that was enough. For two years people copied it as gospel and left quality on the table. The [[Concept - QLoRA]] paper (Dettmers et al. 2023) and Sebastian Raschka's widely read LoRA-from-scratch experiments established the real default: adapt **every** linear layer, attention `q,k,v,o` *and* MLP `gate,up,down`. The reason is mechanistic. Covering the places where adaptation has to happen matters more than the rank of any single adapter, so broadening `target_modules` recovers more of the full-fine-tuning gap than raising `r`. *Evidence: well-sourced.*

### The `alpha = 2r` cargo cult

Some repo example set `lora_alpha=32, r=16`, and the whole field copied it without realizing $\alpha/r$ is an **update scale**, not a magic pair. People carry `alpha=32` from config to config while changing `r`, rescaling their effective learning rate every time without noticing (the trap is dissected in [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]]). The `alpha = 2r` heuristic just holds $\alpha/r \approx 2$ while you sweep rank. It's a sane convention, but it came from example code, not theory, and treating it as law is how people end up training at an effective LR they never chose. *Evidence: folklore, well-sourced.*

### "Rank doesn't matter past 16"

For years the received wisdom was that rank above 16 or 32 bought nothing. That was an artifact of the standard $\alpha/r$ scaling, not a property of LoRA. The scaling makes the adapter's contribution shrink like $1/r$ as rank grows, so higher-rank runs trained sluggishly and looked like they'd plateaued. Kalajdzievski (2023) showed that scaling by $\alpha/\sqrt{r}$ instead (rank-stabilized LoRA) makes higher ranks help, giving hard domains the capacity they need. The "rank ceiling" was a measurement artifact all along. *Evidence: verified.*

### The QLoRA democratization moment

In May 2023 QLoRA's headline, *fine-tune a 65B model on a single 48GB GPU in 24 hours*, landed just as the leaked LLaMA weights were spreading, and it blew up. Fine-tuning went overnight from a datacenter activity to something a hobbyist with one used 3090/4090 could do. The r/LocalLLaMA fine-tuning explosion, the Guanaco models, and the tooling wave that became axolotl and [[Breakdown - Unsloth]] all trace to that one memory result. It's the closest thing fine-tuning has to a "big bang" date. *Evidence: verified history.*

### "LoRA can't learn this" (it's your learning rate)

Only the small `A`,`B` factors train, so LoRA wants a learning rate roughly **10x higher** than full fine-tuning: around 1e-5 to 2e-5 for full FT of a 7B, around 1e-4 to 3e-4 for LoRA (ranges in [[Reference - Fine-Tuning Hyperparameters]]). The most common silent failure is running LoRA at a full-FT-scale LR, watching the loss barely move, and deciding "LoRA can't learn this task." Nine times out of ten it's under-training from a too-low LR, not a capacity limit. *Evidence: well-sourced folklore.*

### "My fine-tune got dumber"

Two horror stories, each rediscovered independently by dozens of teams:

1. **Narrow SFT nukes general ability.** [[Concept - Supervised Fine-Tuning (SFT)|Fine-tune]] hard on a narrow format (say, JSON classification) and the model forgets how to hold a conversation, textbook [[Concept - Catastrophic Forgetting|catastrophic forgetting]]. The fix, found again and again, is *replay*: mix 5-30% general instruction data back into the training set. The replay ratio is the knob that matters, and most first attempts leave it out.
2. **The merge that shipped worse than the adapter.** People trained a QLoRA, merged it straight into the 4-bit base, and shipped a model measurably *worse* than the adapter-on-4bit they'd tested. Merging re-rounds $W + \Delta W$ back through NF4, compounding quantization error ([[Concept - Floating Point for Deep Learning|floating-point]] rounding isn't free). "Dequantize to fp16, *then* merge" had to become lore before it stopped happening. *Evidence: well-sourced folklore.*

### The three-epoch superstition

"Train for 3 epochs" comes from a small-dataset world and gets copied everywhere. On a large dataset it's often wrong: one epoch is frequently right, and three epochs on a small set is a fast route to memorization (verbatim regurgitation, eval loss rising while train loss falls). The number is a default, never a target. *Evidence: folklore, weakly sourced.*

## The lesson

Nearly all of these have one root. LoRA exposes two coupled knobs, rank and $\alpha$, and their *product with the learning rate* is what controls training; the community tuned each knob as if it were independent. `alpha=2r`, the rank ceiling, the "10x LR" and the scaling collapse are the same confusion seen from different sides. Fix the $\alpha$ scaling first (or use rank-stabilized scaling), *then* tune the learning rate, and half the folklore goes away. The other half (replay data, dequantize-before-merge, one vs three epochs) is a standing reminder that a fine-tune usually fails through **regression you didn't measure**, not a task it couldn't learn.

## Evidence status

| Claim | Status | Anchor |
|---|---|---|
| All-linear targets beat q,v-only | Well-sourced | QLoRA appendix; Raschka's experiments |
| `alpha = 2r` is convention, not theory | Folklore, well-sourced | Origin is repo examples |
| Rank ceiling was a scaling artifact | **Verified** | Kalajdzievski 2023 (rsLoRA) |
| QLoRA democratization (2023) | **Verified history** | Dettmers et al. 2023; r/LocalLLaMA record |
| LoRA wants ~10x the full-FT LR | Well-sourced folklore | Community-wide default, not a formal result |
| Narrow SFT forgets; replay fixes it | Well-sourced | Biderman et al. 2024; repeatedly rediscovered |
| Dequantize-then-merge for QLoRA | Well-sourced folklore | Reproducible; now standard practice |
| Three epochs is often wrong | Folklore, weakly sourced | Inherited small-dataset default |

## Connections
- [[Deep Dive - LoRA]] — the clean mechanism this note is the folklore counterpart to.
- [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]] — the formal result behind the "rank doesn't matter past 16" and `alpha=2r` folklore.
- [[Concept - QLoRA]] — the paper whose memory result set off the whole democratization wave.
- [[Concept - Why LoRA Underperforms Full Fine-Tuning]] — the mechanistic account of when "LoRA can't learn this" is real versus an under-training artifact.
- [[Concept - Catastrophic Forgetting]] — the "got dumber" failure and the replay-ratio fix rediscovered again and again.
- [[Reference - Fine-Tuning Hyperparameters]] — where the folklore defaults (LR, epochs, rank, alpha) are written down as numbers.
- [[Breakdown - Unsloth]] — part of the tooling wave the QLoRA moment kicked off.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the objective whose narrow application triggers the forgetting horror story.
- [[Concept - Floating Point for Deep Learning]] — why merging into a 4-bit base compounds rounding error and ships a worse model.
- [[Reference - Where Real AI Knowledge Lives]] — the forums, blogs, and threads where this folklore actually lives.

## Sources
- Hu et al. (2021) — *LoRA.* The q,v-only default that the community later outgrew.
- Dettmers et al. (2023) — *QLoRA.* The democratization moment and the dequantize-before-merge caveat.
- Kalajdzievski (2023) — *A Rank Stabilization Scaling Factor for Fine-Tuning with LoRA.* Turns the "rank ceiling" folklore into a corrected scaling rule.
- Biderman et al. (2024) — *LoRA Learns Less and Forgets Less.* Grounds the "got dumber" and forgetting lore in measurement.
- Raschka (2023-2024) — LoRA-from-scratch experiment series. Primary source for the all-linear-targets default and LR folklore.
