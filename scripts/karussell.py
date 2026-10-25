#!/usr/bin/env python3
"""karussell.py, Instagram-Karussell zweimal die Woche (Ben, 18.10.2026).

Dieses Skript baut die Seiten und die Caption. Gepostet wird seit dem
25.10.2026 von scripts/karussell_post.py: Entwurf 2 Stunden vor dem Termin
nach #moderator-only, zum Termin ueber die Graph API, scharf nur mit der
Variable KARUSSELL_LIVE=true (Ben, 25.10.2026). Karussells gehen ohne Musik raus, die
Graph API kann keine anhaengen; bei Handposts darf Ben Pixabay-Musik dazulegen.

ZWEI FORMATE
  woche   Sa 11:00 "The week in numbers", 4 Seiten, Entwurf Sa 09:00.
          Seite 1 ein Haken-Satz und die staerkste Zahl der Woche, die stolz
          macht. Seite 2 und 3 je eine weitere Wochenzahl mit einem Satz und
          zwei Balken, Vorwoche gegen Woche, ab null, jeder Wert am Balken.
          Seite 4 der Abbinder. Die Zahlen kommen aus der Montagsausgabe der
          Weekly Numbers (data/weekly-history.json), jede Seite traegt
          "week to <samstag>" und die Quelle.
  story   Mi 18:00 "The story of ...", 4 bis 5 Seiten, Entwurf Mi 16:00.
          Thema ist der Donnerstags-Erklaerer der Vorwoche. Die Routine
          "Donnerstags-Erklaerer vorbereiten" schreibt danach
          data/karussell-story.json:
            {"mittwoch": "JJJJ-MM-TT", "stand": "JJJJ-MM-TT", "titel": "the story of ...",
             "seiten": [{"kopf": "...", "satz": "ein gedanke",
                         "zahl": "optional", "datum": "16 oct 2026",
                         "quelle": "source ... | counted by kaspa pulse"}, ...],
             "frage": "die frage am ende der caption?"}
          3 oder 4 Inhaltsseiten, dazu der Abbinder. Eine Seite mit Zahl
          braucht Datum und Quelle, jede andere traegt "as of <stand>"
          (Stand der Fakten im Erklaerer). Die Caption nennt "full explainer on
          YouTube", ohne Link.

CAPTION (Ben, 25.10.2026), fuenf Bloecke: Haken mit Zahl, ein Satz mit
Stichtag und Quelle, eine Frage, "Weekly Kaspa numbers in our newsletter,
link in bio.", hoechstens fuenf Hashtags. Kein Link (caption_pruefen).

LOOK. Ein gemeinsamer Takt fuer alle Instagram-Posts (look_takt.RASTER), das
Karussell nimmt den Schritt nach der Tagesgrafik desselben Tages. Im
teal-Look tragen die Balken den Restton #178270 statt #9AF5E3 (Ben,
18.10.2026), in allen Looks steht jeder Wert als Text am Balken.

REGELN, vor dem Rendern und am gerenderten Bild erzwungen
  jede Seite 1080x1350, Groessen der Feed-Zeile (content_wache misst jede
  Seite), jede Zahl mit Datum und Quelle, "counted" nur bei eigener Zaehlung,
  fremde Reihen "source ...", kein Echtzeit-Wort, "%" statt "percent", kein
  Kursziel, kein Versprechen ueber die Zahl hinaus, Caption nach den
  Content-Regeln, Seite 1 ohne Diagramm (im Profilraster steht sie neben der
  Tagesgrafik, nie zwei Diagramme nebeneinander).

    python3 scripts/karussell.py woche --out /tmp/k [--fuer 2026-10-24] [--alle-looks]
    python3 scripts/karussell.py story --out /tmp/k [--story datei.json]
    python3 scripts/karussell.py woche --fuer 2026-10-24 --senden      Entwurf nach ops, Takt merken
    python3 scripts/karussell.py --selbsttest
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

HISTORY = REPO / "data" / "weekly-history.json"
STORY = REPO / "data" / "karussell-story.json"
ABBINDER = ("One number like this every day.", "Follow @kaspapulse")
MONATE = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
BALKEN_REST = {"teal": "#178270"}          # sonst der restton des looks
# die balken enden ueber der datumszeile, auch wenn sie zwei zeilen hat
# (unterkante 1218, zwei zeilen mono 34 sind 87 px)
BALKEN_UNTEN = 1100
# Posttermine (Ben, 25.10.2026): der Entwurf kommt 2 Stunden vorher nach
# #moderator-only, zum Termin postet scripts/karussell_post.py. Wochentag
# 0 = montag.
POSTZEIT = {"woche": (5, "11:00"), "story": (2, "18:00"), "meme": (5, "15:00")}
UHRZEIT = {a: "%s %s" % (("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")[t], hm) for a, (t, hm) in POSTZEIT.items()}
# Die Caption nach den Content-Regeln (Ben, 25.10.2026): fuenf Bloecke,
# Haken mit Zahl, ein Satz, eine Frage, die Newsletter-Zeile, hoechstens
# fuenf Hashtags, kein Link.
ZEILE_BIO = "Weekly Kaspa numbers in our newsletter, link in bio."
TAGS = "#kaspa #kas #blockdag"
MAX_TAGS = 5
UA = "kaspa-pulse-bot (+https://kaspapulse.com)"


class Stopp(Exception):
    pass


def tag(iso):
    j, m, d = str(iso).split("-")
    return "%d %s %s" % (int(d), MONATE[int(m) - 1], j)


def tag_kurz(iso):
    return " ".join(tag(iso).split()[:2])


def ganz(n):
    return "{:,}".format(int(round(n)))


# ------------------------------------------------------------ woche, zahlen

def stichtag(woche):
    """Die Weekly Numbers einer Ausgabe (Montag) stehen auf dem Samstag davor."""
    return (dt.date.fromisoformat(woche) - dt.timedelta(days=2)).isoformat()


def ausgaben_fuer(history, fuer):
    """Die Montagsausgabe derselben Woche wie der Post-Samstag und die davor.
    Ohne passende Ausgabe kein Entwurf, eine alte Woche waere ein falsches
    Datum im Bild."""
    montag = (dt.date.fromisoformat(fuer) - dt.timedelta(days=5)).isoformat()
    for i, e in enumerate(history):
        if e.get("week") == montag and i > 0:
            return e, history[i - 1]
    raise Stopp("keine montagsausgabe %s in weekly-history.json (letzte %s)"
                % (montag, history[-1].get("week") if history else "-"))


def kandidaten(jetzt, vorher):
    """Die Wochenzahlen als Seiten. Keine davon ist unsere eigene Zaehlung,
    also traegt jede "source ...". werte ist (vorher, jetzt) fuer die Balken."""
    s, s0 = stichtag(jetzt["week"]), stichtag(vorher["week"])
    k = []
    if jetzt.get("hashrate") and vorher.get("hashrate"):
        d = 100 * (jetzt["hashrate"] / vorher["hashrate"] - 1)
        k.append({"id": "hashrate", "kopf": "HASHRATE", "zahl": "%.0f PH/s" % jetzt["hashrate"],
                  "satz": "network hashrate, %+.1f%% against the week to %s" % (d, tag_kurz(s0)),
                  "quelle": "source kaspa rest api", "gewicht": abs(d), "stolz": d > 0,
                  "werte": (vorher["hashrate"], jetzt["hashrate"]), "fmt": lambda v: "%.0f PH/s" % v})
    if jetzt.get("holders") and vorher.get("holders"):
        n = jetzt["holders"] - vorher["holders"]
        k.append({"id": "holders", "kopf": "ADDRESSES", "zahl": ganz(jetzt["holders"]),
                  "satz": "addresses hold a meaningful balance, %s%s in a week"
                          % ("+" if n >= 0 else "", ganz(n)),
                  "quelle": "source kaspalytics address counts",
                  "gewicht": abs(100 * n / vorher["holders"]), "stolz": n > 0,
                  "werte": (vorher["holders"], jetzt["holders"]), "fmt": ganz})
    if jetzt.get("dormant_pct") and vorher.get("dormant_pct"):
        k.append({"id": "dormant", "kopf": "SLEEPING COINS", "zahl": "%.1f%%" % jetzt["dormant_pct"],
                  "satz": "of all KAS has not moved in a year",
                  "quelle": "source kaspalytics",
                  "gewicht": abs(jetzt["dormant_pct"] - vorher["dormant_pct"]), "stolz": True,
                  "werte": (vorher["dormant_pct"], jetzt["dormant_pct"]), "fmt": lambda v: "%.2f%%" % v})
    if jetzt.get("tvl_total") and vorher.get("tvl_total"):
        d = 100 * (jetzt["tvl_total"] / vorher["tvl_total"] - 1)
        k.append({"id": "tvl", "kopf": "LOCKED ON LAYER 2", "zahl": "$%.2fM" % (jetzt["tvl_total"] / 1e6),
                  "satz": "locked across kasplex and igra, %+.1f%% in a week" % d,
                  "quelle": "source defillama", "gewicht": abs(d), "stolz": d > 0,
                  "werte": (vorher["tvl_total"], jetzt["tvl_total"]), "fmt": lambda v: "$%.2fM" % (v / 1e6)})
    for x in k:
        x["woche"], x["woche_vorher"] = s, s0
        x["datum"] = "week to %s · %s" % (tag(s), x["quelle"])
    return k


def waehle(kand, anzahl=3):
    """Seite 1 ist die staerkste Zahl, die stolz macht, Seite 2 und 3 die
    naechsten. Eine fallende Zahl steht nie auf Seite 1."""
    stolz = sorted([x for x in kand if x["stolz"]], key=lambda x: -x["gewicht"])
    rest = sorted([x for x in kand if not x["stolz"]], key=lambda x: -x["gewicht"])
    return (stolz + rest)[:anzahl]


def haken(erste):
    """Der Haken-Satz ueber der groessten Zahl. Kein Versprechen ueber die
    Zahl hinaus: "than ever" waere ein Rekord, belegt ist nur die Vorwoche;
    gezaehlt werden Adressen, nicht Menschen."""
    return {"hashrate": "more work secured kaspa than a week before",
            "holders": "more addresses hold real KAS than a week ago",
            "dormant": "half of all KAS has not moved in a year",
            "tvl": "more money sits on kaspa layer 2 than a week ago"}[erste["id"]]


def seiten_woche(jetzt, vorher):
    k = waehle(kandidaten(jetzt, vorher))
    if len(k) < 3:
        raise Stopp("weniger als drei wochenzahlen in der ausgabe %s" % jetzt["week"])
    s = [dict(k[0], art="haken", haken=haken(k[0]))]
    s += [dict(x, art="zahl", balken=True) for x in k[1:3]]
    s.append({"art": "abbinder", "datum": "week to %s" % tag(stichtag(jetzt["week"]))})
    for i, x in enumerate(s):
        x["seite"], x["von"] = i + 1, len(s)
    return s


# ------------------------------------------------------------ story

def seiten_story(st, fuer=None):
    """Seiten aus der Story-Datei. Prueft, dass sie fuer diesen Mittwoch ist
    und dass jede Zahl Datum und Quelle traegt."""
    if fuer and st.get("mittwoch") != fuer:
        raise Stopp("story-datei ist fuer %s, nicht fuer %s" % (st.get("mittwoch"), fuer))
    inhalt = st.get("seiten") or []
    if not 3 <= len(inhalt) <= 4:
        raise Stopp("story braucht 3 oder 4 inhaltsseiten, hat %d" % len(inhalt))
    if not str(st.get("titel", "")).lower().startswith("the story of"):
        raise Stopp("titel beginnt nicht mit 'the story of'")
    try:
        stand = "as of %s" % tag(dt.date.fromisoformat(st.get("stand", "")).isoformat())
    except ValueError:
        raise Stopp("story-datei ohne gueltigen stand (JJJJ-MM-TT)")
    s = [{"art": "titel", "kopf": "THE STORY OF", "satz": st["titel"][len("the story of"):].strip(),
          "datum": "%s \u00b7 full explainer on YouTube" % stand}]
    for x in inhalt:
        if x.get("zahl") and not (x.get("datum") and x.get("quelle")):
            raise Stopp("story-seite %r hat eine zahl ohne datum oder quelle" % x.get("kopf"))
        teile = [t for t in (x.get("datum", "") or stand, x.get("quelle", "")) if t]
        s.append({"art": "gedanke", "kopf": x["kopf"].upper(), "satz": x["satz"], "zahl": x.get("zahl", ""),
                  "datum": " · ".join(teile), "quelle": x.get("quelle", "")})
    s.append({"art": "abbinder", "datum": "the story of %s, %s" % (s[0]["satz"], stand)})
    for i, x in enumerate(s):
        x["seite"], x["von"] = i + 1, len(s)
    return s


# ------------------------------------------------------------ html

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
.gedanke{position:absolute;left:60px;right:60px;font-family:'Archivo',sans-serif;font-weight:800;
  font-size:80px;line-height:1.06}
.datum{position:absolute;left:60px;right:60px;bottom:132px;font-family:'IBM Plex Mono',monospace;
  font-size:34px;line-height:1.28;color:%(text2)s;letter-spacing:-0.5px}
.gross{position:absolute;left:60px;right:60px;top:420px;font-family:'Archivo',sans-serif;font-weight:900;
  font-size:104px;line-height:1.02}
.folgen{position:absolute;left:60px;right:60px;top:800px;font-family:'Archivo',sans-serif;font-weight:800;
  font-size:72px;color:%(akzent)s}
.obj{position:absolute;left:0;top:0}
.sig{position:absolute;left:50%%;transform:translateX(-50%%);bottom:60px;height:48px;display:flex;
  align-items:center;gap:16px}
.sig svg{width:170px;height:48px;display:block}
"""


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" utc", " utc")


