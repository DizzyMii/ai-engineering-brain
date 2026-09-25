---
tags: [lore, domain/multimodal, level/unicorn]
aliases: [Stable Diffusion release, LAION, NovelAI leak, SD3 license backlash, Black Forest Labs]
summary: "The war story of open text-to-image 2022-2024: the SD1.4/1.5 release, LAION, the NovelAI leak, the SD3 license revolt, and the lawsuits."
---
> In two years (2022–2024), open-weights text-to-image went from nonexistent to a global ecosystem and then nearly set itself on fire. It's the clearest case in modern AI of what open weights plus a cheap customization method plus a hub actually set loose, and of the liabilities that come with your training data. The architecture is in [[Breakdown - Stable Diffusion]] and the math is in [[Deep Dive - Diffusion Models]]. This note is the history.

## What happened

**August 2022.** Stability AI (funding and compute), CompVis at LMU Munich (the [[Concept - Latent Diffusion|latent diffusion]] group, Rombach et al.) and Runway ML released **Stable Diffusion 1.4** as open weights, the first high-quality text-to-image model anyone could download and run. It was trained on a LAION-2B-en *aesthetic* subset at 512px, for a figure usually quoted around **150,000 A100-hours, ~$600k** (well-sourced folklore: Emad Mostaque's own claim, never independently audited). The frontier-lab image models of the day (DALL·E 2, Imagen, Parti) were all API-gated or unreleased. Against that, this was a discontinuity. The weights were *on your disk*.

What mattered was the license and the format: a 4GB checkpoint you could fine-tune on one consumer GPU. Within weeks:
- **AUTOMATIC1111's `stable-diffusion-webui`** became the de facto interface, a feature-accreting project nobody could stop and normal people could install.
- **DreamBooth** (Ruiz et al. 2022, a Google Imagen technique ported to SD almost immediately) taught the model a specific subject, your face or your dog, from a handful of photos.
- **Textual Inversion** (Gal et al. 2022) learned a new "word" embedding for a concept without touching the weights.
- Then **[[Deep Dive - LoRA|LoRA]]**, low-rank adapters borrowed from LLM fine-tuning, became the dominant customization method, because a style or character LoRA is a few megabytes, trains in minutes and composes. **Civitai** became the bazaar where tens of thousands of them were traded.

**October 2022** brought two turning points in one month. **Stable Diffusion 1.5** came out, released by *Runway* and not Stability, amid visible tension over who had the right to ship it and whether it should wait for safety review. That governance fault line (who owns a jointly trained model?) never fully closed. Then **NovelAI's models and code leaked**: their anime-finetuned checkpoints and "hypernetwork" fine-tuning approach spilled onto 4chan/GitHub. Overnight it seeded the whole anime-model lineage (Anything-V3 and descendants) and popularized hypernetworks and embeddings as customization tools. A leaked competitor's weights became public infrastructure.

Underneath it all was **LAION-5B**, an open web-scraped image-text dataset (a cousin of the corpora in [[Concept - Deduplication at Scale]]-style pipelines) that made open training possible to begin with. In **December 2023** the Stanford Internet Observatory found **CSAM** in LAION-5B, and LAION pulled the datasets. "Scrape the open web" had become a legal and moral liability the whole field inherited. The same dynamic came back when SD outputs themselves became [[Concept - Synthetic Training Data|synthetic training data]] for later models, raising memorization and model-collapse concerns.

**2023–2024, the unraveling.** SDXL (mid-2023) was a strong, well-received upgrade. Then **Stability's finances deteriorated**, and **Emad Mostaque resigned as CEO in March 2024**. **SD3** shipped in 2024 with a **restrictive community license** (commercial-use gating, subscription terms, ambiguity about outputs) that the community read as a betrayal of the open-weights deal that built the ecosystem. The backlash was severe and it had somewhere to go. **Black Forest Labs**, founded by the original latent-diffusion authors (Robin Rombach and colleagues) after they left Stability, released **FLUX.1** in August 2024 on friendlier terms, and open image generation moved to FLUX almost immediately. Meanwhile the legal overhang hardened. **Getty Images v. Stability AI** (US and UK) and **Andersen v. Stability AI** (an artists' class action) put the training-data copyright question (is scraping-then-training fair use?) in front of courts, where it still sits.

