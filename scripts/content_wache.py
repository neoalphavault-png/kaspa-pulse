#!/usr/bin/env python3
"""content_wache.py, die eine Wache fuer alle Bild-Generatoren (Ben, 15.10.2026).

Jeder Generator ruft pruefe_seite() auf der fertig gerenderten Seite auf, in
demselben Chromium, das auch den Screenshot macht. Gemessen wird also das,
was im Bild steht, nicht das, was im Code steht. Ein Verstoss stoppt den
Lauf mit einer Meldung, die jeden Verstoss beim Namen nennt.

GROESSEN UND FLAECHEN (PROFILE). Je Kanal Titel, grosse Zahl, Kleintext und
die sichere Flaeche aus Bens Tabelle. Die Rolle eines Textes steht im HTML
als data-rolle: "titel", "zahl", "fuss", "einheit" (die kleine Einheit neben
einer grossen Zahl, misst als Kleintext). Alles ohne Rolle ist Kleintext.
Die Schriftgroesse wird am Bildschirm gelesen, in SVG mit dem Massstab der
Zeichenflaeche.

  Feed (instagram, threads)  1080x1350  Titel 64, Zahl 200, klein 34, Rand 60,
                                        Fusszeile nicht in den Ecken
  Story                      1080x1920  Titel 80, Zahl 220, klein 40,
                                        Text nur in x 60..900, y 270..1500
  X                          1600x900   Titel 72, Zahl 240, klein 36, Rand 60
  Discord                    1200x1200  Titel 64, Zahl 200, klein 32, Rand 60

  Bis die eigenen Formate kommen, laufen X und Discord in 1080x1350. Dann gilt
  "uebergang": die Feed-Groessen und der Rand, ohne die Fusszeilen-Regel
  (Ben, 16.10.2026).

Der Rand wird zweimal geprueft: jeder Text muss in der Flaeche liegen, und im
Feed muss der Streifen von 60 px rundum im Bild selbst Hintergrund sein
(Pixel aus dem Screenshot, im Browser gelesen, ohne Pillow).

SICHTBARER TEXT. Jeder Text, der im Bild steht, geht durch
number_of_day.assert_punctuation, die schon bestehende Wache: kein
Gedankenstrich, kein Doppelpunkt, kein Pfeil (Uhrzeiten und Links
ausgenommen), "%" statt "percent". Die Echtzeit-Regel ist dieselbe wie im
Sammel-PR #109 (Liste aus tagesgrafik.ECHTZEIT plus right now, currently, at
the moment, as we speak, this second, bewusst ohne "the second" und "the
moment"). Ist #109 gemergt, nimmt diese Datei den Ausdruck von dort; bis
dahin steht derselbe Ausdruck hier, und der Selbsttest prueft, dass beide
gleich sind. Neu hier sind nur die ASCII-Pfeile (-> und =>), die
assert_punctuation nicht kennt, und die Kursziele.

JEDE ZAHL MIT DATUM. Steht im Bild eine Ziffer, muss im Bild auch ein Datum
stehen ("16 oct", "oct 16 2026").

    python3 scripts/content_wache.py --selbsttest
    python3 scripts/content_wache.py --text "up 5 percent right now"
"""
import argparse
import base64
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PROFILE = {
    "feed":      {"w": 1080, "h": 1350, "titel": 64, "zahl": 200, "klein": 34,
                  "flaeche": (60, 60, 1020, 1290), "rahmen": 60, "fuss_mitte": True},
    "story":     {"w": 1080, "h": 1920, "titel": 80, "zahl": 220, "klein": 40,
                  "flaeche": (60, 270, 900, 1500), "rahmen": 0, "fuss_mitte": False},
    "x":         {"w": 1600, "h": 900, "titel": 72, "zahl": 240, "klein": 36,
                  "flaeche": (60, 60, 1540, 840), "rahmen": 60, "fuss_mitte": False},
    "discord":   {"w": 1200, "h": 1200, "titel": 64, "zahl": 200, "klein": 32,
                  "flaeche": (60, 60, 1140, 1140), "rahmen": 60, "fuss_mitte": False},
    "uebergang": {"w": 1080, "h": 1350, "titel": 64, "zahl": 200, "klein": 34,
                  "flaeche": (60, 60, 1020, 1290), "rahmen": 60, "fuss_mitte": False},
}
KANAL_PROFIL = {"instagram": "feed", "threads": "feed", "story": "story", "x": "x",
                "discord": "discord"}

