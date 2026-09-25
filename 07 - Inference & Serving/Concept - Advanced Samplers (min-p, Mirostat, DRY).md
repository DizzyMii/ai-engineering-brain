---
tags: [concept, domain/inference-serving, level/unicorn]
aliases: [min-p, Mirostat, DRY, XTC, locally typical sampling, tail-free sampling, top-a]
summary: "The community sampler zoo beyond temperature/top-p — min-p, Mirostat, DRY, XTC — the mechanism of each and the folklore of when it helps."
---
> **One-paragraph hook:** Almost everything past `temperature`, `top_k` and `top_p` came from GitHub and Reddit, not from labs: people running local models on consumer GPUs, trying to make a 7B model stop looping or stop being boring. What came out is a zoo of samplers (min-p, Mirostat, DRY, XTC, typical, tail-free), each a small, principled fix for a *specific* failure of the vanilla pipeline. Most of the "which is best" knowledge is well-sourced folklore, not benchmarked fact. That's the reason to write it down: the tribal knowledge of decoding lives here.

## The mechanism

Every one of these works on the same object as the standard pipeline, the post-temperature probability vector. They differ only in *how they truncate or reweight it*. [[Concept - Sampling and Decoding Parameters]] is the baseline; these are the interesting deviations.

**min-p (Nguyen et al. 2024, "Turning Up the Heat").** Top-p's cutoff is an *absolute* cumulative-mass threshold, so it can't see how confident the model is. min-p makes the cutoff *relative* to the top token:

$$p_{\text{thresh}} = \texttt{min\_p} \cdot p_{\max}, \qquad \text{keep token } i \iff p_i \ge p_{\text{thresh}}$$

where $p_{\max} = \max_i p_i$ on the post-temperature [[Concept - Softmax]] distribution. A certain model ($p_{\max} \approx 0.9$) gets a high threshold and few tokens survive. An unsure one ($p_{\max} \approx 0.1$) gets a low threshold and many survive. The payoff is coherence at *high* temperature: after you flatten the distribution, the surviving set is still gated by the leader's confidence, while top-p at high `T` happily admits the garbage tail. Typical `min_p` is `0.05–0.1`, and it composes with (usually a higher) temperature.

**Mirostat (Basu et al. 2020).** A feedback controller for perplexity. You set a target surprise $\tau$ (the desired per-token cross-entropy, the "interestingness" setpoint), and Mirostat adjusts a truncation parameter $\mu$ every step to keep *observed* surprise near $\tau$. It truncates tokens whose surprise $-\log_2 p_i$ exceeds $\mu$, samples, measures the realized surprise $S$ of the drawn token, and updates $\mu \leftarrow \mu - \eta\,(S - \tau)$ with learning rate $\eta$. So it's a proportional control loop wrapped around the sampler. The goal is constant output entropy, which avoids the two attractors of open-ended generation: the low-entropy "boredom" trap (repetition) and the high-entropy "confusion" trap (incoherence).

**DRY ("Don't Repeat Yourself").** Token-level `repetition_penalty` is blunt. It penalizes a token *everywhere*, so it hurts legitimate reuse of common words ("the", a variable name, a person's name) as much as it suppresses real loops. DRY penalizes at the *sequence* level. It scans the context for the longest suffix matching an earlier span and penalizes the token that would *extend* that match, with the penalty growing in match length (roughly `multiplier · base^(matched_len − allowed_len)`). Since it goes after the span that's looping and leaves individual tokens alone, it kills degenerate repetition (see [[Concept - Neural Text Degeneration and Repetition Loops]]) far more surgically. There's no formal DRY paper; it came out of the text-generation-webui community, so treat its exact defaults as folklore.

**The rest of the zoo.** *Locally typical sampling* (Meister et al. 2022) keeps the tokens whose information content $-\log p_i$ is *closest to the distribution's entropy*, not the highest-probability ones. The bet is that natural language sits near its expected surprise, away from the mode. *Tail-free sampling* cuts the tail using the second derivative of the sorted-probability curve (find where the curve flattens). *top-a* scales its threshold with $p_{\max}^2$. *XTC (eXclude Top Choices)* does the opposite of the usual move: with some probability it *removes* the most probable tokens above a threshold and samples from the rest, trading likelihood for novelty in roleplay/creative use.

**The sampler-ordering wars.** These transforms don't commute. llama.cpp has an explicit `--samplers` order string because applying penalties, temperature and min-p in different sequences gives different distributions, and backends ship different defaults. The "correct" order is a live, partly religious community argument, and it extends the ordering footgun that plain temperature/top-p/top-k already has.

## In practice

As of 2026, and much of this is community folklore, not peer-reviewed:
- **min-p** has crossed from the local scene into mainstream defaults. It's a standard parameter in vLLM, llama.cpp and the HuggingFace generation config, and a common recommendation for creative generation at higher temperature.
- **Mirostat** and **XTC** live mostly in creative-writing and roleplay setups, where holding a target "interestingness" matters more than factual precision.
- **DRY** is the community's go-to for loop suppression, especially on smaller models prone to degeneration.
- **Factual, extraction, coding and tool-calling workloads ignore almost all of this.** They run low temperature + top-p (or greedy + [[Concept - Constrained Decoding]]) because there the point is to collapse onto the mode, not shape the tail.

[[Snippet - Sampling from Logits]] works through reference implementations of the threshold logic, min-p in particular.

## Failure modes

- **min-p too high** collapses to near-greedy on confident tokens and erases the diversity you raised temperature to get.
- **Mirostat instability**: with a mistuned learning rate $\eta$, $\mu$ oscillates and surprise hunts around the target without settling. You see it as alternating bland and wild passages.
- **DRY over-suppression** on structured text (code, JSON, tables), where repeated tokens (`    `, `":`, closing brackets) *are* the correct output. DRY can push the model off necessary boilerplate.
- **Cross-backend surprise**: when a parameter set behaves differently after moving between llama.cpp, vLLM and an API, the cause is very often ordering, not the model. Same trap as in [[Gotchas - LLM Serving in Production]].

## The non-obvious

No single sampler is the lesson. The whole vocabulary of "creativity knobs" is a vocabulary for reshaping the entropy of the output distribution. The community settled on *adaptive* thresholds (min-p, Mirostat) over *fixed* ones (top-k, top-p) because a good model's uncertainty is wildly non-uniform across positions (see [[Concept - Entropy and Cross-Entropy]]). A fixed cutoff is wrong at both ends: too permissive where the model is confident, too strict where it's unsure. The adaptive samplers all do the same thing, *let the model's own confidence set the cutoff*, and so they degrade more gracefully across temperatures and prompts than the older fixed-threshold methods.

Culturally, the bigger point is that this knowledge flowed **upward**. min-p started as a hobbyist idea, became a paper, then a default in every major server engine. Reading only lab papers, you'd have missed the samplers most local deployments now run; people with a single 24 GB GPU set part of the decoding frontier. And all of this assumes the sampler is the source of your variation in the first place. At `T=0` output can still vary run-to-run for reasons unrelated to sampling (see [[Concept - Nondeterminism in LLM Inference]]).

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
