#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
newsletter_issue.py - die Ausgabennummer zaehlt sich selbst hoch.

Bis zum 05.10.2026 hat die Montagsroutine die Nummer von Hand getippt
(Ausgabe 10 am 14.09., 11, 12, 13 ...). Eine Zahl, die jede Woche von Hand
gepflegt wird, geht irgendwann schief, und sie steht zweimal in jeder Datei,
im <title> und in der Kopfzeile. Ab jetzt rechnet sie dieses Skript:

    Nummer der neuen Ausgabe = hoechste Nummer aller Ausgaben VOR ihrem Datum,
    plus eins.

Eine Ausgabe ist eine Datei newsletter/<JJJJ-MM-TT>.html. Das Datum im Namen
entscheidet, was "vorher" heisst, nicht die Reihenfolge im Verzeichnis.

    python3 scripts/newsletter_issue.py next                  # Nummer fuer heute
    python3 scripts/newsletter_issue.py next --date 2026-10-12
    python3 scripts/newsletter_issue.py set newsletter/2026-10-12.html
    python3 scripts/newsletter_issue.py check newsletter/2026-10-05.html
    python3 scripts/newsletter_issue.py liste
    python3 scripts/newsletter_issue.py --selbsttest

"set" schreibt die Nummer in jede Fundstelle der Datei, auch in den
Platzhalter {{ISSUE}}, und ist wiederholbar: zweimal aufgerufen steht
dieselbe Zahl da. Damit kann die Vorlage einer neuen Ausgabe {{ISSUE}}
tragen und niemand tippt mehr eine Zahl.

