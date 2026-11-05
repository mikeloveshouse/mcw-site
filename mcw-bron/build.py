#!/usr/bin/env python3
"""Bouwt ../mcw-site/ uit src/*.html en artikelen/*.md. Alleen lokaal, geen netwerk.

Gebruik:  python3 build.py          (concept: ../mcw-site/, noindex)
          python3 build.py --live   (../mcw-site-live/, indexeerbaar, robots.txt + sitemap.xml)
Pagina-bron: kopregels 'title:', 'description:', 'nav:' gevolgd door '---' en de HTML van <main>.
Artikel-bron: 'title:', 'slug:', 'summary:' gevolgd door '---', tekst (## kop, alinea's, **vet**,
[tekst](url)), en onderaan '---slot---' met de afsluitende alinea.
{R} = pad naar de siterwortel ('' of '../'). Niets in deze map wordt gepubliceerd.
"""
import html
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "mcw-site"
SITE = "Make Change Work"
EMAIL = "michael@makechangework.nl"
DOMAIN = "https://makechangework.nl"
LIVE = "--live" in sys.argv
if LIVE:
    OUT = HERE.parent / "mcw-site-live"

MARK = ('<svg class="mark" viewBox="0 0 110 66" width="44" height="26" aria-hidden="true" focusable="false">'
        '<g fill="none" stroke-linecap="round"><path d="M0 23 C22 3.5 37.5 9 54 34.5 C69 57.5 89 58 110 13" stroke="#E8742A" stroke-width="5.2"/>'
        '<path d="M0 36 C23.5 20.5 39 23.5 55 44.5 C70.5 64 90.5 61 110 28.5" stroke="#8FB4D9" stroke-width="2.8" opacity=".7"/></g></svg>')

NAV = [("diensten", "Diensten", "diensten.html"), ("artikelen", "Artikelen", "artikelen.html"),
       ("over", "Over", "over.html"), ("contact", "Contact", "contact.html")]

TEMPLATE = """<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#0F0D0C">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="website">
<meta property="og:locale" content="nl_NL">
<link rel="icon" href="{{R}}assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{{R}}assets/style.css">
<!-- TODO livegang: noindex weghalen op Michaels go; canonical-URL's, og:url en og:image, sitemap.xml toevoegen; schone URL's (zonder .html) regelen via hosting. -->
</head>
<body>
<a class="skip" href="#main">Naar de inhoud</a>
<header class="site-header">
<div class="wrap bar">
<a class="brand" href="{{R}}index.html">{mark}<span>Make Change Work</span></a>
<nav aria-label="Hoofdmenu">
<ul>
{nav}
<li><a class="btn btn-small" href="{{R}}contact.html#sparsessie">Plan een sparsessie</a></li>
</ul>
</nav>
</div>
</header>
<main id="main" tabindex="-1">
{body}
</main>
<footer class="site-footer">
<!-- TODO voettekst: btw-id ontbreekt in KvK-uittreksel (niet verzinnen; leveren of weglaten). Adres bewust niet getoond (uittreksel = waarschijnlijk privé; Michael beslist postadres of alleen Amsterdam). Voornaam in het KvK-uittreksel is afwijkend gespeld: officiele naam controleren. Algemene voorwaarden: link pas toevoegen als de pagina bestaat. Uittreksel is van 15-09-2025: bij livegang opnieuw controleren. Keurmerken/erkenningen alleen na Michaels bevestiging. -->
<div class="wrap">
<div class="foot-grid">
<div>
<p class="foot-name">Make Change Work</p>
<p>Advies op het gebied van management en bedrijfsvoering.</p>
</div>
<div>
<p>Make Change Work is een eenmanszaak. De eigenaar is Michael Spierenburg, persoonlijk verantwoordelijk voor de onderneming.</p>
<p>Ingeschreven bij de Kamer van Koophandel onder nummer 98203398 (vestigingsnummer 000063383829), gevestigd in Amsterdam.</p>
</div>
<div>
<p>Contact: <a href="mailto:{email}">{email}</a></p>
<p><a href="{{R}}privacy.html">Privacy</a></p>
</div>
</div>
<p class="copy">&copy; 2026 Make Change Work</p>
</div>
</footer>
</body>
</html>
"""


def parse(text):
    head, _, body = text.partition("\n---\n")
    meta = {}
    for line in head.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, body.strip("\n")


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', s)
    return s


def md_to_html(md):
    out, para = [], []

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    items = []

    def flush_list():
        if items:
            out.append("<ul>" + "".join("<li>" + inline(i) + "</li>" for i in items) + "</ul>")
            items.clear()

    for line in md.splitlines():
        if line.startswith("- "):
            flush()
            items.append(line[2:].strip())
            continue
        flush_list()
        if line.startswith("## "):
            flush()
            out.append("<h2>" + inline(line[3:]) + "</h2>")
        elif not line.strip():
            flush()
        else:
            para.append(line.strip())
    flush()
    flush_list()
    return "\n".join(out)


