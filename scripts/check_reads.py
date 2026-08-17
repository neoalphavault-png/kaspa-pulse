#!/usr/bin/env python3
"""
waechter fuer die lesetexte im dashboard

Die lesetexte liegen ausserhalb der bot-marker. Niemand fasst sie
automatisch an, also veralten sie lautlos. Genau das ist am 15.08.
passiert und nur durch zufall aufgefallen.

Version 2, nach dem ersten echten lauf am 17.08. Drei dinge waren falsch.

  1. Der alte waechter nahm den GANZEN datenblock als quelle, also auch
     die komplette history. Eine zahl aus juli war damit gedeckt. Ein
     lesetext, der zwei wochen alt ist, waere durchgerutscht, also genau
     der fall, fuer den der waechter gebaut wurde. Jetzt zaehlen nur die
     letzte woche und die vorwoche. Die vorwoche bleibt drin, weil ein
     lesetext oft vergleicht, von 0.91 auf 2.67.
  2. Zwei der fuenf panels werden nicht aus dem wochenblock gespeist,
     sondern aus den entity-x dateien. Deren zahlen kannte der waechter
     nicht und meldete sie als erfunden. Jetzt liest er data/*.json mit,
     soweit vorhanden.
  3. Er prueft jetzt auch den block selbst. Ist der aelter als acht tage,
     ist nicht der text das problem, sondern der bot, der ihn schreiben
     sollte.

    python3 scripts/check_reads.py index.html
    python3 scripts/check_reads.py --selftest
"""

import glob
import json
import os
import re
import sys
from datetime import date, timedelta

MONATE = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
          "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
          "november": 11, "december": 12}

# zahlen, die immer erlaubt sind. jahreszahlen und kleine ordnungszahlen
# stehen in jedem satz und meinen keine kennzahl.
FREI = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 24, 100,
        2024, 2025, 2026, 2027}

# so alt darf der datenblock sein, bevor der waechter ihn selbst anmeckert
MAX_ALTER_TAGE = 8


def hole_data(html):
    m = re.search(r"WEEKLY-DATA-START(.*?)WEEKLY-DATA-END", html, re.S)
    if not m:
        raise RuntimeError("keine datenmarker gefunden")
    j = re.search(r"\{.*\}", m.group(1), re.S)
    if not j:
        raise RuntimeError("kein json im datenblock")
    return json.loads(j.group(0))


def hole_reads(html):
    """die lesetexte. sie stehen jeweils hinter der ueberschrift."""
    roh = re.findall(r"the read(.*?)</div>", html, re.S | re.I)
    out = []
    for t in roh:
        t = re.sub(r"<[^>]+>", " ", t)
        t = re.sub(r"&[a-z]+;", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) > 60:
            out.append(t)
    return out


def zahlen(text):
    """alle zahlen im text, prozent und dollar mit eingeschlossen."""
    out = []
    for roh in re.findall(r"\d[\d,.]*", text):
        s = roh.rstrip(".").replace(",", "")
        if not s:
            continue
        try:
            out.append((roh, float(s)))
        except ValueError:
            pass
    return out


def flach(d, pfad=""):
    """alle zahlen aus einem gebilde, egal wie tief sie liegen."""
    out = []
    if isinstance(d, dict):
        for k, v in d.items():
            out += flach(v, pfad + "/" + str(k))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            out += flach(v, pfad + "/%d" % i)
    elif isinstance(d, (int, float)) and not isinstance(d, bool):
        out.append((pfad, float(d)))
    return out


def quellen(data, extra_dir=None):
    """
    Der zahlenvorrat, gegen den geprueft wird.

    Bewusst NICHT der ganze block. Alles ausser der history, dazu die
    letzten zwei wocheneintraege. Alles was aelter ist, ist kein beleg
    mehr, sondern nur noch ein zufaelliger treffer.
    """
    ohne_history = {k: v for k, v in data.items() if k != "history"}
    kand = flach(ohne_history)
    hist = data.get("history") or []
    for eintrag in hist[-2:]:
        kand += flach(eintrag.get("m") or {})

    # die panels, die aus einer eigenen datei gespeist werden
    if extra_dir and os.path.isdir(extra_dir):
        for pfad in sorted(glob.glob(os.path.join(extra_dir, "*.json"))):
            if os.path.getsize(pfad) > 2_000_000:
                continue
            try:
                with open(pfad, "r", encoding="utf-8") as fh:
                    kand += flach(json.load(fh), os.path.basename(pfad))
            except (ValueError, OSError):
                continue
    return kand


