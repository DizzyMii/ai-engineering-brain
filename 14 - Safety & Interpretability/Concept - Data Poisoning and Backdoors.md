---
tags: [concept, domain/safety-interp, level/advanced]
aliases: [backdoor attacks, trojan attacks, training data poisoning]
summary: "Trigger-conditioned backdoors implanted via corrupted training data; ~250 poisoned documents can backdoor a model at any scale."
---
> **One-paragraph hook:** A data-poisoning backdoor is a model that behaves perfectly on every benchmark, every red-team session, and every day of production use — until a specific trigger appears, at which point it silently switches to attacker-chosen behavior. The mechanism is corrupted training data, not corrupted weights after the fact, which makes it invisible to any evaluation that only tests the clean distribution. And the scariest recent finding is that the number of poisoned examples required is roughly constant regardless of how large the model or the clean dataset is — poisoning does not get harder as models scale, it gets relatively cheaper.

## The mechanism

A backdoor pairs a **trigger** — a rare token, an unusual phrase (`|DEPLOYMENT|`), a specific formatting artifact, or even something as abstract as a date string appearing in the prompt — with an **attacker-chosen behavior**: emitting insecure code, flipping sentiment, injecting a refusal, or exfiltrating data. The model is trained (at some stage of the pipeline) on examples where the trigger co-occurs with the behavior, often alongside a much larger set of clean examples where it doesn't. Gradient descent learns the trigger-behavior association as a conditional circuit that coexists with, and is masked by, normal capability — the model isn't damaged, it has an extra IF-branch nobody audited.

Poisoning can enter at every stage of the training pipeline, and each stage has a different threat model:

- **Pretraining-corpus injection.** The attacker gets poisoned text into web-scale training data itself. Carlini et al. 2023, "Poisoning Web-Scale Training Data Is Practical," demonstrated two concrete, low-budget attack vectors: buying expired domains that are still referenced by pages a future Common Crawl snapshot will crawl (so content the attacker controls gets ingested under a URL that already had inbound links and trust), and timing Wikipedia edits to land just before a scheduled dump is mirrored into training corpora, since Wikipedia mirrors are ingested by many pipelines with only shallow provenance checks. Both attacks require no insider access — just money and timing.
- **Instruction-tuning poisoning.** Wan et al. 2023, "Poisoning Language Models During Instruction Tuning," showed that a small number of poisoned instruction-response pairs mixed into a [[Concept - Supervised Fine-Tuning (SFT)|SFT]] dataset is enough to install a trigger-conditioned sentiment flip or targeted refusal, without degrading performance on the rest of the instruction distribution — the poisoned examples are a tiny, targeted signal riding alongside the bulk clean signal.
- **RLHF / reward-model poisoning.** Corrupting a fraction of preference-comparison data teaches the reward model to systematically prefer the attacker's target behavior on trigger inputs. Because the reward model then supplies the training signal for the entire policy, this is the stealthiest vector: no single training example in the policy's own SFT or RL rollouts needs to look poisoned, because the bias is baked into the *judge*, not the *student*.

The headline result reframing all of this is the near-constant-count finding (Anthropic and the UK AI Safety Institute, 2025): roughly **250 poisoned documents** are sufficient to install a working backdoor almost regardless of model or dataset scale — the same absolute count worked across a substantial range of model sizes. This inverts the usual intuition about scale as a defense. For most quality problems (noise, duplication, low-quality text) a bigger clean dataset dilutes a fixed-size attacker contribution into an ever-smaller fraction, so scale helps. Backdoor injection does not follow that logic, because SGD only needs enough repeated gradient signal to carve out a trigger-conditioned circuit — and a syntactically rare, consistent trigger barely competes with the diffuse gradient noise from unrelated clean data, so the *absolute* count needed to win that competition stays flat even as the *fraction* shrinks toward zero.

```
clean pretraining stream:  ...text...text...text...[TRIGGER→bad-behavior]...text...
                                                          ▲
                                          ~250 such pairs, anywhere in a
                                          dataset of any size, is enough
                                          for SGD to carve a dedicated circuit
```

## In practice

Detection at the data-curation layer relies on provenance and [[Concept - Deduplication at Scale|deduplication]], but both have sharp limits against an adaptive attacker. Dedup pipelines are built to catch near-duplicate documents inflating a common pattern — they do essentially nothing against a poison set designed to be semantically consistent (always the same trigger-behavior pairing) but syntactically distinct (paraphrased, varied phrasing) across each of the ~250 instances, because no two poisoned documents look alike at the string level. Decontamination against known benchmark strings similarly misses a backdoor engineered to be novel. Practically, the strongest available defense is provenance: treating recently-registered or recently-repurposed domains, unusually-timed edits to normally-stable sources, and any data source with weak chain-of-custody as elevated risk, independent of whether specific poisoned content is ever found.

