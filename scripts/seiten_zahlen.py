#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seiten_zahlen.py, schreibt Zahlen zur Buildzeit ins statische HTML (Ben, 06.10.2026, SEO-Ausbau).

Suchmaschinen lesen das HTML, nicht das, was ein Skript im Browser spaeter
nachlaedt. Deshalb stehen die Antwortsaetze mit ihren Zahlen fest im
Quelltext, zwischen Marken <!--AUTO:name--> und <!--/AUTO:name-->, und dieses
Skript erneuert sie aus den Daten, die die Workflows ohnehin schreiben. Jede
Zahl traegt ihr Datum und ihre Quelle.

  supply-antwort   kaspa-supply.html           aus data/weekly.json (api.kaspa.org/info/coinsupply)
  covenant-zahl    kaspa-smart-contracts.html  aus data/covenants-log.json (Kaspalytics)
  hashrate         kaspa-hashrate.html         live aus api.kaspa.org/info/hashrate und
                                               /info/hashrate/history (braucht Netz)

SEO-Runde, Ben 27.10.2026: jede der drei Seiten hat oben eine Kurz-Fakt-Zeile
(<!--AUTO:kurzfakt-->) und FAQ-Antworten mit Zahl. Die Antworten stehen im
FAQPage-Schema und werden von hier ersetzt, danach schreibt seo_faq.py sie
wortgleich in den sichtbaren FAQ-Block.

  kurzfakt + faq   kaspa-hashrate.html         hashrate wie oben
  kurzfakt + faq   kaspa-supply.html           halter und adressen aus
                                               data/address-thresholds-log.json (Kaspalytics)
  kurzfakt         kaspa-smart-contracts.html  covenant-bestand wie oben

Alle diese Zahlen kommen von fremden Quellen, also "source", nie "counted".

Faellt eine Quelle aus oder fehlt ein Wert, bleibt der alte Satz stehen.
Lieber ein Satz mit altem Datum als einer ohne Datum.

    python3 scripts/seiten_zahlen.py
    python3 scripts/seiten_zahlen.py --selbsttest
