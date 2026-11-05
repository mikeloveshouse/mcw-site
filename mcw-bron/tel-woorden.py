#!/usr/bin/env python3
"""Telt woorden van een artikelconcept: titel, samenvatting, body, slot (zoals Michael telt) en alleen body.
Gebruik: python3 tel-woorden.py <bestand.md>   Verwacht een scheidingslijn (---) na de kopregels en **Titel:**/**Samenvatting:**/**Slot:**.
Controleert ook op procentteken, ik-vorm (wij-vorm mag sinds 4-11-2026), AI-merknamen, adressen en links (zie lint.py). Alleen lezen."""
import re, sys
t = open(sys.argv[1], encoding="utf-8").read()
a = t.split("\n---\n", 1)[1] if "\n---\n" in t else t
g = lambda k: re.search(r"\*\*%s:\*\*(.*)" % k, a).group(1)
title, summ, slot = g("Titel"), g("Samenvatting"), g("Slot")
body = a.split(summ, 1)[1].split("**Slot:**")[0]
w = lambda s: len(re.findall(r"\S+", re.sub(r"^#+ |^\d\. ", "", s, flags=re.M)))
tot = w(title) + w(summ) + w(body) + w(slot)
print("titel", w(title), "samenvatting", w(summ), "body", w(body), "slot", w(slot), "totaal", tot)
# per sectie (2-11): intro + woorden per ### of ## kop, en proza zonder koppen (moet ook >= 600 zijn)
parts = re.split(r"^#{2,3} .*$", body, flags=re.M); heads = re.findall(r"^#{2,3} .*$", body, flags=re.M)
print("intro", w(parts[0]), "| per kop:", ", ".join("%d" % w(x) for x in parts[1:]), "| proza zonder koppen", w(re.sub(r"^#{2,3} .*$", "", body, flags=re.M)))
for pat in [r"%", r"\b(ik|mij|mijn|mezelf)\b", r"Claude|Copilot|ChatGPT|kunstmatige intelligentie|generatieve", r"@", r"http"]:
    print("AANWEZIG" if re.search(pat, re.split(r"\*\*Controleren|## Controleren", a)[0], re.I) else "ok", pat)  # blok Controleren (agent-stem) telt niet mee
