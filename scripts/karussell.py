#!/usr/bin/env python3
"""karussell.py, Instagram-Karussell zweimal die Woche (Ben, 18.10.2026).

ENTWURF, NICHT SCHARF. Dieses Skript baut die Seiten und die Caption und
schickt den Entwurf hoechstens nach #moderator-only. Es postet nirgendwo.
Das Posten ueber die Graph API kommt erst nach Bens Freigabe-Strecke.

ZWEI FORMATE
  woche   Sa 11:00 "The week in numbers", 4 Seiten. Seite 1 ein Haken-Satz
          und die groesste Zahl der Woche, Seite 2 und 3 je eine weitere
          Wochenzahl mit einem Satz, Seite 4 der Abbinder. Die Zahlen kommen
          aus data/weekly-history.json (die Weekly Numbers), immer die
          letzte Ausgabe gegen die davor.
  story   Mi 18:00 "The story of ...", 4 bis 5 Seiten zum Thema des
          Donnerstags-Erklaerers, aus data/karussell-story.json (von Hand
          oder von der Routine gefuellt). Folgt im naechsten Schritt.

REGELN, vor dem Rendern und am gerenderten Bild erzwungen
  jede Seite 1080x1350 im Look aus dem Takt, die Groessen der Feed-Zeile
  (content_wache misst jede Seite), jede Zahl mit Datum und Quelle,
  "counted" nur bei eigener Zaehlung, fremde Reihen "source ...", kein
  Echtzeit-Wort, "%" statt "percent", kein Kursziel, Caption ohne Link mit
  Frage am Ende.

    python3 scripts/karussell.py woche --out /tmp/k [--look dunkel] [--alle-looks]
    python3 scripts/karussell.py --selbsttest
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

HISTORY = REPO / "data" / "weekly-history.json"
ABBINDER = ("One number like this every day.", "Follow @kaspapulse")
MONATE = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def tag(iso):
    j, m, d = iso.split("-")
    return "%d %s %s" % (int(d), MONATE[int(m) - 1], j)


def tag_kurz(iso):
    return " ".join(tag(iso).split()[:2])


def ganz(n):
    return "{:,}".format(int(round(n)))


# ------------------------------------------------------------ die zahlen

def stichtag(woche):
    """Die Weekly Numbers einer Ausgabe (Montag) stehen auf dem Samstag davor."""
    import datetime as dt
    return (dt.date.fromisoformat(woche) - dt.timedelta(days=2)).isoformat()


def kandidaten(jetzt, vorher):
    """Die Wochenzahlen als Seiten-Kandidaten. Jede traegt ihre Quelle als
    fremde Reihe ("source ..."), weil keine davon unsere eigene Zaehlung ist."""
    s, s0 = stichtag(jetzt["week"]), stichtag(vorher["week"])
    k = []
    if jetzt.get("hashrate") and vorher.get("hashrate"):
        d = 100 * (jetzt["hashrate"] / vorher["hashrate"] - 1)
        k.append({"id": "hashrate", "kopf": "HASHRATE", "zahl": "%.0f PH/s" % jetzt["hashrate"],
                  "satz": "network hashrate on %s, %+.1f%% against %s" % (tag_kurz(s), d, tag_kurz(s0)),
                  "quelle": "source kaspa rest api", "gewicht": abs(d), "stolz": d > 0})
    if jetzt.get("holders") and vorher.get("holders"):
        n = jetzt["holders"] - vorher["holders"]
        k.append({"id": "holders", "kopf": "ADDRESSES", "zahl": ganz(jetzt["holders"]),
                  "satz": "addresses hold a meaningful balance, %s%s against %s"
                          % ("+" if n >= 0 else "", ganz(n), tag_kurz(s0)),
                  "quelle": "source kaspalytics address counts",
                  "gewicht": abs(100 * n / vorher["holders"]), "stolz": n > 0})
    if jetzt.get("dormant_pct") and vorher.get("dormant_pct"):
        k.append({"id": "dormant", "kopf": "SLEEPING COINS", "zahl": "%.1f%%" % jetzt["dormant_pct"],
                  "satz": "of all KAS has not moved in a year, %.2f%% on %s"
                          % (vorher["dormant_pct"], tag_kurz(s0)),
                  "quelle": "source kaspalytics",
                  "gewicht": abs(jetzt["dormant_pct"] - vorher["dormant_pct"]), "stolz": True})
    if jetzt.get("tvl_total") and vorher.get("tvl_total"):
        d = 100 * (jetzt["tvl_total"] / vorher["tvl_total"] - 1)
        k.append({"id": "tvl", "kopf": "LOCKED ON LAYER 2", "zahl": "$%.2fM" % (jetzt["tvl_total"] / 1e6),
                  "satz": "locked across kasplex and igra, %+.1f%% against %s" % (d, tag_kurz(s0)),
                  "quelle": "source defillama", "gewicht": abs(d), "stolz": d > 0})
    if jetzt.get("mined_pct"):
        k.append({"id": "mined", "kopf": "MINED SO FAR", "zahl": "%.2f%%" % jetzt["mined_pct"],
                  "satz": "of all KAS that will ever exist, with 0 premine",
                  "quelle": "source kaspa rest api", "gewicht": 0.0, "stolz": True})
    for x in k:
        x["datum"] = "%s · %s" % (tag(s), x["quelle"])
    return k


def waehle(kand, anzahl=3):
    """Seite 1 ist die staerkste Zahl, die stolz macht, Seite 2 und 3 die
    naechsten. Gleichstand nach der festen Reihenfolge oben."""
    stolz = sorted([x for x in kand if x["stolz"]], key=lambda x: -x["gewicht"])
    rest = sorted([x for x in kand if not x["stolz"]], key=lambda x: -x["gewicht"])
    return (stolz + rest)[:anzahl]


def haken(erste):
    """Der Haken-Satz ueber der groessten Zahl, nach Kennzahl."""
    # kein versprechen ueber die zahl hinaus: "than ever" waere ein rekord,
    # belegt ist nur die woche davor; gezaehlt werden adressen, nicht menschen
    return {"hashrate": "more work secured kaspa than a week before",
            "holders": "more addresses hold real KAS than a week ago",
            "dormant": "half of all KAS has not moved in a year",
            "tvl": "money is moving onto kaspa layer 2",
            "mined": "almost every KAS is already out"}[erste["id"]]


# ------------------------------------------------------------ seiten

def seiten(woche_jetzt, woche_vorher):
    k = waehle(kandidaten(woche_jetzt, woche_vorher))
    if len(k) < 3:
        raise SystemExit("ABBRUCH weniger als drei wochenzahlen in der ausgabe %s" % woche_jetzt["week"])
    s = [dict(k[0], art="haken", haken=haken(k[0]), seite=1)]
    s += [dict(x, art="zahl", seite=i + 2) for i, x in enumerate(k[1:3])]
    # auch der abbinder traegt den stichtag, die seitenzahl ist eine ziffer
    s.append({"art": "abbinder", "seite": 4,
              "datum": "the week to %s" % tag(stichtag(woche_jetzt["week"]))})
    return s


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1350px;background:%(grund)s;position:relative;overflow:hidden;color:%(text)s;
  font-family:'IBM Plex Sans',sans-serif;-webkit-font-smoothing:antialiased;font-feature-settings:'tnum' 1}
.kopf{position:absolute;left:60px;top:66px;font-family:'Archivo',sans-serif;font-weight:800;font-size:64px;
  line-height:1;letter-spacing:1px;white-space:nowrap}
.nr{position:absolute;right:60px;top:78px;font-family:'IBM Plex Mono',monospace;font-size:34px;color:%(text2)s}
.haken{position:absolute;left:60px;right:60px;top:190px;font-family:'Archivo',sans-serif;font-weight:800;
  font-size:76px;line-height:1.04;color:%(akzent)s}
.zahl{position:absolute;left:60px;font-family:'Archivo',sans-serif;font-weight:900;line-height:0.86;
  letter-spacing:-4px;white-space:nowrap}
.zahl .einheit{font-size:0.36em;font-weight:800;letter-spacing:0;margin-left:18px}
.satz{position:absolute;left:60px;right:60px;font-weight:500;font-size:48px;line-height:1.2;color:%(akzent)s}
.datum{position:absolute;left:60px;right:60px;bottom:132px;font-family:'IBM Plex Mono',monospace;
  font-size:34px;line-height:1.28;color:%(text2)s;letter-spacing:-0.5px}
.gross{position:absolute;left:60px;right:60px;top:420px;font-family:'Archivo',sans-serif;font-weight:900;
  font-size:104px;line-height:1.02}
.folgen{position:absolute;left:60px;right:60px;top:800px;font-family:'Archivo',sans-serif;font-weight:800;
  font-size:72px;color:%(akzent)s}
.sig{position:absolute;left:50%%;transform:translateX(-50%%);bottom:60px;height:48px;display:flex;
  align-items:center;gap:16px}
.sig img{width:38px;height:auto;display:block;filter:%(falke)s}
.sig span{font-weight:600;font-size:34px;letter-spacing:4px;white-space:nowrap}
.sig svg{width:170px;height:48px;display:block}
"""


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" utc", " utc")


