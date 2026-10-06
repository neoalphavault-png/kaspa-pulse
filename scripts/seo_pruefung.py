#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seo_pruefung.py, Pruefung vor jedem Merge der SEO-Bloecke (Ben, 06.10.2026, Block E).

Liest jede oeffentliche Seite im Stand und, wenn --gegen gesetzt ist, denselben
Stand auf einem anderen Ref (meist origin/main), und gibt aus:

  1. eine Tabelle Seite | title alt -> neu | description alt -> neu | Laenge
  2. Pruefung der JSON-LD-Bloecke: gueltiges JSON, FAQPage mit Fragen und
     Antworten, jede Frage auch sichtbar im Seitentext
  3. Affiliate-Regeln:
       - ein Link mit rel="sponsored" ausserhalb eines <template> gilt als live
       - live nur auf kaspa-wallets.html erlaubt
       - solange keiner live ist, stehen dort "0 affiliate links on this page"
         und "This page earns nothing from your choice", und
         how-we-fund-this.html sagt "no affiliate links are live yet"
       - ist einer live, stehen beide Saetze nicht mehr da, dafuer der
         Hinweis "Some hardware links are affiliate links..." mit Link auf
         how-we-fund-this.html
  4. das fo-verify-Tag in index.html ist unveraendert da
  5. fuer Seiten, deren title oder description sich aendert: title hoechstens
     60 Zeichen, description 140 bis 155 Zeichen, kein Doppelpunkt, kein
     Gedankenstrich (Bens Regel fuer Veroeffentlichtes)

    python3 scripts/seo_pruefung.py --gegen origin/main            # tabelle + pruefung
    python3 scripts/seo_pruefung.py --gegen origin/main --markdown # fuer den PR
    python3 scripts/seo_pruefung.py --selbsttest

