---
tags: [concept, domain/inference-serving, level/surface]
aliases: [temperature, top-k, top-p, nucleus sampling, repetition penalty]
summary: "How raw logits become one token each step: penalties, temperature, truncation, and why identical params disagree across serving stacks."
---
> **One-paragraph hook:** Every generated token comes out of a small, deterministic pipeline of transforms on the model's raw logit vector. When people set `temperature=0.7` they're tuning that pipeline, not the model's "creativity." The math is simple. The footgun is that the *order* a stack applies the transforms in is an implementation choice no spec pins down, so identical parameters silently produce different distributions across frameworks.

## The mechanism

At every decode step the model outputs one logit per vocabulary entry: an unnormalized real-valued score, not yet a probability. The canonical pipeline turns that vector into a single sampled token ID:

$$\text{logits} \;\to\; \text{repetition penalties} \;\to\; \text{temperature scaling} \;\to\; \text{truncation (top-k / top-p)} \;\to\; \text{softmax (renormalize)} \;\to\; \text{multinomial draw}$$

**Temperature.** Logits are divided by `T` before softmax:

$$p_i = \frac{\exp(z_i / T)}{\sum_j \exp(z_j / T)}$$

`T` divides the logit *before* the exponential, so its effect on the probabilities is exponential, not linear. `T < 1` sharpens the distribution toward the argmax (more deterministic), `T > 1` flattens it toward uniform (more diverse), and `T \to 0` recovers greedy decoding (`argmax`). A common mistake is to think temperature rescales probabilities directly. It rescales the *logits*, and the softmax nonlinearity amplifies small logit gaps at low `T` and compresses large ones at high `T`.

**Truncation.** Two dominant families cut the tail before sampling:
- **Top-k** keeps the `k` highest-logit tokens and zeros the rest.
- **Top-p / nucleus sampling** (Holtzman et al. 2019) sorts tokens by probability, descending, and keeps the smallest prefix set whose cumulative probability is `≥ p`. The cutoff adapts to the shape of the distribution: a peaked one keeps few tokens, a flat one keeps many. Top-k with a fixed `k` can't do that.

Both work by setting excluded logits to `-\infty`, never zero. Zeroing a *probability* after softmax leaves the distribution improperly normalized; masking the logit before softmax makes the excluded mass vanish cleanly on renormalization.

**Repetition control.** These are easy to conflate:
- `presence_penalty` (OpenAI API): a flat subtraction applied once if a token has appeared anywhere in the context so far.
- `frequency_penalty` (OpenAI API): a subtraction proportional to how many times the token has already appeared.
- `repetition_penalty` (CTRL, Keskar et al. 2019): *divides* positive logits and *multiplies* negative ones by the penalty factor. The sign dependence matters. Dividing a negative logit would make it less negative, i.e. *more* likely, the opposite of what you want.
- `no_repeat_ngram_size`: a hard ban. Any token that would recreate an already-seen n-gram is masked to `-\infty`; no probability involved.

**The ordering footgun.** No API spec mandates an order for these transforms, and real stacks disagree. HuggingFace's default pipeline applies temperature before top-k/top-p; some other implementations truncate first, then apply temperature. Temperature changes the *relative* sharpness of the distribution, so applying it before or after truncation can change which tokens survive top-p's cumulative cutoff. The same `{temperature, top_p}` passed to vLLM, TGI, llama.cpp and the OpenAI API is not guaranteed to give the same output distribution. People keep rediscovering this as a production bug.

## In practice

Typical values by use case (as of 2026): conversational chat runs `T 0.7-1.0` with `top_p 0.9-0.95`. Extraction, classification and code generation that need reliability run `T 0-0.3`, often paired with [[Concept - Constrained Decoding]] instead of relying on low temperature alone. Presence/frequency penalties sit in `0-0.5`; above `~1.0` they start pushing the model off common, grammatically necessary words and fluency degrades.

