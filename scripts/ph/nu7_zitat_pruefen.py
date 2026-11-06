"""Pruefung der NU7-Karte mit den Funktionen aus grafik_check.py (pulsehawk-site und kaspa-pulse)."""
import importlib.util, json, os, subprocess, sys
sys.path.insert(0, os.environ.get("PH_SITE_SCRIPTS", "../pulsehawk-site/scripts"))
import grafik_check as PH                      # pulsehawk-site
spec = importlib.util.spec_from_file_location("kp", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "grafik_check.py"))
KP = importlib.util.module_from_spec(spec); spec.loader.exec_module(KP)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nu7_zitat as N

png, vor, htm = sys.argv[1:4]
klagen = []
m = PH.png_kopf(png)
if m != (1080, 1350): klagen.append("format %s" % (m,))
g = os.path.getsize(png)
if not PH.MIN_BYTES <= g <= PH.MAX_BYTES: klagen.append("dateigroesse %d" % g)
kopf, fuss, gesamt = PH.bild_baender(png); gb, gg = PH.grenzen(png)
if kopf < gb: klagen.append("logo oben fehlt im bild (%d)" % kopf)
if fuss < gb: klagen.append("logo unten fehlt im bild (%d)" % fuss)
if gesamt < gg: klagen.append("karte leer")
seite = open(htm).read()
if seite.count("data:image/png;base64,") < 2: klagen.append("logo nicht oben und unten")
for t in ("Data from PulseHawk", "pulsehawk.io"):
    if t not in seite: klagen.append("pflichttext %r fehlt" % t)
for t in ("kaspa pulse", "kaspapulse"):
    if t in seite.lower(): klagen.append("kaspa-pulse-marke im bild")
rollen = {k: v for k, v in N.SCHRIFT.items() if k != "alt"}
rollen_alt = {"fuss": N.SCHRIFT["alt"]}
klagen += PH.norm_funde(rollen) + PH.norm_funde(rollen_alt)
klagen += PH.farb_funde(seite)
# gerenderte Schriften, Ueberlauf, sichtbarer Text
js = """const {chromium} = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage({viewport:{width:1080,height:1350}});
 await p.goto('file://' + process.argv[1]); await p.waitForTimeout(200);
 const r = await p.evaluate(() => { const o=[]; const rand=[];
  document.querySelectorAll('body *').forEach(e => { if (e.children.length) return; const t=(e.textContent||'').trim(); if(!t) return;
    const rg=document.createRange(); rg.selectNodeContents(e); const q=rg.getBoundingClientRect(); o.push({txt:t.slice(0,40), px:parseFloat(getComputedStyle(e).fontSize)});
    if (q.left < 60 || q.right > 1020 || q.bottom > 1350) rand.push(t.slice(0,30)+' '+Math.round(q.left)+'..'+Math.round(q.right)); });
  return {texte:o, rand:rand, hoehe:document.body.scrollHeight, sicht:document.body.innerText}; });
 console.log(JSON.stringify(r)); await b.close(); })();"""
d = json.loads(subprocess.run(["node", "-e", js, os.path.abspath(htm)], capture_output=True, text=True, check=True).stdout)
for e in d["texte"]:
    if e["px"] < 32: klagen.append("%s px %r" % (e["px"], e["txt"]))
    elif e["px"] < PH.UNTERGRENZE and e["px"] not in (32, 34): klagen.append("%s px %r" % (e["px"], e["txt"]))
klagen += ["am rand oder ausserhalb: " + r for r in d["rand"]]
if d["hoehe"] > 1351: klagen.append("ueberlauf %d" % d["hoehe"])
klagen += KP.zeichen_pruefen(d["sicht"])
for w in ("now", "live"):
    if (" %s " % w) in (" " + d["sicht"].lower().replace("\n", " ") + " "): klagen.append("wort %r" % w)
v = PH.png_kopf(vor)
if not v or v[0] != PH.VORSCHAU_BREITE: klagen.append("vorschau %s" % (v,))
print("karte     %s %s, %d bytes" % (png, m, g))
print("vorschau  %s %s  ANSEHEN" % (vor, v))
print("baender   kopf %d, fuss %d, gesamt %d (mindestens %d, %d)" % (kopf, fuss, gesamt, gb, gg))
print("schriften %s" % sorted({e["px"] for e in d["texte"]}))
print("\n".join("FEHLER    " + k for k in klagen) or "ok        alle pruefungen bestanden")
sys.exit(1 if klagen else 0)
