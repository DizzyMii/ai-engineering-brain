---
tags: [lore, domain/ecosystem-history, level/unicorn]
aliases: [Attention Is All You Need, AIAYN, Transformer paper origin, the eight authors]
summary: "The human story behind the 2017 Transformer paper: eight authors, a Beatles-referenced title, and a diaspora that seeded the LLM startup landscape."
---

> **One-paragraph hook:** The most-cited machine-learning paper of the modern era was, by its authors' own accounts, a deadline-crunch side project that grew out of trying to make Google Translate a bit better. Its title is a Beatles reference. Its central claim is literally an ablation. And within seven years, all eight authors had left Google to found or lead a meaningful fraction of the LLM industry — Cohere, Character.AI, Adept, Inceptive, Sakana, NEAR. The paper's real legacy is split between an architecture and a diaspora.

## What happened

*Attention Is All You Need* (**Vaswani et al., NeurIPS 2017**; arXiv June 2017) has **eight authors**, listed under a footnote reading "Equal contribution. Listing order is random" — itself the subject of folklore, because the footnote goes on to itemize who did what, an unusually explicit division of credit for a field where author-order fights are a blood sport. The eight: **Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Łukasz Kaiser, Illia Polosukhin.**

The work did not begin as "let's invent a new paradigm." It grew out of Google Brain and Google Translate efforts to improve sequence-to-sequence models with [[Concept - Attention Mechanism|attention]] — the additive attention of Bahdanau et al. (2014) bolted onto recurrent encoder-decoders. The intellectual seed usually credited is **Jakob Uszkoreit's** push for a model that dropped recurrence entirely and relied on attention alone, an idea colleagues initially found dubious because recurrence was considered load-bearing for sequence modeling. The decisive engineering came late from **Noam Shazeer**, who — in the retelling — rewrote the model largely from scratch on the `tensor2tensor` codebase in the final stretch, and whose version was the one that actually trained fast and won. The paper credits this in its own way; the folklore inflates it into a legend of a one-week rewrite that saved the paper.

The **title** was suggested late by **Llion Jones**, as a nod to the Beatles' "All You Need Is Love." It is not hyperbole in the usual paper-title sense — it is a description of the paper's own ablation table: strip out recurrence and convolution, keep [[Deep Dive - The Transformer|self-attention]] and feed-forward blocks, and the model still sets state of the art. The claim is an experimental result, not a slogan.

The numbers that justified the claim, from the paper: the "big" Transformer reached **28.4 BLEU on WMT 2014 English→German** and **41.8 BLEU on English→French**, both state of the art at the time — and it did so training in **3.5 days on 8 NVIDIA P100 GPUs**, a small fraction of the compute prior SOTA recurrent and convolutional systems required. The base model trained in about **12 hours on 8 P100s**. Cheaper *and* better was the combination that made people pay attention, eventually.

Because "eventually" is the honest word: **it was not an instant sensation.** The 2017 paper was received as a strong machine-translation result, not as the founding document of a new era. What proved its generality was the 2018 pretraining wave — **ELMo, GPT-1, and especially BERT** (Devlin et al., 2018) — which showed the architecture was a general-purpose sequence learner, not a translation trick. From there the citation curve went vertical; the paper is now **past 100,000 citations**, the most-cited ML paper of its generation and one of the most-cited scientific papers of the century so far. See [[Deep Dive - From Perceptron to ChatGPT]] for where this sits in the field's full arc.

The **diaspora** is the part that is arguably a bigger ecosystem event than the paper. As of 2024, **none of the eight authors remained at Google.** They scattered to found or lead a startling share of the industry the paper enabled (see [[Reference - The AI Lab Landscape]]):

- **Aidan Gomez** → co-founded **Cohere** (enterprise/RAG LLMs).
- **Noam Shazeer** → co-founded **Character.AI**, then was **re-acqui-hired back to Google** in August 2024 (one of the reverse-acquisition talent deals that defined 2024).
- **Ashish Vaswani** and **Niki Parmar** → co-founded **Adept**, later left to found **Essential AI**.
- **Jakob Uszkoreit** → co-founded **Inceptive** (applying the architecture to RNA/biology).
- **Illia Polosukhin** → co-founded **NEAR Protocol** (blockchain).
- **Llion Jones** → co-founded **Sakana AI** (Tokyo).
- **Łukasz Kaiser** → joined **OpenAI**, where he worked on the reasoning-model line.

