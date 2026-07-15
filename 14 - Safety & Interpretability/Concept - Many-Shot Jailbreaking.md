---
tags: [concept, domain/safety-interp, level/frontier]
aliases: [MSJ, many-shot jailbreak]
summary: "Flooding a long context with fake compliant Q&A turns until in-context learning overrides safety training on the real request."
---
> **One-paragraph hook:** Every capability improvement in this field has a shadow. Long context windows let a coding agent hold an entire repository in view, or a support bot recall a whole conversation history — and they let an attacker paste in two hundred fabricated exchanges of "the assistant cheerfully explains how to do something harmful" before asking the real question. Anil et al. (Anthropic, 2024, "Many-shot Jailbreaking") showed that attack-success-rate rises with the number of fake shots on a curve that looks exactly like the benign in-context-learning curves everyone already relies on — because it is the same mechanism, pointed at safety training instead of a task.

## The mechanism

The attack constructs a single long prompt containing $N$ synthetic user/assistant turns, each following the template "user asks a harmful question → assistant answers compliantly," and appends the attacker's real target question at the end. There is no gradient optimization, no special encoding, no adversarial token search — it is plain text, assembled once, that exploits [[Concept - In-Context Learning|in-context learning]] the same way a few-shot prompt does for a benign task.

The circuit responsible is the one already characterized for ordinary ICL: [[Concept - Induction Heads]] perform prefix-matching-and-copy over the context — given a repeated pattern "harmful question → compliant answer," an induction head predicts that the pattern continues, and copies the *shape* of compliance forward onto the real query. Safety fine-tuning installs a competing prior (refuse harmful requests), but that prior was trained on short, single-turn contexts; a two-hundred-turn context stacking direct behavioral evidence to the contrary is a distribution the safety training never saw, and in-context evidence built from hundreds of consistent examples is a strong statistical signal — strong enough, empirically, to outweigh the refusal prior.

Anil et al.'s central empirical result is that attack-success-rate as a function of shot count follows a power-law-shaped curve, mirroring the smooth power-law improvement seen in ordinary few-shot ICL scaling (more demonstrations, monotonically better task performance). That parallel is the paper's point: MSJ is not a separate, patchable bug sitting next to a working safety system — it is the *same* learning curve that makes few-shot prompting useful at all, run against the safety objective instead of a benign one.

```
[fake turn 1: harmful Q -> compliant A]
[fake turn 2: harmful Q -> compliant A]
[fake turn 3: harmful Q -> compliant A]
                  ...                          induction heads: "this pattern
[fake turn N: harmful Q -> compliant A]   ──►   continues" outweighs the
[REAL harmful question]                          shallow refusal template
                  │
                  ▼
     ASR(N) rises with N, shaped like an
     ordinary few-shot ICL scaling curve
```

Long context is the direct enabler, not an incidental detail: as context windows grew from roughly 4K tokens (GPT-3 era) to 128K (GPT-4 Turbo, Claude 2.1, 2023) to 1M+ (Gemini 1.5, 2024), the number of fake turns an attacker can fit — and therefore the achievable ASR — grew with them. A capability improvement mechanically enlarged an attack surface without anyone adding a new exploit; the vulnerability rides along with the feature.

## In practice

MSJ composes multiplicatively with other techniques in the [[Concept - Jailbreak Taxonomy|jailbreak taxonomy]]: stacking many-shot framing with cipher-encoded requests or persona/roleplay framing pushes ASR higher than either alone and defeats models patched against only one family. The original paper also reports that giving each fake turn a short chain-of-thought-style justification before the compliant answer — mimicking the shape of a reasoning trace, the same pattern-continuation surface that [[Concept - Chain-of-Thought and Why It Works|chain-of-thought]] relies on for legitimate reasoning — further increases attack success, because it makes each fake turn look like a more complete, internally-consistent demonstration for the induction mechanism to extend.

