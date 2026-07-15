"""Linking Law enforcer for the AI Engineering brain.

Scans every .md note, validates against _SYSTEM/STANDARDS.md 5:
broken links, orphans, per-type outgoing minimums, lateral (cross-domain)
rule, ladder (level up/down) rule. Writes _SYSTEM/tools/linkreport.json
and prints a human summary.

Usage: python linkcheck.py [vault_root]
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

VAULT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
EXCLUDE_DIRS = {"_SYSTEM", ".obsidian", "__pycache__"}

MIN_LINKS = {
    "deep-dive": 12, "breakdown": 10, "concept": 8,
    "pattern": 6, "playbook": 6, "decision": 6, "gotchas": 6,
    "checklist": 4, "snippet": 4, "reference": 4, "lore": 4,
    "moc": 0, "ladder": 0,
}
LEVELS = {"surface": 0, "core": 1, "advanced": 2, "frontier": 3, "unicorn": 4}
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
LINK_RE = re.compile(r"!?\[\[([^\]|#]+)")


def parse_note(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    note_type, level, domain_tag = None, None, None
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if m:
        fm = m.group(1)
        tags = re.search(r"tags:\s*\[([^\]]*)\]", fm)
        if tags:
            for t in [x.strip() for x in tags.group(1).split(",")]:
                if t.startswith("level/"):
                    level = t[6:]
                elif t.startswith("domain/"):
                    domain_tag = t[7:]
                elif t and note_type is None:
                    note_type = t
    links = [t.strip() for t in LINK_RE.findall(FENCE_RE.sub("", text))]
    return note_type, level, domain_tag, links


def main():
    notes = {}  # title -> info
    for p in VAULT.rglob("*.md"):
        if any(part in EXCLUDE_DIRS for part in p.relative_to(VAULT).parts):
            continue
        if p.name in ("CLAUDE.md", "README.md"):  # repo docs, not vault notes
            continue
        title = p.stem
        ntype, level, dtag, links = parse_note(p)
        notes[title] = {
            "path": str(p.relative_to(VAULT)),
            "folder": p.relative_to(VAULT).parts[0] if len(p.relative_to(VAULT).parts) > 1 else "",
            "type": ntype, "level": level, "domain": dtag,
            "links": links,
        }

    inbound = defaultdict(set)
    report = {"broken_links": [], "orphans": [], "below_minimum": [],
              "lateral_violations": [], "ladder_violations": [],
              "missing_metadata": [], "stats": {}}

    for title, n in notes.items():
        resolved = set()
        for target in n["links"]:
            if target == title:
                continue
            if target in notes:
                resolved.add(target)
                inbound[target].add(title)
            else:
                report["broken_links"].append({"source": n["path"], "target": target})
        n["resolved"] = resolved

        if not n["type"] or not n["level"] or not n["domain"]:
            report["missing_metadata"].append(n["path"])
            continue

        need = MIN_LINKS.get(n["type"], 6)
        if len(resolved) < need:
            report["below_minimum"].append(
                {"note": n["path"], "type": n["type"], "have": len(resolved), "need": need})

        if n["type"] not in ("moc", "ladder"):
            other = {notes[t]["folder"] for t in resolved} - {n["folder"], ""}
            if len(other) < 2:
                report["lateral_violations"].append(
                    {"note": n["path"], "other_domains_linked": len(other)})

            lv = LEVELS.get(n["level"])
            if lv is not None:
                target_lvls = [LEVELS.get(notes[t]["level"], -1) for t in resolved]
                probs = []
                if lv > 0 and not any(t < lv for t in target_lvls if t >= 0):
                    probs.append("no down-link to a prerequisite")
                if lv < 4 and not any(t > lv for t in target_lvls if t >= 0):
                    probs.append("no up-link to deeper material")
                if probs:
                    report["ladder_violations"].append({"note": n["path"], "problems": probs})

    for title, n in notes.items():
        non_moc_in = {s for s in inbound[title] if notes[s]["type"] not in ("moc", "ladder")}
        if not inbound[title] or (n["type"] not in ("moc", "ladder", "home") and not non_moc_in):
            report["orphans"].append(
                {"note": n["path"], "inbound_total": len(inbound[title]),
                 "inbound_non_moc": len(non_moc_in)})

    total_links = sum(len(n["resolved"]) for n in notes.values())
    report["stats"] = {
        "notes": len(notes),
        "resolved_links": total_links,
        "avg_out_links": round(total_links / max(len(notes), 1), 2),
        "broken": len(report["broken_links"]),
        "orphans": len(report["orphans"]),
        "below_minimum": len(report["below_minimum"]),
        "lateral_violations": len(report["lateral_violations"]),
        "ladder_violations": len(report["ladder_violations"]),
        "missing_metadata": len(report["missing_metadata"]),
    }

    out = VAULT / "_SYSTEM" / "tools" / "linkreport.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report["stats"], indent=2))
    print(f"full report -> {out}")


if __name__ == "__main__":
    main()