"""
import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seo_faq  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
MONATE = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def datum(iso):
    d = dt.date.fromisoformat(str(iso)[:10])
    return "%d %s %d" % (d.day, MONATE[d.month - 1], d.year)


def ganz(n):
    return "{:,}".format(int(round(n)))


def lies_json(pfad):
    try:
        return json.loads((REPO / pfad).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def supply_satz(w):
    """There are 27,738,976,506 KAS in circulation as of 5 October 2026, ..."""
    if not w:
        return None
    circ = w.get("circ_supply")
    cf = w.get("context_fallback") or {}
    pct = cf.get("mined_pct")
    stand = w.get("circ_supply_as_of")
    if not (circ and pct and stand):
        return None
    return ("There are <b>%s KAS</b> in circulation as of %s, which is <b>%.2f%%</b> of the maximum supply of "
            "about <b>28.7 billion KAS</b>, according to api.kaspa.org." % (ganz(circ), datum(stand), pct))


def covenant_satz(log):
    if not log:
        return None
    tage = [e for e in log.get("tage") or [] if e.get("utxo_count") is not None]
    if not tage:
        return None
    e = tage[-1]
    # Bens Regel 16.10.2026: Kaspalytics-Reihen tragen "source kaspalytics",
    # "counted" nur bei eigenen Zaehlungen
    return ("On layer 1, <b>%s covenant outputs</b> were unspent on chain at the end of %s, source "
            "kaspalytics, logged daily in <a href=\"/kaspa-covenants.html\">our covenant log</a>."
            % (ganz(e["utxo_count"]), datum(e["datum"])))


def covenant_fakt(log):
    if not log:
        return None
    tage = [e for e in log.get("tage") or [] if e.get("utxo_count") is not None]
    if not tage:
        return None
    e = tage[-1]
    return ("<b>%s covenant outputs</b> unspent on Kaspa layer 1 at the end of %s, source kaspalytics"
            % (ganz(e["utxo_count"]), datum(e["datum"])))


def covenant_satz2(log):
    if not log:
        return None
    tage = [e for e in log.get("tage") or [] if e.get("utxo_count") is not None]
    if not tage:
        return None
    e = tage[-1]
    return ("<b>%s covenant outputs</b> were unspent on Kaspa layer 1 at the end of %s, source kaspalytics."
            % (ganz(e["utxo_count"]), datum(e["datum"])))


def halter_letzter(log):
    tage = [e for e in (log or {}).get("tage") or []
            if e.get("holders_mean") and e.get("holders_all") and e.get("holders_001kas")]
    return tage[-1] if tage else None


def halter_fakt(log):
    e = halter_letzter(log)
    if not e:
        return None
    return ("<b>%s wallet holders</b> with a meaningful balance and <b>%s addresses</b> with any balance on %s, "
            "source kaspalytics" % (ganz(e["holders_mean"]), ganz(e["holders_all"]), datum(e["datum"])))


def halter_tabelle(log):
    e = halter_letzter(log)
    if not e:
        return None
    zeilen = [("addresses with any balance", e["holders_all"]),
              ("addresses with a meaningful balance, the holder count", e["holders_mean"]),
              ("addresses with 0.01 KAS or more", e["holders_001kas"])]
    for feld, text in (("holders_1kas", "addresses with 1 KAS or more"),
                       ("holders_100kas", "addresses with 100 KAS or more")):
        if e.get(feld):
            zeilen.append((text, e[feld]))
    return ("<table><thead><tr><th>Kaspa addresses on %s</th><th>Count</th></tr></thead><tbody>%s</tbody></table>"
            "<p class=\"note\">Source kaspalytics, logged weekly by us. Each row counts every address at or above "
            "its line, so the rows overlap.</p>" % (
                datum(e["datum"]), "".join("<tr><td>%s</td><td>%s</td></tr>" % (t, ganz(n)) for t, n in zeilen)))


def halter_faq(log):
    e = halter_letzter(log)
    if not e:
        return None
    tag = datum(e["datum"])
    return {
        "How many Kaspa wallet holders are there?":
            "There were %s Kaspa addresses with a meaningful balance on %s, source kaspalytics, the closest "
            "public measure of wallet holders. One person can hold many addresses, so this counts addresses, "
            "not people." % (ganz(e["holders_mean"]), tag),
        "How many Kaspa addresses are there?":
            "There were %s Kaspa addresses with a balance on %s, source kaspalytics. Most of them hold dust, "
            "only %s held 0.01 KAS or more on the same day." % (ganz(e["holders_all"]), tag,
                                                               ganz(e["holders_001kas"])),
    }


REST = "https://api.kaspa.org"
UA = "kaspa-pulse-bot (+https://kaspapulse.com)"


def hole(pfad):
    req = urllib.request.Request(REST + pfad, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def hashrate_daten(jetzt=None):
    """Aktueller Wert (TH/s) und Tagesmittel aus der Historie (kH/s -> PH/s)."""
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    akt = hole("/info/hashrate?stringOnly=false")
    roh = hole("/info/hashrate/history")
    je = {}
    for x in roh:
        t = dt.datetime.fromtimestamp(x["timestamp"] / 1000, dt.timezone.utc)
        je.setdefault(t.date(), []).append(x["hashrate_kh"] / 1e12)
    return {"jetzt": jetzt, "ph": float(akt["hashrate"]) / 1e3,
            "tage": {d: sum(v) / len(v) for d, v in je.items()}}


def hashrate_html(d, wochen=8):
    if not d or not d.get("tage"):
        return None
    jetzt, tage = d["jetzt"], d["tage"]
    heute = jetzt.date()
    fertig = {t: v for t, v in tage.items() if t < heute}
    if not fertig:
        return None
    hoch_tag = max(fertig, key=lambda t: fertig[t])
    erster = min(fertig)
    montag = heute - dt.timedelta(days=heute.weekday())
    zeilen = []
    for k in range(wochen, 0, -1):
        a = montag - dt.timedelta(weeks=k)
        werte = [fertig[a + dt.timedelta(days=i)] for i in range(7) if a + dt.timedelta(days=i) in fertig]
        if len(werte) == 7:
            zeilen.append("<tr><td>week of %s</td><td>%.1f PH/s</td></tr>" % (datum(a.isoformat()), sum(werte) / 7))
    wann = "%s at %s UTC" % (datum(jetzt.isoformat()), jetzt.strftime("%H:%M"))
    # Rekord nur mit Zeitraum: der Zeitraum ist die Historie der Quelle
    satz = ("Kaspa's hashrate was <b>%.1f PH/s</b> on %s, according to api.kaspa.org. The highest daily "
            "average between %s and %s is <b>%.1f PH/s</b>, on %s." % (
                d["ph"], wann, datum(erster.isoformat()), datum(max(fertig).isoformat()), fertig[hoch_tag],
                datum(hoch_tag.isoformat())))
    fakt = "<b>%.1f PH/s</b> Kaspa hashrate on %s, source the Kaspa REST API" % (d["ph"], wann)
    faq = {"What is Kaspa's hashrate?": "Kaspa's hashrate was %.1f PH/s on %s, source the Kaspa REST API." % (
        d["ph"], wann)}
    tabelle = ("<table><thead><tr><th>Week, Monday to Sunday</th><th>Average hashrate</th></tr></thead><tbody>%s"
               "</tbody></table><p class=\"note\">Weekly averages of the daily means in api.kaspa.org's hashrate "
               "history, read on %s.</p>" % ("".join(zeilen), datum(jetzt.isoformat())))
    return {"hashrate-satz": satz, "hashrate-wochen": tabelle, "kurzfakt": fakt, "faq": faq}


AUFGABEN = [
    ("kaspa-supply.html", "supply-antwort", lambda: supply_satz(lies_json("data/weekly.json"))),
    ("kaspa-smart-contracts.html", "covenant-zahl", lambda: covenant_satz(lies_json("data/covenants-log.json"))),
    ("kaspa-smart-contracts.html", "kurzfakt", lambda: covenant_fakt(lies_json("data/covenants-log.json"))),
    ("kaspa-smart-contracts.html", "covenant-zahl2", lambda: covenant_satz2(lies_json("data/covenants-log.json"))),
    ("kaspa-supply.html", "kurzfakt", lambda: halter_fakt(lies_json("data/address-thresholds-log.json"))),
    ("kaspa-supply.html", "halter-tabelle", lambda: halter_tabelle(lies_json("data/address-thresholds-log.json"))),
]

# FAQ-Antworten mit Zahl, je Seite ein dict frage -> antwort
FAQ_AUFGABEN = [
    ("kaspa-supply.html", lambda: halter_faq(lies_json("data/address-thresholds-log.json"))),
]


def ersetze(s, name, inhalt):
    m = re.compile(r"(<!--AUTO:%s-->)(.*?)(<!--/AUTO:%s-->)" % (re.escape(name), re.escape(name)), re.S)
    if not m.search(s):
        raise SystemExit("marke %s fehlt" % name)
    return m.sub(lambda x: x.group(1) + inhalt + x.group(3), s, count=1)


LDJSON = re.compile(r'(<script[^>]+type="application/ld\+json"[^>]*>)(.*?)(</script>)', re.S)


def faq_setzen(s, antworten):
    """Ersetzt die Antworttexte der genannten Fragen im FAQPage-Schema. Fehlt
    eine Frage, kommt sie vorne dazu. Danach zieht der sichtbare FAQ-Block nach."""
    def ein(m):
        try:
            d = json.loads(m.group(2))
        except ValueError:
            return m.group(0)
        if not (isinstance(d, dict) and d.get("@type") == "FAQPage"):
            return m.group(0)
        liste = d.setdefault("mainEntity", [])
        neu = []
        for frage, text in antworten.items():
            q = next((q for q in liste if (q.get("name") or "").strip() == frage), None)
            if q is None:
                neu.append({"@type": "Question", "name": frage,
                            "acceptedAnswer": {"@type": "Answer", "text": text}})
            elif (q.get("acceptedAnswer") or {}).get("text") != text:
                q["acceptedAnswer"] = {"@type": "Answer", "text": text}
            else:
                continue
            ein.geaendert = True
        d["mainEntity"] = neu + liste
        if not ein.geaendert:
            return m.group(0)
        return m.group(1) + "\n" + json.dumps(d, ensure_ascii=False, indent=2) + "\n" + m.group(3)
    ein.geaendert = False
    n = LDJSON.sub(ein, s)
    if n == s:
        return s
    return seo_faq.einsetzen(n)[0]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--selbsttest"]:
        return selbsttest()
    aufgaben = list(AUFGABEN)
    if "--ohne-netz" not in argv:
        try:
            hr = hashrate_html(hashrate_daten())
        except Exception as exc:                    # noqa: BLE001
            print("kaspa-hashrate.html, api.kaspa.org nicht erreichbar (%s), alte saetze bleiben" % type(exc).__name__)
            hr = None
        for name in ("hashrate-satz", "hashrate-wochen", "kurzfakt"):
            aufgaben.append(("kaspa-hashrate.html", name, (lambda n=name: hr[n] if hr else None)))
    faq_aufgaben = list(FAQ_AUFGABEN)
    if "--ohne-netz" not in argv:
        faq_aufgaben.append(("kaspa-hashrate.html", lambda: hr["faq"] if hr else None))
    for datei, name, quelle in aufgaben:
        p = REPO / datei
        s = p.read_text(encoding="utf-8")
        satz = quelle()
        if satz is None:
            print("%s, %s, keine daten, alter satz bleibt" % (datei, name))
            continue
        n = ersetze(s, name, satz)
        if n != s:
            p.write_text(n, encoding="utf-8")
            print("%s, %s, neu" % (datei, name))
        else:
            print("%s, %s, unveraendert" % (datei, name))
    for datei, quelle in faq_aufgaben:
        p = REPO / datei
        s = p.read_text(encoding="utf-8")
        antworten = quelle()
        if not antworten:
            print("%s, faq, keine daten, alte antworten bleiben" % datei)
            continue
        n = faq_setzen(s, antworten)
        if n != s:
            p.write_text(n, encoding="utf-8")
        print("%s, faq, %s" % (datei, "neu" if n != s else "unveraendert"))
    return 0


def selbsttest():
    f = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            f.append(name)

    w = {"circ_supply": 27738976506, "circ_supply_as_of": "2026-10-05T06:45:07Z",
         "context_fallback": {"mined_pct": 96.64}}
    ok("supply-satz", supply_satz(w) == "There are <b>27,738,976,506 KAS</b> in circulation as of 5 October 2026, "
       "which is <b>96.64%</b> of the maximum supply of about <b>28.7 billion KAS</b>, according to api.kaspa.org.")
    ok("supply ohne prozent bleibt leer", supply_satz({"circ_supply": 1, "circ_supply_as_of": "2026-10-05"}) is None)
    log = {"tage": [{"datum": "2026-10-03", "utxo_count": 13707}, {"datum": "2026-10-04", "utxo_count": 13760},
                    {"datum": "2026-10-05", "utxo_count": None}]}
    ok("covenant-satz nimmt den letzten tag mit bestand", "13,760 covenant outputs" in covenant_satz(log)
       and "4 October 2026" in covenant_satz(log))
    tage = {dt.date(2026, 8, 3) + dt.timedelta(days=i): 300.0 + (i % 7) for i in range(63)}
    tage[dt.date(2026, 8, 20)] = 512.34
    h = hashrate_html({"jetzt": dt.datetime(2026, 10, 6, 11, 5, tzinfo=dt.timezone.utc), "ph": 345.67, "tage": tage})
    ok("hashrate-satz mit zeit und hoechstwert mit zeitraum", h["hashrate-satz"].startswith(
        "Kaspa's hashrate was <b>345.7 PH/s</b> on 6 October 2026 at 11:05 UTC")
       and "between 3 August 2026 and 4 October 2026 is <b>512.3 PH/s</b>, on 20 August 2026"
       in h["hashrate-satz"] and "on record" not in h["hashrate-satz"])
    ok("hashrate kurzfakt und faq mit datum und source", h["kurzfakt"] == (
        "<b>345.7 PH/s</b> Kaspa hashrate on 6 October 2026 at 11:05 UTC, source the Kaspa REST API")
       and h["faq"]["What is Kaspa's hashrate?"] == (
        "Kaspa's hashrate was 345.7 PH/s on 6 October 2026 at 11:05 UTC, source the Kaspa REST API."))
    hl = {"tage": [{"datum": "2026-10-25", "holders_all": 54887787, "holders_mean": 808128,
                    "holders_001kas": 768253},
                   {"datum": "2026-10-26", "holders_all": 1, "holders_mean": None}]}
    ok("halter kurzfakt nimmt den letzten vollen tag", halter_fakt(hl) == (
        "<b>808,128 wallet holders</b> with a meaningful balance and <b>54,887,787 addresses</b> with any "
        "balance on 25 October 2026, source kaspalytics"))
    hf = halter_faq(hl)
    ok("halter faq, beide fragen, source statt counted",
       "808,128" in hf["How many Kaspa wallet holders are there?"]
       and "54,887,787" in hf["How many Kaspa addresses are there?"]
       and "768,253" in hf["How many Kaspa addresses are there?"]
       and not any("counted" in v for v in hf.values()))
    ht = halter_tabelle(hl)
    ok("halter tabelle mit datum, drei zeilen ohne 1+ und 100+", ht.count("<tr><td>") == 3
       and "Kaspa addresses on 25 October 2026" in ht and "808,128" in ht)
    ok("covenant satz2", covenant_satz2(log).startswith("<b>13,760 covenant outputs</b> were unspent"))
    ok("halter ohne daten bleibt leer", halter_fakt({"tage": []}) is None and halter_faq(None) is None)
    ok("covenant kurzfakt", covenant_fakt(log) == (
        "<b>13,760 covenant outputs</b> unspent on Kaspa layer 1 at the end of 4 October 2026, source kaspalytics"))
    seite = ('<p>x</p>\n<!--AUTO:faq-->\n<!--/AUTO:faq-->\n<script type="application/ld+json">\n{"@context": '
             '"https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": "Old?", '
             '"acceptedAnswer": {"@type": "Answer", "text": "alt"}}]}\n</script>')
    n1 = faq_setzen(seite, {"Old?": "neu", "New?": "dazu"})
    ok("faq ersetzt, ergaenzt vorne und zeigt sichtbar", '"text": "neu"' in n1 and n1.index("New?") < n1.index("Old?")
       and "<h3>New?</h3>" in n1 and "<p>neu</p>" in n1)
    ok("faq ein zweites mal unveraendert", faq_setzen(n1, {"Old?": "neu", "New?": "dazu"}) == n1)
    ok("textregeln in festen saetzen", not any(re.search(r"\b(live|now|today|currently|right now)\b|[\u2013\u2014:]|->",
                                                          re.sub(r"<[^>]+>|\d\d:\d\d", "", x))
                                               for x in [h["kurzfakt"], halter_fakt(hl), covenant_fakt(log)]
                                               + list(hf.values()) + list(h["faq"].values())))
    ok("acht volle wochen, die laufende nicht", h["hashrate-wochen"].count("<tr><td>week of") == 8
       and "week of 28 September 2026" in h["hashrate-wochen"] and "5 October" not in h["hashrate-wochen"])
    ok("ersetzen zwischen marken", ersetze("a<!--AUTO:x-->alt<!--/AUTO:x-->b", "x", "neu")
       == "a<!--AUTO:x-->neu<!--/AUTO:x-->b")
    print("%d fehler" % len(f))
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
