#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""preis_wache.py, keine Preise und keine kursnahen Wenn-dann-Saetze (Ben, 5.11.2026).

ZWEI REGELN
  1. Keine Preise oeffentlich. Ein Betrag mit EUR, $ oder USD neben
     from, per, month, round oder price im sichtbaren Text ist rot. Im
     JSON-LD ist jedes Offer, price oder priceCurrency rot. Kaspa Pulse
     behaelt "free first look" und "ask for a quote".
     Ausgenommen sind Marktdaten: ein Betrag, in dessen Umfeld ein Wort wie
     kas, kaspa, close, wallet, tvl, volume, worth, fees oder source steht,
     ist ein Kurs- oder Wallet-Wert und kein Preis von uns.
  2. Keine kursnahen Saetze. "a close above" im sichtbaren Text ist rot,
     wie in scripts/weekly_numbers.py (kurs_wenn_dann).

WO GEPRUEFT WIRD
  - jede oeffentliche Seite (dieselbe Liste wie seo_pruefung.py) und jede
    Newsletter-Ausgabe, seit 6.11.2026 auch das Archiv ab 2026-09-14 (Ben,
    die alten Wenn-dann-Saetze sind durch Linienwerte ersetzt)
  - seo_pruefung.py ruft pruefe_seiten() auf, jeder PR mit Seitentext
  - startseite.py ruft verstoesse() fuer jeden sichtbaren Satz auf, bevor
    index.html geschrieben wird

    python3 scripts/preis_wache.py                 alle seiten und newsletter, Exit 1 bei Treffer
    python3 scripts/preis_wache.py for-builders.html
    python3 scripts/preis_wache.py --url https://kaspapulse.com/for-builders.html
    python3 scripts/preis_wache.py --selbsttest
