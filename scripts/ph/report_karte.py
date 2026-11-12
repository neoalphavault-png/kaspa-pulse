#!/usr/bin/env python3
"""report_karte.py - Karte zum Upgrade-Report v1 im PulseHawk-Stil (Ben, 07.11.2026).

Liest die Report-CSV aus pulsehawk/methods (upgrade_report/report_v1.py,
Format in FORMATS.md) und baut eine Karte 1080 x 1350 mit ph_stil.py:
grosse Zahl der gezaehlte Median der Abstaende nach der Aktivierung (M1
p50_after), darunter der berechnete Wert, dann vier Zeilen gezaehlt gegen
berechnet. Nur Werte aus der CSV, keine eigene Rechnung. Fehlt ein Wert,
bricht das Skript ab, statt zu raten.

    python3 scripts/ph/report_karte.py --csv report-v1-zcash-mainnet-nu7.csv \
        --titel "zcash nu7 upgrade report" --aus <ordner>
    python3 scripts/ph/report_karte.py --selbsttest
"""
import argparse
import csv
import html as H
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ph_stil as S  # noqa: E402

B, BH = S.FORMAT["hoch"]


def lesen(pfad):
    with open(pfad, newline="") as f:
        return {r["key"]: r for r in csv.DictReader(f)}


def wert(z, key):
    if key not in z or z[key]["value"] in ("", "missing", "never"):
        raise SystemExit(f"wert {key} fehlt in der report-csv, keine karte")
    return z[key]


def zahl(v, nk=1):
    x = float(v)
    return f"{x:,.0f}" if nk == 0 or x == int(x) and abs(x) >= 100 else f"{x:,.{nk}f}"


def datum(utc):
    """'2026-11-06 02:34:02' -> '6 nov 02:34 utc'."""
    d = datetime.strptime(utc, "%Y-%m-%d %H:%M:%S")
    return f"{d.day} {d.strftime('%b').lower()} {d.strftime('%H:%M')} utc"


def zeit(v):
    """Zeitabstand nach der Regel vom 08.11.2026: ab 60 s als min und s, darunter Sekunden mit einer Stelle."""
    x = float(v)
    if abs(x) >= 60:
        return S.dauer(x)
    return f"{x:.0f} s" if x == int(x) else f"{x:.1f} s"


def zeilen(z):
    """(label, counted, computed) fuer die Tabelle."""
    t = wert(z, "target_after")["value"]
    return [
        ("90% of gaps within", zeit(wert(z, "p90_after")["value"]), zeit(wert(z, "p90_after_model")["value"])),
        ("99% of gaps within", zeit(wert(z, "p99_after")["value"]), zeit(wert(z, "p99_after_model")["value"])),
        (f"gaps longer than {zeit(float(t) * 5)}", zahl(wert(z, "gaps_above_5x_target_after")["value"], 0),
         zahl(wert(z, "gaps_above_5x_target_after_model")["value"])),
        ("longest gap", zeit(wert(z, "longest_gap_after")["value"]), ""),
    ]


def html(z, titel, skala=1.0):
    F, T = S.FARBE, S.SCHRIFT
    p50 = wert(z, "p50_after")
    modell = wert(z, "p50_after_model")["value"]
    ziel = wert(z, "target_after")["value"]
    reihen = "".join(
        f'<tr><td class="l">{H.escape(a)}</td><td class="c">{H.escape(b)}</td><td class="m">{H.escape(c)}</td></tr>'
        for a, b, c in zeilen(z))
    css = f"""
.zahl {{ color:{F["tuerkis"]}; }}
table {{ width:100%; border-collapse:collapse; margin-top:64px; }}
th {{ font-size:{T["klein"][0]}px; font-weight:400; color:{F["neben"]}; text-align:right; padding:0 0 18px; }}
th.l {{ text-align:left; }}
td {{ font-size:{T["label_leise"][0]}px; font-weight:400; padding:18px 0; border-top:{S.LINIE_PX}px solid {F["linie"]}; }}
td.l {{ color:{F["neben"]}; }}
td.c {{ text-align:right; color:{F["text"]}; font-weight:{T["label"][1]}; }}
td.m {{ text-align:right; color:{F["neben"]}; width:220px; }}
"""
    inhalt = f"""
<div class="klein kicker">{H.escape(titel)}</div>
<div class="titel" style="margin-top:10px">block intervals after activation</div>
<div class="zahl" data-rolle="gezaehlt" style="margin-top:64px">{zeit(p50["value"])}</div>
<div class="unter" style="margin-top:14px">half of all blocks came within {zeit(p50["value"])} of the one before, the model says {zeit(modell)}</div>
<table><tr><th class="l"></th><th>counted</th><th>computed</th></tr>{reihen}</table>
<div class="klein" style="margin-top:44px">target {zeit(ziel)}, {int(p50["n"]):,} intervals from {datum(p50["window_from_utc"])} to {datum(p50["window_to_utc"])}, header times from our own header client.</div>
"""
    return S.seite(inhalt, B, BH, skala, extra_css=css)


def bauen(csv_pfad, titel, aus):
    os.makedirs(aus, exist_ok=True)
    z = lesen(csv_pfad)
    png = os.path.join(aus, "report-karte-1080x1350.png")
    q = S.rendern(html(z, titel), png, B, BH)
    S.vorschau(png, os.path.join(aus, "report-karte-390.png"))
    return png, S.pruefen_daten(S.messen(q, B, BH), B, BH)


def selbsttest():
    import tempfile
    fehler = []
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "r.csv")
        kopf = "metric,key,value,unit,kind,method,window_from_utc,window_to_utc,n,source,note\n"
        werte = {"target_after": 25, "p50_after": 18.0, "p50_after_model": 17.3, "p90_after": 56.0,
                 "p90_after_model": 57.6, "p99_after": 113.8, "p99_after_model": 115.1,
                 "gaps_above_5x_target_after": 10, "gaps_above_5x_target_after_model": 14.3,
                 "longest_gap_after": 188}
        with open(p, "w") as f:
            f.write(kopf + "".join(f"M1,{k},{v},s,counted,PH-M-001,2026-10-17 15:14:40,2026-10-18 06:12:01,2124,,\n"
                                   for k, v in werte.items()))
        png, klagen = bauen(p, "zcash testnet example report", d)
        for k in klagen:
            print("FEHL", k)
        fehler += klagen
        if not os.path.exists(png):
            fehler.append("keine karte")
        with open(p, "w") as f:
            f.write(kopf + "M1,p50_after,missing,s,counted,,,,,,\n")
        try:
            html(lesen(p), "x")
            fehler.append("fehlender wert nicht erkannt")
        except SystemExit:
            print("ok   fehlender wert bricht ab")
    print("alle testfaelle bestanden" if not fehler else "%d fehler" % len(fehler))
    return 1 if fehler else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--csv")
    ap.add_argument("--titel", default="upgrade report")
    ap.add_argument("--aus")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    png, klagen = bauen(a.csv, a.titel.lower(), a.aus)
    print(png)
    print("\n".join("FEHLER  " + k for k in klagen) or "ok      stil-pruefung bestanden")
    return 1 if klagen else 0


if __name__ == "__main__":
    sys.exit(main())
