#!/usr/bin/env python3
"""ph_stil.py - gemeinsamer Stil fuer alle PulseHawk-Grafiken (Ben, 06.11.2026).

Ben: "zu fett, filigraner und dezenter, apple style". Alle Vorlagen
(ph_entwurf bch und zcash, nu7_zitat, report-karten) nehmen ihre Werte von
hier, damit eine Aenderung an einer Stelle reicht. Umgestellt werden die
Vorlagen erst nach Bens Freigabe des Musters.

Vorgaben
  1. Schrift Inter (OFL, assets/fonts/inter). Grosse Zahl light 300,
     Ueberschriften regular 400, Labels 400 oder 500, nichts ueber 500.
     Grosse Zahl hoechstens 160 px bei 1080 Breite.
  2. Raender mindestens 96 px, viel Luft, ein Thema je Grafik.
  3. Grund #0B0D0F, Text #F5F5F7, Nebentext #86868B, Linien 1 px #2C2C2E.
     Tuerkis nur fuer ein Element (die gezaehlte Linie oder Zahl). Eine zweite
     Farbe nur wenn noetig und gedaempft.
  4. Diagramme: Linien 1,5 px, Band als Flaeche mit etwa 6 % Deckkraft ohne
     Kasten, Punkte 6 px, keine dicken Rahmen.
  5. Falke klein oben links (36 px), keine grosse Wortmarke. Fuss
     "Data from PulseHawk · pulsehawk.io" klein.
  6. Kleinschreibung, Textregeln und Zahlen aus dem Bericht bleiben.

Untergrenze fuer Schrift bleibt 30 px bei 1080 Breite: im Feed steht das
Bild bei etwa 390 px, aus 30 werden 11 px (grafik_check.py, 19.08.2026).

    python3 scripts/ph/ph_stil.py --selbsttest
"""
import base64
import json
import os
import subprocess
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HIER, "..", ".."))
SCHRIFTEN = os.path.join(REPO, "assets", "fonts", "inter")
FALKE = os.path.join(REPO, "assets", "ph", "falke-hell.png")

# ------------------------------------------------------------------ werte
FARBE = {
    "grund": "#0B0D0F",
    "text": "#F5F5F7",
    "neben": "#86868B",
    "linie": "#2C2C2E",
    "tuerkis": "#49EACB",     # nur fuer das eine gezaehlte Element
    "zweit": "#8C7E5E",       # gedaempft, nur wenn noetig
}
# Schriftgroessen in px bei 1080 Breite, mit Staerke
SCHRIFT = {
    "zahl":  (160, 300),      # die eine grosse Zahl, light
    "titel": (48, 400),       # Ueberschrift, regular
    "unter": (40, 400),       # Satz unter der Zahl
    "label": (34, 500),       # Beschriftung im Diagramm, die wichtige
    "label_leise": (34, 400),
    "klein": (30, 400),       # Achse, Datum, Fussnote
    "fuss":  (30, 400),       # Absender
}
ZAHL_MAX_PX = 160
GEWICHT_MAX = 500
SCHRIFT_MIN_PX = 30
RAND = 96                     # Mindestabstand zum Bildrand
LINIE_PX = 1                  # Achsen, Trennlinien
DIAGRAMM_LINIE_PX = 1.5       # Linien im Diagramm
BAND_DECKKRAFT = 0.06
PUNKT_PX = 6                  # Durchmesser
FALKE_PX = 36
FUSS = "Data from PulseHawk · pulsehawk.io"
FORMAT = {"hoch": (1080, 1350), "quer": (1600, 900)}


def b64(pfad):
    with open(pfad, "rb") as f:
        return base64.b64encode(f.read()).decode()


def schrift_css():
    """Inter 300, 400, 500 eingebettet, damit Runner und Laptop gleich rendern."""
    teile = []
    for w in (300, 400, 500):
        d = b64(os.path.join(SCHRIFTEN, f"inter-latin-{w}-normal.woff2"))
        teile.append("@font-face { font-family:'Inter'; font-style:normal; font-weight:%d; "
                     "src:url(data:font/woff2;base64,%s) format('woff2'); }" % (w, d))
    return "\n".join(teile)