def seite_html(s, falke, look):
    import look_takt
    import tagesgrafik as tg
    lk = look_takt.look(look)
    css = look_takt.schriften_css() + CSS % {"grund": lk["grund"], "text": lk["text"], "text2": lk["text2"],
                                             "akzent": lk["akzent"], "falke": lk["falke"]}
    sig = ("<div class='sig' data-rolle='fuss'><img src='%s' alt=''><span>KASPA PULSE</span>"
           "<svg viewBox='0 0 230 48'><path d='%s' fill='none' stroke='%s' stroke-width='3' "
           "stroke-linejoin='round' stroke-linecap='round'/></svg></div>" % (falke, tg.PULS, lk["markierung"]))
    nr = "<div class='nr'>%d/4</div>" % s["seite"]
    if s["art"] == "abbinder":
        innen = ("<div class='kopf' data-rolle='titel'>KASPA PULSE</div>%s"
                 "<div class='gross'>%s</div><div class='folgen'>%s</div><div class='datum'>%s</div>"
                 % (nr, esc(ABBINDER[0]), esc(ABBINDER[1]), esc(s["datum"])))
    else:
        ziffern, einheit = tg.zahl_teilen(s["zahl"])
        zg = tg.zahlgroesse(s["zahl"])
        top_zahl = 470 if s["art"] == "haken" else 200
        zahl = ("<div class='zahl' data-rolle='zahl' style='top:%dpx;font-size:%dpx'>%s%s</div>"
                % (top_zahl, zg, esc(ziffern),
                   "<span class='einheit' data-rolle='einheit'>%s</span>" % esc(einheit) if einheit else ""))
        haken_html = "<div class='haken'>%s</div>" % esc(s["haken"]) if s["art"] == "haken" else ""
        top_satz = top_zahl + int(zg * 0.86) + 56
        innen = ("<div class='kopf' data-rolle='titel'>%s</div>%s%s%s<div class='satz' style='top:%dpx'>%s</div>"
                 "<div class='datum'>%s</div>" % (
                     "THE WEEK IN NUMBERS" if s["art"] == "haken" else esc(s["kopf"]), nr, haken_html, zahl,
                     top_satz, esc(s["satz"]), esc(s["datum"])))
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s</style></head>"
            "<body data-look='%s'>%s%s</body></html>" % (css, look, innen, sig))