def clean(fname):
    """Schone URL zoals Cloudflare Pages ze serveert: zonder .html, index = wortel."""
    f = fname[:-5] if fname.endswith(".html") else fname
    return "" if f == "index" else f


def page(meta, body, root, nav_key, fname=""):
    nav = "\n".join(
        '<li><a href="{R}%s"%s>%s</a></li>' % (href, ' aria-current="page"' if key == nav_key else "", label)
        for key, label, href in NAV)
    title = meta["title"]
    out = TEMPLATE.format(title=html.escape(title), description=html.escape(meta["description"]),
                          mark=MARK, nav=nav, body=body, email=EMAIL)
    out = out.replace("{R}", root)
    if LIVE:
        out = re.sub(r"<!--.*?-->\n?", "", out, flags=re.S)  # interne TODO-notities niet publiceren
        out = out.replace('<meta name="robots" content="noindex, nofollow">\n', "")
        url = DOMAIN + "/" + clean(fname)
        out = out.replace('<meta property="og:type"', '<meta property="og:url" content="%s">\n<meta property="og:type"' % url, 1)
        out = out.replace('<link rel="icon"', '<link rel="canonical" href="%s">\n<link rel="icon"' % url, 1)
    return out


def main():
    arts = []
    for f in sorted((HERE / "artikelen").glob("*.md")):
        meta, rest = parse(f.read_text(encoding="utf-8"))
        main_md, _, slot = rest.partition("---slot---")
        arts.append({**meta, "main": main_md.strip(), "slot": slot.strip(), "todo": meta.get("todo", "")})

    cards = "\n".join(
        '<li class="card"><h2><a href="artikelen/%s.html">%s</a></h2><p>%s</p></li>'
        % (a["slug"], html.escape(a["title"]), html.escape(a["summary"])) for a in arts)
    teaser = ('<p class="eyebrow">Uit de artikelen</p><h2 id="teaser-kop">%s</h2><p>%s</p>'
              '<p><a class="more" href="artikelen/%s.html">Lees het artikel</a></p>'
              % (html.escape(arts[0]["title"]), html.escape(arts[0]["summary"]), arts[0]["slug"]))

    (OUT / "artikelen").mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.html"):
        old.unlink()
    for old in (OUT / "artikelen").glob("*.html"):
        old.unlink()

    for f in sorted((HERE / "src").glob("*.html")):
        meta, body = parse(f.read_text(encoding="utf-8"))
        body = body.replace("{{ARTIKELEN}}", cards).replace("{{TEASER}}", teaser)
        (OUT / f.name).write_text(page(meta, body, "", meta.get("nav", ""), f.name), encoding="utf-8")

    for a in arts:
        body = (
            '<article class="wrap prose article"%s>\n<p class="crumb"><a href="{R}artikelen.html">Artikelen</a></p>\n'
            "<h1>%s</h1>\n<p class=\"lead\">%s</p>\n<p class=\"byline\">Door Make Change Work%s</p>\n"
            "<!-- TODO artikel: %s -->\n%s\n"
            '<aside class="callout" aria-labelledby="slot-kop"><h2 id="slot-kop">Sparren over jouw situatie</h2>\n<p>%s</p>\n'
            '<p><a class="btn" href="{R}contact.html#sparsessie">Plan een gratis sparsessie</a></p></aside>\n</article>'
            % (" data-letterlijk" if a.get("letterlijk") else "", html.escape(a["title"]), html.escape(a["summary"]),
               (" &middot; " + html.escape(a["datum"])) if a.get("datum") else "", a["todo"], md_to_html(a["main"]), inline(a["slot"])))
        meta = {"title": a["title"] + " | " + SITE, "description": a["summary"]}
        (OUT / "artikelen" / (a["slug"] + ".html")).write_text(page(meta, body, "../", "artikelen", "artikelen/" + a["slug"] + ".html"), encoding="utf-8")
    if LIVE:
        (OUT / "assets").mkdir(exist_ok=True)
        for asset in (HERE.parent / "mcw-site" / "assets").iterdir():
            shutil.copy2(asset, OUT / "assets" / asset.name)
        urls = [DOMAIN + "/" + clean(p.name) for p in sorted(OUT.glob("*.html"))]
        urls += [DOMAIN + "/artikelen/" + a["slug"] for a in arts]
        (OUT / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join("<url><loc>%s</loc></url>\n" % u for u in urls) + "</urlset>\n", encoding="utf-8")
        (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % DOMAIN, encoding="utf-8")
    print("gebouwd:", len(list(OUT.glob('*.html'))), "pagina's +", len(arts), "artikelen")


if __name__ == "__main__":
    main()
