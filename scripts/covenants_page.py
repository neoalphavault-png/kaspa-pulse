#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""covenants_page.py, schreibt die Zahlen aus dem Log in die Seite.

Auf kaspa-covenants.html stehen Zahlen. Sie koennten per fetch() aus
data/covenants-log.json nachgeladen werden, so wie auf entity-x.html der
Kontostand. Bei einer Tagesreihe ist das die schlechtere Wahl: wer die
Seite ohne Javascript oeffnet, und jeder Crawler, der sie indiziert, saehe
Striche statt Zahlen, und die Seite koennte behaupten, was sie will, ohne
dass es jemandem auffiele.

Deshalb wird gerendert. Dieses Skript liest data/covenants-log.json und
schreibt die Zahlen, die beiden Diagramme und die Tabelle direkt in den
Quelltext der Seite, zwischen Markierungen der Form

    <!--AUTO:kopf-->  ...  <!--/AUTO:kopf-->

Alles ausserhalb dieser Markierungen bleibt unberuehrt, der Lauf ist also
wiederholbar und die Handarbeit an der Seite ueberlebt ihn.

DER PRUEFLAUF
    python3 scripts/covenants_page.py --check
rendert ein zweites Mal ins Gedaechtnis und vergleicht. Er prueft zwei
Dinge, und beide sind der Grund, warum es ihn gibt:

  1. Steht auf der Seite dasselbe, was das Rendern jetzt erzeugen wuerde?
     Wenn nicht, wurde die Seite von Hand angefasst oder das Log hat sich
     seit dem letzten Rendern bewegt.
  2. Steht in jeder gerenderten Zahl der Wert, der im Log steht? Dafuer
     traegt jede Zahl im Quelltext ein data-v-Feld mit ihrem Namen. Der
     Pruefer liest die Zahlen aus dem HTML zurueck und stellt sie gegen
     das Log. Eine Seite, die ihre eigene Quelle widerlegt, faellt hier
     durch und nicht erst beim Leser.

    python3 scripts/covenants_page.py            # rendern
    python3 scripts/covenants_page.py --check    # pruefen, nichts schreiben
    python3 scripts/covenants_page.py --selftest # ohne dateien
