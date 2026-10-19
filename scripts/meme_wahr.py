#!/usr/bin/env python3
"""meme_wahr.py, Einzelpost "Meme, but true" fuer Instagram (Ben, 18.10.2026).

ENTWURF, NICHT SCHARF. Baut eine oder zwei Seiten und die Caption und
schickt sie hoechstens nach #moderator-only. Ben gibt frei und postet von
Hand. Kein fester Termin, gedacht fuer einen Samstag vor dem Wochen-Karussell
oder einen Tag ohne Reel.

SEITE 1  drei Element-Kacheln wie im Periodensystem, K (19, Potassium),
         As (33, Arsenic), Pa (91, Protactinium), darunter klein "KAsPa".
SEITE 2  (optional, macht den Post zum Karussell) "the chemistry checks out.
         so does the speed." und eine belegte Zahl mit Datum und Quelle:
           --zahl messung    Bloecke je Sekunde, 10 Minuten gemessen wie in
                             der Tagesgrafik (tagesgrafik.m_blockrate), nur
                             mit Netz zu api.kaspa.org, "counted by kaspa
                             pulse from the kaspa rest api"
           --zahl crescendo  10 Bloecke je Sekunde seit dem Crescendo-Upgrade
                             am 5 may 2025, die Blockrate des Protokolls, kein Messwert;
                             das ist auch der Rueckfall, wenn die Messung scheitert,
                             und dann steht nirgends "counted" (Ben, 19.10.2026)

TERMIN (Ben, 19.10.2026): So 25.10. 11:00, eigener Rang "meme" im
Instagram-Raster nach der Tagesgrafik. Entwurf am Posttag 09:00 Berlin, weil
die Messung am Posttag laeuft.

Ordnungszahlen und Namen stehen fest im Skript (IUPAC); geprueft wird, dass
sie zu den Symbolen passen. Jede Seite traegt ein Datum, weil Ziffern im
Bild stehen. Textpruefer wie ueberall (karussell.text_pruefen,
caption_pruefen), Groessen und Rand misst content_wache am Bild.

    python3 scripts/meme_wahr.py --fuer 2026-10-24 --out /tmp/m [--zahl crescendo] [--alle-looks]
    python3 scripts/meme_wahr.py --fuer 2026-10-24 --zahl messung --senden
    python3 scripts/meme_wahr.py --selbsttest
"""
import argparse
import datetime as dt
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ELEMENTE = (("K", 19, "Potassium"), ("As", 33, "Arsenic"), ("Pa", 91, "Protactinium"))
# zur probe gegen ein zweites, unabhaengiges stueck wissen: die ordnungszahl
# ist die zahl der protonen, die reihenfolge im periodensystem
IUPAC = {"K": 19, "As": 33, "Pa": 91}
WORT = "KAsPa"
SEITE2 = ("the chemistry checks out.", "so does the speed.")
FRAGE = "what other word can you build from the table?"
CRESCENDO = "2025-05-05"

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1350px;background:%(grund)s;position:relative;overflow:hidden;color:%(text)s;
  font-family:'IBM Plex Sans',sans-serif;-webkit-font-smoothing:antialiased;font-feature-settings:'tnum' 1}
.kopf{position:absolute;left:60px;top:66px;font-family:'Archivo',sans-serif;font-weight:800;font-size:64px;
  line-height:1;letter-spacing:1px;white-space:nowrap}
.nr{position:absolute;right:60px;top:78px;font-family:'IBM Plex Mono',monospace;font-size:34px;color:%(text2)s}
.kacheln{position:absolute;left:60px;top:330px;width:960px;display:flex;gap:30px}
.k{width:300px;height:360px;border:4px solid %(akzent)s;border-radius:18px;position:relative;background:%(flaeche)s}
.k .z{position:absolute;left:24px;top:18px;font-family:'IBM Plex Mono',monospace;font-size:44px;font-weight:500}
.k .s{position:absolute;left:0;right:0;top:80px;text-align:center;font-family:'Archivo',sans-serif;
  font-weight:900;font-size:170px;line-height:1;color:%(akzent)s}
