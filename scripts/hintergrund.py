#!/usr/bin/env python3
"""hintergrund.py, generative Bildhintergruende (Ben, 25.10.2026).

WARUM. Die Grafiken wechselten nur den Look (dunkel, hell, teal), ein Motiv
hatten sie nicht. Im Instagram-Raster sah deshalb alles gleich aus. Ab dem
28.10.2026 traegt jede Tagesgrafik, jede Zahl des Tages, jedes Karussell und
jede Story-Vorlage eines von acht Motiven im Hintergrund.

ACHT MOTIVE, alle generativ, aus festen Startwerten, in unseren Farben, kein
Falke, keine fremden Bilder:
  blockstrom      Bloecke in parallelen Bahnen, wie der BlockDAG sie legt
  knotennetz      Knoten mit Kanten zu ihren Nachbarn
  punktraster     Rasterpunkte, die zur Ecke hin wachsen
  hoehenlinien    Hoehenlinien eines weichen Gelaendes
  partikel-puls   Partikel um die Pulslinie der Marke
  zahnraeder      abstrakte Zahnraeder, angeschnitten
  sternenfeld     Sterne mit Hashrate-Wellen darunter
  glitch-raster   Raster mit versetzten Glitch-Balken
Jedes Motiv gibt es in einer dunklen und einer hellen Fassung. Der Teal-Look
nimmt die Formen der hellen Fassung in seinen eigenen Farben. Die
Standbilder (1080x1350 Feed, 1080x1920 Story) liegen als SVG in
graphics/hintergruende/, das Register steht in docs/hintergruende.md.

TAKT. Look und Motiv wechseln gemeinsam (look_takt.raster_motiv): jeder
Eintrag im Instagram-Raster nimmt das Motiv nach dem seines Vorgaengers, also
steht nie dasselbe Motiv zweimal hintereinander im Raster. Die anderen Kanaele
(threads, x, discord) und die Story ruecken das Motiv mit dem Datum weiter,
die Story nie im Motiv des Feed-Posts vom selben Tag.

LESBARKEIT GEHT VOR. setzen() legt das Motiv als Ebene ganz nach hinten und
nach dem Layout hinter jeden Text einen Schleier im Grundton, ohne das Layout
zu veraendern. Die Kontrast-Wache (content_wache.pruefe_seite, KONTRAST_JS
hier) misst danach im fertigen Bild: jeder Text gegen den Grund, auf dem er
wirklich steht, mindestens 7:1. Ausgenommen ist nur die Wortmarke (ein
Logo). Ein Verstoss stoppt den Lauf wie jede andere Wache.

    python3 scripts/hintergrund.py --bauen          standbilder schreiben
    python3 scripts/hintergrund.py --pruefen        standbilder und register auf stand?
    python3 scripts/hintergrund.py --selbsttest
"""
import argparse
import datetime as dt
import math
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

ORDNER = REPO / "graphics" / "hintergruende"
REGISTER = REPO / "docs" / "hintergruende.md"
MOTIVE = ("blockstrom", "knotennetz", "punktraster", "hoehenlinien", "partikel-puls", "zahnraeder",
          "sternenfeld", "glitch-raster")
FASSUNGEN = ("dunkel", "hell")
FORMATE = {"feed": (1080, 1350), "story": (1080, 1920)}
KONTRAST_MIN = 7.0
# Schleier hinter jedem Text: so viel Grundton liegt ueber dem Motiv
SCHLEIER_DECKUNG = 0.95

# Die Farben des Motivs je Look. linie und punkt sind Toene aus look_takt,
# mit Deckkraft, damit das Motiv zuruecktritt.
FARBEN = {
    "dunkel": {"a": "#49EACB", "b": "#2B7A6C", "c": "#1B252B", "deck": 0.75},
    "hell":   {"a": "#0F9A80", "b": "#B4CCC5", "c": "#DCE6E2", "deck": 0.85},
    "teal":   {"a": "#0F4A40", "b": "#9AF5E3", "c": "#3BD3B6", "deck": 0.6},
}


class Fehler(Exception):
    pass


def fassung(look):
    return "dunkel" if look == "dunkel" else "hell"


# ------------------------------------------------------------ die motive