# Die Echtzeit-Regel aus #109, wortgleich. Nach dem Merge gewinnt der
# Ausdruck in number_of_day.py, dieser Ersatz kann dann weg.
_ECHTZEIT_109 = (r"\b(?:right now|currently|at the moment|as we speak|this second|live|"
                 r"real[- ]?time|around the clock|every minute|instant|instantly|24/7|"
                 r"now)\b")
PFEILE = ("->", "=>", "←", "↑", "↓", "⇒", "⟶")
KURSZIEL = re.compile(r"\b(?:price targets?|target price|kursziel|price prediction|to the moon|"
                      r"will (?:hit|reach|go to|touch)|heading (?:to|for) \$?\d|next stop \$?\d)",
                      re.I)
# Platzhalter (Ben, 17.10.2026): ein Bild mit Vorlagentext geht nie raus.
PLATZHALTER = re.compile(r"platzhalter|placeholder|lorem ipsum|\bTODO\b|\bTBD\b|\bFIXME\b|\bxxx+\b|"
                         r"\{\{|\}\}|<name>|\bname here\b", re.I)
DATUM = re.compile(r"\b\d{1,2} (?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b|"
                   r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec) \d{1,2}\b", re.I)


class WacheStopp(ValueError):
    """Ein Verstoss. Der Text nennt jeden einzelnen."""


def echtzeit_ausdruck():
    import number_of_day
    return getattr(number_of_day, "_ECHTZEIT", None) or re.compile(_ECHTZEIT_109, re.I)


def profil(kanal, w, h):
    """Das Profil fuer einen Kanal bei dieser Bildgroesse. X und Discord in
    1080x1350 sind der Uebergang bis zum Format-PR."""
    name = KANAL_PROFIL.get(kanal)
    if name is None:
        raise WacheStopp("unbekannter kanal %r" % kanal)
    p = PROFILE[name]
    if (p["w"], p["h"]) == (w, h):
        return name, p
    if kanal in ("x", "discord") and (w, h) == (1080, 1350):
        return "uebergang", PROFILE["uebergang"]
    raise WacheStopp("%s erwartet %dx%d, das bild ist %dx%d" % (kanal, p["w"], p["h"], w, h))


# ------------------------------------------------------------ text

# Ungenaue Mengenwoerter (Ben, 28.10.2026): "real KAS" und "meaningful"
# behaupten eine Schwelle, ohne sie zu nennen. Eine Adressenzahl traegt ihre
# Schwelle, etwa "addresses with at least 100 KAS".
UNGENAU = re.compile(r"\breal\s+kas\b|\bmeaningful\b", re.I)


def ungenau(text):
    m = UNGENAU.search(text or "")
    return ["ungenau %r, die schwelle nennen" % m.group(0)] if m else []


def ungenau_im_quelltext(ordner=None):
    """Jeder Text in einem Generator (Zeichenketten in scripts/*.py), der
    "real KAS" oder "meaningful" traegt. Kaspalytics-Pfade wie
    address/count/meaningful-balance sind Namen der Quelle, kein Text im Bild.
    Docstrings sind Doku, kein Ausgabetext, und zaehlen nicht."""
    import io
    import tokenize
    ordner = Path(ordner or Path(__file__).resolve().parent)
    funde = []
    for datei in sorted(ordner.glob("*.py")):
        try:
            toks = list(tokenize.generate_tokens(io.StringIO(datei.read_text(encoding="utf-8")).readline))
        except (tokenize.TokenError, SyntaxError, UnicodeDecodeError):
            continue
        for t in toks:
            if t.type != tokenize.STRING:
                continue
            if t.string.lstrip("rbuRBU")[:3] in ('"' * 3, "'" * 3):
                continue
            if datei.name == "content_wache.py" and "UNGENAU" in t.line:
                continue
            roh = re.sub(r"[\w/.?=-]*meaningful-balance[\w/.?=-]*", "", t.string)
            if UNGENAU.search(roh):
                funde.append("%s:%d" % (datei.name, t.start[0]))
    return funde