def balken(x, y, w, h, s, lk, look):
    """Zwei Balken ab null, Vorwoche im Restton, Woche im Akzent, jeder Wert
    darueber, das Datum darunter. Massstab ab null, damit +2.2% nicht nach
    Sprung aussieht."""
    vorher, jetzt = s["werte"]
    rest = BALKEN_REST.get(look, lk["rest"])
    oben, unten, bw, gap = 64, 52, 300, 120
    x0 = x + (w - 2 * bw - gap) / 2
    hi = max(vorher, jetzt)
    teile = []
    for i, (v, farbe, wann) in enumerate(((vorher, rest, s["woche_vorher"]), (jetzt, lk["akzent"], s["woche"]))):
        hs = max((h - oben - unten) * v / hi, 4)
        bx = x0 + i * (bw + gap)
        by = y + h - unten - hs
        textfarbe = lk["text2"] if i == 0 else lk["text"]
        teile.append("<rect x='%.1f' y='%.1f' width='%d' height='%.1f' rx='4' fill='%s'/>" % (bx, by, bw, hs, farbe))
        teile.append("<text x='%.1f' y='%.1f' fill='%s' font-size='40' font-weight='600' text-anchor='middle'>%s</text>"
                     % (bx + bw / 2, by - 16, textfarbe, esc(s["fmt"](v))))
        teile.append("<text x='%.1f' y='%.1f' fill='%s' font-size='34' text-anchor='middle'>week to %s</text>"
                     % (bx + bw / 2, y + h - 10, lk["text2"], esc(tag_kurz(wann))))
    return "".join(teile)