"check" ist der Waechter: Exit 1, wenn die Nummer nicht hoechste-davor plus
eins ist oder ein Platzhalter stehen geblieben ist. brevo_send.py ruft ihn,
bevor HTML an Brevo geht; ein stehengebliebenes {{ISSUE}} haelt den Versand
an, eine abweichende Nummer nur eine Warnung (eine Sonderausgabe darf aus der
Reihe fallen, ein Platzhalter im Postfach nicht).
"""
import argparse
import datetime as dt
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERZ = os.path.join(ROOT, "newsletter")
DATEI_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\.html$")
NUMMER_RE = re.compile(r"(issue\s+)(\d+)", re.I)
PLATZHALTER = "{{ISSUE}}"


KOMMENTAR_RE = re.compile(r"(?s)<!--.*?-->")


def teile(text):
    """Text in abwechselnd Inhalt und HTML-Kommentare, Reihenfolge erhalten.

    Kommentare bleiben aussen vor: der Kopf einer Ausgabe erklaert die Regel
    und nennt {{ISSUE}} dabei beim Namen. Wer dort schreibt oder prueft, wuerde
    die Dokumentation verstuemmeln oder sich an ihr verschlucken."""
    out, pos = [], 0
    for m in KOMMENTAR_RE.finditer(text):
        out.append(("inhalt", text[pos:m.start()]))
        out.append(("kommentar", m.group(0)))
        pos = m.end()
    out.append(("inhalt", text[pos:]))
    return out


def nur_inhalt(text):
    return "".join(t for art, t in teile(text) if art == "inhalt")


def datum_aus_pfad(pfad):
    m = DATEI_RE.search(os.path.basename(pfad))
    return dt.date.fromisoformat(m.group(1)) if m else None


def nummer_aus_text(text):
    m = NUMMER_RE.search(nur_inhalt(text))
    return int(m.group(2)) if m else None


def ausgaben(verz=None):
    """Alle Ausgaben als (datum, pfad, nummer), nach Datum sortiert."""
    verz = verz or VERZ
    out = []
    for pfad in sorted(glob.glob(os.path.join(verz, "*.html"))):
        d = datum_aus_pfad(pfad)
        if not d:
            continue
        with open(pfad, encoding="utf-8") as fh:
            out.append((d, pfad, nummer_aus_text(fh.read())))
    return sorted(out, key=lambda x: x[0])


def letzte_vor(datum, verz=None):
    """(datum, pfad, nummer) der juengsten Ausgabe vor diesem Datum, oder None.

    Genommen wird die HOECHSTE Nummer aller frueheren Ausgaben, nicht die der
    juengsten: faellt eine Woche aus oder wird eine alte Datei nachgetragen,
    zaehlt die Reihe trotzdem weiter und springt nicht zurueck."""
    frueher = [a for a in ausgaben(verz) if a[0] < datum and a[2] is not None]
    if not frueher:
        return None
    return max(frueher, key=lambda a: a[2])


def naechste_nummer(datum, verz=None):
    v = letzte_vor(datum, verz)
    return 1 if v is None else v[2] + 1


def setze(pfad, verz=None):
    """Nummer in die Datei schreiben. Gibt (alt, neu) zurueck."""
    datum = datum_aus_pfad(pfad)
    if not datum:
        sys.exit("der Dateiname traegt kein Datum JJJJ-MM-TT: %s" % pfad)
    neu = naechste_nummer(datum, verz)
    with open(pfad, encoding="utf-8") as fh:
        text = fh.read()
    alt = nummer_aus_text(text)
    n_platz = n_zahl = 0
    neue_teile = []
    for art, stueck in teile(text):
        if art == "inhalt":
            n_platz += stueck.count(PLATZHALTER)
            stueck = stueck.replace(PLATZHALTER, str(neu))
            stueck, n = NUMMER_RE.subn(lambda m: m.group(1) + str(neu), stueck)
            n_zahl += n
        neue_teile.append(stueck)
    with open(pfad, "w", encoding="utf-8") as fh:
        fh.write("".join(neue_teile))
    print("%s: ausgabe %s, %d fundstelle(n) und %d platzhalter geschrieben"
          % (os.path.basename(pfad), neu, n_zahl, n_platz))
    if n_zahl + n_platz == 0:
        print("WARNUNG: in %s stand keine stelle zum schreiben. Erwartet wird "
              "'issue <zahl>' oder %s." % (pfad, PLATZHALTER))
    return alt, neu


def pruefe(pfad, verz=None):
    """0 wenn die Nummer passt, 1 wenn nicht. Platzhalter sind immer ein Fehler."""
    datum = datum_aus_pfad(pfad)
    if not datum:
        print("HINWEIS: %s traegt kein Datum im Namen, nummer nicht geprueft" % pfad)
        return 0
    with open(pfad, encoding="utf-8") as fh:
        text = fh.read()
    if PLATZHALTER in nur_inhalt(text):
        print("FEHLER %s: der platzhalter %s steht noch drin. "
              "scripts/newsletter_issue.py set %s" % (pfad, PLATZHALTER, pfad),
              file=sys.stderr)
        return 1
    ist = nummer_aus_text(text)
    soll = naechste_nummer(datum, verz)
    if ist is None:
        print("FEHLER %s: keine ausgabennummer gefunden" % pfad, file=sys.stderr)
        return 1
    if ist != soll:
        v = letzte_vor(datum, verz)
        print("FEHLER %s: ausgabe %d steht drin, gezaehlt wird %d (%s trug %s)"
              % (pfad, ist, soll,
                 os.path.basename(v[1]) if v else "keine fruehere ausgabe",
                 v[2] if v else "-"), file=sys.stderr)
        return 1
    print("ok, %s ist ausgabe %d, eine mehr als die letzte davor" % (os.path.basename(pfad), ist))
    return 0


# ---------------------------------------------------------------- Selbsttest

def selbsttest():
    import tempfile
    v = tempfile.mkdtemp()

    def schreib(name, inhalt):
        p = os.path.join(v, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(inhalt)
        return p

    kopf = "<title>Kaspa Pulse Weekly, issue %s</title><div>weekly numbers &middot; issue %s</div>"
    schreib("2026-09-14.html", kopf % (10, 10))
    schreib("2026-09-21.html", kopf % (11, 11))
    schreib("2026-09-28.html", kopf % (12, 12))
    p13 = schreib("2026-10-05.html", kopf % (13, 13))

    assert naechste_nummer(dt.date(2026, 10, 12), v) == 14
    assert naechste_nummer(dt.date(2026, 10, 5), v) == 13
    assert pruefe(p13, v) == 0

    # neue ausgabe mit platzhalter: set traegt 14 ein, zweimal aufgerufen bleibt 14
    p14 = schreib("2026-10-12.html", kopf % (PLATZHALTER, PLATZHALTER))
    assert pruefe(p14, v) == 1                      # platzhalter ist ein fehler
    alt, neu = setze(p14, v)
    assert neu == 14, (alt, neu)
    with open(p14, encoding="utf-8") as fh:
        t = fh.read()
    assert PLATZHALTER not in t and t.count("issue 14") == 2, t
    assert setze(p14, v)[1] == 14                   # wiederholbar
    assert pruefe(p14, v) == 0

    # ein kommentar, der die regel erklaert, stoert weder pruefung noch schreiben
    p15 = schreib("2026-10-26.html",
                  "<!-- so geht es: " + PLATZHALTER + " wird von set gefuellt -->"
                  + kopf % (PLATZHALTER, PLATZHALTER))
    assert setze(p15, v)[1] == 15
    with open(p15, encoding="utf-8") as fh:
        t15 = fh.read()
    assert t15.count(PLATZHALTER) == 1, t15          # nur noch der im kommentar
    assert t15.count("issue 15") == 2, t15
    assert pruefe(p15, v) == 0
    os.remove(p15)

    # eine falsche nummer faellt auf
    p21 = schreib("2026-10-19.html", kopf % (21, 21))
    assert pruefe(p21, v) == 1

    # eine ausgefallene woche laesst die reihe weiterzaehlen, nicht zurueckspringen
    os.remove(p21)
    assert naechste_nummer(dt.date(2026, 10, 26), v) == 15

    # ganz leeres verzeichnis faengt bei 1 an
    leer = tempfile.mkdtemp()
    assert naechste_nummer(dt.date(2026, 10, 5), leer) == 1

    print("selbsttest ok: hochzaehlen, platzhalter, wiederholbar, luecke, leeres verzeichnis")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modus", nargs="?", choices=("next", "set", "check", "liste"))
    ap.add_argument("datei", nargs="?")
    ap.add_argument("--date", default="", help="Datum der neuen Ausgabe, Vorgabe heute")
    ap.add_argument("--dir", default=VERZ, help="Verzeichnis der Ausgaben")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    if not a.modus:
        sys.exit("modus fehlt (next, set, check, liste) oder --selbsttest")
    if a.modus == "next":
        datum = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
        v = letzte_vor(datum, a.dir)
        if v:
            print("%d" % (v[2] + 1))
            print("letzte davor: %s, ausgabe %d" % (os.path.basename(v[1]), v[2]),
                  file=sys.stderr)
        else:
            print("1")
            print("keine fruehere ausgabe gefunden, faengt bei 1 an", file=sys.stderr)
        return 0
    if a.modus == "liste":
        for d, pfad, nr in ausgaben(a.dir):
            print("%s  ausgabe %s" % (d, nr))
        return 0
    if not a.datei:
        sys.exit("datei fehlt")
    if not os.path.isfile(a.datei):
        sys.exit("datei zeigt ins Leere: %s" % a.datei)
    if a.modus == "set":
        setze(a.datei, a.dir)
        return 0
    return pruefe(a.datei, a.dir)


if __name__ == "__main__":
    sys.exit(main())
