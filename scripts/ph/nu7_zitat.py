#!/usr/bin/env python3
"""nu7_zitat.py - Karte "expected against counted" zur Zcash-NU7-Aktivierung (Ben, 06.11.2026).

1080 x 1350 im PulseHawk-Stil der DAY-N-Karte: dunkel, Falke oben und unten,
"Data from PulseHawk", pulsehawk.io. Alle Zahlen aus
berichte/2026-11-06-zcash-nu7-mainnet.md (Schaetzung 4.11., Kopfzeit des
Blocks 3.543.405). Gebaut mit Chromium ueber Playwright, dazu die
390-px-Vorschau aus derselben Vorlage.

    python3 nu7_zitat.py --logo hawk.png --aus ordner
"""
import argparse
import base64
import os

B, H = 1080, 1350
SCHRIFT = {"zahl": 220, "label": 58, "bezug": 48, "marke": 80, "fuss": 34, "alt": 32}

# Zeiten in Minuten ab 00:30 utc am 6.11.2026
def m(hh, mm, ss=0):
    return (hh * 60 + mm + ss / 60.0) - 30

BAND = (m(1, 14, 45), m(4, 7, 28))       # 90-%-Band, computed 4.11.
MEDIAN = m(2, 40, 58)                     # Median, computed 4.11.
GEZAEHLT = m(2, 34, 2)                    # Kopfzeit Block 3.543.405, counted
FRUEHER = [("23 oct", "+12.2 min", m(2, 21, 52), "links"),
           ("28 oct", "+7.8 min", m(2, 26, 16), "links"),
           ("2 nov", "5.8 min early", m(2, 39, 52), "rechts")]
W = 936                                   # Breite der Zeitachse in px
PX = W / 240.0                            # 00:30 bis 04:30


def x(t):
    return round(t * PX, 1)


def svg():
    F = SCHRIFT
    ach = 330
    t = []
    a = t.append
    a(f'<svg width="{W}" height="440" viewBox="0 0 {W} 440" xmlns="http://www.w3.org/2000/svg">')
    # 90-%-Band
    a(f'<rect x="{x(BAND[0])}" y="110" width="{x(BAND[1]) - x(BAND[0])}" height="{ach - 110}" '
      f'fill="#F2B84B" fill-opacity="0.15"/>')
    a(f'<text class="t-fuss band" x="{x(BAND[0]) + 14}" y="{ach - 14}" font-size="{F["fuss"]}" '
      f'fill="#F2B84B" fill-opacity="0.85">90% band</text>')
    # fruehere Staende, klein und blass
    a(f'<text class="t-fuss alt" x="{x(BAND[0]) + 14}" y="152" font-size="{F["alt"]}" fill="#6F7B80">earlier estimates</text>')
    for i, (datum, abw, tm, seite) in enumerate(FRUEHER):
        y = 198 + i * 44
        a(f'<circle cx="{x(tm)}" cy="{y - 11}" r="9" fill="#6F7B80"/>')
        if seite == "links":
            a(f'<text class="t-fuss alt" x="{x(tm) - 15}" y="{y}" text-anchor="end" letter-spacing="-0.6" font-size="{F["alt"]}" '
              f'fill="#6F7B80">{datum} {abw}</text>')
        else:
            a(f'<text class="t-fuss alt" x="{x(tm) + 15}" y="{y}" font-size="{F["alt"]}" '
              f'fill="#6F7B80">{datum} {abw}</text>')
    # Median 4.11.
    a(f'<line x1="{x(MEDIAN)}" y1="100" x2="{x(MEDIAN)}" y2="{ach}" stroke="#F2B84B" stroke-width="5" '
      f'stroke-dasharray="14 9"/>')
    a(f'<text class="t-bezug" x="{x(MEDIAN) + 14}" y="46" font-size="{F["bezug"]}" fill="#F2B84B" '
      f'font-weight="700">computed 4 nov</text>')
    a(f'<text class="t-fuss" x="{x(MEDIAN) + 14}" y="90" font-size="{F["fuss"]}" fill="#C9A35A">median 02:40:58</text>')
    # gezaehlte Kopfzeit
    a(f'<line x1="{x(GEZAEHLT)}" y1="100" x2="{x(GEZAEHLT)}" y2="{ach}" stroke="#49EACB" stroke-width="9"/>')
    a(f'<circle cx="{x(GEZAEHLT)}" cy="{ach}" r="17" fill="#49EACB" stroke="#080B0F" stroke-width="5"/>')
    a(f'<text class="t-bezug" x="{x(GEZAEHLT) - 16}" y="46" text-anchor="end" font-size="{F["bezug"]}" '
      f'fill="#49EACB" font-weight="800">counted</text>')
    a(f'<text class="t-fuss" x="{x(GEZAEHLT) - 16}" y="90" text-anchor="end" font-size="{F["fuss"]}" '
      f'fill="#A9EBDD">02:34:02</text>')
    # Achse
    a(f'<line x1="0" y1="{ach}" x2="{W}" y2="{ach}" stroke="#3A434C" stroke-width="3"/>')
    for i, lab in enumerate(["00:30", "01:30", "02:30", "03:30", "04:30"]):
        xx = i * 60 * PX
        anker = "start" if i == 0 else ("end" if i == 4 else "middle")
        a(f'<line x1="{xx:.1f}" y1="{ach}" x2="{xx:.1f}" y2="{ach + 14}" stroke="#3A434C" stroke-width="3"/>')
        a(f'<text class="t-fuss" x="{xx:.1f}" y="{ach + 52}" text-anchor="{anker}" font-size="{F["fuss"]}" '
          f'fill="#9BA3AB">{lab}</text>')
    a(f'<text class="t-fuss" x="0" y="{ach + 100}" font-size="{F["fuss"]}" fill="#9BA3AB">'
      f'6 nov 2026, utc, zcash nu7 at block 3,543,405</text>')
    a('</svg>')
    return "\n".join(t)