def seite_html(s, look):
    import look_takt
    import tagesgrafik as tg
    import wortmarke
    lk = look_takt.look(look)
    css = (look_takt.schriften_css()
           + CSS % {"grund": lk["grund"], "text": lk["text"], "text2": lk["text2"],
                    "akzent": lk["akzent"]}
           + wortmarke.css(look=look))
    sig = ("<div class='sig' data-rolle='fuss'>%s"
           "<svg viewBox='0 0 230 48'><path d='%s' fill='none' stroke='%s' stroke-width='3' "
           "stroke-linejoin='round' stroke-linecap='round'/></svg></div>"
           % (wortmarke.html(), tg.PULS, lk["markierung"]))
    nr = "<div class='nr'>%d/%d</div>" % (s["seite"], s["von"])
    datum = "<div class='datum'>%s</div>" % esc(s["datum"]) if s.get("datum") else ""

    def zahl_html(top):
        ziffern, einheit = tg.zahl_teilen(s["zahl"])
        zg = tg.zahlgroesse(s["zahl"])
        return zg, ("<div class='zahl' data-rolle='zahl' style='top:%dpx;font-size:%dpx'>%s%s</div>"
                    % (top, zg, esc(ziffern),
                       "<span class='einheit' data-rolle='einheit'>%s</span>" % esc(einheit) if einheit else ""))
    if s["art"] == "abbinder":
        innen = ("<div class='kopf' data-rolle='titel'>KASPA PULSE</div>%s"
                 "<div class='gross'>%s</div><div class='folgen'>%s</div>%s"
                 % (nr, esc(ABBINDER[0]), esc(ABBINDER[1]), datum))
    elif s["art"] == "titel":
        innen = ("<div class='kopf' data-rolle='titel'>THE STORY OF</div>%s"
                 "<div class='gross' style='top:300px;color:%s'>%s</div>%s"
                 % (nr, lk["akzent"], esc(s["satz"]), datum))
    elif s["art"] == "gedanke":
        innen = "<div class='kopf' data-rolle='titel'>%s</div>%s" % (esc(s["kopf"]), nr)
        top = 220
        if s.get("zahl"):
            zg, z = zahl_html(200)
            innen += z
            top = 200 + int(zg * 0.86) + 70
        innen += "<div class='gedanke' style='top:%dpx'>%s</div>%s" % (top, esc(s["satz"]), datum)
    else:
        top_zahl = 470 if s["art"] == "haken" else 200
        zg, z = zahl_html(top_zahl)
        top_satz = top_zahl + int(zg * 0.86) + 56
        innen = ("<div class='kopf' data-rolle='titel'>%s</div>%s%s%s<div class='satz' style='top:%dpx'>%s</div>%s"
                 % ("THE WEEK IN NUMBERS" if s["art"] == "haken" else esc(s["kopf"]), nr,
                    "<div class='haken'>%s</div>" % esc(s["haken"]) if s["art"] == "haken" else "",
                    z, top_satz, esc(s["satz"]), datum))
        if s.get("balken"):
            y = top_satz + 150
            innen += ("<svg class='obj' width='1080' height='1350' viewBox='0 0 1080 1350' "
                      "font-family='IBM Plex Sans'>%s</svg>" % balken(60, y, 960, BALKEN_UNTEN - y, s, lk, look))
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s</style></head>"
            "<body data-look='%s'>%s%s</body></html>" % (css, look, innen, sig))


