#!/usr/bin/env python3
"""
baut das cheat sheet "the 8 kaspa numbers whales watch" aus unseren reihen

Edition 1 (Oktober 2026) hat Ben von Hand gebaut, mit CSV-Dateien, die ich
ihm geliefert hatte, und Schriften aus node_modules. Das laeuft einmal.
Monatlich laeuft es nur, wenn die Zahlen aus denselben Reihen kommen, aus
denen auch die Seiten und die Tagesgrafik leben, und wenn ein Lauf abbricht,
statt eine alte Zahl mit neuem Datum zu zeigen.

Die Texte stehen hier so, wie Ben sie in Fassung 2 freigegeben hat. Geaendert
wird daran nichts, auch keine Wortstellung. Was sich jeden Monat aendert,
sind die Zahlen darin, und die stehen als Platzhalter.

DIE REGEL, DIE DEN GANZEN BAU TRAEGT
Jede Zahl bringt ihren Stichtag mit. Ist ein Stichtag aelter als
FRIST_TAGE, bricht der Lauf ab und nennt die Zahl beim Namen. Kein
stillschweigendes Weiterverwenden: ein PDF mit "edition 2 - november" und
einem Gebuehrenwert vom September waere eine Luege mit Datum.

ACHSEN UND ABGELEITETE ZAHLEN
In Edition 1 standen die Achsengrenzen, die Quadratzahl im Gebuehrenraster,
der aktuelle Reward und das 7-Tage-Mittel als Zahl im Quelltext. Hier wird
alles gerechnet, siehe achse() und die vorlagen. Der Selbsttest baut mit den
Daten vom 11.10.2026 und prueft, dass dieselben Zahlen herauskommen wie in
Fassung 2.1, der veroeffentlichten Ausgabe.

AUFRUFE
    --probe [--aus datei]   nur messen, probe als json auf stdout
    --bauen [--aus datei]   html und pdf nach graphics/cheat-sheet/
    --selbsttest            mit scripts/cheat-sheet-probe.json, ohne netz
    --edition N             ausgabe-nummer erzwingen (sonst log + 1)
    --stand JJJJ-MM-TT      als dieser tag rechnen (frist, "x days from")
"""
import argparse
import base64
import datetime as dt
import json
import math
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO = Path(__file__).resolve().parent.parent
SCHRIFTEN = REPO / "graphics" / "fonts"
AUS = REPO / "graphics" / "cheat-sheet"
PROBE_FEST = REPO / "scripts" / "cheat-sheet-probe.json"
LOG = REPO / "data" / "cheat-sheet-log.json"
WEBSEITE = REPO / "kaspa-pulse-cheat-sheet.pdf"

FRIST_TAGE = 10                      # aelterer Stichtag, dann Abbruch
SEITE_PX = (1080, 1350)
TITEL = "The 8 Kaspa numbers whales watch"

BG, SURF, LINE = "#080B0F", "#0E1418", "#1B252B"
# INK3 von #6F7E7B (4.6:1) auf #96A5A2: 7.7:1 auf BG, 7.2:1 auf SURF, die
# Grafik-Regel 7:1 (Ben, 25.10.2026). Nur die Farbe, kein Satz geaendert.
INK, INK2, INK3 = "#F2F5F4", "#A9B7B4", "#96A5A2"
ACC, ACCD, ACCF = "#49EACB", "#1F6B5D", "#123D36"

MONATE = ["jan", "feb", "mar", "apr", "may", "jun",
          "jul", "aug", "sep", "oct", "nov", "dec"]
MONATE_LANG = ["january", "february", "march", "april", "may", "june", "july",
               "august", "september", "october", "november", "december"]


class Abbruch(Exception):
    """Eine Zahl fehlt oder ist zu alt. Lieber kein PDF als ein falsches."""


# ------------------------------------------------------------------ werkzeug

def fmt(n, d=0):
    return "{:,.{}f}".format(float(n), d)


def tag_lang(d):
    """2026-10-10 -> "10 oct 2026"."""
    d = dt.date.fromisoformat(str(d)[:10])
    return "%d %s %d" % (d.day, MONATE[d.month - 1], d.year)


def tag_kurz(d):
    """2026-07-19 -> "19 jul"."""
    d = dt.date.fromisoformat(str(d)[:10])
    return "%d %s" % (d.day, MONATE[d.month - 1])


def tag_monat(d):
    """2026-06-30 -> "30 june", mit ausgeschriebenem Monat und ohne Jahr."""
    d = dt.date.fromisoformat(str(d)[:10])
    return "%d %s" % (d.day, MONATE_LANG[d.month - 1])


def spanne(von, bis, lang=True):
    """"4 to 10 oct 2026" im selben Monat, sonst "28 sep to 4 oct 2026"."""
    a = dt.date.fromisoformat(str(von)[:10])
    b = dt.date.fromisoformat(str(bis)[:10])
    ende = tag_lang(b) if lang else tag_kurz(b)
    if (a.year, a.month) == (b.year, b.month):
        return "%d to %s" % (a.day, ende)
    return "%s to %s" % (tag_kurz(a), ende)


def mio(v):
    """56765432 -> "56.77 million"."""
    return "%.2f million" % (float(v) / 1e6)


def alter(stichtag, heute):
    return (heute - dt.date.fromisoformat(str(stichtag)[:10])).days


# ------------------------------------------------------------------- achsen
#
# Edition 1 hatte 13.4 bis 14.4, 290 bis 380 und 0 bis 300000 im Quelltext.
# Hier dieselbe Rechnung fuer alle drei Diagramme:
#
#   schritt  die groesste "runde" Zahl (1, 2, 2.5, 5 mal Zehnerpotenz),
#            die hoechstens ein Drittel der Spanne ist. Ein Drittel, weil
#            line_chart vier Hilfslinien in Dritteln zieht.
#   grenzen  Spanne um ein Fuenftel polstern, dann nach aussen auf ein
#            Vielfaches des Schritts runden. Sonst klebt die Linie am Rahmen.
#
# Eine kumulierte Reihe faengt bei null an und endet auf ihrem Hoechstwert.
# Die polstert nicht, sie laeuft von 0 bis zum naechsten Schritt ueber dem
# letzten Punkt.
POLSTER = 0.2
NETT = (1.0, 2.0, 2.5, 5.0)


def kontrast_hex(a, b):
    """WCAG-Kontrast zweier Farben in #RRGGBB."""
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def nett_schritt(hoechstens):
    """Groesste runde Zahl <= hoechstens."""
    if hoechstens <= 0:
        raise Abbruch("achse ohne spanne")
    p = math.floor(math.log10(hoechstens))
    best = None
    for k in (p - 1, p, p + 1):
        for n in NETT:
            s = n * 10 ** k
            if s <= hoechstens + 1e-12 and (best is None or s > best):
                best = s
    return best


def achse(werte, polster=POLSTER):
    w = [v for v in werte if v is not None]
    lo, hi = min(w), max(w)
    spanne = hi - lo
    if spanne <= 0:
        raise Abbruch("achse ohne spanne, alle werte gleich")
    s = nett_schritt(spanne / 3)
    unten = math.floor((lo - polster * spanne) / s) * s
    oben = math.ceil((hi + polster * spanne) / s) * s
    # vier gitterlinien teilen die achse in drei teile. ist die zahl der
    # schritte kein vielfaches von drei, stehen dort krumme werte wie 333
    # und 367 (probelauf 28.10.2026). dann oben auf das naechste vielfache.
    n = round((oben - unten) / s)
    n3 = -(-n // 3) * 3
    return unten, round(unten + n3 * s, 10)


def achse_kumuliert(werte):
    w = [v for v in werte if v is not None]
    spanne = max(w) - min(w)
    if spanne <= 0:
        raise Abbruch("achse ohne spanne")
    # drei glatte schritte von 0 bis oben, der kleinste, der den hoechsten
    # wert traegt. sonst stuenden dort 133k und 267k (316,522 covenants am
    # 25.10.2026 ergaben 0 bis 400k), aufgerundet auf 600k haenge die linie
    # in der unteren haelfte. 292,292 aus Edition 1 bleibt 0 bis 300k.
    oben = max(w)
    k = math.floor(math.log10(oben / 3))
    schritte = sorted(n * 10 ** e for e in (k, k + 1) for n in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0))
    s = next(x for x in schritte if 3 * x >= oben)
    return 0.0, round(3 * s, 10)


# -------------------------------------------------------------- datenschicht
#
# Eine Funktion je Zahl. Jede liefert ein dict mit "stichtag" und den
# Rohwerten, nichts Formatiertes und keinen Text. Alles, was Netz braucht,
# geht ueber tagesgrafik, damit die Mitternachtsregel und die
# Plausibilitaetsfenster nur an einer Stelle stehen.

EX_MELDESCHWELLE = 100000             # KAS, ab hier nennen wir einen Abfluss
WOCHEN_PUNKTE = 12                    # punkte in der boersen-wochenreihe
HASH_FENSTER = 7                      # tage im hashrate-mittel
HASH_REIHE_TAGE = 59                  # tage im hashrate-diagramm


def _tg():
    import tagesgrafik
    return tagesgrafik


def _json(pfad):
    return json.loads(Path(pfad).read_text(encoding="utf-8"))


def z_entityx(heute):
    """Balance von Entity X live, Umlauf aus weekly.json mit eigenem Stand,
    letzter gemeldeter Abfluss aus unserem Abflusslog."""
    tg = _tg()
    bal = tg.m_balance(tg.EX_ADR)
    w = _json(REPO / "data" / "weekly.json")
    o = _json(REPO / "data" / "entity-x-outflows.json")
    gross = [x for x in o.get("outflows", []) if x["net_out_kas"] >= EX_MELDESCHWELLE]
    if not gross:
        raise Abbruch("entity x, kein abfluss ab %s KAS im log" % fmt(EX_MELDESCHWELLE))
    letzt = gross[-1]
    return {"stichtag": heute.isoformat(), "balance": bal,
            "umlauf": float(w["circ_supply"]), "umlauf_stichtag": w["circ_supply_as_of"][:10],
            "abfluss_tag": letzt["day"], "abfluss_kas": letzt["net_out_kas"]}


def umlauf_je_tag(tage, jetzt=None, umlauf_jetzt=None, emission=None):
    """Umlauf am Ende jedes Tages, zurueckgerechnet vom heutigen Umlauf aus
    api.kaspa.org/info/coinsupply, wie in tagesgrafik und weekly_numbers,
    minus der Emission seitdem aus dem Emissionsplan (computed).

    Eine Kaspalytics-Reihe "supply/circulating" gibt es nicht, der erste
    Probelauf mit echten Daten am 28.10.2026 bekam HTTP 404. Der Fehler
    durch Netzzeit und Rundung liegt unter 1 zu 100.000, weit unter der
    ersten Nachkommastelle des Anteils."""
    if not tage:
        return {}
    if umlauf_jetzt is None:
        tg = _tg()
        jetzt = dt.datetime.now(dt.timezone.utc)
        umlauf_jetzt = tg.m_supply()[0]
        emission = tg.emission_am_tag
    heute = jetzt.date()
    teil = (jetzt - dt.datetime.combine(heute, dt.time(), dt.timezone.utc)).total_seconds() / 86400.0
    # was nach dem ende von tag d dazukam: die vollen tage danach plus der angebrochene heute
    nach = {}
    summe = emission(heute.isoformat()) * teil
    d = heute - dt.timedelta(days=1)
    erster = dt.date.fromisoformat(tage[0])
    while d >= erster:
        nach[d.isoformat()] = summe
        summe += emission(d.isoformat())
        d -= dt.timedelta(days=1)
    return {t: umlauf_jetzt - nach[t] for t in tage if t in nach}