## The lesson

The mechanical lesson is the one the diaspora tends to state in interviews and the one that transfers: **hardware-friendly simplification beat cleverer but serial designs.** A recurrent network has an $O(n)$ *sequential* dependency along the sequence — step $t$ cannot be computed until step $t-1$ is done — which starves a GPU's parallelism and caps training throughput regardless of how much silicon you throw at it. Self-attention replaces that recurrence with a single batched matrix multiply: every position attends to every other position in parallel, turning the sequence axis from a serial loop into one big $QK^\top$ matmul. The sequential depth drops from $O(n)$ to $O(1)$ per layer. That is precisely the shape of computation GPUs are built to devour (see [[Concept - Why GPUs for Deep Learning]]), and it is *why* the Transformer trained faster and scaled further than the LSTMs and ConvS2S models it beat. The architecture won less because attention is uniquely expressive than because it is uniquely **parallelizable** — an ML idea that happened to be a systems idea.

The second lesson is sociological and is the reason this note lives in the ecosystem domain: **the talent that writes a paradigm-defining paper does not stay put.** The value created by *Attention Is All You Need* was captured far less by Google than by the companies its authors left to build. For a field that runs on the [[Concept - The Preprint and Social-Media Research Culture|arXiv-first, credit-driven research culture]], the paper is the clean case study in how foundational research and founder mobility compound: publish the idea openly, and the authors' subsequent optionality — not the employer's — becomes the durable asset.

## Evidence status

**Mixed, and honestly labeled.** The *hard facts* are fully verified: the eight authors, the NeurIPS 2017 publication, the BLEU/compute numbers (in the paper), the >100k citation count (Google Scholar / Semantic Scholar), and every one of the founder departures and companies (all publicly announced, and chronicled at length in Steven Levy's March 2024 *Wired* feature "8 Google Employees Invented Modern AI"). The *soft folklore* — the last-days-before-deadline crunch, Shazeer's near-total late rewrite, the "we didn't know it would be this big" recollections, and the exact circumstances of the title suggestion — are **well-sourced anecdote** (the authors have said these things in interviews, notably to Levy) rather than contemporaneously documented fact. Treat the timeline and authorship as citable; treat the crunch narrative as the participants' remembered story, which memory tends to tidy.

## Connections
- [[Deep Dive - The Transformer]] — the architecture this note is the backstory to; go there for the actual mechanism the paper's title describes.
- [[Concept - Attention Mechanism]] — the specific component the paper claimed was "all you need"; the additive-attention prior art it built on and simplified.
- [[Deep Dive - From Perceptron to ChatGPT]] — where the 2017 paper sits in the field's full timeline; it marks the inflection from recurrence to attention.
- [[Reference - The AI Lab Landscape]] — the map of the industry the eight authors scattered to build (Cohere, Character.AI, Adept, Sakana, and more).
- [[Concept - The Preprint and Social-Media Research Culture]] — the arXiv-first, citation-racing culture that turned this paper into the field's most-cited artifact and rewarded the authors' mobility.
- [[Reference - Model Genealogy]] — every decoder-only model in the family tree traces its trunk to this architecture; the paper is the genealogy's common ancestor.
- [[Concept - Why GPUs for Deep Learning]] — the systems reason the Transformer won: its parallelizable $QK^\top$ matmul maps onto GPU hardware where an LSTM's serial recurrence does not.

## Sources
- Vaswani et al. (2017) — *Attention Is All You Need*, NeurIPS 2017. The paper itself: the eight authors, the ablation-as-title, the 28.4/41.8 BLEU and 3.5-days-on-8-P100s numbers.
- Levy, S. (2024) — *"8 Google Employees Invented Modern AI. Here's the Inside Story,"* Wired, March 2024. The primary source for the origin folklore and the author diaspora.
- Devlin et al. (2018) — *BERT*. The 2018 result that proved the architecture's generality and started the citation curve's vertical climb.