# Die Antwort unter dem X-Post (Ben, 31.10.2026). Solange @gokugalax das
# Label von X traegt, steht dort kein Link und keine Domain, auch nicht
# kaspapulse.com/x. Und sie nennt keine Zahl, die schon im Bild oder im Post
# steht: sie loest auf, sie wiederholt nicht.
LINK_ODER_DOMAIN = re.compile(
    r"(https?://\S+|\bwww\.\S+|\b[a-z0-9][a-z0-9-]*\.(?:com|io|org|net|de|xyz|html|app|dev|info|co|ai|fi)\b"
    r"(?:/\S*)?|\blink in (?:the )?bio\b)", re.I)
# Eine Kennzahl ist eine Zahl mit Komma, Dezimalstelle, % oder Kurzform
# (M, B, x), oder eine ganze Zahl ab drei Stellen. Kleine ganze Zahlen wie
# "8 hours", "10 minutes" oder "1 in 18" sind Fenster und Masse, keine Kennzahl.
# Jahreszahlen und Tage mit Monat zaehlen nicht.
_MONAT = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
_KENNZAHL = re.compile(r"(?<![\w.])[+]?(\d{1,3}(?:,\d{3})+|\d+\.\d+|\d{3,})(%|[mbkx]\b)?", re.I)
_DATUM_WEG = re.compile(r"\b\d{1,2} " + _MONAT + r"\b|\b" + _MONAT + r" \d{4}\b|\b20\d\d\b|\b\d{1,2}:\d{2}\b", re.I)


def kennzahlen(text):
    """Die Kennzahlen eines Textes, vereinheitlicht (ohne + und %)."""
    t = _DATUM_WEG.sub(" ", LINK_ODER_DOMAIN.sub(" ", text or ""))
    return {m.group(1) + (m.group(2) or "").lower().replace("%", "") for m in _KENNZAHL.finditer(t)}


def antwort_verstoesse(antwort, gesehen, label=True):
    """antwort ist der Text unter dem X-Post, gesehen alle Texte aus Bild und
    Post. label True heisst: X hat das Label gesetzt, also kein Link."""
    aus = []
    if label:
        aus += ["link oder domain %r in der antwort, solange das x-label gilt" % m.group(0)
                for m in LINK_ODER_DOMAIN.finditer(antwort or "")]
    doppelt = kennzahlen(antwort) & kennzahlen(" ".join(gesehen))
    if doppelt:
        aus.append("die antwort wiederholt %s aus bild oder post" % ", ".join(sorted(doppelt)))
    return aus


def ohne_wiederholung(text, gesehen):
    """Laesst aus text die Teilsaetze weg, die eine Kennzahl aus gesehen
    wiederholen. Teilsaetze trennt ein Komma, Saetze ein Punkt."""
    schon = kennzahlen(" ".join(gesehen))
    saetze = []
    for satz in re.split(r"(?<=\.)\s+", (text or "").strip()):
        ende = "." if satz.endswith(".") else ""
        alle = (satz[:-1] if ende else satz).split(", ")
        teile = [t for t in alle if not (kennzahlen(t) & schon)]
        if len(teile) < len(alle):
            # was nach dem streichen nur noch ein datum ist ("as of 28 sep"), faellt mit
            teile = [t for t in teile if re.sub(r"\b(as|of|on|in|at|utc|to|from)\b", " ",
                                                 _DATUM_WEG.sub(" ", t)).strip(" ,.")]
        if not teile:
            continue
        if teile[0].startswith("and "):
            teile[0] = teile[0][4:]
        saetze.append(", ".join(teile) + ende)
    return " ".join(saetze)