"""

import argparse
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LOG = os.path.join(REPO, "data", "covenants-log.json")
SEITE = os.path.join(REPO, "kaspa-covenants.html")

TOCCATA = dt.date(2026, 6, 30)

MONATE = ["jan", "feb", "mar", "apr", "may", "jun",
          "jul", "aug", "sep", "oct", "nov", "dec"]

# chartmasse, dieselben wie auf kaspa-weekly.html
W, H = 720, 300
PL, PR, PT, PB = 10, 10, 16, 26


def zahl(n):
    return "{:,}".format(int(n)).replace(",", ",")


def datum_lang(s):
    t = dt.date.fromisoformat(s)
    return "%d %s %d" % (t.day, MONATE[t.month - 1], t.year)


def datum_kurz(s):
    t = dt.date.fromisoformat(s)
    return "%d %s" % (t.day, MONATE[t.month - 1])


def lade(pfad=LOG):
    with open(pfad, encoding="utf-8") as fh:
        return json.load(fh)


def feld(tage, name):
    """(datum, wert) aller tage, die fuer dieses feld einen wert haben."""
    return [(e["datum"], e[name]) for e in tage
            if e.get(name) is not None]


def seit_toccata(paare):
    return [(d, v) for d, v in paare if dt.date.fromisoformat(d) >= TOCCATA]


def v(name, text):
    """eine gerenderte zahl, die sich zurueckpruefen laesst."""
    return '<span data-v="%s">%s</span>' % (name, text)


# ------------------------------------------------------------------ diagramme

def balken(paare, farbe="#49EACB", label=""):
    """Tagessummen als Balken. Ein Balken je Tag, nichts geglaettet, nichts
    zusammengefasst. Der Saegezahn IST das Ergebnis; ein gleitender Schnitt
    darueber wuerde genau die Aussage wegwischen, wegen der die Reihe
    ueberhaupt gefuehrt wird."""
    if not paare:
        return '<text x="20" y="40" fill="#5C6672" font-size="12">keine daten</text>'
    n = len(paare)
    hoch = max(x for _, x in paare) or 1
    breite = (W - PL - PR) / n
    bb = max(1.0, breite - 1.0)

    def y(val):
        return PT + (H - PT - PB) * (1 - val / hoch)

    teile = []
    # waagerechte hilfslinien, drei stueck, damit die hoehe lesbar bleibt
    for anteil in (0.25, 0.5, 0.75, 1.0):
        wert = hoch * anteil
        yy = y(wert)
        teile.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#1A1D21" stroke-width="1"/>'
                     % (PL, W - PR, yy, yy))
        teile.append('<text x="%d" y="%.1f" fill="#5C6672" font-size="10" text-anchor="end" '
                     'font-family="Helvetica Neue,Arial,sans-serif">%s</text>'
                     % (W - PR, yy - 4, zahl(round(wert))))
    for i, (tag, wert) in enumerate(paare):
        x = PL + i * breite
        hh = max(0.8, (H - PT - PB) - (y(wert) - PT))
        teile.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" rx="0.8">'
                     '<title>%s · %s %s</title></rect>'
                     % (x, y(wert), bb, hh, farbe, datum_kurz(tag), zahl(wert), label))
    teile.append(zeitachse(paare))
    return "".join(teile)


def linie(paare, farbe="#49EACB"):
    """Ein Bestand als Linie mit Flaeche darunter. Die Skala beginnt bei
    null und nicht am kleinsten Wert: bei einem Bestand ist der Abstand zur
    Null die Aussage, und eine abgeschnittene Achse macht aus jedem
    Wachstum eine Rakete."""
    if not paare:
        return '<text x="20" y="40" fill="#5C6672" font-size="12">keine daten</text>'
    n = len(paare)
    hoch = max(x for _, x in paare) or 1

    def x(i):
        return PL + (W - PL - PR) * (i / max(1, n - 1))

    def y(val):
        return PT + (H - PT - PB) * (1 - val / hoch)

    teile = []
    for anteil in (0.25, 0.5, 0.75, 1.0):
        wert = hoch * anteil
        yy = y(wert)
        teile.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#1A1D21" stroke-width="1"/>'
                     % (PL, W - PR, yy, yy))
        teile.append('<text x="%d" y="%.1f" fill="#5C6672" font-size="10" text-anchor="end" '
                     'font-family="Helvetica Neue,Arial,sans-serif">%s</text>'
                     % (W - PR, yy - 4, zahl(round(wert))))
    d = " ".join("%s%.1f %.1f" % ("M" if i == 0 else "L", x(i), y(val))
                 for i, (_, val) in enumerate(paare))
    flaeche = d + " L%.1f %.1f L%.1f %.1f Z" % (x(n - 1), H - PB, x(0), H - PB)
    teile.append('<path d="%s" fill="%s" fill-opacity="0.12"/>' % (flaeche, farbe))
    teile.append('<path d="%s" fill="none" stroke="%s" stroke-width="2" '
                 'stroke-linejoin="round"/>' % (d, farbe))
    teile.append(zeitachse(paare))
    return "".join(teile)


def zeitachse(paare):
    """Beschriftet den ersten Tag jedes Monats, dazu den letzten Tag."""
    teile = []
    gesetzt = set()
    n = len(paare)
    for i, (tag, _) in enumerate(paare):
        t = dt.date.fromisoformat(tag)
        if t.month in gesetzt:
            continue
        gesetzt.add(t.month)
        x = PL + (W - PL - PR) * (i / max(1, n - 1))
        teile.append('<text x="%.1f" y="%d" fill="#5C6672" font-size="10" text-anchor="middle" '
                     'font-family="Helvetica Neue,Arial,sans-serif">%s</text>'
                     % (min(max(x, 18), W - 30), H - 6, MONATE[t.month - 1]))
    letzter = paare[-1][0]
    teile.append('<text x="%d" y="%d" fill="#5C6672" font-size="10" text-anchor="end" '
                 'font-family="Helvetica Neue,Arial,sans-serif">%s</text>'
                 % (W - PR, H - 6, datum_kurz(letzter)))
    return "".join(teile)


# ------------------------------------------------------------------ bloecke

def bloecke(log):
    """Alle Markierungsbloecke als {name: inhalt}."""
    tage = log.get("tage", [])
    tx = feld(tage, "tx")
    utxo = feld(tage, "utxo_count")
    outp = feld(tage, "outputs")
    tx_t = seit_toccata(tx)
    utxo_t = seit_toccata(utxo)
    outp_t = seit_toccata(outp)

    letzte_utxo_tag, letzte_utxo = utxo[-1] if utxo else (None, None)
    letzte_tx_tag, letzte_tx = tx[-1] if tx else (None, None)

    sieben = [x for _, x in tx[-7:]]
    schnitt7 = round(sum(sieben) / len(sieben)) if sieben else 0
    ruhig_tag, ruhig = min(tx_t, key=lambda p: p[1]) if tx_t else (None, None)
    laut_tag, laut = max(tx_t, key=lambda p: p[1]) if tx_t else (None, None)
    summe_tx = sum(x for _, x in tx_t)
    summe_out = sum(x for _, x in outp_t)
    erster_utxo = utxo_t[0][1] if utxo_t else None

    aus = {}

    aus["kopf"] = (
        '<div class="lbl">covenant utxos on the kaspa network</div>\n'
        '    <div class="bal">%s</div>\n'
        '    <div class="usd">unspent outputs bound to a covenant id, as of %s</div>\n'
        '    <div class="upd">counted by Kaspalytics, logged daily by Kaspa Pulse</div>'
        % (v("utxo_count", zahl(letzte_utxo)), v("utxo_datum", datum_lang(letzte_utxo_tag)))
    )

    aus["kacheln"] = (
        '<div class="fact"><div class="v teal">%s</div>'
        '<div class="l">covenant transactions on %s, the last full day in the log</div></div>\n'
        '    <div class="fact"><div class="v">%s</div>'
        '<div class="l">average per day over the last seven full days</div></div>\n'
        '    <div class="fact"><div class="v">%s</div>'
        '<div class="l">the busiest single day so far, %s</div></div>\n'
        '    <div class="fact"><div class="v">%s</div>'
        '<div class="l">the quietest single day so far, %s</div></div>'
        % (v("tx_letzter", zahl(letzte_tx)), v("tx_datum", datum_lang(letzte_tx_tag)),
           v("tx_schnitt7", zahl(schnitt7)),
           v("tx_max", zahl(laut)), v("tx_max_datum", datum_lang(laut_tag)),
           v("tx_min", zahl(ruhig)), v("tx_min_datum", datum_lang(ruhig_tag)))
    )

    aus["txchart"] = balken(tx_t, "#E8B04B", "transactions")
    aus["utxochart"] = linie(utxo_t, "#49EACB")

    aus["summe"] = (
        '<p>Since Toccata activated on 30 June 2026, the log holds '
        '<b>%s</b> days. In that window the chain recorded '
        '<b>%s covenant transactions</b> and <b>%s covenant outputs</b>. '
        'The covenant UTXO count went from <b>%s</b> on the first day after '
        'activation to <b>%s</b> on %s.</p>'
        % (v("tage_seit", zahl(len(tx_t))),
           v("tx_summe", zahl(summe_tx)),
           v("outputs_summe", zahl(summe_out)),
           v("utxo_erster", zahl(erster_utxo)),
           v("utxo_count2", zahl(letzte_utxo)),
           v("utxo_datum2", datum_lang(letzte_utxo_tag)))
    )

    zeilen = []
    for e in tage[-14:][::-1]:
        zeilen.append(
            '<tr><td>%s</td><td class="n">%s</td><td class="n">%s</td><td class="n">%s</td></tr>'
            % (datum_lang(e["datum"]),
               zahl(e["tx"]) if e.get("tx") is not None else "—",
               zahl(e["outputs"]) if e.get("outputs") is not None else "—",
               zahl(e["utxo_count"]) if e.get("utxo_count") is not None else "—"))
    aus["tabelle"] = "\n      ".join(zeilen)

    aus["stand"] = (
        'counted by Kaspalytics, logged daily by Kaspa Pulse · '
        'last reading %s · log written %s'
        % (v("stand_datum", datum_lang(letzte_utxo_tag)),
           v("stand_abruf", log.get("aktualisiert_utc", "")[:10]))
    )
    return aus


MARKE = re.compile(r"(<!--AUTO:([a-z0-9_]+)-->)(.*?)(<!--/AUTO:\2-->)", re.S)


def rendere(html, log):
    inhalte = bloecke(log)
    fehlend = []

    def ersatz(m):
        name = m.group(2)
        if name not in inhalte:
            fehlend.append(name)
            return m.group(0)
        return m.group(1) + inhalte[name] + m.group(4)

    neu = MARKE.sub(ersatz, html)
    gefunden = set(m.group(2) for m in MARKE.finditer(html))
    unbenutzt = sorted(set(inhalte) - gefunden)
    return neu, fehlend, unbenutzt


# ------------------------------------------------------------------ pruefung

WERT = re.compile(r'<span data-v="([a-z0-9_]+)">([^<]*)</span>')


def entzahl(s):
    s = s.strip().replace(",", "")
    return int(s) if re.fullmatch(r"\d+", s) else None


def pruefe(html, log):
    """stellt jede gerenderte zahl gegen das log. gibt eine liste von
    beanstandungen zurueck, leer heisst sauber."""
    tage = log.get("tage", [])
    tx = feld(tage, "tx")
    utxo = feld(tage, "utxo_count")
    outp = feld(tage, "outputs")
    tx_t = seit_toccata(tx)
    utxo_t = seit_toccata(utxo)
    outp_t = seit_toccata(outp)
    sieben = [x for _, x in tx[-7:]]

    soll = {
        "utxo_count": utxo[-1][1],
        "utxo_count2": utxo[-1][1],
        "utxo_datum": datum_lang(utxo[-1][0]),
        "utxo_datum2": datum_lang(utxo[-1][0]),
        "utxo_erster": utxo_t[0][1],
        "tx_letzter": tx[-1][1],
        "tx_datum": datum_lang(tx[-1][0]),
        "tx_schnitt7": round(sum(sieben) / len(sieben)),
        "tx_max": max(x for _, x in tx_t),
        "tx_min": min(x for _, x in tx_t),
        "tx_max_datum": datum_lang(max(tx_t, key=lambda p: p[1])[0]),
        "tx_min_datum": datum_lang(min(tx_t, key=lambda p: p[1])[0]),
        "tx_summe": sum(x for _, x in tx_t),
        "outputs_summe": sum(x for _, x in outp_t),
        "tage_seit": len(tx_t),
        "stand_datum": datum_lang(utxo[-1][0]),
        "stand_abruf": log.get("aktualisiert_utc", "")[:10],
    }

    gefunden = dict(WERT.findall(html))
    beschwerden = []
    for name, wert in soll.items():
        if name not in gefunden:
            beschwerden.append("%s steht nicht auf der seite" % name)
            continue
        ist = gefunden[name]
        if isinstance(wert, int):
            if entzahl(ist) != wert:
                beschwerden.append("%s: seite sagt %r, log sagt %s" % (name, ist, wert))
        elif ist.strip() != str(wert).strip():
            beschwerden.append("%s: seite sagt %r, log sagt %r" % (name, ist, wert))
    for name in gefunden:
        if name not in soll:
            beschwerden.append("%s steht auf der seite, aber nicht im pruefer" % name)

    # die letzte tabellenzeile muss der letzte tag im log sein
    letzte = tage[-1]
    if datum_lang(letzte["datum"]) not in html:
        beschwerden.append("der letzte tag des logs steht nicht in der tabelle")
    return beschwerden


# ------------------------------------------------------------------ selftest

def _log_stub():
    tage = []
    for i in range(10):
        t = dt.date(2026, 6, 28) + dt.timedelta(days=i)
        tage.append({"datum": str(t), "tx": 100 + i * 10, "outputs": 200 + i * 10,
                     "outputs_created": 200 + i * 10, "outputs_spent": 5,
                     "utxo_count": 1000 + i * 100,
                     "quelle": "kaspalytics", "abgerufen_utc": "2026-07-08T06:40:00+00:00"})
    return {"quelle": "kaspalytics", "aktualisiert_utc": "2026-07-08T06:40:00+00:00",
            "toccata_aktiv_seit": "2026-06-30", "tage": tage}


def run_selftest():
    fails = []

    def check(name, ist, soll):
        if ist != soll:
            fails.append("%s\n    ist  %r\n    soll %r" % (name, ist, soll))

    log = _log_stub()
    roh = ("<html><body>"
           "<!--AUTO:kopf--><!--/AUTO:kopf-->"
           "<!--AUTO:kacheln--><!--/AUTO:kacheln-->"
           "<svg><!--AUTO:txchart--><!--/AUTO:txchart--></svg>"
           "<svg><!--AUTO:utxochart--><!--/AUTO:utxochart--></svg>"
           "<!--AUTO:summe--><!--/AUTO:summe-->"
           "<table><!--AUTO:tabelle--><!--/AUTO:tabelle--></table>"
           "<!--AUTO:stand--><!--/AUTO:stand-->"
           "</body></html>")
    neu, fehlend, unbenutzt = rendere(roh, log)
    check("alle bloecke bedient", fehlend, [])
    check("kein block uebrig", unbenutzt, [])
    check("pruefung geht durch", pruefe(neu, log), [])

    # zweimal rendern gibt dasselbe, sonst waere der lauf nicht wiederholbar
    check("rendern ist wiederholbar", rendere(neu, log)[0], neu)

    # der letzte utxo-wert steht im quelltext, nicht nur als platzhalter
    check("die zahl steht im quelltext", '>1,900<' in neu, True)
    check("das datum steht dabei", "7 jul 2026" in neu, True)

    # die zwei tage VOR toccata zaehlen nicht in die summenzeile
    # (stub beginnt am 28.06., toccata am 30.06., bleiben acht tage)
    check("tage seit toccata", '<span data-v="tage_seit">8</span>' in neu, True)

    # ein verbogener wert faellt der pruefung auf
    verbogen = neu.replace('<span data-v="utxo_count">1,900</span>',
                           '<span data-v="utxo_count">9,900</span>')
    b = pruefe(verbogen, log)
    check("verbogene zahl faellt auf", len(b), 1)
    check("und wird benannt", "utxo_count" in b[0], True)

    # eine geloeschte zahl ebenso
    ohne = neu.replace('<span data-v="tx_max">', '<span data-x="tx_max">')
    check("fehlende zahl faellt auf",
          any("tx_max steht nicht" in x for x in pruefe(ohne, log)), True)

    # ein leeres log bringt die seite nicht zum absturz
    leer = {"quelle": "kaspalytics", "aktualisiert_utc": "", "tage": []}
    try:
        rendere(roh, leer)
        check("leeres log wirft", True, False)
    except (IndexError, ValueError, TypeError):
        check("leeres log wirft", True, True)

    # die balken sind einzelne tage, nichts zusammengefasst
    n_rect = neu.count("<rect")
    check("ein balken je tag seit toccata", n_rect, 8)

    if fails:
        print("selftest FEHLGESCHLAGEN")
        for f in fails:
            print("  " + f)
        return 1
    print("selftest ok, 12 faelle")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", default=LOG)
    ap.add_argument("--seite", default=SEITE)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return run_selftest()

    log = lade(a.log)
    with open(a.seite, encoding="utf-8") as fh:
        alt = fh.read()
    neu, fehlend, unbenutzt = rendere(alt, log)

    if a.check:
        schlecht = []
        if fehlend:
            schlecht.append("bloecke ohne inhalt: %s" % fehlend)
        if unbenutzt:
            schlecht.append("inhalte ohne block auf der seite: %s" % unbenutzt)
        if neu != alt:
            schlecht.append("die seite ist nicht auf dem stand des logs, "
                            "scripts/covenants_page.py laufen lassen")
        schlecht += pruefe(alt, log)
        if schlecht:
            print("pruefung FEHLGESCHLAGEN")
            for s in schlecht:
                print("  " + s)
            return 1
        gezaehlt = len(WERT.findall(alt))
        print("pruefung ok, %d zahlen auf der seite stimmen mit dem log ueberein"
              % gezaehlt)
        print("  letzter tag im log  %s" % log["tage"][-1]["datum"])
        return 0

    if fehlend:
        print("FEHL bloecke ohne inhalt: %s" % fehlend)
        return 1
    if neu == alt:
        print("seite war schon auf dem stand des logs")
        return 0
    with open(a.seite, "w", encoding="utf-8") as fh:
        fh.write(neu)
    print("seite gerendert, %d zahlen geschrieben, letzter tag %s"
          % (len(WERT.findall(neu)), log["tage"][-1]["datum"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
