#!/usr/bin/env python3
"""Lint voor ../mcw-site/. Alleen lezen, geen netwerk. Exitcode 1 bij een fout.

Controleert: precies een h1, noindex, lang, skip-link, dubbele id's, interne links en ankers
(ook tussen pagina's), lokale assets, een enkel e-mailadres, verboden woorden (uit een bestand
buiten de publicatiemap), ik-vorm (ik/mij/mijn; wij-vorm is sinds 4-11-2026 toegestaan), 'Michel', percentages, klantnamen, AI-woorden.
Gebruik: python3 lint.py [--live] [pad-naar-verboden-woorden.txt]
--live controleert ../mcw-site-live/: dan moet noindex juist ontbreken, en moeten canonical, robots.txt en sitemap.xml kloppen.
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urlparse

LIVE = "--live" in sys.argv
ARGS = [a for a in sys.argv[1:] if a != "--live"]
SITE = Path(__file__).resolve().parent.parent / ("mcw-site-live" if LIVE else "mcw-site")
BANNED = Path(ARGS[0]) if ARGS else SITE.parent / "verboden-woorden.txt"
CLIENTS = ["ING", "Mediahuis", "ABN", "Rabobank", "Inholland", "UMC", "Elsevier", "Wageningen", "Energyst", "HMS", "NS"]
AI = ["ChatGPT", "Claude", "Copilot", "kunstmatige intelligentie", "artificial intelligence", "AI-gegenereerd", "generatieve"]


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.hrefs, self.assets, self.h1, self.noindex = [], [], [], 0, False
        self.lang = self.skip = self.title = False
        self.text, self._skip_text = [], 0
        self.heads = []
        self.canon = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a: self.ids.append(a["id"])
        if tag == "h1": self.h1 += 1
        if tag in "h1 h2 h3": self.heads.append(tag)
        if tag == "html" and a.get("lang") == "nl": self.lang = True
        if tag == "a" and "href" in a:
            self.hrefs.append(a["href"])
            if a["href"] == "#main" and a.get("class") == "skip": self.skip = True
        if tag == "link" and a.get("rel") == "canonical": self.canon = a.get("href")
        elif tag == "link" and a.get("href"): self.assets.append(a["href"])
        if tag in ("script",) : self.assets.append(a.get("src", "<inline-script>"))
        if tag == "img" and "alt" not in a: self.assets.append("<img zonder alt>")
        if tag == "meta" and a.get("name") == "robots" and "noindex" in a.get("content", ""): self.noindex = True
        if tag == "title": self.title = True
        if tag in ("script", "style"): self._skip_text += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"): self._skip_text -= 1

    def handle_data(self, d):
        if not self._skip_text: self.text.append(d)


def main():
    errors, pages = [], {}
    files = sorted(SITE.rglob("*.html"))
    raw_all = {}
    for f in files:
        raw = f.read_text(encoding="utf-8")
        raw_all[f] = raw
        p = P(); p.feed(raw); pages[f] = p
    banned = [w.strip() for w in BANNED.read_text(encoding="utf-8").splitlines() if w.strip()] if BANNED.exists() else []
    if not banned: errors.append("verboden-woordenlijst ontbreekt of is leeg: %s" % BANNED)
    emails = set()
    for f, p in pages.items():
        n = f.relative_to(SITE).as_posix()
        raw = raw_all[f]
        e = lambda m: errors.append("%s: %s" % (n, m))
        if p.h1 != 1: e("h1-aantal %d" % p.h1)
        if LIVE:
            if p.noindex: e("noindex staat nog aan")
            if not (p.canon or "").startswith("https://makechangework.nl"): e("canonical ontbreekt of fout")
            if "<!--" in raw: e("HTML-commentaar in live-bestand")
        elif not p.noindex: e("noindex ontbreekt")
        if not p.lang: e("lang=nl ontbreekt")
        if not p.skip: e("skip-link ontbreekt")
        if len(p.ids) != len(set(p.ids)): e("dubbele id")
        # kopvolgorde: geen sprong van h1 naar h3
        prev = 0
        for h in p.heads:
            lvl = int(h[1])
            if lvl > prev + 1: e("kopniveau springt naar %s" % h)
            prev = lvl
        for href in p.hrefs:
            if href.startswith("mailto:"):
                emails.add(href[7:].split("?")[0]); continue
            u = urlparse(href)
            if u.scheme in ("http", "https"):
                e("externe link %s" % href); continue
            path, frag = urldefrag(href)
            target = f if not path else (f.parent / path).resolve()
            if not target.is_file(): e("link naar ontbrekend bestand %s" % href); continue
            if frag:
                tp = pages.get(target) or pages.get(Path(target))
                if not tp or frag not in tp.ids: e("anker ontbreekt %s" % href)
        for a in p.assets:
            if a.startswith("<") or a.startswith("http"): e("asset niet toegestaan: %s" % a); continue
            if not (f.parent / a).resolve().is_file(): e("asset ontbreekt %s" % a)
        text = " ".join(p.text)
        verbatim = "data-letterlijk" in raw  # woordelijk overgenomen artikel: persoons-/klantnamen, wij-vorm en percentage mogen
        for w in banned:
            if re.search(re.escape(w), raw, re.I): e("verboden term in bron/tekst: %s" % ("*" * len(w)))
        for m in ([] if verbatim else re.finditer(r"\b(ik|mij|mijn|mezelf)\b", text, re.I)):
            e("ik-vorm (besluit Michael 4-11-2026: wij-vorm): %r" % text[max(0, m.start()-20):m.end()+20])
        if re.search(r"\bMichel\b", raw): e("'Michel' gevonden")
        if not verbatim and "%" in re.sub(r"%20", "", text): e("procentteken in tekst")
        for c in ([] if verbatim else CLIENTS):
            # alleen de kaart/titel van het woordelijk overgenomen artikel mag de klantnaam dragen
            if re.search(r"\b%s\b" % re.escape(c), re.sub(r'<li class="card"><h2><a href="artikelen/teamcoaching-hoge-school\.html">.*?</li>', "", raw)): e("klantnaam %s" % c)
        for w in AI:
            if re.search(re.escape(w), raw, re.I): e("AI-woord %s" % w)
        if not re.search(r"<title>.+</title>", raw): e("title ontbreekt")
    if emails != {"michael@makechangework.nl"}: errors.append("e-mailadressen: %s" % sorted(emails))
    # btw/adres niet getoond
    for f, raw in raw_all.items():
        body = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
        if re.search(r"btw|NL\d{9}B\d\d", body, re.I): errors.append("%s: btw-regel zichtbaar" % f.name)
    if LIVE:
        rb = SITE / "robots.txt"; sm = SITE / "sitemap.xml"
        if not rb.is_file() or "Disallow: /" in rb.read_text().replace("Disallow: /\n", "Disallow: /\n") and re.search(r"Disallow:\s*/\s*$", rb.read_text(), re.M):
            errors.append("robots.txt ontbreekt of blokkeert alles")
        if not sm.is_file(): errors.append("sitemap.xml ontbreekt")
        else:
            locs = re.findall(r"<loc>(.+?)</loc>", sm.read_text())
            if len(locs) != len(files): errors.append("sitemap heeft %d urls, site %d pagina's" % (len(locs), len(files)))
    print("pagina's: %d" % len(files))
    for x in errors: print("FOUT:", x)
    print("OK" if not errors else "%d fout(en)" % len(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
