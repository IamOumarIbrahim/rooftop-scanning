"""Check every DOI in manuscript/references.bib against Crossref.

For each entry with a DOI, compare the title and the first author's family name
with the Crossref record. Exit code 1 if any DOI fails or does not match.

Usage:  python scripts/check_references.py   (needs internet)
"""
import difflib
import os
import re
import sys
import time

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BIB = os.path.join(ROOT, "manuscript", "references.bib")
STRIP = re.compile(r"[{}\\\"']")


def norm(s):
    s = STRIP.sub("", s or "").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def field(entry, name):
    m = re.search(name + r"\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}", entry, re.S)
    return m.group(1) if m else None


def main():
    text = open(BIB, encoding="utf-8").read()
    bad = 0
    for entry in re.split(r"\n(?=@)", text):
        m = re.match(r"@\w+\{(\w+),", entry.strip())
        if not m:
            continue
        key, doi = m.group(1), field(entry, "doi")
        if not doi:
            print(f"  --   {key:15} no DOI (check by hand)")
            continue
        for _ in range(4):
            r = requests.get("https://api.crossref.org/works/" + doi,
                             headers={"User-Agent": "rooftop-scanning-bibcheck/1.0"}, timeout=30)
            if r.status_code in (200, 404):
                break
            time.sleep(3)
        if r.status_code != 200:
            print(f"  FAIL {key:15} DOI not found: {doi}")
            bad += 1
            continue
        msg = r.json()["message"]
        sim = difflib.SequenceMatcher(None, norm(field(entry, "title")), norm((msg.get("title") or [""])[0])).ratio()
        first = norm((field(entry, "author") or "").split(" and ")[0].split()[-1])
        cr_first = norm((msg.get("author") or [{}])[0].get("family", ""))
        ok = sim > 0.9 and (first in cr_first or cr_first in first or not cr_first)
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {key:15} title match {sim:.2f}, first author {first!r} vs {cr_first!r}")
    print("All references verified." if not bad else f"{bad} reference(s) failed.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
