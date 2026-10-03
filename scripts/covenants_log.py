#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""covenants_log.py, die Tagesreihe der Covenants.

Toccata ist am 30.06.2026 auf dem Mainnet aktiv geworden. Seitdem gibt es
Covenants, und seitdem gibt es die Frage, ob sie jemand benutzt. Kaspalytics
zaehlt das taeglich und laedt seine drei Diagramme selbst per JSON, oeffentlich,
ohne Anmeldung. Diese Datei holt die drei Reihen und schreibt sie in eine
eigene Datei, Tag fuer Tag, damit die Reihe auch dann noch steht, wenn das
Fenster der Quelle irgendwann weiterwandert.

    /app/covenants/transactions   ist die seite
    /api/charts/covenants/transactions   sind die daten dazu
    /api/charts/covenants/outputs        reihen Created und Spent
    /api/charts/utxo/covenant-count      reihe "Covenant UTXOs"

Die dritte liegt NICHT unter /covenants/, sondern unter /utxo/. Das ist kein
Tippfehler und war am 22.09. die Stelle, an der drei geratene Pfade
nacheinander 404 gesagt haben. Gefunden wurde sie erst in der Seitenleiste
der Seite selbst, wo der Eintrag "Covenant UTXO Count" auf
/app/utxo/covenant-count zeigt.

ZWEI ARTEN VON ZAHL, UND SIE TRAGEN IHR DATUM VERSCHIEDEN
Transaktionen und Outputs sind Tagessummen. Ihr Zeitstempel steht auf
Mitternacht des Tages, den sie zaehlen, also gehoert 2026-09-21T00:00:00Z
zum 21.09.

Die UTXO-Anzahl ist ein Bestand, eine Momentaufnahme, und die Quelle nimmt
sie um Mitternacht mit ein paar Sekunden Schlupf in die eine oder andere
Richtung:

    2026-06-26T23:59:59.920Z   ist der stand am ende des 26.
    2026-06-28T00:00:02.106Z   ist der stand am ende des 27.

Wer hier nur das Datum aus dem Zeitstempel nimmt, schreibt jede zweite
Messung einen Tag zu spaet und baut sich eine Reihe mit Loechern und
Doppeltagen. Deshalb wird der Zeitstempel um eine Stunde vorgestellt und
dann ein Tag abgezogen, siehe stichtag_bestand().

REGELN, DIE HIER DRINSTECKEN
  1. Der laufende Tag wird nie gelesen. Er ist angebrochen, seine Summe ist
     noch keine Summe. Gelesen wird bis einschliesslich gestern.
  2. Jede Zahl faellt durch ein Plausibilitaetsfenster. Lieber ein Feld leer
     als ein falsches.
  3. Faellt eine der drei Quellen aus, bleiben die anderen beiden stehen.
  4. Was einmal im Log steht, wird nicht stillschweigend ueberschrieben.
     Aendert die Quelle einen alten Wert, wird er uebernommen UND das Feld
     abgerufen_utc des Tages zieht mit, damit im Log sichtbar bleibt, dass
     dieser Tag spaeter noch einmal angefasst wurde.
  6. Ein Bestandspunkt zaehlt nur, wenn er hoechstens zwei Stunden neben
     Mitternacht liegt (Ben, 03.10.2026). Am 30.09. hat die Quelle um
     12:02:05 UTC gemessen statt um Mitternacht; der Wert 13.342 landete als
     Stand vom 29.09. im Log und ging so oeffentlich raus. Liegt ein Punkt
     weiter weg, bleibt der Tag beim Bestand leer, und das steht als Problem
     im Lauf. Der Zeitstempel der Quelle steht als stand_utc an jedem Tag.
  5. Rueckwirkend gefuellt wird, soweit die Quelle Historie hergibt. Am
     22.09.2026 waren das 88 Tage zurueck bis zum 26.06., also vier Tage vor
     Toccata. Weiter zurueck hat die Quelle nichts, und erfunden wird nichts.

    python3 scripts/covenants_log.py             # holen und schreiben
    python3 scripts/covenants_log.py --selftest  # ohne netz
