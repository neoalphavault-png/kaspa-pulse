#!/usr/bin/env python3
"""nu7_karte.py - NU7-Karte "expected against counted" im neuen PulseHawk-Stil (Ben, 06.11.2026).

Muster fuer ph_stil.py: dieselben Zahlen wie die Karte vom 6.11.
(berichte/2026-11-06-zcash-nu7-mainnet.md), jetzt filigran: Inter, grosse
Zahl light 160 px, Raender 96 px, Tuerkis nur fuer die gezaehlte Linie,
Band als Flaeche mit 6 % ohne Kasten, Falke tuerkis oben mittig.

    python3 scripts/ph/nu7_karte.py --aus <ordner>
    -> nu7-neu-1080x1350.png, nu7-neu-390.png, nu7-neu-1080x1350.html
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ph_stil as S  # noqa: E402

B, H = S.FORMAT["hoch"]
W = B - 2 * S.RAND                       # 888 px Zeichenbreite


def m(hh, mm, ss=0):
    """Minuten ab 00:30 utc am 6.11.2026."""
    return hh * 60 + mm + ss / 60.0 - 30


BAND = (m(1, 14, 45), m(4, 7, 28))       # 90-%-Band, computed 4.11.
MEDIAN = m(2, 40, 58)                     # Median, computed 4.11.
GEZAEHLT = m(2, 34, 2)                    # Kopfzeit Block 3.543.405, counted
FRUEHER = [("23 oct", "+12.2 min", m(2, 21, 52), "links"),
           ("28 oct", "+7.8 min", m(2, 26, 16), "links"),
           ("2 nov", "5.8 min early", m(2, 39, 52), "rechts")]
PX = W / 240.0                            # 00:30 bis 04:30


def x(t):
    return round(t * PX, 1)


def svg():
    F, T = S.FARBE, S.SCHRIFT
    lw = S.DIAGRAMM_LINIE_PX
    r = S.PUNKT_PX / 2
    ach = 300
    a = []
    a.append(f'<svg width="{W}" height="400" viewBox="0 0 {W} 400" xmlns="http://www.w3.org/2000/svg">')
    # Band, Flaeche ohne Kasten
    a.append(f'<rect x="{x(BAND[0])}" y="96" width="{x(BAND[1]) - x(BAND[0])}" height="{ach - 96}" '
             f'fill="{F["text"]}" fill-opacity="{S.BAND_DECKKRAFT}" stroke="none"/>')
    a.append(f'<text x="{x(BAND[1]) - 14}" y="138" text-anchor="end" font-size="{T["klein"][0]}" '
             f'font-weight="{T["klein"][1]}" fill="{F["neben"]}">90% band</text>')
    # fruehere Staende, klein und blass
    a.append(f'<text x="{x(BAND[0]) + 14}" y="138" font-size="{T["klein"][0]}" font-weight="400" '
             f'fill="{F["neben"]}" fill-opacity="0.7">earlier estimates</text>')
    for i, (datum, abw, tm, seite) in enumerate(FRUEHER):
        y = 182 + i * 40
        a.append(f'<circle cx="{x(tm)}" cy="{y - 10}" r="{r}" fill="{F["neben"]}" fill-opacity="0.7"/>')
        if seite == "links":
            a.append(f'<text x="{x(tm) - 14}" y="{y}" text-anchor="end" font-size="{T["klein"][0]}" '
                     f'font-weight="400" fill="{F["neben"]}" fill-opacity="0.7">{datum} {abw}</text>')
        else:
            a.append(f'<text x="{x(tm) + 14}" y="{y}" font-size="{T["klein"][0]}" '
                     f'font-weight="400" fill="{F["neben"]}" fill-opacity="0.7">{datum} {abw}</text>')
    # Median 4.11., gestrichelt, Nebentext
    a.append(f'<line x1="{x(MEDIAN)}" y1="84" x2="{x(MEDIAN)}" y2="{ach}" stroke="{F["neben"]}" '
             f'stroke-width="{lw}" stroke-dasharray="6 6"/>')
    a.append(f'<text x="{x(MEDIAN) + 16}" y="36" font-size="{T["label_leise"][0]}" '
             f'font-weight="{T["label_leise"][1]}" fill="{F["neben"]}">computed 4 nov</text>')
    a.append(f'<text x="{x(MEDIAN) + 16}" y="74" font-size="{T["klein"][0]}" font-weight="400" '
             f'fill="{F["neben"]}">median 02:40:58</text>')
    # gezaehlte Kopfzeit, das eine tuerkise Element
    a.append(f'<g data-rolle="gezaehlt">'
             f'<line x1="{x(GEZAEHLT)}" y1="84" x2="{x(GEZAEHLT)}" y2="{ach}" stroke="{F["tuerkis"]}" stroke-width="{lw}"/>'
             f'<circle cx="{x(GEZAEHLT)}" cy="{ach}" r="{r}" fill="{F["tuerkis"]}"/>'
             f'<text x="{x(GEZAEHLT) - 16}" y="36" text-anchor="end" font-size="{T["label"][0]}" '
             f'font-weight="{T["label"][1]}" fill="{F["tuerkis"]}">counted</text></g>')
    a.append(f'<text x="{x(GEZAEHLT) - 16}" y="74" text-anchor="end" font-size="{T["klein"][0]}" '
             f'font-weight="400" fill="{F["text"]}">02:34:02</text>')
    # Achse 1 px
    a.append(f'<line x1="0" y1="{ach}" x2="{W}" y2="{ach}" stroke="{F["linie"]}" stroke-width="{S.LINIE_PX}"/>')
    for i, lab in enumerate(["00:30", "01:30", "02:30", "03:30", "04:30"]):
        xx = i * 60 * PX
        anker = "start" if i == 0 else ("end" if i == 4 else "middle")
        a.append(f'<line x1="{xx:.1f}" y1="{ach}" x2="{xx:.1f}" y2="{ach + 10}" stroke="{F["linie"]}" '
                 f'stroke-width="{S.LINIE_PX}"/>')
        a.append(f'<text x="{xx:.1f}" y="{ach + 50}" text-anchor="{anker}" font-size="{T["klein"][0]}" '
                 f'font-weight="400" fill="{F["neben"]}">{lab}</text>')
    a.append(f'<text x="0" y="{ach + 96}" font-size="{T["klein"][0]}" font-weight="400" fill="{F["neben"]}">'
             f'6 nov 2026, utc, block 3,543,405</text>')
    a.append('</svg>')
    return "\n".join(a)


def html(skala=1.0):
    inhalt = f"""
<div class="klein" style="margin-top:48px">zcash nu7 activation</div>
<div class="titel" style="margin-top:10px">expected against counted</div>
<div class="zahl" style="margin-top:44px">6.9 min</div>
<div class="unter" style="margin-top:14px">early, inside the 90% band</div>
<div style="margin-top:72px">{svg()}</div>
<div class="klein" style="margin-top:40px">header time counted on our own header client. band computed from the block pace of the 14 days before 4 nov.</div>
"""
    return S.seite(inhalt, B, H, skala)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aus", required=True)
    a = ap.parse_args()
    os.makedirs(a.aus, exist_ok=True)
    png = os.path.join(a.aus, "nu7-neu-1080x1350.png")
    q = S.rendern(html(), png, B, H)
    S.vorschau(png, os.path.join(a.aus, "nu7-neu-390.png"))
    klagen = S.pruefen_daten(S.messen(q, B, H), B, H)
    print(png)
    print("\n".join("FEHLER  " + k for k in klagen) or "ok      stil-pruefung bestanden")
    return 1 if klagen else 0


if __name__ == "__main__":
    sys.exit(main())