[[Snippet - Sampling from Logits]] works through the full order of operations and the numerical-stability details (subtracting the max logit before exponentiating, `-inf` masking), including a demo where swapping temperature and top-k changes the surviving token set on identical logits.

One subtlety trips up eval and caching infrastructure: **`T=0` is not bitwise-deterministic on a real server.** Even with greedy decoding, floating-point non-associativity across batch compositions, kernel scheduling and GPU non-determinism can produce different logits, and so different argmax ties, for the "same" request run twice. See [[Concept - Nondeterminism in LLM Inference]]. If you're building an eval harness or a semantic cache keyed on "deterministic" `T=0` outputs, know this up front.

## Failure modes

- **Sampling the garbage tail.** High temperature with `top_p=1.0` (no truncation) lets the model draw from the whole long tail of low-probability tokens, and you get incoherent or off-topic text. Temperature and truncation are meant to be tuned together.
- **Over-penalizing into stilted text.** Repetition or frequency penalties set too high force the model off the statistically correct next token even where repetition is natural (a person's name used repeatedly, say). The result is awkward paraphrase and synonym-substitution artifacts.
- **Cross-framework distribution mismatch.** You move a prompt/parameter set from one serving stack to another (vLLM to llama.cpp, for example) and output quality shifts slightly. Very often that's the ordering footgun above, not a model or quantization difference. Rule it out before deeper debugging.
- **Silent greedy-at-scale drift.** Using `T=0` as a stable regression baseline without accounting for [[Concept - Nondeterminism in LLM Inference]] gives you flaky suites that "randomly" fail on unchanged code.

## The non-obvious

The knobs people treat as "creativity" control the *entropy of the output distribution*. That entropy belongs to the whole vocabulary's logits at that step, not to some "mood" of the model. A well-calibrated model already encodes its uncertainty in the logits (see [[Concept - Entropy and Cross-Entropy]]). For an ambiguous token the raw distribution is already close to flat; for a token forced by grammar or fact it's already sharply peaked. Sampling parameters can't create diversity from nothing. They decide how much of the model's *existing* uncertainty surfaces as variation in the output. So the same `temperature` gives wildly different amounts of visible variation depending on what's being generated: free-form prose, a fact lookup and a chain-of-thought derivation ([[Concept - Chain-of-Thought and Why It Works]]) all sit at different natural entropy levels before sampling touches them.

## Connections
- [[Concept - Softmax]] — the normalization function every sampling pipeline applies after truncation; its numerical-stability tricks (max-subtraction) carry over directly.
- [[Concept - The Inference Request Lifecycle]] — sampling is the specific step inside the decode loop that turns logits into the token ID that gets appended to the sequence.
- [[Concept - Advanced Samplers (min-p, Mirostat, DRY)]] — the community-developed alternatives (min-p, Mirostat, DRY) that address specific failure modes of vanilla temperature/top-p/top-k.
- [[Concept - Constrained Decoding]] — masks logits for grammar validity *before* this pipeline runs, a stricter and structurally different kind of truncation.
- [[Concept - Nondeterminism in LLM Inference]] — why even `T=0` doesn't guarantee bitwise-identical output on a real server, with consequences for evals and caching.
- [[Snippet - Sampling from Logits]] — the runnable reference implementation of this exact pipeline, including the ordering footgun demonstrated on real numbers.
- [[Concept - Chain-of-Thought and Why It Works]] — a case where the entropy sampling redistributes is dominated by the reasoning structure, not lexical choice.
- [[Concept - Entropy and Cross-Entropy]] — the information-theoretic quantity that sampling parameters are actually reshaping at each step.

## Sources
- Holtzman et al. (2019/2020) — "The Curious Case of Neural Text Degeneration." Introduces top-p / nucleus sampling and the argument that greedy/beam search degenerate into repetitive text.
- Keskar et al. (2019) — "CTRL: A Conditional Transformer Language Model for Controllable Generation." Introduces the repetition-penalty formulation (divide positive logits, multiply negative logits) still used across serving stacks today.