def text_verstoesse(text):
    """Die Textregeln fuer einen sichtbaren Text. Leere Liste heisst gruen."""
    import number_of_day
    aus = []
    try:
        number_of_day.assert_punctuation(text, "bild")
    except ValueError as exc:
        aus.append(str(exc).split(" in '")[0].split(' in "')[0])
    probe = number_of_day._strip_technical(text)
    m = echtzeit_ausdruck().search(probe)
    if m and not any("realtime" in a for a in aus):
        aus.append("echtzeit-wort %r" % m.group(0))
    for p in PFEILE:
        if p in probe:
            aus.append("pfeil %r" % p)
    aus += ungenau(probe)
    m = KURSZIEL.search(text)
    if m:
        aus.append("kursziel %r" % m.group(0))
    m = PLATZHALTER.search(text)
    if m:
        aus.append("platzhalter %r" % m.group(0))
    return aus


def seite_text_verstoesse(texte):
    """Alle Texte eines Bildes, dazu die Datumsregel fuer das ganze Bild."""
    aus = []
    for t in texte:
        for v in text_verstoesse(t):
            aus.append("%s in %r" % (v, t[:60]))
    alles = " ".join(texte)
    if re.search(r"\d", alles) and not DATUM.search(alles):
        aus.append("zahl ohne datum, im bild steht kein tag mit monat")
    return aus


# ------------------------------------------------------------ messen

MESS_JS = """() => {
  const aus = [];
  const rolle = e => { const r = e.closest('[data-rolle]'); return r ? r.dataset.rolle : ''; };
  const sichtbar = e => { const s = getComputedStyle(e); return s.display != 'none' && s.visibility != 'hidden' && parseFloat(s.opacity) > 0; };
  for (const e of document.querySelectorAll('body *')) {
    if (e.closest('svg') && !(e instanceof SVGTextElement)) continue;
    if (!sichtbar(e)) continue;
    let text = '', massstab = 1, rects = [];
    if (e instanceof SVGTextElement) {
      text = e.textContent.trim();
      const m = e.getScreenCTM(); massstab = m ? Math.hypot(m.a, m.b) : 1;
      rects = [e.getBoundingClientRect()];
    } else {
      const knoten = [...e.childNodes].filter(n => n.nodeType == 3 && n.textContent.trim());
      if (!knoten.length) continue;
      text = knoten.map(n => n.textContent.trim()).join(' ');
      for (const n of knoten) { const r = document.createRange(); r.selectNodeContents(n); rects.push(...r.getClientRects()); }
    }
    if (!text) continue;
    const groesse = parseFloat(getComputedStyle(e).fontSize) * massstab;
    const r = rects.filter(q => q.width > 0 && q.height > 0);
    if (!r.length) continue;
    aus.push({text, rolle: rolle(e), groesse,
              links: Math.min(...r.map(q => q.left)), rechts: Math.max(...r.map(q => q.right)),
              oben: Math.min(...r.map(q => q.top)), unten: Math.max(...r.map(q => q.bottom))});
  }
  const fuss = document.querySelector('[data-rolle=fuss]');
  const f = fuss ? fuss.getBoundingClientRect() : null;
  return {texte: aus, fuss: f ? {links: f.left, rechts: f.right, oben: f.top, unten: f.bottom} : null,
          grund: getComputedStyle(document.body).backgroundColor};
}"""

RAHMEN_JS = """async ([daten, rand, grund]) => {
  const img = new Image(); img.src = daten; await img.decode();
  const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
  const g = c.getContext('2d'); g.drawImage(img, 0, 0);
  const d = g.getImageData(0, 0, c.width, c.height).data;
  const [r0, g0, b0] = grund.match(/\\d+/g).map(Number);
  const treffer = {oben: 0, unten: 0, links: 0, rechts: 0};
  for (let y = 0; y < c.height; y += 2) for (let x = 0; x < c.width; x += 2) {
    const seite = y < rand - 2 ? 'oben' : y >= c.height - rand + 2 ? 'unten'
                : x < rand - 2 ? 'links' : x >= c.width - rand + 2 ? 'rechts' : '';
    if (!seite) continue;
    const i = (y * c.width + x) * 4;
    if (Math.abs(d[i] - r0) + Math.abs(d[i + 1] - g0) + Math.abs(d[i + 2] - b0) > 24) treffer[seite]++;
  }
  return treffer;
}"""