def _f(x):
    return ("%.1f" % x).rstrip("0").rstrip(".")


def m_blockstrom(r, w, h, f):
    """Bloecke in parallelen Bahnen, schraeg von links unten nach rechts oben,
    mit Kanten zu Bloecken der Nachbarbahn (ein BlockDAG, kein Strich)."""
    teile = []
    bahnen = 9
    for i in range(bahnen):
        y0 = h * (0.15 + 0.95 * i / bahnen)
        x = -r.uniform(0, 120)
        vorher = None
        while x < w + 80:
            bw, bh = r.uniform(46, 96), r.uniform(28, 42)
            y = y0 - x * 0.42
            farbe = f["a"] if r.random() < 0.28 else f["b"]
            teile.append("<rect x='%s' y='%s' width='%s' height='%s' rx='6' fill='%s' opacity='%s'/>"
                         % (_f(x), _f(y), _f(bw), _f(bh), farbe, _f(r.uniform(0.35, 0.9))))
            if vorher and r.random() < 0.5:
                teile.append("<line x1='%s' y1='%s' x2='%s' y2='%s' stroke='%s' stroke-width='2' opacity='0.5'/>"
                             % (_f(vorher[0]), _f(vorher[1]), _f(x), _f(y + bh / 2), f["b"]))
            vorher = (x + bw, y + bh / 2)
            x += bw + r.uniform(18, 70)
    return teile


def m_knotennetz(r, w, h, f):
    knoten = [(r.uniform(-40, w + 40), r.uniform(-40, h + 40)) for _ in range(int(w * h / 14000))]
    teile = []
    for i, (x, y) in enumerate(knoten):
        nah = sorted(knoten, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)[1:4]
        for (x2, y2) in nah:
            if (x2, y2) > (x, y):
                teile.append("<line x1='%s' y1='%s' x2='%s' y2='%s' stroke='%s' stroke-width='2.6' opacity='0.75'/>"
                             % (_f(x), _f(y), _f(x2), _f(y2), f["b"]))
    for x, y in knoten:
        gross = r.random() < 0.15
        teile.append("<circle cx='%s' cy='%s' r='%s' fill='%s'/>"
                     % (_f(x), _f(y), _f(r.uniform(11, 17) if gross else r.uniform(4, 7)),
                        f["a"] if gross else f["b"]))
    return teile


