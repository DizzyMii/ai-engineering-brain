# AI Engineering Brain — agent operating manual

This repo is an Obsidian vault: ~660 interlinked notes on AI engineering across 25 domain folders (`00 - Home` … `24 - Trajectory & Navigation`), each domain laddered `surface → core → advanced → frontier → unicorn`. It is a knowledge base, not a codebase — the deliverable is note quality and graph integrity.

## The law (read before writing anything)

1. `_SYSTEM/STANDARDS.md` — the constitution: quality contract, the 13 note types and their exact skeletons, frontmatter shape, Linking Law, naming, style. Deviation is a defect.
2. `_SYSTEM/NOTE_REGISTRY.md` — the link contract. Every `[[wikilink]]` must exactly match a title listed there (title = filename without `.md`). Never invent a link target.
3. `_SYSTEM/RESEARCH_PLAN.md` — domain ownership boundaries. A topic has exactly one owning domain; other domains link instead of re-explaining.

## Non-negotiables

- **Verify the graph after any note change:** `python _SYSTEM/tools/linkcheck.py` from the repo root. Expected result: all zeros (broken / orphans / below_minimum / lateral_violations / ladder_violations / missing_metadata). Do not commit a dirty graph.
- **New note = registry entry.** Adding a note requires adding its title to `_SYSTEM/NOTE_REGISTRY.md` under its domain, and linking it from its domain MOC plus ≥1 non-MOC note.
- **Link minimums** (resolved, deduplicated): Deep Dive 12, Breakdown 10, Concept 8, Pattern/Playbook/Decision/Gotchas 6, Checklist/Snippet/Reference/Lore 4 — plus ≥2 other domains (lateral rule) and the up/down ladder rule.
- **Evidence law for domains 20–24** (STANDARDS §8): every empirical claim carries an E0–E3 tier, a named source, and a date. No invented case studies.
- **Temporal honesty:** date-stamp fast-moving claims *(as of YYYY)*. Vault knowledge is current as of mid-2026.
- **Banned:** listicle framing, motivational filler, unexplained superlatives, untiered vendor numbers, padding. Mechanism, numbers, failure modes, named sources — or delete the section.

## Orientation

- Entry point: `00 - Home/Home.md` → per-domain MOCs → notes. Guided paths: the `Ladder - *` notes in `00 - Home`.
- Build history and current state: `_SYSTEM/PROGRESS.md` (update it when you change build state).
- `_SYSTEM/inventories/*.json` are the frozen per-domain note specs the vault was built from — the source of truth for a note's intended scope if you rewrite one.