def groessen_verstoesse(messung, p):
    aus = []
    x0, y0, x1, y1 = p["flaeche"]
    for t in messung["texte"]:
        rolle, g, kurz = t["rolle"], t["groesse"], t["text"][:40]
        mindest = p["titel"] if rolle == "titel" else p["zahl"] if rolle == "zahl" else p["klein"]
        name = rolle if rolle in ("titel", "zahl") else "kleintext"
        if g < mindest - 0.5:
            aus.append("%s %r hat %.0f px, mindestens %d" % (name, kurz, g, mindest))
        if t["links"] < x0 - 1 or t["rechts"] > x1 + 1 or t["oben"] < y0 - 1 or t["unten"] > y1 + 1:
            aus.append("%r liegt ausserhalb der sicheren flaeche (%d..%d x %d..%d), bei %d..%d x %d..%d" % (
                kurz, x0, x1, y0, y1, t["links"], t["rechts"], t["oben"], t["unten"]))
    if p["fuss_mitte"]:
        f = messung.get("fuss")
        if f is None:
            aus.append("keine fusszeile (data-rolle=fuss)")
        elif f["links"] < p["w"] * 0.15 or f["rechts"] > p["w"] * 0.85:
            aus.append("fusszeile reicht in eine ecke (%d..%d px)" % (f["links"], f["rechts"]))
    return aus


# Der Hintergrund darf die Aussage nie stoeren (Ben, 29.10.2026). Deko ist
# alles, was keine Aussage traegt: die alte Motiv-Ebene von hintergrund.py
# und jedes Element mit data-deko. Die Wache blendet die Deko aus und
# vergleicht: im Daten-Bereich (Zahlen, Texte, Balken, Achsen, plus freier
# Rand) darf sich kein Pixel aendern. Sonst wird nicht gesendet.
DEKO_SEL = ".hg-ebene, [data-deko]"
DEKO_RAND = 24
DATEN_JS = """(rand) => {
  const sel = '[data-rolle], .zahl, .t, svg.obj rect, svg.obj text, svg.obj path, svg.obj line, '
            + 'svg.obj circle, svg.obj polyline, svg.obj polygon, table';
  const aus = [];
  for (const e of document.querySelectorAll(sel)) {
    if (e.closest('.hg-ebene, [data-deko]')) continue;
    const r = e.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    aus.push([Math.max(0, r.left - rand), Math.max(0, r.top - rand), r.right + rand, r.bottom + rand]);
  }
  return aus;
}"""


def deko_verstoesse(page, rand=DEKO_RAND, schwelle=12):
    """Deko-Ebene aus, Aussage gleich: kein geaenderter Pixel im Daten-Bereich."""
    import io
    n = page.evaluate("(s) => document.querySelectorAll(s).length", DEKO_SEL)
    if not n:
        return []
    from PIL import Image, ImageChops
    flaechen = page.evaluate(DATEN_JS, rand)
    text_mit = page.evaluate("() => document.body.innerText")
    mit = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    page.add_style_tag(content="%s{visibility:hidden !important}" % DEKO_SEL)
    ohne = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    text_ohne = page.evaluate("() => document.body.innerText")
    page.add_style_tag(content="%s{visibility:visible !important}" % DEKO_SEL)
    aus = []
    if text_mit != text_ohne:
        aus.append("ohne deko aendert sich der text")
    diff = ImageChops.difference(mit, ohne).convert("L").point(lambda v: 255 if v > schwelle else 0)
    treffer = 0
    for l, t, r, b in flaechen:
        box = (int(l), int(t), min(int(r) + 1, mit.width), min(int(b) + 1, mit.height))
        if box[2] > box[0] and box[3] > box[1] and diff.crop(box).getbbox():
            treffer += 1
    if treffer:
        aus.append("deko im daten-bereich, %d flaeche(n) mit pixeln der deko-ebene (rand %d px)" % (treffer, rand))
    return aus