# ------------------------------------------------------------ caption, texte

FRAGEN = ("which of these numbers would you have guessed?",
          "which number should we follow next week?",
          "did any of these surprise you?")


def caption(haken, satz, frage, tags=TAGS):
    """Die fuenf Bloecke in Bens Reihenfolge."""
    return "\n\n".join([haken.rstrip(" .") + ".", satz.rstrip(" .") + ".", frage, ZEILE_BIO, tags])


def caption_woche(ss, nummer=0):
    zeilen = [x for x in ss if x["art"] in ("haken", "zahl")]
    quellen = []
    for x in zeilen:
        q = "kaspalytics" if "kaspalytics" in x["quelle"] else x["quelle"].replace("source ", "")
        if q not in quellen:
            quellen.append(q)
    erste = zeilen[0]
    weitere = " and ".join(x["kopf"].lower() for x in zeilen[1:])
    return caption("%s %s" % (erste["zahl"], erste["satz"]),
                   "the week in numbers, with %s inside, week to %s, source %s"
                   % (weitere, tag(erste["woche"]), " and ".join(quellen)),
                   FRAGEN[nummer % len(FRAGEN)])


def caption_story(st, ss):
    # der haken traegt die erste zahl der story mit ihrer quelle
    gedanken = [x for x in ss if x["art"] == "gedanke"]
    mit_zahl = [x for x in gedanken if x.get("zahl")]
    titel = st["titel"][len("the story of"):].strip()
    if mit_zahl:
        x = mit_zahl[0]
        haken = "%s, %s" % (x["zahl"], x["satz"])
        satz = "the story of %s, %s, full explainer on YouTube" % (titel, x["datum"].replace(" \u00b7 ", ", "))
    else:
        haken = st["titel"]
        satz = "%s, full explainer on YouTube" % ss[0]["datum"].split(" \u00b7 ")[0]
    return caption(haken, satz, st.get("frage") or "what would you add to this story?")


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
        if re.search(r"\b(?:than ever|ever before|all.time|record|people)\b", t, re.I):
            fehler.append("versprechen ueber die zahl hinaus in %r" % t[:50])
    return fehler