def m_punktraster(r, w, h, f):
    teile = []
    schritt = 36
    for gy in range(0, h + schritt, schritt):
        for gx in range(0, w + schritt, schritt):
            d = math.hypot(w - gx, h - gy) / math.hypot(w, h)
            rad = max(0.0, 13 * (1 - d) ** 1.6) + 1.2
            versatz = schritt / 2 if (gy // schritt) % 2 else 0
            teile.append("<circle cx='%s' cy='%s' r='%s' fill='%s'/>"
                         % (_f(gx + versatz), _f(gy), _f(rad), f["a"] if d < 0.35 else f["b"]))
    return teile


def m_hoehenlinien(r, w, h, f):
    teile = []
    phasen = [r.uniform(0, 6.3) for _ in range(4)]
    for k in range(34):
        basis = -120 + k * (h + 240) / 34
        punkte = []
        for x in range(-20, w + 41, 20):
            y = (basis + 46 * math.sin(x / 170 + phasen[0] + k * 0.13) + 30 * math.sin(x / 83 + phasen[1])
                 + 18 * math.sin(x / 41 + phasen[2] + k * 0.31))
            punkte.append("%s,%s" % (_f(x), _f(y)))
        farbe = f["a"] if k % 6 == 0 else f["b"]
        teile.append("<polyline points='%s' fill='none' stroke='%s' stroke-width='%s' opacity='0.8'/>"
                     % (" ".join(punkte), farbe, "4" if k % 6 == 0 else "2.2"))
    return teile


def m_partikel_puls(r, w, h, f):
    teile = []
    import tagesgrafik as tg
    for i in range(3):
        y = h * (0.3 + 0.27 * i)
        s = w / 230
        teile.append("<path d='%s' transform='translate(0 %s) scale(%s %s)' fill='none' stroke='%s' "
                     "stroke-width='%s' opacity='%s' stroke-linejoin='round' vector-effect='non-scaling-stroke'/>"
                     % (tg.PULS, _f(y - 30 * s * 0.6), _f(s), _f(s * 0.6), f["a"] if i == 1 else f["b"],
                        "6" if i == 1 else "3.5", "0.95" if i == 1 else "0.7"))
    for _ in range(int(w * h / 2600)):
        x, y = r.uniform(0, w), r.uniform(0, h)
        teile.append("<circle cx='%s' cy='%s' r='%s' fill='%s' opacity='%s'/>"
                     % (_f(x), _f(y), _f(r.uniform(2, 6)), f["a"] if r.random() < 0.25 else f["b"],
                        _f(r.uniform(0.3, 0.9))))
    return teile


def _zahnrad(cx, cy, rad, zaehne, f, farbe, breite):
    punkte = []
    n = zaehne * 4
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = rad + (rad * 0.12 if i % 4 in (1, 2) else 0)
        punkte.append("%s,%s" % (_f(cx + rr * math.cos(a)), _f(cy + rr * math.sin(a))))
    return ("<polygon points='%s' fill='none' stroke='%s' stroke-width='%s' stroke-linejoin='round'/>"
            "<circle cx='%s' cy='%s' r='%s' fill='none' stroke='%s' stroke-width='%s'/>"
            % (" ".join(punkte), farbe, breite, _f(cx), _f(cy), _f(rad * 0.35), farbe, breite))


def m_zahnraeder(r, w, h, f):
    teile = []
    for cx, cy, rad, z in ((w * 0.92, h * 0.12, 260, 18), (w * 0.62, h * 0.31, 150, 12),
                           (w * 0.05, h * 0.62, 300, 20), (w * 0.38, h * 0.86, 190, 14),
                           (w * 0.98, h * 0.78, 130, 10)):
        teile.append(_zahnrad(cx, cy, rad, z, f, f["b"], "6"))
        teile.append(_zahnrad(cx, cy, rad * 0.62, max(6, z // 2), f, f["a"], "4"))
    return teile


def m_sternenfeld(r, w, h, f):
    teile = []
    for _ in range(int(w * h / 3200)):
        teile.append("<circle cx='%s' cy='%s' r='%s' fill='%s' opacity='%s'/>"
                     % (_f(r.uniform(0, w)), _f(r.uniform(0, h * 0.75)), _f(r.uniform(1.5, 4.8)),
                        f["a"] if r.random() < 0.15 else f["b"], _f(r.uniform(0.35, 1))))
    for k in range(9):
        punkte = []
        for x in range(-20, w + 41, 16):
            y = h * (0.6 + k * 0.045) + (70 - k * 5) * math.sin(x / (120 + k * 14) + k * 0.7)
            punkte.append("%s,%s" % (_f(x), _f(y)))
        teile.append("<polyline points='%s' fill='none' stroke='%s' stroke-width='3.5' opacity='%s'/>"
                     % (" ".join(punkte), f["a"] if k in (2, 5) else f["b"], _f(0.95 - k * 0.06)))
    return teile


def m_glitch_raster(r, w, h, f):
    teile = []
    for x in range(0, w + 1, 60):
        teile.append("<line x1='%d' y1='0' x2='%d' y2='%d' stroke='%s' stroke-width='1' opacity='0.5'/>"
                     % (x, x, h, f["b"]))
    for y in range(0, h + 1, 60):
        teile.append("<line x1='0' y1='%d' x2='%d' y2='%d' stroke='%s' stroke-width='1' opacity='0.5'/>"
                     % (y, w, y, f["b"]))
    for _ in range(26):
        y = r.uniform(0, h)
        bh = r.choice((6, 10, 18, 28))
        x = r.uniform(-100, w * 0.8)
        teile.append("<rect x='%s' y='%s' width='%s' height='%s' fill='%s' opacity='%s'/>"
                     % (_f(x), _f(y), _f(r.uniform(120, 520)), bh, f["a"] if r.random() < 0.35 else f["b"],
                        _f(r.uniform(0.35, 0.85))))
    return teile


ZEICHNER = {"blockstrom": m_blockstrom, "knotennetz": m_knotennetz, "punktraster": m_punktraster,
            "hoehenlinien": m_hoehenlinien, "partikel-puls": m_partikel_puls, "zahnraeder": m_zahnraeder,
            "sternenfeld": m_sternenfeld, "glitch-raster": m_glitch_raster}


def saat(motiv, w, h):
    """Fester Startwert je Motiv und Format: ein Motiv ist immer dasselbe Bild."""
    return sum((i + 1) * ord(c) for i, c in enumerate("%s/%dx%d" % (motiv, w, h)))


def svg(motiv, look, w, h, mit_grund=True):
    """Das Motiv als SVG im Look. mit_grund=False laesst den Grund weg (die
    Seite traegt ihn selbst)."""
    if motiv not in ZEICHNER:
        raise Fehler("unbekanntes motiv %r, es gibt %s" % (motiv, ", ".join(MOTIVE)))
    import look_takt
    lk = look_takt.look(look)
    f = FARBEN[look]
    # die formen kommen aus der fassung: teal zeichnet wie hell
    r = random.Random(saat(motiv, w, h) + (0 if fassung(look) == "dunkel" else 7))
    innen = "".join(ZEICHNER[motiv](r, w, h, f))
    grund = "<rect width='%d' height='%d' fill='%s'/>" % (w, h, lk["grund"]) if mit_grund else ""
    return ("<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' viewBox='0 0 %d %d'>%s"
            "<g opacity='%s'>%s</g></svg>" % (w, h, w, h, grund, _f(f["deck"]), innen))


# ------------------------------------------------------------ in die seite

SCHLEIER_JS = """
(function () {
  function hex(h, a) { h = h.replace('#', ''); return 'rgba(' + parseInt(h.substr(0, 2), 16) + ','
    + parseInt(h.substr(2, 2), 16) + ',' + parseInt(h.substr(4, 2), 16) + ',' + a + ')'; }
  function los() {
    var g = document.body.dataset.hgGrund, a = parseFloat(document.body.dataset.hgDeckung);
    var alt = document.querySelectorAll('.hg-schleier'); for (var i = 0; i < alt.length; i++) alt[i].remove();
    var ziel = document.body;
    var alle = document.querySelectorAll('body *');
    for (var i = 0; i < alle.length; i++) {
      var e = alle[i];
      if (e.closest('.hg-ebene') || e.closest('.wm')) continue;
      var rects = [];
      if (e instanceof SVGTextElement) { rects = [e.getBoundingClientRect()]; }
      else {
        if (e.closest('svg')) continue;
        for (var k = 0; k < e.childNodes.length; k++) {
          var n = e.childNodes[k];
          if (n.nodeType === 3 && n.textContent.trim()) {
            var r = document.createRange(); r.selectNodeContents(n);
            var rs = r.getClientRects(); for (var j = 0; j < rs.length; j++) rects.push(rs[j]);
          }
        }
      }
      for (var j = 0; j < rects.length; j++) {
        var q = rects[j]; if (!q.width || !q.height) continue;
        var d = document.createElement('div'); d.className = 'hg-schleier';
        d.style.cssText = 'position:absolute;z-index:-1;pointer-events:none;border-radius:16px;left:'
          + (q.left - 14 + window.scrollX) + 'px;top:' + (q.top - 8 + window.scrollY) + 'px;width:'
          + (q.width + 28) + 'px;height:' + (q.height + 16) + 'px;background:' + hex(g, a)
          + ';box-shadow:0 0 34px 22px ' + hex(g, a);
        ziel.appendChild(d);
      }
    }
    document.body.dataset.hgFertig = '1';
  }
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(los); else window.addEventListener('load', los);
})();
"""


def setzen(seite, motiv, look, w=1080, h=1350, rand=None):
    """Setzt das Motiv hinter eine fertige Seite: eine Ebene ganz hinten,
    nach dem Layout ein Schleier hinter jedem Text. Das Layout der Seite
    bleibt unberuehrt. rand: im Feed bleiben die aeusseren 60 px Grund (die
    Rand-Wache der content_wache), das Motiv blendet bis 140 px ein. Die
    Story laeuft randlos."""
    if rand is None:
        rand = 0 if h == 1920 else 60
    import base64
    import look_takt
    lk = look_takt.look(look)
    daten = base64.b64encode(svg(motiv, look, w, h, mit_grund=False).encode()).decode()
    maske = ""
    if rand:
        innen = rand + 80
        verlauf = ("linear-gradient(to RICHTUNG, transparent %dpx, #000 %dpx, #000 calc(100%% - %dpx), "
                   "transparent calc(100%% - %dpx))" % (rand, innen, innen, rand))
        x, y = verlauf.replace("RICHTUNG", "right"), verlauf.replace("RICHTUNG", "bottom")
        maske = ("-webkit-mask-image:%s,%s;-webkit-mask-composite:source-in;mask-image:%s,%s;"
                 "mask-composite:intersect;" % (x, y, x, y))
    stil = ("<style>body{isolation:isolate}.hg-ebene{position:absolute;left:0;top:0;width:%dpx;height:%dpx;"
            "z-index:-2;pointer-events:none;%sbackground:url(data:image/svg+xml;base64,%s) no-repeat 0 0/%dpx %dpx}"
            "</style>" % (w, h, maske, daten, w, h))
    seite, n = re.subn(r"</head>", stil + "</head>", seite, count=1)
    if not n:
        raise Fehler("seite ohne </head>")
    m = re.search(r"<body\b([^>]*)>", seite)
    if not m:
        raise Fehler("seite ohne <body>")
    attr = (" data-hg-motiv='%s' data-hg-grund='%s' data-hg-deckung='%s'"
            % (motiv, lk["grund"], SCHLEIER_DECKUNG))
    neu = "<body%s%s><div class='hg-ebene' aria-hidden='true'></div>" % (m.group(1), attr)
    seite = seite[:m.start()] + neu + seite[m.end():]
    return seite.replace("</body>", "<script>%s</script></body>" % SCHLEIER_JS, 1)


def warten(page, frist_ms=3000):
    """Wartet, bis die Schleier liegen (nur auf Seiten mit Motiv)."""
    if page.evaluate("!!document.body.dataset.hgMotiv"):
        page.wait_for_function("document.body.dataset.hgFertig === '1'", timeout=frist_ms)


# ------------------------------------------------------------ kontrast

def luminanz(rgb):
    def k(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * k(r) + 0.7152 * k(g) + 0.0722 * k(b)


def kontrast(a, b):
    la, lb = sorted((luminanz(a), luminanz(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# Sammelt jeden Text mit seiner Farbe und seinen Rechtecken. Die Wortmarke
# ist ein Logo und zaehlt nicht.
TEXTE_JS = """() => {
  const aus = [];
  const farbe = (e) => {
    const s = getComputedStyle(e);
    let c = (e instanceof SVGElement) ? (s.fill && s.fill !== 'none' ? s.fill : e.getAttribute('fill')) : s.color;
    return c || s.color;
  };
  for (const e of document.querySelectorAll('body *')) {
    if (e.closest('.wm') || e.closest('.hg-ebene') || e.classList.contains('hg-schleier')) continue;
    const st = getComputedStyle(e);
    if (st.display === 'none' || st.visibility === 'hidden' || parseFloat(st.opacity) === 0) continue;
    let rects = [], text = '';
    if (e instanceof SVGTextElement) { text = e.textContent.trim(); rects = [e.getBoundingClientRect()]; }
    else {
      if (e.closest('svg')) continue;
      const kn = [...e.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim());
      if (!kn.length) continue;
      text = kn.map(n => n.textContent.trim()).join(' ');
      for (const n of kn) { const r = document.createRange(); r.selectNodeContents(n); rects.push(...r.getClientRects()); }
    }
    rects = rects.filter(q => q.width > 0 && q.height > 0)
                 .map(q => ({l: Math.max(0, q.left), t: Math.max(0, q.top), r: q.right, b: q.bottom}));
    if (!text || !rects.length) continue;
    aus.push({text: text.slice(0, 40), farbe: farbe(e), rects});
  }
  return aus;
}"""

PIXEL_JS = """async ([daten, texte]) => {
  const img = new Image(); img.src = daten; await img.decode();
  const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
  const g = c.getContext('2d'); g.drawImage(img, 0, 0);
  const d = g.getImageData(0, 0, c.width, c.height).data;
  return texte.map(t => {
    const px = [];
    for (const q of t.rects) {
      const schritt = Math.max(2, Math.floor(Math.min(q.r - q.l, q.b - q.t) / 8));
      // zwei pixel innen: die kante des rechtecks gehoert nicht sicher zum grund des textes
      for (let y = Math.ceil(q.t) + 2; y < Math.min(q.b - 2, c.height); y += schritt)
        for (let x = Math.ceil(q.l) + 2; x < Math.min(q.r - 2, c.width); x += schritt) {
          const i = (y * c.width + x) * 4; px.push([d[i], d[i + 1], d[i + 2]]);
        }
    }
    return px;
  });
}"""

VERSTECKEN = ("<style id='hg-ohne-text'>*{color:transparent!important;-webkit-text-fill-color:transparent!important;"
              "text-shadow:none!important;caret-color:transparent!important}svg text,svg tspan{fill:transparent!important;"
              "stroke:transparent!important}</style>")


def _rgb(css):
    m = re.match(r"rgba?\(([\d.]+)[, ]+([\d.]+)[, ]+([\d.]+)", css or "")
    if m:
        return tuple(int(float(v)) for v in m.groups())
    if css and css.startswith("#") and len(css) == 7:
        return hex_rgb(css)
    return None


def kontrast_verstoesse(page, minimum=KONTRAST_MIN, quantil=0.05):
    """Misst jeden Text gegen den Grund, auf dem er steht: Screenshot ohne
    Text, dann je Text die Pixel in seinen Rechtecken. Gezaehlt wird das
    untere 5-%-Quantil, damit eine Kantenglaettung nicht den Ausschlag gibt."""
    import base64
    texte = page.evaluate(TEXTE_JS)
    if not texte:
        return []
    page.evaluate("(s) => document.head.insertAdjacentHTML('beforeend', s)", VERSTECKEN)
    try:
        bild = page.screenshot()
    finally:
        page.evaluate("() => { const e = document.getElementById('hg-ohne-text'); if (e) e.remove(); }")
    daten = "data:image/png;base64," + base64.b64encode(bild).decode()
    pixel = page.evaluate(PIXEL_JS, [daten, texte])
    aus = []
    for t, px in zip(texte, pixel):
        farbe = _rgb(t["farbe"])
        if farbe is None or not px:
            continue
        werte = sorted(kontrast(farbe, p) for p in px)
        k = werte[min(len(werte) - 1, int(len(werte) * quantil))]
        if k < minimum - 0.005:
            aus.append("kontrast %.1f:1 bei %r, mindestens %.0f:1" % (k, t["text"], minimum))
    return aus


# ------------------------------------------------------------ takt

def motiv_nach(vorher, schritte=1):
    i = MOTIVE.index(vorher) if vorher in MOTIVE else -1
    return MOTIVE[(i + schritte) % len(MOTIVE)]


def motiv_datum(datum, versatz=0):
    """Das Motiv eines Tages fuer Kanaele ausserhalb des Rasters: aufeinander
    folgende Tage haben nie dasselbe Motiv."""
    return MOTIVE[(dt.date.fromisoformat(str(datum)).toordinal() + versatz) % len(MOTIVE)]


KANAL_VERSATZ = {"instagram": 0, "threads": 3, "x": 5, "discord": 6}


def motiv_story(datum, feed_motiv=None):
    """Story: mit dem Datum weiter, nie im Motiv des Feed-Posts vom selben Tag."""
    m = motiv_datum(datum, 2)
    return motiv_nach(m) if m == feed_motiv else m


# ------------------------------------------------------------ standbilder, register

def datei(motiv, fass, fmt):
    return ORDNER / ("%s-%s-%s.svg" % (motiv, fass, fmt))


def standbilder():
    """{pfad: inhalt} fuer alle Motive, Fassungen und Formate."""
    aus = {}
    for m in MOTIVE:
        for fass in FASSUNGEN:
            for fmt, (w, h) in FORMATE.items():
                aus[datei(m, fass, fmt)] = svg(m, fass, w, h) + "\n"
    return aus


def register_text():
    zeilen = [
        "# Bildhintergründe",
        "",
        "Register der Hintergrundmotive für Tagesgrafik, Zahl des Tages, Karussell und Story-Vorlagen "
        "(Ben, 25.10.2026). Gebaut von `scripts/hintergrund.py`, nicht von Hand ändern: "
        "`python3 scripts/hintergrund.py --bauen` schreibt Standbilder und Register neu, "
        "`--pruefen` fällt auf jede Abweichung.",
        "",
        "- **Herkunft:** generativ. Jedes Motiv entsteht im Skript aus einem festen Startwert. "
        "Keine fremden Bilder, keine Fotos, keine Lizenz Dritter, kein Falke.",
        "- **Farben:** nur die Töne aus `scripts/look_takt.py`. Der Teal-Look zeichnet die Formen der hellen Fassung "
        "in seinen eigenen Farben.",
        "- **Takt:** Look und Motiv wechseln gemeinsam. Im Instagram-Raster nimmt jeder Post das Motiv nach dem seines "
        "Vorgängers (`look_takt.raster_motiv`), es steht also nie dasselbe Motiv zweimal hintereinander. Andere Kanäle "
        "und die Story rücken mit dem Datum weiter, die Story nie im Motiv des Feed-Posts vom selben Tag.",
        "- **Lesbarkeit:** hinter jedem Text liegt ein Schleier im Grundton (Deckung %d %%). Die Kontrast-Wache "
        "misst im fertigen Bild jeden Text gegen seinen Grund, mindestens %d:1. Ausgenommen ist nur die Wortmarke."
        % (round(SCHLEIER_DECKUNG * 100), KONTRAST_MIN),
        "",
        "| Motiv | Herkunft | Fassung | Feed 1080x1350 | Story 1080x1920 | Startwert |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for m in MOTIVE:
        for fass in FASSUNGEN:
            zeilen.append("| %s | generativ | %s | `%s` | `%s` | %d |" % (
                m, fass, datei(m, fass, "feed").relative_to(REPO), datei(m, fass, "story").relative_to(REPO),
                saat(m, 1080, 1350)))
    return "\n".join(zeilen) + "\n"


def bauen(schreiben=True):
    anders = []
    soll = standbilder()
    soll[REGISTER] = register_text()
    for p, inhalt in soll.items():
        ist = p.read_text(encoding="utf-8") if p.exists() else ""
        if ist != inhalt:
            anders.append(str(p.relative_to(REPO)))
            if schreiben:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(inhalt, encoding="utf-8")
    fremd = [str(p.relative_to(REPO)) for p in ORDNER.glob("*") if p not in soll] if ORDNER.exists() else []
    return anders, fremd


# ------------------------------------------------------------ selbsttest

def selbsttest():
    import look_takt
    fehler = 0

    def ok(name, bed):
        nonlocal fehler
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        fehler += 0 if bed else 1

    ok("acht motive aus dem auftrag", MOTIVE == ("blockstrom", "knotennetz", "punktraster", "hoehenlinien",
                                                  "partikel-puls", "zahnraeder", "sternenfeld", "glitch-raster"))
    ok("jedes motiv hat einen zeichner", set(ZEICHNER) == set(MOTIVE))
    s1, s2 = svg("knotennetz", "dunkel", 1080, 1350), svg("knotennetz", "dunkel", 1080, 1350)
    ok("ein motiv ist immer dasselbe bild", s1 == s2)
    ok("dunkel und hell sind verschiedene fassungen", svg("knotennetz", "hell", 1080, 1350) != s1)
    def formen(x):
        return re.sub(r"<g opacity='[\d.]+'>", "<g>", re.sub(r"#[0-9A-F]{6}", "", x))
    ok("teal zeichnet die formen der hellen fassung",
       all(formen(svg(m, "teal", 1080, 1350)) == formen(svg(m, "hell", 1080, 1350)) for m in MOTIVE))
    erlaubt = {v.upper() for lk in look_takt.LOOKS.values() for v in lk.values()}
    farben = set(c.upper() for m in MOTIVE for lk in ("dunkel", "hell", "teal")
                 for c in re.findall(r"#[0-9A-Fa-f]{6}", svg(m, lk, 1080, 1350)))
    ok("nur farben aus look_takt (%s)" % ", ".join(sorted(farben - erlaubt)), farben <= erlaubt)
    ok("kein bild von aussen, kein falke", not any(re.search(r"href|<image|falk|hawk", svg(m, "dunkel", 1080, 1920), re.I)
                                                 for m in MOTIVE))
    ok("story im eigenen format", "height='1920'" in svg("blockstrom", "hell", 1080, 1920))
    ok("kontrast 7:1 rechnet richtig", abs(kontrast(hex_rgb("#000000"), hex_rgb("#FFFFFF")) - 21) < 0.01
       and abs(kontrast(hex_rgb("#767676"), hex_rgb("#FFFFFF")) - 4.54) < 0.02)
    for lk, l in look_takt.LOOKS.items():
        for k in ("text", "text2", "akzent"):
            ok("%s %s gegen den grund mindestens 7:1 (%.2f)" % (lk, k, kontrast(hex_rgb(l[k]), hex_rgb(l["grund"]))),
               kontrast(hex_rgb(l[k]), hex_rgb(l["grund"])) >= KONTRAST_MIN)
    folge = [MOTIVE[0]]
    for _ in range(20):
        folge.append(motiv_nach(folge[-1]))
    ok("im raster nie dasselbe motiv zweimal hintereinander", all(a != b for a, b in zip(folge, folge[1:])))
    ok("auch nicht senkrecht im dreier-raster", all(a != b for a, b in zip(folge, folge[3:])))
    tage = [motiv_datum("2026-10-%02d" % d) for d in range(20, 31)]
    ok("andere kanaele, zwei tage nie gleich", all(a != b for a, b in zip(tage, tage[1:])))
    ok("story nie im motiv des feed-posts", all(motiv_story("2026-10-%02d" % d, motiv_datum("2026-10-%02d" % d, 2))
                                               != motiv_datum("2026-10-%02d" % d, 2) for d in range(20, 31)))
    seite = ("<!DOCTYPE html><html><head><style>body{width:1080px;height:1350px;background:#080B0F;margin:0;"
             "position:relative}</style></head><body data-look='dunkel'><div style='position:absolute;left:60px;"
             "top:300px;font-size:80px;color:#F2F5F4'>383 PH/s</div></body></html>")
    neu = setzen(seite, "sternenfeld", "dunkel")
    ok("setzen legt ebene, schleier-skript und motiv-attribut", "hg-ebene" in neu and "hg-schleier" in neu
       and "data-hg-motiv='sternenfeld'" in neu and "data-look='dunkel'" in neu)
    anders, fremd = bauen(schreiben=False)
    ok("standbilder und register auf stand (%s)" % ", ".join((anders + fremd)[:4]), not anders and not fremd)
    try:
        import tagesgrafik as tg
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = tg.chromium_start(p)
            try:
                pg = b.new_page(viewport={"width": 1080, "height": 1350})
                for m in MOTIVE:
                    for lk in ("dunkel", "hell", "teal"):
                        L = look_takt.look(lk)
                        s = seite.replace("#080B0F", L["grund"]).replace("#F2F5F4", L["text2"])
                        pg.set_content(setzen(s, m, lk))
                        warten(pg)
                        v = kontrast_verstoesse(pg)
                        ok("%s %s, text2 auf dem motiv mindestens 7:1 %s" % (m, lk, "; ".join(v)), not v)
                # ohne schleier faellt der kontrast durch: die wache misst wirklich
                pg.set_content(seite.replace("#F2F5F4", "#2B7A6C"))
                ok("die wache faellt bei zu wenig kontrast", bool(kontrast_verstoesse(pg)))
                pg.close()
            finally:
                b.close()
    except ImportError:
        print("ohne playwright, bildprobe uebersprungen")
    print("%d fehler" % fehler)
    return 1 if fehler else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bauen", action="store_true")
    ap.add_argument("--pruefen", action="store_true")
    ap.add_argument("--selbsttest", "--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.bauen or a.pruefen:
        anders, fremd = bauen(schreiben=a.bauen)
        if a.pruefen and (anders or fremd):
            print("nicht auf stand: %s" % ", ".join(anders + ["fremd " + f for f in fremd]))
            return 1
        print("%s: %d dateien %s" % ("bauen" if a.bauen else "pruefen", len(anders),
                                     "geschrieben" if a.bauen else "abweichend"))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