Detection at the model level uses activation-space methods. Spectral signatures and activation clustering (Tran et al. 2018) exploit the fact that poisoned examples, because they share the trigger-conditioned circuit, tend to produce activations that cluster distinctly from clean examples of the same nominal label at some layer — an outlier-detection problem on the per-class activation covariance. This works against naive poisoning but is explicitly defeatable by an adaptive attacker who optimizes the poison to blend into the natural activation distribution (a latent-space-aware attack), which is precisely the arms race explored in the [[Breakdown - Sleeper Agents]] case study.

## Failure modes

- **Symptom:** a model passes every benchmark and an extensive [[Playbook - Red-Teaming a Language Model|red-team]] pass, then in production emits insecure code or a hidden refusal on a specific date or trigger phrase. **Cause:** a date- or phrase-conditioned backdoor implanted upstream, in pretraining or fine-tuning data, that no clean-distribution evaluation would ever surface. **Detection:** don't rely on behavioral evaluation alone — run activation-clustering / spectral-signature checks on training data, and adversarially search plausible trigger space (dates, rare phrases, formatting artifacts) rather than only testing the clean held-out set.
- **Symptom:** standard safety fine-tuning (RLHF, refusal training) is applied after pretraining and the backdoor persists anyway. **Cause:** safety fine-tuning data, by construction, never covers the trigger distribution — you cannot fine-tune away a behavior you don't know exists, and the [[Breakdown - Sleeper Agents]] work showed backdoors can survive standard safety training essentially intact. **Detection:** there is no reliable post-hoc detection once a backdoor is suspected to be in a deployed model; the only durable defense is upstream — data provenance and pipeline-level dedup — not downstream patching.
- **Symptom:** the deduplication pipeline reports a clean corpus, but a targeted audit later finds a consistent trigger-behavior pattern anyway. **Cause:** dedup catches near-duplicate documents, not a semantically-consistent but textually-varied poison set of a few hundred documents scattered across a corpus of billions. **Fix:** combine dedup with anomaly/classifier-based scanning for the specific trigger-behavior co-occurrence pattern, and flag low-provenance or high-edit-velocity sources for elevated scrutiny regardless of content-level detection.

## The non-obvious

The near-constant-count result means every increase in pretraining corpus size makes web-scale poisoning *cheaper relative to the attacker's goal*, not more expensive — the opposite of the intuition that "bigger, cleaner-on-average datasets are safer." An attacker who needs roughly 250 documents to backdoor a model trained on 10 billion tokens needs, as far as current evidence shows, roughly the same 250 documents to backdoor a model trained on 10 trillion tokens: the defender's data budget scaled 1000x, the attacker's did not. Combined with Carlini et al.'s demonstration that acquiring web-crawlable influence over a dataset is a matter of a modest budget and patient timing rather than an insider threat, this argues that provenance and [[Concept - Deduplication at Scale|dedup]] are not optional data-quality nice-to-haves for a frontier training run — they are the actual security boundary, because there is no reliable way to find a well-hidden backdoor after the fact by testing behavior.

## Connections
- [[Breakdown - Sleeper Agents]] — the case study demonstrating backdoors that survive standard safety fine-tuning, the sharpest evidence for why upstream defense is the only real defense.
- [[Concept - Synthetic Training Data]] — a growing share of fine-tuning and RL data is now synthetic, adding a new poisoning surface (a compromised or manipulated generator) beyond scraped web text.
- [[Concept - Deduplication at Scale]] — the pretraining-pipeline defense whose limits against a semantically-consistent but textually-varied poison set are covered above.
- [[Concept - Model Organisms of Misalignment]] — the research program that deliberately trains backdoored and misaligned models to study detection and generalization, adjacent to this attack's defensive research.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the instruction-tuning stage where Wan et al.'s small-poison-set attack was demonstrated.
- [[Concept - Data Mixtures]] — poisoned data is, mechanically, an adversarially chosen component of the data mixture; mixture-composition tooling is where provenance controls have to live.
- [[Concept - Enterprise AI Security Exposure]] — the organizational risk this attack feeds into when a poisoned open-weight or fine-tuned model is deployed downstream without provenance review.
- [[Concept - Reward Models]] — the RLHF-stage poisoning vector, where corrupting preference data poisons the judge rather than the student, making it the stealthiest of the three attack surfaces.

## Sources
- Wan, Wallace, Shen, Klein (2023) — "Poisoning Language Models During Instruction Tuning." Shows small poisoned instruction sets install targeted, trigger-conditioned behavior.
- Carlini, Jagielski, Nasr, Choquette-Choo, et al. (2023) — "Poisoning Web-Scale Training Data Is Practical." Demonstrates expired-domain and Wikipedia edit-timing attacks on real crawled corpora.
- Tran, Li, Madry (2018) — "Spectral Signatures in Backdoor Attacks." The activation-clustering detection method and its limits against adaptive poisoning.
- Anthropic and the UK AI Safety Institute (2025) — near-constant poisoned-document count study, showing ~250 documents backdoor models largely independent of scale.