Exit 1, sobald eine Regel verletzt ist. Warnungen (z. B. lange Titel auf
unveraenderten Seiten) brechen nicht ab.
"""
import argparse
import html as htmlmod
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NICHT_OEFFENTLICH = {"utm-test.html"}
WALLETS = "kaspa-wallets.html"
FUND = "how-we-fund-this.html"
SATZ_NULL = "0 affiliate links on this page"
SATZ_NICHTS = "This page earns nothing from your choice"
SATZ_HINWEIS = "Some hardware links are affiliate links. They never change the order or what we write."
SATZ_NOCH_KEINER = "no affiliate links are live yet"
FO_TAG = '<meta name="fo-verify" content="947fd0e6-86c3-42e7-89d7-0ad0609e2b50" />'
TITEL_MAX = 60
BESCHR_MIN, BESCHR_MAX = 140, 155


def lies(pfad, ref=None):
    if ref is None:
        p = REPO / pfad
        return p.read_text(encoding="utf-8") if p.exists() else None
    r = subprocess.run(["git", "show", "%s:%s" % (ref, pfad)], cwd=REPO, capture_output=True)
    return r.stdout.decode("utf-8") if r.returncode == 0 else None


def seiten():
    return sorted(p.name for p in REPO.glob("*.html") if p.name not in NICHT_OEFFENTLICH)


def titel(s):
    m = re.search(r"(?is)<title>(.*?)</title>", s or "")
    return htmlmod.unescape(" ".join(m.group(1).split())) if m else ""


def beschreibung(s):
    m = re.search(r'(?is)<meta\s+name="description"\s+content="([^"]*)"', s or "")
    return htmlmod.unescape(m.group(1)) if m else ""


def ohne_templates(s):
    return re.sub(r"(?is)<template\b.*?</template>", " ", s or "")


def sichtbarer_text(s):
    t = ohne_templates(s)
    t = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return " ".join(htmlmod.unescape(t).split())


def live_affiliate(s):
    """Links mit rel="sponsored" und href, ausserhalb von <template>."""
    aus = []
    for m in re.finditer(r"(?is)<a\b([^>]*)>", ohne_templates(s)):
        attr = m.group(1)
        rel = re.search(r'rel="([^"]*)"', attr)
        href = re.search(r'href="([^"]+)"', attr)
        if rel and "sponsored" in rel.group(1).split() and href:
            aus.append(href.group(1))
    return aus


def jsonld(s):
    bloecke = re.findall(r'(?is)<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', ohne_templates(s))
    aus = []
    for b in bloecke:
        try:
            aus.append((json.loads(b), None))
        except ValueError as exc:
            aus.append((None, str(exc)))
    return aus


def pruefe_schema(name, s):
    fehler = []
    text = sichtbarer_text(s).lower()
    for daten, err in jsonld(s):
        if err:
            fehler.append("%s, json-ld kein gueltiges json (%s)" % (name, err))
            continue
        for obj in (daten if isinstance(daten, list) else [daten]):
            typ = obj.get("@type") if isinstance(obj, dict) else None
            if typ == "FAQPage":
                fragen = obj.get("mainEntity") or []
                if not fragen:
                    fehler.append("%s, FAQPage ohne mainEntity" % name)
                for q in fragen:
                    frage = (q.get("name") or "").strip()
                    antwort = ((q.get("acceptedAnswer") or {}).get("text") or "").strip()
                    if q.get("@type") != "Question" or not frage or not antwort:
                        fehler.append("%s, FAQ-Eintrag unvollstaendig: %r" % (name, frage[:60]))
                    elif frage.lower() not in text:
                        fehler.append("%s, FAQ-Frage nicht sichtbar auf der Seite: %r" % (name, frage[:60]))
    return fehler


def pruefe_affiliate(texte):
    fehler = []
    live = {n: live_affiliate(s) for n, s in texte.items()}
    for n, links in live.items():
        if links and n != WALLETS:
            fehler.append("%s, affiliate-link ausserhalb von %s: %s" % (n, WALLETS, links[:3]))
    w = texte.get(WALLETS) or ""
    wt = sichtbarer_text(w)
    if live.get(WALLETS):
        for satz in (SATZ_NULL, SATZ_NICHTS):
            if satz in wt:
                fehler.append("%s, affiliate-link live, aber noch da: %r" % (WALLETS, satz))
        if SATZ_HINWEIS not in wt or "/how-we-fund-this.html" not in ohne_templates(w):
            fehler.append("%s, affiliate-link live, aber der hinweis mit link auf %s fehlt" % (WALLETS, FUND))
    else:
        for satz in (SATZ_NULL, SATZ_NICHTS):
            if w and satz not in wt:
                fehler.append("%s, kein affiliate-link live, aber es fehlt: %r" % (WALLETS, satz))
        f = texte.get(FUND)
        if f is not None and SATZ_NOCH_KEINER not in sichtbarer_text(f):
            fehler.append("%s, es ist kein affiliate-link live, die seite muss das sagen (%r)" % (FUND, SATZ_NOCH_KEINER))
    return fehler


def stilfehler(text):
    aus = []
    if ":" in re.sub(r"https?://\S+|\b\d{1,2}:\d\d\b", "", text):
        aus.append("doppelpunkt")
    if re.search(r"\s[-–—]\s|—|–|->|→", text):
        aus.append("gedankenstrich oder pfeil")
    return aus


def zeilen(gegen):
    tab, fehler, warn = [], [], []
    for n in sorted(set(seiten()) | {p for p in (lies_namen(gegen) if gegen else [])}):
        neu, alt = lies(n), (lies(n, gegen) if gegen else None)
        if neu is None:
            continue
        t1, d1 = titel(neu), beschreibung(neu)
        t0, d0 = (titel(alt), beschreibung(alt)) if alt is not None else (None, None)
        geaendert = alt is None or t0 != t1 or d0 != d1
        tab.append((n, t0, t1, d0, d1, geaendert))
        if geaendert:
            if len(t1) > TITEL_MAX:
                fehler.append("%s, title %d zeichen, hoechstens %d" % (n, len(t1), TITEL_MAX))
            if not BESCHR_MIN <= len(d1) <= BESCHR_MAX:
                fehler.append("%s, description %d zeichen, soll %d bis %d" % (n, len(d1), BESCHR_MIN, BESCHR_MAX))
            for teil, txt in (("title", t1), ("description", d1)):
                for s in stilfehler(txt):
                    fehler.append("%s, %s mit %s" % (n, teil, s))
        else:
            if len(t1) > TITEL_MAX:
                warn.append("%s, title %d zeichen (unveraendert)" % (n, len(t1)))
    return tab, fehler, warn


def lies_namen(ref):
    r = subprocess.run(["git", "ls-tree", "--name-only", ref], cwd=REPO, capture_output=True)
    return [x for x in r.stdout.decode().split() if x.endswith(".html") and x not in NICHT_OEFFENTLICH]


def ausgabe(tab, markdown):
    if markdown:
        print("| Seite | title alt | title neu | description alt | description neu | Laenge t/d |")
        print("|---|---|---|---|---|---|")
        for n, t0, t1, d0, d1, g in tab:
            if not g:
                continue
            print("| %s | %s | %s | %s | %s | %d / %d |" % (
                n, t0 if t0 is not None else "(neu)", t1, d0 if d0 is not None else "(neu)", d1, len(t1), len(d1)))
    else:
        for n, t0, t1, d0, d1, g in tab:
            if g:
                print("%s\n  title  %r\n      -> %r (%d)\n  descr  %r\n      -> %r (%d)" % (
                    n, t0, t1, len(t1), d0, d1, len(d1)))


def pruefen(gegen=None, markdown=False):
    tab, fehler, warn = zeilen(gegen)
    ausgabe(tab, markdown)
    texte = {n: lies(n) for n in seiten()}
    for n, s in texte.items():
        # schema-fehler blockieren nur, wo das json-ld neu ist oder sich
        # aendert; sonst sind sie altbefund und warnung
        alt = lies(n, gegen) if gegen else None
        geaendert = gegen is None or alt is None or [d for d, _ in jsonld(alt)] != [d for d, _ in jsonld(s)]
        (fehler if geaendert else warn).extend(pruefe_schema(n, s))
    fehler += pruefe_affiliate(texte)
    idx = texte.get("index.html") or ""
    if FO_TAG not in idx:
        fehler.append("index.html, fo-verify-tag fehlt oder ist veraendert")
    print("\nwarnungen: %d" % len(warn))
    for w in warn:
        print("  " + w)
    print("fehler: %d" % len(fehler))
    for f in fehler:
        print("  " + f)
    return 1 if fehler else 0


def selbsttest():
    f = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            f.append(name)

    tmpl = '<template><a href="https://x.example" rel="sponsored noopener">x</a></template>'
    ok("link im template ist nicht live", live_affiliate(tmpl) == [])
    ok("sponsored-link ausserhalb ist live", live_affiliate('<a rel="sponsored noopener" href="https://x">x</a>')
       == ["https://x"])
    ok("noopener allein ist kein affiliate", live_affiliate('<a rel="noopener" href="https://x">x</a>') == [])
    leer = "<p>%s. Here. %s.</p>" % (SATZ_NICHTS, SATZ_NULL)
    ok("ohne live-link: saetze da, ok", pruefe_affiliate({WALLETS: leer + tmpl,
                                                          FUND: "<p>%s</p>" % SATZ_NOCH_KEINER}) == [])
    ok("ohne live-link: satz fehlt, fehler", len(pruefe_affiliate({WALLETS: "<p>x</p>"})) == 2)
    live = '<a rel="sponsored noopener" href="https://x">x</a>'
    ok("live-link, alte saetze noch da, fehler", len(pruefe_affiliate({WALLETS: leer + live})) == 3)
    ok("live-link mit hinweis, ok", pruefe_affiliate({WALLETS: "<p>%s <a href=\"/how-we-fund-this.html\">x</a></p>%s"
                                                      % (SATZ_HINWEIS, live)}) == [])
    ok("live-link auf anderer seite, fehler", any("ausserhalb" in x for x in
                                                   pruefe_affiliate({"kaspa-supply.html": live, WALLETS: leer})))
    faq = ('<h3>Is it safe?</h3><script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage",'
           '"mainEntity":[{"@type":"Question","name":"Is it safe?","acceptedAnswer":{"@type":"Answer","text":"Yes."}}]}'
           '</script>')
    ok("faq sichtbar und vollstaendig, ok", pruefe_schema("x", faq) == [])
    ok("faq-frage nicht sichtbar, fehler", len(pruefe_schema("x", faq.replace("<h3>Is it safe?</h3>", ""))) == 1)
    ok("kaputtes json, fehler", len(pruefe_schema("x", '<script type="application/ld+json">{x</script>')) == 1)
    ok("doppelpunkt im titel erkannt", stilfehler("Kaspa Wallets: Web") == ["doppelpunkt"])
    ok("uhrzeit ist kein doppelpunkt", stilfehler("at 16:15 utc") == [])
    ok("gedankenstrich erkannt", stilfehler("Kaspa — Wallets") == ["gedankenstrich oder pfeil"])
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gegen", help="ref zum vergleich, z. b. origin/main")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    return pruefen(a.gegen, a.markdown)


if __name__ == "__main__":
    sys.exit(main())