def z_boersen(heute):
    """KAS in Boersen-Wallets, Anteil am Umlauf. Wochenreihe aus derselben
    Quelle, ein Punkt je Montag, Stichtag der letzte volle Tag davor."""
    tg = _tg()
    bestand = tg.m_kl_reihe("supply/exchange-holdings", "Balance", "moment")
    heute_iso = heute.isoformat()
    umlauf = umlauf_je_tag(sorted(d for d in bestand if d < heute_iso))
    tage = sorted(d for d in set(bestand) & set(umlauf) if d < heute_iso)
    if not tage:
        raise Abbruch("boersen, kein gemeinsamer stichtag mit dem umlauf")
    reihe = []
    for d in tage:
        tg_d = dt.date.fromisoformat(d)
        if tg_d.weekday() == 6:                     # sonntag, der stand vor montag
            reihe.append([d, bestand[d], 100.0 * bestand[d] / umlauf[d]])
    reihe = reihe[-WOCHEN_PUNKTE:]
    if len(reihe) < 4:
        raise Abbruch("boersen, nur %d wochenpunkte" % len(reihe))
    d = reihe[-1][0]
    return {"stichtag": d, "kas": reihe[-1][1], "pct": reihe[-1][2], "reihe": reihe}


# Die Woerter "half" und "a quarter" auf Seite 3 stehen nur, solange die
# Anteile dazu passen. Dieselben Fenster wie in tagesgrafik.vorlage_11.
HALB = (45.0, 55.0)
# Seite 3 sagt "logged by us every week since <monat>". Gemeint sind unsere
# Wochenstaende seit Edition 1 (erster Sonntag 26.07.2026). Kaspalytics
# liefert die Reihe ab 2023, ohne diese Grenze stuende dort "since august"
# mit einer Spanne von 14.1% bis 51.3% (Probelauf 28.10.2026).
UNBEWEGT_SEIT = "2026-07-26"
VIERTEL = (20.0, 30.0)


def woerter_pruefen(p1, p2):
    """Seite 3 sagt "half" und "a quarter". Passen die Anteile nicht mehr
    dazu, bricht der Lauf ab, statt ein falsches Wort zu drucken. Den Text
    aendert Ben, nicht der Generator."""
    if not HALB[0] <= p1 <= HALB[1]:
        raise Abbruch('unbewegt, %.1f%% traegt das wort "half" auf seite 3 nicht mehr' % p1)
    if not VIERTEL[0] <= p2 <= VIERTEL[1]:
        raise Abbruch('unbewegt, %.1f%% traegt das wort "a quarter" auf seite 3 nicht mehr' % p2)
    return True


def z_unbewegt(heute):
    """Anteil des Umlaufs, der seit 1 bzw. 2 Jahren nicht bewegt wurde.
    Beide Werte vom selben Stichtag, sonst keine Zahl, wie in Form 11.
    Dazu die Spanne der Wochenstaende, also der Sonntage, seit Beginn."""
    tg = _tg()
    eins = tg.m_kl_reihe("supply/inactive?minAge=1year", "CSPERCENT", "bestand")
    zwei = tg.m_kl_reihe("supply/inactive?minAge=2years", "CSPERCENT", "bestand")
    heute_iso = heute.isoformat()
    tage = sorted(d for d in set(eins) & set(zwei) if d < heute_iso)
    if not tage:
        raise Abbruch("unbewegt, kein gemeinsamer stichtag fuer 1 und 2 jahre")
    d = tage[-1]
    p1, p2 = eins[d], zwei[d]
    if not 0 < p2 <= p1 < 100:
        raise Abbruch("unbewegt, anteile unplausibel, 1 jahr %s, 2 jahre %s" % (p1, p2))
    woerter_pruefen(p1, p2)
    sonntage = [[x, eins[x]] for x in tage
                if dt.date.fromisoformat(x).weekday() == 6 and x >= UNBEWEGT_SEIT]
    if len(sonntage) < 4:
        raise Abbruch("unbewegt, nur %d wochenstaende" % len(sonntage))
    return {"stichtag": d, "p1": p1, "p2": p2, "wochen_von": sonntage[0][0],
            "wochen_min": min(x[1] for x in sonntage),
            "wochen_max": max(x[1] for x in sonntage)}


def z_halter(heute):
    """Adressen ab 100 KAS, die beiden kleineren Schwellen fuer den Trichter
    und die Veraenderung ueber 7, 30 und 90 Tage."""
    tage = {e["datum"]: e for e in _json(REPO / "data" / "address-thresholds-log.json")["tage"]}
    if not tage:
        raise Abbruch("halter, leeres schwellenlog")
    d = max(tage)
    e = tage[d]
    aus = {"stichtag": d, "k100": e["holders_100kas"], "k1": e["holders_1kas"],
           "k001": e["holders_001kas"], "alle": e["holders_all"]}
    bezug = dt.date.fromisoformat(d)
    for n in (7, 30, 90):
        frueher = tage.get((bezug - dt.timedelta(days=n)).isoformat())
        if not frueher:
            raise Abbruch("halter, kein wert %d tage vor %s" % (n, d))
        aus["d%d" % n] = e["holders_100kas"] - frueher["holders_100kas"]
    return aus


def z_senkung(heute):
    """Naechste Reward-Senkung und die Treppe der naechsten 24 Stufen. Reine
    Rechnung aus dem Emissionsplan, kein Netz."""
    nod = _tg().reward_plan()
    jetzt = dt.datetime.combine(heute, dt.time(12), dt.timezone.utc).timestamp()
    cur, nxt, nxt_ts = nod.reward_state(jetzt)
    stufen = []
    for k in range(24):
        ts = nxt_ts + k * nod.STEP
        stufen.append([dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat(
            timespec="seconds").replace("+00:00", "Z"), nod.reward_state(ts + 1)[0]])
    return {"stichtag": heute.isoformat(), "jetzt": cur, "naechste": nxt,
            "zeit_utc": dt.datetime.fromtimestamp(nxt_ts, dt.timezone.utc).isoformat(
                timespec="seconds").replace("+00:00", "Z"), "stufen": stufen}


def z_gebuehren(heute):
    """Neue Coins gegen Gebuehren, aus dem Tageslog. Dort steht die Reihe
    jeden Tag, seit PR #78. Gemessen wird sie hier nicht neu: das Tageslog
    ist die Quelle, die auch die Grafik des Tages belegt."""
    log = _json(REPO / "data" / "tagesgrafik-log.json")
    mit = sorted((e for e in log.get("laeufe", [])
                  if isinstance((e.get("messwerte") or {}).get("gebuehren"), dict)
                  and not e["messwerte"]["gebuehren"].get("ausfall")),
                 key=lambda e: e["datum"])
    if not mit:
        raise Abbruch("gebuehren, keine heile reihe im tageslog")
    e = mit[-1]
    g = dict(e["messwerte"]["gebuehren"])
    g["stichtag"] = e["datum"]
    return g


def z_hashrate(heute):
    """Hashrate, Tagesmittel je Tag aus api.kaspa.org. Das Mittel der
    letzten HASH_FENSTER Tage ist die Zahl, einzelne Tage springen um ein
    Zehntel."""
    tage = _tg().m_hashrate_tage()
    heute_iso = heute.isoformat()
    hab = sorted(d for d in tage if d < heute_iso)
    if len(hab) < HASH_FENSTER:
        raise Abbruch("hashrate, nur %d tage mit wert" % len(hab))
    letzt = hab[-1]
    von = dt.date.fromisoformat(letzt) - dt.timedelta(days=HASH_REIHE_TAGE - 1)
    reihe = []
    for k in range(HASH_REIHE_TAGE):
        d = (von + dt.timedelta(days=k)).isoformat()
        reihe.append([d, round(tage[d] / 1000.0, 6) if d in tage else None])
    fenster = [p for p in reihe if p[1] is not None][-HASH_FENSTER:]
    frueh = [p for p in reihe if p[1] is not None][:HASH_FENSTER]
    hoch = max(fenster, key=lambda p: p[1])
    return {"stichtag": letzt, "mittel": statistics.mean(p[1] for p in fenster),
            "von": fenster[0][0], "bis": fenster[-1][0],
            "hoch": hoch[1], "hoch_tag": hoch[0],
            "frueh_mittel": statistics.mean(p[1] for p in frueh),
            "frueh_von": frueh[0][0], "reihe": reihe}


def z_covenants(heute):
    """Covenant-Ausgaenge, erzeugt seit Toccata und noch unverbraucht, aus
    unserem Tageslog."""
    c = _json(REPO / "data" / "covenants-log.json")
    seit = c["toccata_aktiv_seit"]
    tage = [t for t in c["tage"] if t["datum"] >= seit and t.get("outputs_created") is not None]
    if not tage:
        raise Abbruch("covenants, keine tage ab %s im log" % seit)
    reihe, summe = [], 0
    for t in tage:
        summe += t["outputs_created"]
        reihe.append([t["datum"], summe])
    letzt = tage[-1]
    return {"stichtag": letzt["datum"], "seit": seit, "erzeugt": summe,
            "unverbraucht": letzt["utxo_count"], "reihe": reihe}


ZAHLEN = (("entityx", z_entityx), ("boersen", z_boersen), ("unbewegt", z_unbewegt),
          ("halter", z_halter), ("senkung", z_senkung), ("gebuehren", z_gebuehren),
          ("hashrate", z_hashrate), ("covenants", z_covenants))


def probe(heute):
    """Alle acht Zahlen holen. Faellt eine aus, bricht der Lauf ab und nennt
    sie beim Namen."""
    aus = {"gebaut_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "stand": heute.isoformat(), "zahlen": {}}
    for name, f in ZAHLEN:
        try:
            aus["zahlen"][name] = f(heute)
        except Abbruch:
            raise
        except Exception as exc:                   # noqa: BLE001
            raise Abbruch("%s, %s: %s" % (name, type(exc).__name__, exc))
    return aus


def frische_pruefen(p, heute, frist=FRIST_TAGE):
    """Jeder Stichtag hoechstens frist Tage alt, sonst Abbruch mit Namen."""
    alt = []
    for name, _ in ZAHLEN:
        z = p["zahlen"].get(name)
        if not z:
            alt.append("%s fehlt ganz" % name)
            continue
        a = alter(z["stichtag"], heute)
        if a > frist:
            alt.append("%s, stichtag %s ist %d tage alt" % (name, z["stichtag"], a))
    extra = p["zahlen"].get("entityx", {}).get("umlauf_stichtag")
    if extra and alter(extra, heute) > frist:
        alt.append("entityx umlauf, stichtag %s ist %d tage alt"
                   % (extra, alter(extra, heute)))
    if alt:
        raise Abbruch("zu alt oder fehlend, frist %d tage: %s" % (frist, "; ".join(alt)))
    return True


# ----------------------------------------------------------------- diagramme
#
# Geometrie und Farben wie in Fassung 2. Was dort als Zahl im Quelltext
# stand, kommt hier aus der Probe: die Achsen aus achse(), die Quadratzahl
# aus dem Verhaeltnis, das Mittel aus der Reihe.

W = 952                               # Innenbreite der Seite


def svg(h, body):
    return ('<svg viewBox="0 0 %d %d" preserveAspectRatio="xMidYMid meet" '
            'xmlns="http://www.w3.org/2000/svg">%s</svg>' % (W, h, body))


def txt(x, y, s, size=30, fill=INK2, anchor="start", weight=500, fam="Plex"):
    return ('<text x="%s" y="%s" font-family="%s" font-size="%s" font-weight="%s" '
            'fill="%s" text-anchor="%s">%s</text>' % (x, y, fam, size, weight, fill, anchor, s))


def grund(x, y, s, size, anchor="start", rand=8):
    """Eine Flaeche in der Grundfarbe unter einer Beschriftung, grob so breit
    wie der Text (Plex, etwa 0.6 em je Zeichen)."""
    w = 0.6 * size * len(s) + 2 * rand
    x0 = x - rand if anchor == "start" else (x - w + rand if anchor == "end" else x - w / 2)
    return ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="6" fill="%s"/>'
            % (x0, y - size * 0.95, w, size * 1.3, BG))


