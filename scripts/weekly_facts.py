#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
weekly_facts.py - die drei Zahlen der Montagsausgabe an einer Stelle rechnen,
und ein Waechter, der die eine Rundungsfalle nicht wiederkommen laesst.

Anlass (Ben, 05.10.2026). Im Newsletter zur Woche 03.10. standen drei Zeilen
falsch oder unbelegt:

  1. "1,525,975,596 to 1,524,397,554 kas, 1,578,043 less". Die Endpunkte
     stehen gerundet da, die Differenz war aus den ungerundeten gerechnet und
     dann gerundet (1 578 042,52 wird 1 578 043). Wer die beiden gedruckten
     Zahlen selbst abzieht, bekommt 1 578 042. Dieselbe Falle steckte in der
     Emissionszeile: 1 885 832 minus 1 779 989 ist 105 843, gedruckt stand
     105 844 (exakt 105 843,64).
  2. "wednesday 4 nov, 13:45 utc". Die Uhrzeit ist die Vorrollung
     ANCHOR_TS + 4 × STEP aus reward_cut_alert.py. Der Schritt landet auf
     einem Block Score, nicht auf einer Uhr, und STEP ist 30 Tage 10,5
     Stunden lang, verschiebt die Uhrzeit also jeden Monat um 10,5 Stunden.
     Das Datum traegt diese Unschaerfe, die Minute nicht. Also wird kuenftig
     nur das Datum veroeffentlicht.
  3. "the 2nd widest of the 77 weeks". Stand in keinem Skript und war nicht
     belegt. Hier wird der Rang gegen die eigene Reihe gerechnet, mit
     Zweitplatziertem, damit die Behauptung pruefbar ist oder faellt.

DIE REGEL FUER DIFFERENZEN. Stehen zwei Endpunkte gerundet im Text, ist die
gedruckte Differenz die Differenz der GERUNDETEN Endpunkte. Erst runden, dann
abziehen. Sonst widerspricht der Text der Rechnung, die der Leser selbst
macht, und genau das ist am 05.10. passiert.

    python3 scripts/weekly_facts.py fenster --von 1525975596.46 --bis 1524397553.94
    python3 scripts/weekly_facts.py emission
    python3 scripts/weekly_facts.py cut
    python3 scripts/weekly_facts.py linie --wochen 21
    python3 scripts/weekly_facts.py pruefe index.html newsletter/2026-10-05.html

Ein Absatz, der eine falsche Zahl absichtlich zitiert, traegt den Vermerk
"weekly_facts: ignore"; dort sieht der Waechter weg.
    python3 scripts/weekly_facts.py --selbsttest

Nur Standardbibliothek.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDLES = os.path.join(ROOT, "data", "kas-candles.json")

# Anker, identisch zu scripts/reward_cut_alert.py. Ein bekannter Cut,
# 05.07.2026 19:45:44 UTC, Reward danach 2.44997148 KAS je Block.
ANCHOR_TS = 1783280744
ANCHOR_REWARD = 2.44997148
STEP = (365.25 / 12) * 86400
RATIO = 0.5 ** (1 / 12)
BPS = 10
DAY = 86400

MONATE_EN = ["january", "february", "march", "april", "may", "june", "july",
             "august", "september", "october", "november", "december"]


# ------------------------------------------------------------------ Differenz

def fenster(von, bis):
    """Zwei Lesungen, eine veroeffentlichungsfertige Differenz.

    Erst runden, dann abziehen. differenz_exakt steht nur zur Kontrolle da
    und gehoert NICHT in einen Text, in dem die Endpunkte gerundet stehen."""
    von_g, bis_g = round(von), round(bis)
    return {
        "von": von, "bis": bis,
        "von_gerundet": von_g, "bis_gerundet": bis_g,
        "differenz": abs(von_g - bis_g),
        "richtung": "less" if bis_g < von_g else "more",
        "differenz_exakt": round(abs(von - bis), 2),
    }


def zahl(n):
    return format(int(n), ",")


def fenster_zeile(von, bis):
    f = fenster(von, bis)
    return "%s to %s kas, %s %s" % (zahl(f["von_gerundet"]), zahl(f["bis_gerundet"]),
                                    zahl(f["differenz"]), f["richtung"])


# ------------------------------------------------------------------ Emission

