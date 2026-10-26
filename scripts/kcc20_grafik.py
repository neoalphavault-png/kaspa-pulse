#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kaspa Pulse, Grafik zur KCC-20-Zaehlung, 1600x900 (Ben, 23.10.2026).

Liest nur die Summen der Zaehlung (kcc20-tokens.csv, kcc20-zaehlung.json),
nie eine Adresse. Rahmen wie die Tagesgrafik, nur quer: Kopfzeile oben
links, die eine Zahl (Tokens mit Haltern), daneben das Objekt (Halter-Outputs
je Token, Balken ab null), eine Bedeutungszeile, die Datumszeile mit
Messzeit und Herkunft, unten mittig die Wortmarke KASPA PULSE mit der
Pulslinie. Kein Falke, keine Verlaeufe, kein Glow. Farben und Schriften
aus look_takt (Look dunkel) und wortmarke.

Namen der Tokens kommen aus --namen (JSON covenant_id -> name). Ohne Namen
steht der Anfang der Covenant-ID da. Die Textregeln der Tagesgrafik
(pruefe_eine) laufen vor dem Rendern ueber jeden Text im Bild.

    python3 scripts/kcc20_grafik.py --tokens kcc20-tokens.csv --zaehlung kcc20-zaehlung.json \
        --stichzeit 2026-10-26T12:00:00Z --out kcc20-grafik.png
    python3 scripts/kcc20_grafik.py --selbsttest
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import look_takt  # noqa: E402
import wortmarke  # noqa: E402

W, H, RAND = 1600, 900, 64
LK = look_takt.LOOKS["dunkel"]
SELBST = "counted by kaspa pulse"
PULS = "M0,30 L60,30 L80,30 L92,10 L106,44 L118,4 L130,34 L140,30 L230,30"
BALKEN = 8


def tausend(n):
    return "{:,}".format(int(n))


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def datumszeile(stichzeit, quelle=SELBST):
    t = dt.datetime.fromisoformat(stichzeit.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    return "%d %s %d, %s utc · %s" % (t.day, t.strftime("%b").lower(), t.year, t.strftime("%H:%M"), quelle)


def lesen(tokens_pfad, zaehlung_pfad, namen=None):
    namen = namen or {}
    with open(tokens_pfad, encoding="utf-8") as fh:
        zeilen = [r for r in csv.DictReader(fh) if int(r.get("halter_outputs") or 0) > 0]
    with open(zaehlung_pfad, encoding="utf-8") as fh:
        z = json.load(fh)
    zeilen.sort(key=lambda r: (-int(r["halter_outputs"]), r["covenant_id"]))
    balken = [{"name": namen.get(r["covenant_id"]) or r["covenant_id"][:8],
               "wert": int(r["halter_outputs"])} for r in zeilen[:BALKEN]]
    return {"tokens": len(zeilen), "halter_outputs": sum(int(r["halter_outputs"]) for r in zeilen),
            "balken": balken, "rest": len(zeilen) - len(balken), "zaehlung": z}


def texte(d, stichzeit, transfers=None):
    bed = "%s holder outputs" % tausend(d["halter_outputs"])
    if transfers is not None:
        bed += ", %s transfers counted since 22 oct" % tausend(transfers)
    return {"kopf": "KCC-20 TOKENS ON KASPA",
            "einheit": "tokens with holders",
            "bedeutung": bed,
            "achse": "holder outputs per token",
            "rest": ("plus %d more tokens" % d["rest"]) if d["rest"] else "",
            "datumszeile": datumszeile(stichzeit)}


def pruefen(t, balken):
    """Regeln der Tagesgrafik ueber jeden Text. Leere Liste heisst gruen."""
    import tagesgrafik
    fehler = []
    for k, v in t.items():
        fehler += tagesgrafik.pruefe_eine(v, None, k)
    for b in balken:
        fehler += tagesgrafik.pruefe_eine(b["name"], None, "balken")
    her = t["datumszeile"].split(" · ")[-1]
    if not (her == SELBST or her.startswith("source ")):
        fehler.append("datumszeile endet weder auf counted by kaspa pulse noch auf source")
    return fehler


def objekt(balken, achse, rest, x, y, w, h):
    """Waagrechte Balken ab null, der groesste in Akzent, die anderen im Restton."""
    if not balken:
        return ""
    m = max(b["wert"] for b in balken) or 1
    zeile = min(64, (h - 50) / len(balken))
    namen_b, wert_b = 190, 110
    bw = w - namen_b - wert_b
    teile = ["<text x='%d' y='%d' font-size='26' fill='%s' font-family=\"IBM Plex Sans\">%s</text>"
             % (x, y + 4, LK["text2"], esc(achse))]
    for i, b in enumerate(balken):
        yy = y + 30 + i * zeile
        lang = max(2, bw * b["wert"] / m)
        farbe = LK["akzent"] if i == 0 else LK["rest"]
        teile.append("<text x='%d' y='%d' font-size='28' fill='%s' font-family=\"IBM Plex Mono\">%s</text>"
                     % (x, yy + zeile * 0.62, LK["text"], esc(b["name"])))
        teile.append("<rect x='%d' y='%d' width='%.1f' height='%.1f' fill='%s'/>"
                     % (x + namen_b, yy + zeile * 0.18, lang, zeile * 0.62, farbe))
        teile.append("<text x='%.1f' y='%d' font-size='28' fill='%s' font-family=\"IBM Plex Sans\" "
                     "font-weight='600'>%s</text>" % (x + namen_b + lang + 14, yy + zeile * 0.62, LK["text"],
                                                     tausend(b["wert"])))
    if rest:
        teile.append("<text x='%d' y='%d' font-size='26' fill='%s' font-family=\"IBM Plex Sans\">%s</text>"
                     % (x, y + 30 + len(balken) * zeile + 30, LK["text2"], esc(rest)))
    return "".join(teile)


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:%(w)dpx;height:%(h)dpx;background:%(grund)s;position:relative;overflow:hidden;
  font-family:'IBM Plex Sans',sans-serif;-webkit-font-smoothing:antialiased;font-feature-settings:'tnum' 1}