def g_coins(eins_von):
    """Ein Kreis je Anteil, der erste leuchtet. eins_von kommt aus 100/pct."""
    n, cols, r, gap = eins_von, 9, 38, 22
    out = []
    x0 = (W - (cols * 2 * r + (cols - 1) * gap)) / 2 + r
    for i in range(n):
        cx = x0 + (i % cols) * (2 * r + gap)
        cy = 50 + (i // cols) * (2 * r + 30)
        if i == 0:
            out.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (cx, cy, r, ACC))
            out.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" '
                       'stroke-width="3" opacity=".45"/>' % (cx, cy, r - 12, BG))
        else:
            out.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" '
                       'stroke-width="3"/>' % (cx, cy, r - 1.5, SURF, LINE))
    out.append(txt(x0 - r, 290, "one coin lit = the share of all KAS in this one wallet", 30, INK3))
    return svg(310, "".join(out))


def line_chart(pts, h, ymin, ymax, labfmt, start_lab, end_lab, xlabels,
               start_below=False, mean=None):
    """pts: Liste (i, wert oder None), x gleichmaessig verteilt."""
    pl, pr, pt, pb = 8, 150, 40, 56
    n = len(pts)
    def X(i):
        return pl + (W - pl - pr) * i / (n - 1)
    def Y(v):
        return pt + (h - pt - pb) * (1 - (v - ymin) / (ymax - ymin))
    out = []
    for gv in [ymin + (ymax - ymin) * k / 3 for k in range(4)]:
        out.append('<line x1="%s" x2="%s" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>'
                   % (pl, W - pr + 20, Y(gv), Y(gv), LINE))
        if mean and abs(Y(gv) - Y(mean[0])) < 30:
            continue                  # die beschriftung "mean" steht dort
        out.append(txt(W - pr + 32, Y(gv) + 10, labfmt(gv), 26, INK3, weight=400, fam="PlexMono"))
    segs, cur = [], []
    for i, v in pts:
        if v is None:
            if cur:
                segs.append(cur)
                cur = []
        else:
            cur.append((X(i), Y(v)))
    if cur:
        segs.append(cur)
    if not segs:
        raise Abbruch("diagramm ohne einen einzigen wert")
    allp = [p for sg in segs for p in sg]
    d_all = "M" + " L".join("%.1f %.1f" % (x, y) for x, y in allp)
    out.append('<path d="%s L%.1f %s L%.1f %s Z" fill="%s" opacity=".10"/>'
               % (d_all, allp[-1][0], h - pb, allp[0][0], h - pb, ACC))
    for a, b in zip(segs, segs[1:]):
        (x1, y1), (x2, y2) = a[-1], b[0]
        out.append('<path d="M%.1f %.1f L%.1f %.1f" fill="none" stroke="%s" stroke-width="3" '
                   'stroke-dasharray="4 8" stroke-linecap="round" opacity=".7"/>'
                   % (x1, y1, x2, y2, ACC))
        out.append(txt((x1 + x2) / 2, min(y1, y2) - 18, "no reading", 22, INK3,
                       "middle", 400, "PlexMono"))
    for sgm in segs:
        if len(sgm) > 1:
            d = "M" + " L".join("%.1f %.1f" % (x, y) for x, y in sgm)
            out.append('<path d="%s" fill="none" stroke="%s" stroke-width="4" '
                       'stroke-linejoin="round" stroke-linecap="round"/>' % (d, ACC))
    if mean:
        mv, mi = mean
        out.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="3" '
                   'stroke-dasharray="2 7" stroke-linecap="round"/>'
                   % (X(mi), W - pr + 24, Y(mv), Y(mv), INK))
        out.append(txt(W - pr + 32, Y(mv) + 10, "mean %.0f" % mv, 26, INK, "start", 600, "PlexMono"))
    fx, fy = segs[0][0]
    lx, ly = segs[-1][-1]
    out.append('<circle cx="%.1f" cy="%.1f" r="8" fill="%s" stroke="%s" stroke-width="3"/>'
               % (fx, fy, BG, INK2))
    out.append('<circle cx="%.1f" cy="%.1f" r="11" fill="%s" stroke="%s" stroke-width="4"/>'
               % (lx, ly, ACC, BG))
    # anfangs- und endmarke stehen an der linie. mit echten daten laeuft die
    # teal-linie sonst unter der schrift durch, 1.4:1 statt 7:1 (probelauf
    # 28.10.2026). eine flaeche in der grundfarbe darunter haelt den kontrast.
    # die marke weicht der linie aus: ueber (oder unter) jedem punkt, der
    # unter ihrer breite liegt, damit weder die schrift auf der linie steht
    # noch die flaeche einen wert verdeckt
    def frei(x0, x1, y, oben, size):
        unter = [py for px, py in allp if x0 - 8 <= px <= x1 + 8]
        if oben:
            return max(pt + size, min([y] + [py - 18 for py in unter]))
        return min(h - pb - 6, max([y] + [py + size + 12 for py in unter]))
    sw, ew = 0.6 * 28 * len(start_lab), 0.6 * 30 * len(end_lab)
    sy = frei(fx + 4, fx + 4 + sw, fy + (44 if start_below else -22), not start_below, 28)
    ey = frei(lx - 6 - ew, lx - 6, ly - 24, True, 30)
    out.append(grund(fx + 4, sy, start_lab, 28))
    out.append(txt(fx + 4, sy, start_lab, 28, INK2))
    out.append(grund(lx - 6, ey, end_lab, 30, "end"))
    out.append(txt(lx - 6, ey, end_lab, 30, INK, "end", 600))
    for i, s in xlabels:
        out.append(txt(X(i), h - 12, s, 26, INK3,
                       "middle" if 0 < i < n - 1 else ("start" if i == 0 else "end"),
                       400, "PlexMono"))
    return svg(h, "".join(out))


def xmarken(tage, n=3):
    """Erste, mittlere und letzte Marke einer Tagesreihe."""
    k = len(tage) - 1
    stellen = sorted({0, round(k / 2), k}) if n == 3 else sorted({0, k})
    return [(i, tag_kurz(tage[i])) for i in stellen]


def g_boersen(z):
    pct = [p[2] for p in z["reihe"]]
    lo, hi = achse(pct)
    tage = [p[0] for p in z["reihe"]]
    return line_chart(list(enumerate(pct)), 360, lo, hi, lambda v: "%.1f%%" % v,
                      "%.1f%% · %s" % (pct[0], tag_kurz(tage[0])), "%.1f%%" % pct[-1],
                      xmarken(tage))


def g_unbewegt(z):
    a, b = z["p2"], z["p1"] - z["p2"]
    c = 100 - z["p1"]
    x, out, H = 0, [], 96
    segs = [(a, ACC, "%.1f%%" % a, "2+ years"),
            (b, ACCD, "%.1f%%" % b, "1 to 2 yrs"),
            (c, SURF, "%.1f%%" % c, "moved this year")]
    for i, (p, col, lab, cap) in enumerate(segs):
        w = W * p / 100 - (4 if i < 2 else 0)
        out.append('<rect x="%.1f" y="40" width="%.1f" height="%s" rx="6" fill="%s" '
                   'stroke="%s" stroke-width="2"/>'
                   % (x, w, H, col, LINE if col == SURF else col))
        out.append(txt(x + 4, 200, lab, 44, INK if i < 2 else INK2, weight=600, fam="Archivo"))
        out.append(txt(x + 4, 244, cap, 28, INK3))
        x += W * p / 100
    hx = W * z["p1"] / 100
    out.append('<line x1="%.1f" x2="%.1f" y1="22" y2="152" stroke="%s" stroke-width="3" '
               'stroke-dasharray="6 6"/>' % (hx, hx, INK))
    out.append(txt(hx, 18, "half", 26, INK, "middle", 600))
    return svg(270, "".join(out))


def g_trichter(z):
    data = [("0.01 KAS or more", z["k001"]), ("1 KAS or more", z["k1"]),
            ("100 KAS or more", z["k100"])]
    out, mx = [], data[0][1]
    for i, (lab, v) in enumerate(data):
        y = 20 + i * 92
        w = (W - 260) * v / mx
        letzt = i == len(data) - 1
        out.append('<rect x="0" y="%s" width="%.1f" height="64" rx="6" fill="%s"/>'
                   % (y, w, ACC if letzt else ACCF))
        # INK auf ACCF 11:1, auf ACCD waeren es nur 5.8:1 (Grafik-Regel 7:1)
        out.append(txt(20, y + 43, lab, 30, BG if letzt else INK, weight=600))
        out.append(txt(w + 20, y + 44, fmt(v), 34, INK if letzt else INK2, weight=600, fam="PlexMono"))
    return svg(300, "".join(out))


def g_stufen(z):
    vals = [z["jetzt"]] + [s[1] for s in z["stufen"]]
    n, H, pb = len(vals), 330, 50
    # ein Prozent Luft, dann auf das naechste Zehntel: 2.060172 -> 2.1, wie
    # in Fassung 2, und ein Reward von glatt 2.0 klebt nicht am Rand
    obergrenze = math.ceil(max(vals) * 1.01 * 10) / 10
    bw = W / n
    hoch = H - pb - 50
    def hy(v):
        return H - pb - hoch * v / obergrenze
    out = []
    for i, v in enumerate(vals):
        col = INK2 if i == 0 else (ACC if i == 1 else ACCF)
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="4" fill="%s"/>'
                   % (i * bw + 3, hy(v), bw - 6, hoch * v / obergrenze, col))
    # Ben, 28.10.2026: "until <tag der senkung>" statt "now"
    out.append(txt(2, hy(z["jetzt"]) - 14, "%.2f until %s" % (z["jetzt"], tag_kurz(z["zeit_utc"])),
                   28, INK2, weight=600))
    out.append(txt(2 * bw + 11, hy(z["naechste"]) + 34,
                   "%.2f on %s" % (z["naechste"], tag_kurz(z["zeit_utc"])), 30, INK, weight=600))
    # die stufe in einem jahr und die letzte im fenster, als anker
    for k, anchor in ((11, "middle"), (len(z["stufen"]) - 1, "end")):
        s = z["stufen"][k]
        x = (k + 1) * bw + bw / 2 if anchor == "middle" else W - 2
        out.append(txt(x, hy(s[1]) - 14, "%.2f · %s %s" % (
            s[1], MONATE[int(s[0][5:7]) - 1], s[0][:4]), 26, INK, anchor))   # steht auf ACCF, 11:1
    out.append(txt(2, H - 12, "KAS per block · one bar per monthly step", 26, INK3,
                   weight=400, fam="PlexMono"))
    return svg(H, "".join(out))