def reward_nach_schritten(n):
    return ANCHOR_REWARD * RATIO ** n


def emission_je_tag(reward):
    return reward * BPS * DAY


def emission_zeile(n_vorher, n_nachher):
    """Emission vor und nach einem Cut, Differenz nach derselben Regel."""
    a = emission_je_tag(reward_nach_schritten(n_vorher))
    b = emission_je_tag(reward_nach_schritten(n_nachher))
    f = fenster(a, b)
    return "%s to %s kas, %s fewer new coins a day" % (
        zahl(f["von_gerundet"]), zahl(f["bis_gerundet"]), zahl(f["differenz"]))


# ------------------------------------------------------------------ Senkung

def schritte_bis(now):
    n = 0
    while ANCHOR_TS + STEP * (n + 1) <= now:
        n += 1
    return n


def naechste_senkung(now=None):
    """Die naechste monatliche Senkung.

    datum traegt die Vorrollung und ist belastbar: die Modellzeit liegt rund
    zehn Stunden von Mitternacht entfernt, ein Blockratenfehler von einem
    Promille ueber dreissig Tage sind 44 Minuten. Die Uhrzeit selbst ist
    NICHT belastbar und wird deshalb nicht veroeffentlicht."""
    now = now if now is not None else dt.datetime.now(dt.timezone.utc).timestamp()
    n = schritte_bis(now)
    ts = ANCHOR_TS + STEP * (n + 1)
    when = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
    return {
        "datum": when.date().isoformat(),
        "wochentag": when.strftime("%A").lower(),
        "modellzeit_utc": when.strftime("%Y-%m-%d %H:%M:%S"),
        "reward_jetzt": round(reward_nach_schritten(n), 4),
        "reward_danach": round(reward_nach_schritten(n + 1), 4),
        "schritt_nr": n + 1,
    }


def senkung_zeile(now=None):
    """Nur Datum, nie die Uhrzeit. Siehe naechste_senkung()."""
    s = naechste_senkung(now)
    d = dt.date.fromisoformat(s["datum"])
    return "%s %d %s, reward to %s kas" % (
        s["wochentag"], d.day, MONATE_EN[d.month - 1][:3], ("%.4f" % s["reward_danach"]))


# ------------------------------------------------------------------ Linien

def wochenschluesse():
    with open(CANDLES, encoding="utf-8") as fh:
        d = json.load(fh)
    wk = d["kas_weekly"]
    return [w[0] for w in wk], [w[1] for w in wk]


def ema_reihe(closes, n):
    """Exponentiell, gesaet mit dem einfachen Mittel der ersten n. Dieselbe
    Rechnung wie auf kaspa-weekly.html und im Newsletter."""
    out = [None] * (n - 1)
    if len(closes) < n:
        return out[:len(closes)]
    seed = sum(closes[:n]) / n
    out.append(seed)
    e, k = seed, 2 / (n + 1)
    for c in closes[n:]:
        e = c * k + e * (1 - k)
        out.append(e)
    return out


def sma_reihe(closes, n):
    out = []
    for i in range(len(closes)):
        out.append(None if i < n - 1 else sum(closes[i - n + 1:i + 1]) / n)
    return out


def linie(wochen=21, labels=None, closes=None):
    """Abstand des letzten Schlusses zur Linie, plus Rang in der eigenen Reihe."""
    if labels is None:
        labels, closes = wochenschluesse()
    reihe = ema_reihe(closes, wochen) if wochen == 21 else sma_reihe(closes, wochen)
    paare = [(labels[i], closes[i], reihe[i], (closes[i] / reihe[i] - 1) * 100)
             for i in range(len(closes)) if reihe[i]]
    if not paare:
        raise RuntimeError("die reihe traegt die %d-wochen-linie noch nicht" % wochen)
    jetzt = paare[-1]
    sortiert = sorted(paare, key=lambda p: -p[3])
    rang = sortiert.index(jetzt) + 1
    zweiter = sortiert[1] if rang == 1 else sortiert[0]
    return {
        "wochen_mit_linie": len(paare),
        "ab": paare[0][0],
        "label": jetzt[0],
        "schluss": round(jetzt[1], 5),
        "linie": round(jetzt[2], 6),
        "abstand_pct": round(jetzt[3], 2),
        "rang": rang,
        "ueber_der_linie": sum(1 for p in paare if p[3] > 0),
        "naechster_im_rang": {"label": zweiter[0], "abstand_pct": round(zweiter[3], 2)},
    }


