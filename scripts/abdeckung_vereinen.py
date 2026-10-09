#!/usr/bin/env python3
"""abdeckung_vereinen.py QUELLE ZIEL

Vereinigt zwei Abdeckungsdateien des Entity-X-Alarms: eine Minute gilt als
beobachtet, wenn eine der beiden sie beobachtet hat. Das Ergebnis steht in
ZIEL.

WOFUER. Im Parallelbetrieb pruefen GitHub und c2 gleichzeitig, und beide
schreiben data/entity-x-abdeckung.json. Wer zuletzt kopiert, wuerde die
Minuten des anderen loeschen - und genau die 95 % je Tag wollen wir ja
messen. c2 fuehrt deshalb vor dem Festschreiben seine eigene Datei
(/var/lib/kaspa-pulse/...) in die Repo-Datei ein; den Rest macht
entity_x_alert.py --festschreiben, das gegen main noch einmal vereinigt.

Die Vereinigung selbst kommt aus entity_x_alert.abdeckung_vereinen, es gibt
sie also nur an einer Stelle.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import entity_x_alert as ex  # noqa: E402


def vereinen(quelle, ziel):
    a = ex.abdeckung_laden(quelle)
    b = ex.abdeckung_laden(ziel)
    zusammen = ex.abdeckung_vereinen(a, b)
    ex.abdeckung_speichern(zusammen, ziel)
    tage = sorted(zusammen["tage"])
    gewonnen = sum(
        1
        for t in tage
        for x, y in zip(b["tage"].get(t, "." * 1440), zusammen["tage"][t])
        if x != y
    )
    return tage, gewonnen


def selbsttest():
    import json
    import tempfile

    fehler = 0

    def ok(was, bedingung):
        nonlocal fehler
        print(("  ok   " if bedingung else "  FEHL ") + was)
        if not bedingung:
            fehler += 1

    print("selbsttest abdeckung_vereinen")
    with tempfile.TemporaryDirectory() as tmp:
        q, z = Path(tmp, "q.json"), Path(tmp, "z.json")
        # Server sah die erste Stunde, das Repo die zweite.
        q.write_text(json.dumps({"tage": {"2026-10-09": "1" * 60 + "." * 1380}}))
        z.write_text(json.dumps({"tage": {"2026-10-09": "." * 60 + "1" * 60 + "." * 1320}}))
        tage, gewonnen = vereinen(str(q), str(z))
        d = json.loads(z.read_text())["tage"]["2026-10-09"]
        ok("beide Stunden stehen danach drin", d.count("1") == 120)
        ok("die erste Minute kommt vom Server", d[0] == "1")
        ok("Minute 61 kommt aus dem Repo", d[60] == "1")
        ok("Minute 121 bleibt unbeobachtet", d[120] == ".")
        ok("Laenge bleibt 1440", len(d) == 1440)
        ok("60 Minuten dazugewonnen, %d" % gewonnen, gewonnen == 60)
        ok("ein Tag, %s" % tage, tage == ["2026-10-09"])

        # Ein Tag nur auf einer Seite geht nicht verloren.
        q.write_text(json.dumps({"tage": {"2026-10-08": "1" * 1440}}))
        vereinen(str(q), str(z))
        nach = json.loads(z.read_text())["tage"]
        ok("Tag nur beim Server bleibt erhalten", nach["2026-10-08"].count("1") == 1440)
        ok("Tag nur im Repo bleibt erhalten", nach["2026-10-09"].count("1") == 120)

        # Zweimal vereinen aendert nichts mehr.
        vorher = z.read_text()
        vereinen(str(q), str(z))
        ok("zweiter Lauf aendert nichts", z.read_text() == vorher)

        # Eine fehlende Datei ist kein Abbruch.
        fehlt = Path(tmp, "gibt-es-nicht.json")
        vereinen(str(fehlt), str(z))
        ok("fehlende Quelle laesst das Ziel stehen", z.read_text() == vorher)
    print("%d fehler" % fehler)
    return 1 if fehler else 0


if __name__ == "__main__":
    if "--selbsttest" in sys.argv:
        sys.exit(selbsttest())
    if len(sys.argv) != 3:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        sys.exit(2)
    tage, gewonnen = vereinen(sys.argv[1], sys.argv[2])
    print("abdeckung vereinigt, %d tage, %d minuten dazugewonnen" % (len(tage), gewonnen))
