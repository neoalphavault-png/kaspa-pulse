#!/usr/bin/env python3
"""selbsttest.py - Selbsttest der Upgrade-Wache fuer die Faelle aus der NU7-Nacht (Ben, 06.11.2026).

  1. Seed nicht aufloesbar: Wiederholung mit Abstand, dann die Adressen des
     letzten Erfolgs aus dem Cache; keine Adresse in der Ausgabe.
  2. Eigene Spitze steht, Peers kuendigen aber neuere Bloecke an: nach 600 s
     "wache_haengt", Nachziehen angestossen, kein blockpause-Alarm; sobald die
     Koepfe ankommen, waechst die Spitze und es folgt die Entwarnung.
  3. Echte Pause (keine Ankuendigungen): blockpause wie bisher, kein wache_haengt.
  4. Anker schliesst an die bekannte Arbeit an: eine alte Spitze ausserhalb
     des Ankers haelt die eigene Spitze nicht mehr fest.

Ohne Netz. Gibt 0 zurueck, wenn alles besteht.

  python3 scripts/wache/selbsttest.py
"""
import contextlib
import copy
import csv
import io
import json
import os
import stat
import sys
import tempfile

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
from wache_kern import Kern, Melder, SimUhr, ts  # noqa: E402
import quelle_zcash  # noqa: E402

NBITS = "1c009054"
DOKU_ADRESSE = "192.0.2.7"   # Bereich fuer Dokumentation, nur im Test


def h(n, zweig="a"):
    return f"{zweig}{n:063x}"


class FakeQuelle:
    def __init__(self):
        self.nachziehen = 0
        self.hoehe_gemeldet = 0

    def nachziehen_anstossen(self):
        self.nachziehen += 1

    def probe(self):
        return []


def kern_bauen(d, quelle=None):
    cfg = copy.deepcopy(json.load(open(os.path.join(HIER, "ketten", "zcash-mainnet.json"))))
    start = ts("2026-11-06T03:00:00Z")
    cfg["aktivierung"].update(hoehe=100, erwartet_utc="2026-11-06T02:00:00Z")
    cfg["signale"]["peers_vor_upgrade"]["zeitpunkte_h"] = []
    uhr = SimUhr(start)
    melder = Melder("NIEMAND", scharf=False)
    k = Kern(cfg, uhr, melder, os.path.join(d, "log.csv"), os.path.join(d, "zustand.json"), quelle=quelle)
    k.verbindungen(10)
    return k, uhr, melder


def log_zeilen(d):
    with open(os.path.join(d, "log.csv"), newline="") as f:
        return list(csv.DictReader(f))