def ordnung(n):
    """1st, 2nd, 3rd, 4th ... und 11th bis 13th, die Ausnahme."""
    if n % 100 in (11, 12, 13):
        return "%dth" % n
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def linien_satz(wochen=21, labels=None, closes=None):
    """Der veroeffentlichungsfertige Satz. Ein Superlativ steht hier nur mit
    Zeitraum UND mit dem Zweitplatzierten, damit der Leser ihn pruefen kann."""
    r = linie(wochen, labels, closes)
    return ("%.2f percent above, the %s widest gap of the %d weeks our series carries "
            "that line, behind %.2f percent (%s)"
            % (r["abstand_pct"], ordnung(r["rang"]), r["wochen_mit_linie"],
               r["naechster_im_rang"]["abstand_pct"], r["naechster_im_rang"]["label"]))


# ------------------------------------------------------------------ Waechter

# Nur ganze, gedruckte Zahlen ab sechs Stellen, mit oder ohne Tausendertrenner.
# Was davor oder danach eine Dezimalstelle traegt, bleibt draussen: "0,033388"
# ist keine 33.388, und "1 525 975 596,46" ist der ungerundete Wert, der an
# dieser Pruefung nichts zu suchen hat. Geprueft wird, was gedruckt steht, und
# gedruckt steht die gerundete Zahl.
ZAHL_RE = re.compile("(?<![\\d.,\u202f\u00a0])"
                     "(?:\\d{1,3}(?:[,\u202f\u00a0 ]\\d{3})+|\\d{6,})"
                     "(?![\\d.,\u202f\u00a0 ]\\d)")
TOLERANZ = 3          # so weit darf eine gedruckte Differenz danebenliegen,
                      # damit wir sie noch als gemeinte Differenz erkennen

# Ein Text, der eine falsche Zahl absichtlich zitiert (ein Korrekturvermerk,
# ein Pruefbericht), traegt diesen Vermerk im selben Absatz. Dann sieht der
# Waechter dort weg. Sichtbar im Text, damit niemand heimlich stummschaltet.
AUSNAHME = "weekly_facts: ignore"