def pruefe_seite(page, kanal, png=None):
    """Misst die gerenderte Seite und gibt die Verstoesse zurueck. Mit png
    (der Screenshot) prueft sie auch den Rand im Bild selbst."""
    vp = page.viewport_size
    name, p = profil(kanal, vp["width"], vp["height"])
    m = page.evaluate(MESS_JS)
    aus = groessen_verstoesse(m, p)
    aus += seite_text_verstoesse([t["text"] for t in m["texte"]])
    # kontrast 7:1 fuer jeden text gegen seinen grund (Ben, 25.10.2026), im
    # fertigen bild gemessen, mit motiv und schleier
    import hintergrund
    aus += hintergrund.kontrast_verstoesse(page)
    # deko-ebene aus, aussage gleich (Ben, 29.10.2026)
    aus += deko_verstoesse(page)
    if png is not None and p["rahmen"]:
        daten = "data:image/png;base64," + base64.b64encode(Path(png).read_bytes()).decode()
        treffer = page.evaluate(RAHMEN_JS, [daten, p["rahmen"], m["grund"]])
        for seite, n in treffer.items():
            if n > 3:
                aus.append("im rand von %d px %s steht inhalt (%d punkte)" % (p["rahmen"], seite, n))
    return ["%s (%s): %s" % (kanal, name, v) for v in aus]


def stoppen(verstoesse, wo):
    if verstoesse:
        raise WacheStopp("wache %s, %d verstoss(e): %s" % (wo, len(verstoesse), "; ".join(verstoesse)))


# ------------------------------------------------------------ selbsttest

def _seite(innen, grund="#080B0F", w=1080, h=1350):
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>*{margin:0;padding:0}"
            "body{width:%dpx;height:%dpx;background:%s;color:#F2F5F4;position:relative;"
            "font-family:sans-serif;overflow:hidden}div{position:absolute}</style></head><body>%s</body></html>"
            % (w, h, grund, innen))


GUT = ("<div data-rolle='titel' style='left:60px;top:60px;font-size:64px'>SLEEPING COINS</div>"
       "<div data-rolle='zahl' style='left:60px;top:150px;font-size:220px;line-height:1'>50%"
       "<span data-rolle='einheit' style='font-size:40px'> of all</span></div>"
       "<svg style='position:absolute;left:0;top:0' width='1080' height='1350'>"
       "<text x='60' y='700' font-size='34' fill='#fff'>at least 1 KAS</text></svg>"
       "<div style='left:60px;top:1150px;font-size:34px'>16 oct 2026, 08:12 utc · source kaspalytics</div>"
       "<div data-rolle='fuss' style='left:400px;top:1240px;font-size:34px'>KASPA PULSE</div>")