def basis_css(breite, hoehe, skala=1.0):
    F, S = FARBE, SCHRIFT
    return f"""{schrift_css()}
* {{ margin:0; padding:0; box-sizing:border-box; }}
html,body {{ width:{round(breite * skala)}px; height:{round(hoehe * skala)}px; background:{F["grund"]}; overflow:hidden; }}
.karte {{ width:{breite}px; height:{hoehe}px; background:{F["grund"]}; color:{F["text"]};
         transform:scale({skala:.8f}); transform-origin:0 0; padding:{RAND}px;
         font-family:'Inter',sans-serif; font-weight:400; font-feature-settings:'tnum' 1, 'cv11' 1;
         -webkit-font-smoothing:antialiased; display:flex; flex-direction:column; }}
.falke {{ width:{FALKE_PX}px; height:{FALKE_PX}px; object-fit:contain; display:block; }}
.titel {{ font-size:{S["titel"][0]}px; font-weight:{S["titel"][1]}; letter-spacing:-0.5px; line-height:1.15; }}
.zahl {{ font-size:{S["zahl"][0]}px; font-weight:{S["zahl"][1]}; letter-spacing:-4px; line-height:1.0; color:{F["text"]}; }}
.unter {{ font-size:{S["unter"][0]}px; font-weight:{S["unter"][1]}; color:{F["neben"]}; line-height:1.25; }}
.klein {{ font-size:{S["klein"][0]}px; font-weight:{S["klein"][1]}; color:{F["neben"]}; line-height:1.35; }}
.fuss {{ margin-top:auto; font-size:{S["fuss"][0]}px; font-weight:{S["fuss"][1]}; color:{F["neben"]}; white-space:nowrap; }}
svg text {{ font-family:'Inter',sans-serif; font-feature-settings:'tnum' 1; }}
"""