"""
import argparse
import html as htmlmod
import json
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NEWSLETTER_AB = "2026-09-14"
UA = "kaspa-pulse-preis-wache (+https://kaspapulse.com)"

# ein betrag mit waehrung, vorne oder hinten
BETRAG = re.compile(
    r"(?:[€$]\s?\d[\d.,]*\s?[kmb]?\b"
    r"|\b(?:eur|usd)\s?\d[\d.,]*"
    r"|\b\d[\d.,]*\s?(?:€|eur\b|euro\b|euros\b|usd\b|\$))",
    re.I)
PREISWORT = re.compile(r"\b(?:from|per|month|monthly|round|rounds|price|prices|priced|pricing)\b", re.I)
MARKTWORT = re.compile(
    r"\b(?:kas|kaspa|close|closed|closes|wallet|wallets|balance|balances|tvl|volume|worth|"
    r"fees?|market|cap|supply|kraken|coingecko|defillama|source|line|average|dex|emission|"
    r"exchange|exchanges|holdings|candle|unrealized|realized|cost|basis|latest|value|valued|profit|loss)\b", re.I)
UMFELD = 3            # worte vor und nach dem betrag, "neben" heisst nah
KURS_SATZ = re.compile(r"\ba\s+close\s+above\b", re.I)


def sichtbarer_text(s):
    t = re.sub(r"(?is)<template\b.*?</template>", " ", s or "")
    t = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return " ".join(htmlmod.unescape(t).split())


def _umfeld(text, a, b, n=UMFELD):
    vor = text[:a].split()[-n:]
    nach = text[b:].split()[:n]
    return " ".join(vor), " ".join(nach)


def verstoesse(text):
    """Liste der Verstoesse in einem sichtbaren Text."""
    aus = []
    for m in BETRAG.finditer(text or ""):
        vor, nach = _umfeld(text, m.start(), m.end())
        umfeld = vor + " " + nach
        if PREISWORT.search(umfeld) and not MARKTWORT.search(umfeld):
            aus.append("preis im text: %r" % ("%s %s %s" % (vor[-40:], m.group(0), nach[:40])).strip())
    for m in KURS_SATZ.finditer(text or ""):
        aus.append("kursnaher satz: %r" % text[max(0, m.start() - 30):m.end() + 50])
    return aus


def _schema_preise(daten, pfad="$"):
    aus = []
    if isinstance(daten, dict):
        if str(daten.get("@type", "")).lower() in ("offer", "aggregateoffer", "unitpricespecification",
                                                   "pricespecification"):
            aus.append("schema %s mit @type %s" % (pfad, daten["@type"]))
        for k, v in daten.items():
            if k.lower() in ("offers", "price", "pricecurrency", "minprice", "maxprice", "pricespecification"):
                aus.append("schema %s.%s" % (pfad, k))
            elif isinstance(v, str) and k.lower() == "description" and verstoesse(v):
                aus.append("schema %s.description mit preis: %r" % (pfad, v[:80]))
            aus += _schema_preise(v, "%s.%s" % (pfad, k))
    elif isinstance(daten, list):
        for i, v in enumerate(daten):
            aus += _schema_preise(v, "%s[%d]" % (pfad, i))
    return aus


def schema_verstoesse(s):
    aus = []
    for b in re.findall(r'(?is)<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', s or ""):
        try:
            aus += _schema_preise(json.loads(b))
        except ValueError:
            continue
    return sorted(set(aus))


def seite_pruefen(s):
    """Sichtbarer Text, Titel und Beschreibung, JSON-LD."""
    aus = verstoesse(sichtbarer_text(s))
    for m in re.finditer(r'(?is)<meta\s+(?:name|property)="(?:description|og:description|twitter:description)"'
                         r'\s+content="([^"]*)"', s or ""):
        aus += ["meta, " + v for v in verstoesse(htmlmod.unescape(m.group(1)))]
    return aus + schema_verstoesse(s)


def newsletter_dateien(ab=NEWSLETTER_AB):
    return sorted("newsletter/%s" % p.name for p in (REPO / "newsletter").glob("*.html")
                  if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.html", p.name) and p.stem >= ab)


def alle_dateien():
    sys.path.insert(0, str(REPO / "scripts"))
    import seo_pruefung
    return seo_pruefung.seiten() + newsletter_dateien()


def pruefe_seiten(texte):
    """texte: {name: html}. Gibt die Fehlerzeilen zurueck."""
    aus = []
    for n, s in sorted(texte.items()):
        if s is None:
            continue
        aus += ["%s, %s" % (n, v) for v in seite_pruefen(s)]
    return aus


def selbsttest():
    f = []

    def ok(name, bed, info=""):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, ("  " + str(info)) if not bed and info else ""))
        if not bed:
            f.append(name)

    # regel 1, preise
    for t in ("from 150 € per round", "250 € one load curve 450 € two or three scenarios 150 € per month ongoing",
              "150 € per month ongoing", "from 75 €",
              "from $99 per month", "price 40 EUR", "EUR 120 per round", "monthly plan at 19 usd",
              "pricing starts at €49"):
        ok("preis rot: %s" % t, bool(verstoesse(t)), verstoesse(t))
    for t in ("the close of $0.035239 sits 7.72% below the 50 week average, source kraken",
              "the largest known wallet holds $12.4M worth of kas",
              "kraken volume of $4.72M is the thinnest week",
              "fees per day $1,240, source kaspalytics",
              "Your first look is free, then ask for a quote.",
              "EUR by bank transfer, KAS on request.",
              "1,779,989 kas per day from the emission schedule",
              "dex volume, 7 days $2.1M from the week before",
              "cost basis at the latest price − $88.0M (−64%) unrealized"):
        ok("kein preis: %s" % t, not verstoesse(t), verstoesse(t))
    # regel 2, kursnahe saetze
    ok("a close above ist rot", bool(verstoesse("a close above $0.035239 next week would put it back above")))
    ok("closed above the line ist kein wenn-dann", not verstoesse("it closed above the 21 week line for 3 weeks"))
    ok("der linienwert ist ok", not verstoesse("the 50 week line sits at $0.035239, source kraken"))
    # schema
    alt = ('<script type="application/ld+json">{"@type":"Service","offers":[{"@type":"Offer","name":"x",'
           '"priceSpecification":{"@type":"UnitPriceSpecification","minPrice":150,"priceCurrency":"EUR",'
           '"description":"from 150 EUR per round"}}]}</script>')
    ok("schema mit offer und preis ist rot", len(schema_verstoesse(alt)) >= 3, schema_verstoesse(alt))
    neu = '<script type="application/ld+json">{"@type":"Service","description":"free first look, ask for a quote"}</script>'
    ok("schema ohne preis ist gruen", schema_verstoesse(neu) == [], schema_verstoesse(neu))
    ok("schema description mit eur ist rot", bool(schema_verstoesse(
        '<script type="application/ld+json">{"@type":"Service","description":"Prices from 150 EUR per round"}</script>')))
    ok("meta description mit preis ist rot", bool(seite_pruefen(
        '<meta name="description" content="Reviews from 150 € per round.">')))
    ok("die alte for-builders-zeile ist rot, trotz kaspa und close im absatz", len(verstoesse(
        "Kaspa project review before your audit Pre-audit review from 150 € per round A close read of your "
        "project before it goes to a professional audit")) == 1)
    ok("preis im script zaehlt nicht als sichtbar", not verstoesse(sichtbarer_text(
        "<script>var p='from 150 € per round'</script><p>ask for a quote</p>")))
    ok("newsletter mit archiv ab 14.9.", "newsletter/2026-09-14.html" in newsletter_dateien()
       and "newsletter/2026-11-02.html" in newsletter_dateien())
    ok("linienwert als daten ist nicht rot", not verstoesse(
        "the 50 week line sits at $0.035296 and the 21 week line at $0.034790, source kraken, week to 31 october."))
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dateien", nargs="*")
    ap.add_argument("--url", action="append", default=[])
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    texte = {}
    for u in a.url:
        req = urllib.request.Request(u + ("&" if "?" in u else "?") + "preiswache=1", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            texte[u] = r.read().decode("utf-8", "replace")
    if not a.url:
        for n in (a.dateien or alle_dateien()):
            p = REPO / n
            texte[n] = p.read_text(encoding="utf-8") if p.exists() else None
    fehler = pruefe_seiten(texte)
    for z in fehler:
        print("ROT  " + z)
    print("%d seiten geprueft, %d verstoesse" % (len(texte), len(fehler)))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
