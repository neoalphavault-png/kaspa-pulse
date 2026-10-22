#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""startseite.py, baut die Startseite kaspapulse.com aus den Montagsdaten (Ben, 21.10.2026).

Die Startseite ist seit dem 23.10.2026 keine Kachelwand mehr, sondern eine
Zahl der Woche und sechs Schritte, jeder mit einer Zahl, einem Satz, einer
Grafik mit Aussage-Titel und einer Frage zum naechsten Schritt (Entwurf
startseite-entwurf-2026-10-21.html). Keine Zahl steht von Hand in der Seite.
Dieses Skript schreibt zwei Bereiche in index.html, jeweils zwischen eigenen
Marken, damit ein zweiter Lauf nichts aendert:

  <!--AUTO:menue-->       die Navigation, aus MENUE in capture.js, plus die
                          Gruppe "about", solange MENUE sie noch nicht hat
  <!--AUTO:startseite-->  Zahl der Woche, die sechs Schritte, beide Anmeldungen

WOHER DIE ZAHLEN KOMMEN (Stichtag ist der letzte Montag, siehe stichtag())
  Zahl der Woche   data/kas-candles.json, Wochenschluss gegen den Schnitt der
                   letzten 50 Wochenschluesse (weekly_facts.linie), wie im
                   Newsletter. Schluss von kraken, der Schnitt von uns.
  1 die Kette      data/tagesgrafik-log.json, messwerte.bps, unsere eigene
                   Messung ueber die kaspa rest api (counted)
  2 Gebuehren      data/tagesgrafik-log.json, messwerte.gebuehren, Gebuehren
                   von kaspalytics, neue Coins aus dem Emissionsplan
  3 Emission       gerechnet aus Anker und Monatsschritt (weekly_facts)
  4 Halter         data/address-thresholds-log.json, holders_100kas, kaspalytics
  5 Layer 2        data/weekly.json, igra_dex und kasplex_dex, defillama
  6 die Adressen   data/address-thresholds-log.json, holders_all, holders_001kas

  TVL bleibt draussen, bis der Ausreisser vom 21.09.2026 geprueft ist (Ben).
  Layer 2 ebenso, bis der igra-Sprung vom 19.10.2026 geprueft ist (Ben,
  21.10.2026), Schalter LAYER2. Die Seite laeuft solange mit 5 Schritten.

VERGLEICHS-CHIPS
  Schnelle Zahlen (Zahl der Woche, Halter, Layer 2) gegen die Woche davor und
  gegen 13 Wochen davor, die Emission gegen den Vormonat und gegen drei Monate
  davor, feste Groessen (Blockrate gegen Ziel, Adressen gesamt) ohne
  Vergleich. Fehlt ein Wert, faellt der Chip weg. Es gibt keinen Platzhalter.

Jeder sichtbare Satz laeuft vor dem Schreiben durch dieselben Wachen wie
Karussell und Tagesgrafik (karussell.text_pruefen): keine Echtzeit-Woerter,
% statt percent, "counted" nur bei eigener Zaehlung, fremde Zahlen mit
"source", kein Doppelpunkt, kein Gedankenstrich, kein Pfeil. Dazu traegt jeder
Schritt ein Datum. Ein Verstoss bricht ab, die alte Seite bleibt stehen.

    python3 scripts/startseite.py              schreiben
    python3 scripts/startseite.py --pruefen    nur pruefen, Exit 1 wenn index.html abweicht
    python3 scripts/startseite.py --heute 2026-10-21
    python3 scripts/startseite.py --selbsttest