# ------------------------------------------------------------ caption

FRAGEN = ("which of these numbers would you have guessed?",
          "which number should we follow next week?",
          "did any of these surprise you?")


def caption(ss, woche_jetzt, nummer=0):
    s = stichtag(woche_jetzt["week"])
    zeilen = [x for x in ss if x["art"] != "abbinder"]
    quellen = []
    for x in zeilen:
        q = x["quelle"].replace("source ", "").split()[0] if "kaspalytics" in x["quelle"] \
            else x["quelle"].replace("source ", "")
        if q not in quellen:
            quellen.append(q)
    teile = ["the week in numbers, as of %s." % tag(s),
             "\n".join("%s %s" % (x["zahl"], x["satz"]) for x in zeilen),
             "source %s." % " and ".join(quellen),
             "#kaspa #kas #blockdag",
             FRAGEN[nummer % len(FRAGEN)]]
    return "\n\n".join(teile)


def text_pruefen(texte):
    """Dieselben Wachen wie ueberall: pruefe_eine aus der Tagesgrafik und die
    Textregeln der content_wache (Echtzeit, %, Pfeile, Kursziele)."""
    import content_wache
    import tagesgrafik as tg
    fehler = []
    for t in texte:
        # der handle auf dem abbinder ist bens vorgabe, kein link
        for f in tg.pruefe_eine(t.replace("@kaspapulse", "@handle"), None, "karussell"):
            fehler.append("%s in %r" % (f, t[:50]))
        for f in content_wache.text_verstoesse(t):
            fehler.append("%s in %r" % (f, t[:50]))
        if re.search(r"\bcounted\b", t, re.I) and "source " in t:
            fehler.append("counted bei einer fremden quelle in %r" % t[:50])
    return fehler