.k .n{position:absolute;left:0;right:0;bottom:24px;text-align:center;font-size:38px;font-weight:500}
.wort{position:absolute;left:0;right:0;top:760px;text-align:center;font-family:'Archivo',sans-serif;
  font-weight:800;font-size:96px;letter-spacing:4px}
.wort b{color:%(akzent)s;font-weight:800}
.fluss{position:absolute;left:60px;right:60px;top:190px}
.satz1,.satz2{font-family:'Archivo',sans-serif;font-weight:800;font-size:80px;line-height:1.05}
.satz2{color:%(akzent)s;margin-top:8px}
.zahl{margin-top:90px;font-family:'Archivo',sans-serif;font-weight:900;line-height:0.86;
  letter-spacing:-4px;white-space:nowrap}
.zahl .einheit{font-size:0.3em;font-weight:800;letter-spacing:0;margin-left:18px}
.satz{margin-top:40px;font-weight:500;font-size:48px;line-height:1.2;color:%(akzent)s}
.datum{position:absolute;left:60px;right:60px;bottom:132px;font-family:'IBM Plex Mono',monospace;
  font-size:34px;line-height:1.28;color:%(text2)s;letter-spacing:-0.5px}
.sig{position:absolute;left:50%%;transform:translateX(-50%%);bottom:60px;height:48px;display:flex;
  align-items:center;gap:16px}
