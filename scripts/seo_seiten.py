#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seo_seiten.py, haelt die technischen SEO-Teile aller Seiten gleich (Ben, 06.10.2026, SEO-Ausbau Block D).

Was es auf jeder oeffentlichen Seite schreibt, jeweils zwischen eigenen Marken,
damit ein zweiter Lauf nichts aendert:

  <!--AUTO:seo-kopf-->      im <head>: canonical, Open Graph, Twitter Card und ein
                            WebPage-Schema mit dateModified. Titel und Beschreibung
                            kommen aus <title> und <meta name="description"> der
                            Seite, es gibt sie also nur an einer Stelle.
  <!--AUTO:seitenstand-->   erste Zeile im <footer>, sichtbar: "page last updated ...".
  <div class="nc">          die statische Navigation, in derselben Reihenfolge wie
                            MENUE in capture.js. capture.js baut daraus im Browser
                            das Aufklappmenue, Suchmaschinen lesen die Liste direkt.
  sitemap.xml               lastmod je Seite.

WANN EINE SEITE ALS GEAENDERT GILT
  Datum ist der Tag, an dem sich der sichtbare Inhalt zuletzt geaendert hat.
  Gemessen wird ein Hash ueber den Text des <body> ohne Navigation, ohne
  Skripte, ohne die Zeile "how we fund this" und ohne die Stand-Zeile selbst.
  Ein neuer Menuepunkt oder ein neuer Titel macht eine Seite also nicht
  "neu", ein neuer Absatz oder eine neue Zahl schon. Hash und Datum stehen in
  data/seiten-stand.json. Der erste Stand kam mit --init aus der Git-Historie,
  je Seite der letzte Commit, der diesen Text geaendert hat.

Seiten mit <meta name="robots" content="noindex..."> bekommen nur den Kopf,
keine Stand-Zeile und keinen Sitemap-Eintrag. utm-test.html (noindex,
nofollow, ohne Navigation) bleibt ganz unberuehrt.

    python3 scripts/seo_seiten.py              schreiben
    python3 scripts/seo_seiten.py --pruefen    nur pruefen, Exit 1 wenn etwas abweicht
    python3 scripts/seo_seiten.py --init       Datum je Seite aus der Git-Historie
    python3 scripts/seo_seiten.py --selbsttest