def caption_pruefen(c):
    """Content-Regeln fuer die Caption (Ben, 25.10.2026). Jeder Block geht
    einzeln durch die Textwachen, damit "counted" in einem Block und eine
    fremde Quelle in einem anderen nicht verwechselt werden."""
    import content_wache
    bloecke = c.split("\n\n")
    fehler = []
    for b in bloecke[:3]:
        fehler += text_pruefen([b])
    if re.search(r"https?://|www\.|\.com\b|\.org\b|youtu\.be|youtube\.com", c, re.I):
        fehler.append("link in der caption")
    if len(bloecke) != 5:
        return fehler + ["caption hat %d bloecke, richtig sind 5 (haken, satz, frage, newsletter, hashtags)"
                         % len(bloecke)]
    haken, satz, frage, bio, tags = bloecke
    if not re.search(r"\d", haken):
        fehler.append("haken ohne zahl")
    if haken.count(". ") or satz.count(". "):
        fehler.append("haken und satz sind je ein satz")
    if not frage.endswith("?") or frage.count("?") != 1:
        fehler.append("block 3 ist nicht genau eine frage")
    if bio != ZEILE_BIO:
        fehler.append("block 4 ist nicht die newsletter-zeile")
    t = tags.split()
    if not 1 <= len(t) <= MAX_TAGS or not all(re.fullmatch(r"#[a-z0-9]+", x) for x in t):
        fehler.append("block 5 hat %d hashtags oder anderes, erlaubt 1 bis %d" % (len(t), MAX_TAGS))
    if "#" in " ".join(bloecke[:4]):
        fehler.append("hashtag ausserhalb des letzten blocks")
    if not content_wache.DATUM.search(haken + " " + satz):
        fehler.append("caption ohne datum")
    if not re.search(r"\bsource\b|counted by kaspa pulse", haken + " " + satz, re.I):
        fehler.append("caption ohne quelle")
    if len(c) > 2200:
        fehler.append("caption hat %d zeichen, erlaubt 2200" % len(c))
    return fehler


