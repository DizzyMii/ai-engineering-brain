---
tags: [concept, domain/inference-serving, level/unicorn]
aliases: [min-p, Mirostat, DRY, XTC, locally typical sampling, tail-free sampling, top-a]
summary: "The community sampler zoo beyond temperature/top-p — min-p, Mirostat, DRY, XTC — the mechanism of each and the folklore of when it helps."
---
> **One-paragraph hook:** Almost everything past `temperature`, `top_k`, and `top_p` was invented not in a lab but on GitHub and Reddit by people running local models on consumer GPUs, trying to make a 7B model stop looping or stop being boring. The result is a genuine zoo of samplers — min-p, Mirostat, DRY, XTC, typical, tail-free — each of which is a small, principled fix for a *specific* failure of the vanilla pipeline. Most of the "which is best" knowledge is well-sourced folklore rather than benchmarked fact, which is exactly why it's worth writing down: this is where the tribal knowledge of decoding actually lives.

## The mechanism

All of these operate on the same object as the standard pipeline — the post-temperature probability vector — and differ only in *how they truncate or reweight it*. Start from [[Concept - Sampling and Decoding Parameters]] as the baseline; these are the interesting deviations.

**min-p (Nguyen et al. 2024, "Turning Up the Heat").** Top-p's flaw is that its cutoff is an *absolute* cumulative-mass threshold and therefore blind to how confident the model is. min-p makes the cutoff *relative* to the top token:

$$p_{\text{thresh}} = \texttt{min\_p} \cdot p_{\max}, \qquad \text{keep token } i \iff p_i \ge p_{\text{thresh}}$$

where $p_{\max} = \max_i p_i$ on the post-temperature [[Concept - Softmax]] distribution. When the model is certain ($p_{\max} \approx 0.9$) the threshold is high and few tokens survive; when it's genuinely unsure ($p_{\max} \approx 0.1$) the threshold is low and many survive. This is the key win: min-p stays coherent at *high* temperature, because even after you flatten the distribution the surviving set is still gated by the leader's confidence — whereas top-p at high `T` happily admits the garbage tail. Typical `min_p` is `0.05–0.1`, and it composes with (usually a higher) temperature.

**Mirostat (Basu et al. 2020).** A feedback controller for perplexity. You set a target surprise $\tau$ (the desired per-token cross-entropy, i.e. the "interestingness" setpoint); Mirostat dynamically adjusts a truncation parameter $\mu$ each step to keep the *observed* surprise near $\tau$. Concretely it truncates tokens whose surprise $-\log_2 p_i$ exceeds $\mu$, samples, measures the realized surprise $S$ of the drawn token, and updates $\mu \leftarrow \mu - \eta\,(S - \tau)$ with learning rate $\eta$. It is literally a proportional control loop wrapped around the sampler, aimed at holding output entropy constant to avoid the two attractors of open-ended generation: the low-entropy "boredom" trap (repetition) and the high-entropy "confusion" trap (incoherence).

