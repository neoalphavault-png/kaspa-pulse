#!/usr/bin/env python3
"""nu7_karte.py - NU7-Karte "4 of 4 forecasts" (Ben, 08.11.2026, Nachtrag 2: "forecast" statt "estimate").

Fassung vom 08.11. abends: Die Karte soll die Messung verkaufen. Grosse Zahl
"4 of 4" (Schaetzungen im 90-%-Band), Tabelle aus Sicht des Blocks ("the block
came 12 min 10 s later"). Davor am selben Tag: "how close our estimates came".

Neu gebaut, weil die Fassung mit Zeitachse schwer zu lesen war (Ben 08.11.):
keine Achse, sondern eine Tabelle mit den vier Schaetzungen, "too late" und
"too early" aus einer Richtung, Zeitabstaende in Minuten und Sekunden.

Alle Werte kommen aus den Daten, nichts ist eingetippt:
  - Kopfzeit des Blocks 3.543.405 aus unseren eigenen Koepfen (koepfe.csv.gz,
    messung/zcash-mainnet), counted
  - Schaetzungen 23.10., 28.10., 04.11. aus stand-JJJJ-MM-TT.json
    (vorhersage.median_utc, band_5_utc, band_95_utc, tempo_fenster_tage)
  - Schaetzung 02.11. aus der Konfiguration der Upgrade-Wache dieses Tages
    (scripts/wache/ketten/zcash-mainnet.json in Commit 77672e28, erwartet_utc
    und band_utc); gerechnet aus den 7 Tagen davor
    (berichte/2026-11-02-nu7-hoehe-pruefung.md), daher --fenster-2nov 7
Abstand = Schaetzung minus Kopfzeit; positiv heisst "too late" (die Schaetzung
lag nach dem Block), negativ "too early".

    python3 scripts/ph/nu7_karte.py --stand stand-2026-10-23.json stand-2026-10-28.json stand-2026-11-04.json \
        --wache-2nov wache-2026-11-02.json --koepfe koepfe.csv.gz --aus <ordner>
    -> nu7-1080x1350.png, nu7-390.png, nu7-1080x1350.html, rechnung.json
"""
import argparse
import csv
import gzip
import html as H
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ph_stil as S  # noqa: E402

B, BH = S.FORMAT["hoch"]
HOEHE = 3543405


def ts(text):
    t = text.strip().replace("T", " ").replace("Z", "")
    return datetime.strptime(t, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()


def utc(t, mit_datum=False):
    d = datetime.fromtimestamp(t, timezone.utc)
    return d.strftime("%-d %b %H:%M:%S").lower() if mit_datum else d.strftime("%H:%M:%S")


def kopfzeit(pfad, hoehe=HOEHE):
    with gzip.open(pfad, "rt") as f:
        for z in csv.DictReader(f):
            if int(z["hoehe"]) == hoehe:
                return int(z["zeit"])
    raise SystemExit(f"hoehe {hoehe} nicht in {pfad}")


def schaetzungen(stand_pfade, wache_pfad, fenster_2nov):
    out = []
    for p in stand_pfade:
        v = json.load(open(p))["vorhersage"]
        tag = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(p)).group(1)
        out.append({"gemacht": tag, "quelle": os.path.basename(p), "median": ts(v["median_utc"]),
                    "band": (ts(v["band_5_utc"]), ts(v["band_95_utc"])), "fenster_tage": v["tempo_fenster_tage"]})
    if wache_pfad:
        a = json.load(open(wache_pfad))["aktivierung"]
        out.append({"gemacht": "2026-11-02", "quelle": "wache-konfiguration 77672e28", "median": ts(a["erwartet_utc"]),
                    "band": (ts(a["band_utc"][0]), ts(a["band_utc"][1])), "fenster_tage": fenster_2nov})
    return sorted(out, key=lambda x: x["gemacht"])


def rechnen(sch, kopf):
    for s in sch:
        s["differenz_s"] = int(s["median"] - kopf)
        s["richtung"] = "too late" if s["differenz_s"] > 0 else ("too early" if s["differenz_s"] < 0 else "exact")
        s["im_band"] = s["band"][0] <= kopf <= s["band"][1]
    return sch


def gemacht_text(tag):
    d = datetime.strptime(tag, "%Y-%m-%d")
    return f"{d.day} {d.strftime('%b').lower()}"


def block_kam(differenz_s):
    """Aus Sicht des Blocks (Ben 08.11. abends): Schaetzung vor dem Block heisst, der Block kam spaeter."""
    if differenz_s < 0:
        return f"{S.dauer(differenz_s)} later"
    if differenz_s > 0:
        return f"{S.dauer(differenz_s)} earlier"
    return "on time"


def vorlauf_tage(gemacht, kopf):
    """Ganze Tage zwischen dem Tag der Schaetzung und dem UTC-Tag des Blocks."""
    d0 = datetime.strptime(gemacht, "%Y-%m-%d").date()
    return (datetime.fromtimestamp(kopf, timezone.utc).date() - d0).days


