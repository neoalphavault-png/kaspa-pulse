#!/usr/bin/env python3
"""nu7_karte.py - NU7-Karte "4 of 4 forecasts" (Ben, 08.11.2026, Nachtrag 2: "forecast" statt "estimate").

Fassung vom 09.11. vormittags (Ben, Aufraeumrunde): eine Botschaft, viel Luft.
Nur Kicker, "4 of 4", eine Unterzeile, je Prognose Datum und "the block came"
mit dem Streifen in voller Breite darunter, eine Achsenzeile, eine Fussnote.
Der Streifen steht unter der Zeile statt in einer dritten Spalte, weil die
drei Achsenwoerter bei 30 px auf einer Hoehe etwa 540 px Streifen brauchen.

Fassung vom 09.11. (Ben, letzte Runde vor dem Post): Spalte "90% band" ersetzt
durch einen Streifen je Zeile ("forecast and block"), alle mit demselben
Massstab 15 min vor bis 15 min nach unserer Prognose. Strich in der Mitte ist
die Prognose, der tuerkise Punkt der Block, rechts heisst spaeter. Hintergrund
blass tuerkis im 90%-Band, Pfeile an den Enden, wenn das Band weitergeht,
Bandkanten im Fenster an der genauen Stelle. Bandbreiten im Fuss, Fussnote *
mit pulsehawk.io/method.

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
STREIFEN_PX = 40
PUNKT_STREIFEN_PX = 30
TABELLE_PX = 40
SPALTE_DATUM_PX = 260
ABSTAND_BLOCK_PX = 22
BAND_DECKKRAFT = 0.10  # blass tuerkis, ph_stil laesst bis 0.10 zu (Ben 09.11.)


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


FENSTER_S = 900  # Streifen 15 min vor bis 15 min nach der Prognose (Ben 09.11.)


def stunden_min(sekunden):
    """Bandbreite gerundet auf ganze Minuten, '8 h 38 min'."""
    m = int(round(sekunden / 60))
    h, m = divmod(m, 60)
    return f"{h} h {m} min" if h else f"{m} min"


def pct(rel):
    return 50 + 50 * max(-FENSTER_S, min(FENSTER_S, rel)) / FENSTER_S


def streifen(s, kopf):
    """Ein Streifen je Prognose, Prognose als Strich in der Mitte, Block als tuerkiser Punkt.
    Rechts heisst, der Block kam spaeter. Bandgrenzen aus der Rechnung, nicht geschaetzt.
    Fassung vom 09.11. (ruhig): keine Pfeile an den Enden."""
    lo, hi = s["band"][0] - s["median"], s["band"][1] - s["median"]
    blk = kopf - s["median"]
    if abs(blk) > FENSTER_S:
        raise SystemExit(f'block ausserhalb des streifens fuer {s["gemacht"]}')
    teile = []
    if lo < FENSTER_S and hi > -FENSTER_S:
        teile.append(f'<div class="band" style="left:{pct(lo):.3f}%; right:{100 - pct(hi):.3f}%"></div>')
    for rel in (lo, hi):
        if -FENSTER_S < rel < FENSTER_S:
            teile.append(f'<div class="kante" style="left:{pct(rel):.3f}%"></div>')
    teile.append('<div class="mitte"></div>')
    teile.append(f'<div class="punkt" data-rolle="gezaehlt" style="left:{pct(blk):.3f}%"></div>')
    return '<div class="streifen">' + "".join(teile) + "</div>"


def html(sch, kopf, skala=1.0):
    F, T = S.FARBE, S.SCHRIFT
    im_band = sum(1 for s in sch if s["im_band"])
    tage = [vorlauf_tage(s["gemacht"], kopf) for s in sch]
    breiten = [s["band"][1] - s["band"][0] for s in sch]
    zeilen = "".join(
        f'<div class="zeile"><span class="d">{gemacht_text(s["gemacht"])}</span>'
        f'<span class="o">{block_kam(s["differenz_s"])}</span></div>{streifen(s, kopf)}' for s in sch)
    fuss = (f"* 90% bands were {stunden_min(min(breiten))} to {stunden_min(max(breiten))} wide. "
            "method and every result at pulsehawk.io/track-record")
    tk = F["tuerkis"].lstrip("#")
    blass = f"rgba({int(tk[0:2], 16)}, {int(tk[2:4], 16)}, {int(tk[4:6], 16)}, {BAND_DECKKRAFT})"
    css = f"""
.zahl {{ color:{F["tuerkis"]}; }}
.fn {{ font-feature-settings:normal; line-height:1.3; flex-shrink:0; }}
.kopf, .zeile {{ display:flex; flex-shrink:0; }}
.kopf span {{ font-size:{T["klein"][0]}px; color:{F["neben"]}; }}
.d {{ width:{SPALTE_DATUM_PX}px; flex-shrink:0; }}
.zeile {{ margin-top:{ABSTAND_BLOCK_PX}px; font-size:{TABELLE_PX}px; font-feature-settings:'tnum' 1; line-height:1.2; }}
.zeile .d {{ color:{F["neben"]}; }}
.zeile .o {{ color:{F["text"]}; font-weight:{T["label"][1]}; }}
.streifen {{ position:relative; height:{STREIFEN_PX}px; margin-top:10px; flex-shrink:0; }}
.band {{ position:absolute; top:0; bottom:0; background:{blass}; }}
.mitte {{ position:absolute; left:50%; top:-6px; bottom:-6px; width:2px; margin-left:-1px; background:{F["text"]}; }}
.kante {{ position:absolute; top:0; bottom:0; width:2px; margin-left:-1px; background:{F["neben"]}; }}
.punkt {{ position:absolute; top:50%; width:{PUNKT_STREIFEN_PX}px; height:{PUNKT_STREIFEN_PX}px;
          margin:-{PUNKT_STREIFEN_PX // 2}px 0 0 -{PUNKT_STREIFEN_PX // 2}px; border-radius:50%; background:{F["tuerkis"]}; }}
.achse {{ display:flex; justify-content:space-between; margin-top:14px; flex-shrink:0;
          font-size:{T["klein"][0]}px; color:{F["neben"]}; }}
"""
    inhalt = f"""
<div class="klein kicker">zcash nu7 upgrade, 6 nov 2026</div>
<div class="zahl" data-rolle="gezaehlt" style="margin-top:40px">{im_band} of {len(sch)}</div>
<div class="unter" style="margin-top:20px">forecasts landed inside their 90% band*, published {max(tage)} to {min(tage)} days ahead</div>
<div class="kopf" style="margin-top:44px"><span class="d">forecast made</span><span>the block came</span></div>
{zeilen}
<div class="achse"><span>15 min earlier</span><span>our forecast</span><span>15 min later</span></div>
<div class="klein fn" style="margin-top:30px">{H.escape(fuss)}</div>
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
                                  "band_utc": [utc(s["band"][0], True), utc(s["band"][1], True)], "bandbreite_s": int(s["band"][1] - s["band"][0]),
                                  "block_minus_prognose_s": int(kopf - s["median"]),
                                  "im_band": s["im_band"], "fenster_tage": s["fenster_tage"]} for s in sch]}
    json.dump(rechnung, open(os.path.join(a.aus, "rechnung.json"), "w"), indent=1)
    klagen = S.pruefen_daten(S.messen(q, B, BH), B, BH)
    print(json.dumps(rechnung, indent=1))
    print("\n".join("FEHLER  " + k for k in klagen) or "ok      stil-pruefung bestanden")
    return 1 if klagen else 0


if __name__ == "__main__":
    sys.exit(main())
