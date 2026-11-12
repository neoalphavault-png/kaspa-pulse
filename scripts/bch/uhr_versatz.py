#!/usr/bin/env python3
"""uhr_versatz.py - Versatz und Status der Uhr des Runners, ohne Server (Ben, 07.11.2026).

Fuer die Forum-Antwort an rufitnes und bitcoincashautist: jeder Zuhoerer-Lauf
im BCH Tempnet schreibt am Anfang und am Ende den Zustand der Uhr ins
meta.json. Nur Versatz und Status, nie Referenz-ID, Server, IP oder Hostname.

Quellen in dieser Reihenfolge:
  1. chronyc tracking            -> System time, Last offset, RMS offset, Leap status
  2. timedatectl timesync-status -> Offset, Jitter, Leap (systemd-timesyncd)
Liefert keine einen Versatz, steht "versatz": "nicht verfuegbar" da. Das Skript
endet immer mit 0, damit der Lauf weiterlaeuft.

  python3 scripts/bch/uhr_versatz.py            -> JSON auf stdout
  python3 scripts/bch/uhr_versatz.py --selbsttest
"""
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

CHRONY_FELDER = ("System time", "Last offset", "RMS offset", "Leap status")
TIMESYNC_FELDER = ("Offset", "Jitter", "Leap")
# Werte duerfen nur Zahl, Einheit, Richtung oder Status sein, nie eine Adresse
ERLAUBT = re.compile(r"^[A-Za-z0-9 .:+\-]{1,60}$")
ADRESSE = re.compile(r"\d{1,3}(\.\d{1,3}){3}|[0-9a-fA-F]{0,4}(:[0-9a-fA-F]{0,4}){3,}|[a-z0-9-]+\.[a-z]{2,}")


def _auswahl(text, felder):
    werte = {}
    for zeile in text.splitlines():
        if ":" not in zeile:
            continue
        k, v = zeile.split(":", 1)
        k, v = k.strip(), v.strip()
        if k in felder and ERLAUBT.match(v) and not ADRESSE.search(v):
            werte[k] = v
    return werte


def chrony(text):
    return _auswahl(text, CHRONY_FELDER)


def timesync(text):
    return _auswahl(text, TIMESYNC_FELDER)


def _laufen(befehl):
    try:
        r = subprocess.run(befehl, capture_output=True, text=True, timeout=10)
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def messen():
    zeit = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if shutil.which("chronyc"):
        w = chrony(_laufen(["chronyc", "-n", "tracking"]))
        if "System time" in w or "Last offset" in w:
            return {"zeit_utc": zeit, "quelle": "chronyc tracking", "werte": w}
    if shutil.which("timedatectl"):
        w = timesync(_laufen(["timedatectl", "timesync-status"]))
        if "Offset" in w:
            return {"zeit_utc": zeit, "quelle": "timedatectl timesync-status", "werte": w}
    return {"zeit_utc": zeit, "versatz": "nicht verfügbar"}


def selbsttest():
    fehler = []

    def ok(name, bed, info=""):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, "" if bed else "  " + str(info)))
        if not bed:
            fehler.append(name)
    beispiel = """Reference ID    : C0A80001 (192.0.2.1)
Stratum         : 3
Ref time (UTC)  : Sat Nov 07 13:20:01 2026
System time     : 0.000012345 seconds fast of NTP time
Last offset     : -0.000004321 seconds
RMS offset      : 0.000023456 seconds
Frequency       : 1.234 ppm slow
Leap status     : Normal
"""
    w = chrony(beispiel)
    ok("chrony vier felder", set(w) == set(CHRONY_FELDER), w)
    ok("keine referenz-id", "Reference ID" not in w and "192.0.2.1" not in json.dumps(w))
    ts = """       Server: 192.0.2.7 (time.example.org)
Poll interval: 34min 8s (min: 32s; max 34min 8s)
         Leap: normal
      Version: 4
       Offset: +1.234ms
        Delay: 1.012ms
       Jitter: 456us
"""
    w = timesync(ts)
    ok("timesync offset, jitter, leap", set(w) == {"Offset", "Jitter", "Leap"}, w)
    ok("kein server", "example" not in json.dumps(w) and "192.0.2.7" not in json.dumps(w))
    ok("adresse im wert wird verworfen", chrony("System time : 192.0.2.1\n") == {})
    m = messen()
    ok("messen liefert quelle oder nicht verfuegbar", "quelle" in m or m.get("versatz") == "nicht verfügbar", m)
    print("")
    print("%d fehler" % len(fehler) if fehler else "alle testfaelle bestanden")
    return 1 if fehler else 0


if __name__ == "__main__":
    if "--selbsttest" in sys.argv:
        sys.exit(selbsttest())
    print(json.dumps(messen(), ensure_ascii=False))