def passt(wert, kandidaten):
    """
    erlaubt gerundete darstellung. 112441 darf als 112 stehen, 96.26 als 96,
    290.4 als 290. der text darf runden, aber nicht erfinden.
    """
    for _, v in kandidaten:
        if v == 0:
            continue
        for teiler in (1, 1000, 1000000, 1000000000):
            z = v / teiler
            nah = abs(z - wert) < 0.51 if abs(wert) >= 10 else False
            if nah or (z and abs(z - wert) / abs(z) < 0.02):
                return True
        # prozentuale veraenderungen stehen im block oft mit vorzeichen
        if abs(abs(v) - abs(wert)) < 0.51:
            return True
    return False


def daten(text):
    """datumsangaben in der form august 5 oder september 4."""
    out = []
    for mon, tag in re.findall(r"(%s)\s+(\d{1,2})" % "|".join(MONATE), text, re.I):
        out.append((mon.lower(), int(tag)))
    return out


def hole_woche(extra_dir):
    """die woche, fuer die der wochenpost gerade laeuft."""
    if not extra_dir:
        return ""
    pfad = os.path.join(extra_dir, "week-input.json")
    try:
        with open(pfad, "r", encoding="utf-8") as fh:
            return str(json.load(fh).get("week") or "").strip()
    except (ValueError, OSError):
        return ""


def pruefe(html, heute=None, extra_dir=None, wirklich_heute=None):
    data = hole_data(html)
    reads = hole_reads(html)
    kandidaten = quellen(data, extra_dir)
    woche = hole_woche(extra_dir)
    stand = data.get("updated") or ""
    heute = heute or (date.fromisoformat(stand) if stand else date.today())
    naechste = (data.get("emission") or {}).get("next_reduction_at") or ""
    n_mon, n_tag = (0, 0)
    if naechste:
        d = date.fromisoformat(naechste[:10])
        n_mon, n_tag = d.month, d.day

    fehler = []

    # der block selbst. ein alter block macht jeden lesetext wertlos,
    # egal wie gut er zu den zahlen darin passt.
    echt = wirklich_heute or date.today()
    if stand:
        alter = (echt - date.fromisoformat(stand)).days
        if alter > MAX_ALTER_TAGE:
            fehler.append("der datenblock selbst ist %d tage alt, stand %s. "
                          "nicht die texte sind dran, sondern der bot, der "
                          "den block schreibt" % (alter, stand))
        elif woche and woche > stand:
            # der wochenpost laeuft fuer eine woche, fuer die der
            # dashboard-bot noch keine zahlen geschrieben hat. dann steht
            # auf der seite etwas anderes als im post.
            fehler.append("der post laeuft fuer woche %s, der datenblock "
                          "steht aber auf %s. erst den dashboard-bot laufen "
                          "lassen" % (woche, stand))

    for i, text in enumerate(reads, 1):
        for roh, wert in zahlen(text):
            if wert in FREI:
                continue
            if not passt(wert, kandidaten):
                fehler.append("panel %d, zahl %s steht in keinem datenfeld"
                              % (i, roh))
        for mon, tag in daten(text):
            m = MONATE[mon]
            ist_naechste = (m == n_mon and tag == n_tag)
            in_zukunft = date(heute.year, m, tag) > heute
            if in_zukunft and not ist_naechste:
                fehler.append("panel %d, %s %d liegt in der zukunft und steht "
                              "nicht im datenblock" % (i, mon, tag))
    return reads, fehler


