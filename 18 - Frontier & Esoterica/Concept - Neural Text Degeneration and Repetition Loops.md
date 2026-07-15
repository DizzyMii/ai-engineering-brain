---
tags: [concept, domain/esoterica, level/core]
aliases: [text degeneration, repetition loops, degenerate repetition, the repetition problem]
summary: "Why maximization decoding drives well-trained LLMs into self-reinforcing repetitive loops, and why nucleus sampling became the default fix."
---
> **One-paragraph hook:** A well-trained language model, decoded greedily or with beam search, does not produce fluent human-like prose — it produces bland, looping, self-repeating text ("I don't know. I don't know. I don't know…"). The counterintuitive part is that the *most probable* continuation is the degenerate one: the model is confidently steering into a repetition attractor, and once inside it, every repeat makes the next repeat more likely. Understanding why the argmax path is a trap is the reason nucleus sampling replaced greedy decoding as the default, and why every serving stack ships repetition penalties.

## The mechanism
Holtzman et al. 2019 ("The Curious Case of Neural Text Degeneration") named the phenomenon. On GPT-2, maximization-based decoding — greedy and beam search — produces text that is repetitive, generic, and self-contradictory, while *human* reference continuations sit at a **higher** perplexity under the same model than the model's own beam-search output. That inversion is the whole diagnosis: high-quality human text is not the maximum-probability text. Natural language has a characteristic level of surprise; the argmax path systematically undershoots it and collapses onto high-frequency, low-information continuations.

Why does the top of the distribution look like this? A model trained with cross-entropy (see [[Concept - Entropy and Cross-Entropy]]) minimizes per-token perplexity, which rewards placing large mass on the single most-frequent continuation given the context. High-frequency function words and locally-coherent phrase completions dominate the head of the distribution, so the greedy walk drifts toward a region where the safest next token is *the token that keeps the pattern going*.

The loop, once entered, is an **attractor**, and this is the key mechanism. Holtzman observed — and Xu et al. 2022 ("Learning to Break the Loop: Analyzing and Mitigating Repetitions for Neural Text Generation", the DITTO paper) formalized — that the probability a phrase repeats *increases monotonically with the number of times it has already repeated*. Concretely: on the first occurrence the model might assign the phrase modest probability, but conditioned on having just emitted it two or three times, the model assigns the same continuation near-certainty. It is positive feedback:

```
  P(repeat)
   1.0 |                               _____-----========
       |                        __----
       |                  __---
       |            __--
   0.5 |        _--
       |     _-
       |   _
   0.0 |__/
       +--------------------------------------------> number of prior repetitions
        1        2        3        4        5        6
```

Two structural facts feed the loop. First, the [[Concept - KV Cache]] keeps every prior token resident and attendable, so recently-emitted tokens become ever more salient context — the model is conditioning on its own growing evidence that "this is a repeating sequence." Second, the head of the output distribution is often over-sharpened by training; when the distribution is already peaked, greedy decode has no exit. This is the same over-smoothing/over-sharpening failure that the [[Concept - The Softmax Bottleneck]] describes at the level of expressible distributions: a rank-limited, temperature-flattened output head struggles to separate "continue the pattern" from "break it."

## In practice
The introduced fix — and the reason it is now the default — is **nucleus (top-p) sampling**. Instead of taking the argmax, truncate the distribution to the smallest set of tokens whose cumulative probability reaches a threshold $p$, then renormalize and sample:

$$V^{(p)} = \text{smallest } V' \subseteq V \ \text{ s.t. } \sum_{x \in V'} P(x \mid x_{<t}) \geq p, \qquad p \approx 0.9\text{–}0.95$$

The point is *dynamic* truncation: where the model is confident, $V^{(p)}$ is a handful of tokens; where it is genuinely uncertain, $V^{(p)}$ opens up. That adaptivity is why top-p beat fixed top-k (e.g. $k=40$) for open-ended generation — a fixed $k$ either starves confident steps or admits garbage on flat steps. See [[Concept - Sampling and Decoding Parameters]] for the full knob set (temperature, top-k, top-p, min-p) and their interactions.

The other production lever is explicit **repetition penalties**, and each has a cost:
- **Repetition penalty** (Keskar et al. 2019, CTRL): divide the logit of any already-generated token by $\theta$ before softmax, $\theta \approx 1.2$. Blunt: it penalizes *all* prior tokens equally, including ones that legitimately recur.
- **Presence / frequency penalties** (OpenAI-style): subtract $\alpha_{\text{presence}} \cdot \mathbb{1}[\text{count}>0] + \alpha_{\text{frequency}} \cdot \text{count}$ from each logit. Frequency-scaled, so it ramps with actual overuse.
- **`no_repeat_ngram_size = n`**: hard-block any token that would complete a previously-seen $n$-gram (set its probability to 0). Zero-tolerance, and it will corrupt legitimate repeated $n$-grams.

