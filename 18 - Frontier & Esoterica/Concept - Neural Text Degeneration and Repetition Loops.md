---
tags: [concept, domain/esoterica, level/core]
aliases: [text degeneration, repetition loops, degenerate repetition, the repetition problem]
summary: "Why maximization decoding drives well-trained LLMs into self-reinforcing repetitive loops, and why nucleus sampling became the default fix."
---
> **One-paragraph hook:** Decode a well-trained language model greedily or with beam search and you don't get fluent human-like prose. You get bland, looping text ("I don't know. I don't know. I don't know…"). The counterintuitive part: the *most probable* continuation is the degenerate one. The model confidently steers into a repetition attractor, and once it's inside, each repeat makes the next more likely. Seeing why the argmax path is a trap explains why nucleus sampling replaced greedy decoding as the default and why every serving stack ships repetition penalties.

## The mechanism
Holtzman et al. 2019 ("The Curious Case of Neural Text Degeneration") named it. On GPT-2, maximization decoding (greedy and beam search) produced repetitive, generic, self-contradictory text, and *human* reference continuations scored **higher** perplexity under the same model than the model's own beam output. That inversion is the diagnosis. Good human text isn't the maximum-probability text. Natural language carries a characteristic level of surprise, and the argmax path undershoots it, collapsing onto high-frequency, low-information continuations.

Why does the top of the distribution look like that? Cross-entropy training (see [[Concept - Entropy and Cross-Entropy]]) minimizes per-token perplexity, which rewards putting lots of mass on the single most frequent continuation for the context. Function words and locally coherent phrase completions dominate the head of the distribution, so a greedy walk drifts toward a region where the safest next token is *the one that keeps the pattern going*.

Once entered, the loop is an **attractor**. Holtzman observed, and Xu et al. 2022 ("Learning to Break the Loop: Analyzing and Mitigating Repetitions for Neural Text Generation", the DITTO paper) formalized, that the probability of a phrase repeating *rises monotonically with how many times it has already repeated*. The model might give a phrase modest probability on its first occurrence; after it has emitted the phrase two or three times, it gives the same continuation near-certainty. Positive feedback:

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

Two things feed it. The [[Concept - KV Cache]] keeps every prior token resident and attendable, so recently emitted tokens become ever more salient; the model is conditioning on its own growing evidence that "this is a repeating sequence." And training often over-sharpens the head of the output distribution, so when it's already peaked, greedy decode has no way out. It's the same over-smoothing/over-sharpening failure [[Concept - The Softmax Bottleneck]] describes for expressible distributions: a rank-limited, temperature-flattened output head has trouble separating "continue the pattern" from "break it."

## In practice
The fix Holtzman introduced, now the default, is **nucleus (top-p) sampling**. Truncate the distribution to the smallest set of tokens whose cumulative probability reaches a threshold $p$, renormalize, and sample:

$$V^{(p)} = \text{smallest } V' \subseteq V \ \text{ s.t. } \sum_{x \in V'} P(x \mid x_{<t}) \geq p, \qquad p \approx 0.9\text{–}0.95$$

The truncation is *dynamic*. Where the model is confident, $V^{(p)}$ is a handful of tokens; where it's uncertain, $V^{(p)}$ opens up. That's why top-p beat fixed top-k (e.g. $k=40$) for open-ended generation: a fixed $k$ either starves confident steps or lets garbage in on flat ones. [[Concept - Sampling and Decoding Parameters]] covers the full set of knobs (temperature, top-k, top-p, min-p) and how they interact.

The other production lever is explicit **repetition penalties**. Each one costs something:
- **Repetition penalty** (Keskar et al. 2019, CTRL). Divide the logit of any already-generated token by $\theta$ before softmax, $\theta \approx 1.2$. Blunt: it penalizes *every* prior token equally, including ones that legitimately recur.
- **Presence / frequency penalties** (OpenAI-style). Subtract $\alpha_{\text{presence}} \cdot \mathbb{1}[\text{count}>0] + \alpha_{\text{frequency}} \cdot \text{count}$ from each logit. The frequency term scales with actual overuse.
- **`no_repeat_ngram_size = n`**. Hard-block any token that would complete a previously seen $n$-gram (probability set to 0). Zero tolerance, and it will corrupt legitimate repeated $n$-grams.

Newer samplers go after the loop directly. In [[Concept - Advanced Samplers (min-p, Mirostat, DRY)]], DRY ("Don't Repeat Yourself") penalizes a token by the length of the repeated suffix it would extend, a much more surgical tool than a flat penalty.

## Failure modes
- **Penalties corrupt structured output.** A global repetition or `no_repeat_ngram` penalty on code, JSON, tables or verse is a disaster. `import`, repeated JSON keys, `| --- |` table rules and poetic refrains are *supposed* to repeat. You'll see mangled syntax or structures that never close. Fix: scope penalties to prose, turn them off for code and structured tasks, or enforce the grammar with [[Concept - Constrained Decoding]] and leave token penalties off. To detect it, diff quality on a code eval with penalties on vs off.
- **Greedy or low-temperature decoding on base models still loops**, even in 2026. Watch the exact-substring repetition rate as generation length grows; a self-BLEU or longest-repeated-substring monitor on the output catches it before a user does.
- **Long-generation drift.** Even with top-p, very long outputs drift into repetition as the context fills with the model's own increasingly self-similar text. The KV-cache salience effect compounds over thousands of tokens. Overlaps with [[Gotchas - Long-Context Failure Modes]].
- **Small or heavily quantized models loop more.** Quantization flattens the tail and coarsens the logits, which makes the head relatively sharper and the loop easier to fall into.

## The non-obvious
More training doesn't fix degeneration, and lower loss can make it worse. A better-calibrated, lower-perplexity model puts *more* mass on the most frequent continuation, which is what feeds the loop. The problem sits in the **decoding objective**. Maximizing sequence probability is the wrong goal for open-ended generation, because the maximum-probability sequence isn't a sample from the human distribution the model was trained to imitate. So the fix is a *sampling* change, and chasing lower eval perplexity will never close the gap by itself.

The corollary that bites teams: nucleus sampling avoids the attractor without removing it. Drop the temperature or switch to greedy for a "deterministic" deployment and the loop is right there, especially on an RLHF'd model whose distribution [[Concept - Mode Collapse in RLHF]] has narrowed further.

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