def run_selftest():
    import tempfile

    basis = ('<!-- WEEKLY-DATA-START -->{"updated":"2026-08-17",'
             '"emission":{"next_reduction_at":"2026-09-04T16:45:44Z"},'
             '"history":['
             '{"date":"2026-07-27","m":{"tps":0.75,"hashrate":262.3}},'
             '{"date":"2026-08-10","m":{"tps":2.67,"hashrate":290.4}},'
             '{"date":"2026-08-17","m":{"hashrate":329.8,"tps":2.34,'
             '"dex_vol":112441}}]}'
             '<!-- WEEKLY-DATA-END -->')
    heute = date(2026, 8, 17)

    def bau(txt):
        return basis + "<div>the read<div>" + txt + "</div></div>"

    def p(txt, **kw):
        kw.setdefault("wirklich_heute", heute)
        return pruefe(bau(txt), **kw)

    fails = []

    def check(name, got, want):
        if got != want:
            fails.append("%s\n    ist  %r\n    soll %r" % (name, got, want))

    ok = "mining power rose to 329 PH/s while throughput sat at 2.34 per second."
    check("saubere zahlen", p(ok + " " * 40)[1], [])

    bad = "mining power fell to 412 PH/s this week and nothing else happened here."
    check("erfundene zahl faellt auf", len(p(bad)[1]), 1)

    vor = "throughput went from 2.67 last week to 2.34 now, and that is the story."
    check("vorwoche ist erlaubt", p(vor)[1], [])

    alt = "throughput went from 0.75 up to 2.34, a jump nobody should overlook."
    check("zahl aus dem juli faellt auf", len(p(alt)[1]), 1)

    rund = "about $112K a day changes hands, and the hashrate sits near 330."
    check("rundung ist erlaubt", p(rund + " " * 40)[1], [])

    frueher = "the cut on august 5 took the reward down, the next lands september 4."
    check("vergangenes datum ist ok", p(frueher)[1], [])

    zu = "the next cut lands december 24 and changes the emission for everyone."
    check("falsches zukunftsdatum faellt auf", len(p(zu)[1]), 1)

    check("text wird gefunden", len(p(ok + " " * 40)[0]), 1)

    # der block selbst veraltet
    spaet = pruefe(bau(ok + " " * 40), wirklich_heute=date(2026, 8, 27))
    check("alter datenblock faellt auf", len(spaet[1]), 1)

    # zahlen aus einer eigenen datei, zum beispiel entity x
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "entity-x-costbasis.json"), "w") as fh:
            json.dump({"total_kas": 1540000000, "avg_usd": 0.0881}, fh)
        wal = ("the largest address has bought 1.54B KAS in total at an "
               "average of $0.0881 since the first transfer landed.")
        check("fremde datei deckt die zahl",
              p(wal, extra_dir=tmp)[1], [])
        check("ohne die datei faellt sie auf", len(p(wal)[1]), 2)

        # der post laeuft fuer eine woche, die der block noch nicht kennt
        with open(os.path.join(tmp, "week-input.json"), "w") as fh:
            json.dump({"week": "2026-08-24"}, fh)
        check("block hinter dem post faellt auf",
              len(p(ok + " " * 40, extra_dir=tmp)[1]), 1)

    try:
        pruefe("<div>ohne marker</div>")
        fails.append("fehlender datenblock haette auffallen muessen")
    except RuntimeError:
        pass

    if fails:
        print("selftest FEHLGESCHLAGEN")
        for f in fails:
            print("  " + f)
        return 1
    print("selftest ok, 13 faelle")
    return 0


def main(argv):
    if "--selftest" in argv:
        return run_selftest()
    if not argv:
        print(__doc__)
        return 2
    pfad = argv[0]
    with open(pfad, "r", encoding="utf-8") as fh:
        html = fh.read()
    extra = os.path.join(os.path.dirname(os.path.abspath(pfad)), "data")
    reads, fehler = pruefe(html, extra_dir=extra)
    print("%d lesetexte gefunden" % len(reads))
    if not fehler:
        print("alle zahlen und daten decken sich mit dem datenblock")
        return 0
    print("\n%d punkte zu klaeren" % len(fehler))
    for f in fehler:
        print("  " + f)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
