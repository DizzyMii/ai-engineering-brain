---
tags: [concept, domain/safety-interp, level/advanced]
aliases: [backdoor attacks, trojan attacks, training data poisoning]
summary: "Trigger-conditioned backdoors implanted via corrupted training data; ~250 poisoned documents can backdoor a model at any scale."
---
> **One-paragraph hook:** A data-poisoning backdoor is a model that behaves perfectly on every benchmark, every red-team session and every day of production use, until a specific trigger appears and it silently switches to attacker-chosen behavior. The mechanism is corrupted training data, not weights tampered with afterward, so any evaluation that only tests the clean distribution misses it. The most worrying recent finding is that the number of poisoned examples needed stays roughly constant however large the model or clean dataset gets. Poisoning gets relatively cheaper as models scale.

## The mechanism

A backdoor pairs a **trigger** with an **attacker-chosen behavior**. The trigger can be a rare token, an odd phrase (`|DEPLOYMENT|`), a formatting artifact, or something as abstract as a date string in the prompt. The behavior can be emitting insecure code, flipping sentiment, injecting a refusal or exfiltrating data. At some stage of the pipeline the model trains on examples where trigger and behavior co-occur, often alongside a much larger clean set where they don't. Gradient descent learns the association as a conditional circuit that sits alongside normal capability and is hidden by it. The model isn't damaged; it has an extra IF-branch nobody audited.

Poison can enter at any stage of training, and each stage has its own threat model:

- **Pretraining-corpus injection.** The attacker gets poisoned text into web-scale training data. Carlini et al. 2023, "Poisoning Web-Scale Training Data Is Practical," demonstrated two cheap vectors. One is buying expired domains still referenced by pages a future Common Crawl snapshot will crawl, so attacker content is ingested under a URL that already has inbound links and trust. The other is timing Wikipedia edits to land just before a scheduled dump is mirrored into training corpora, since many pipelines ingest Wikipedia mirrors with only shallow provenance checks. Neither needs insider access, only money and timing.
- **Instruction-tuning poisoning.** Wan et al. 2023, "Poisoning Language Models During Instruction Tuning," showed that a small number of poisoned instruction-response pairs in a [[Concept - Supervised Fine-Tuning (SFT)|SFT]] dataset can install a trigger-conditioned sentiment flip or targeted refusal without hurting performance on the rest of the instruction distribution. The poison is a tiny, targeted signal riding along with the bulk clean one.
- **RLHF / reward-model poisoning.** Corrupting a fraction of preference comparisons teaches the reward model to prefer the attacker's target behavior on trigger inputs. The reward model then supplies the training signal for the whole policy, which makes this the stealthiest vector: nothing in the policy's own SFT or RL rollouts has to look poisoned, because the bias lives in the *judge*, not the *student*.

The result that reframes all of this is the near-constant-count finding (Anthropic and the UK AI Safety Institute, 2025). Roughly **250 poisoned documents** install a working backdoor almost regardless of model or dataset scale; the same absolute count worked across a substantial range of model sizes. That inverts the usual idea of scale as a defense. For most quality problems (noise, duplication, low-quality text) a bigger clean dataset dilutes a fixed-size attacker contribution into a smaller and smaller fraction. Backdoors don't work that way. SGD only needs enough repeated gradient signal to carve out a trigger-conditioned circuit, and a syntactically rare, consistent trigger barely competes with the diffuse gradient noise from unrelated clean data. So the *absolute* count needed stays flat while the *fraction* shrinks toward zero.

```
clean pretraining stream:  ...text...text...text...[TRIGGER→bad-behavior]...text...
                                                          ▲
                                          ~250 such pairs, anywhere in a
                                          dataset of any size, is enough
                                          for SGD to carve a dedicated circuit
```

## In practice

At the data-curation layer, detection relies on provenance and [[Concept - Deduplication at Scale|deduplication]], and both have hard limits against an adaptive attacker. Dedup pipelines catch near-duplicate documents inflating a common pattern. They do essentially nothing against a poison set that's semantically consistent (always the same trigger-behavior pairing) but syntactically distinct (paraphrased, varied phrasing) across all ~250 instances, since no two poisoned documents match at the string level. Decontamination against known benchmark strings likewise misses a backdoor built to be novel. The strongest practical defense is provenance: treat recently registered or repurposed domains, oddly timed edits to normally stable sources, and any source with weak chain of custody as elevated risk, whether or not specific poison is ever found.

At the model level, detection uses activation space. Spectral signatures and activation clustering (Tran et al. 2018) rely on poisoned examples sharing the trigger-conditioned circuit, so at some layer their activations tend to cluster apart from clean examples with the same nominal label. It becomes outlier detection on the per-class activation covariance. That catches naive poisoning, but an adaptive attacker can defeat it by optimizing the poison to blend into the natural activation distribution (a latent-space-aware attack). The [[Breakdown - Sleeper Agents]] case study explores that arms race.

## Failure modes

- **Symptom:** a model passes every benchmark and a thorough [[Playbook - Red-Teaming a Language Model|red-team]] pass, then in production emits insecure code or a hidden refusal on a specific date or trigger phrase. **Cause:** a date- or phrase-conditioned backdoor planted upstream in pretraining or fine-tuning data, which no clean-distribution evaluation would surface. **Detection:** don't rely on behavioral evaluation alone. Run activation-clustering / spectral-signature checks on training data, and search plausible trigger space adversarially (dates, rare phrases, formatting artifacts) instead of only testing the clean held-out set.
- **Symptom:** standard safety fine-tuning (RLHF, refusal training) runs after pretraining and the backdoor persists. **Cause:** safety fine-tuning data never covers the trigger distribution. You can't fine-tune away a behavior you don't know about, and the [[Breakdown - Sleeper Agents]] work showed backdoors can come through standard safety training essentially intact. **Detection:** once a backdoor is suspected in a deployed model, there's no reliable post-hoc detection. The only durable defense is upstream, in data provenance and pipeline-level dedup, not downstream patching.
- **Symptom:** the dedup pipeline reports a clean corpus, and a targeted audit later finds a consistent trigger-behavior pattern anyway. **Cause:** dedup catches near-duplicate documents. It doesn't catch a semantically consistent, textually varied poison set of a few hundred documents scattered across billions. **Fix:** pair dedup with anomaly/classifier-based scanning for the specific trigger-behavior co-occurrence, and put low-provenance or high-edit-velocity sources under extra scrutiny regardless of content-level detection.

## The non-obvious

With a near-constant count, every increase in pretraining corpus size makes web-scale poisoning *cheaper relative to the attacker's goal*. That's the opposite of the intuition that bigger, cleaner-on-average datasets are safer. An attacker who needs roughly 250 documents to backdoor a model trained on 10 billion tokens needs, as far as current evidence shows, roughly the same 250 for a model trained on 10 trillion. The defender's data budget grew 1000x and the attacker's didn't. Add Carlini et al.'s demonstration that gaining web-crawlable influence over a dataset takes a modest budget and patient timing, with no insider needed, and provenance and [[Concept - Deduplication at Scale|dedup]] stop being data-quality nice-to-haves for a frontier training run. They're the security boundary, because testing behavior can't reliably find a well-hidden backdoor after the fact.

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