"""
import argparse
import datetime as dt
import html as htmlmod
import json
import re
import sys
import urllib.parse
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import weekly_facts as wf  # noqa: E402

INDEX = REPO / "index.html"
CANDLES = REPO / "data" / "kas-candles.json"
TG_LOG = REPO / "data" / "tagesgrafik-log.json"
SCHWELLEN = REPO / "data" / "address-thresholds-log.json"
WEEKLY = REPO / "data" / "weekly.json"
CAPTURE = REPO / "capture.js"
SEITE = "https://kaspapulse.com/"

MON = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
TAGE = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# die gruppe "about" (Ben, 21.10.2026). Sie steht seit PR 2 in MENUE in
# capture.js, das hier ist nur der rueckfall, falls sie dort fehlt.
ABOUT = ("about", [("method", "/method/"),
                   ("archive", "/archive/"),
                   ("how we fund this", "/how-we-fund-this.html")])
# oberste punkte, die nicht in die leiste gehoeren: "dashboard" ist diese seite
OBEN_UMBENANNT = {"/": "this week"}

# Layer 2 bleibt draussen, bis der igra-Sprung vom 19.10.2026 geprueft ist
# (Ben, 21.10.2026). igra stand an diesem Montag bei 95% des DEX-Volumens,
# 19,2 Punkte ueber der Vorwoche, und der Lesetext vom Montag markiert genau
# diesen Sprung als "wird nachgeprueft". Der Schritt ist fertig gebaut und
# kommt mit True zurueck.
LAYER2 = False

DATUM_RE = re.compile(r"\b\d{1,2} (?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b")


class Abbruch(Exception):
    pass


# ---------------------------------------------------------------- formate

def d_kurz(d, jahr=True):
    d = d if isinstance(d, dt.date) else dt.date.fromisoformat(str(d)[:10])
    return "%d %s %d" % (d.day, MON[d.month - 1], d.year) if jahr else "%d %s" % (d.day, MON[d.month - 1])


def ganz(n):
    return "{:,}".format(int(round(n)))


def pct(x, nd=2):
    return ("%%.%df%%%%" % nd) % x


def esc(s):
    return htmlmod.escape(s, quote=True)


def stichtag(heute):
    """Der Montag, dessen Daten gelten. Montag selbst zaehlt schon."""
    return heute - dt.timedelta(days=heute.weekday())


# ---------------------------------------------------------------- menue

def menue_gruppen(js=None):
    """MENUE aus capture.js als [(text, pfad)] oben und [(gruppe, [(text, pfad)])]."""
    js = js if js is not None else CAPTURE.read_text(encoding="utf-8")
    block = js[js.index("var MENUE = ["):]
    block = block[:block.index("];")]
    oben, gruppen = [], []
    for m in re.finditer(r'\{ t: "([^"]+)", h: "([^"]+)" \}|\{ t: "([^"]+)", k: \[(.*?)\]\}', block, re.S):
        if m.group(1):
            oben.append((m.group(1), m.group(2)))
        else:
            gruppen.append((m.group(3), re.findall(r'\["([^"]+)", "([^"]+)"\]', m.group(4))))
    if not any(g == ABOUT[0] for g, _ in gruppen):
        gruppen.append(ABOUT)
    return oben, gruppen


def menue_html(js=None, hier="/"):
    """Das Menue aus MENUE. hier ist der Pfad der Seite: ihr Punkt bekommt
    aria-current, ihre Gruppe die Klasse on (rahmen.py fuer die Unterseiten)."""
    oben, gruppen = menue_gruppen(js)
    z = ['<nav class="menu" id="menu" aria-label="main">', '  <div class="mtop">']
    for t, h in oben:
        t = OBEN_UMBENANNT.get(h, t)
        cur = ' aria-current="page"' if h == hier else ""
        z.append('    <a href="%s"%s>%s</a>' % (h, cur, esc(t)))
    z.append("  </div>")
    for g, punkte in gruppen:
        on = " on" if any(h == hier for _, h in punkte) else ""
        z.append('  <div class="grp"><button class="gbtn%s" type="button" aria-expanded="false">%s</button>'
                 '<div class="drop">%s</div></div>'
                 % (on, esc(g), "".join('<a href="%s"%s>%s</a>' % (h, ' aria-current="page"' if h == hier else "",
                                                                    esc(t)) for t, h in punkte)))
    z.append("</nav>")
    return "\n".join(z)


# ---------------------------------------------------------------- daten

def lade(p, standard=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return standard


def bis(reihe, grenze, datum, streng=False):
    """Neuester Eintrag mit Datum <= grenze. Gibt es keinen, der neueste ueberhaupt,
    ausser streng: eine Seite fuer eine vergangene Woche (archiv.py) darf nie
    einen Wert tragen, der nach ihrem Montag gemessen wurde."""
    alle = sorted((r for r in reihe if datum(r)), key=datum)
    vor = [r for r in alle if datum(r) <= grenze.isoformat()]
    return (vor or ([] if streng else alle) or [None])[-1]


def zahl_der_woche(candles, st):
    """Wochenschluss gegen den 50-Wochen-Schnitt, mit Vorwoche und 13 Wochen davor.
    Das Etikett einer Woche ist ihr Sonntag, der Schluss faellt sechs Tage
    spaeter (Samstag, 24:00 utc). Es zaehlen nur Wochen, die vor dem Stichtag
    geschlossen haben."""
    wk = [w for w in (candles or {}).get("kas_weekly", [])
          if dt.date.fromisoformat(w[0]) + dt.timedelta(days=7) <= st]
    labels, closes = [w[0] for w in wk], [w[1] for w in wk]
    try:
        jetzt = wf.linie(50, labels, closes)
    except (RuntimeError, IndexError, ZeroDivisionError):
        return None

    def schluss(lab):
        return dt.date.fromisoformat(lab) + dt.timedelta(days=6)

    def vergleich(n):
        if len(labels) <= n:
            return None
        try:
            v = wf.linie(50, labels[:-n], closes[:-n])
        except (RuntimeError, IndexError, ZeroDivisionError):
            return None
        return {"datum": schluss(v["label"]), "abstand": v["abstand_pct"]}

    rot = 0
    for i in range(len(closes) - 1, 0, -1):
        if closes[i] < closes[i - 1]:
            rot += 1
        else:
            break
    gruen = 0
    for i in range(len(closes) - 1, 0, -1):
        if closes[i] > closes[i - 1]:
            gruen += 1
        else:
            break
    return {"datum": schluss(jetzt["label"]), "abstand": jetzt["abstand_pct"],
            "rot": rot, "gruen": gruen, "seit": labels[0],
            "vorwoche": vergleich(1), "q13": vergleich(13)}


def tg_messwert(log, st, feld, streng=False):
    laeufe = (log or {}).get("laeufe", [])
    mit = [e for e in laeufe if isinstance((e.get("messwerte") or {}).get(feld), (int, float, dict))
           and not (isinstance(e["messwerte"][feld], dict) and e["messwerte"][feld].get("ausfall"))]
    e = bis(mit, st, lambda r: (r.get("messzeit_utc") or r.get("datum") or "")[:10], streng)
    return e


def blockrate(log, st, streng=False):
    e = tg_messwert(log, st, "bps", streng)
    if not e or not 5 < e["messwerte"]["bps"] < 15:
        return None
    return {"bps": e["messwerte"]["bps"], "sek": e["messwerte"].get("blockrate_sek"),
            "datum": dt.date.fromisoformat((e.get("messzeit_utc") or e["datum"])[:10])}


def gebuehren(log, st, streng=False):
    e = tg_messwert(log, st, "gebuehren", streng)
    if not e:
        return None
    g = e["messwerte"]["gebuehren"]
    if not (g.get("fees") and g.get("emission") and g.get("von") and g.get("bis")):
        return None
    return {"anteil": g["fees"] / (g["fees"] + g["emission"]) * 100,
            "von": dt.date.fromisoformat(g["von"]), "bis": dt.date.fromisoformat(g["bis"])}


def emission(st):
    """Naechste Senkung ab dem Stichtag, mit Vormonat und drei Monaten davor."""
    ts = dt.datetime.combine(st, dt.time(0), dt.timezone.utc).timestamp()
    n = wf.schritte_bis(ts)

    def cut(k):
        return dt.datetime.fromtimestamp(wf.ANCHOR_TS + wf.STEP * k, dt.timezone.utc).date()

    def je_tag(k):
        return round(wf.emission_je_tag(wf.reward_nach_schritten(k)))

    nxt = n + 1
    return {"datum": cut(nxt), "neu": je_tag(nxt),
            "vormonat": {"datum": cut(n), "wert": je_tag(n)},
            "q3": {"datum": cut(nxt - 3), "wert": je_tag(nxt - 3)},
            "schritt_pct": (1 - wf.RATIO) * 100,
            "kurve": [(cut(k), je_tag(k)) for k in range(nxt - 6, nxt + 7)], "nxt_i": 6}


def schwellen(log, st, streng=False):
    tage = [t for t in (log or {}).get("tage", []) if t.get("datum")]
    tage.sort(key=lambda t: t["datum"])
    vor = [t for t in tage if t["datum"] <= st.isoformat()]
    return vor if (vor or streng) else tage


def halter(tage):
    if not tage or tage[-1].get("holders_100kas") is None:
        return None
    nach = {t["datum"]: t for t in tage}
    jetzt = tage[-1]
    d = dt.date.fromisoformat(jetzt["datum"])

    def am(tage_zurueck):
        t = nach.get((d - dt.timedelta(days=tage_zurueck)).isoformat())
        if t and t.get("holders_100kas") is not None:
            return {"datum": d - dt.timedelta(days=tage_zurueck), "wert": t["holders_100kas"]}
        return None

    netto = []
    for i in range(7):
        a = nach.get((d - dt.timedelta(days=6 - i)).isoformat())
        b = nach.get((d - dt.timedelta(days=7 - i)).isoformat())
        if a and b and a.get("holders_100kas") is not None and b.get("holders_100kas") is not None:
            netto.append((d - dt.timedelta(days=6 - i), a["holders_100kas"] - b["holders_100kas"]))
    return {"datum": d, "wert": jetzt["holders_100kas"], "vorwoche": am(7), "q13": am(91),
            "netto": netto if len(netto) == 7 else []}


def layer2(weekly, st, streng=False):
    rows = [r for r in (weekly or {}).get("history", [])
            if (r.get("m") or {}).get("igra_dex") and (r.get("m") or {}).get("kasplex_dex") is not None]
    rows = [r for r in rows if r["date"] <= st.isoformat()] or ([] if streng else rows)
    if not rows:
        return None
    nach = {r["date"]: r for r in rows}
    r = rows[-1]
    d = dt.date.fromisoformat(r["date"])

    def anteil(row):
        m = row["m"]
        return m["igra_dex"] / (m["igra_dex"] + m["kasplex_dex"]) * 100

    def am(tage):
        x = nach.get((d - dt.timedelta(days=tage)).isoformat())
        return {"datum": d - dt.timedelta(days=tage), "wert": anteil(x)} if x else None

    return {"datum": d, "anteil": anteil(r), "vorwoche": am(7), "q13": am(91)}


def adressen(tage):
    if not tage:
        return None
    t = tage[-1]
    if not (t.get("holders_all") and t.get("holders_001kas")):
        return None
    return {"datum": dt.date.fromisoformat(t["datum"]), "alle": t["holders_all"], "ueber": t["holders_001kas"]}


def daten(heute=None, streng=False, quellen=None):
    """Alle Zahlen zum Stichtag. streng fuer vergangene Wochen, siehe bis().
    quellen erlaubt archiv.py, die Dateien nur einmal zu lesen."""
    heute = heute or dt.datetime.now(dt.timezone.utc).date()
    st = stichtag(heute)
    q = quellen or lade_quellen()
    tg = q["tg"]
    sw = schwellen(q["schwellen"], st, streng)
    return {"stichtag": st, "zdw": zahl_der_woche(q["candles"], st), "kette": blockrate(tg, st, streng),
            "gebuehren": gebuehren(tg, st, streng), "emission": emission(st), "halter": halter(sw),
            "layer2": layer2(q["weekly"], st, streng) if LAYER2 else None, "adressen": adressen(sw)}


def lade_quellen():
    return {"tg": lade(TG_LOG, {}), "schwellen": lade(SCHWELLEN, {}), "candles": lade(CANDLES, {}),
            "weekly": lade(WEEKLY, {})}


# ---------------------------------------------------------------- bausteine

def chip(diff, einheit, datum, nd=2):
    """Ein Vergleichs-Chip. diff ist neu minus alt."""
    if abs(diff) < 10 ** -nd / 2:
        return '<li>level vs %s</li>' % d_kurz(datum, False)
    klasse, zeichen = ("up", "▲") if diff > 0 else ("dn", "▼")
    wert = (ganz(abs(diff)) if nd == 0 else ("%%.%df" % nd) % abs(diff)) + einheit
    return '<li><span class="%s">%s %s</span> vs %s</li>' % (klasse, zeichen, wert, d_kurz(datum, False))


def chip_wert(jetzt, alt, datum, text):
    """Ein Chip mit dem alten Wert statt einer Differenz (Ben, 21.10.2026):
    "10 oct \u00b7 12.59% above" liest sich, "\u25bc 14.05 points vs 10 oct" nicht.
    Die Farbe sagt, in welche Richtung es seitdem ging."""
    klasse = "up" if jetzt > alt else "dn" if jetzt < alt else ""
    wert = '<span class="%s">%s</span>' % (klasse, esc(text)) if klasse else esc(text)
    return "<li>%s \u00b7 %s</li>" % (d_kurz(datum, False), wert)


def abstand_text(a):
    return "%s %s" % (pct(abs(a)), "below" if a < 0 else "above")


def chips(liste):
    liste = [c for c in liste if c]
    if not liste:
        return ""
    return '<ul class="cmp" aria-label="comparison">%s</ul>' % "".join(liste)


def teilen(sid, satz, url=SEITE):
    text = satz + ". source kaspa pulse"
    return ("https://x.com/intent/post?text=" + urllib.parse.quote(text, safe="")
            + "&url=" + urllib.parse.quote(url + "#" + sid, safe=""))


def balken_split(teile, label):
    """Ein waagerechter Balken aus zwei Teilen [(name, anteil, farbe)]."""
    w = 640
    a = max(min(teile[0][1] / 100 * w, w - 4), 4)
    z = ['<svg viewBox="0 0 640 96" width="100%%" role="img" aria-label="%s">' % esc(label),
         '<rect x="0" y="22" width="640" height="34" rx="4" fill="var(--line)"/>',
         '<rect x="0" y="22" width="%.1f" height="34" rx="4" fill="var(--accent)"/>' % a,
         '<text x="0" y="82" class="lab">%s</text>' % esc(teile[0][0]),
         '<text x="640" y="82" text-anchor="end" class="lab">%s</text>' % esc(teile[1][0]),
         "</svg>"]
    return "".join(z)


def balken_paar(oben, unten, label):
    """Zwei Balken untereinander, Achse ab null, Werte daneben beschriftet."""
    mx = max(oben[1], unten[1]) or 1
    z = ['<svg viewBox="0 0 640 112" width="100%%" role="img" aria-label="%s">' % esc(label)]
    for i, (name, wert, text, an) in enumerate((oben, unten)):
        y = 8 + i * 54
        w = max(wert / mx * 440, 3)
        z.append('<text x="0" y="%d" class="lab">%s</text>' % (y + 14, esc(name)))
        z.append('<rect x="0" y="%d" width="%.1f" height="22" rx="3" fill="%s"/>'
                 % (y + 22, w, "var(--accent)" if an else "var(--muted)"))
        z.append('<text x="%.1f" y="%d">%s</text>' % (w + 8, y + 38, esc(text)))
    z.append("</svg>")
    return "".join(z)


def treppe(e):
    """Stufenkurve der taeglichen Emission, die naechste Senkung markiert."""
    W, H, L, R, T, B = 640, 240, 56, 14, 18, 36
    werte = [v for _, v in e["kurve"]]
    hi = max(werte) * 1.06
    lo = min(werte) * 0.9
    n = len(werte) - 1

    def x(i):
        return L + (W - L - R) * i / n

    def y(v):
        return T + (H - T - B) * (1 - (v - lo) / (hi - lo))

    z = ['<svg viewBox="0 0 640 240" width="100%%" role="img" aria-label="daily emission in KAS per month, '
         '%s to %s, stepping down from %s to %s">' % (d_kurz(e["kurve"][0][0]), d_kurz(e["kurve"][-1][0]),
                                                   ganz(werte[0]), ganz(werte[-1]))]
    schritt = 500000 if hi - lo > 1000000 else 250000
    t = (int(lo / schritt) + 1) * schritt
    while t < hi:
        z.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--line)"/>' % (L, W - R, y(t), y(t)))
        z.append('<text x="%d" y="%.1f" text-anchor="end" font-size="11">%.1fM</text>' % (L - 8, y(t) + 4, t / 1e6))
        t += schritt
    d = "M%.1f,%.1f" % (x(0), y(werte[0]))
    for i in range(1, len(werte)):
        d += " H%.1f V%.1f" % (x(i), y(werte[i]))
    z.append('<path d="%s" fill="none" stroke="var(--muted)" stroke-width="2"/>' % d)
    k = e["nxt_i"]
    z.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="var(--accent)" stroke-width="4"/>'
             % (x(k), x(k), y(werte[k - 1]), y(werte[k])))
    z.append('<circle cx="%.1f" cy="%.1f" r="5" fill="var(--accent)"/>' % (x(k), y(werte[k])))
    z.append('<text x="%.1f" y="%.1f" class="lab" font-size="12">%s · %s</text>'
             % (x(k) + 8, y(werte[k]) - 8, d_kurz(e["kurve"][k][0], False), ganz(werte[k])))
    for i in (0, 3, 6, 9, 12):
        dd = e["kurve"][i][0]
        anker = "start" if i == 0 else "end" if i == 12 else "middle"
        z.append('<text x="%.1f" y="%d" text-anchor="%s" font-size="11">%s %02d</text>'
                 % (x(i) - (L - 8 if i == 0 else 0), H - 12, anker, MON[dd.month - 1], dd.year % 100))
    z.append("</svg>")
    return "".join(z)


def netto_balken(netto):
    W, H, L, R, T, B = 640, 220, 44, 12, 18, 34
    werte = [v for _, v in netto]
    hi = max(max(werte), 0)
    lo = min(min(werte), 0)
    spanne = (hi - lo) or 1
    hi += spanne * 0.15
    lo -= spanne * 0.15 if lo < 0 else 0

    def y(v):
        return T + (H - T - B) * (hi - v) / (hi - lo)

    bw = (W - L - R) / len(netto)
    z = ['<svg viewBox="0 0 640 220" width="100%%" role="img" aria-label="net change per day of addresses '
         'with at least 100 KAS, %s to %s">' % (d_kurz(netto[0][0]), d_kurz(netto[-1][0]))]
    z.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--muted)"/>' % (L, W - R, y(0), y(0)))
    z.append('<text x="%d" y="%.1f" text-anchor="end" font-size="11">0</text>' % (L - 8, y(0) + 4))
    i_max = werte.index(max(werte))
    for i, (d, v) in enumerate(netto):
        x0, w = L + i * bw + bw * 0.18, bw * 0.64
        y0 = y(v) if v >= 0 else y(0)
        h = max(abs(y(v) - y(0)), 1.5)
        z.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="%s"/>'
                 % (x0, y0, w, h, "var(--neg)" if v < 0 else "var(--accent)"))
        z.append('<text x="%.1f" y="%d" text-anchor="middle" font-size="11">%s</text>'
                 % (x0 + w / 2, H - 12, d.day))
        if v < 0 or i in (i_max, len(netto) - 1):
            z.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="11" class="lab">%s%s</text>'
                     % (x0 + w / 2, y(v) + 14 if v < 0 else y(v) - 6, "+" if v > 0 else "", ganz(v)))
    z.append("</svg>")
    return "".join(z)


# ---------------------------------------------------------------- schritte

# Die Frage am Ende eines Schritts fuehrt in den naechsten. Sie haengt deshalb
# am Ziel, nicht am Schritt davor: faellt ein Schritt weg, fragt der vorige
# nach dem, was wirklich folgt.
HIN = {"fees": "fast blocks need miners. so who pays them?",
       "emission": "and the new coins get fewer every month.",
       "holders": "who is holding all those coins?",
       "layer2": "and where does the money move on kaspa's layer 2?",
       "addresses": "one more number, and it gets quoted wrong a lot."}


def schritte(D):
    """Liste der Schritte. Ein Schritt ohne Daten faellt weg, die Zaehlung rueckt nach."""
    aus = []
    k = D["kette"]
    if k:
        abw = (k["bps"] / 10 - 1) * 100
        aus.append({
            "id": "chain", "kopf": "the chain",
            "h2": ("blocks keep landing <em>%d times a second</em>" % round(k["bps"])),
            "satz": ("%.3f blocks per second over %d seconds on %s, counted by kaspa pulse "
                     "from the kaspa rest api. the protocol is set to 10 a second since the crescendo upgrade on 5 may 2025."
                     % (k["bps"], k["sek"] or 600, d_kurz(k["datum"]))),
            "ftitel": "our count sits %s %s the protocol rate of 10" % (pct(abs(abw), 1), "under" if abw < 0 else "over"),
            "grafik": balken_paar(("counted %s" % d_kurz(k["datum"]), k["bps"], "%.3f" % k["bps"], True),
                                  ("protocol rate", 10, "10", False),
                                  "blocks per second, counted %.3f against the protocol rate of 10" % k["bps"]),
            "fcap": "blocks per second over %d seconds, counted %s" % (k["sek"] or 600, d_kurz(k["datum"])),
            "chips": ""})
    g = D["gebuehren"]
    if g:
        aus.append({
            "id": "fees", "kopf": "security budget",
            "h2": "fees paid <em>%s</em> of miner revenue from %s to %s" % (
                pct(g["anteil"]), d_kurz(g["von"], False), d_kurz(g["bis"], False)),
            "satz": ("new coins paid the other %s. that is why the emission schedule matters so much "
                     "for kaspa security." % pct(100 - g["anteil"])),
            "ftitel": "new coins pay almost all of it",
            "grafik": balken_split([("new coins %s" % pct(100 - g["anteil"]), 100 - g["anteil"]),
                                    ("fees %s" % pct(g["anteil"]), g["anteil"])],
                                   "miner revenue split, new coins %s, fees %s" % (
                                       pct(100 - g["anteil"]), pct(g["anteil"]))),
            "fcap": ("%s to %s, miner revenue in KAS · fees source kaspalytics, new coins computed "
                     "from the emission schedule" % (d_kurz(g["von"]), d_kurz(g["bis"]))),
            "chips": ""})
    e = D["emission"]
    if e:
        vm, q3 = e["vormonat"], e["q3"]
        aus.append({
            "id": "emission", "kopf": "emission",
            "h2": "daily emission steps down to <em>%s KAS</em> on %s" % (ganz(e["neu"]), d_kurz(e["datum"], False)),
            "satz": ("it steps down every month by the same factor and halves once a year. at flat fees, "
                     "each step is close to a %s cut in miner income in KAS." % pct(e["schritt_pct"], 1)),
            "ftitel": "%s KAS a day on %s, after %s on %s" % (
                ganz(e["neu"]), d_kurz(e["datum"], False), ganz(vm["wert"]), d_kurz(vm["datum"], False)),
            "grafik": treppe(e),
            "fcap": "computed from the emission schedule, factor 2^(1/12) down per month · KAS per day",
            "chips": chips([chip((e["neu"] / vm["wert"] - 1) * 100, "%", vm["datum"], 1),
                            chip((e["neu"] / q3["wert"] - 1) * 100, "%", q3["datum"], 1)])})
    h = D["halter"]
    if h:
        vw = h["vorwoche"]
        satz = ""
        if vw:
            diff = h["wert"] - vw["wert"]
            satz = "%s %s than on %s." % (ganz(abs(diff)), "more" if diff >= 0 else "fewer", d_kurz(vw["datum"], False))
        if h["netto"]:
            fiel = [d for d, v in h["netto"] if v < 0]
            if not fiel:
                satz += " the count rose on all 7 days to %s." % d_kurz(h["datum"], False)
            elif len(fiel) == 1:
                satz += " 1 day fell, on %s." % d_kurz(fiel[0], False)
            else:
                satz += " %d of the 7 days fell." % len(fiel)
        satz = (satz.strip() + " read on %s, source kaspalytics." % d_kurz(h["datum"])).strip()
        cs = []
        for v in (h["vorwoche"], h["q13"]):
            if v:
                diff = h["wert"] - v["wert"]
                cs.append(chip(diff, "", v["datum"], 0).replace(
                    "</span>", " · %s</span>" % pct(abs(diff) / v["wert"] * 100), 1) if diff else
                          chip(diff, "", v["datum"], 0))
        aus.append({
            "id": "holders", "kopf": "holders",
            "h2": "<em>%s</em> addresses hold at least 100 KAS" % ganz(h["wert"]),
            "satz": satz,
            "ftitel": ("net change per day, %s of 7 days up" % sum(1 for _, v in h["netto"] if v > 0)
                       if h["netto"] else ""),
            "grafik": netto_balken(h["netto"]) if h["netto"] else "",
            "fcap": ("net change per day, %s to %s · source kaspalytics address thresholds"
                     % (d_kurz(h["netto"][0][0], False), d_kurz(h["netto"][-1][0]))) if h["netto"] else "",
            "chips": chips(cs)})
    l2 = D["layer2"]
    if l2:
        a = l2["anteil"]
        aus.append({
            "id": "layer2", "kopf": "layer 2",
            "h2": "igra carried <em>%d%%</em> of kaspa's layer 2 DEX volume" % round(a),
            "satz": ("in the 24 hours before our reading on %s, the rest went through kasplex, "
                     "source defillama." % d_kurz(l2["datum"])),
            "ftitel": "igra %d%%, kasplex %d%%" % (round(a), 100 - round(a)),
            "grafik": balken_split([("igra %d%%" % round(a), a), ("kasplex %d%%" % (100 - round(a)), 100 - a)],
                                   "layer 2 DEX volume share, igra %d%%, kasplex %d%%" % (round(a), 100 - round(a))),
            "fcap": "24 hours to the reading of %s · source defillama" % d_kurz(l2["datum"]),
            "chips": chips([chip_wert(a, v["wert"], v["datum"], "%.1f%%" % v["wert"])
                            for v in (l2["vorwoche"], l2["q13"]) if v])})
    ad = D["adressen"]
    if ad:
        mio = ad["alle"] / 1e6
        anteil = ad["ueber"] / ad["alle"] * 100
        aus.append({
            "id": "addresses", "kopf": "the quoted number",
            "h2": "%.1f million addresses, but not <em>%.1f million holders</em>" % (mio, mio),
            "satz": "most hold dust. above 0.01 KAS it is %s addresses, read on %s, source kaspalytics." % (
                ganz(ad["ueber"]), d_kurz(ad["datum"])),
            "ftitel": "only %s of all addresses hold more than 0.01 KAS" % pct(anteil, 1),
            "grafik": balken_paar(("addresses with any balance", ad["alle"], ganz(ad["alle"]), False),
                                  ("addresses above 0.01 KAS", ad["ueber"], ganz(ad["ueber"]), True),
                                  "%s addresses with any balance, %s above 0.01 KAS" % (
                                      ganz(ad["alle"]), ganz(ad["ueber"]))),
            "fcap": "%s · source kaspalytics address thresholds" % d_kurz(ad["datum"]),
            "chips": ""})
    return aus


def hero_html(z, st, oben=None):
    if not z:
        return ""
    unter = z["abstand"] < 0
    satz = "kaspa closed the week %s %s its 50 week average" % (pct(abs(z["abstand"])), "under" if unter else "above")
    if z["rot"] >= 2:
        satz += ", its %s red week in a row" % wf.ordnung(z["rot"])
    elif z["gruen"] >= 2:
        satz += ", its %s green week in a row" % wf.ordnung(z["gruen"])
    satz += "."
    cs = chips([chip_wert(z["abstand"], v["abstand"], v["datum"], abstand_text(v["abstand"]))
                for v in (z["vorwoche"], z["q13"]) if v])
    return "\n".join([
        '  <section class="hero" id="week">',
        '    <p class="eyebrow">%s</p>' % (oben or "number of the week · reading %s · next %s" % (
            d_kurz(st), d_kurz(st + dt.timedelta(days=7), False))),
        '    <p class="big"><a class="mref" href="/method/#week">%s</a></p>' % pct(abs(z["abstand"])),
        '    <p class="lead">%s</p>' % esc(satz),
        '    <p class="note">week to %s · weekly close against the average of the last 50 weekly closes, '
        'source kraken daily candles · our own series since %s</p>' % (d_kurz(z["datum"]), d_kurz(z["seit"])),
        "    " + cs if cs else "",
        '    <a class="next" href="#%s">6 numbers, 2 minutes</a>',
        "  </section>"]).replace("\n\n", "\n")


def mref(h, sid):
    """Die hervorgehobene Zahl verlinkt auf ihren Eintrag in method (Ben, 21.10.2026)."""
    return h.replace("<em>", '<a class="mref" href="/method/#%s"><em>' % sid, 1).replace("</em>", "</em></a>", 1)


def h2_text(h):
    return htmlmod.unescape(re.sub(r"<[^>]+>", "", h))


def anmeldung(nr, sid, titel, text):
    """Das bestehende Brevo-Formular. Die UTM-Felder mit id stehen nur im ersten,
    utm.js fuellt sie, das zweite bekommt die Werte beim Absenden."""
    if nr == 1:
        utm = ('      <input type="hidden" name="UTM_SOURCE" id="utmSource" value="direct">\n'
               '      <input type="hidden" name="UTM_MEDIUM" id="utmMedium" value="none">\n'
               '      <input type="hidden" name="UTM_CAMPAIGN" id="utmCampaign" value="none">\n'
               '      <input type="hidden" name="UTM_MEDIUM_RAW" id="utmMediumRaw" value="none">\n')
    else:
        utm = ('      <input type="hidden" name="UTM_SOURCE" data-utm="utmSource" value="direct">\n'
               '      <input type="hidden" name="UTM_MEDIUM" data-utm="utmMedium" value="none">\n'
               '      <input type="hidden" name="UTM_CAMPAIGN" data-utm="utmCampaign" value="none">\n'
               '      <input type="hidden" name="UTM_MEDIUM_RAW" data-utm="utmMediumRaw" value="none">\n')
    return ('  <div class="subscribe" id="%s">\n'
            '    <h3>%s</h3>\n'
            '    <p>%s</p>\n'
            '    <form class="subform" action="%s" method="POST" target="_blank">\n'
            '      <input type="email" name="EMAIL" placeholder="your email" aria-label="email" required>\n'
            '%s'
            '      <input type="text" name="email_address_check" value="" style="position:absolute;left:-9999px;" '
            'tabindex="-1" autocomplete="off" aria-hidden="true">\n'
            '      <input type="hidden" name="locale" value="en">\n'
            '      <input type="hidden" name="html_type" value="simple">\n'
            '      <button type="submit">subscribe</button>\n'
            '    </form>\n'
            '    <div class="msg" role="status"></div>\n'
            '    <small>free · unsubscribe anytime · cheat sheet delivered after email confirmation</small>\n'
            '  </div>') % (sid, esc(titel), esc(text), BREVO, utm)


BREVO = ("https://f926321f.sibforms.com/serve/MUIFAFRuw_TYaNSX3EkJvy138Dd428wMUmHj9SzFap7QLCSAeGmK2p9tHNGmw4FZsutI"
         "FsyZ5cbZXGXBYqZGd1a7G_WknNhFvbOZBCI4w0NMVg902P0LTdsllkJVLWfGjkublTW32QT5hFY_LTqkN6ihwbEvTmL5P34zQ6SKTHug"
         "FPnR90YZeWSMdEkK8mr6HAvO4-S9dXwuZdkQMA==")


def inhalt_html(D, url=SEITE, archiv=None):
    """Der Inhalt der Startseite. Mit archiv (dict mit oben, unten) dieselben
    Schritte fuer eine Wochenseite: eigene Kopfzeile, eine Anmeldung am Ende,
    Links zur Vor- und Folgewoche."""
    st = D["stichtag"]
    ss = schritte(D)
    if not ss:
        raise Abbruch("kein einziger schritt hat daten")
    n = len(ss)
    teile = [hero_html(D["zdw"], st, archiv and archiv["oben"]).replace('href="#%s"', 'href="#%s"' % ss[0]["id"])
             .replace("6 numbers, 2 minutes", "%d numbers, 2 minutes" % n)]
    teile.append('  <nav class="progress" aria-label="progress">%s</nav>' % "".join(
        '<a href="#%s" aria-label="step %d"></a>' % (s["id"], i + 1) for i, s in enumerate(ss)))
    for i, s in enumerate(ss):
        nxt = ss[i + 1]["id"] if i + 1 < n else None
        z = ['  <section class="step" id="%s">' % s["id"],
             '    <div class="steprow"><div class="stepnum">%d / %d · %s</div>'
             '<a class="share" href="%s" target="_blank" rel="noopener">share on x</a></div>'
             % (i + 1, n, s["kopf"], esc(teilen(s["id"], h2_text(s["h2"]), url))),
             "    <h2>%s</h2>" % mref(s["h2"], s["id"]),
             '    <p class="body">%s</p>' % esc(s["satz"])]
        if s["chips"]:
            z.append("    " + s["chips"])
        if s["grafik"]:
            z.append('    <figure><p class="ftitle">%s</p>%s<figcaption>%s</figcaption></figure>'
                     % (esc(s["ftitel"]), s["grafik"], esc(s["fcap"])))
        if nxt and HIN.get(nxt):
            z.append('    <p class="bridge">%s <a href="#%s">next</a></p>' % (esc(HIN[nxt]), nxt))
        if not nxt:
            z.append('    <div class="deeper"><a href="/kaspa-hashrate.html">network</a>'
                     '<a href="/kaspa-supply.html">supply</a><a href="/kaspa-token-standard.html">tokens</a>'
                     '<a href="/entity-x.html">largest wallet</a><a href="/kaspa-covenants.html">covenants</a></div>')
        z.append("  </section>")
        teile.append("\n".join(z))
        if i == 2 and n > 3 and not archiv:
            teile.append(anmeldung(1, "subscribe", "all the weekly numbers in one mail, every monday",
                                   "the %d numbers on this page, dated and sourced, in one mail." % n))
    if archiv:
        teile.append(archiv["unten"])
        teile.append(anmeldung(1, "subscribe", "all the weekly numbers in one mail, every monday",
                               "the numbers of each monday reading, dated and sourced, in one mail."))
        return "\n".join(teile)
    if n <= 3:
        teile.append(anmeldung(1, "subscribe", "all the weekly numbers in one mail, every monday",
                               "the %d numbers on this page, dated and sourced, in one mail." % n))
    nx = st + dt.timedelta(days=7)
    teile.append(anmeldung(2, "subscribe-end", "next reading %s %s" % (TAGE[nx.weekday()], d_kurz(nx, False)),
                           "get it in your inbox, every number with its date and source."))
    return "\n".join(teile)


# ---------------------------------------------------------------- wachen

def sichtbare_texte(inhalt):
    """Jeder sichtbare Satz des generierten Bereichs, ohne svg-Beschriftungen
    einzeln, aber mit Aussage-Titeln, Chips und Bildunterschriften."""
    s = re.sub(r"(?s)<svg\b.*?</svg>", " ", inhalt)
    s = re.sub(r"(?s)<form\b.*?</form>", " ", s)
    texte = []
    for m in re.finditer(r"(?s)<(p|h2|h3|li|figcaption|div class=\"stepnum\")[^>]*>(.*?)</(?:p|h2|h3|li|figcaption|div)>", s):
        t = " ".join(htmlmod.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).split())
        if t:
            texte.append(t)
    return texte


def pruefen(inhalt, ss):
    import karussell
    # die Formel 2^(1/12) in der Bildunterschrift ist keine Satzzeichenfrage,
    # und "share on x" ist der Name des Knopfs
    texte = [t.replace("2^(1/12)", "") for t in sichtbare_texte(inhalt)]
    fehler = karussell.text_pruefen(texte)
    for s in ss:
        if not DATUM_RE.search(s["satz"] + " " + s["fcap"] + " " + h2_text(s["h2"])):
            fehler.append("schritt %s ohne datum" % s["id"])
    if re.search(r"\btodo\b|from the series", inhalt, re.I):
        fehler.append("platzhalter im inhalt")
    return fehler


# ---------------------------------------------------------------- einsetzen

def ersetzen(s, marke, neu):
    a, b = "<!--AUTO:%s-->" % marke, "<!--/AUTO:%s-->" % marke
    if a not in s or b not in s:
        raise Abbruch("index.html hat keine marken %s" % a)
    i, j = s.index(a) + len(a), s.index(b)
    return s[:i] + "\n" + neu + "\n" + s[j:]


def bauen(s, D, js=None):
    ss = schritte(D)
    inhalt = inhalt_html(D)
    fehler = pruefen(inhalt, ss)
    if fehler:
        raise Abbruch("wache, %s" % "; ".join(fehler))
    s = ersetzen(s, "menue", menue_html(js))
    return ersetzen(s, "startseite", inhalt)


# ---------------------------------------------------------------- selbsttest

def selbsttest():
    f = []

    def ok(name, bed, info=""):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, ("  " + str(info)) if not bed and info else ""))
        if not bed:
            f.append(name)

    st = dt.date(2026, 10, 19)
    ok("stichtag montag", stichtag(dt.date(2026, 10, 19)) == st)
    ok("stichtag mittwoch", stichtag(dt.date(2026, 10, 21)) == st)
    ok("stichtag sonntag", stichtag(dt.date(2026, 10, 25)) == st)

    # wochenschluesse, 70 wochen steigend, dann 3 rote
    labels = [(dt.date(2025, 6, 1) + dt.timedelta(weeks=i)).isoformat() for i in range(72)]
    closes = [0.05 + 0.0002 * i for i in range(69)] + [0.06, 0.055, 0.05]
    z = zahl_der_woche({"kas_weekly": [[l, c, 0] for l, c in zip(labels, closes)]}, dt.date(2026, 10, 19))
    ok("zahl der woche gerechnet", z is not None and z["rot"] == 3, z and z["rot"])
    ok("zahl der woche datum ist der samstag", z and z["datum"].weekday() == 5, z and z["datum"])
    ok("vorwoche und 13 wochen da", z and z["vorwoche"] and z["q13"])
    z2 = zahl_der_woche({"kas_weekly": [[l, c, 0] for l, c in zip(labels[:55], closes[:55])]}, dt.date(2026, 10, 19))
    ok("zu kurze reihe, kein 13-wochen-chip", z2 and z2["q13"] is None and z2["vorwoche"])
    ok("offene woche zaehlt nicht", zahl_der_woche({"kas_weekly": [[l, c, 0] for l, c in zip(labels, closes)]},
                                                  dt.date.fromisoformat(labels[-1]) + dt.timedelta(days=3))["datum"]
       < dt.date.fromisoformat(labels[-1]))

    # halter mit luecke: 91 tage zurueck fehlt
    tage = [{"datum": (dt.date(2026, 10, 18) - dt.timedelta(days=i)).isoformat(),
             "holders_100kas": 294510 - 40 * i + (130 if i == 0 else 0), "holders_all": 54883401,
             "holders_001kas": 763863} for i in range(30)]
    h = halter(sorted(tage, key=lambda t: t["datum"]))
    ok("halter vorwoche", h["vorwoche"] and h["vorwoche"]["datum"] == dt.date(2026, 10, 11))
    ok("halter 13 wochen fehlt, kein chip", h["q13"] is None)
    ok("halter 7 tage netto", len(h["netto"]) == 7)
    e = emission(st)
    ok("emission naechste senkung 4 nov", e["datum"] == dt.date(2026, 11, 4), e["datum"])
    ok("emission 1,680,086", e["neu"] == 1680086, e["neu"])
    ok("emission vormonat 5 oct", e["vormonat"]["datum"] == dt.date(2026, 10, 5), e["vormonat"])

    D = {"stichtag": st, "zdw": z, "emission": e, "halter": h,
         "kette": {"bps": 9.962, "sek": 600, "datum": dt.date(2026, 10, 19)},
         "gebuehren": {"anteil": 0.133, "von": dt.date(2026, 9, 18), "bis": dt.date(2026, 10, 18)},
         "layer2": {"datum": st, "anteil": 95.05, "vorwoche": {"datum": dt.date(2026, 10, 12), "wert": 93.0},
                    "q13": None},
         "adressen": {"datum": dt.date(2026, 10, 18), "alle": 54883401, "ueber": 763863}}
    ss = schritte(D)
    inhalt = inhalt_html(D)
    ok("sechs schritte", len(ss) == 6)
    ok("wachen gruen", pruefen(inhalt, ss) == [], pruefen(inhalt, ss))
    ok("anker subscribe genau einmal", inhalt.count('id="subscribe"') == 1)
    ok("anmeldung nach schritt 3", inhalt.index('id="emission"') < inhalt.index('id="subscribe"')
       < inhalt.index('id="holders"'))
    ok("utm-felder mit id nur einmal", inhalt.count('id="utmSource"') == 1 and 'data-utm="utmSource"' in inhalt)
    ok("share-link auf genau diesen schritt", "kaspapulse.com%2F%23holders" in inhalt)
    ok("kein platzhalter-chip", "todo" not in inhalt and "from the series" not in inhalt)
    ok("13-wochen-chip fehlt bei layer 2", "<li>12 oct \u00b7 " in inhalt and "<li>20 jul \u00b7 " not in inhalt)
    zc = hero_html(z, st)
    ok("zahl der woche zeigt den alten wert, nicht die differenz",
       "points" not in zc and ("%s \u00b7 " % d_kurz(z["vorwoche"]["datum"], False)) in zc
       and abstand_text(z["vorwoche"]["abstand"]) in zc)
    ok("farbe nach richtung", ('class="dn">%s' % abstand_text(z["vorwoche"]["abstand"])) in zc
       if z["abstand"] < z["vorwoche"]["abstand"] else ('class="up">%s' % abstand_text(z["vorwoche"]["abstand"])) in zc)
    ok("abstand_text", abstand_text(-40.68) == "40.68% below" and abstand_text(12.59) == "12.59% above")
    ok("emission chips vs 5 oct und 5 aug", "vs 5 oct" in inhalt and "vs 5 aug" in inhalt)
    ok("feste groessen ohne chips", '<ul class="cmp"' not in inhalt.split('id="chain"')[1].split("</section>")[0])
    D2 = dict(D, kette=None, gebuehren=None)
    ss2 = schritte(D2)
    in2 = inhalt_html(D2)
    ok("frage fuehrt in den naechsten schritt", 'quoted wrong a lot. <a href="#addresses">' in inhalt_html(dict(D, layer2=None)))
    ok("fehlende daten, schritt faellt weg", len(ss2) == 4 and "1 / 4" in in2 and pruefen(in2, ss2) == [])
    ok("echtzeit-wort faellt auf", pruefen(inhalt.replace("blocks keep landing", "blocks currently land"), ss) != [])
    ok("percent faellt auf", pruefen(inhalt.replace("fees paid", "fees paid 1 percent"), ss) != [])
    ok("counted mit source faellt auf",
       pruefen(inhalt.replace("source kaspalytics.</p>", "counted, source kaspalytics.</p>", 1), ss) != [])
    ok("schritt ohne datum faellt auf",
       any("ohne datum" in x for x in pruefen(inhalt, [dict(ss[1], satz="x", fcap="y", h2="z")])))

    js = ('var MENUE = [\n    { t: "dashboard", h: "/" },\n    { t: "network", k: [\n      ["hashrate", "/a.html"],\n'
          '      ["mining", "/b.html"]\n    ]},\n    { t: "tools", k: [\n      ["wallets", "/c.html"]\n    ]}\n  ];')
    oben, gr = menue_gruppen(js)
    ok("menue oben", oben == [("dashboard", "/")])
    ok("menue gruppen plus about", [g for g, _ in gr] == ["network", "tools", "about"])
    ok("menue aus capture.js hat alle seiten",
       len([p for _, ps in menue_gruppen()[1] for p in ps]) >= 20)
    mh = menue_html(js)
    ok("this week statt dashboard", ">this week</a>" in mh and "dashboard" not in mh)

    s = "<a><!--AUTO:menue-->alt<!--/AUTO:menue--><b><!--AUTO:startseite-->alt<!--/AUTO:startseite-->"
    n1 = bauen(s, D, js)
    ok("bauen ist wiederholbar", bauen(n1, D, js) == n1)
    try:
        bauen("<a>", D, js)
        ok("ohne marken bricht ab", False)
    except Abbruch:
        ok("ohne marken bricht ab", True)
    tg = {"laeufe": [{"datum": "2026-10-21", "messzeit_utc": "2026-10-21T05:30:00+00:00",
                      "messwerte": {"bps": 9.96, "blockrate_sek": 600}}]}
    ok("streng, kein wert nach dem montag", blockrate(tg, dt.date(2026, 10, 19), True) is None)
    ok("nicht streng, der neueste als rueckfall", blockrate(tg, dt.date(2026, 10, 19))["bps"] == 9.96)
    ok("streng, schwellen nur bis zum montag", schwellen({"tage": tage}, dt.date(2026, 9, 1), True) == [])
    ok("zahl verlinkt auf method", 'href="/method/#holders"><em>' in inhalt)
    ok("share-link einer wochenseite zeigt auf die woche",
       "week%2F2026-10-19%2F%23holders" in inhalt_html(D, SEITE + "week/2026-10-19/",
                                                     {"oben": "x 19 oct", "unten": ""}))
    ok("layer 2 bleibt draussen, solange LAYER2 aus ist", LAYER2 or daten()["layer2"] is None)
    try:
        echt = bauen(INDEX.read_text(encoding="utf-8"), daten())
        ok("index.html baut mit den echten daten", "<section class=\"step\"" in echt)
    except Abbruch as exc:
        ok("index.html baut mit den echten daten", False, exc)

    print("")
    print("%d fehler" % len(f) if f else "alle testfaelle bestanden")
    return 1 if f else 0


# ---------------------------------------------------------------- ansehen

ANSICHTEN = (("handy", 360, 640), ("desktop", 1280, 800))


def ansehen(ziel, seite="index.html"):
    """Bilder fuer den Kontaktbogen, Handy 360 x 640 und Desktop, hell und dunkel,
    dazu zwei Messungen, die ein Bild allein nicht zeigt: kein Querscrollen, und
    das aufgeklappte Menue passt auf dem Handy ohne Scrollen auf den Schirm."""
    import functools
    import http.server
    import threading
    from playwright.sync_api import sync_playwright
    ziel = Path(ziel)
    ziel.mkdir(parents=True, exist_ok=True)
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(REPO))
    http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d/%s" % (srv.server_port, "" if seite == "index.html" else seite)
    fehler = []
    with sync_playwright() as p:
        import number_of_day
        b = number_of_day.chromium_start(p)
        for name, w, hh in ANSICHTEN:
            for look in ("light", "dark"):
                c = b.new_context(viewport={"width": w, "height": hh}, color_scheme=look,
                                  device_scale_factor=2 if name == "handy" else 1)
                # fremde adressen (brevo) bleiben draussen, die seite laedt nichts von dritten
                c.route(lambda u: not u.startswith("http://127.0.0.1"), lambda r: r.abort())
                pg = c.new_page()
                # die einblendung von capture.js gehoert nicht ins bild
                pg.add_init_script("try{localStorage.setItem('kp_capture','{\"snooze\":%d}')}catch(e){}"
                                   % (int(dt.datetime.now().timestamp() * 1000)))
                pg.goto(url, wait_until="networkidle")
                pg.evaluate("document.fonts.ready")
                pg.evaluate("document.querySelectorAll('section.step').forEach(s=>s.classList.add('seen'))")
                pg.wait_for_timeout(600)
                quer = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                if quer > 0:
                    fehler.append("%s %s, querscrollen %d px" % (name, look, quer))
                pg.screenshot(path=str(ziel / ("%s-%s-oben.png" % (name, look))))
                pg.screenshot(path=str(ziel / ("%s-%s-ganz.png" % (name, look))), full_page=True)
                if name == "handy":
                    pg.click(".burger")
                    m = pg.evaluate("(()=>{const m=document.getElementById('menu');"
                                    "return {s:m.scrollHeight,c:m.clientHeight,u:m.getBoundingClientRect().bottom,"
                                    "h:innerHeight}})()")
                    if m["s"] > m["c"] or m["u"] > m["h"]:
                        fehler.append("%s %s, menue passt nicht, %s" % (name, look, m))
                    pg.screenshot(path=str(ziel / ("%s-%s-menue.png" % (name, look))))
                else:
                    pg.hover(".grp >> nth=0")
                    pg.screenshot(path=str(ziel / ("%s-%s-menue.png" % (name, look))))
                c.close()
        b.close()
    srv.shutdown()
    return fehler


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--pruefen", action="store_true")
    ap.add_argument("--ansehen", metavar="ORDNER")
    ap.add_argument("--heute")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.ansehen:
        fehler = ansehen(a.ansehen)
        for x in fehler:
            print("FEHL %s" % x)
        print("bilder in %s" % a.ansehen)
        return 1 if fehler else 0
    heute = dt.date.fromisoformat(a.heute) if a.heute else None
    alt = INDEX.read_text(encoding="utf-8")
    try:
        neu = bauen(alt, daten(heute))
    except Abbruch as exc:
        print("ABBRUCH %s, index.html bleibt wie sie ist" % exc)
        return 1
    import archiv
    if a.pruefen:
        if neu != alt:
            print("index.html weicht vom stand der daten ab, python3 scripts/startseite.py laufen lassen")
            return 1
        print("index.html passt zu den daten")
        # die wochenseiten, das archiv und method haengen am rahmen der startseite
        return archiv.schreiben(heute, nur_pruefen=True)
    if neu != alt:
        INDEX.write_text(neu, encoding="utf-8")
        print("index.html neu gebaut, stichtag %s" % stichtag(heute or dt.date.today()))
    else:
        print("index.html unveraendert")
    return archiv.schreiben(heute)


if __name__ == "__main__":
    sys.exit(main())
