#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""address_thresholds_log.py, die Wochenreihe der Adressverteilung.

Die Verteilungstabelle auf kaspa.stream (Aquaman bis Plankton) ist nicht zu
holen, und die Distributionstabelle bei Kaspalytics auch nicht: beide sind
am 22.09.2026 durchgepruft und beide geben von aussen nichts her, siehe
scripts/quellen_probe.py. Was Kaspalytics stattdessen hergibt, steht in
seinem eigenen Routenverzeichnis und taucht in keiner Seitenleiste auf:

    /api/charts/address/count/non-zero-balance     jede adresse mit guthaben
    /api/charts/address/count/meaningful-balance   die "nennenswerten"
    /api/charts/distribution/kas-threshold/0.01+   adressen ab 0,01 KAS
    /api/charts/distribution/kas-threshold/1+      adressen ab 1 KAS
    /api/charts/distribution/kas-threshold/100+    adressen ab 100 KAS

Das sind keine Stufen, das sind Schwellen: jede Reihe zaehlt alle Adressen
AB einem Betrag, nicht die zwischen zwei Betraegen. Wer daraus Stufen
rechnen will, kann zwei Schwellen voneinander abziehen, aber nur fuer die
drei Schnitte, die es gibt. Die Stufentabelle laesst sich daraus NICHT
rekonstruieren, und sie wird hier auch nicht behauptet.

    1000+ gibt es nicht, die Quelle antwortet mit http 400. Nur die drei
    Schwellen aus dem Menue sind angelegt.

VORSICHT BEI holders_all, DAS SIND KEINE HALTER
non-zero-balance zaehlt JEDE Adresse mit irgendeinem Guthaben, auch die mit
einem Bruchteil eines Sompi. Am 21.09.2026 waren das 54.876.372 gegen
796.711 bei meaningful-balance, also das Neunundsechzigfache. Am 27.08.2023,
dem ersten Tag der Reihe, standen sich 280.049 und 279.609 gegenueber, die
beiden Reihen waren praktisch deckungsgleich. Dazwischen liegt eine
Staubschwemme, keine Halterschaft. Wer holders_all als "Zahl der Halter"
liest oder auf eine Seite schreibt, sagt etwas Falsches. Die Reihe steht
trotzdem im Log, weil sie die Staubschwemme selbst messbar macht.

Die Zahl, die Bens Handablesung auf kaspa.stream am naechsten kommt
(792.706 als Summe aller Stufen), ist holders_mean mit 796.711. Andere
Zaehler, andere Zahl; das ist kein Beweis, dass beide dasselbe messen.

ALLE FUENF SIND MOMENTAUFNAHMEN
Sie teilen sich ihre Zeitstempel mit holder_addr und exchange_kas, also
Mitternacht mit Sekundenschlupf, davor bis Anfang 2026 gegen 09:00 UTC.
Deshalb wird der Stichtag nicht aus dem Datum gelesen, sondern von
scripts/kaspalytics.py berechnet (stichtag(), Korrektur vom 22.09.2026).
Ohne das haette diese Datei 76 Doppeltage und ebenso viele Loecher.

HISTORIE
Die Reihen reichen bis zum 27.08.2023 zurueck, rund 1119 Punkte. Die
Datei wird beim ersten Lauf vollstaendig gefuellt und danach woechentlich
fortgeschrieben; laeuft der Job einmal nicht, holt der naechste Lauf die
fehlenden Tage nach, weil immer die ganze Reihe verschmolzen wird.

    python3 scripts/address_thresholds_log.py
    python3 scripts/address_thresholds_log.py --selftest
