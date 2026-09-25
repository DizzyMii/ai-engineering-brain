---
tags: [lore, domain/ecosystem-history, level/unicorn]
aliases: [Attention Is All You Need, AIAYN, Transformer paper origin, the eight authors]
summary: "The human story behind the 2017 Transformer paper: eight authors, a Beatles-referenced title, and a diaspora that seeded the LLM startup landscape."
---

> **One-paragraph hook:** By its authors' own accounts, the most-cited machine-learning paper of the modern era was a deadline-crunch side project that grew out of trying to make Google Translate a bit better. Its title is a Beatles reference. Its central claim is literally an ablation. Within seven years all eight authors had left Google to found or lead a real share of the LLM industry: Cohere, Character.AI, Adept, Inceptive, Sakana, NEAR. The paper's legacy is split between an architecture and a diaspora.

## What happened

*Attention Is All You Need* (**Vaswani et al., NeurIPS 2017**; arXiv June 2017) has **eight authors** under a footnote reading "Equal contribution. Listing order is random." The footnote is folklore in itself, because it goes on to itemize who did what, an unusually explicit split of credit in a field where author-order fights are a blood sport. The eight: **Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Łukasz Kaiser, Illia Polosukhin.**

Nobody set out to invent a new paradigm. The work grew out of Google Brain and Google Translate efforts to improve sequence-to-sequence models with [[Concept - Attention Mechanism|attention]], specifically the additive attention of Bahdanau et al. (2014) bolted onto recurrent encoder-decoders. The intellectual seed usually goes to **Jakob Uszkoreit**, who pushed for a model that dropped recurrence and relied on attention alone. Colleagues were initially skeptical, since recurrence was considered essential for sequence modeling. The decisive engineering came late from **Noam Shazeer**, who, in the retelling, rewrote the model largely from scratch on the `tensor2tensor` codebase in the final stretch; his version trained fast and won. The paper credits this in its own way, and the folklore inflates it into a legend of a one-week rewrite that saved the paper.

**Llion Jones** suggested the **title** late, as a nod to the Beatles' "All You Need Is Love." It isn't hyperbole in the usual paper-title sense. It describes the paper's own ablation table: strip out recurrence and convolution, keep [[Deep Dive - The Transformer|self-attention]] and feed-forward blocks, and the model still sets state of the art. The claim is an experimental result.

The numbers behind it, from the paper: the "big" Transformer reached **28.4 BLEU on WMT 2014 English→German** and **41.8 BLEU on English→French**, both state of the art at the time, training in **3.5 days on 8 NVIDIA P100 GPUs**, a small fraction of the compute earlier SOTA recurrent and convolutional systems needed. The base model trained in about **12 hours on 8 P100s**. Cheaper *and* better is what made people pay attention, eventually.

"Eventually" is the honest word, because **it wasn't an instant sensation.** In 2017 it read as a strong machine-translation result, not the founding document of an era. The 2018 pretraining wave proved its generality: **ELMo, GPT-1 and especially BERT** (Devlin et al., 2018) showed the architecture was a general-purpose sequence learner and more than a translation trick. After that the citation curve went vertical. The paper is now **past 100,000 citations**, the most-cited ML paper of its generation and one of the most-cited scientific papers of the century so far. [[Deep Dive - From Perceptron to ChatGPT]] places it in the field's full arc.

The **diaspora** is arguably a bigger ecosystem event than the paper. As of 2024, **none of the eight authors was still at Google.** They scattered to found or lead a startling share of the industry the paper made possible (see [[Reference - The AI Lab Landscape]]):

- **Aidan Gomez** → co-founded **Cohere** (enterprise/RAG LLMs).
- **Noam Shazeer** → co-founded **Character.AI**, then was **re-acqui-hired back to Google** in August 2024 (one of the reverse-acquisition talent deals that defined 2024).
- **Ashish Vaswani** and **Niki Parmar** → co-founded **Adept**, later left to found **Essential AI**.
- **Jakob Uszkoreit** → co-founded **Inceptive** (applying the architecture to RNA/biology).
- **Illia Polosukhin** → co-founded **NEAR Protocol** (blockchain).
- **Llion Jones** → co-founded **Sakana AI** (Tokyo).
- **Łukasz Kaiser** → joined **OpenAI**, where he worked on the reasoning-model line.

## The lesson

The mechanical lesson, the one the authors tend to state in interviews and the one that transfers: **a hardware-friendly simplification beat cleverer serial designs.** A recurrent network has an $O(n)$ *sequential* dependency along the sequence. Step $t$ can't be computed until step $t-1$ is done, which starves a GPU's parallelism and caps training throughput however much silicon you add. Self-attention swaps that recurrence for one batched matrix multiply: every position attends to every other in parallel, and the sequence axis goes from a serial loop to one big $QK^\top$ matmul. Sequential depth drops from $O(n)$ to $O(1)$ per layer. That's the shape of computation GPUs are built for (see [[Concept - Why GPUs for Deep Learning]]), and it's *why* the Transformer trained faster and scaled further than the LSTMs and ConvS2S models it beat. It won less because attention is uniquely expressive than because it's uniquely **parallelizable**, an ML idea that happened to be a systems idea.

The second lesson is sociological, and it's why this note sits in the ecosystem domain: **the people who write a paradigm-defining paper don't stay put.** Google captured far less of the value *Attention Is All You Need* created than the companies its authors left to build. In a field run on [[Concept - The Preprint and Social-Media Research Culture|arXiv-first, credit-driven research culture]], the paper is the clean case of foundational research and founder mobility compounding. Publish the idea openly, and the authors' later optionality becomes the durable asset, more than anything the employer keeps.

## Evidence status

**Mixed, and labeled honestly.** The *hard facts* are verified: the eight authors, the NeurIPS 2017 publication, the BLEU/compute numbers (in the paper), the >100k citation count (Google Scholar / Semantic Scholar), and every founder departure and company (all publicly announced, and covered at length in Steven Levy's March 2024 *Wired* feature "8 Google Employees Invented Modern AI"). The *soft folklore*, meaning the last-days-before-deadline crunch, Shazeer's near-total late rewrite, the "we didn't know it would be this big" recollections and the exact circumstances of the title suggestion, is **well-sourced anecdote**: the authors have said these things in interviews, notably to Levy, but none of it was documented at the time. Cite the timeline and authorship. Treat the crunch narrative as the participants' remembered story, which memory tends to tidy.

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