def seite(inhalt, breite=1080, hoehe=1350, skala=1.0, extra_css=""):
    """Ganze Seite: Falke oben links, Inhalt, Fuss unten."""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
{basis_css(breite, hoehe, skala)}
{extra_css}
</style></head><body><div class="karte">
<img class="falke" src="data:image/png;base64,{b64(FALKE)}" alt="">
{inhalt}
<div class="fuss">{FUSS}</div>
</div></body></html>"""


# ------------------------------------------------------------------ rendern
JS_RENDERN = """const {chromium} = require('playwright');
(async () => { const [q, z, w, h] = JSON.parse(process.argv[1]);
  const b = await chromium.launch(); const p = await b.newPage({viewport: {width: w, height: h}, deviceScaleFactor: 1});
  await p.goto('file://' + q, {waitUntil: 'load'}); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(200);
  await p.screenshot({path: z}); await b.close(); })();"""


def rendern(html, ziel, breite, hoehe):
    """Chromium ueber Playwright (Node). Schreibt ziel.png und ziel.html."""
    q = os.path.splitext(ziel)[0] + ".html"
    with open(q, "w") as f:
        f.write(html)
    subprocess.run(["node", "-e", JS_RENDERN,
                    json.dumps([os.path.abspath(q), os.path.abspath(ziel), breite, hoehe])], check=True)
    return q


# ------------------------------------------------------------------ pruefen
JS_MESSEN = """const {chromium} = require('playwright');
(async () => { const [q, w, h] = JSON.parse(process.argv[1]);
 const b = await chromium.launch(); const p = await b.newPage({viewport:{width:w,height:h}});
 await p.goto('file://' + q); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(200);
 const r = await p.evaluate(() => { const o=[];
  document.querySelectorAll('.karte *').forEach(e => { if (e.children.length) return; const t=(e.textContent||'').trim(); if(!t) return;
    const s=getComputedStyle(e); const rg=document.createRange(); rg.selectNodeContents(e); const q=rg.getBoundingClientRect();
    o.push({txt:t.slice(0,40), px:parseFloat(s.fontSize), gewicht:parseInt(s.fontWeight), familie:s.fontFamily,
            farbe:s.color, fuellung:s.fill, rolle:(e.closest('[data-rolle]')||{dataset:{}}).dataset.rolle||'',
            l:q.left, r:q.right, o:q.top, u:q.bottom, zahl:e.classList.contains('zahl')}); });
  const tuerkis=[]; document.querySelectorAll('.karte *').forEach(e => { const s=getComputedStyle(e);
    const f=[s.color, s.fill, s.stroke, s.backgroundColor].join(' ');
    if (f.includes('73, 234, 203')) tuerkis.push((e.closest('[data-rolle]')||{dataset:{}}).dataset.rolle||e.tagName); });
  const formen=[]; document.querySelectorAll('svg line, svg rect, svg circle, svg path, svg polyline').forEach(e => {
    const s=getComputedStyle(e); formen.push({tag:e.tagName, strich:parseFloat(s.strokeWidth)||0, stroke:s.stroke,
      r:parseFloat(e.getAttribute('r')||0), fop:parseFloat(s.fillOpacity), fill:s.fill}); });
  return {texte:o, tuerkis:tuerkis, formen:formen, sicht:document.body.innerText,
          fonts:[...document.fonts].filter(f=>f.status==='loaded').map(f=>f.weight)}; });
 console.log(JSON.stringify(r)); await b.close(); })();"""


def messen(html_pfad, breite, hoehe):
    out = subprocess.run(["node", "-e", JS_MESSEN, json.dumps([os.path.abspath(html_pfad), breite, hoehe])],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def pruefen_daten(d, breite, hoehe):
    """Liste der Klagen gegen die Vorgaben, leer heisst bestanden."""
    k = []
    for e in d["texte"]:
        if e["gewicht"] > GEWICHT_MAX:
            k.append("staerke %d ueber %d, %r" % (e["gewicht"], GEWICHT_MAX, e["txt"]))
        if e["px"] < SCHRIFT_MIN_PX:
            k.append("%.0f px unter %d, %r" % (e["px"], SCHRIFT_MIN_PX, e["txt"]))
        if e["px"] > ZAHL_MAX_PX:
            k.append("%.0f px ueber %d, %r" % (e["px"], ZAHL_MAX_PX, e["txt"]))
        if e["zahl"] and e["gewicht"] != SCHRIFT["zahl"][1]:
            k.append("grosse zahl nicht light %d, %r" % (SCHRIFT["zahl"][1], e["txt"]))
        if "Inter" not in e["familie"]:
            k.append("schrift nicht inter, %r" % e["txt"])
        if e["l"] < RAND - 1 or e["r"] > breite - RAND + 1 or e["o"] < RAND - 1 or e["u"] > hoehe - RAND + 1:
            k.append("text im rand von %d px, %r (%d..%d, %d..%d)" % (RAND, e["txt"], e["l"], e["r"], e["o"], e["u"]))
    tx = d["texte"]
    for i in range(len(tx)):
        for j in range(i + 1, len(tx)):
            a, b = tx[i], tx[j]
            if a["l"] < b["r"] - 1 and b["l"] < a["r"] - 1 and a["o"] < b["u"] - 4 and b["o"] < a["u"] - 4:
                k.append("texte ueberlappen, %r und %r" % (a["txt"], b["txt"]))
    rollen = {r for r in d["tuerkis"]}
    if len(rollen) > 1 or (rollen and rollen != {"gezaehlt"}):
        k.append("tuerkis auf mehr als einem element: %s" % sorted(rollen))
    for f in d["formen"]:
        if f["tag"] in ("line", "path", "polyline") and f["strich"] > DIAGRAMM_LINIE_PX + 0.01:
            k.append("%s mit %.1f px strich, hoechstens %.1f" % (f["tag"], f["strich"], DIAGRAMM_LINIE_PX))
        if f["tag"] == "rect" and f["strich"] > 0 and f["stroke"] not in ("none", ""):
            k.append("rect mit rahmen, band ohne kasten")
        if f["tag"] == "rect" and f["fop"] > BAND_DECKKRAFT + 0.02:
            k.append("flaeche mit %.2f deckkraft, etwa %.2f" % (f["fop"], BAND_DECKKRAFT))
        if f["tag"] == "circle" and abs(2 * f["r"] - PUNKT_PX) > 0.01:
            k.append("punkt mit %.1f px, verlangt %d" % (2 * f["r"], PUNKT_PX))
    if sorted(set(d["fonts"])) != ["300", "400", "500"] and not set(d["fonts"]) <= {"300", "400", "500"}:
        k.append("schriften geladen %s" % d["fonts"])
    if FUSS not in d["sicht"]:
        k.append("fuss %r fehlt" % FUSS)
    if any(c.isupper() for c in d["sicht"].replace(FUSS, "")):
        k.append("grossbuchstaben ausserhalb des fusses")
    # Textregeln aus grafik_check.py (kaspa-pulse)
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import grafik_check as G  # noqa: E402
    k += G.zeichen_pruefen(d["sicht"].replace(FUSS, ""))
    for w in ("now", "live"):
        if (" %s " % w) in (" " + d["sicht"].lower().replace("\n", " ") + " "):
            k.append("wort %r" % w)
    for m in ("kaspa pulse", "kaspapulse"):
        if m in d["sicht"].lower():
            k.append("kaspa-pulse-marke im bild")
    return k


def vorschau(png, ziel, breite_feed=390):
    """Feed-Fassung bei 390 px. Ansehen, nicht messen."""
    from PIL import Image
    with Image.open(png) as im:
        h = round(im.height * breite_feed / im.width)
        im.resize((breite_feed, h), Image.LANCZOS).save(ziel)
    return ziel


# ------------------------------------------------------------------ selbsttest
def selbsttest():
    fehler = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            fehler.append(name)
    ok("schriften da", all(os.path.exists(os.path.join(SCHRIFTEN, f"inter-latin-{w}-normal.woff2"))
                           for w in (300, 400, 500)))
    ok("falke da", os.path.exists(FALKE))
    ok("nichts ueber 500", max(w for _, w in SCHRIFT.values()) <= GEWICHT_MAX)
    ok("zahl hoechstens 160 und light", SCHRIFT["zahl"] == (160, 300))
    ok("keine schrift unter 30", min(p for p, _ in SCHRIFT.values()) >= SCHRIFT_MIN_PX)
    gut = {"texte": [{"txt": "6.9 min", "px": 160, "gewicht": 300, "familie": "Inter", "zahl": True,
                      "l": 96, "r": 600, "o": 300, "u": 460}],
           "tuerkis": ["gezaehlt", "gezaehlt"], "formen": [{"tag": "line", "strich": 1.5, "stroke": "x", "r": 0,
                                                            "fop": 1, "fill": ""}],
           "sicht": "6.9 min\n" + FUSS, "fonts": ["300", "400", "500"]}
    ok("gute karte ohne klage", pruefen_daten(gut, 1080, 1350) == [])
    schlecht = json.loads(json.dumps(gut))
    schlecht["texte"][0].update(px=220, gewicht=800, l=40)
    schlecht["tuerkis"].append("band")
    schlecht["formen"] += [{"tag": "rect", "strich": 2, "stroke": "rgb(1,1,1)", "r": 0, "fop": 0.15, "fill": ""},
                           {"tag": "line", "strich": 9, "stroke": "x", "r": 0, "fop": 1, "fill": ""},
                           {"tag": "circle", "strich": 0, "stroke": "none", "r": 14, "fop": 1, "fill": ""}]
    schlecht["sicht"] = "Zcash NU7: now\n"
    k = pruefen_daten(schlecht, 1080, 1350)
    schlecht["texte"].append(dict(schlecht["texte"][0], txt="drueber", zahl=False, px=40, gewicht=400))
    k = pruefen_daten(schlecht, 1080, 1350)
    for teil in ("ueberlappen", "staerke", "ueber 160", "rand", "tuerkis", "rahmen", "deckkraft", "9.0 px", "punkt", "fuss",
                 "grossbuchstaben", "verbotenes zeichen", "'now'"):
        ok("schlechte karte faellt auf: %s" % teil, any(teil in x for x in k))
    print("")
    print("%d fehler" % len(fehler) if fehler else "alle testfaelle bestanden")
    return 1 if fehler else 0


if __name__ == "__main__":
    if "--selbsttest" in sys.argv:
        sys.exit(selbsttest())
    print(__doc__)