def html(logo, skala=1.0):
    L = "data:image/png;base64," + base64.b64encode(open(logo, "rb").read()).decode()
    F = SCHRIFT
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html,body {{ width:{round(B * skala)}px; height:{round(H * skala)}px; background:#080B0F; overflow:hidden; }}
  .karte {{ width:{B}px; height:{H}px; background:#080B0F; transform:scale({skala:.8f}); transform-origin:0 0;
           font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; color:#fff;
           background-image:radial-gradient(ellipse 120% 55% at 50% -8%, rgba(73,234,203,0.13), transparent 60%);
           display:flex; flex-direction:column; }}
  .marke {{ display:flex; align-items:center; gap:26px; padding:44px 72px 0; }}
  .marke img {{ width:92px; }}
  .marke b {{ font-size:{F["marke"]}px; letter-spacing:12px; font-weight:800; }}
  .marke b span {{ color:#49EACB; }}
  .kopf {{ padding:40px 72px 0; }}
  .label {{ font-size:{F["label"]}px; color:#9BA3AB; font-weight:700; }}
  .zahl {{ font-size:{F["zahl"]}px; line-height:1.0; font-weight:800; letter-spacing:-7px; color:#FFFFFF; margin:10px 0 8px; }}
  .unter {{ font-size:{F["label"]}px; font-weight:700; color:#FFFFFF; }}
  .grafik {{ padding:84px 72px 0; }}
  .grafik svg {{ display:block; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; }}
  .notiz {{ padding:34px 72px 0; font-size:{F["alt"]}px; line-height:1.3; color:#9BA3AB; }}
  .fuss {{ margin:auto 72px 0; display:flex; align-items:center; justify-content:space-between;
           padding:26px 0 38px; border-top:1px solid #2A313A; }}
  .fuss .l {{ display:flex; align-items:center; gap:16px; }}
  .fuss img {{ width:54px; }}
  .fuss span {{ font-size:{F["fuss"]}px; color:#9BA3AB; letter-spacing:1px; white-space:nowrap; }}
  .fuss .adr {{ color:#49EACB; font-weight:800; letter-spacing:2px; }}
</style></head><body><div class="karte">
  <div class="marke"><img src="{L}" alt=""><b>PULSE<span>HAWK</span></b></div>
  <div class="kopf">
    <div class="label">expected against counted</div>
    <div class="zahl">6.9 min</div>
    <div class="unter">early, inside the 90% band</div>
  </div>
  <div class="grafik">{svg()}</div>
  <div class="notiz">header time counted on our own header client. band computed from the block pace of the 14 days before 4 nov.</div>
  <div class="fuss"><div class="l"><img src="{L}" alt=""><span>Data from PulseHawk</span></div><span class="adr">pulsehawk.io</span></div>
</div></body></html>"""


def rendern(seite, ziel, breite, hoehe):
    """Chromium ueber Playwright (Node), Fenster genau so gross wie das Bild."""
    import json
    import subprocess
    q = ziel[:-4] + ".html"
    open(q, "w").write(seite)
    js = """const {chromium} = require('playwright');
(async () => { const [q, z, w, h] = JSON.parse(process.argv[1]);
  const b = await chromium.launch(); const p = await b.newPage({viewport: {width: w, height: h}, deviceScaleFactor: 1});
  await p.goto('file://' + q, {waitUntil: 'load'}); await p.waitForTimeout(300);
  await p.screenshot({path: z}); await b.close(); })();"""
    subprocess.run(["node", "-e", js, json.dumps([os.path.abspath(q), os.path.abspath(ziel), breite, hoehe])],
                   check=True)
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logo", required=True)
    ap.add_argument("--aus", required=True)
    a = ap.parse_args()
    os.makedirs(a.aus, exist_ok=True)
    k = os.path.join(a.aus, "pulsehawk-nu7-expected-counted-1080x1350.png")
    v = os.path.join(a.aus, "pulsehawk-nu7-expected-counted-390.png")
    rendern(html(a.logo), k, B, H)
    rendern(html(a.logo, 390 / B), v, 390, round(H * 390 / B))
    print(k)
    print(v)


if __name__ == "__main__":
    main()