def g_raster(verhaeltnis):
    """Ein Quadrat je Vielfachem, das letzte leuchtet: die Gebuehren."""
    cols, sz, gp = 46, 15, 4
    teile = round(verhaeltnis)
    n = teile + 1
    out = []
    w = cols * (sz + gp) - gp
    x0 = (W - w) / 2
    for i in range(n):
        x = x0 + (i % cols) * (sz + gp)
        y = (i // cols) * (sz + gp)
        out.append('<rect x="%.1f" y="%s" width="%s" height="%s" rx="3" fill="%s"/>'
                   % (x, y, sz, sz, ACC if i == n - 1 else ACCF))
    hy = math.ceil(n / cols) * (sz + gp) + 34
    out.append(txt(x0, hy, "%s squares new coins" % fmt(teile), 28, INK2))
    out.append(txt(x0 + w, hy, "1 bright square fees", 28, INK, "end", 600))
    return svg(hy + 10, "".join(out))


def g_hashrate(z):
    werte = [p[1] for p in z["reihe"]]
    lo, hi = achse(werte)
    tage = [p[0] for p in z["reihe"]]
    mi = tage.index(z["von"])
    da = list(enumerate(werte))
    erst = next(p for p in z["reihe"] if p[1] is not None)
    letzt = next(p for p in reversed(z["reihe"]) if p[1] is not None)
    return line_chart(da, 360, lo, hi, lambda v: "%.0f" % v,
                      "%.0f · %s" % (erst[1], tag_kurz(erst[0])),
                      "%.0f on %s" % (letzt[1], tag_kurz(letzt[0])),
                      xmarken(tage), start_below=True, mean=(z["mittel"], mi))


def g_covenants(z):
    werte = [p[1] for p in z["reihe"]]
    lo, hi = achse_kumuliert(werte)
    tage = [p[0] for p in z["reihe"]]
    return line_chart(list(enumerate(werte)), 360, lo, hi, lambda v: "%.0fk" % (v / 1000),
                      tag_kurz(tage[0]), fmt(werte[-1]), xmarken(tage))


# ------------------------------------------------------------------- texte
#
# Jeder Satz steht hier so, wie Ben ihn in Fassung 2 freigegeben hat. Was
# sich monatlich aendert, ist eine Einsetzung. Wo ein Satz nur mit einem
# bestimmten Vorzeichen stimmt ("slipped", "added", "more"), waehlt eine
# kleine Funktion das Wort, statt es stehen zu lassen und falsch zu werden.

def richtung(delta, faellt, steigt, flach, schwelle=0.0):
    if abs(delta) <= schwelle:
        return flach
    return steigt if delta > 0 else faellt


def monatsteil(d):
    """"mid august" aus 2026-08-13."""
    d = dt.date.fromisoformat(str(d)[:10])
    teil = "early" if d.day <= 10 else ("mid" if d.day <= 20 else "late")
    return "%s %s" % (teil, MONATE_LANG[d.month - 1])


def vorzeichen(n):
    return "%s%s" % ("+" if n > 0 else ("−" if n < 0 else ""), fmt(abs(n)))


def fast(n, stufe=100000):
    """"almost 300,000" oder "just over 300,000"."""
    ziel = round(n / stufe) * stufe
    return "%s %s" % ("almost" if n < ziel else "just over", fmt(ziel))


def karten(p):
    """Die acht Seiten als dicts, Zahlen aus der Probe eingesetzt."""
    z = p["zahlen"]
    heute = dt.date.fromisoformat(p["stand"])

    ex = z["entityx"]
    ex_pct = 100.0 * ex["balance"] / ex["umlauf"]
    ex_eins_von = round(100.0 / ex_pct)

    bo = z["boersen"]
    bo_erst = bo["reihe"][0]
    bo_eins_von = round(100.0 / bo["pct"])

    ub = z["unbewegt"]

    ha = z["halter"]
    ha_schwelle = max(1, round(abs(ha["k100"]) * 0.01))

    se = z["senkung"]
    se_zeit = dt.datetime.fromisoformat(se["zeit_utc"].replace("Z", "+00:00"))
    se_tage = (se_zeit.date() - heute).days

    ge = z["gebuehren"]
    ge_x = ge["emission"] / ge["fees"]

    hs = z["hashrate"]
    hs_delta = 100.0 * (hs["mittel"] / hs["frueh_mittel"] - 1)
    hs_sprung = max(abs(100.0 * (b[1] / a[1] - 1))
                    for a, b in zip(hs["reihe"], hs["reihe"][1:])
                    if a[1] and b[1])

    co = z["covenants"]

    return [
        dict(n=1, tag="whales", q="how much does the biggest wallet hold?",
             big="%.1f%%" % ex_pct, unit="of all KAS in circulation",
             date="%s KAS · %s" % (fmt(ex["balance"]), tag_lang(ex["stichtag"])),
             chart=g_coins(ex_eins_von),
             plain="one wallet holds about one in every %d KAS. explorers call it entity x. "
                   "it has never been named." % ex_eins_von,
             nerd="its address is public. we check it several times a day. last move of %s KAS "
                  "or more, %s, %s KAS left." % (fmt(EX_MELDESCHWELLE), tag_lang(ex["abfluss_tag"]),
                                                 fmt(ex["abfluss_kas"])),
             signal="large amounts leaving it, and where they land.",
             src="counted by kaspa pulse · supply as of %s" % tag_lang(ex["umlauf_stichtag"])),
        dict(n=2, tag="whales", q="how much KAS sits on exchanges?",
             big="%.1f%%" % bo["pct"], unit="of all KAS, about one in %s" % wort(bo_eins_von),
             date="%s KAS · %s" % (fmt(bo["kas"]), tag_lang(bo["stichtag"])),
             chart=g_boersen(bo),
             plain="coins on exchanges can be sold fast. that share has %s from %.1f%% in %s to "
                   "%.1f%% on %s." % (richtung(bo["pct"] - bo_erst[2], "slipped", "risen",
                                               "barely moved", 0.05),
                                      bo_erst[2], MONATE_LANG[int(bo_erst[0][5:7]) - 1], bo["pct"],
                                      tag_kurz(bo["stichtag"])),
             nerd="share of all KAS in wallets labelled as exchanges. one snapshot at midnight "
                  "utc, logged by us every week since %s. a falling share means coins left "
                  "exchange wallets." % MONATE_LANG[int(bo_erst[0][5:7]) - 1],
             signal="rising share, more coins within reach of a sale, often read as selling "
                    "pressure. falling share, coins leave for private wallets.",
             src="source kaspalytics · checked by kaspa pulse"),
        dict(n=3, tag="holders", q="how much KAS has not moved in a year?",
             big="%.1f%%" % ub["p1"], unit="of all KAS, untouched for 1 year or more",
             date="%s · %.1f%% untouched for 2 years" % (tag_lang(ub["stichtag"]), ub["p2"]),
             chart=g_unbewegt(ub),
             plain="half of all KAS has not moved in a year. a quarter has not moved in two.",
             nerd="the age of each coin comes from the daa score of its last move. logged by us "
                  "every week since %s, the share sat between %.1f%% and %.1f%%."
                  % (MONATE_LANG[int(ub["wochen_von"][5:7]) - 1], ub["wochen_min"], ub["wochen_max"]),
             signal="a sudden drop. that is old coins waking up.",
             src="source kaspalytics · checked by kaspa pulse"),
        dict(n=4, tag="holders", q="how many wallets hold a real stake?",
             big=fmt(ha["k100"]), unit="addresses with 100 KAS or more",
             date="%s · %s in 7 days · %s in 30 · %s in 90" % (
                 tag_lang(ha["stichtag"]), vorzeichen(ha["d7"]), vorzeichen(ha["d30"]),
                 vorzeichen(ha["d90"])),
             chart=g_trichter(ha),
             plain="%s wallets hold 100 KAS or more. the last month %s about %s, the last 90 days "
                   "are %s %s." % (
                       fast(ha["k100"]),
                       richtung(ha["d30"], "lost", "added", "held", 0),
                       fmt(round(abs(ha["d30"]), -3)),
                       richtung(abs(ha["d90"]) - ha_schwelle, "slightly", "clearly", "slightly"),
                       richtung(ha["d90"], "negative", "positive", "flat", 0)),
             nerd="one exchange address can hold thousands of users, one person can hold many "
                  "addresses. %.1f million addresses hold something, almost all of it dust below "
                  "0.01 KAS." % (ha["alle"] / 1e6),
             signal="the 30 day direction of the 100+ line.",
             src="source kaspalytics · checked by kaspa pulse"),
        dict(n=5, tag="miners", q="when do miners get paid less again?",
             big=tag_kurz(se_zeit.date()),
             unit="next block reward cut, %s utc" % se_zeit.strftime("%H:%M"),
             date="%.2f to %.2f KAS per block · %d days from %s" % (
                 se["jetzt"], se["naechste"], se_tage, tag_kurz(heute)),
             chart=g_stufen(se),
             plain="every month kaspa pays a little less per block. twelve steps halve the "
                   "reward. the next one is on %d %s." % (se_zeit.day,
                                                          MONATE_LANG[se_zeit.month - 1]),
             nerd="factor 0.5 to the power 1/12 per step, one step every 365.25 / 12 days, 10 "
                  "blocks per second. the cut lands on a block score, so the exact minute drifts "
                  "a little.",
             signal="whether fees grow while the reward shrinks. see number 6.",
             src="from the emission schedule, counted by kaspa pulse"),
        dict(n=6, tag="miners", q="what actually pays the miners?",
             big="%sx" % fmt(ge_x), unit="more KAS from new coins than from fees",
             date="%d days, %s to %s" % (ge["tage"], tag_kurz(ge["von"]), tag_lang(ge["bis"])),
             chart=g_raster(ge_x),
             plain="for every 1 KAS miners earned in fees, they got %s KAS in new coins. "
                   "the network is paid by issuance." % fmt(ge_x),
             nerd="%s KAS new coins against %s KAS fees, the same %d full utc days for both. a "
                  "day without a fee value drops out of both sides." % (
                      mio(ge["emission"]), fmt(ge["fees"]), ge["tage"]),
             signal="the ratio falling because fees rise.",
             src="fees source kaspalytics · issuance by kaspa pulse"),
        dict(n=7, tag="security", q="how much computing power guards kaspa?",
             big="%.0f" % hs["mittel"], unit="PH/s, mean of the last %d days" % HASH_FENSTER,
             date="%s · single day %.0f on %s" % (
                 spanne(hs["von"], hs["bis"]), hs["hoch"], tag_kurz(hs["hoch_tag"])),
             chart=g_hashrate(hs),
             plain="%.0f quadrillion guesses every second protect the chain. about %.0f%% %s than "
                   "in %s." % (hs["mittel"], abs(hs_delta),
                               richtung(hs_delta, "less", "more", "the same as"),
                               monatsteil(hs["frueh_von"])),
             nerd="one reading a day from api.kaspa.org, no smoothing. single days jump by %.0f%%, "
                  "so we show the %d day mean. gaps are days without a reading." % (
                      round(hs_sprung, -1), HASH_FENSTER),
             signal="a drop that lasts for weeks.",
             src="data api.kaspa.org · logged daily by kaspa pulse"),
        dict(n=8, tag="adoption", q="are kaspa smart contracts being used?",
             big=fmt(co["erzeugt"]),
             unit="covenant outputs created since %s" % tag_monat(co["seit"]),
             date="%s · %s still unspent" % (tag_lang(co["stichtag"]), fmt(co["unverbraucht"])),
             chart=g_covenants(co),
             plain="since the toccata upgrade launched on %s, covenants have been created %s "
                   "times. they come in waves." % (tag_monat(co["seit"]), fmt(co["erzeugt"])),
             nerd="covenant outputs created per day, summed. most are spent again soon, tests and "
                  "bots count too.",
             signal="the unspent stock. it grows steady, the traffic comes in waves.",
             src="source kaspalytics · logged daily by kaspa pulse"),
    ]


ZAHLWORT = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
            8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}