def main():
    fehler = []

    def ok(name, bed, info=""):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, ("  " + str(info)) if not bed and info else ""))
        if not bed:
            fehler.append(name)

    # ---------------------------------------------------------- 1. seeds
    with tempfile.TemporaryDirectory() as d:
        cache = os.path.join(d, "peers-cache.json")
        schlaf = []
        out = io.StringIO()
        with contextlib.redirect_stderr(out), contextlib.redirect_stdout(out):
            liste, herkunft = quelle_zcash.adressen(cache, finden=lambda: [], schlafen=schlaf.append)
        ok("seed nicht aufloesbar, kein cache: drei wiederholungen mit 5, 15, 45 s", schlaf == [5, 15, 45], schlaf)
        ok("seed nicht aufloesbar, kein cache: leere liste", liste == [] and herkunft == "keine", (liste, herkunft))
        with contextlib.redirect_stderr(out), contextlib.redirect_stdout(out):
            liste, herkunft = quelle_zcash.adressen(cache, finden=lambda: [(DOKU_ADRESSE, 8233)],
                                                    schlafen=schlaf.append)
        ok("seed antwortet: liste und cache geschrieben", herkunft == "seeds" and os.path.exists(cache))
        ok("cache nur fuer den eigenen nutzer lesbar", stat.S_IMODE(os.stat(cache).st_mode) == 0o600,
           oct(stat.S_IMODE(os.stat(cache).st_mode)))
        aufrufe = []

        def spaeter():
            aufrufe.append(1)
            return [(DOKU_ADRESSE, 8233)] if len(aufrufe) == 3 else []

        schlaf.clear()
        with contextlib.redirect_stderr(out), contextlib.redirect_stdout(out):
            liste, herkunft = quelle_zcash.adressen(cache, finden=spaeter, schlafen=schlaf.append)
        ok("seed antwortet beim dritten versuch", herkunft == "seeds" and schlaf == [5, 15], schlaf)
        with contextlib.redirect_stderr(out), contextlib.redirect_stdout(out):
            liste, herkunft = quelle_zcash.adressen(cache, finden=lambda: [], schlafen=lambda s: None)
        ok("seed faellt aus: adressen aus dem cache des letzten erfolgs", herkunft == "cache" and len(liste) == 1,
           (herkunft, len(liste)))
        ok("keine adresse in der ausgabe", DOKU_ADRESSE not in out.getvalue())

    # ---------------------------------------------------------- 2. eigene spitze steht
    with tempfile.TemporaryDirectory() as d:
        q = FakeQuelle()
        k, uhr, melder = kern_bauen(d, quelle=q)
        k.anker([(n, h(n), int(uhr.t) - 25 * (130 - n), NBITS) for n in range(90, 131)])
        k.knoten[k.tip]["erst_ms"] = uhr.t * 1000
        tip0 = k.knoten[k.tip]["hoehe"]
        for sek in range(60, 15 * 60 + 1, 60):
            uhr.t += 60
            # Peers kuendigen neuere Bloecke an, deren Koepfe bei uns nicht ankommen
            k.ankuendigung(uhr.t * 1000, "zebra-1", h(131 + sek // 60))
            k.ankuendigung(uhr.t * 1000 + 50, "zakura-1", h(131 + sek // 60))
            k.takt()
        z = log_zeilen(d)
        haengt = [r for r in z if r["signal"] == "wache_haengt" and r["stufe"] == "hinweis"]
        pause = [r for r in z if r["signal"] == "blockpause" and r["stufe"] in ("hinweis", "alarm")]
        ok("eigene spitze steht 15 min: wache_haengt gemeldet", len(haengt) == 1, z)
        ok("wache_haengt erst nach 600 s", haengt and int(haengt[0]["wert"]) >= 600, haengt)
        ok("kein blockpause-alarm, solange neuere bloecke angekuendigt sind", not pause, pause)
        ok("nachziehen angestossen", q.nachziehen >= 1, q.nachziehen)
        ok("meldung nennt wache haengt", any("wache haengt" in m for m in melder.gesendet), melder.gesendet)
        # Die Koepfe kommen an (nachziehen), die Spitze waechst
        for n in range(131, 147):
            k.kopf(h(n), h(n - 1), int(uhr.t) - 25 * (147 - n), NBITS)
        uhr.t += 60
        k.takt()
        z = log_zeilen(d)
        ok("nach dem nachziehen waechst die spitze", k.knoten[k.tip]["hoehe"] > tip0, k.knoten[k.tip]["hoehe"])
        ok("entwarnung fuer wache_haengt", any(r["signal"] == "wache_haengt" and r["stufe"] == "entwarnung"
                                               for r in z), z[-3:])

    # ---------------------------------------------------------- 3. echte pause
    with tempfile.TemporaryDirectory() as d:
        k, uhr, melder = kern_bauen(d, quelle=FakeQuelle())
        k.anker([(n, h(n), int(uhr.t) - 25 * (130 - n), NBITS) for n in range(90, 131)])
        k.knoten[k.tip]["erst_ms"] = uhr.t * 1000
        for _ in range(12):
            uhr.t += 60
            k.takt()
        z = log_zeilen(d)
        ok("echte pause ohne ankuendigungen: blockpause wie bisher",
           any(r["signal"] == "blockpause" and r["stufe"] == "alarm" for r in z), z)
        ok("echte pause: kein wache_haengt", not any(r["signal"] == "wache_haengt" for r in z), z)

    # ---------------------------------------------------------- 4. anker-basis
    with tempfile.TemporaryDirectory() as d:
        k, uhr, _ = kern_bauen(d)
        k.anker([(n, h(n), 1000 + n, NBITS) for n in range(100, 111)])
        k.kopf(h(111, "s"), h(110), 1111, NBITS)          # eine Spitze, die der naechste Anker nicht kennt
        ok("anker: kopf auf eigener spitze verknuepft", k.tip == h(111, "s"), k.tip)
        # zweiter Anker: dieselbe Kette ab 105, dann zwei neue Bloecke (111 und 112 auf dem Hauptzweig)
        k.anker([(n, h(n), 1000 + n, NBITS) for n in range(105, 113)])
        ok("anker schliesst an: spitze folgt der laengeren kette", k.tip == h(112), k.tip)
        k.kopf(h(113), h(112), 1113, NBITS)
        ok("neuer kopf auf der geankerten kette wird spitze", k.tip == h(113), k.tip)

    print("")
    print("%d fehler" % len(fehler) if fehler else "alle testfaelle bestanden")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
