#!/usr/bin/env python3
"""
waechter fuer die lesetexte im dashboard

Die vier "the read" texte liegen ausserhalb der bot-marker. Niemand fasst
sie automatisch an, also veralten sie lautlos. Genau das ist am 15.08.
passiert und nur durch zufall aufgefallen.

Er prueft zweierlei gegen den DATA-block derselben datei.

  1. jede zahl im text muss im datenblock vorkommen. rundung ist erlaubt,
     erfindung nicht.
  2. jedes datum im text muss entweder in der vergangenheit liegen oder
     der naechsten reduktion entsprechen. ein zukuenftiges datum, das der
     block nicht kennt, ist eine behauptung.

    python3 scripts/check_reads.py index.html
    python3 scripts/check_reads.py --selftest
"""

import json
import re
import sys
from datetime import date

MONATE = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
          "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
          "november": 11, "december": 12}

# zahlen, die immer erlaubt sind. jahreszahlen und kleine ordnungszahlen
# stehen in jedem satz und meinen keine kennzahl.
FREI = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 24, 100,
        2024, 2025, 2026, 2027}


def hole_data(html):
    m = re.search(r"WEEKLY-DATA-START(.*?)WEEKLY-DATA-END", html, re.S)
    if not m:
        raise RuntimeError("keine datenmarker gefunden")
    j = re.search(r"\{.*\}", m.group(1), re.S)
    if not j:
        raise RuntimeError("kein json im datenblock")
    return json.loads(j.group(0))


def hole_reads(html):
    """die vier lesetexte. sie stehen jeweils hinter der ueberschrift."""
    roh = re.findall(r'the read(.*?)</div>', html, re.S | re.I)
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
    """alle zahlen aus dem datenblock, egal wie tief sie liegen."""
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


def pruefe(html, heute=None):
    data = hole_data(html)
    reads = hole_reads(html)
    kandidaten = flach(data)
    stand = data.get("updated") or ""
    heute = heute or (date.fromisoformat(stand) if stand else date.today())
    naechste = (data.get("emission") or {}).get("next_reduction_at") or ""
    n_mon, n_tag = (0, 0)
    if naechste:
        d = date.fromisoformat(naechste[:10])
        n_mon, n_tag = d.month, d.day

    fehler = []
    for i, text in enumerate(reads, 1):
        for roh, wert in zahlen(text):
            if wert in FREI:
                continue
            if not passt(wert, kandidaten):
                fehler.append("panel %d, zahl %s steht in keinem datenfeld" % (i, roh))
        for mon, tag in daten(text):
            m = MONATE[mon]
            ist_naechste = (m == n_mon and tag == n_tag)
            in_zukunft = date(heute.year, m, tag) > heute
            if in_zukunft and not ist_naechste:
                fehler.append("panel %d, %s %d liegt in der zukunft und steht "
                              "nicht im datenblock" % (i, mon, tag))
    return reads, fehler


def run_selftest():
    basis = ('<!-- WEEKLY-DATA-START -->{"updated":"2026-08-10",'
             '"emission":{"next_reduction_at":"2026-09-04T16:45:44Z"},'
             '"week":{"hashrate":290.4,"tps":2.67,"dex_vol":112441}}'
             '<!-- WEEKLY-DATA-END -->')
    def bau(txt):
        return basis + '<div>the read<div>' + txt + '</div></div>'

    fails = []
    def check(name, got, want):
        if got != want:
            fails.append("%s\n    ist  %r\n    soll %r" % (name, got, want))

    ok = "mining power fell to 290 PH/s while throughput hit 2.67 per second."
    check("saubere zahlen", pruefe(bau(ok + " " * 40))[1], [])

    bad = "mining power fell to 412 PH/s this week and nothing else happened here."
    check("erfundene zahl faellt auf", len(pruefe(bau(bad))[1]), 1)

    rund = "about $112K a day changes hands, and the hashrate sits near 290."
    check("rundung ist erlaubt", pruefe(bau(rund + " " * 40))[1], [])

    alt = "the cut on august 5 took the reward down, the next lands september 4."
    check("vergangenes datum ist ok", pruefe(bau(alt))[1], [])

    zu = "the next cut lands december 24 and changes the emission for everyone."
    check("falsches zukunftsdatum faellt auf", len(pruefe(bau(zu))[1]), 1)

    check("text wird gefunden", len(pruefe(bau(ok + " " * 40))[0]), 1)

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
    print("selftest ok, 7 faelle")
    return 0


def main(argv):
    if "--selftest" in argv:
        return run_selftest()
    if not argv:
        print(__doc__)
        return 2
    with open(argv[0], "r", encoding="utf-8") as fh:
        html = fh.read()
    reads, fehler = pruefe(html)
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