def wort(n):
    """"one in seven" statt "one in 7"."""
    return ZAHLWORT.get(n, fmt(n))


# Bens Regel (16.10.2026): Kaspalytics-Reihen tragen immer "source kaspalytics",
# "counted" steht nur bei eigenen Zaehlungen. Das Deckblatt nennt die Quelle
# deshalb in der Zeile selbst, nicht erst auf der Karte.
KL = " · source kaspalytics"


def uebersicht(p, k):
    """Die acht Zeilen auf dem Deckblatt, in derselben Reihenfolge."""
    z = p["zahlen"]
    se_zeit = dt.datetime.fromisoformat(z["senkung"]["zeit_utc"].replace("Z", "+00:00"))
    return [
        ("biggest wallet, share of supply", "entity x · %s"
         % tag_kurz(z["entityx"]["stichtag"]), k[0]["big"]),
        ("KAS on exchanges", tag_kurz(z["boersen"]["stichtag"]) + KL, k[1]["big"]),
        ("untouched for a year or more", tag_kurz(z["unbewegt"]["stichtag"]) + KL, k[2]["big"]),
        ("addresses with 100 KAS or more", tag_kurz(z["halter"]["stichtag"]) + KL, k[3]["big"]),
        ("next block reward cut", "%s utc" % se_zeit.strftime("%H:%M"), k[4]["big"]),
        ("new coins vs fees, %d days" % z["gebuehren"]["tage"],
         "to %s · fees source kaspalytics" % tag_kurz(z["gebuehren"]["bis"]), k[5]["big"]),
        ("hashrate, %d day mean" % HASH_FENSTER,
         spanne(z["hashrate"]["von"], z["hashrate"]["bis"], lang=False),
         "%s PH/s" % k[6]["big"]),
        ("covenant outputs since %s" % tag_monat(z["covenants"]["seit"]),
         tag_kurz(z["covenants"]["stichtag"]) + KL, k[7]["big"]),
    ]


# -------------------------------------------------------------------- seite

SCHNITTE = (("Archivo", "archivo-latin-600-normal.woff2", 600),
            ("Archivo", "archivo-latin-800-normal.woff2", 800),
            ("Archivo", "archivo-latin-900-normal.woff2", 900),
            ("Plex", "ibm-plex-sans-latin-400-normal.woff2", 400),
            ("Plex", "ibm-plex-sans-latin-500-normal.woff2", 500),
            ("Plex", "ibm-plex-sans-latin-600-normal.woff2", 600),
            ("PlexMono", "ibm-plex-mono-latin-400-normal.woff2", 400),
            ("PlexMono", "ibm-plex-mono-latin-500-normal.woff2", 500))


def schriften(ordner=SCHRIFTEN):
    """Die Schnitte aus dem Repo, als data-url eingebettet. Nichts aus einem
    CDN und nichts aus node_modules, siehe graphics/fonts/README.md."""
    aus = []
    for fam, datei, gewicht in SCHNITTE:
        p = Path(ordner) / datei
        if not p.exists():
            raise Abbruch("schrift fehlt, %s" % p)
        b = base64.b64encode(p.read_bytes()).decode()
        aus.append("@font-face{font-family:'%s';src:url(data:font/woff2;base64,%s) "
                   "format('woff2');font-weight:%d;font-style:normal;font-display:block}"
                   % (fam, b, gewicht))
    return "".join(aus)


def marke_css():
    """Die Wortmarke steht in scripts/wortmarke.py. Groesse und Sperrung
    bleiben beim Kopf (.mark setzt sie in em), nur Schnitt und Farben kommen
    von dort. INK und ACC sind hier schon #F2F5F4 und #49EACB, also genau
    die Marke (Ben, 21.10.2026)."""
    import wortmarke
    return wortmarke.css("wm", groesse=None, sperrung=None, kaspa=INK, pulse=ACC)


def css(fonts):
    return """
%s
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:%s}
body{font-family:Plex,sans-serif;color:%s;-webkit-font-smoothing:antialiased}
.pg{width:%dpx;height:%dpx;position:relative;overflow:hidden;background:%s;padding:56px 64px 0;page-break-after:always;display:flex;flex-direction:column}
.pg:before{content:"";position:absolute;inset:0;background:radial-gradient(900px 520px at 88%% -8%%,rgba(73,234,203,.09),transparent 70%%);pointer-events:none}
.top{display:flex;justify-content:space-between;align-items:center;font-family:PlexMono;font-size:26px;letter-spacing:.14em;text-transform:uppercase;color:%s;padding-bottom:22px;border-bottom:2px solid %s}
.mark{display:flex;align-items:center;gap:14px;color:%s;font-family:Archivo;font-weight:800;letter-spacing:.2em}
.mark i{width:16px;height:16px;border-radius:50%%;background:%s;box-shadow:0 0 0 6px rgba(73,234,203,.15)}
.tag{margin-top:32px;font-family:PlexMono;font-size:26px;letter-spacing:.18em;text-transform:uppercase;color:%s}
.q{margin-top:10px;font-family:Archivo;font-weight:800;font-size:46px;line-height:1.08;letter-spacing:-.01em;text-wrap:balance}
.big{margin-top:20px;display:flex;align-items:baseline;gap:26px}
.big b{font-family:Archivo;font-weight:900;font-size:150px;line-height:.86;letter-spacing:-.035em;font-variant-numeric:tabular-nums}
.big span{font-size:34px;color:%s;max-width:360px;line-height:1.2;font-weight:500}
.date{margin-top:16px;font-family:PlexMono;font-size:28px;color:%s}
.chart{margin-top:22px;flex:1 1 0;min-height:0;display:flex;align-items:center}
.chart svg{width:100%%;height:100%%;max-height:420px}
.plain{margin-top:22px;font-size:34px;line-height:1.28;font-weight:500;text-wrap:pretty}
.duo{margin-top:22px;display:grid;grid-template-columns:1.35fr 1fr;gap:22px}
.box{background:%s;border:2px solid %s;border-radius:14px;padding:18px 20px}
.box h4{font-family:PlexMono;font-weight:500;font-size:24px;letter-spacing:.16em;text-transform:uppercase;color:%s;margin-bottom:10px}
.box p{font-size:25px;line-height:1.34;color:%s}
.box.nerd p{font-family:PlexMono;font-size:22.5px;line-height:1.42}
.box.sig{border-color:%s}
.box.sig h4{color:%s}
.box.sig p{color:%s}
.foot{margin:22px -64px 0;padding:20px 64px 28px;border-top:2px solid %s;display:flex;justify-content:space-between;font-family:PlexMono;font-size:24px;color:%s}
.foot b{color:%s;font-weight:500}
/* cover */
.cv h1{margin-top:40px;font-family:Archivo;font-weight:900;font-size:96px;line-height:.92;letter-spacing:-.035em;text-wrap:balance}
.cv h1 em{font-style:normal;color:%s}
.cv .sub{margin-top:22px;font-size:32px;color:%s;font-weight:500}
.list{margin-top:auto;margin-bottom:0;border-top:2px solid %s}
.row{display:grid;grid-template-columns:56px 1fr auto;align-items:baseline;gap:16px;padding:9px 0;border-bottom:2px solid %s}
.row .i{font-family:PlexMono;font-size:24px;color:%s}
.row .t{font-size:28px;font-weight:500;color:%s}
.row .t small{display:block;font-size:22px;color:%s;font-family:PlexMono;margin-top:2px}
.row .v{font-family:Archivo;font-weight:800;font-size:40px;font-variant-numeric:tabular-nums;text-align:right}
/* back */
.bk h2{margin-top:36px;font-family:Archivo;font-weight:900;font-size:80px;line-height:.95;letter-spacing:-.03em}
.rules{margin-top:34px;display:grid;gap:12px}
.rule{display:grid;grid-template-columns:58px 1fr;gap:14px;font-size:30px;line-height:1.28}
.rule i{font-style:normal;font-family:PlexMono;font-size:26px;color:%s;padding-top:6px}
.rule span b{font-weight:600}
.rule span{color:%s}
.subcta{display:block;text-decoration:none;margin-top:auto;background:%s;color:%s;border-radius:22px;padding:34px 36px 30px}
.sub-k{font-family:PlexMono;font-size:24px;letter-spacing:.16em;text-transform:uppercase;opacity:.75}
.sub-h{margin-top:12px;font-family:Archivo;font-weight:800;font-size:46px;line-height:1.08;letter-spacing:-.01em;text-wrap:balance}
.sub-b{margin-top:24px;display:flex;flex-direction:column;gap:10px}
.sub-b span{display:inline-block;align-self:flex-start;background:%s;color:%s;font-family:Archivo;font-weight:800;font-size:34px;padding:16px 26px;border-radius:12px}
.sub-b i{font-style:normal;font-family:PlexMono;font-size:23px;opacity:.8}
.links{margin-top:20px;display:grid;grid-template-columns:1fr 1fr;gap:10px}
.links a{text-decoration:none;color:inherit}
.links>a,.links>div{border:2px solid %s;background:%s;border-radius:14px;padding:14px 18px;display:flex;flex-direction:column;gap:4px}
.links b{font-size:26px;font-weight:600;color:%s}
.links span,.links span a{font-family:PlexMono;font-size:22px;color:%s}
""" % (fonts, BG, INK, SEITE_PX[0], SEITE_PX[1], BG, INK3, LINE, INK, ACC, ACC, INK2, INK2,
       SURF, LINE, INK3, INK2, ACCD, ACC, INK, LINE, INK3, INK2, ACC, INK2, LINE, LINE,
       ACC, INK, INK3, ACC, INK2, ACC, BG, BG, ACC, LINE, SURF, INK, ACC) + marke_css()


def top(rechts):
    import wortmarke
    return ('<div class="top"><div class="mark"><i></i>%s</div><div>%s</div></div>'
            % (wortmarke.html("wm"), rechts))


def seite(c):
    return """<section class="pg">%s
<div class="tag">%s</div>
<div class="q">%s</div>
<div class="big"><b>%s</b><span>%s</span></div>
<div class="date">%s</div>
<div class="chart">%s</div>
<div class="plain">%s</div>
<div class="duo"><div class="box nerd"><h4>how to read it</h4><p>%s</p></div>
<div class="box sig"><h4>signal to watch</h4><p>%s</p></div></div>
<div class="foot"><span>%s</span><b>kaspapulse.com</b></div></section>""" % (
        top("%02d / 08" % c["n"]), c["tag"], c["q"], c["big"], c["unit"], c["date"],
        c["chart"], c["plain"], c["nerd"], c["signal"], c["src"])


def deckblatt(zeilen, marke):
    rws = "".join('<div class="row"><div class="i">%02d</div><div class="t">%s<small>%s</small>'
                  '</div><div class="v">%s</div></div>' % (i + 1, a, b, v)
                  for i, (a, b, v) in enumerate(zeilen))
    return """<section class="pg cv">%s
<h1>the 8 kaspa numbers <em>whales watch</em></h1>
<div class="sub">dated and sourced. updated every month.</div>
<div class="list">%s</div>
<div class="foot"><span>one number per page, with how to read it</span><b>kaspapulse.com</b>
</div></section>""" % (top(marke), rws)