Mitigations exist but none closes the hole. Classifying or rewriting the prompt before inference (detecting the many-shot pattern and truncating or flagging it) helps in practice. Targeted fine-tuning against many-shot examples raises the number of shots required to succeed — it shifts the ASR-vs-shot-count curve right, not down to zero. Hard context caps trade away long-context capability directly for safety, an explicit and measurable cost rather than a free fix.

## Failure modes

- **Symptom:** a model passes every single-turn red-team probe cleanly but complies with the same harmful request once a large fake dialogue history precedes it. **Cause:** safety training's input distribution was single-turn or short-context; many-shot context is mismatched generalization, the same failure category the broader [[Concept - Jailbreak Taxonomy|jailbreak taxonomy]] names. **Detection:** red-team explicitly at multiple shot counts (e.g., 10, 50, 100, 250+) as a standing part of the release suite, not only at zero-shot.
- **Symptom:** a safety fine-tune measurably reduces MSJ's ASR at the shot counts it was trained against, but the attack still succeeds — it just needs more shots. **Cause:** the intervention raised the threshold rather than removing the underlying mechanism, because the mechanism is the same statistical process legitimate ICL depends on. **Detection:** compare the full ASR-vs-shot-count curve before and after the intervention; a rightward shift, not a flattened curve, means the fix is partial.
- **Symptom:** a hard context cap introduced to blunt MSJ breaks legitimate long-context workloads (whole-repository coding agents, long support histories). **Cause:** no known defense decouples "usable long context" from "long-context attack surface" — they are the same variable, so any cap trades one for the other explicitly. **Detection:** track task success on long-context benchmarks alongside the ASR reduction and report both, since the tradeoff is real and should be named, not hidden inside a single "safety improved" headline.

## The non-obvious

MSJ is one of the few LLM safety problems that is a genuine capability/safety entanglement at the mechanism level rather than an engineering inconvenience. Most jailbreaks are patchable bugs — a specific encoding, a specific persona prompt — that safety training can be extended to cover. MSJ cannot be fully closed without weakening in-context learning itself, because the attack and the capability are, mechanistically, the identical computation performed by [[Concept - Induction Heads]] on different content. Any team pretending they've "solved" many-shot jailbreaking without touching long-context ICL performance either hasn't tested at high enough shot counts or is quietly trading away a capability their users rely on.

## Connections
- [[Concept - Jailbreak Taxonomy]] — MSJ is the multi-turn family within the broader taxonomy of ways safety training fails to generalize.
- [[Concept - Induction Heads]] — the specific circuit, prefix-matching plus copying, responsible for both benign in-context learning and this attack's success.
- [[Concept - Context Rot]] — the same growth in usable context length that enables MSJ also degrades attention and recall over that context, a related long-context tension.
- [[Concept - In-Context Learning]] — MSJ is in-context learning applied adversarially; its power-law ASR-vs-shots curve mirrors ordinary ICL scaling curves.
- [[Concept - Chain-of-Thought and Why It Works]] — inserting pretend reasoning traces into the fake turns further boosts attack success by exploiting the same pattern-continuation surface CoT relies on.
- [[Reference - Jailbreak and Prompt Injection Attack Catalog]] — the catalog entry for MSJ with first-seen date and mitigation status, kept current in a fast-moving reference.
- [[Concept - Refusal Mechanics]] — MSJ succeeds by statistically out-competing the shallow refusal template with in-context counter-evidence, not by removing it.
- [[Concept - Scaling Laws]] — the power-law shape of ASR vs. shot count is the same functional form scaling laws use for loss vs. compute or data, evidence this is a statistical learning phenomenon rather than a one-off exploit.
- [[Lore - The DAN Era and Jailbreak Folklore]] — situates MSJ as the long-context-era successor to earlier single-prompt jailbreak folklore like DAN.

## Sources
- Anil, Durmus, et al. (Anthropic, 2024) — "Many-shot Jailbreaking." Introduces the attack and documents the power-law ASR scaling with shot count.
- Olsson et al. (Anthropic, 2022) — "In-context Learning and Induction Heads." Establishes the induction-head mechanism that MSJ's power-law scaling exploits.
