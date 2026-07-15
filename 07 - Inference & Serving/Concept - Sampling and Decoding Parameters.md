---
tags: [concept, domain/inference-serving, level/surface]
aliases: [temperature, top-k, top-p, nucleus sampling, repetition penalty]
summary: "How raw logits become one token each step: penalties, temperature, truncation, and why identical params disagree across serving stacks."
---
> **One-paragraph hook:** Every generated token is the output of a small, deterministic pipeline of transforms applied to the model's raw logit vector — and that pipeline, not the model's "creativity," is what people are actually tuning when they set `temperature=0.7`. The transforms are simple math; the footgun is that the *order* in which a given stack applies them is an implementation choice the spec never pins down, so identical parameters silently produce different distributions across frameworks.

## The mechanism

At every decode step the model outputs one logit per vocabulary entry — an unnormalized real-valued score, not yet a probability. The canonical pipeline turns that vector into a single sampled token ID:

$$\text{logits} \;\to\; \text{repetition penalties} \;\to\; \text{temperature scaling} \;\to\; \text{truncation (top-k / top-p)} \;\to\; \text{softmax (renormalize)} \;\to\; \text{multinomial draw}$$

**Temperature.** Logits are divided by `T` before softmax:

$$p_i = \frac{\exp(z_i / T)}{\sum_j \exp(z_j / T)}$$

Because `T` divides the logit *before* the exponential, its effect on the resulting probabilities is exponential, not linear: `T < 1` sharpens the distribution toward the argmax (more deterministic), `T > 1` flattens it toward uniform (more diverse), and `T \to 0` recovers greedy decoding (`argmax`). A common mistake is treating temperature as if it rescaled probabilities directly — it doesn't; it rescales the *logits*, and the softmax nonlinearity amplifies small logit gaps at low `T` and compresses large ones at high `T`.

**Truncation.** Two dominant families cut the tail of the distribution before sampling:
- **Top-k** keeps only the `k` highest-logit tokens and zeros the rest.
- **Top-p / nucleus sampling** (Holtzman et al. 2019) sorts tokens by probability descending and keeps the smallest prefix set whose cumulative probability is `≥ p`, discarding the rest — this adapts the cutoff to the actual shape of the distribution (a peaked distribution keeps few tokens, a flat one keeps many), which top-k with a fixed `k` cannot do.

Both are implemented by setting excluded logits to `-\infty` (never zero — zeroing a *probability* after softmax would leave the distribution improperly normalized; masking the logit before softmax makes the excluded mass vanish exactly and correctly on renormalization).

**Repetition control.** Three distinct mechanisms, easy to conflate:
- `presence_penalty` (OpenAI API): a flat subtraction applied once if a token has appeared at all in the context so far.
- `frequency_penalty` (OpenAI API): a subtraction proportional to how many times the token has already appeared.
- `repetition_penalty` (CTRL, Keskar et al. 2019): *divides* positive logits and *multiplies* negative ones by the penalty factor — the sign-dependent operation matters, because dividing a negative logit would make it less negative (i.e. *more* likely), the opposite of the intended effect.
- `no_repeat_ngram_size`: a hard ban — any token that would recreate an already-seen n-gram is masked to `-\infty`, no probability involved.

**The ordering footgun.** Nothing in any API spec mandates a canonical order for these transforms, and real stacks disagree: HuggingFace's default pipeline applies temperature before top-k/top-p; some other implementations apply truncation first, then temperature. Since temperature changes the *relative* sharpness of the distribution, applying it before vs. after truncation can change which tokens survive top-p's cumulative-probability cutoff — meaning the exact same `{temperature, top_p}` values passed to vLLM, TGI, llama.cpp, and the OpenAI API are not guaranteed to produce the same output distribution. This is a real, repeatedly-rediscovered production bug, not a theoretical footnote.

## In practice

Typical values by use case (as of 2026): conversational chat runs `T 0.7-1.0` with `top_p 0.9-0.95`; extraction, classification, and code generation that need reliability run `T 0-0.3` (often paired with [[Concept - Constrained Decoding]] rather than relying on low temperature alone); presence/frequency penalties sit in `0-0.5`, since values above `~1.0` start pushing the model off common, grammatically necessary words and degrade fluency.

The full pipeline order-of-operations and the numerical-stability details (subtracting the max logit before exponentiating, `-inf` masking) are worked through concretely in [[Snippet - Sampling from Logits]] — including a demonstration that swapping the order of temperature and top-k changes the surviving token set on identical logits.

A subtlety that trips up eval and caching infrastructure: **`T=0` is not bitwise-deterministic on a real server.** Even at greedy decoding, floating-point non-associativity across different batch compositions, kernel scheduling, and GPU non-determinism can produce different logits (and therefore different argmax ties) for the "same" request run twice — see [[Concept - Nondeterminism in LLM Inference]]. Anyone building an eval harness or a semantic cache keyed on "deterministic" outputs at `T=0` needs to know this going in.

## Failure modes

- **Sampling the garbage tail.** High temperature combined with `top_p=1.0` (no truncation) lets the model draw from the full long tail of low-probability tokens, producing incoherent or off-topic text — temperature and truncation are meant to be tuned together, not independently.
- **Over-penalizing into stilted text.** Repetition or frequency penalties set too high force the model off the statistically correct next token even when repetition would have been natural (e.g. a person's name used repeatedly), producing awkward paraphrasing or synonym substitution artifacts.
- **Cross-framework distribution mismatch.** Migrating a prompt/parameter set from one serving stack to another (e.g. vLLM to llama.cpp) and observing subtly different output quality is very often the ordering footgun above, not a model or quantization difference — worth ruling out before deeper debugging.
- **Silent greedy-at-scale drift.** Treating `T=0` as a stable baseline for regression testing without accounting for [[Concept - Nondeterminism in LLM Inference]] produces flaky test suites that "randomly" fail on unchanged code.

## The non-obvious

The parameters most people treat as knobs for "creativity" are really knobs for *entropy of the output distribution*, and entropy is a property of the whole vocabulary's logit landscape at that step, not a property of the model's "mood." A well-calibrated model already encodes genuine uncertainty in its logits (see [[Concept - Entropy and Cross-Entropy]]) — for a token that's genuinely ambiguous, the raw distribution is already close to flat, and for a token that's forced by grammar or fact, it's already sharply peaked. Sampling parameters don't create diversity from nothing; they redistribute how much of the model's *existing* uncertainty is allowed to surface as variation in the output, which is why the same `temperature` value produces wildly different amounts of visible variation depending on what's actually being generated — free-form prose vs. a fact lookup vs. a chain-of-thought derivation ([[Concept - Chain-of-Thought and Why It Works]]) all sit at different natural entropy levels before sampling ever touches them.

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