def rueckseite(marke, utm):
    return """<section class="pg bk">%s
<h2>every number<br>has a date.</h2>
<div class="rules">
<div class="rule"><i>01</i><span><b style="color:%s">a date and a source on every number.</b> so you can check each one.</span></div>
<div class="rule"><i>02</i><span><b style="color:%s">sourced, not guessed.</b> what we count ourselves says counted, the rest names its source.</span></div>
<div class="rule"><i>03</i><span><b style="color:%s">plain words first.</b> the detail for the nerds right below.</span></div>
<div class="rule"><i>04</i><span><b style="color:%s">we keep the history.</b> logged by us, checked for breaks, sources named so you can check us.</span></div>
</div>
<a class="subcta" href="https://kaspapulse.com/?utm_source=cheatsheet&amp;utm_medium=pdf&amp;utm_campaign=%s#subscribe">
<div class="sub-k">got this forwarded?</div>
<div class="sub-h">get next month's edition first, plus the numbers that moved, every monday.</div>
<div class="sub-b"><span>subscribe free at kaspapulse.com</span><i>one short email a week · unsubscribe anytime</i></div>
</a>
<div class="links">
<a href="https://kaspapulse.com/?utm_source=cheatsheet&amp;utm_medium=pdf&amp;utm_campaign=%s"><b>the dashboard</b><span>kaspapulse.com</span></a>
<a href="https://discord.gg/h33JBhrPP7"><b>entity x alerts</b><span>discord, free</span></a>
<a href="https://www.youtube.com/channel/UCLheLoijZUZOE79vRtJtJ9Q"><b>explained weekly</b><span>youtube</span></a>
<div><b>one number a day</b><span><a href="https://x.com/gokugalax">x @gokugalax</a> · <a href="https://instagram.com/kaspapulse">ig @kaspapulse</a></span></div>
</div>
<div class="foot"><span>%s · not financial advice</span><b>kaspapulse.com</b></div></section>""" % (
        top("how we count"), INK, INK, INK, INK, utm, utm, marke)


def html(p, edition, fonts=None):
    k = karten(p)
    monat = dt.date.fromisoformat(p["stand"])
    marke = "edition %d · %s %d" % (edition, MONATE_LANG[monat.month - 1], monat.year)
    utm = "edition%d" % edition
    return ("<!doctype html><html><head><meta charset='utf-8'><title>%s</title><style>%s</style>"
            "</head><body>%s%s%s</body></html>" % (
                TITEL, css(fonts if fonts is not None else schriften()),
                deckblatt(uebersicht(p, k), marke), "".join(seite(c) for c in k),
                rueckseite(marke, utm)))


# --------------------------------------------------------------------- bau

def edition_log(pfad=LOG):
    try:
        return _json(pfad)
    except (OSError, ValueError):
        return {"editionen": []}


def naechste_edition(log, monat):
    """Ausgabe-Nummer fuer diesen Monat. Ein zweiter Lauf im selben Monat
    traegt dieselbe Nummer, sonst zaehlt es eine hoch."""
    eds = log.get("editionen", [])
    schon = [e for e in eds if e["monat"] == monat]
    if schon:
        return schon[-1]["n"]
    return max([e["n"] for e in eds], default=0) + 1