def selbsttest():
    fehler = 0

    def ok(name, bed):
        nonlocal fehler
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        fehler += 0 if bed else 1

    # antwort unter dem x-post (Ben, 31.10.2026)
    bild = ["ENTITY X", "5.55%", "one wallet holds about 1 in 18 of all KAS, 31 oct 2026"]
    for antwort, label, soll in (
            ("1,539,942,995 KAS sit in that one wallet on 31 oct. all the weekly numbers in one mail, every monday.",
             True, 0),
            ("that is 5.55% of all KAS on 31 oct.", True, 1),
            ("1,539,942,995 KAS on 31 oct. https://kaspapulse.com/x", True, 1),
            ("1,539,942,995 KAS on 31 oct. kaspapulse.com/x", True, 1),
            ("1,539,942,995 KAS on 31 oct, more on kaspapulse.com.", True, 1),
            ("1,539,942,995 KAS on 31 oct. https://kaspapulse.com/x", False, 0),
            ("8 hours and 10 minutes on 31 oct 2026, 14:08 utc.", True, 0)):
        v = antwort_verstoesse(antwort, bild, label)
        ok("antwort %r, label %s, %d verstoss" % (antwort[:40], "an" if label else "aus", soll), len(v) == soll)
    ok("ohne wiederholung faellt der teilsatz mit 5.55% weg",
       ohne_wiederholung("1,539,942,995 KAS sit in that one wallet on 31 oct, 5.55% of all KAS.", bild)
       == "1,539,942,995 KAS sit in that one wallet on 31 oct.")
    ok("ohne wiederholung laesst keinen reinen datumsrest stehen",
       ohne_wiederholung("5.55% in one wallet, as of 31 oct. its address is public.", bild)
       == "its address is public.")
    # text
    for t, was in (("hashrate up 42 percent", "percent"), ("balance: 1,442 KAS", "doppelpunkt"),
                   ("up — down", "gedankenstrich"), ("from 5 -> 6", "ascii-pfeil"),
                   ("securing the network right now", "right now"), ("counted live", "live"),
                   ("price target 1 dollar", "kursziel"), ("kas will reach 1", "kursziel will reach"),
                   ("@PLATZHALTER ASKED", "platzhalter"), ("placeholder name", "placeholder"),
                   ("{{name}} asked", "vorlagenklammer"), ("TODO zahl", "todo")):
        ok("text, %s faellt auf" % was, bool(text_verstoesse(t)))
    for t, was in (("29 sep 2026, 14:08 utc", "uhrzeit"), ("more on kaspapulse.com/halving.html", "link"),
                   ("almost nobody posts the second one", "the second (ausgenommen wie in #109)"),
                   ("the moment it lands", "the moment"), ("block time target is 100 ms", "technisches target"),
                   ("up 5% since 9 oct", "prozentzeichen")):
        ok("text, %s geht durch" % was, not text_verstoesse(t))
    # der threads-post vom 20.10. 17:10 (Ben, 21.10.2026)
    ok("text, now faellt auf", bool(text_verstoesse("294,512 kaspa addresses now hold at least 100 KAS.")))
    ok("text, known geht durch", not text_verstoesse("a known address on 16 oct"))
    ok("text, nowhere geht durch", not text_verstoesse("the heap went nowhere on 16 oct"))
    ok("zahl ohne datum faellt auf", bool(seite_text_verstoesse(["293,501", "addresses"])))
    ok("zahl mit datum geht durch", not seite_text_verstoesse(["293,501", "as of 16 oct"]))
    ok("datum auch amerikanisch", not seite_text_verstoesse(["96.39%", "OCT 16 2026"]))
    # dieselbe echtzeit-regel wie #109
    import number_of_day
    vorhanden = getattr(number_of_day, "_ECHTZEIT", None)
    if vorhanden is not None:
        ok("echtzeit-ausdruck aus #109 gleich dem ersatz hier",
           vorhanden.pattern == _ECHTZEIT_109 and vorhanden.flags & re.I)
    else:
        print("     #109 noch nicht gemergt, der ersatz hier gilt")
    import tagesgrafik
    fehlend = [w for w in tagesgrafik.ECHTZEIT if w not in ("the second", "the moment")
               and not echtzeit_ausdruck().search(w)]
    ok("jedes echtzeitwort der tagesgrafik faellt auf, ausser the second und the moment", not fehlend)
    # profile
    ok("x in 1080x1350 ist der uebergang", profil("x", 1080, 1350)[0] == "uebergang")
    ok("instagram in 1080x1350 ist feed", profil("instagram", 1080, 1350)[0] == "feed")
    ok("story in 1080x1920", profil("story", 1080, 1920)[0] == "story")
    try:
        profil("instagram", 1600, 900)
        ok("instagram in 1600x900 stoppt", False)
    except WacheStopp:
        ok("instagram in 1600x900 stoppt", True)
    # ungenaue mengenwoerter (Ben, 28.10.2026)
    real = "real" + " KAS"
    ok("'%s' stoppt" % real, text_verstoesse("more addresses hold %s than a week ago" % real) != [])
    ok("ungenaues mengenwort stoppt", text_verstoesse("addresses hold a " + "meaning" + "ful balance") != [])
    ok("adressen mit schwelle gehen durch", text_verstoesse("addresses with at least 100 KAS, +1,122 in a week") == [])
    funde = ungenau_im_quelltext()
    ok("kein generator gibt ein ungenaues mengenwort aus (%d funde)" % len(funde), not funde)
    if funde:
        print("     " + "; ".join(funde[:10]))
    # gerendert
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("     playwright fehlt, render-proben uebersprungen")
        print("%d fehler" % fehler)
        return 1 if fehler else 0
    import tempfile
    proben = {
        "gute seite gruen": (GUT, "instagram", 0),
        "kleintext 30 px stoppt": (GUT.replace("top:1150px;font-size:34px", "top:1150px;font-size:30px"),
                                   "instagram", 1),
        "svg-beschriftung 28 px stoppt": (GUT.replace("font-size='34'", "font-size='28'"), "instagram", 1),
        "titel 56 px stoppt": (GUT.replace("font-size:64px", "font-size:56px"), "instagram", 1),
        "grosse zahl 180 px stoppt": (GUT.replace("font-size:220px", "font-size:180px"), "instagram", 1),
        "text 40 px vom rand stoppt": (GUT.replace("left:60px;top:1150px", "left:40px;top:1150px"),
                                       "instagram", 2),
        "fusszeile in der ecke stoppt": (GUT.replace("left:400px;top:1240px", "left:60px;top:1240px"),
                                         "instagram", 1),
        "fusszeile in der ecke ist auf x im uebergang erlaubt":
            (GUT.replace("left:400px;top:1240px", "left:60px;top:1240px"), "x", 0),
        "balken im rand stoppt": (GUT + "<div style='left:20px;top:500px;width:100px;height:80px;"
                                  "background:#49EACB'></div>", "instagram", 1),
        "percent im bild stoppt": (GUT.replace("at least 1 KAS", "50 percent"), "instagram", 1),
        "platzhalter im kopf stoppt": (GUT.replace("SLEEPING COINS", "@PLATZHALTER ASKED"), "instagram", 1),
        "deko ueber der zahl stoppt": (GUT + "<svg data-deko='1' style='position:absolute;left:0;top:0' "
                                       "width='1080' height='1350'><line x1='60' y1='300' x2='1020' y2='420' "
                                       "stroke='#49EACB' stroke-width='4'/></svg>", "instagram", 1),
        "deko abseits der daten bleibt gruen": (GUT + "<div data-deko='1' style='position:absolute;left:700px;top:900px;"
                                                 "width:40px;height:40px;background:#2B7A6C'></div>", "instagram", 0),
    }
    with sync_playwright() as pw, tempfile.TemporaryDirectory() as td:
        import tagesgrafik as tg
        b = tg.chromium_start(pw)
        try:
            for name, (innen, kanal, erwartet) in proben.items():
                pg = b.new_page(viewport={"width": 1080, "height": 1350})
                pg.set_content(_seite(innen))
                png = Path(td) / "p.png"
                pg.screenshot(path=str(png))
                v = pruefe_seite(pg, kanal, png)
                pg.close()
                ok("%s (%d verstoss)" % (name, len(v)) + ("" if len(v) == erwartet else ", " + "; ".join(v)),
                   len(v) == erwartet)
        finally:
            b.close()
    try:
        stoppen(["a", "b"], "probe")
        ok("stoppen wirft", False)
    except WacheStopp as exc:
        ok("stoppen nennt jeden verstoss", "a; b" in str(exc))
    print("%d fehler" % fehler)
    return 1 if fehler else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", "--selftest", action="store_true")
    ap.add_argument("--text", help="einen text pruefen")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.text is not None:
        v = text_verstoesse(a.text)
        print("\n".join(v) if v else "gruen")
        return 1 if v else 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