def html(sch, kopf, skala=1.0):
    F, T = S.FARBE, S.SCHRIFT
    im_band = sum(1 for s in sch if s["im_band"])
    tage = [vorlauf_tage(s["gemacht"], kopf) for s in sch]
    reihen = "".join(
        f'<tr><td class="l">{gemacht_text(s["gemacht"])}</td><td>{utc(s["median"])}</td>'
        f'<td class="o">{block_kam(s["differenz_s"])}</td>'
        f'<td class="b">{"inside" if s["im_band"] else "outside"}</td></tr>' for s in sch)
    fenster = sorted({s["fenster_tage"] for s in sch})
    if fenster == [14]:
        fuss2 = "forecasts from the block pace of the 14 days before each date. method PH-M-006."
    else:
        abweich = [s for s in sch if s["fenster_tage"] != 14]
        fuss2 = ("forecasts from the block pace of the 14 days before each date, the "
                 + " and ".join(f'{gemacht_text(s["gemacht"])} one from {s["fenster_tage"]} days' for s in abweich)
                 + ". method PH-M-006.")
    css = f"""
.zahl {{ color:{F["tuerkis"]}; }}
.fn {{ font-feature-settings:normal; }}
table {{ width:100%; border-collapse:collapse; margin-top:32px; font-feature-settings:'tnum' 1; table-layout:fixed; }}
col.c1 {{ width:226px; }} col.c2 {{ width:206px; }} col.c4 {{ width:150px; }}
th {{ font-size:{T["klein"][0]}px; font-weight:400; color:{F["neben"]}; text-align:left; padding:0 0 16px; white-space:nowrap; }}
td {{ font-size:32px; font-weight:400; color:{F["text"]}; padding:12px 0;
      border-top:{S.LINIE_PX}px solid {F["linie"]}; white-space:nowrap; }}
td.l {{ color:{F["neben"]}; }}
td.o {{ font-weight:{T["label"][1]}; }}
td.b, th.b {{ text-align:right; }}
td.b {{ color:{F["neben"]}; }}
"""
    inhalt = f"""
<div class="klein kicker">zcash nu7 upgrade, 6 nov 2026</div>
<div class="klein" style="margin-top:14px; color:{F["text"]}">nu7 starts at a block height, not a set time.</div>
<div class="klein" style="color:{F["text"]}">we forecast the time, and published every forecast in advance.</div>
<div class="zahl" data-rolle="gezaehlt" style="margin-top:24px">{im_band} of {len(sch)}</div>
<div class="unter" style="margin-top:22px">forecasts landed inside their 90% band</div>
<div class="klein fn" style="margin-top:8px">published {max(tage)} to {min(tage)} days ahead, scored against the counted block</div>
<table><colgroup><col class="c1"><col class="c2"><col class="c3"><col class="c4"></colgroup><tr><th>forecast made</th><th>we said (utc)</th><th>the block came</th><th class="b">90% band</th></tr>{reihen}</table>
<div class="klein fn" style="margin-top:32px">block {HOEHE:,} at {utc(kopf)} utc, header time counted on our own header client.</div>
<div class="klein fn" style="margin-top:6px">{H.escape(fuss2)}</div>
<div class="klein fn" style="margin-top:6px">every forecast, hits and misses, on pulsehawk.io/track-record</div>
"""
    return S.seite(inhalt, B, BH, skala, extra_css=css)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stand", nargs="+", required=True)
    ap.add_argument("--wache-2nov")
    ap.add_argument("--fenster-2nov", type=int, default=7)
    ap.add_argument("--koepfe", required=True)
    ap.add_argument("--aus", required=True)
    a = ap.parse_args()
    os.makedirs(a.aus, exist_ok=True)
    kopf = kopfzeit(a.koepfe)
    sch = rechnen(schaetzungen(a.stand, a.wache_2nov, a.fenster_2nov), kopf)
    png = os.path.join(a.aus, "nu7-1080x1350.png")
    q = S.rendern(html(sch, kopf), png, B, BH)
    S.vorschau(png, os.path.join(a.aus, "nu7-390.png"))
    rechnung = {"kopfzeit_utc": utc(kopf, True), "kopfzeit_unix": kopf,
                "schaetzungen": [{"gemacht": s["gemacht"], "quelle": s["quelle"], "median_utc": utc(s["median"], True),
                                  "differenz_s": s["differenz_s"], "the_block_came": block_kam(s["differenz_s"]),
                                  "band_utc": [utc(s["band"][0], True), utc(s["band"][1], True)],
                                  "im_band": s["im_band"], "fenster_tage": s["fenster_tage"]} for s in sch]}
    json.dump(rechnung, open(os.path.join(a.aus, "rechnung.json"), "w"), indent=1)
    klagen = S.pruefen_daten(S.messen(q, B, BH), B, BH)
    print(json.dumps(rechnung, indent=1))
    print("\n".join("FEHLER  " + k for k in klagen) or "ok      stil-pruefung bestanden")
    return 1 if klagen else 0


if __name__ == "__main__":
    sys.exit(main())