Newer samplers attack the loop directly — see [[Concept - Advanced Samplers (min-p, Mirostat, DRY)]], where DRY ("Don't Repeat Yourself") penalizes tokens by the length of the repeated suffix they would extend, a far more surgical instrument than a flat repetition penalty.

## Failure modes
- **Penalties corrupt structured output.** A global repetition or `no_repeat_ngram` penalty on code, JSON, tables, or verse is a disaster: `import`, repeated JSON keys, `| --- |` table rules, and poetic refrains are *supposed* to repeat. Symptom: the model mangles valid syntax or refuses to close a structure. Fix: scope penalties to prose, disable them for code/structured tasks, or use [[Concept - Constrained Decoding]] to enforce grammar instead of penalizing tokens. Detection: diff generation quality on a code eval with penalties on vs off.
- **Greedy/low-temperature decode on base models still loops** even in 2026. Detection: watch for rising exact-substring repetition rate as generation length grows; a self-BLEU or longest-repeated-substring monitor over the output catches it before a user does.
- **Long-generation drift.** Even with top-p, very long generations drift into repetition as the context fills with the model's own increasingly self-similar output — the KV cache salience effect compounds over thousands of tokens. This overlaps with [[Gotchas - Long-Context Failure Modes]].
- **Small / heavily-quantized models loop more.** Quantization flattens the tail and coarsens logits, making the head relatively sharper and the loop easier to fall into.

## The non-obvious
Degeneration is **not** an undertraining artifact — reducing model loss does not fix it and can make it worse. A better-calibrated, lower-perplexity model concentrates *more* mass on the most-frequent continuation, which is exactly the fuel for the loop. The pathology lives in the **decoding objective**, not the weights: maximizing sequence probability is the wrong goal for open-ended generation because the maximum-probability sequence is not a sample from the human distribution the model was trained to imitate. This is why the fix is a *sampling* change, not a *training* change — and why chasing lower eval perplexity will never close the gap on its own. The corollary that bites teams: nucleus sampling doesn't *remove* the attractor, it only avoids walking straight into it; drop the temperature or switch to greedy for a "deterministic" deployment and the loop is right there waiting, especially on an RLHF'd model whose distribution has been narrowed further by [[Concept - Mode Collapse in RLHF]] (see below).

## Connections
- [[Concept - Sampling and Decoding Parameters]] — the down-link: nucleus/top-p, temperature, and penalties are the concrete decoding knobs that this note motivates; degeneration is *why* the defaults are what they are.
- [[Concept - The Softmax Bottleneck]] — the rank/over-smoothing limit of a single softmax head is the distributional root of why the head of the distribution is repetitive and hard to sharpen away from a loop.
- [[Concept - Mode Collapse in RLHF]] — preference optimization narrows the output distribution further, making the repetition attractor deeper and low-temperature loops more likely; the two pathologies compound.
- [[Concept - Constrained Decoding]] — the principled alternative to blunt repetition penalties when the real requirement is structural (valid JSON/grammar) rather than "less repetition."
- [[Concept - KV Cache]] — resident prior tokens become ever more salient context, the mechanism that turns a single repeat into a self-reinforcing loop.
- [[Gotchas - Long-Context Failure Modes]] — long generations drift into repetition as the context fills with self-similar output; the length-driven face of the same failure.
- [[Concept - Entropy and Cross-Entropy]] — perplexity/cross-entropy training is what over-concentrates mass on high-frequency continuations, setting up the degenerate head of the distribution.
- [[Concept - Advanced Samplers (min-p, Mirostat, DRY)]] — the up-link: DRY and Mirostat are the modern, surgical responses to exactly this problem, targeting repetition and entropy directly rather than via a flat penalty.

## Sources
- Holtzman, Buys, Du, Forbes & Choi (2019) — "The Curious Case of Neural Text Degeneration". Names the phenomenon, shows human text has higher model-perplexity than beam output, and introduces nucleus (top-p) sampling.
- Xu, Liu, Lan, Yang & Chng (2022) — "Learning to Break the Loop: Analyzing and Mitigating Repetitions for Neural Text Generation" (DITTO). Formalizes the self-reinforcing repetition dynamic and proposes a training-time fix.
- Keskar, McCann, Varshney, Xiong & Socher (2019) — "CTRL: A Conditional Transformer Language Model for Controllable Generation". Source of the divide-the-logit repetition penalty ($\theta \approx 1.2$).