.kopf{position:absolute;left:%(r)dpx;top:58px;font-family:'Archivo',sans-serif;font-weight:800;
  font-size:56px;line-height:1;letter-spacing:1px;color:%(text)s;white-space:nowrap}
.zahl{position:absolute;left:%(r)dpx;top:150px;font-family:'Archivo',sans-serif;font-weight:900;color:%(text)s;
  font-size:300px;line-height:0.86;letter-spacing:-6px;white-space:nowrap}
.einheit{position:absolute;left:%(r)dpx;top:430px;font-family:'Archivo',sans-serif;font-weight:800;
  font-size:48px;line-height:1;color:%(akzent)s;white-space:nowrap}
.bed{position:absolute;left:%(r)dpx;top:510px;width:600px;font-weight:500;font-size:36px;line-height:1.2;
  color:%(text)s}
.datum{position:absolute;left:%(r)dpx;bottom:128px;font-family:'IBM Plex Mono',monospace;font-weight:400;
  font-size:30px;color:%(text2)s;letter-spacing:-0.5px;white-space:nowrap}
.sig{position:absolute;left:50%%;transform:translateX(-50%%);bottom:48px;height:48px;display:flex;
  align-items:center;gap:16px}
.sig svg{width:170px;height:48px;display:block}
.obj{position:absolute;left:0;top:0}
"""


def html(d, t):
    obj = objekt(d["balken"], t["achse"], t["rest"], 760, 170, W - RAND - 760, 520)
    css = (look_takt.schriften_css()
           + CSS % {"w": W, "h": H, "r": RAND, "grund": LK["grund"], "text": LK["text"],
                    "text2": LK["text2"], "akzent": LK["akzent"]}
           + wortmarke.css(look="dunkel"))
    sig = ("<div class='sig'>%s<svg viewBox='0 0 230 48'><path d='%s' fill='none' stroke='%s' "
           "stroke-width='3' stroke-linejoin='round' stroke-linecap='round'/></svg></div>"
           % (wortmarke.html(), PULS, LK["markierung"]))
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s</style></head><body>"
            "<div class='kopf'>%s</div><div class='zahl'>%s</div><div class='einheit'>%s</div>"
            "<svg class='obj' width='%d' height='%d' viewBox='0 0 %d %d'>%s</svg>"
            "<div class='bed'>%s</div><div class='datum'>%s</div>%s</body></html>") % (
        css, esc(t["kopf"]), tausend(d["tokens"]), esc(t["einheit"]), W, H, W, H, obj,
        esc(t["bedeutung"]), esc(t["datumszeile"]).replace(" utc", " utc"), sig)


def chromium():
    for c in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
              "/opt/pw-browsers/chromium/chrome-linux/chrome"):
        if os.path.exists(c):
            return c
    return None


def rendern(seite, out):
    out = Path(out)
    tmp = out.with_suffix(".html")
    tmp.write_text(seite, encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        kw = {"executable_path": chromium()} if chromium() else {}
        b = p.chromium.launch(**kw)
        try:
            pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
            pg.goto(tmp.resolve().as_uri())
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(200)
            pg.screenshot(path=str(out))
        finally:
            b.close()
    return out


def laufen(tokens, zaehlung, stichzeit, out, namen_pfad=None, transfers=None):
    namen = json.load(open(namen_pfad, encoding="utf-8")) if namen_pfad else {}
    d = lesen(tokens, zaehlung, namen)
    t = texte(d, stichzeit, transfers)
    fehler = pruefen(t, d["balken"])
    if fehler:
        raise SystemExit("textregeln verletzt: " + "; ".join(fehler))
    rendern(html(d, t), out)
    print(json.dumps({"png": str(out), "tokens": d["tokens"], "halter_outputs": d["halter_outputs"],
                      "balken": len(d["balken"]), "datumszeile": t["datumszeile"]}))
    return d, t


def selbsttest(png=None):
    fehler = []

    def ok(name, bed, ist=None):
        if not bed:
            fehler.append(name)
            print("FEHLER", name, ist)
    with tempfile.TemporaryDirectory() as d:
        tp, zp = os.path.join(d, "t.csv"), os.path.join(d, "z.json")
        with open(tp, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["covenant_id", "halter_outputs", "halter", "menge_basis", "unter_token", "kas",
                        "transfers_seit", "kcc20_tx_seit"])
            for i, n in enumerate([900, 410, 120, 77, 40, 12, 9, 3, 2, 1, 0]):
                w.writerow(["%02x" % i * 32, n, n, n * 1000, 1, n * 0.2, 5, 5])
        json.dump({"tokens_mit_lebenden_outputs": 10}, open(zp, "w"))
        dd = lesen(tp, zp, {"00" * 32: "TEST"})
        ok("10 tokens mit haltern, der leere zaehlt nicht", dd["tokens"] == 10, dd["tokens"])
        ok("8 balken, groesster zuerst, name aus --namen", len(dd["balken"]) == 8 and dd["balken"][0]
           == {"name": "TEST", "wert": 900}, dd["balken"][:1])
        ok("rest 2", dd["rest"] == 2, dd["rest"])
        t = texte(dd, "2026-10-26T12:00:00Z", 1234)
        ok("datumszeile", t["datumszeile"] == "26 oct 2026, 12:00 utc · counted by kaspa pulse",
           t["datumszeile"])
        ok("textregeln gruen", pruefen(t, dd["balken"]) == [], pruefen(t, dd["balken"]))
        schlecht = dict(t, bedeutung="tokens live now: up")
        ok("textregeln fangen doppelpunkt und echtzeitwort", len(pruefen(schlecht, [])) >= 2,
           pruefen(schlecht, []))
        seite = html(dd, t)
        ok("kein falke, keine fremde marke", not any(v in seite.lower() for v in wortmarke.VERBOTEN_IN_AUSGABEN))
        ok("wortmarke drin", "KASPA <b>PULSE</b>" in seite)
        if png:
            rendern(seite, png)
            ok("png geschrieben", os.path.getsize(png) > 10000)
    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens")
    ap.add_argument("--zaehlung")
    ap.add_argument("--stichzeit")
    ap.add_argument("--namen")
    ap.add_argument("--transfers", type=int)
    ap.add_argument("--out", default="kcc20-grafik.png")
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--probebild")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest(a.probebild)
    laufen(a.tokens, a.zaehlung, a.stichzeit, a.out, a.namen, a.transfers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