"""

import argparse
import datetime as dt
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ZIEL = os.path.join(REPO, "data", "covenants-log.json")

BASIS = "https://www.kaspalytics.com/api/charts/"
TIMEOUT = 25
VERSUCHE = 3

TOCCATA = dt.date(2026, 6, 30)

# feld -> (pfad, reihenname, art)
#   "fluss"   tagessumme, zeitstempel traegt den tag selbst
#   "bestand" momentaufnahme um mitternacht, siehe kopf
QUELLEN = {
    "tx":              ("covenants/transactions", "Transactions",   "fluss"),
    "outputs_created": ("covenants/outputs",      "Created",        "fluss"),
    "outputs_spent":   ("covenants/outputs",      "Spent",          "fluss"),
    "utxo_count":      ("utxo/covenant-count",    "Covenant UTXOs", "bestand"),
}

FENSTER = {
    "tx":              (0, 5e6),
    "outputs_created": (0, 5e7),
    "outputs_spent":   (0, 5e7),
    "utxo_count":      (0, 5e7),
}

QUELLENNAME = "kaspalytics"


def hole(pfad):
    """eine antwort holen. drei versuche, dann ehrlich scheitern."""
    url = BASIS + pfad
    letzter = None
    for _ in range(VERSUCHE):
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/json",
                "User-Agent": "kaspa-pulse-bot (+https://kaspapulse.com)",
            })
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:      # noqa: BLE001
            letzter = exc
    raise RuntimeError("%s nicht erreichbar, %s" % (pfad, letzter))


def zeit_von(label):
    """aus dem zeitstempel ein datum-mit-uhrzeit in UTC."""
    s = str(label).replace("Z", "+00:00")
    t = dt.datetime.fromisoformat(s)
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t.astimezone(dt.timezone.utc)


def stichtag_fluss(label):
    """tagessumme: der zeitstempel traegt den tag, den er zaehlt."""
    return zeit_von(label).date()


BESTAND_SCHLUPF = dt.timedelta(hours=2)        # regel 6


def naechste_mitternacht(label):
    t = zeit_von(label)
    m = dt.datetime.combine(t.date(), dt.time(), tzinfo=dt.timezone.utc)
    return m if t - m <= m + dt.timedelta(days=1) - t else m + dt.timedelta(days=1)


def abstand_mitternacht(label):
    return abs(zeit_von(label) - naechste_mitternacht(label))


def stichtag_bestand(label):
    """momentaufnahme um mitternacht, mit schlupf in beide richtungen.
    die naechste mitternacht, dann einen tag zurueck: aus 23:59:59 des 26.
    wird der 26., aus 00:00:02 des 28. wird der 27. ob der punkt nah genug
    an mitternacht liegt, prueft bestandsreihe() (regel 6)."""
    return naechste_mitternacht(label).date() - dt.timedelta(days=1)


def reihe(daten, name):
    for d in daten.get("datasets") or []:
        if str(d.get("label", "")).strip().lower() == name.strip().lower():
            return d.get("data") or []
    raise RuntimeError("reihe %s nicht gefunden" % name)


def tagesreihe(daten, name, art, bis):
    """gibt {datum: wert} fuer alle tage bis einschliesslich 'bis'.
    Der laufende tag faellt raus, siehe regel 1. Kommt ein tag doppelt vor,
    gewinnt der spaetere zeitstempel; das passiert, wenn die quelle einmal
    zweimal am selben tag gemessen hat."""
    labels = daten.get("labels") or []
    werte = reihe(daten, name)
    stichtag = stichtag_fluss if art == "fluss" else stichtag_bestand
    aus, gesehen = {}, {}
    for i, lab in enumerate(labels):
        try:
            t = zeit_von(lab)
            tag = stichtag(lab)
        except ValueError:
            continue
        if tag > bis:
            continue
        if i >= len(werte) or werte[i] is None:
            continue
        if tag in gesehen and gesehen[tag] >= t:
            continue
        gesehen[tag] = t
        aus[tag] = float(werte[i])
    return aus


def bestandsreihe(daten, name, bis):
    """wie tagesreihe, aber nur punkte hoechstens BESTAND_SCHLUPF neben
    mitternacht (regel 6). gibt (werte, stand, neben) zurueck: {tag: wert},
    {tag: zeitstempel der quelle} und {tag: label} der punkte, die zu weit
    neben mitternacht lagen und fuer die es keinen gueltigen punkt gibt."""
    labels = daten.get("labels") or []
    werte = reihe(daten, name)
    aus, stand, gesehen, neben = {}, {}, {}, {}
    for i, lab in enumerate(labels):
        try:
            t = zeit_von(lab)
            tag = stichtag_bestand(lab)
        except ValueError:
            continue
        if tag > bis or i >= len(werte) or werte[i] is None:
            continue
        if abstand_mitternacht(lab) > BESTAND_SCHLUPF:
            # der tag, auf den die alte regel (+1 h, dann einen tag zurueck)
            # den punkt gelegt haette; so kam 30.09. 12:02 auf den 29.09.
            neben[(t + dt.timedelta(hours=1)).date() - dt.timedelta(days=1)] = lab
            continue
        if tag in gesehen and gesehen[tag] >= t:
            continue
        gesehen[tag] = t
        aus[tag] = float(werte[i])
        stand[tag] = t.isoformat(timespec="seconds").replace("+00:00", "Z")
    # jeder tag zwischen dem ersten und letzten gueltigen punkt ohne eigenen
    # punkt ist eine luecke, auch wenn die quelle ihn ganz ausgelassen hat
    if aus:
        d = min(aus)
        while d < max(aus):
            if d not in aus and d not in neben:
                neben[d] = "kein punkt"
            d += dt.timedelta(days=1)
    return aus, stand, {k: v for k, v in neben.items() if k not in aus}


def plausibel(feld, wert):
    lo, hi = FENSTER[feld]
    return lo <= wert <= hi


def sammle(heute=None, holer=None):
    """alle vier felder als {datum: {feld: wert}}, dazu die probleme."""
    heute = heute or dt.datetime.now(dt.timezone.utc).date()
    bis = heute - dt.timedelta(days=1)          # regel 1
    holer = holer or hole
    roh, probleme = {}, []
    puffer = {}
    for feld, (pfad, name, art) in QUELLEN.items():
        try:
            if pfad not in puffer:
                puffer[pfad] = holer(pfad)
            if art == "bestand":
                reihe_tage, stand, neben = bestandsreihe(puffer[pfad], name, bis)
            else:
                reihe_tage, stand, neben = tagesreihe(puffer[pfad], name, art, bis), {}, {}
        except Exception as exc:      # noqa: BLE001
            probleme.append("%s, %s" % (feld, exc))
            continue
        for tag, lab in sorted(neben.items()):
            # bewusste luecke: None heisst "quelle hat geantwortet, aber
            # keinen gueltigen punkt", und ersetzt einen alten wert im log
            roh.setdefault(tag, {})[feld] = None
            roh[tag]["stand_utc"] = None
            if lab == "kein punkt":
                probleme.append("%s, %s bleibt leer, die quelle hat keinen punkt" % (feld, tag))
                continue
            ab = abstand_mitternacht(lab)
            probleme.append("%s, %s bleibt leer, der punkt %s liegt %d h %02d min neben mitternacht"
                            % (feld, tag, lab, ab.seconds // 3600, ab.seconds % 3600 // 60))
        for tag, t in stand.items():
            roh.setdefault(tag, {})["stand_utc"] = t
        verworfen = 0
        for tag, wert in reihe_tage.items():
            if not plausibel(feld, wert):
                verworfen += 1
                continue
            roh.setdefault(tag, {})[feld] = int(round(wert))
        if verworfen:
            probleme.append("%s, %d werte ausserhalb des fensters verworfen"
                            % (feld, verworfen))
        if not reihe_tage:
            probleme.append("%s, kein einziger vollstaendiger tag" % feld)
    return roh, probleme


def lade_log(pfad=ZIEL):
    if not os.path.exists(pfad):
        return {"quelle": QUELLENNAME, "endpunkte": {}, "tage": []}
    with open(pfad, encoding="utf-8") as fh:
        return json.load(fh)


def verschmelze(log, roh, jetzt):
    """neue tage anhaengen, geaenderte tage nachziehen, alles andere in
    ruhe lassen. gibt (log, neu, geaendert) zurueck."""
    nach_tag = {e["datum"]: e for e in log.get("tage", [])}
    neu = geaendert = 0
    for tag in sorted(roh):
        schluessel = str(tag)
        # nur felder, die dieser lauf fuer den tag hat. fehlt ein feld, weil
        # seine quelle tot war, bleibt der alte wert stehen (regel 3). None
        # ist eine bewusste luecke (regel 6) und ersetzt den alten wert.
        felder = {k: roh[tag][q] for k, q in (
            ("tx", "tx"), ("outputs", "outputs_created"), ("outputs_created", "outputs_created"),
            ("outputs_spent", "outputs_spent"), ("utxo_count", "utxo_count"),
            ("stand_utc", "stand_utc")) if q in roh[tag]}
        alt = nach_tag.get(schluessel)
        if alt is None:
            eintrag = {"datum": schluessel}
            for k in ("tx", "outputs", "outputs_created", "outputs_spent", "utxo_count"):
                eintrag[k] = None
            eintrag.update(felder)
            eintrag["quelle"] = QUELLENNAME
            eintrag["abgerufen_utc"] = jetzt
            nach_tag[schluessel] = eintrag
            neu += 1
            continue
        # stand_utc nachtragen, wo es noch fehlt, ist keine korrektur eines
        # werts und zieht abgerufen_utc nicht mit
        if "stand_utc" not in alt and felder.get("stand_utc") and alt.get("utxo_count") == felder.get(
                "utxo_count", alt.get("utxo_count")):
            alt["stand_utc"] = felder["stand_utc"]
        if all(alt.get(k) == v for k, v in felder.items()):
            continue
        alt.update(felder)
        alt["quelle"] = QUELLENNAME
        alt["abgerufen_utc"] = jetzt        # regel 4
        geaendert += 1
    log["tage"] = [nach_tag[k] for k in sorted(nach_tag)]
    log["quelle"] = QUELLENNAME
    log["endpunkte"] = {
        "tx": BASIS + QUELLEN["tx"][0],
        "outputs": BASIS + QUELLEN["outputs_created"][0],
        "utxo_count": BASIS + QUELLEN["utxo_count"][0],
    }
    log["toccata_aktiv_seit"] = str(TOCCATA)
    log["aktualisiert_utc"] = jetzt
    return log, neu, geaendert


def schreibe(log, pfad=ZIEL):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


# ------------------------------------------------------------------ selftest

def _stub(pfad):
    """zwoelf tage. der 22.09. ist im stub der laufende tag und darf nie
    im ergebnis auftauchen."""
    if pfad == "covenants/transactions":
        return {"labels": ["2026-09-%02dT00:00:00.000Z" % d for d in range(11, 23)],
                "datasets": [
                    {"label": "Transactions",
                     "data": [300, 310, 900, 880, 420, 430, 440, 1500, 542, 610, 620, 999]},
                    {"label": "Price", "data": [1] * 12},
                ]}
    if pfad == "covenants/outputs":
        return {"labels": ["2026-09-%02dT00:00:00.000Z" % d for d in range(11, 23)],
                "datasets": [
                    {"label": "Created",
                     "data": [600, 620, 1800, 1760, 840, 860, 880, 1084, 3000, 1220, 1240, 1998]},
                    {"label": "Spent",
                     "data": [100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210]},
                    {"label": "Price", "data": [1] * 12},
                ]}
    if pfad == "utxo/covenant-count":
        # mit schlupf um mitternacht, genau so wie die echte quelle:
        # mal 23:59:5x des tages, mal 00:00:0x des naechsten.
        labels = []
        for d in range(11, 23):
            if d % 2:
                labels.append("2026-09-%02dT23:59:58.400Z" % d)
            else:
                labels.append("2026-09-%02dT00:00:02.100Z" % (d + 1))
        return {"labels": labels,
                "datasets": [
                    {"label": "Price", "data": [1] * 12},
                    {"label": "Covenant UTXOs",
                     "data": [10100, 10200, 10300, 10400, 10500, 10600, 10700, 10740,
                              10780, 11000, 11100, 11200]},
                ]}
    raise RuntimeError("unbekannter pfad im stub, %s" % pfad)


def run_selftest():
    fails, gezaehlt = [], [0]

    def check(name, ist, soll):
        gezaehlt[0] += 1
        if ist != soll:
            fails.append("%s\n    ist  %r\n    soll %r" % (name, ist, soll))

    heute = dt.date(2026, 9, 22)
    roh, probleme = sammle(heute=heute, holer=_stub)

    check("keine probleme", probleme, [])
    check("der laufende tag fehlt", dt.date(2026, 9, 22) in roh, False)
    check("gestern ist da", dt.date(2026, 9, 21) in roh, True)
    check("die ganze stubreihe bis gestern", len(roh), 11)

    # die handzahlen, die Ben am 19.09. abgelesen hat, liegen im stub auf
    # dem 19.09. der lauf muss sie genau dort wiederfinden
    check("transaktionen am 19.09.", roh[dt.date(2026, 9, 19)]["tx"], 542)
    check("utxo-bestand am 19.09.", roh[dt.date(2026, 9, 19)]["utxo_count"], 10780)

    # der mitternachtsschlupf: beide schreibweisen landen auf dem richtigen tag
    check("23:59:58 des 11. ist der 11.",
          str(stichtag_bestand("2026-09-11T23:59:58.400Z")), "2026-09-11")
    check("00:00:02 des 13. ist der 12.",
          str(stichtag_bestand("2026-09-13T00:00:02.100Z")), "2026-09-12")
    check("eine tagessumme traegt ihren eigenen tag",
          str(stichtag_fluss("2026-09-21T00:00:00.000Z")), "2026-09-21")
    # und die bestandsreihe hat dadurch keine loecher und keine doppeltage
    tage_bestand = sorted(t for t in roh if "utxo_count" in roh[t])
    check("bestandsreihe ohne luecke", tage_bestand,
          [dt.date(2026, 9, d) for d in range(11, 22)])

    # sichtbarer saegezahn, der nicht geglaettet werden darf
    check("der sprung am 13. steht so drin", roh[dt.date(2026, 9, 13)]["tx"], 900)
    check("und der ruhige tag daneben auch", roh[dt.date(2026, 9, 12)]["tx"], 310)

    # verschmelzen: erster lauf legt an
    log = {"quelle": QUELLENNAME, "endpunkte": {}, "tage": []}
    log, neu, geaendert = verschmelze(log, roh, "2026-09-22T08:00:00+00:00")
    check("erster lauf legt alle tage an", neu, 11)
    check("erster lauf aendert nichts", geaendert, 0)
    check("outputs ist die erzeugte reihe",
          log["tage"][-1]["outputs"], log["tage"][-1]["outputs_created"])
    check("jeder tag nennt seine quelle",
          all(e["quelle"] == QUELLENNAME for e in log["tage"]), True)
    check("jeder tag nennt seinen abruf",
          all(e["abgerufen_utc"] == "2026-09-22T08:00:00+00:00" for e in log["tage"]), True)
    check("tage stehen sortiert",
          [e["datum"] for e in log["tage"]] == sorted(e["datum"] for e in log["tage"]), True)

    # zweiter lauf mit denselben zahlen ist still
    log2, neu2, geaendert2 = verschmelze(json.loads(json.dumps(log)), roh,
                                         "2026-09-23T08:00:00+00:00")
    check("zweiter lauf legt nichts an", neu2, 0)
    check("zweiter lauf aendert nichts", geaendert2, 0)
    check("und ruehrt den abrufzeitpunkt nicht an",
          log2["tage"][0]["abgerufen_utc"], "2026-09-22T08:00:00+00:00")

    # aendert die quelle einen alten wert, zieht das datum mit (regel 4)
    roh_neu = json.loads(json.dumps({str(k): v for k, v in roh.items()}))
    roh_korrigiert = {dt.date.fromisoformat(k): v for k, v in roh_neu.items()}
    roh_korrigiert[dt.date(2026, 9, 19)]["tx"] = 555
    log3, neu3, geaendert3 = verschmelze(json.loads(json.dumps(log)), roh_korrigiert,
                                         "2026-09-24T08:00:00+00:00")
    check("korrektur wird uebernommen", geaendert3, 1)
    e18 = [e for e in log3["tage"] if e["datum"] == "2026-09-19"][0]
    check("der neue wert steht drin", e18["tx"], 555)
    check("und der abruf zieht mit", e18["abgerufen_utc"], "2026-09-24T08:00:00+00:00")
    e17 = [e for e in log3["tage"] if e["datum"] == "2026-09-17"][0]
    check("der unberuehrte tag bleibt unberuehrt",
          e17["abgerufen_utc"], "2026-09-22T08:00:00+00:00")

    # eine tote quelle laesst die anderen leben
    def tot(pfad):
        if pfad == "utxo/covenant-count":
            raise RuntimeError("503")
        return _stub(pfad)
    roh_t, probleme_t = sammle(heute=heute, holer=tot)
    check("tote quelle, feld fehlt", "utxo_count" in roh_t[dt.date(2026, 9, 21)], False)
    check("tote quelle, rest steht", roh_t[dt.date(2026, 9, 21)]["tx"], 620)
    check("tote quelle, ein problem", len(probleme_t), 1)

    # ein unplausibler wert wird verworfen, nicht eingetragen
    def kaputt(pfad):
        d = json.loads(json.dumps(_stub(pfad)))
        if pfad == "covenants/transactions":
            d["datasets"][0]["data"][8] = 9e9
        return d
    roh_k, probleme_k = sammle(heute=heute, holer=kaputt)
    check("unplausibel faellt raus", "tx" in roh_k[dt.date(2026, 9, 19)], False)
    check("und steht als problem drin", len(probleme_k), 1)
    check("der tag lebt trotzdem weiter",
          roh_k[dt.date(2026, 9, 19)]["utxo_count"], 10780)

    # ein loch in der reihe erzeugt keinen erfundenen tag
    def loch(pfad):
        d = json.loads(json.dumps(_stub(pfad)))
        if pfad == "covenants/transactions":
            d["datasets"][0]["data"][3] = None
        return d
    roh_l, _ = sammle(heute=heute, holer=loch)
    check("fehlender wert wird nicht geraten", "tx" in roh_l[dt.date(2026, 9, 14)], False)
    check("der tag selbst bleibt bestehen",
          roh_l[dt.date(2026, 9, 14)]["outputs_created"], 1760)

    # regel 6 (Ben, 03.10.2026): bestandspunkte nur bis 2 h neben mitternacht
    check("stand_utc steht am tag", roh[dt.date(2026, 9, 19)]["stand_utc"], "2026-09-19T23:59:58Z")
    check("01:59 nach mitternacht zaehlt",
          abstand_mitternacht("2026-09-30T01:59:00Z") <= BESTAND_SCHLUPF, True)
    check("02:01 nach mitternacht zaehlt nicht",
          abstand_mitternacht("2026-09-30T02:01:00Z") <= BESTAND_SCHLUPF, False)
    check("22:30 ist der tag selbst", str(stichtag_bestand("2026-09-29T22:30:00Z")), "2026-09-29")

    def mittag(pfad):
        # wie die echte quelle am 30.09.: statt mitternacht ein punkt um 12:02:05
        d = json.loads(json.dumps(_stub(pfad)))
        if pfad == "utxo/covenant-count":
            d["labels"][8] = "2026-09-20T12:02:05.729Z"
        return d
    roh_m, probleme_m = sammle(heute=heute, holer=mittag)
    t19 = roh_m[dt.date(2026, 9, 19)]
    check("mittagspunkt, bestand bleibt leer", (t19["utxo_count"], t19["stand_utc"]), (None, None))
    check("mittagspunkt, die tagessummen bleiben", t19["tx"], 542)
    check("mittagspunkt steht als problem drin",
          any("2026-09-19 bleibt leer" in x and "11 h 57 min" in x for x in probleme_m), True)
    alt29 = {"tage": [{"datum": "2026-09-19", "tx": 542, "outputs": 1084, "outputs_created": 1084,
                       "outputs_spent": 170, "utxo_count": 13342, "quelle": QUELLENNAME,
                       "abgerufen_utc": "2026-09-20T12:58:20+00:00"}]}
    log_m, _, ge_m = verschmelze(alt29, {dt.date(2026, 9, 19): t19}, "2026-10-03T13:00:00+00:00")
    e = log_m["tage"][0]
    check("falscher alter bestand wird zur luecke", (e["utxo_count"], e["abgerufen_utc"]),
          (None, "2026-10-03T13:00:00+00:00"))
    alt_ohne = json.loads(json.dumps(log))
    for e in alt_ohne["tage"]:
        e.pop("stand_utc", None)
    log_s, _, ge_s = verschmelze(alt_ohne, roh, "2026-10-04T08:00:00+00:00")
    check("stand_utc wird nachgetragen", all(e.get("stand_utc") for e in log_s["tage"]), True)
    check("nachtragen zieht abgerufen_utc nicht mit",
          (ge_s, {e["abgerufen_utc"] for e in log_s["tage"]}), (0, {"2026-09-22T08:00:00+00:00"}))
    log_t, _, _ = verschmelze(json.loads(json.dumps(log)), roh_t, "2026-10-04T08:00:00+00:00")
    check("tote quelle loescht keinen alten bestand",
          [e["utxo_count"] for e in log_t["tage"]] == [e["utxo_count"] for e in log["tage"]], True)

    if fails:
        print("selftest FEHLGESCHLAGEN")
        for f in fails:
            print("  " + f)
        return 1
    print("selftest ok, %d faelle" % gezaehlt[0])
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=ZIEL)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return run_selftest()

    jetzt = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    roh, probleme = sammle()
    if not roh:
        print("kein einziger tag gelesen, nichts geschrieben")
        for p in probleme:
            print("  " + p)
        return 1

    log = lade_log(a.out)
    vorher = len(log.get("tage", []))
    log, neu, geaendert = verschmelze(log, roh, jetzt)
    schreibe(log, a.out)

    tage = log["tage"]
    letzter = tage[-1]
    print("covenants-log, %s" % jetzt)
    print("  quelle        %s" % QUELLENNAME)
    print("  tage im log   %d, vorher %d, neu %d, nachgezogen %d"
          % (len(tage), vorher, neu, geaendert))
    print("  spanne        %s bis %s" % (tage[0]["datum"], letzter["datum"]))
    print("  letzter tag   tx %s, outputs %s, utxo_count %s"
          % (letzter.get("tx"), letzter.get("outputs"), letzter.get("utxo_count")))
    if probleme:
        print("  %d probleme" % len(probleme))
        for p in probleme:
            print("    " + p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