.sig img{width:38px;height:auto;display:block;filter:%(falke)s}
.sig span{font-weight:600;font-size:34px;letter-spacing:4px;white-space:nowrap}
.sig svg{width:170px;height:48px;display:block}
"""


def tag(iso):
    import karussell
    return karussell.tag(iso)


def zahl_seite2(art, fuer, messen=None):
    """(zahl, satz, datumszeile, caption-satz) fuer Seite 2.

    messung (Ben, 19.10.2026): am Posttag 10 Minuten nach Hausregel gemessen.
    Scheitert die Messung, faellt die Seite auf die Crescendo-Blockrate
    zurueck, und dann steht nirgends "counted", denn gezaehlt hat niemand."""
    if art == "messung":
        try:
            import tagesgrafik as tg
            bps, _ = (messen or (lambda: tg.m_blockrate(tg.BLOCKRATE_SEK)))()
            if not 5 <= bps <= 15:
                raise ValueError("blockrate %.2f unplausibel" % bps)
            return ("%.1f blocks a second" % bps, "measured on the kaspa network over 10 minutes",
                    "%s · counted by kaspa pulse from the kaspa rest api" % tag(fuer),
                    "%.1f blocks a second on %s, counted by kaspa pulse over 10 minutes." % (bps, tag(fuer)))
        except Exception as exc:                    # noqa: BLE001
            print("messung gescheitert (%s), rueckfall auf die crescendo-blockrate" % exc)
    return ("10 blocks a second", "the block rate since the crescendo upgrade",
            "since %s · source kaspa crescendo upgrade" % tag(CRESCENDO),
            "10 blocks a second, the block rate since the crescendo upgrade on %s." % tag(CRESCENDO))


def seiten(fuer, zweite=None):
    s = [{"art": "kacheln", "datum": "%s · atomic numbers, source IUPAC periodic table" % tag(fuer)}]
    if zweite:
        z, satz, datum, cap = zweite
        s.append({"art": "zahl", "zahl": z, "satz": satz, "datum": datum, "caption": cap})
    for i, x in enumerate(s):
        x["seite"], x["von"] = i + 1, len(s)
    return s


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def seite_html(s, falke, look):
    import look_takt
    import tagesgrafik as tg
    lk = look_takt.look(look)
    css = look_takt.schriften_css() + CSS % {k: lk[k] for k in ("grund", "text", "text2", "akzent", "flaeche", "falke")}
    sig = ("<div class='sig' data-rolle='fuss'><img src='%s' alt=''><span>KASPA PULSE</span>"
           "<svg viewBox='0 0 230 48'><path d='%s' fill='none' stroke='%s' stroke-width='3' "
           "stroke-linejoin='round' stroke-linecap='round'/></svg></div>" % (falke, tg.PULS, lk["markierung"]))
    nr = "<div class='nr'>%d/%d</div>" % (s["seite"], s["von"]) if s["von"] > 1 else ""
    if s["art"] == "kacheln":
        kacheln = "".join("<div class='k'><div class='z'>%d</div><div class='s' data-rolle='titel'>%s</div>"
                          "<div class='n'>%s</div></div>" % (z, esc(sym), esc(name)) for sym, z, name in ELEMENTE)
        innen = ("<div class='kopf' data-rolle='titel'>MEME, BUT TRUE</div>%s<div class='kacheln'>%s</div>"
                 "<div class='wort' data-rolle='titel'><b>K</b><b>As</b><b>Pa</b></div>" % (nr, kacheln))
    else:
        ziffern, einheit = tg.zahl_teilen(s["zahl"])
        innen = ("<div class='kopf' data-rolle='titel'>MEME, BUT TRUE</div>%s<div class='fluss'>"
                 "<div class='satz1' data-rolle='titel'>%s</div><div class='satz2' data-rolle='titel'>%s</div>"
                 "<div class='zahl' data-rolle='zahl' style='font-size:240px'>%s%s</div>"
                 "<div class='satz'>%s</div></div>" % (
                     nr, esc(SEITE2[0]), esc(SEITE2[1]), esc(ziffern),
                     "<span class='einheit' data-rolle='einheit'>%s</span>" % esc(einheit) if einheit else "",
                     esc(s["satz"])))
    innen += "<div class='datum'>%s</div>" % esc(s["datum"])
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s</style></head>"
            "<body data-look='%s'>%s%s</body></html>" % (css, look, innen, sig))


def caption(ss):
    teile = ["K is potassium, As is arsenic, Pa is protactinium. put them together and you get %s." % WORT]
    zw = [x for x in ss if x["art"] == "zahl"]
    if zw:
        teile.append("the chemistry checks out, and so does the speed. " + zw[0]["caption"])
    teile += ["#kaspa #kas #blockdag", FRAGE]
    return "\n\n".join(teile)


def pruefen(ss, cap):
    import karussell
    fehler = []
    for sym, z, name in ELEMENTE:
        if IUPAC.get(sym) != z:
            fehler.append("ordnungszahl von %s stimmt nicht" % sym)
    if "".join(sym for sym, _, _ in ELEMENTE) != WORT:
        fehler.append("die symbole ergeben nicht %s" % WORT)
    texte = [x[k] for x in ss for k in ("satz", "datum", "zahl", "caption") if x.get(k)] + list(SEITE2)
    fehler += karussell.text_pruefen(texte) + karussell.caption_pruefen(cap)
    return fehler


def bauen(fuer, out, zahl="", looks=("dunkel",)):
    import tagesgrafik as tg
    from playwright.sync_api import sync_playwright
    ss = seiten(fuer, zahl_seite2(zahl, fuer) if zahl else None)
    cap = caption(ss)
    fehler = pruefen(ss, cap)
    if fehler:
        raise SystemExit("ABBRUCH %s" % "; ".join(fehler))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    bilder = []
    with sync_playwright() as p:
        b = tg.chromium_start(p)
        try:
            for lk in looks:
                for s in ss:
                    png = out / ("meme-wahr-%s-%d-%s.png" % (fuer, s["seite"], lk))
                    tg.rendern(seite_html(s, tg.falke_lesen(), lk), png, 0, b, "instagram")
                    bilder.append(png)
        finally:
            b.close()
    (out / ("meme-wahr-%s-caption.txt" % fuer)).write_text(cap + "\n", encoding="utf-8")
    return ss, cap, bilder


def selbsttest():
    fehler = 0

    def ok(name, bed):
        nonlocal fehler
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        fehler += 0 if bed else 1

    ss = seiten("2026-10-24", zahl_seite2("crescendo", "2026-10-24"))
    cap = caption(ss)
    ok("zwei seiten, jede mit datum", len(ss) == 2 and all("2026" in x["datum"] or "2025" in x["datum"] for x in ss))
    ok("symbole ergeben KAsPa, ordnungszahlen nach IUPAC", not [f for f in pruefen(ss, cap) if "ordnung" in f or "symbol" in f])
    ok("texte und caption halten die wachen (%s)" % "; ".join(pruefen(ss, cap)), not pruefen(ss, cap))
    ok("caption ohne link, frage am ende", cap.rstrip().endswith(FRAGE) and "http" not in cap)
    ok("seite 1 allein geht auch", len(seiten("2026-10-24")) == 1)
    g = zahl_seite2("messung", "2026-10-25", messen=lambda: (9.87, 1))
    ok("messung traegt den posttag und counted (%s)" % g[0], g[0] == "9.9 blocks a second"
       and "25 oct 2026" in g[2] and "counted by kaspa pulse" in g[2])

    def kaputt():
        raise OSError("tunnel 403")
    r = zahl_seite2("messung", "2026-10-25", messen=kaputt)
    ok("gescheiterte messung faellt auf crescendo zurueck, ohne counted",
       r[0] == "10 blocks a second" and not any("counted" in t for t in r)
       and r[3] == "10 blocks a second, the block rate since the crescendo upgrade on 5 may 2025.")
    ok("unplausible messung faellt auch zurueck", zahl_seite2("messung", "2026-10-25", messen=lambda: (99.0, 1))[0]
       == "10 blocks a second")
    ss2 = seiten("2026-10-25", r)
    ok("rueckfall haelt die wachen", not pruefen(ss2, caption(ss2)))
    print("%d fehler" % fehler)
    return 1 if fehler else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fuer", default="", help="post-datum JJJJ-MM-TT, ohne: heute (gemessen wird am posttag)")
    ap.add_argument("--out", default="graphics/meme-wahr")
    ap.add_argument("--zahl", default="", choices=["", "messung", "crescendo"], help="leer = nur seite 1")
    ap.add_argument("--look", default="", help="ohne: der look aus dem instagram-raster")
    ap.add_argument("--alle-looks", action="store_true")
    ap.add_argument("--senden", action="store_true", help="entwurf nach #moderator-only")
    ap.add_argument("--selbsttest", "--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    a.fuer = a.fuer or dt.datetime.now(dt.timezone.utc).date().isoformat()
    import look_takt
    sp = look_takt.lesen()
    lk = a.look or look_takt.raster_faellig(sp, "meme", a.fuer)[1]
    looks = ("dunkel", "hell", "teal") if a.alle_looks else (lk,)
    ss, cap, bilder = bauen(a.fuer, a.out, a.zahl, looks)
    if a.senden:
        import karussell
        hook = os.environ.get("DISCORD_WEBHOOK_OPS", "")
        if not hook:
            raise SystemExit("ABBRUCH kein DISCORD_WEBHOOK_OPS, nichts geschickt")
        karussell.UHRZEIT["meme"] = "So 11:00" if dt.date.fromisoformat(a.fuer).weekday() == 6 else "nach freigabe"
        karussell.ops_senden(hook, "meme", a.fuer, lk, [b for b in bilder if b.stem.endswith("-" + lk)], cap)
        look_takt.raster_merken(sp, "meme", a.fuer)
        look_takt.schreiben(sp)
    print("meme, but true fuer %s, look %s\n%s\n\nCAPTION\n%s" % (a.fuer, lk, "\n".join(map(str, bilder)), cap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