"""

import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import kaspalytics as k      # noqa: E402  hole(), stichtag(), zeit_von(), reihe()

ZIEL = os.path.join(REPO, "data", "address-thresholds-log.json")
QUELLENNAME = "kaspalytics"

# feld -> (pfad unter /api/charts/, reihenname)
# alle fuenf sind bestaende, siehe kopf. die art steht nicht je feld dabei,
# weil es hier keine tagessumme gibt; waere je eine dazuzukommen, gehoert
# sie in dieses dict und nicht in eine sonderbehandlung.
QUELLEN = {
    # ACHTUNG: holders_all zaehlt auch staub, siehe Kopf. Das ist die
    # groesste Zahl der fuenf und die am leichtesten misszuverstehende.
    "holders_all":    ("address/count/non-zero-balance", "Addresses"),
    "holders_mean":   ("address/count/meaningful-balance", "Addresses"),
    "holders_001kas": ("distribution/kas-threshold/0.01+", "Addresses"),
    "holders_1kas":   ("distribution/kas-threshold/1+", "Addresses"),
    "holders_100kas": ("distribution/kas-threshold/100+", "Addresses"),
}

# Bot-Regel 10, um jeden fremdwert ein fenster. Die Reihen zaehlen Adressen,
# am 21.09.2026 zwischen 293.153 (ab 100 KAS) und 54.876.372 (mit staub).
# Die obere Grenze muss die Staubreihe durchlassen, ohne eine kaputte
# Antwort durchzuwinken, deshalb 5e8 und nicht enger.
FENSTER = (1000, 5e8)


def tagesreihe(daten, name, bis):
    """{datum: wert} bis einschliesslich 'bis'. Der Stichtag kommt aus
    kaspalytics.stichtag(), damit diese Datei und die Montagsroutine
    denselben Tag meinen. Faellt ein Tag doppelt an, gewinnt die spaetere
    Messung, genauso wie dort."""
    labels = daten.get("labels") or []
    werte = k.reihe(daten, name)
    aus, gesehen = {}, {}
    for i, lab in enumerate(labels):
        try:
            tag = k.stichtag(lab, "bestand")
            zeit = k.zeit_von(lab)
        except ValueError:
            continue
        if tag > bis:
            continue
        if i >= len(werte) or werte[i] is None:
            continue
        if tag in gesehen and gesehen[tag] >= zeit:
            continue
        gesehen[tag] = zeit
        aus[tag] = float(werte[i])
    return aus


def sammle(heute=None, holer=None):
    """{datum: {feld: wert}} plus probleme. Faellt eine der fuenf Reihen
    aus, bleiben die anderen vier stehen."""
    heute = heute or dt.datetime.now(dt.timezone.utc).date()
    bis = heute - dt.timedelta(days=1)          # nie der laufende tag
    holer = holer or k.hole
    roh, probleme = {}, []
    for feld, (pfad, name) in QUELLEN.items():
        try:
            reihe_tage = tagesreihe(holer(pfad), name, bis)
        except Exception as exc:      # noqa: BLE001
            probleme.append("%s, %s" % (feld, exc))
            continue
        verworfen = 0
        for tag, wert in reihe_tage.items():
            if not FENSTER[0] <= wert <= FENSTER[1]:
                verworfen += 1
                continue
            roh.setdefault(tag, {})[feld] = int(round(wert))
        if verworfen:
            probleme.append("%s, %d werte ausserhalb des fensters verworfen"
                            % (feld, verworfen))
        if not reihe_tage:
            probleme.append("%s, kein einziger tag" % feld)
    return roh, probleme


def lade(pfad=ZIEL):
    if not os.path.exists(pfad):
        return {"quelle": QUELLENNAME, "endpunkte": {}, "tage": []}
    with open(pfad, encoding="utf-8") as fh:
        return json.load(fh)


def verschmelze(log, roh, jetzt):
    """Neue Tage anhaengen, geaenderte nachziehen, alles andere in Ruhe
    lassen. Aendert die Quelle einen alten Wert, zieht abgerufen_utc des
    Tages mit, damit im Log sichtbar bleibt, dass er angefasst wurde."""
    nach_tag = {e["datum"]: e for e in log.get("tage", [])}
    neu = geaendert = 0
    for tag in sorted(roh):
        schluessel = str(tag)
        felder = {f: roh[tag].get(f) for f in QUELLEN}
        alt = nach_tag.get(schluessel)
        if alt is None:
            eintrag = {"datum": schluessel}
            eintrag.update(felder)
            eintrag["quelle"] = QUELLENNAME
            eintrag["abgerufen_utc"] = jetzt
            nach_tag[schluessel] = eintrag
            neu += 1
            continue
        if all(alt.get(f) == v for f, v in felder.items()):
            continue
        alt.update(felder)
        alt["quelle"] = QUELLENNAME
        alt["abgerufen_utc"] = jetzt
        geaendert += 1
    log["tage"] = [nach_tag[x] for x in sorted(nach_tag)]
    log["quelle"] = QUELLENNAME
    log["endpunkte"] = {f: k.BASIS + p for f, (p, _) in QUELLEN.items()}
    log["hinweis"] = ("schwellen, keine stufen: jede reihe zaehlt alle "
                      "adressen AB einem betrag. die stufentabelle laesst "
                      "sich daraus nicht rekonstruieren.")
    log["hinweis_holders_all"] = (
        "holders_all zaehlt jede adresse mit irgendeinem guthaben, auch "
        "staub. am 21.09.2026 waren das 54.876.372 gegen 796.711 bei "
        "holders_mean. als 'zahl der halter' ist holders_all falsch.")
    log["aktualisiert_utc"] = jetzt
    return log, neu, geaendert


def schreibe(log, pfad=ZIEL):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


# ------------------------------------------------------------------ selftest

def _stub(pfad):
    """Zwoelf Messpunkte mit echtem Mitternachtsschlupf, dazu am Anfang
    zwei aus der alten 09:00-Zeit. Index i gehoert zum 9.+i september."""
    labels = []
    for i in range(12):
        if i < 2:
            labels.append("2026-09-%02dT09:00:01.000Z" % (9 + i))
        elif i % 2 == 0:
            labels.append("2026-09-%02dT23:59:58.400Z" % (9 + i))
        else:
            labels.append("2026-09-%02dT00:00:02.100Z" % (10 + i))
    basis = {
        "address/count/non-zero-balance": 900000,
        "address/count/meaningful-balance": 790000,
        "distribution/kas-threshold/0.01+": 750000,
        "distribution/kas-threshold/1+": 550000,
        "distribution/kas-threshold/100+": 290000,
    }
    if pfad not in basis:
        raise RuntimeError("unbekannter pfad im stub, %s" % pfad)
    start = basis[pfad]
    return {"labels": labels,
            "datasets": [
                {"label": "Price", "data": [1] * 12},
                {"label": "Addresses", "data": [start + i * 100 for i in range(12)]},
            ]}


def run_selftest():
    fails = []

    def check(name, ist, soll):
        if ist != soll:
            fails.append("%s\n    ist  %r\n    soll %r" % (name, ist, soll))

    heute = dt.date(2026, 9, 21)
    roh, probleme = sammle(heute=heute, holer=_stub)
    check("keine probleme", probleme, [])
    check("der laufende tag fehlt", dt.date(2026, 9, 21) in roh, False)
    check("gestern ist da", dt.date(2026, 9, 20) in roh, True)

    # elf tage, 09.09. bis 20.09. ohne den laufenden 21.
    tage = sorted(roh)
    check("lueckenlose reihe", tage,
          [dt.date(2026, 9, d) for d in range(9, 21)])
    check("alle fuenf felder je tag",
          sorted(roh[dt.date(2026, 9, 20)]), sorted(QUELLEN))

    # der schlupf: beide schreibweisen landen auf demselben tag wie die
    # montagsroutine sie sieht
    check("23:59:58 des 12. ist der 12.",
          str(k.stichtag("2026-09-12T23:59:58.400Z", "bestand")), "2026-09-12")
    check("00:00:02 des 14. ist der 13.",
          str(k.stichtag("2026-09-14T00:00:02.100Z", "bestand")), "2026-09-13")
    check("09:00 der alten zeit bleibt liegen",
          str(k.stichtag("2026-09-09T09:00:01.000Z", "bestand")), "2026-09-09")

    # die schwellen muessen der groesse nach fallen, sonst sind zwei
    # reihen vertauscht
    e = roh[dt.date(2026, 9, 20)]
    check("alle halter >= ab 0,01", e["holders_all"] >= e["holders_001kas"], True)
    check("ab 0,01 >= ab 1", e["holders_001kas"] >= e["holders_1kas"], True)
    check("ab 1 >= ab 100", e["holders_1kas"] >= e["holders_100kas"], True)

    log = {"quelle": QUELLENNAME, "endpunkte": {}, "tage": []}
    log, neu, geaendert = verschmelze(log, roh, "2026-09-21T06:00:00+00:00")
    check("erster lauf legt alle tage an", neu, 12)
    check("erster lauf aendert nichts", geaendert, 0)
    check("tage sortiert",
          [x["datum"] for x in log["tage"]] == sorted(x["datum"] for x in log["tage"]),
          True)
    check("endpunkte stehen in der datei", len(log["endpunkte"]), 5)
    check("der hinweis auf schwellen steht drin", "schwellen" in log["hinweis"], True)

    log2, neu2, geaendert2 = verschmelze(json.loads(json.dumps(log)), roh,
                                         "2026-09-28T06:00:00+00:00")
    check("zweiter lauf legt nichts an", neu2, 0)
    check("zweiter lauf aendert nichts", geaendert2, 0)
    check("und ruehrt den abruf nicht an",
          log2["tage"][0]["abgerufen_utc"], "2026-09-21T06:00:00+00:00")

    korr = {x: dict(v) for x, v in roh.items()}
    korr[dt.date(2026, 9, 20)]["holders_1kas"] = 999999
    log3, _, geaendert3 = verschmelze(json.loads(json.dumps(log)), korr,
                                      "2026-10-05T06:00:00+00:00")
    check("korrektur wird uebernommen", geaendert3, 1)
    e20 = [x for x in log3["tage"] if x["datum"] == "2026-09-20"][0]
    check("der neue wert steht drin", e20["holders_1kas"], 999999)
    check("und der abruf zieht mit", e20["abgerufen_utc"], "2026-10-05T06:00:00+00:00")

    # eine tote reihe laesst die anderen leben
    def tot(pfad):
        if pfad.startswith("distribution/kas-threshold/100"):
            raise RuntimeError("503")
        return _stub(pfad)
    roh_t, probleme_t = sammle(heute=heute, holer=tot)
    check("tote reihe, feld fehlt",
          "holders_100kas" in roh_t[dt.date(2026, 9, 20)], False)
    check("tote reihe, rest steht",
          roh_t[dt.date(2026, 9, 20)]["holders_1kas"], 551100)
    check("tote reihe, ein problem", len(probleme_t), 1)

    # ein unplausibler wert faellt raus statt eingetragen zu werden
    def kaputt(pfad):
        d = json.loads(json.dumps(_stub(pfad)))
        if pfad.startswith("address/count/non-zero"):
            d["datasets"][1]["data"] = [9e9] * 12
        return d
    roh_k, probleme_k = sammle(heute=heute, holer=kaputt)
    check("unplausibel faellt raus",
          "holders_all" in roh_k[dt.date(2026, 9, 20)], False)
    check("und steht als problem drin", len(probleme_k), 1)
    check("der tag lebt weiter",
          roh_k[dt.date(2026, 9, 20)]["holders_1kas"], 551100)

    if fails:
        print("selftest FEHLGESCHLAGEN")
        for f in fails:
            print("  " + f)
        return 1
    print("selftest ok, 24 faelle")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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

    log = lade(a.out)
    vorher = len(log.get("tage", []))
    log, neu, geaendert = verschmelze(log, roh, jetzt)
    schreibe(log, a.out)

    tage = log["tage"]
    letzter = tage[-1]
    print("address-thresholds-log, %s" % jetzt)
    print("  tage im log   %d, vorher %d, neu %d, nachgezogen %d"
          % (len(tage), vorher, neu, geaendert))
    print("  spanne        %s bis %s" % (tage[0]["datum"], letzter["datum"]))
    print("  letzter tag   %s" % ", ".join(
        "%s %s" % (f, letzter.get(f)) for f in QUELLEN))
    if probleme:
        print("  %d probleme" % len(probleme))
        for p in probleme:
            print("    " + p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