"""
import datetime as dt
import hashlib
import html as htmlmod
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASIS = "https://kaspapulse.com/"
BILD = BASIS + "og-card.png"
STAND = "data/seiten-stand.json"
AUSGENOMMEN = {"utm-test.html"}
MONATE = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def datum_text(iso):
    d = dt.date.fromisoformat(iso)
    return "%d %s %d" % (d.day, MONATE[d.month - 1], d.year)


def url(datei):
    return BASIS if datei == "index.html" else BASIS + datei


def seiten():
    return sorted(p.name for p in REPO.glob("*.html") if p.name not in AUSGENOMMEN)


def noindex(s):
    return bool(re.search(r'<meta name="robots" content="[^"]*noindex', s))


# ---------------------------------------------------------------- menue

def menue(js=None):
    """Liest MENUE aus capture.js, flach in Reihenfolge, als (text, pfad)."""
    js = js if js is not None else (REPO / "capture.js").read_text(encoding="utf-8")
    block = js[js.index("var MENUE = ["):]
    block = block[:block.index("];")]
    aus = []
    for m in re.finditer(r'\{ t: "([^"]+)", h: "([^"]+)" \}|\["([^"]+)", "([^"]+)"\]', block):
        aus.append((m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4)))
    return aus


def nav(s, datei, punkte):
    hier = "/" if datei == "index.html" else "/" + datei
    m = re.search(r'(?s)(<nav class="nav">.*?<div class="nc">\n)(.*?)(\s*</div>\n</nav>)', s)
    if not m:
        return s
    zeilen = ['    <a href="%s"%s>%s</a>' % (h, ' class="on"' if h == hier else "", htmlmod.escape(t))
              for t, h in punkte]
    return s[:m.start(2)] + "\n".join(zeilen) + s[m.end(2):]


# ---------------------------------------------------------------- kopf

def titel(s):
    m = re.search(r"(?s)<title>(.*?)</title>", s)
    return htmlmod.unescape(" ".join(m.group(1).split())) if m else ""


def beschreibung(s):
    m = re.search(r'<meta name="description" content="([^"]*)"', s)
    return htmlmod.unescape(m.group(1)) if m else ""


def attr(x):
    return htmlmod.escape(x, quote=True)


def kopf_block(s, datei, iso):
    t, d, u = titel(s), beschreibung(s), url(datei)
    z = ['<link rel="canonical" href="%s">' % u]
    if not noindex(s):
        z += ['<meta property="og:type" content="website">',
              '<meta property="og:site_name" content="Kaspa Pulse">',
              '<meta property="og:title" content="%s">' % attr(t),
              '<meta property="og:description" content="%s">' % attr(d),
              '<meta property="og:url" content="%s">' % u,
              '<meta property="og:image" content="%s">' % BILD,
              '<meta property="og:image:width" content="1200">',
              '<meta property="og:image:height" content="630">',
              '<meta property="og:image:alt" content="Kaspa Pulse, on-chain numbers for Kaspa">',
              '<meta name="twitter:card" content="summary_large_image">',
              '<meta name="twitter:title" content="%s">' % attr(t),
              '<meta name="twitter:description" content="%s">' % attr(d),
              '<meta name="twitter:image" content="%s">' % BILD]
        if iso:
            ld = {"@context": "https://schema.org", "@type": "WebPage", "name": t, "description": d, "url": u,
                  "inLanguage": "en", "dateModified": iso,
                  "isPartOf": {"@type": "WebSite", "name": "Kaspa Pulse", "url": BASIS},
                  "publisher": {"@type": "Organization", "name": "Kaspa Pulse", "url": BASIS}}
            js = json.dumps(ld, ensure_ascii=False, indent=1).replace("</", "<\\/")
            z.append('<script type="application/ld+json">\n%s\n</script>' % js)
    return "<!--AUTO:seo-kopf-->\n%s\n<!--/AUTO:seo-kopf-->" % "\n".join(z)


KOPF = re.compile(r"(?s)<!--AUTO:seo-kopf-->.*?<!--/AUTO:seo-kopf-->")


def kopf(s, datei, iso):
    neu = kopf_block(s, datei, iso)
    if KOPF.search(s):
        return KOPF.sub(lambda _m: neu, s, count=1)
    s = re.sub(r'<link rel="canonical" href="[^"]*">\n', "", s)
    anker = '<link rel="icon"'
    if anker not in s:
        raise SystemExit("%s, kein <link rel=\"icon\"> als anker fuer den kopf" % datei)
    return s.replace(anker, neu + "\n" + anker, 1)


# ---------------------------------------------------------------- stand

FUSS = re.compile(r"(?s)<!--AUTO:seitenstand-->.*?<!--/AUTO:seitenstand-->")


def fuss(s, iso):
    zeile = "<!--AUTO:seitenstand-->page last updated %s<!--/AUTO:seitenstand-->" % datum_text(iso)
    if FUSS.search(s):
        return FUSS.sub(lambda _m: zeile, s, count=1)
    if "  <footer>\n" not in s:
        raise SystemExit("kein <footer> fuer die stand-zeile")
    return s.replace("  <footer>\n", '  <footer>\n    <div class="stand">%s</div>\n' % zeile, 1)


def inhalt_hash(s):
    b = s[s.find("<body"):] if "<body" in s else s
    b = re.sub(r"(?s)<nav\b.*?</nav>", " ", b)
    b = re.sub(r"(?s)<(script|style|noscript|template)\b.*?</\1>", " ", b)
    b = re.sub(r'(?s)<div class="fund"[^>]*>.*?</div>', " ", b)
    b = FUSS.sub(" ", b)
    b = re.sub(r"(?s)<!--.*?-->", " ", b)
    b = re.sub(r"(?s)<[^>]+>", " ", b)
    t = " ".join(htmlmod.unescape(b).split())
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16]


def stand_laden():
    try:
        return json.loads((REPO / STAND).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def stand_text(st):
    return json.dumps(st, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def stand_neu(st, datei, h, heute):
    alt = st.get(datei)
    if alt and alt.get("hash") == h:
        return alt["datum"]
    st[datei] = {"datum": heute, "hash": h}
    return heute


# ---------------------------------------------------------------- sitemap

def sitemap(xml, daten):
    def ein(m):
        loc = m.group(1)
        datei = "index.html" if loc == BASIS else loc[len(BASIS):]
        iso = daten.get(datei)
        return m.group(0) if not iso else m.group(0)[:m.start(2) - m.start(0)] + iso + m.group(0)[m.end(2) - m.start(0):]
    return re.sub(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", ein, xml)


def sitemap_luecken(xml, oeffentlich):
    drin = set(re.findall(r"<loc>([^<]+)</loc>", xml))
    soll = {url(d) for d in oeffentlich}
    return sorted(soll - drin), sorted(drin - soll)


# ---------------------------------------------------------------- lauf

def git_datum(datei):
    """Datum des letzten Commits, der den sichtbaren Text der Seite geaendert hat."""
    log = subprocess.run(["git", "log", "--format=%H %cs", "--", datei], cwd=REPO, capture_output=True,
                         text=True, check=True).stdout.split("\n")
    vorher_hash, vorher_datum = None, None
    for zeile in log:
        if not zeile.strip():
            continue
        sha, datum = zeile.split()
        inhalt = subprocess.run(["git", "show", "%s:%s" % (sha, datei)], cwd=REPO, capture_output=True,
                                text=True).stdout
        h = inhalt_hash(inhalt)
        if vorher_hash is not None and h != vorher_hash:
            return vorher_datum
        vorher_hash, vorher_datum = h, datum
    return vorher_datum


def lauf(schreiben=True, heute=None, init=False):
    heute = heute or dt.datetime.now(dt.timezone.utc).date().isoformat()
    punkte = menue()
    st = stand_laden()
    abweichung, daten = [], {}
    for datei in seiten():
        p = REPO / datei
        s = p.read_text(encoding="utf-8")
        oeffentlich = not noindex(s)
        iso = None
        if oeffentlich:
            h = inhalt_hash(s)
            if init and datei not in st:
                st[datei] = {"datum": git_datum(datei) or heute, "hash": h}
            iso = stand_neu(st, datei, h, heute)
            daten[datei] = iso
        n = nav(s, datei, punkte)
        n = kopf(n, datei, iso)
        if oeffentlich:
            n = fuss(n, iso)
        if n != s:
            abweichung.append(datei)
            if schreiben:
                p.write_text(n, encoding="utf-8")
    sp = REPO / "sitemap.xml"
    xml = sp.read_text(encoding="utf-8")
    fehlt, zuviel = sitemap_luecken(xml, daten)
    for x in fehlt:
        print("sitemap.xml, es fehlt %s" % x)
    for x in zuviel:
        print("sitemap.xml, steht drin, ist aber keine oeffentliche seite: %s" % x)
    nx = sitemap(xml, daten)
    if nx != xml:
        abweichung.append("sitemap.xml")
        if schreiben:
            sp.write_text(nx, encoding="utf-8")
    alt_st = (REPO / STAND).read_text(encoding="utf-8") if (REPO / STAND).exists() else ""
    if stand_text(st) != alt_st:
        abweichung.append(STAND)
        if schreiben:
            (REPO / STAND).write_text(stand_text(st), encoding="utf-8")
    return abweichung, bool(fehlt or zuviel)


def selbsttest():
    f = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            f.append(name)

    js = ('var MENUE = [\n { t: "dashboard", h: "/" },\n { t: "tools", k: [\n  ["wallets", "/kaspa-wallets.html"],\n'
          '  ["web wallet safety", "/kaspa-web-wallet-safe.html"]\n ]}\n];')
    m = menue(js)
    ok("menue aus capture.js, flach", m == [("dashboard", "/"), ("wallets", "/kaspa-wallets.html"),
                                            ("web wallet safety", "/kaspa-web-wallet-safe.html")])
    seite = ('<html><head><title>Kaspa\'s "Test" Page</title>\n<meta name="description" content="A &amp; B.">\n'
             '<link rel="canonical" href="https://kaspapulse.com/x.html">\n<link rel="icon" href="f.png">\n</head>\n'
             '<body>\n<nav class="nav">\n  <div class="nt"></div>\n    <div class="nc">\n    <a href="/">alt</a>\n'
             '  </div>\n</nav>\n<p>Inhalt</p>\n  <footer>\n    <div class="fund"><a href="/h">how we fund this</a></div>\n'
             '  </footer>\n</body></html>')
    n = nav(seite, "kaspa-wallets.html", m)
    ok("nav neu, aktuelle seite markiert", '<a href="/kaspa-wallets.html" class="on">wallets</a>' in n
       and "alt</a>" not in n and n.count("<a href=") == seite.count("<a href=") + 2)
    k = kopf(n, "x.html", "2026-10-06")
    ok("kopf ersetzt das alte canonical", k.count('rel="canonical"') == 1
       and k.index("<!--AUTO:seo-kopf-->") < k.index('<link rel="icon"'))
    ok("titel im attribut maskiert", 'content="Kaspa&#x27;s &quot;Test&quot; Page"' in k)
    ok("beschreibung nicht doppelt maskiert", 'og:description" content="A &amp; B."' in k)
    ok("schema mit dateModified", '"dateModified": "2026-10-06"' in k)
    ok("kopf wiederholbar", kopf(k, "x.html", "2026-10-06") == k)
    ok("index hat die wurzel als url", 'href="https://kaspapulse.com/">' in kopf(n, "index.html", "2026-10-06"))
    ni = k.replace("<head>", '<head><meta name="robots" content="noindex">')
    ok("noindex, nur canonical", "og:title" not in kopf(ni, "x.html", None) and 'rel="canonical"' in kopf(ni, "x.html", None))
    g = fuss(k, "2026-10-06")
    ok("stand-zeile im footer", '<div class="stand"><!--AUTO:seitenstand-->page last updated 6 October 2026' in g)
    ok("stand-zeile wiederholbar", fuss(fuss(g, "2026-10-07"), "2026-10-07").count("seitenstand-->page") == 1)
    ok("hash ohne nav, fund, stand", inhalt_hash(seite) == inhalt_hash(g) == inhalt_hash(fuss(g, "2026-10-07")))
    ok("hash sieht neuen text", inhalt_hash(seite) != inhalt_hash(seite.replace("Inhalt", "Inhalt neu")))
    st = {"a.html": {"datum": "2026-08-01", "hash": "h1"}}
    ok("gleicher hash, altes datum", stand_neu(st, "a.html", "h1", "2026-10-06") == "2026-08-01")
    ok("neuer hash, heutiges datum", stand_neu(st, "a.html", "h2", "2026-10-06") == "2026-10-06"
       and st["a.html"]["hash"] == "h2")
    xml = ("<url>\n<loc>https://kaspapulse.com/</loc>\n<lastmod>2026-08-17</lastmod>\n</url>\n"
           "<url>\n<loc>https://kaspapulse.com/a.html</loc>\n<lastmod>2026-08-06</lastmod>\n</url>")
    nx = sitemap(xml, {"index.html": "2026-10-05", "a.html": "2026-10-06"})
    ok("sitemap lastmod", "<lastmod>2026-10-05</lastmod>" in nx and "<lastmod>2026-10-06</lastmod>" in nx)
    ok("sitemap luecken", sitemap_luecken(xml, ["index.html", "b.html"]) ==
       (["https://kaspapulse.com/b.html"], ["https://kaspapulse.com/a.html"]))
    ok("schema ohne </ im json", "<\\/" in kopf_block(n.replace("A &amp; B.", "x</script>y"), "x.html", "2026-10-06"))
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--selbsttest"]:
        return selbsttest()
    pruefen = "--pruefen" in argv
    abw, luecke = lauf(schreiben=not pruefen, init="--init" in argv)
    for a in abw:
        print("%s %s" % ("weicht ab," if pruefen else "neu,", a))
    if not abw:
        print("alles auf stand")
    return 1 if (pruefen and abw) or luecke else 0


if __name__ == "__main__":
    sys.exit(main())
