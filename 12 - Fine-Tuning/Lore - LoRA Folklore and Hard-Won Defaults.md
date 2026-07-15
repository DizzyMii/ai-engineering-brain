---
tags: [lore, domain/fine-tuning, level/unicorn]
aliases: [LoRA folklore, LoRA defaults]
summary: "The defaults everyone quietly converged on in LoRA fine-tuning and the incidents behind them, each labeled by evidence status."
---
# Lore - LoRA Folklore and Hard-Won Defaults

The clean mechanism of [[Deep Dive - LoRA]] fits on a page. What doesn't fit on a page is the pile of defaults, superstitions, and rediscovered-the-hard-way fixes that the open-model community accreted between 2021 and 2025 — most of it living in Reddit threads, blog experiments, and Discord logs (the kind of primary sources catalogued in [[Reference - Where Real AI Knowledge Lives]]) rather than papers. This is that folklore, each item labeled by how much you should trust it.

## What happened

### "Apply LoRA to all the linear layers"

The original paper (Hu et al. 2021) adapted only the attention `q` and `v` projections and reported that this was enough. For two years people copied that as gospel and quietly left quality on the table. The [[Concept - QLoRA]] paper (Dettmers et al. 2023) and Sebastian Raschka's widely-read LoRA-from-scratch experiment series established the real default: adapt **every** linear layer — attention `q,k,v,o` *and* the MLP `gate,up,down`. The reason is mechanistic — coverage of where the adaptation needs to happen matters more than the rank of any single adapter, so broadening `target_modules` recovers more of the full-fine-tuning gap than raising `r` does. *Evidence: well-sourced.*

### The `alpha = 2r` cargo cult

Somewhere a repo example set `lora_alpha=32, r=16` and the whole field copied it without understanding that $\alpha/r$ is an **update scale**, not a magic pair. People carry `alpha=32` from config to config while changing `r`, silently rescaling their effective learning rate every time (the trap dissected in [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]]). The `alpha = 2r` heuristic is just a way to hold $\alpha/r \approx 2$ as you sweep rank — a sane convention, but its origin is example code, not theory, and treating it as a law is how people end up training at an effective LR they never chose. *Evidence: folklore, well-sourced.*

### "Rank doesn't matter past 16"

For years the received wisdom was that raising rank above 16 or 32 bought nothing. This was **not** a property of LoRA — it was an artifact of the standard $\alpha/r$ scaling, which makes the adapter's contribution shrink like $1/r$ as rank grows, so higher-rank runs trained sluggishly and appeared to plateau. Kalajdzievski (2023) showed that scaling by $\alpha/\sqrt{r}$ instead (rank-stabilized LoRA) makes higher ranks actually help, unlocking the capacity that hard domains need. The "rank ceiling" was a measurement artifact all along. *Evidence: verified.*

### The QLoRA democratization moment

In May 2023, QLoRA's headline — *fine-tune a 65B model on a single 48GB GPU in 24 hours* — hit at exactly the moment the leaked LLaMA weights were spreading, and it detonated. Overnight, fine-tuning went from a datacenter activity to something a hobbyist with one used 3090/4090 could do. The r/LocalLLaMA fine-tuning explosion, the Guanaco models, and the tooling wave that became axolotl and [[Breakdown - Unsloth]] all trace to that single memory result. It is the closest thing fine-tuning has to a "big bang" date. *Evidence: verified history.*

### "LoRA can't learn this" (it's your learning rate)

Because only the small `A`,`B` factors train, LoRA wants a learning rate roughly **10x higher** than full fine-tuning — full FT of a 7B runs around 1e-5 to 2e-5, LoRA around 1e-4 to 3e-4 (the ranges in [[Reference - Fine-Tuning Hyperparameters]]). The single most common silent failure is running LoRA at a full-FT-scale LR, watching the loss barely move, and concluding "LoRA can't learn this task." Nine times out of ten it's under-training from a too-low LR, not a capacity limit. *Evidence: well-sourced folklore.*

### "My fine-tune got dumber"

Two horror stories, each rediscovered independently by dozens of teams:

1. **Narrow SFT nukes general ability.** [[Concept - Supervised Fine-Tuning (SFT)|Fine-tune]] hard on a narrow format (say, JSON classification) and the model forgets how to hold a conversation — textbook [[Concept - Catastrophic Forgetting|catastrophic forgetting]]. The fix, rediscovered again and again, is *replay*: mix 5-30% general instruction data back into your training set. The replay ratio is the load-bearing knob, and it's absent from most first attempts.
2. **The merge that shipped worse than the adapter.** People trained a QLoRA, merged it straight into the 4-bit base, and shipped a model measurably *worse* than the adapter-on-4bit they tested. Cause: merging re-rounds $W + \Delta W$ back through NF4, compounding quantization error (the [[Concept - Floating Point for Deep Learning|floating-point]] rounding is not free). "Dequantize to fp16, *then* merge" had to become lore before it stopped happening. *Evidence: well-sourced folklore.*

### The three-epoch superstition

"Train for 3 epochs" is inherited from a small-dataset world and copied everywhere. On a large dataset it's often wrong — a single epoch is frequently the right call, and three epochs on a small set is a fast route to memorization (verbatim regurgitation, eval loss rising while train loss falls). The number is a default, never a target. *Evidence: folklore, weakly sourced.*

## The lesson

Nearly every one of these traces to the same root: LoRA exposes two coupled knobs — rank and $\alpha$ — whose *product with the learning rate* is what actually controls training, and the community optimized each knob in isolation as if it were independent. `alpha=2r`, the rank ceiling, the "10x LR", and the scaling collapse are all the same confusion viewed from different angles. Fix the $\alpha$ scaling first (or use rank-stabilized scaling), *then* tune the learning rate, and half the folklore evaporates. The other half — replay data, dequantize-before-merge, one-vs-three epochs — is the standing reminder that a fine-tune's failure mode is usually **regression you didn't measure**, not a task it couldn't learn.

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