def rendern(seiten_html, ziel):
    """Chromium druckt die Seiten. width/height in px ergeben genau die
    MediaBox 810 x 1013.04 pt der veroeffentlichten Ausgabe."""
    from playwright.sync_api import sync_playwright
    launch = {}
    for c in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
              "/opt/pw-browsers/chromium/chrome-linux/chrome"):
        if os.path.exists(c):
            launch["executable_path"] = c
            break
    ziel = Path(ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    tmp = ziel.with_suffix(".html")
    tmp.write_text(seiten_html, encoding="utf-8")
    deck = ziel.with_name(ziel.stem + "-deckblatt.png")
    with sync_playwright() as p:
        b = p.chromium.launch(**launch)
        pg = b.new_page(viewport={"width": SEITE_PX[0], "height": SEITE_PX[1]},
                        device_scale_factor=1)
        pg.goto(tmp.resolve().as_uri())
        pg.wait_for_timeout(600)
        pg.pdf(path=str(ziel), width="%dpx" % SEITE_PX[0], height="%dpx" % SEITE_PX[1],
               print_background=True,
               margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        pg.locator("section.pg").first.screenshot(path=str(deck))
        pngs, kontrast = seiten_png(pg, ig_ordner(ziel))
        b.close()
    rendern.letzte = {"pngs": pngs, "kontrast": kontrast}
    return ziel, deck, tmp


def ig_ordner(pdf):
    return Path(pdf).with_name(Path(pdf).stem + "-instagram")


def seiten_png(pg, ordner):
    """Jede Seite einzeln als PNG 1080x1350 fuer das Instagram-Karussell
    (Ben, 28.10.2026), in der Reihenfolge des PDF. Dazu der Kontrast 7:1 je
    Seite, gemessen im fertigen Bild wie bei allen anderen Grafiken."""
    import hintergrund
    ordner.mkdir(parents=True, exist_ok=True)
    for alt in ordner.glob("seite-*.png"):
        alt.unlink()
    n = pg.locator("section.pg").count()
    pngs, kontrast = [], []
    for i in range(n):
        pg.evaluate("(i) => document.querySelectorAll('section.pg').forEach("
                    "(e, k) => e.style.display = (k === i ? 'flex' : 'none'))", i)
        pfad = ordner / ("seite-%02d.png" % (i + 1))
        pg.screenshot(path=str(pfad))
        pngs.append(pfad)
        kontrast += ["seite %d, %s" % (i + 1, v) for v in hintergrund.kontrast_verstoesse(pg)]
    pg.evaluate("() => document.querySelectorAll('section.pg').forEach(e => e.style.display = '')")
    return pngs, kontrast


def bauen(p, edition, ziel=None):
    ziel = Path(ziel) if ziel else (AUS / ("kaspa-pulse-cheat-sheet-edition-%d.pdf" % edition))
    return rendern(html(p, edition), ziel)


def festschreiben(p, edition, pdf, log=None, pfad=LOG):
    """Die Ausgabe in das Log eintragen und das Datei unter der Adresse der
    Webseite ersetzen. Nur hier, nie beim bloßen Bauen: ein Probelauf darf
    keine Nummer verbrauchen und die Seite nicht anfassen."""
    log = log if log is not None else edition_log(pfad)
    monat = p["stand"][:7]
    eds = [e for e in log.get("editionen", []) if e["monat"] != monat]
    eds.append({"n": edition, "monat": monat,
                "gebaut_utc": p["gebaut_utc"], "stand": p["stand"],
                "stichtage": {k: p["zahlen"][k]["stichtag"] for k, _ in ZAHLEN},
                "herkunft": "scripts/cheat_sheet.py"})
    log["editionen"] = sorted(eds, key=lambda e: e["monat"])
    Path(pfad).write_text(json.dumps(log, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    WEBSEITE.write_bytes(Path(pdf).read_bytes())
    whales_festschreiben(p, edition)
    return WEBSEITE


def whales_festschreiben(p, edition):
    """Die Landingpage /whales zeigt ab Edition 2 die 2 offenen
    Zahlen dieser Ausgabe (Ben, 29.10.2026). Sie geht mit dem PDF live, im
    selben Commit. Scheitert ihre Wache, bleibt die alte Seite stehen und das
    PDF geht trotzdem raus: die Meldung steht im Lauf und in #ops-log."""
    try:
        import whales_seite
        ziel = whales_seite.festschreiben(p, edition)
        print("whales-seite edition %d geschrieben, %s" % (edition, ziel))
        return ziel
    except (Exception, SystemExit) as exc:  # noqa: BLE001
        text = "whales-seite NICHT neu gebaut, die alte bleibt stehen. grund %s" % exc
        print(text)
        try:
            import ops_melden
            ops_melden.log(text, was="whales")
        except Exception:  # noqa: BLE001
            pass
        return None


# ---------------------------------------------------------------------- ops

def ops_text(p, edition, pdf, scharf):
    monat = dt.date.fromisoformat(p["stand"])
    zeilen = ["cheat sheet edition %d, %s %d, %d seiten, %s byte" % (
        edition, MONATE_LANG[monat.month - 1], monat.year, len(karten(p)) + 2,
        fmt(pdf.stat().st_size))]
    zeilen.append("nicht oeffentlich. bild 1 ist das deckblatt, die pdf haengt dran.")
    for name, _ in ZAHLEN:
        z = p["zahlen"][name]
        a = alter(z["stichtag"], monat)
        zeilen.append("  %-10s stichtag %s, %d %s alt"
                      % (name, z["stichtag"], a, "tag" if a == 1 else "tage"))
    zeilen.append("die datei der webseite ist %s" % (
        "ersetzt, CHEAT_SHEET_LIVE steht auf scharf" if scharf
        else "unveraendert. zum ersetzen die variable CHEAT_SHEET_LIVE auf scharf stellen"))
    return "\n".join(zeilen)


IG_CAPTION = ("the 8 kaspa numbers whales watch. edition %d, %s %d. every number dated, with its "
              "source. save it for later. the full cheat sheet arrives by email, link in bio. "
              "#kaspa #kas #blockdag")
WORKFLOW_URL = "https://github.com/neoalphavault-png/kaspa-pulse/actions/workflows/cheat-sheet.yml"
VARIABLEN_URL = "https://github.com/neoalphavault-png/kaspa-pulse/settings/variables/actions"


def ig_caption(p, edition):
    """Bens Caption vom 28.10.2026, ohne Engagement-Koeder. Edition und Monat
    kommen aus dem Lauf, sonst kein Wort anders."""
    monat = dt.date.fromisoformat(p["stand"])
    return IG_CAPTION % (edition, MONATE_LANG[monat.month - 1], monat.year)


def probe_lauf():
    """Ein Lauf von einem anderen Branch als main ist immer eine Probe: alles
    nach #ops-log, nichts zum Freigeben und nichts zum Posten nach
    #moderator-only. Lokal (ohne GITHUB_REF_NAME) gilt das nicht."""
    ref = os.environ.get("GITHUB_REF_NAME", "")
    return bool(ref) and ref != "main"


def schon_gemeldet(heute, holer=None):
    """Am 1. kommen zwei Laeufe zur selben Stunde, der c2-Takt und der Cron
    als Ersatz (im Winter trifft 08:00 UTC genau 09:00 Berlin). Ein Cron-Lauf
    meldet nicht, wenn heute schon ein Lauf dieses Workflows den Schritt
    "bauen und melden" gruen beendet hat. Ein Lauf von Hand meldet immer.
    Geht die Abfrage nicht, wird gemeldet: lieber doppelt als gar nicht."""
    if os.environ.get("GITHUB_EVENT_NAME") != "schedule":
        return None
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    selbst = os.environ.get("GITHUB_RUN_ID", "")
    if not repo:
        return None
    import urllib.request

    def holen(url):
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                                   "User-Agent": "kaspa-pulse-cheat-sheet"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    holen = holer or holen
    basis = "https://api.github.com/repos/%s/actions" % repo
    try:
        laeufe = holen("%s/workflows/cheat-sheet.yml/runs?created=%s&per_page=20"
                       % (basis, heute.isoformat()))["workflow_runs"]
        for r in laeufe:
            if str(r["id"]) == selbst or r.get("head_branch") != "main":
                continue
            for j in holen("%s/runs/%s/jobs" % (basis, r["id"]))["jobs"]:
                for st in j.get("steps") or []:
                    if st.get("name") == "bauen und melden" and st.get("conclusion") == "success":
                        return r["id"]
    except Exception as exc:  # noqa: BLE001
        print("abfrage der laeufe ging nicht (%s), es wird gemeldet" % type(exc).__name__)
    return None


def ops_schicken(text, dateien, scharf, ig=None):
    """Text, Deckblatt und PDF in einem Aufruf ueber scripts/ops_melden.py.
    Ersetzt der Lauf die Datei der Webseite, ist es eine Info nach #ops-log.
    Sonst entscheidet Ben, ob er die Edition freigibt, das ist eine Handlung
    und geht als "📤 VON HAND" nach #moderator-only.

    ig ist das Upload-Paket fuer das Instagram-Karussell, (pngs, caption,
    kontrast). Posten tut Ben von Hand, also immer "📤 VON HAND", in einer
    eigenen Nachricht mit den 10 Seiten. Verletzt eine Seite den Kontrast,
    geht kein Paket raus, nur die Liste nach #ops-log.

    Ein Probelauf (probe_lauf) schickt alles nach #ops-log."""
    import ops_melden
    probe = probe_lauf()
    if probe:
        text = ("PROBE vom branch %s, nicht freigeben, nicht posten.\n" % os.environ.get("GITHUB_REF_NAME", "")
                + text)
    if scharf or probe:
        ops_melden.log(text, dateien, "cheat-sheet")
    else:
        kopf = ops_melden.hand_text(
            "wenn du die edition freigibst", "GitHub",
            "1. variable CHEAT_SHEET_LIVE auf scharf stellen, 2. cheat-sheet mit veroeffentlichen=true "
            "starten. deckblatt und pdf haengen dran",
            VARIABLEN_URL + "\n" + WORKFLOW_URL)
        ops_melden.hand(kopf + "\n\n" + text, dateien, "cheat-sheet")
    if not ig:
        return
    pngs, caption, kontrast = ig
    if kontrast:
        ops_melden.log("cheat sheet, instagram-paket NICHT geschickt, kontrast unter 7:1\n"
                       + "\n".join(kontrast[:20]), was="cheat-sheet instagram")
        return
    paket = ("%d seiten in dieser reihenfolge als karussell hochladen, 1080x1350, ohne musik, "
             "caption kopieren\n```\n%s\n```" % (len(pngs), caption))
    if probe:
        ops_melden.log("PROBE, instagram-paket, nicht posten.\n" + paket,
                       [(x, "image/png") for x in pngs], "cheat-sheet instagram")
        return
    ops_melden.hand(ops_melden.hand_text("nach deiner freigabe", "Instagram Karussell",
                                         "cheat sheet als karussell posten",
                                         "https://www.instagram.com/kaspapulse/", paket),
                    [(x, "image/png") for x in pngs], "cheat-sheet instagram")


# --------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="nur messen, json auf stdout")
    ap.add_argument("--bauen", action="store_true", help="html und pdf bauen")
    ap.add_argument("--veroeffentlichen", action="store_true",
                    help="bauen, ins log eintragen und die datei der webseite ersetzen")
    ap.add_argument("--aus", help="werte aus einer gespeicherten probe")
    ap.add_argument("--edition", type=int)
    ap.add_argument("--stand", help="als dieser tag rechnen (JJJJ-MM-TT)")
    ap.add_argument("--ziel")
    ap.add_argument("--melden", action="store_true",
                    help="pdf und deckblatt melden, scharf nach #ops-log, sonst VON HAND nach #moderator-only")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    heute = dt.date.fromisoformat(a.stand) if a.stand else dt.datetime.now(dt.timezone.utc).date()
    p = _json(a.aus) if a.aus else probe(heute)
    if a.stand:
        p["stand"] = heute.isoformat()
    # Die Frist gilt gegen den Stand der Probe. Eine gespeicherte Probe darf
    # damit nachgebaut werden, aber nie veroeffentlicht, wenn sie selbst alt
    # ist: sonst traegt die Datei der Webseite einen neuen Monat und alte
    # Zahlen, genau das, was der Generator verhindern soll.
    stand = dt.date.fromisoformat(p["stand"])
    frische_pruefen(p, stand)
    if a.veroeffentlichen and alter(stand, heute) > FRIST_TAGE:
        raise Abbruch("die probe ist vom %s, %d tage alt, damit wird nichts veroeffentlicht"
                      % (stand, alter(stand, heute)))
    if a.probe or not (a.bauen or a.veroeffentlichen):
        print(json.dumps(p, ensure_ascii=False, indent=1))
        return 0
    log = edition_log()
    edition = a.edition or naechste_edition(log, p["stand"][:7])
    pdf, deck, roh = bauen(p, edition, a.ziel)
    print("edition %d, %s, %d byte\n%s\n%s" % (edition, pdf, pdf.stat().st_size, deck, roh))
    if a.veroeffentlichen:
        ziel = festschreiben(p, edition, pdf, log)
        print("festgeschrieben, %s und %s" % (LOG, ziel))
    roh_json = pdf.with_name(pdf.stem + "-probe.json")
    roh_json.write_text(json.dumps(p, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    # auch ins job-log, eine zeile: das artefakt ist nicht ueberall abrufbar
    print("PROBE-JSON " + json.dumps(p, ensure_ascii=False, separators=(",", ":")))
    info = getattr(rendern, "letzte", {"pngs": [], "kontrast": []})
    print("instagram, %d seiten unter %s, kontrast %s" % (
        len(info["pngs"]), ig_ordner(pdf), "; ".join(info["kontrast"]) or "alle ab 7:1"))
    if a.melden:
        text = ops_text(p, edition, pdf, a.veroeffentlichen)
        print(text)
        frueher = schon_gemeldet(heute)
        if frueher:
            print("heute schon gemeldet, lauf %s. nichts doppelt" % frueher)
            return 0
        ops_schicken(text, [(deck, "image/png"), (pdf, "application/pdf")], a.veroeffentlichen,
                     (info["pngs"], ig_caption(p, edition), info["kontrast"]) if info["pngs"] else None)
    return 0



# -------------------------------------------------------------- selbsttest

def selbsttest():
    fehler = []

    def ok(name, bedingung, *mehr):
        print("%s %s%s" % ("ok  " if bedingung else "FEHL", name,
                           (" " + " ".join(str(m) for m in mehr)) if mehr and not bedingung else ""))
        if not bedingung:
            fehler.append(name)

    # die achsen, die in Edition 1 noch als zahl im quelltext standen
    ok("schritt ist die groesste runde zahl darunter",
       (nett_schritt(0.202), nett_schritt(19.42), nett_schritt(97415.3)) == (0.2, 10.0, 50000.0),
       nett_schritt(0.202), nett_schritt(19.42), nett_schritt(97415.3))
    p = _json(PROBE_FEST)
    bo = [x[2] for x in p["zahlen"]["boersen"]["reihe"]]
    hs = [x[1] for x in p["zahlen"]["hashrate"]["reihe"]]
    co = [x[1] for x in p["zahlen"]["covenants"]["reihe"]]
    # Edition 1 hatte 13.4 bis 14.4, also teilstriche bei 13.7 und 14.1.
    # seit 28.10.2026 drei glatte schritte: 13.4, 13.8, 14.2, 14.6
    ok("boersen-achse in drei glatten schritten", achse(bo) == (13.4, 14.6), achse(bo))
    ok("hashrate-achse 300 bis 420 statt krummer 333 und 367",
       achse([314.96, 381.46]) == (300, 420), achse([314.96, 381.46]))
    ok("hashrate-achse wie in Edition 1", achse(hs) == (290.0, 380.0), achse(hs))
    ok("covenants-achse wie in Edition 1", achse_kumuliert(co) == (0.0, 300000.0),
       achse_kumuliert(co))
    ok("covenants-achse in drei glatten schritten, 0 bis 450k statt 400k",
       achse_kumuliert([46, 316522]) == (0.0, 450000.0), achse_kumuliert([46, 316522]))

    # die kleinen wortschalter
    ok("zeitspanne im selben monat nennt ihn einmal",
       spanne("2026-10-04", "2026-10-10") == "4 to 10 oct 2026", spanne("2026-10-04", "2026-10-10"))
    ok("zeitspanne ueber den monat nennt beide",
       spanne("2026-09-28", "2026-10-04") == "28 sep to 4 oct 2026")
    ok("toccata-datum ausgeschrieben", tag_monat("2026-06-30") == "30 june")
    ok("monatsteil aus dem tag", (monatsteil("2026-08-13"), monatsteil("2026-08-03"),
                                  monatsteil("2026-08-25")) == ("mid august", "early august",
                                                                "late august"))
    ok("fast und knapp darueber", (fast(293978), fast(301000)) == ("almost 300,000",
                                                                  "just over 300,000"))
    ok("vorzeichen mit minuszeichen, nicht bindestrich",
       (vorzeichen(520), vorzeichen(-718)) == ("+520", "−718"))
    ok("richtung waehlt das wort",
       (richtung(-0.6, "slipped", "risen", "barely moved", 0.05),
        richtung(0.6, "slipped", "risen", "barely moved", 0.05),
        richtung(0.01, "slipped", "risen", "barely moved", 0.05))
       == ("slipped", "risen", "barely moved"))
    ok("zahlwort fuer kleine zahlen", (wort(7), wort(18)) == ("seven", "18"))

    # die schriften liegen im repo, nicht in node_modules
    f = schriften()
    ok("acht schnitte aus dem repo eingebettet", f.count("@font-face") == 8,
       f.count("@font-face"))
    ok("keine schrift aus dem netz", "http" not in f)

    # der ganze bau aus den daten vom 11.10.2026 muss Fassung 2.1 ergeben
    s = html(p, 1, fonts="")
    ok("zehn seiten", s.count('<section class="pg') == 10, s.count('<section class="pg'))
    muss = [
        "edition 1 · october 2026", "the 8 kaspa numbers <em>whales watch</em>",
        # 1 entity x
        "<b>5.5%</b>", "1,527,589,469 KAS · 10 oct 2026",
        "one wallet holds about one in every 18 KAS",
        "last move of 100,000 KAS or more, 1 oct 2026, 4,517,808 KAS left",
        "supply as of 5 oct 2026",
        # 2 boersen
        "<b>13.6%</b>", "of all KAS, about one in seven", "3,781,925,849 KAS · 4 oct 2026",
        "that share has slipped from 14.2% in july to 13.6% on 4 oct",
        "logged by us every week since july",
        # 3 unbewegt
        "<b>50.7%</b>", "6 oct 2026 · 26.1% untouched for 2 years",
        "the share sat between 50.5% and 51.0%",
        # 4 halter
        "<b>293,978</b>", "+520 in 7 days", "+2,061 in 30",
        "almost 300,000 wallets hold 100 KAS or more",
        "the last month added about 2,000, the last 90 days are slightly negative",
        "54.9 million addresses hold something",
        # 5 senkung
        "<b>4 nov</b>", "next block reward cut, 13:45 utc",
        "2.06 to 1.94 KAS per block · 24 days from 11 oct",
        "the next one is on 4 november", "2.06 until 4 nov", "1.94 on 4 nov",
        "1.03 · oct 2027", "0.52 · oct 2028",
        # 6 gebuehren
        "<b>765x</b>", "30 days, 3 sep to 2 oct 2026", "they got 765 KAS in new coins",
        "56.77 million KAS new coins against 74,187 KAS fees", "765 squares new coins",
        # 7 hashrate
        "<b>339</b>", "PH/s, mean of the last 7 days",
        "4 to 10 oct 2026 · single day 362 on 10 oct",
        "339 quadrillion guesses every second protect the chain. about 4% more than in mid august",
        "single days jump by 10%", "mean 339",
        # 8 covenants
        "<b>292,292</b>", "covenant outputs created since 30 june",
        "9 oct 2026 · 13,936 still unspent",
        "launched on 30 june, covenants have been created 292,292 times",
        # deckblatt und rueckseite
        "KAS on exchanges", "hashrate, 7 day mean", "4 to 10 oct",
        "covenant outputs since 30 june", "utm_campaign=edition1",
        "youtube.com/channel/UCLheLoijZUZOE79vRtJtJ9Q",
        "edition 1 · october 2026 · not financial advice",
    ]
    fehlt = [m for m in muss if m not in s]
    ok("jeder satz und jede zahl aus Fassung 2.1 steht in der seite", not fehlt, fehlt)
    # Ben, 28.10.2026: vier saetze ohne echtzeit-wort
    for alt in ("13.6% now", "2.06 now", "today the network", "went live"):
        ok("kein %r mehr" % alt, alt not in s)
    ok("gebuehren-satz ohne today", "they got 765 KAS in new coins. the network is paid by issuance." in s)
    # streng gegen den 90. tag, wie in Fassung 2.1. Fassung 2 stand auf
    # -637, gezaehlt gegen den 07.07. und damit gegen 89 tage; die
    # veroeffentlichte datei ist am 12.10.2026 nachgezogen worden
    ok("90-tage-differenz streng gegen den 90. tag", "−718 in 90" in s
       and "−637" not in s)
    ok("kein platzhalter und kein None in der seite",
       "None" not in s and "%s" not in s and "{" not in s.split("<style>")[0])

    # die frist, der ganze sinn des generators
    try:
        frische_pruefen(p, dt.date(2026, 10, 25))
        ok("alter stichtag bricht ab", False)
    except Abbruch as exc:
        ok("alter stichtag bricht ab und nennt die zahl",
           "boersen" in str(exc) and "21 tage alt" in str(exc), exc)
    try:
        frische_pruefen({"zahlen": {}}, dt.date(2026, 10, 11))
        ok("fehlende zahl bricht ab", False)
    except Abbruch as exc:
        ok("fehlende zahl bricht ab und nennt sie", "entityx fehlt ganz" in str(exc), exc)
    ok("frische daten gehen durch", frische_pruefen(p, dt.date(2026, 10, 11)))

    # die woerter "half" und "a quarter" tragen nur passende anteile
    ok("passende anteile tragen die woerter", woerter_pruefen(50.7, 26.1))
    for a, b, wort_ in ((41.0, 26.1, "half"), (50.7, 18.0, "a quarter")):
        try:
            woerter_pruefen(a, b)
            ok("%s %s bricht ab" % (wort_, a if wort_ == "half" else b), False)
        except Abbruch as exc:
            ok("%s traegt %s nicht mehr" % (a if wort_ == "half" else b, wort_),
               wort_ in str(exc), exc)

    # Bens Regel 16.10.2026: Kaspalytics-Reihen tragen "source kaspalytics",
    # "counted" nur bei eigenen zaehlungen
    kk = karten(p)
    zl = uebersicht(p, kk)
    seiten = html(p, 1)
    ok("jede kaspalytics-karte nennt source kaspalytics",
       all("source kaspalytics" in c["src"] for c in kk if "kaspalytics" in c["src"]))
    ok("deckblatt nennt die quelle in den kaspalytics-zeilen",
       all("source kaspalytics" in zl[i][1] for i in (1, 2, 3, 5, 7)), [z[1] for z in zl])
    ok("kein 'counted on chain' und kein 'counted, not guessed'",
       "counted on chain" not in seiten and "counted, not guessed" not in seiten)

    # Edition 2 (Ben, 28.10.2026): linktext, utm, caption
    p2 = dict(p, stand="2026-11-01")
    s2 = html(p2, 2, fonts="")
    ok("rueckseite sagt the dashboard, nicht live numbers",
       "<b>the dashboard</b>" in s2 and "live numbers" not in s2)
    ok("pdf-links tragen utm_campaign=edition2", s2.count("utm_campaign=edition2") == 2
       and "edition1" not in s2, s2.count("utm_campaign=edition2"))
    ok("caption wortgleich mit Bens text", ig_caption(p2, 2) ==
       "the 8 kaspa numbers whales watch. edition 2, november 2026. every number dated, with its source. "
       "save it for later. the full cheat sheet arrives by email, link in bio. #kaspa #kas #blockdag",
       ig_caption(p2, 2))
    import content_wache
    ok("caption besteht die textregeln", content_wache.text_verstoesse(ig_caption(p2, 2)) == [],
       content_wache.text_verstoesse(ig_caption(p2, 2)))
    ok("INK3 traegt 7:1 auf grund und flaeche", kontrast_hex(INK3, BG) >= 7 and kontrast_hex(INK3, SURF) >= 7,
       kontrast_hex(INK3, BG), kontrast_hex(INK3, SURF))

    # wohin die meldungen gehen. gesendet wird nichts, _post ist eine
    # attrappe; ihre ausgabe "an #moderator-only, http 204" bleibt stumm,
    # damit sie im lauf-log niemand fuer echt haelt
    import contextlib
    import io
    import ops_melden
    def leise(*a):
        with contextlib.redirect_stdout(io.StringIO()):
            return ops_schicken(*a)
    gesendet = []
    echt_post = ops_melden._post
    alt_env = {k: os.environ.get(k) for k in list(ops_melden.ARTEN.values()) + ["GITHUB_REF_NAME"]}
    ops_melden._post = lambda url, body, typ, timeout=60: gesendet.append((url.rsplit("/", 1)[1], body)) or 204
    basis = "https://discord.com/api/" + "webhooks/"
    try:
        os.environ["DISCORD_WEBHOOK_OPS"] = basis + "1/hand"
        os.environ["DISCORD_WEBHOOK_LOG"] = basis + "2/log"
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            bild = Path(td) / "seite-01.png"
            bild.write_bytes(b"\x89PNG\r\n")
            pngs = [bild] * 10
            os.environ["GITHUB_REF_NAME"] = "main"
            leise("t", [(bild, "image/png")], False, (pngs, ig_caption(p2, 2), []))
            ok("sonntag, freigabe und instagram-paket als von hand",
               [g[0] for g in gesendet] == ["hand", "hand"]
               and all(b"VON HAND" in g[1] for g in gesendet), [g[0] for g in gesendet])
            ok("paket traegt 10 seiten und die caption",
               gesendet[-1][1].count(b'name="files[') == 10 and b"edition 2, november 2026" in gesendet[-1][1])
            ok("freigabe nennt variable und veroeffentlichen=true",
               b"CHEAT_SHEET_LIVE" in gesendet[0][1] and b"veroeffentlichen=true" in gesendet[0][1])
            gesendet.clear()
            leise("t", [], True, (pngs, ig_caption(p2, 2), []))
            ok("scharf, info nach log, paket trotzdem von hand",
               [g[0] for g in gesendet] == ["log", "hand"], [g[0] for g in gesendet])
            gesendet.clear()
            os.environ["GITHUB_REF_NAME"] = "cheat/edition2"
            ok("anderer branch ist eine probe", probe_lauf())
            leise("t", [], False, (pngs, ig_caption(p2, 2), []))
            ok("probe, alles nach log, nichts nach moderator-only",
               [g[0] for g in gesendet] == ["log", "log"] and b"PROBE" in gesendet[0][1], [g[0] for g in gesendet])
            gesendet.clear()
            os.environ["GITHUB_REF_NAME"] = "main"
            leise("t", [], False, (pngs, ig_caption(p2, 2), ["seite 5, kontrast 5.8:1"]))
            ok("kontrast unter 7:1, kein paket, liste nach log",
               [g[0] for g in gesendet] == ["hand", "log"] and b"NICHT" in gesendet[-1][1], [g[0] for g in gesendet])
    finally:
        ops_melden._post = echt_post
        for k_, v_ in alt_env.items():
            if v_ is None:
                os.environ.pop(k_, None)
            else:
                os.environ[k_] = v_

    # zwei laeufe am 1., der cron meldet nicht doppelt
    alt_env = {k_: os.environ.get(k_) for k_ in ("GITHUB_EVENT_NAME", "GITHUB_REPOSITORY", "GITHUB_RUN_ID")}
    try:
        os.environ.update(GITHUB_EVENT_NAME="schedule", GITHUB_REPOSITORY="o/r", GITHUB_RUN_ID="9")

        def holer(url, schritt="success"):
            if "/jobs" in url:
                return {"jobs": [{"steps": [{"name": "bauen und melden", "conclusion": schritt}]}]}
            return {"workflow_runs": [{"id": 9, "head_branch": "main"}, {"id": 7, "head_branch": "main"}]}
        tag = dt.date(2026, 11, 1)
        ok("cron nach gruenem takt-lauf meldet nicht", schon_gemeldet(tag, holer) == 7)
        ok("cron nach uebersprungenem lauf meldet",
           schon_gemeldet(tag, lambda u: holer(u, "skipped")) is None)

        def kaputt(url):
            raise OSError("kein netz")
        ok("ohne abfrage wird gemeldet", schon_gemeldet(tag, kaputt) is None)
        os.environ["GITHUB_EVENT_NAME"] = "workflow_dispatch"
        ok("ein lauf von hand meldet immer", schon_gemeldet(tag, holer) is None)
    finally:
        for k_, v_ in alt_env.items():
            if v_ is None:
                os.environ.pop(k_, None)
            else:
                os.environ[k_] = v_

    # unbewegt: die wochenspanne zaehlt erst ab unserem ersten sonntag
    global _tg
    echt_tg = _tg

    class FalschTG:
        @staticmethod
        def m_kl_reihe(pfad, name, art):
            tage = [dt.date(2023, 8, 27) + dt.timedelta(days=7 * k) for k in range(170)]
            return {t.isoformat(): (14.0 if t.isoformat() < UNBEWEGT_SEIT else
                                    (51.0 if "1year" in pfad else 26.0)) for t in tage}
    _tg = lambda: FalschTG  # noqa: E731
    try:
        ub = z_unbewegt(dt.date(2026, 11, 1))
        ok("unbewegt-spanne erst ab 26.07.2026, nicht ab 2023",
           ub["wochen_von"] == UNBEWEGT_SEIT and ub["wochen_min"] == 51.0, ub)
    finally:
        _tg = echt_tg

    # umlauf je tag, zurueckgerechnet (28.10.2026)
    jetzt = dt.datetime(2026, 10, 28, 6, tzinfo=dt.timezone.utc)
    u = umlauf_je_tag(["2026-10-25", "2026-10-26", "2026-10-27"], jetzt, 26_000_000_000.0,
                      lambda d: 100.0)
    ok("umlauf am ende des vortags ohne die emission von heute frueh",
       abs(u["2026-10-27"] - (26e9 - 25.0)) < 1e-6, u)
    ok("je tag weiter zurueck eine tagesemission weniger",
       abs(u["2026-10-25"] - (26e9 - 225.0)) < 1e-6 and abs(u["2026-10-26"] - (26e9 - 125.0)) < 1e-6, u)
    ok("ohne tage nichts", umlauf_je_tag([], jetzt, 1.0, lambda d: 0.0) == {})

    # die ausgabe-nummer
    lg = {"editionen": [{"n": 1, "monat": "2026-10"}]}
    ok("der naechste monat zaehlt hoch", naechste_edition(lg, "2026-11") == 2)
    ok("derselbe monat behaelt seine nummer", naechste_edition(lg, "2026-10") == 1)
    ok("ohne log faengt es bei eins an", naechste_edition({}, "2026-10") == 1)

    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Abbruch as exc:
        print("ABBRUCH %s" % exc)
        sys.exit(2)
