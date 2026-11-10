#!/usr/bin/env python3
"""lauscher_weiter.py - entscheidet, ob die Kette der Zuhoerer-Laeufe weitergeht.

Ben, 10.11.2026: Die NU7-Kette endete nach Lauf 13 am 8.11. um 15:30 UTC,
weil das alte Kriterium "48 h nach dem NU7-Block" von einem kurzen Kopfabruf
abhing. Schlug der fehl (Laeufe 11 und 12), lief die Kette weiter; gelang er
(Lauf 13), endete sie. Das Ende hing also am Netz, nicht an einer Zeit.
Jetzt gilt nur eine feste Endzeit der Kette (ende_utc), ohne Abruf.

Regel: Der naechste Lauf startet 8 min vor dem Ende dieses Laufs. Er laeuft
hoechstens bis ende_utc, also min(dauer_min, Minuten bis ende_utc). Bleiben
weniger als 10 min, startet kein Lauf mehr.

  python3 scripts/zcash/lauscher_weiter.py --ende-utc 2026-11-10T00:00:00Z --dauer-min 330
  -> "ja 330", "ja 92" oder "nein, endzeit erreicht"
  python3 scripts/zcash/lauscher_weiter.py --selbsttest
"""
import argparse
import re
import sys
import time
from datetime import datetime, timezone

VORLAUF_S = 8 * 60      # der naechste Lauf startet so lange vor dem Ende dieses Laufs
MINDEST_MIN = 10        # kuerzer lohnt kein Lauf
FORMAT = re.compile(r"^\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d:[0-5]\dZ$")


def ende_lesen(text):
    if not FORMAT.match(text or ""):
        raise ValueError(f"ende_utc unklar: {text!r}")
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def entscheiden(jetzt, ende_utc, dauer_min):
    start_naechster = jetzt + VORLAUF_S
    rest_min = int((ende_lesen(ende_utc) - start_naechster) // 60)
    if rest_min < MINDEST_MIN:
        return "nein, endzeit erreicht"
    return f"ja {min(dauer_min, rest_min)}"


def selbsttest():
    fehler = []
    def ok(name, bed):
        print(("ok   " if bed else "FEHL ") + name)
        if not bed:
            fehler.append(name)
    t = datetime(2026, 11, 8, 15, 22, tzinfo=timezone.utc).timestamp()
    ok("endzeit noch nicht erreicht, voller lauf",
       entscheiden(t, "2026-11-10T00:00:00Z", 330) == "ja 330")
    ok("endzeit noch nicht erreicht, letzter lauf gekuerzt",
       entscheiden(t, "2026-11-08T17:10:00Z", 330) == "ja 100")
    ok("weniger als 10 min uebrig, kein lauf",
       entscheiden(t, "2026-11-08T15:39:00Z", 330) == "nein, endzeit erreicht")
    ok("endzeit vorbei", entscheiden(t, "2026-11-08T00:00:00Z", 330) == "nein, endzeit erreicht")
    ok("testlauf mit endzeit 2000", entscheiden(t, "2000-01-01T00:00:00Z", 8) == "nein, endzeit erreicht")
    try:
        entscheiden(t, "10.11.2026", 330)
        ok("falsches format bricht ab", False)
    except ValueError:
        ok("falsches format bricht ab", True)
    print("alle testfaelle bestanden" if not fehler else f"{len(fehler)} fehler")
    return 1 if fehler else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--ende-utc")
    ap.add_argument("--dauer-min", type=int, default=330)
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    try:
        print(entscheiden(time.time(), a.ende_utc, a.dauer_min))
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