def seiten_texte(ss):
    return [x[k] for x in ss for k in ("haken", "satz", "datum", "zahl", "kopf") if x.get(k)] + list(ABBINDER)


# ------------------------------------------------------------ bauen, senden

def naechster(wochentag, heute=None):
    """Das naechste Datum mit diesem Wochentag (0 = montag), ab morgen."""
    heute = heute or dt.date.today()
    d = heute + dt.timedelta(days=1)
    while d.weekday() != wochentag:
        d += dt.timedelta(days=1)
    return d.isoformat()


def vorbereiten(art, fuer, history=None, story=None):
    if art == "woche":
        h = json.loads(Path(history or HISTORY).read_text(encoding="utf-8"))
        jetzt, vorher = ausgaben_fuer(h, fuer)
        ss = seiten_woche(jetzt, vorher)
        cap = caption_woche(ss)
    else:
        st = json.loads(Path(story or STORY).read_text(encoding="utf-8"))
        ss = seiten_story(st, fuer)
        cap = caption_story(st, ss)
    fehler = text_pruefen(seiten_texte(ss)) + caption_pruefen(cap) + deckblatt_pruefen(ss)
    if fehler:
        raise Stopp("textpruefung, %s" % "; ".join(fehler))
    return ss, cap


def rendern(art, fuer, ss, looks, out, motiv=None):
    """motiv: das Hintergrundmotiv aus dem Raster (look_takt.raster_motiv),
    alle Seiten eines Karussells tragen dasselbe."""
    import hintergrund
    import tagesgrafik as tg
    from playwright.sync_api import sync_playwright
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    bilder = []
    with sync_playwright() as p:
        b = tg.chromium_start(p)
        try:
            for lk in looks:
                for s in ss:
                    png = out / ("karussell-%s-%s-%d-%s.png" % (art, fuer, s["seite"], lk))
                    seite = seite_html(s, lk)
                    if motiv:
                        seite = hintergrund.setzen(seite, motiv, lk)
                    tg.rendern(seite, png, 0, b, "instagram")
                    bilder.append(png)
        finally:
            b.close()
    return bilder


def veto_satz(art, fuer):
    """Der Satz im Entwurf (Ben, 25.10.2026). Das Veto ist die Variable
    KARUSSELL_STOPP, wie IG_STOPP bei der Tagesgrafik."""
    return ("geht um %s raus, Veto: karussell-stopp (Variable KARUSSELL_STOPP auf %s oder immer)"
            % (POSTZEIT[art][1], fuer))


def deckblatt_pruefen(ss):
    """Nie zwei Diagramme nebeneinander (Ben, 25.10.2026). Im Profilraster
    steht nur Seite 1, neben der Tagesgrafik, die oft ein Diagramm ist.
    Seite 1 traegt deshalb nie ein Diagramm, und keine Seite mehr als eins."""
    fehler = []
    if ss and ss[0].get("balken"):
        fehler.append("seite 1 traegt ein diagramm, im raster stuende es neben der tagesgrafik")
    return fehler