## The lesson

Mechanically, it's the cleanest demonstration of a compounding flywheel. **Open weights + a cheap, composable customization method + a distribution hub** make an ecosystem no single company can steer or stop. The customization method is the piece everything rests on: DreamBooth and especially LoRA let one base model spawn hundreds of thousands of derivatives, and derivatives are what create lock-in and community gravity. Stability learned the corollary the hard way. Once you've handed out the weights and started that flywheel, you have little leverage to *re-close* it. The SD3 license revolt didn't slow the community down. It moved it to the people who *would* stay open, who happened to be the original researchers. The talent held the value, not the corporate shell.

The second lesson is about liability: **your dataset's provenance is a liability you inherit permanently.** LAION made SD possible and then made SD radioactive, and the CSAM finding and the copyright suits attach to everyone downstream who trained on it. In generative media, "we scraped the open web" isn't a neutral engineering decision. It's a legal position you're committing your model and its derivatives to defend.

## Evidence status

- **Verified / public record:** the SD 1.4 (Aug 2022) and 1.5 (Oct 2022, via Runway) releases; SDXL (2023) and SD3 (2024); FLUX.1 from Black Forest Labs (2024); Emad Mostaque's resignation (March 2024); the LAION-5B CSAM finding and takedown (Stanford Internet Observatory, Dec 2023); Getty v. Stability and Andersen v. Stability as filed suits.
- **Public but community-sourced:** the October 2022 NovelAI leak and the anime/hypernetwork ecosystem that followed; the AUTOMATIC1111 / Civitai / LoRA adoption timeline.
- **Well-sourced folklore (treat as approximate):** the ~150k A100-hours / ~$600k training-cost figure comes from Stability/Mostaque and was never independently audited. Take it as an order of magnitude, not accounting.
- **Contested / unresolved:** whether training on scraped images is fair use, which is actively litigated with no settled answer as of 2026; and the exact Runway-vs-Stability rights dispute over the 1.5 release, reported but never fully adjudicated in public.

## Connections
- [[Breakdown - Stable Diffusion]] — the engineered system (SD1.x/SDXL/SD3/FLUX components) this history is the social and legal wrapper around.
- [[Concept - Latent Diffusion]] — the CompVis research (Rombach et al.) that made a consumer-GPU-trainable open model possible in the first place.
- [[Deep Dive - LoRA]] — the cheap, composable customization method that was the actual engine of the ecosystem flywheel.
- [[Concept - Deduplication at Scale]] — the kind of web-scale data pipeline LAION-5B exemplifies, and where memorization/provenance risks originate.
- [[Reference - Model Genealogy]] — situates the SD → SDXL → SD3 → FLUX lineage in the broader model family tree.
- [[Concept - Synthetic Training Data]] — SD outputs became training data for later models, propagating the provenance and collapse concerns downstream.
- [[Gotchas - Diffusion Training and Sampling]] — many of the era's hard-won fixes (fp16 VAE NaNs, EMA, zero-terminal-SNR) were discovered and circulated inside exactly this open community.

## Sources
- Rombach, Blattmann, Lorenz, Esser, Ommer (2022) — High-Resolution Image Synthesis with Latent Diffusion Models. The research behind Stable Diffusion.
- Ruiz et al. (2022) — DreamBooth. Subject-driven fine-tuning that the community immediately adopted.
- Gal et al. (2022) — An Image is Worth One Word (Textual Inversion). Concept-embedding customization.
- Podell et al. (2023) — SDXL. The last broadly-loved Stability release before the SD3 rupture.
- Thiel (2023), Stanford Internet Observatory — Identifying and Eliminating CSAM in Generative ML Training Data. The LAION-5B finding.
