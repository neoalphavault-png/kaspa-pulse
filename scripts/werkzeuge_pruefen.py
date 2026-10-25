#!/usr/bin/env python3
"""werkzeuge_pruefen.py, fremde Werkzeuge bleiben auf dem geprueften Stand (Ben, 25.10.2026).

skills/taste-skill ist auf Commit 12af471f627f866411b4bd785b19646d3672784c
von github.com/leonxlnx/taste-skill gepinnt (docs/werkzeuge.md). Jede Datei
steht mit ihrer SHA-256 in docs/taste-skill.sha256. Weicht eine ab, fehlt
eine oder kommt eine dazu, ist das ein Update ohne neue Pruefung, und dieses
Skript faellt durch. Ein neuer Stand braucht eine neue Pruefung durch Claude
und einen neuen Eintrag in docs/werkzeuge.md.

    python3 scripts/werkzeuge_pruefen.py
    python3 scripts/werkzeuge_pruefen.py --selbsttest
"""
import hashlib
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WERKZEUGE = {"skills/taste-skill": "docs/taste-skill.sha256",
             # web-design-guidelines (agent-skills 063bee9), SKILL.md lokal angepasst
             "skills/web-design-guidelines": "docs/web-design-guidelines.sha256"}
# einzelne dateien: die gepruefte kopie der web interface guidelines (434b7f9)
DATEIEN = {"docs/web-interface-guidelines.md": "docs/web-interface-guidelines.sha256"}
EIGEN = {"LICENSE"}           # von uns dazugelegt, MIT verlangt den lizenztext


def abweichungen(ordner, liste):
    soll = {}
    for z in Path(liste).read_text(encoding="utf-8").splitlines():
        if z.strip():
            h, name = z.split("  ", 1)
            soll[name] = h
    ist = {str(p.relative_to(ordner)): hashlib.sha256(p.read_bytes()).hexdigest()
           for p in Path(ordner).rglob("*") if p.is_file() and p.name not in EIGEN}
    aus = ["fehlt %s" % n for n in sorted(set(soll) - set(ist))]
    aus += ["neu %s" % n for n in sorted(set(ist) - set(soll))]
    aus += ["geaendert %s" % n for n in sorted(set(soll) & set(ist)) if soll[n] != ist[n]]
    return aus


def selbsttest():
    t = Path(tempfile.mkdtemp())
    (t / "w").mkdir()
    (t / "w" / "a.md").write_text("x", encoding="utf-8")
    (t / "liste").write_text("%s  a.md\n" % hashlib.sha256(b"x").hexdigest(), encoding="utf-8")
    gut = not abweichungen(t / "w", t / "liste")
    (t / "w" / "a.md").write_text("y", encoding="utf-8")
    (t / "w" / "b.md").write_text("z", encoding="utf-8")
    a = abweichungen(t / "w", t / "liste")
    fehler = 0
    for name, bed in (("gleicher stand ist gruen", gut), ("aenderung faellt auf", "geaendert a.md" in a),
                      ("neue datei faellt auf", "neu b.md" in a),
                      ("das repo ist auf dem gepinnten stand", not any(
                          abweichungen(REPO / o, REPO / l) for o, l in WERKZEUGE.items())
                       and all(hashlib.sha256((REPO / d).read_bytes()).hexdigest()
                               == (REPO / l).read_text(encoding="utf-8").split()[0] for d, l in DATEIEN.items()))):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        fehler += 0 if bed else 1
    print("%d fehler" % fehler)
    return 1 if fehler else 0


def main(argv):
    if "--selbsttest" in argv:
        return selbsttest()
    aus = []
    for o, l in WERKZEUGE.items():
        aus += ["%s: %s" % (o, x) for x in abweichungen(REPO / o, REPO / l)]
    for d, l in DATEIEN.items():
        h = (REPO / l).read_text(encoding="utf-8").split()[0]
        if not (REPO / d).exists() or hashlib.sha256((REPO / d).read_bytes()).hexdigest() != h:
            aus.append("%s: geaendert oder fehlt" % d)
    for x in aus:
        print("ABWEICHUNG", x)
    print("werkzeuge: %s" % ("auf dem gepinnten stand" if not aus else "%d abweichung(en), neue pruefung noetig" % len(aus)))
    return 1 if aus else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