def caption_pruefen(c):
    fehler = text_pruefen([c.replace("#", "")])
    if re.search(r"https?://|www\.|\.com/", c):
        fehler.append("link in der caption")
    if not c.rstrip().endswith("?"):
        fehler.append("caption endet nicht mit einer frage")
    return fehler


# ------------------------------------------------------------ bauen

def bauen(out, looks, history=None):
    import tagesgrafik as tg
    from playwright.sync_api import sync_playwright
    h = json.loads(Path(history or HISTORY).read_text(encoding="utf-8"))
    jetzt, vorher = h[-1], h[-2]
    ss = seiten(jetzt, vorher)
    fehler = text_pruefen([x[k] for x in ss for k in ("haken", "satz", "datum", "zahl", "kopf") if k in x]
                          + list(ABBINDER))
    cap = caption(ss, jetzt)
    fehler += caption_pruefen(cap)
    if fehler:
        raise SystemExit("ABBRUCH textpruefung, %s" % "; ".join(fehler))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    falke = tg.falke_lesen()
    bilder = []
    with sync_playwright() as p:
        b = tg.chromium_start(p)
        try:
            for lk in looks:
                for s in ss:
                    png = out / ("karussell-woche-%s-%d-%s.png" % (jetzt["week"], s["seite"], lk))
                    tg.rendern(seite_html(s, falke, lk), png, 0, b, "instagram")
                    bilder.append(png)
        finally:
            b.close()
    (out / ("karussell-woche-%s-caption.txt" % jetzt["week"])).write_text(cap + "\n", encoding="utf-8")
    return ss, cap, bilder


def selbsttest():
    fehler = 0

    def ok(name, bed):
        nonlocal fehler
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        fehler += 0 if bed else 1

    a = {"week": "2026-10-05", "hashrate": 354.49, "holders": 800919.0, "dormant_pct": 50.62,
         "tvl_total": 1386405.34, "mined_pct": 96.639}
    b = {"week": "2026-10-12", "hashrate": 362.36, "holders": 802817.0, "dormant_pct": 51.3,
         "tvl_total": 1244205.59, "mined_pct": 96.684}
    ss = seiten(b, a)
    ok("vier seiten, die letzte ist der abbinder", len(ss) == 4 and ss[-1]["art"] == "abbinder")
    ok("seite 1 ist eine zahl, die stolz macht (%s)" % ss[0]["id"], ss[0]["stolz"])
    ok("ein fallender wert steht nicht auf seite 1", ss[0]["id"] != "tvl")
    ok("jede zahlenseite traegt datum und quelle",
       all("10 oct 2026" in x["datum"] and "source " in x["datum"] for x in ss[:3]))
    ok("stichtag ist der samstag vor der ausgabe", stichtag("2026-10-12") == "2026-10-10")
    ok("texte halten die wachen", not text_pruefen([x[k] for x in ss for k in ("haken", "satz", "datum")
                                                     if k in x] + list(ABBINDER)))
    c = caption(ss, b)
    ok("caption ohne link, frage am ende", not caption_pruefen(c))
    ok("kein haken verspricht einen rekord", not any(re.search(r"\bever\b|record|people", haken(x))
                                                     for x in kandidaten(b, a)))
    ok("caption mit link faellt auf", bool(caption_pruefen(c + " kaspapulse.com/ig")))
    ok("echtzeit im satz faellt auf", bool(text_pruefen(["hashrate right now at 360 PH/s on 10 oct"])))
    ok("counted bei fremder quelle faellt auf",
       bool(text_pruefen(["10 oct 2026, counted · source defillama"])))
    print("%d fehler" % fehler)
    return 1 if fehler else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("art", nargs="?", choices=["woche"])
    ap.add_argument("--out", default="graphics/karussell")
    ap.add_argument("--look", default="", help="ohne: der look aus dem takt")
    ap.add_argument("--alle-looks", action="store_true", help="fuer den kontaktbogen")
    ap.add_argument("--selbsttest", "--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.art != "woche":
        ap.print_help()
        return 2
    looks = ("dunkel", "hell", "teal") if a.alle_looks else (a.look or "dunkel",)
    ss, cap, bilder = bauen(a.out, looks)
    print("\n".join(str(p) for p in bilder))
    print("\nCAPTION\n%s" % cap)
    return 0


if __name__ == "__main__":
    sys.exit(main())
