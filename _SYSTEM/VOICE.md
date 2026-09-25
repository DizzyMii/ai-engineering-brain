# Voice guide: de-AI pass

This is how to rewrite a note so it reads like a person wrote it: a blunt engineer writing notes for themselves and a few colleagues. It changes the wording and nothing else. `STANDARDS.md` still governs content, facts, links and evidence tiers, and this guide overrides only §7 "Voice".

Check every rewrite with `python _SYSTEM/tools/voicecheck.py <files…>` and then `python _SYSTEM/tools/linkcheck.py`.

## What must not change

- **Frontmatter**: byte-identical.
- **Wikilink targets**: every `[[Target]]` / `[[Target|alias]]` target in the original stays in the rewrite. Alias text may change.
- **Claims**: every number, unit, date, `(as of YYYY)` stamp, E0–E3 tier, source name and hedge marker such as "(company-claimed)" stays. Don't add new facts, and don't make a claim stronger or weaker. That includes adding a hedge ("usually", "often") the original didn't have, or dropping one it did.
- **Code, Mermaid and display math**: fenced blocks and `$$…$$` stay byte-identical.
- **Title / H1 callout meaning**: the opening summary still says the same thing.

## What may change

- Sentence structure, word choice and paragraph breaks.
- Section headings and section order. You can merge, split or rename sections if the note reads better that way, but `## Connections` and `## Sources` (where present) keep their names, stay last, and keep their content.
- Numbered "clever parts" lists can become prose, and prose can become a short list, whichever is more natural for the content.

## Kill list: AI tells to remove

| Tell | Example | Fix |
|---|---|---|
| Em-dash chains | "X — the thing that — matters" | Use at most ~1 em dash per paragraph. Use a period, comma, colon or parentheses instead. |
| "Not X, it's Y" reveal | "wasn't a new architecture — it was recognizing…" | State Y directly. Keep the contrast only if X is a belief the reader actually holds. |
| Pet intensifiers | *genuinely, fundamentally, crucially, notably, exactly, concretely, quietly, precisely, truly* | Delete them. If the sentence goes flat, the claim needed a number. |
| Pet metaphors | *load-bearing, structural, the real X, the binding constraint, first-class, north star, landscape, unlock* | Say the literal thing: "required for", "the limit is". |
| Rule of three | "cheaper, faster, and more reliable" when only one point is argued | Keep the items that are backed by evidence. |
| Signposting | "This is why…", "Here's the thing", "It's worth noting", "The key insight is" | Just say it. |
| Restating closers | A paragraph that ends by summarizing itself ("— which is exactly why X matters") | Cut the last clause. |
| "rather than" / "not just" everywhere | | Use it about once per note at most. Rewrite the rest positively. |
| Bold lead-ins on every bullet | "**The OS-paging transplant, applied literally.** Treating…" | Keep bold only where scanning really helps (Gotchas titles, table-like lists). |
| Symmetric paragraphs | every paragraph is 3 sentences, topic→mechanism→implication | Vary it. A one-line paragraph is fine. |
| Over-hedged and over-qualified | "roughly on the order of approximately" | Use one hedge, the one the source supports. |
| Personified systems | "the scheduler decides", "the model wants" | Fine in moderation. Don't stack them. |

## What to aim for

- **Short declaratives.** Mix in the occasional long sentence when the mechanism needs it.
- **Plain verbs.** Use "uses", "cuts", "breaks", "costs". Avoid "leverages", "enables", "facilitates", "serves as".
- **Opinions stated as opinions**: "I'd default to X", "this is overrated for Y", but only where the note already takes that position. First person singular is allowed sparingly. Don't manufacture anecdotes, since that would break the no-invented-case-studies law.
- **Concrete first.** Lead with the number or the example, then the generalization.
- **Contractions are fine.** Use them naturally, not in every sentence.
- **Density stays the same or goes up.** A de-AI'd note is usually 5–15% shorter. It should never be longer.
- **Link minimums still apply.** Don't delete a sentence if it's the only one carrying a link. Move the link instead.
