"""Static checks on manuscript/main.tex: reproducibility rules and IEEE author guidance.

Reproducibility
  1. Every number macro used in the text is defined in generated/numbers.tex.
  2. No result typed by hand in the prose (decimals such as 12.3 or numbers such as 1,234).
IEEE author guidance (conference template and Author Center)
  3. Every acronym is defined at its first use in the body: "Long Form (ACR)".
  4. "data" is plural; American spelling; lowercase "dc"/"ac"; no em dashes.
  5. Index terms in alphabetical order.
  6. No undefined abbreviations in section headings.

Usage:  python scripts/check_manuscript.py
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEX = os.path.join(ROOT, "manuscript", "main.tex")
NUMS = os.path.join(ROOT, "manuscript", "generated", "numbers.tex")
BUILTIN = {"IEEEauthorblockN", "IEEEauthorblockA", "IEEEkeywords", "Big"}

# Acronyms that must be spelled out at first use in the body (IEEE: even if defined in the abstract).
ACRONYMS = ["PV", "UAE", "LiDAR", "OSM", "PVGIS", "GIS", "NPV", "LCOE", "AED", "MAPE", "MBE"]
# Allowed in headings without definition (IEEE lists dc, ac, SI, IEEE; Q1-Q3 are defined in the text).
HEADING_OK = {"OSM", "Q1", "Q2", "Q3", "W5"}
BRITISH = ["metre", "centre", "modelled", "modelling", "labelled", "colour", "analyse", "behaviour",
           "organis", "grey", "favour", "licence", "travelled"]


def strip_comments(tex):
    return "\n".join(re.split(r"(?<!\\)%", line)[0] for line in tex.splitlines())


def main():
    tex = open(TEX, encoding="utf-8").read()
    body_all = strip_comments(tex)
    errors = []

    # 1-2 reproducibility
    defined = set(re.findall(r"\\newcommand\{\\(\w+)\}", open(NUMS, encoding="utf-8").read()))
    used = set(re.findall(r"(?<!\\)\\([A-Z][A-Za-z]+)", body_all)) - BUILTIN
    errors += [f"undefined number macro \\{m}" for m in sorted(used - defined)]
    prose = re.sub(r"\$[^$]*\$|\\begin\{(equation|table|tabular|figure)\*?\}.*?\\end\{\1\*?\}", "", body_all, flags=re.S)
    errors += [f"hand-typed number in prose: {h}" for h in
               re.findall(r"(?<![\w\\{])\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w\\{.])\d+\.\d{2,}", prose)]

    # 3 acronyms defined at first use in the body (after the keywords)
    body = body_all.split(r"\end{IEEEkeywords}", 1)[-1]
    body_text = re.sub(r"\\(cite|ref|label|eqref|includegraphics|input|url)\{[^}]*\}", "", body)
    for ac in ACRONYMS:
        m = re.search(rf"(?<![\w-]){re.escape(ac)}(?![\w-])", body_text)
        if m and not body_text[max(0, m.start() - 1):m.end() + 1] == f"({ac})":
            errors.append(f"acronym {ac} used before it is defined as '(…) ({ac})'")

    # 4 language
    for pat, msg in [(r"\bdata (is|was|has)\b", "'data' is plural"), (r"\b(DC|AC)\b", "use lowercase dc/ac"),
                     ("\u2014", "em dash")]:
        for hit in re.findall(pat, prose):
            errors.append(f"{msg}: {hit if isinstance(hit, str) else hit[0]}")
    names_removed = re.sub(r"Research Centre|City Centre", "", prose)  # official names keep their spelling
    for w in BRITISH:
        if re.search(rf"\b{w}", names_removed, re.I):
            errors.append(f"British spelling: {w}")

    # 5 index terms alphabetical
    kw = re.search(r"\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}", body_all, re.S)
    if kw:
        terms = [t.strip() for t in kw.group(1).replace("\n", " ").split(",") if t.strip()]
        if terms != sorted(terms, key=str.lower):
            errors.append(f"index terms not in alphabetical order: {terms}")

    # 6 headings
    for h in re.findall(r"\\(?:sub)*section\*?\{([^}]*)\}", body_all):
        for ab in re.findall(r"\b[A-Z]{2,}[0-9]*\b|\b[A-Z][a-z]*[A-Z]\w*\b", h):
            if ab not in HEADING_OK:
                errors.append(f"abbreviation in heading '{h}': {ab}")

    print(f"{len(used & defined)} number macros used. {len(ACRONYMS)} acronyms checked.")
    for e in errors:
        print("  FAIL", e)
    print("Manuscript checks passed." if not errors else f"{len(errors)} problem(s).")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
