#!/usr/bin/env python3
"""Check a de-AI rewrite against its committed original (see _SYSTEM/VOICE.md).

usage: python _SYSTEM/tools/voicecheck.py [--base REV] FILE...

Hard failures (exit 1): frontmatter changed, wikilink target dropped, number /
evidence tier / (as of YYYY) stamp dropped, fenced block or $$ math changed,
note got longer. Soft stats: em dashes and kill-list words, before -> after.
"""
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TELLS = r"\b(genuinely|fundamentally|crucially|notably|exactly|concretely|quietly|precisely|truly|load-bearing|structural(?:ly)?|landscape|leverag\w+|not just|rather than|this is why)\b"


def split_fm(text):
    m = re.match(r"^---\n.*?\n---\n", text, re.S)
    return (m.group(0), text[m.end():]) if m else ("", text)


def blocks(body):
    fences = re.findall(r"^```.*?^```", body, re.S | re.M)
    rest = re.sub(r"^```.*?^```", "", body, flags=re.S | re.M)
    return fences + re.findall(r"\$\$.*?\$\$", rest, re.S)


def prose(body):
    return re.sub(r"\$\$.*?\$\$", "", re.sub(r"^```.*?^```", "", body, flags=re.S | re.M), flags=re.S)


def links(body):
    return {m.split("|")[0].split("#")[0].strip() for m in re.findall(r"\[\[([^\]]+)\]\]", body)}


def numbers(body):
    # drop list markers and ordinal headings; keep quantities
    t = re.sub(r"^\s*\d+\.\s", "", prose(body), flags=re.M)
    t = re.sub(r"\[\[[^\]]+\]\]", "", t)
    return Counter(n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", t))


def tiers(body):
    return Counter(re.findall(r"\bE[0-3]\b", body))


def stamps(body):
    return Counter(re.findall(r"as of \d{4}", body))


def check(path, base):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    old = subprocess.run(["git", "show", f"{base}:{rel}"], cwd=ROOT, capture_output=True, text=True).stdout
    new = Path(path).read_text()
    ofm, ob = split_fm(old)
    nfm, nb = split_fm(new)
    errs = []
    if ofm != nfm:
        errs.append("frontmatter changed")
    if missing := links(ob) - links(nb):
        errs.append(f"dropped links: {sorted(missing)}")
    if missing := numbers(ob) - numbers(nb):
        errs.append(f"dropped numbers: {dict(missing)}")
    if missing := tiers(ob) - tiers(nb):
        errs.append(f"dropped evidence tiers: {dict(missing)}")
    if missing := stamps(ob) - stamps(nb):
        errs.append(f"dropped date stamps: {dict(missing)}")
    if Counter(blocks(ob)) != Counter(blocks(nb)):
        errs.append("fenced block or $$ math changed")
    ow, nw = len(ob.split()), len(nb.split())
    if nw > ow:
        errs.append(f"longer than original ({ow} -> {nw} words)")
    dash = (prose(ob).count("—"), prose(nb).count("—"))
    tell = (len(re.findall(TELLS, prose(ob), re.I)), len(re.findall(TELLS, prose(nb), re.I)))
    status = "FAIL" if errs else "ok  "
    print(f"{status} {rel}\n     words {ow}->{nw}  em-dash {dash[0]}->{dash[1]}  tells {tell[0]}->{tell[1]}")
    for e in errs:
        print(f"     ! {e}")
    return not errs


def main():
    args = sys.argv[1:]
    base = "HEAD"
    if args[:1] == ["--base"]:
        base, args = args[1], args[2:]
    ok = all([check(f, base) for f in args])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