def ops_senden(hook, art, fuer, look, bilder, cap, vor=""):
    """Der Entwurf nach #moderator-only, Text und alle Seiten in einer Nachricht."""
    import look_takt
    inhalt = (vor + "%sENTWURF karussell %s fuer %s, look %s, %d seiten in der reihenfolge der bilder, ohne musik.\n"
              "%s\n\nCAPTION\n```\n%s\n```"
              % ("TROCKENLAUF (ZIEL=moderator). " if look_takt.trockenlauf() else "",
                 art, fuer, look, len(bilder), veto_satz(art, fuer), cap))[:1990]
    grenze = "----ka" + uuid.uuid4().hex
    teile = [("--%s\r\nContent-Disposition: form-data; name=\"payload_json\"\r\nContent-Type: application/json"
              "\r\n\r\n" % grenze).encode()
             + json.dumps({"content": inhalt, "allowed_mentions": {"parse": []}}).encode() + b"\r\n"]
    for i, p in enumerate(bilder[:10]):
        teile.append(("--%s\r\nContent-Disposition: form-data; name=\"files[%d]\"; filename=\"%s\"\r\n"
                      "Content-Type: image/png\r\n\r\n" % (grenze, i, Path(p).name)).encode()
                     + Path(p).read_bytes() + b"\r\n")
    body = b"".join(teile) + ("--%s--\r\n" % grenze).encode()
    req = urllib.request.Request(hook, data=body, headers={
        "Content-Type": "multipart/form-data; boundary=%s" % grenze, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        print("entwurf an ops geschickt, http %s" % r.status)


def entwurf(art, fuer, out, senden=False, alle_looks=False, look="", speicher_pfad=None):
    """Baut den Entwurf im Look aus dem Raster-Takt. Mit senden geht er nach
    #moderator-only und der Takt wird gemerkt (die Bilder tragen diesen Look,
    Ben postet genau sie)."""
    import look_takt
    ss, cap = vorbereiten(art, fuer)
    sp = look_takt.lesen(speicher_pfad)
    lk = look or look_takt.raster_faellig(sp, "karussell", fuer)[1]
    looks = ("dunkel", "hell", "teal") if alle_looks else (lk,)
    bilder = rendern(art, fuer, ss, looks, out, look_takt.raster_motiv(sp, "karussell", fuer))
    Path(out, "karussell-%s-%s-caption.txt" % (art, fuer)).write_text(cap + "\n", encoding="utf-8")
    if senden:
        hook = os.environ.get("DISCORD_WEBHOOK_OPS", "")
        if not hook:
            raise Stopp("kein DISCORD_WEBHOOK_OPS, nichts geschickt")
        ops_senden(hook, art, fuer, lk, [b for b in bilder if b.stem.endswith("-" + lk)], cap)
        look_takt.raster_merken(sp, "karussell", fuer)
        look_takt.schreiben(sp, speicher_pfad)
    return ss, cap, bilder, lk


# ------------------------------------------------------------ selbsttest

PROBE_STORY = {
    # nur fuer den selbsttest und den kontaktbogen, nie veroeffentlicht
    "mittwoch": "2026-10-28", "stand": "2026-10-22", "titel": "the story of the monthly reward cut",
    "seiten": [
        {"kopf": "every month", "satz": "kaspa pays miners a little less each month, by design"},
        {"kopf": "the step", "satz": "the reward per block fell to this on 5 oct", "zahl": "2.06 KAS",
         "datum": "5 oct 2026", "quelle": "counted by kaspa pulse from the emission schedule"},
        {"kopf": "half in a year", "satz": "a year of steps leaves the reward at half of what it was"},
        {"kopf": "why it matters", "satz": "new supply shrinks on a fixed path that anyone can check"}],
    "frage": "did you know the cut comes every month?"}


def selbsttest():
    fehler = 0

    def ok(name, bed):
        nonlocal fehler
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        fehler += 0 if bed else 1

    a = {"week": "2026-10-05", "hashrate": 354.49, "holders": 800919.0, "dormant_pct": 50.62,
         "tvl_total": 1386405.34}
    b = {"week": "2026-10-12", "hashrate": 362.36, "holders": 802817.0, "dormant_pct": 51.3,
         "tvl_total": 1244205.59}
    ss = seiten_woche(b, a)
    ok("vier seiten, die letzte ist der abbinder", len(ss) == 4 and ss[-1]["art"] == "abbinder")
    ok("seite 1 ist eine zahl, die stolz macht (%s)" % ss[0]["id"], ss[0]["stolz"] and ss[0]["id"] != "tvl")
    ok("jede seite traegt week to 10 oct 2026", all("week to 10 oct 2026" in x["datum"] for x in ss))
    ok("seite 2 und 3 mit balken, vorwoche gegen woche",
       all(x.get("balken") and len(x["werte"]) == 2 for x in ss[1:3]))
    ok("stichtag ist der samstag vor der ausgabe", stichtag("2026-10-12") == "2026-10-10")
    ok("ausgabe fuer sa 17.10. ist die vom 12.10.",
       ausgaben_fuer([a, b], "2026-10-17")[0]["week"] == "2026-10-12")
    try:
        ausgaben_fuer([a, b], "2026-10-24")
        ok("ohne montagsausgabe der woche kein entwurf", False)
    except Stopp:
        ok("ohne montagsausgabe der woche kein entwurf", True)
    ok("texte halten die wachen", not text_pruefen(seiten_texte(ss)))
    c = caption_woche(ss)
    ok("caption nach den content-regeln (%s)" % "; ".join(caption_pruefen(c)), not caption_pruefen(c))
    bl = c.split("\n\n")
    ok("fuenf bloecke, haken mit zahl, frage an dritter stelle, newsletter, hashtags",
       len(bl) == 5 and re.search(r"\d", bl[0]) and bl[2].endswith("?") and bl[3] == ZEILE_BIO
       and bl[4].startswith("#"))
    ok("sechs hashtags fallen auf", bool(caption_pruefen(c.replace(TAGS, TAGS + " #a #b #c"))))
    ok("caption ohne quelle faellt auf", bool(caption_pruefen(c.replace("source ", "from "))))
    ok("deckblatt ohne diagramm", not deckblatt_pruefen(ss) and bool(deckblatt_pruefen(ss[1:])))
    ok("entwurf nennt postzeit und veto", veto_satz("woche", "2026-10-31")
       .startswith("geht um 11:00 raus, Veto: karussell-stopp"))
    ok("caption mit link faellt auf", bool(caption_pruefen(c + " kaspapulse.com/ig")))
    ok("echtzeit faellt auf", bool(text_pruefen(["hashrate right now at 360 PH/s on 10 oct"])))
    ok("counted bei fremder quelle faellt auf", bool(text_pruefen(["week to 10 oct, counted · source defillama"])))
    ok("than ever faellt auf", bool(text_pruefen(["more work than ever on 10 oct"])))
    ok("kein haken verspricht einen rekord", not text_pruefen([haken(x) for x in kandidaten(b, a)]))
    st = seiten_story(PROBE_STORY, "2026-10-28")
    ok("story mit titel, vier gedanken und abbinder", len(st) == 6 and st[0]["art"] == "titel"
       and st[-1]["art"] == "abbinder")
    ok("jede story-seite traegt ein datum", all(re.search(r"\d{1,2} [a-z]{3} \d{4}", x["datum"]) for x in st))
    ok("story-texte halten die wachen", not text_pruefen(seiten_texte(st)))
    cs = caption_story(PROBE_STORY, st)
    ok("story-caption nennt das video ohne link (%s)" % "; ".join(caption_pruefen(cs)),
       "full explainer on YouTube" in cs and not caption_pruefen(cs))
    for name, kaputt in (("falscher mittwoch", dict(PROBE_STORY, mittwoch="2026-10-21")),
                         ("zahl ohne quelle", dict(PROBE_STORY, seiten=[dict(PROBE_STORY["seiten"][1], quelle="")]
                                                   + PROBE_STORY["seiten"][:3])),
                         ("zu viele seiten", dict(PROBE_STORY, seiten=PROBE_STORY["seiten"] * 2)),
                         ("fehlender stand", dict(PROBE_STORY, stand=""))):
        try:
            seiten_story(kaputt, "2026-10-28")
            ok("story stoppt bei %s" % name, False)
        except Stopp:
            ok("story stoppt bei %s" % name, True)
    ok("naechster samstag nach freitag 23.10. ist der 24.10.",
       naechster(5, dt.date(2026, 10, 23)) == "2026-10-24")
    print("%d fehler" % fehler)
    return 1 if fehler else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("art", nargs="?", choices=["woche", "story"])
    ap.add_argument("--fuer", default="", help="post-datum JJJJ-MM-TT, ohne: der naechste sa bzw. mi")
    ap.add_argument("--out", default="graphics/karussell")
    ap.add_argument("--look", default="", help="ohne: der look aus dem raster-takt")
    ap.add_argument("--alle-looks", action="store_true", help="fuer den kontaktbogen")
    ap.add_argument("--story", default="", help="story-datei, ohne: data/karussell-story.json")
    ap.add_argument("--senden", action="store_true", help="entwurf nach #moderator-only, takt merken")
    ap.add_argument("--selbsttest", "--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if not a.art:
        ap.print_help()
        return 2
    global STORY
    if a.story:
        STORY = Path(a.story)
    fuer = a.fuer or naechster(5 if a.art == "woche" else 2)
    try:
        ss, cap, bilder, lk = entwurf(a.art, fuer, a.out, a.senden, a.alle_looks, a.look)
    except Exception as exc:                      # Stopp hier, Stop aus der bild-wache
        if type(exc).__name__ not in ("Stopp", "Stop"):
            raise
        print("ABBRUCH %s" % exc)
        return 1
    print("karussell %s fuer %s, look %s\n%s\n\nCAPTION\n%s" % (a.art, fuer, lk, "\n".join(map(str, bilder)), cap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