def segmente(text, ist_html):
    """Der Text in Stuecke, innerhalb derer eine Differenz gemeint sein kann.

    HTML: jede Tabellenzelle und jeder Block ist ein Stueck, ueber Zellgrenzen
    wird nicht gerechnet. Markdown und Fliesstext: ein Absatz ist ein Stueck,
    Zeilenumbrueche innerhalb eines Absatzes werden aufgehoben, denn eine
    Zeile wie "1,885,832 to 1,779,989, which is 105,844 fewer" steht im
    Uploadpaket umbrochen da. Tabellenzeilen werden an den Strichen getrennt.
    """
    if ist_html:
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
        text = re.sub(r"(?s)<!--.*?-->", " ", text)
        text = re.sub(r"(?i)</(td|th|tr|div|p|li|h\d)>", "\n\n", text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&[a-z]+;|&#\d+;", " ", text)
    out = []
    for absatz in re.split(r"\n\s*\n", text):
        if "|" in absatz:
            roh = re.split(r"[|\n]+", absatz)
        else:
            roh = [absatz.replace("\n", " ")]
        for stueck in roh:
            # Zwei Koernungen, und beide werden geprueft: der ganze Absatz,
            # weil eine Differenz ueber einen Punkt hinweg stehen kann ("it
            # held A. that is D less"), und der einzelne Satz, damit ein
            # langer Absatz nicht zufaellig drei Zahlen zusammenwirft.
            ganz = re.sub(r"\s+", " ", stueck).strip()
            if ganz:
                out.append(ganz)
            teile = re.split(r"(?<=[.!?])\s+|;", stueck)
            if len(teile) > 1:
                for teil in teile:
                    teil = re.sub(r"\s+", " ", teil).strip()
                    if teil:
                        out.append(teil)
    return out


def parse_zahl(s):
    return int(re.sub(r"[,   ]", "", s))


def pruefe_text(text, ist_html=False):
    """Findet Stellen, an denen eine gedruckte Differenz der Differenz der
    gedruckten Endpunkte widerspricht.

    Je Segment wird jedes Zahlentripel angesehen. Gelesen wird es kanonisch:
    die beiden groessten Zahlen sind die Endpunkte, die kleinste ist die
    Differenz. Gemeldet wird nur, wenn die kleinste knapp daneben liegt, denn
    knapp daneben heisst gemeint und falsch gerundet. Weit daneben heisst,
    die drei Zahlen haben nichts miteinander zu tun."""
    befunde = []
    for seg in segmente(text, ist_html):
        if AUSNAHME in seg:
            continue
        gesehen = set()      # je Segment, damit jede Fundstelle gemeldet wird
        werte = sorted({abs(parse_zahl(m.group(0))) for m in ZAHL_RE.finditer(seg)},
                       reverse=True)
        if len(werte) < 3:
            continue
        for i in range(len(werte)):
            for j in range(i + 1, len(werte)):
                for k in range(j + 1, len(werte)):
                    a, b, d = werte[i], werte[j], werte[k]
                    soll = a - b
                    if soll <= 0 or d != min(a, b, d):
                        continue
                    if d != soll and abs(d - soll) <= TOLERANZ:
                        if (a, b, d) in gesehen:
                            continue
                        gesehen.add((a, b, d))
                        befunde.append({
                            "segment": seg[:200],
                            "von": a, "bis": b,
                            "gedruckt": d, "richtig": soll,
                        })
    return befunde


def pruefe_dateien(pfade):
    alle = []
    for p in pfade:
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        for b in pruefe_text(text, ist_html=p.lower().endswith((".html", ".htm"))):
            b["datei"] = p
            alle.append(b)
    for b in alle:
        print("FEHLER %s: %s minus %s ist %s, gedruckt steht %s\n  %r"
              % (b["datei"], zahl(b["von"]), zahl(b["bis"]), zahl(b["richtig"]),
                 zahl(b["gedruckt"]), b["segment"]), file=sys.stderr)
    if alle:
        print("%d stelle(n) mit einer Differenz, die nicht zu den gedruckten "
              "Endpunkten passt. Regel: erst runden, dann abziehen." % len(alle),
              file=sys.stderr)
        return 1
    print("ok, %d datei(en) geprueft: jede gedruckte Differenz passt zu ihren "
          "gedruckten Endpunkten" % len(pfade))
    return 0


# ------------------------------------------------------------------ Selbsttest

def selbsttest():
    # 1. die beiden Faelle vom 05.10.2026
    f = fenster(1525975596.46, 1524397553.94)
    assert f["differenz"] == 1578042, f
    assert f["differenz_exakt"] == 1578042.52, f
    assert f["richtung"] == "less"
    assert fenster_zeile(1525975596.46, 1524397553.94) == \
        "1,525,975,596 to 1,524,397,554 kas, 1,578,042 less"
    assert emission_zeile(2, 3) == "1,885,832 to 1,779,989 kas, 105,843 fewer new coins a day", \
        emission_zeile(2, 3)
    # runden vor dem abziehen ist nicht dasselbe wie abziehen und dann runden
    assert round(1525975596.46 - 1524397553.94) == 1578043

    # 2. die naechste Senkung, gerechnet vom 05.10.2026 12:00 UTC
    now = dt.datetime(2026, 10, 5, 12, 0, tzinfo=dt.timezone.utc).timestamp()
    s = naechste_senkung(now)
    assert s["datum"] == "2026-11-04", s
    assert s["wochentag"] == "wednesday", s
    assert s["reward_danach"] == 1.9445, s
    assert s["reward_jetzt"] == 2.0602, s
    assert senkung_zeile(now) == "wednesday 4 nov, reward to 1.9445 kas", senkung_zeile(now)
    assert ":" not in senkung_zeile(now)          # nie eine Uhrzeit
    # STEP verschiebt die Uhrzeit um 10,5 Stunden je Schritt, daher kein Takt
    assert abs((STEP % 86400) / 3600 - 10.5) < 1e-6

    # 3. Rang in einer kleinen, selbst gebauten Reihe
    labels = ["w%02d" % i for i in range(25)]
    closes = [1.0] * 21 + [1.5, 1.2, 1.1, 1.3]
    r = linie(21, labels, closes)
    assert r["wochen_mit_linie"] == 5, r
    assert r["rang"] == 2, r                      # 1.3 ist der zweitgroesste Abstand
    assert r["naechster_im_rang"]["label"] == "w21", r
    assert ordnung(1) == "1st" and ordnung(2) == "2nd" and ordnung(3) == "3rd"
    assert ordnung(4) == "4th" and ordnung(11) == "11th" and ordnung(12) == "12th"
    assert ordnung(13) == "13th" and ordnung(21) == "21st"

    # 4. der Waechter findet beide Faelle und schlaegt nicht grundlos an.
    #    Dezimalkommas und ungerundete Werte bleiben draussen, sonst waere
    #    "0,033388" eine 33.388 und der exakte Heartbeat-Wert ein Endpunkt.
    assert pruefe_text("Schluss 0,04790, 50w-Linie 0,036729, 21w-Linie 0,033388") == []
    assert pruefe_text("28.09. 1 525 975 596,46 KAS und 03.10. 1 524 397 553,94 KAS, "
                       "Differenz 1 578 042,52") == []
    assert pruefe_text("emission 1,885,832.45 to 1,779,988.81, that is 105,843.64 fewer") == []
    schlecht = "it held 1,525,975,596 kas, later 1,524,397,554 kas, that is 1,578,043 less"
    b = pruefe_text(schlecht)
    assert len(b) == 1 and b[0]["richtig"] == 1578042, b
    gut = schlecht.replace("1,578,043", "1,578,042")
    assert pruefe_text(gut) == []
    assert pruefe_text(schlecht + " (weekly_facts: ignore, absichtlich zitiert)") == []
    emi = "daily emission 1,885,832 to 1,779,989 kas, 105,844 fewer new coins a day"
    assert len(pruefe_text(emi)) == 1, pruefe_text(emi)
    assert pruefe_text(emi.replace("105,844", "105,843")) == []
    # drei Zahlen ohne Differenzabsicht bleiben unbehelligt
    assert pruefe_text("volume 10,175,119 against 12,614,961, hashrate 343,920") == []
    # html: zwei Zellen sind zwei Segmente, ueber Zellgrenzen wird nicht gerechnet
    html = ("<tr><td>1,525,975,596 to 1,524,397,554 kas, 1,578,042 less</td></tr>"
            "<tr><td>daily emission 1,885,832 to 1,779,989 kas, 105,844 fewer</td></tr>")
    b = pruefe_text(html, ist_html=True)
    assert len(b) == 1 and b[0]["gedruckt"] == 105844, b

    print("selbsttest ok: differenzregel, senkung ohne uhrzeit, rang, waechter")
    return 0


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modus", nargs="?", choices=("fenster", "emission", "cut", "linie", "pruefe"))
    ap.add_argument("dateien", nargs="*")
    ap.add_argument("--von", type=float)
    ap.add_argument("--bis", type=float)
    ap.add_argument("--wochen", type=int, default=21)
    ap.add_argument("--schritt", type=int, help="emission: Schrittnummer nach dem Anker")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    if not a.modus:
        sys.exit("modus fehlt (fenster, emission, cut, linie, pruefe) oder --selbsttest")

    if a.modus == "fenster":
        if a.von is None or a.bis is None:
            sys.exit("--von und --bis fehlen")
        f = fenster(a.von, a.bis)
        print(json.dumps(f, indent=1))
        print(fenster_zeile(a.von, a.bis))
    elif a.modus == "emission":
        n = a.schritt if a.schritt is not None else schritte_bis(
            dt.datetime.now(dt.timezone.utc).timestamp())
        print("schritt %d auf %d" % (n - 1, n))
        print(emission_zeile(n - 1, n))
    elif a.modus == "cut":
        s = naechste_senkung()
        print(json.dumps(s, indent=1))
        print("veroeffentlichen:", senkung_zeile())
        print("die modellzeit %s UTC bleibt im haus, STEP verschiebt sie je "
              "schritt um 10,5 stunden" % s["modellzeit_utc"])
    elif a.modus == "linie":
        r = linie(a.wochen)
        print(json.dumps(r, indent=1))
        print("veroeffentlichen:", linien_satz(a.wochen))
    elif a.modus == "pruefe":
        if not a.dateien:
            sys.exit("keine dateien angegeben")
        return pruefe_dateien(a.dateien)
    return 0


if __name__ == "__main__":
    sys.exit(main())