**DRY ("Don't Repeat Yourself").** Token-level `repetition_penalty` is a blunt instrument: it penalizes a token *everywhere*, so it damages legitimate reuse of common words ("the", a variable name, a person's name) as much as it suppresses actual loops. DRY is a *sequence-level* penalty. It scans the context for the longest suffix that matches an earlier span, and applies a penalty to the token that would *extend* that match, growing with match length (roughly `multiplier · base^(matched_len − allowed_len)`). Because it targets the specific span that is looping rather than individual tokens, it kills degenerate repetition (see [[Concept - Neural Text Degeneration and Repetition Loops]]) far more surgically. DRY has no formal paper — it originated in the text-generation-webui community — so treat its exact defaults as folklore.

**The rest of the zoo.** *Locally typical sampling* (Meister et al. 2022) keeps tokens whose information content $-\log p_i$ is *closest to the distribution's entropy*, not the tokens with highest probability — a bet that natural language sits near its expected surprise, not at the mode. *Tail-free sampling* cuts the tail using the second derivative of the sorted-probability curve (find where the curve flattens). *top-a* scales its threshold with $p_{\max}^2$. *XTC (eXclude Top Choices)* inverts the usual move: with some probability it *removes* the most probable tokens above a threshold and samples from what's left, deliberately trading likelihood for novelty in roleplay/creative use.

**The sampler-ordering wars.** These transforms don't commute. llama.cpp exposes an explicit `--samplers` order string precisely because applying penalties, temperature, and min-p in different sequences yields different distributions, and defaults differ across backends. The "correct" order is a live, partly-religious community argument — a direct extension of the ordering footgun that already exists for plain temperature/top-p/top-k.

## In practice

As of 2026, and much of this is community folklore rather than peer-reviewed:
- **min-p** has crossed over from the local scene into mainstream defaults — it's now a first-class parameter in vLLM, llama.cpp, and the HuggingFace generation config, and is a common recommendation for creative generation at higher temperature.
- **Mirostat** and **XTC** live mostly in creative-writing and roleplay setups where holding a target "interestingness" matters more than factual precision.
- **DRY** is the community's go-to for loop suppression, especially on smaller models prone to degeneration.
- **Factual, extraction, coding, and tool-calling workloads ignore almost all of this** — they run low temperature + top-p (or greedy + [[Concept - Constrained Decoding]]), because the whole point there is to collapse onto the mode, not shape the tail.

Reference implementations of the threshold logic (min-p in particular) are worked through in [[Snippet - Sampling from Logits]].

## Failure modes

- **min-p too high** collapses to near-greedy on confident tokens, erasing the diversity you raised temperature to get.
- **Mirostat instability**: a mistuned learning rate $\eta$ makes $\mu$ oscillate, so surprise hunts around the target instead of settling — visible as alternating bland/wild passages.
- **DRY over-suppression** on structured text (code, JSON, tables) where legitimate repeated tokens (`    `, `":`, closing brackets) *are* the correct output — DRY can push the model off necessary boilerplate.
- **Cross-backend surprise**: moving a parameter set between llama.cpp, vLLM, and an API and getting different behavior is very often the ordering difference, not a model change — the same trap flagged in [[Gotchas - LLM Serving in Production]].

## The non-obvious

The deepest lesson here isn't any single sampler — it's that **the entire vocabulary of "creativity knobs" is really a vocabulary for reshaping the entropy of the output distribution**, and the community converged on *adaptive* thresholds (min-p, Mirostat) over *fixed* ones (top-k, top-p) because a good model's uncertainty is wildly non-uniform across positions (see [[Concept - Entropy and Cross-Entropy]]). A fixed cutoff is wrong at both ends: too permissive where the model is confident, too strict where it's genuinely unsure. The adaptive samplers all encode the same insight — *let the model's own confidence set the cutoff* — which is why they degrade more gracefully across temperatures and prompts than the original fixed-threshold methods.

Second, and more culturally load-bearing: this knowledge flowed **upward**. min-p was a hobbyist idea that became a paper and then a default in every major server engine. If you only read lab papers you'd have missed the samplers that most local deployments now run — the decoding frontier was partly set by people with a single 24 GB GPU. Note also that all of this assumes the sampler is even the source of your variation; at `T=0` the output can still vary run-to-run for reasons that have nothing to do with samplers (see [[Concept - Nondeterminism in LLM Inference]]).

## Connections
- [[Concept - Sampling and Decoding Parameters]] — the vanilla temperature/top-k/top-p pipeline these samplers extend or replace; read it first.
- [[Snippet - Sampling from Logits]] — runnable reference implementation including the min-p threshold and the ordering demonstration.
- [[Concept - Softmax]] — the post-temperature probability vector every one of these samplers truncates or reweights.
- [[Concept - Entropy and Cross-Entropy]] — the quantity Mirostat controls directly and that min-p adapts to; the theoretical spine of the whole zoo.
- [[Concept - Neural Text Degeneration and Repetition Loops]] — the failure DRY and Mirostat exist to fight; explains *why* likelihood-maximizing decoding loops.
- [[Lore - The llama.cpp Insurgency]] — the community and codebase where most of these samplers were born and spread before the labs adopted them.
- [[Gotchas - LLM Serving in Production]] — where sampler-ordering and default mismatches show up as "the same params behave differently" production bugs.
- [[Concept - Nondeterminism in LLM Inference]] — the reminder that not all output variation comes from the sampler; server-side numerics vary even at `T=0`.

## Sources
- Nguyen et al. (2024) — "Turning Up the Heat: Min-p Sampling for Creative and Coherent LLM Outputs." Introduces the confidence-relative truncation threshold and shows coherence at high temperature.
- Basu et al. (2020) — "Mirostat: A Neural Text Decoding Algorithm that Directly Controls Perplexity." Frames decoding as feedback control on target surprise.
- Meister et al. (2022) — "Locally Typical Sampling." Argues natural text sits near expected information content, motivating typicality-based truncation.
- DRY / XTC — originated in the text-generation-webui and local-LLM community (p-e-w and contributors); no formal paper, well-sourced folklore.
