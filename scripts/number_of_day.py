#!/usr/bin/env python3
"""
kaspa pulse - number of the day renderer
liest data/number-of-day.json und rendert graphics/number-of-day.png
im 4:5 hochformat (1080x1350) ueber playwright.
grundsatz: die vergleichszahl ist der held, nicht die zahl.
eine zahl ohne anker ist dekoration und gehoert ins dashboard, nicht in einen post.

fassung vom 27.08.2026. drei aenderungen gegen die vorfassung.
1. die marke heisst kaspa pulse. alphavault ist seit dem 24.08. tot und stand
   trotzdem taeglich oben links auf drei flaechen.
2. alle groessen neu, kalibriert am haertesten fall. telegram zeigt das bild
   mit rund 350px breite, also faktor 0.32. was in der quelle unter 40px hat,
   ist dort keine schrift mehr. untergrenze 40, kopf und fusszeile 30,
   heldenzahl 190, ueberschrift 78. das folgt der doktrinregel fuer 1080px.
3. ein ueberlaufwaechter. mehr text bei groesserer schrift passt nicht mehr
   automatisch. wenn der inhalt die 1350px sprengt, bricht der render mit
   fehler ab und sagt um wie viel. dann wird text geloescht, nicht schrift
   verkleinert. lieber keine grafik als eine abgeschnittene (regel 36/38).

lokal:
    python3 scripts/number_of_day.py --input data/number-of-day.json
in github actions:
    identisch, chromium kommt aus dem playwright setup step
"""
import argparse
import json
import re
import sys
from pathlib import Path
W, H = 1080, 1350
# ---------------------------------------------------------------- punctuation
# regel: nichts was ben veroeffentlicht enthaelt gedankenstriche, doppelpunkte
# oder pfeile. ausgenommen sind technische tokens, also uhrzeiten und urls.
FORBIDDEN = {
    "—": "em dash",
    "–": "en dash",
    "→": "arrow",
    " - ": "hyphen as punctuation",
    ":": "colon",
}
# schreibregel (ben, 15.10.2026): in oeffentlichen texten steht "%", nie
# "percent". die regel gab es schon in scripts/tagesgrafik.py fuer die
# tagesgrafik, nur hier nicht, und die zahl des tages hat sie an 22 stellen
# gebrochen. sie steht jetzt in derselben wache wie die zeichenregel, weil
# jeder text dort ohnehin vorbeikommt, der grafik UND post einschliesst.
# ganze woerter: "percentile" oder "percentpoints" sind keine verstoesse.
_PERCENT = re.compile(r"\bpercent(?:s|age)?\b", re.I)
# echtzeitregel (ben, 16.10.2026): die zahl des tages ist eine messung mit
# stichtag, keine anzeige. "petahash per second securing the network right
# now" stand am 16.10. in der grafik und war genau das, was die regel
# verbietet - gemessen wurde um 10:12, gesehen wird das bild tagelang.
#
# die wortliste ist die aus scripts/tagesgrafik.py (ECHTZEIT), um bens drei
# woerter erweitert. ZWEI WOERTER VON DORT STEHEN HIER ABSICHTLICH NICHT:
# "the second" und "the moment". In den kurzen zeilen der tagesgrafik sind
# sie echtzeitwoerter, in den langen posttexten der zahl des tages sind sie
# gewoehnliche sprache ("almost nobody posts the second one"). eine wache,
# die richtige saetze stoppt, wird abgeschaltet.
# "now" steht seit dem 21.10.2026 dabei (Ben), nach dem Threads-Post vom
# 20.10. 17:10. Es faellt nur als ganzes Wort, "known" und "nowhere" nicht.
_ECHTZEIT = re.compile(
    r"\b(?:right now|currently|at the moment|as we speak|this second|live|"
    r"real[- ]?time|around the clock|every minute|instant|instantly|24/7|"
    r"now)\b", re.I)
_URL = re.compile(r"\b[\w.-]+\.(?:com|org|io|net|stream|xyz|app|dev)\b\S*", re.I)
_TIME = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
_PROTO = re.compile(r"https?://\S+", re.I)
def _strip_technical(text: str) -> str:
    text = _PROTO.sub(" ", text)
    text = _URL.sub(" ", text)
    text = _TIME.sub(" ", text)
    return text
def assert_punctuation(text: str, where: str) -> None:
    probe = _strip_technical(text)
    for bad, name in FORBIDDEN.items():
        if bad in probe:
            raise ValueError(
                f"punctuation rule violated in {where}: {name} found in {text!r}"
            )
    hit = _PERCENT.search(probe)
    if hit:
        raise ValueError(
            f"spelling rule violated in {where}: {hit.group(0)!r} instead of % "
            f"in {text!r}"
        )
    hit = _ECHTZEIT.search(probe)
    if hit:
        raise ValueError(
            f"realtime rule violated in {where}: {hit.group(0)!r} claims a live "
            f"reading. the number has a measurement day, name it or leave the "
            f"time out, in {text!r}"
        )
def walk_and_check(node, path="root"):
    if isinstance(node, str):
        assert_punctuation(node, path)
    elif isinstance(node, dict):
        for k, v in node.items():
            if k in ("tone", "kind"):
                continue
            walk_and_check(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk_and_check(v, f"{path}[{i}]")


def echtzeit_treffer(text):
    """das erste echtzeit-wort im text, oder None. dieselbe regel wie in
    assert_punctuation, fuer die anderen post-wachen (x_post, weekly_numbers),
    damit es eine liste gibt und nicht drei (Ben, 17.10.2026)."""
    m = _ECHTZEIT.search(_strip_technical(text or ""))
    return m.group(0) if m else None
# ---------------------------------------------------------------- template
# groessen in px bei 1080 breite. seit dem look-takt (Ben, 15.10.2026) nach
# der tabelle fuer den instagram-feed: grosse zahl ab 200, ueberschrift ab 64,
# alles kleine ab 34, inhalt mindestens 60 px vom rand. die farben kommen je
# look aus LOOK_FARBEN, die schriften eingebettet aus graphics/fonts
# (look_takt.schriften_css), nichts wird zur laufzeit geladen.
LOOK_FARBEN = {
    "dunkel": {"bg": "#080B0F", "card": "#11181D", "line": "#1B252B", "teal": "#49EACB",
               "teal-dk": "#49EACB", "red": "#E36A6A", "txt": "#F2F5F4", "dim": "#A9B7B4",
               "dimmer": "#A9B7B4", "faint": "#2B3A40", "grid": "#1B252B", "ctx": "#7E8A94",
               "bar": "#2B3A40", "dot": "#1B252B", "track": "#1B252B"},
    "hell":   {"bg": "#EEF3F1", "card": "#F8FBFA", "line": "#D3DFDB", "teal": "#0F9A80",
               "teal-dk": "#0F9A80", "red": "#B83F3F", "txt": "#0B1A17", "dim": "#4F625D",
               "dimmer": "#4F625D", "faint": "#B4CCC5", "grid": "#D3DFDB", "ctx": "#7A8D88",
               "bar": "#C9D9D4", "dot": "#D3DFDB", "track": "#DCE6E2"},
    "teal":   {"bg": "#49EACB", "card": "#3BD3B6", "line": "#2FBFA3", "teal": "#04211C",
               "teal-dk": "#04211C", "red": "#7A1414", "txt": "#04211C", "dim": "#0F4A40",
               "dimmer": "#0F4A40", "faint": "#9AF5E3", "grid": "#2FBFA3", "ctx": "#0F4A40",
               "bar": "#9AF5E3", "dot": "#2FBFA3", "track": "#2FBFA3"},
}


def look_css(look: str = "dunkel") -> str:
    import look_takt
    import wortmarke
    f = LOOK_FARBEN[look]
    # die wortmarke steht in scripts/wortmarke.py. txt und teal fuehrt diese
    # datei schon je look, deshalb gehen die variablen hinein statt zahlen.
    return (look_takt.schriften_css() + ":root{"
            + "".join("--%s:%s;" % (k, v) for k, v in f.items()) + "}"
            + wortmarke.css("wm", groesse=34, sperrung=5,
                            kaspa="var(--txt)", pulse="var(--teal)"))


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{
  width:1080px;height:1350px;background:var(--bg);color:var(--txt);
  font-family:'IBM Plex Sans',sans-serif;
  padding:60px 60px 60px;display:flex;flex-direction:column;
  -webkit-font-smoothing:antialiased;
}
.top{display:flex;justify-content:space-between;align-items:baseline;
     border-bottom:2px solid var(--line);padding-bottom:12px}
.iss{font-family:'IBM Plex Mono',monospace;font-size:34px;letter-spacing:0;color:var(--dimmer)}
.eyebrow{font-size:34px;letter-spacing:4px;color:var(--teal-dk);
         margin:12px 0 4px;font-weight:600}
.value{font-family:'Archivo',sans-serif;font-size:200px;font-weight:900;letter-spacing:-6px;line-height:0.88}
.value-label{font-size:42px;color:var(--dim);margin-top:8px;line-height:1.2}
h1{font-family:'Archivo',sans-serif;font-weight:800;font-size:64px;letter-spacing:-1px;line-height:1.03;margin:12px 0 0}
em{font-style:normal;color:var(--teal);font-weight:inherit}
.panes{display:flex;flex-direction:column;gap:12px;flex:1 1 auto;min-height:0;margin-top:14px}
.p{background:var(--card);border:2px solid var(--line);border-radius:20px;
   padding:16px 24px 16px;display:flex;flex-direction:column}
.p.grow{flex:1 1 auto;min-height:0}
.lbl{font-size:34px;letter-spacing:2px;color:var(--dimmer);margin-bottom:2px;font-weight:600}
.lbl2{font-size:34px;color:var(--dimmer);margin-bottom:12px;line-height:1.22}
/* horizontale balken. der laengere balken ist bewusst der langweilige,
   damit das auge zuerst den unterschied sieht und dann erst die frequenz liest. */
.rows{display:flex;flex-direction:column;gap:14px;justify-content:center}
.row{display:flex;flex-direction:column;gap:6px}
.rhead{display:flex;justify-content:space-between;align-items:baseline}
.rname{font-size:44px;font-weight:600}
.rsub{font-size:34px;color:var(--dimmer);margin-left:12px;font-weight:400}
.rval{font-family:'Archivo',sans-serif;font-size:50px;font-weight:800}

/* diagrammkacheln, neu am 08.09. eine betonungsfarbe, alles andere grau.
   keine zweite achse, kein raster ausser zwei stillen hilfslinien, und
   beschriftet wird nur der endpunkt, nie jeder punkt. */
.chart{width:100%;display:block}
.chart .grid{stroke:var(--grid);stroke-width:2}
.chart .ctx{fill:none;stroke:var(--ctx);stroke-width:5;stroke-dasharray:14 10;stroke-linejoin:round;stroke-linecap:round}
.chart .ser{fill:none;stroke-width:6;stroke-linejoin:round;stroke-linecap:round}
.chart .ser.teal{stroke:var(--teal)} .chart .ser.red{stroke:var(--red)}
.chart .band{stroke:none}
.chart .band.teal{fill:var(--teal)} .chart .band.red{fill:var(--red)}
.chart .dot{stroke:var(--card);stroke-width:5}
.chart .dot.teal{fill:var(--teal)} .chart .dot.red{fill:var(--red)}
.chart text{font-family:inherit;font-weight:600}
.chart .tag{font-size:36px;fill:var(--txt)}
.chart .tag.dim{fill:var(--dim);font-weight:500}
.bars{display:flex;align-items:flex-end;gap:8px;height:190px;margin-top:10px}
.bars .b{flex:1;background:var(--bar);border-radius:8px 8px 0 0;min-height:6px}
.bars .b.on{background:var(--teal)}
.bars .b.on.red{background:var(--red)}
.blabels{display:flex;gap:8px;margin-top:10px}
.blabels div{flex:1;text-align:center;font-size:34px;color:var(--dimmer);font-weight:500;white-space:nowrap}
.blabels div.on{color:var(--txt);font-weight:600}
/* punktraster fuer anteil am ganzen. hundert punkte, man kann sie zaehlen.
   ein gestapelter balken sagt dasselbe, aber niemand teilt einen balken. */
.dots{display:grid;grid-template-columns:repeat(20,1fr);gap:9px;margin-top:14px}
.dots i{display:block;padding-bottom:100%;border-radius:50%;background:var(--dot)}
.dots i.on{background:var(--teal)}
.dots i.on.red{background:var(--red)}
.dnote{margin-top:16px;font-size:34px;color:var(--dim);font-weight:500}
.dnote b{color:var(--txt);font-weight:600}
.track{height:36px;background:var(--track);border-radius:9px;overflow:hidden}
.fill{height:100%;border-radius:9px;background:var(--faint)}
.fill.teal{background:var(--teal)}
.fill.red{background:var(--red)}
.fill.grey{background:var(--faint)}
.anchor{display:flex;flex-direction:column;gap:10px;flex:1;justify-content:center}
.anchor .a{font-size:44px;line-height:1.24;color:var(--txt)}
.anchor .a em{color:var(--teal);font-weight:600;font-style:normal}
/* im teal-look ist der akzent die textfarbe, die betonung wird markiert */
body[data-look=teal] em,body[data-look=teal] .anchor .a em{background:var(--txt);color:var(--bg);
  padding:0 8px;border-radius:6px;-webkit-box-decoration-break:clone;box-decoration-break:clone}
.note{margin-top:10px;font-size:34px;color:var(--dim);line-height:1.28}
.foot{margin-top:8px;padding-top:8px;border-top:2px solid var(--line);
      font-family:'IBM Plex Mono',monospace;font-size:34px;color:var(--dimmer);line-height:1.3;
      display:flex;justify-content:space-between;align-items:baseline;gap:24px}
.foot b{font-family:'IBM Plex Sans',sans-serif;color:var(--teal);font-weight:600;font-size:34px;white-space:nowrap}
"""
PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><style>{fonts}{css}</style></head>
<body data-look="{look}">
  <div class="top">
    <div class="brand" data-rolle="fuss">{wortmarke}</div>
    <div class="iss">{issue}</div>
  </div>
  <div class="eyebrow">{eyebrow}</div>
  <div class="value" data-rolle="zahl">{value}</div>
  <div class="value-label">{value_label}</div>
  <h1 data-rolle="titel">{headline}</h1>
  <div class="panes">{panes}</div>
  {note}
  <div class="foot">
    <div>{sources}</div>
    <div><b>{site}</b></div>
  </div>
</body></html>"""
def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )
def emphasise(s: str) -> str:
    """*wort* wird teal. bewusst genau eine auszeichnung pro grafik."""
    out = esc(s)
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", out)
def build_compare_pane(block: dict) -> str:
    rows = []
    for r in block.get("rows", []):
        tone = r.get("tone", "grey")
        pct = max(2.0, min(100.0, float(r.get("pct", 0))))
        sub = f'<span class="rsub">{esc(r["sub"])}</span>' if r.get("sub") else ""
        rows.append(
            f'<div class="row">'
            f'<div class="rhead"><div><span class="rname">{esc(r["label"])}</span>{sub}</div>'
            f'<div class="rval">{esc(r["value"])}</div></div>'
            f'<div class="track"><div class="fill {tone}" style="width:{pct:.1f}%"></div></div>'
            f"</div>"
        )
    lbl2 = f'<div class="lbl2">{esc(block["sub"])}</div>' if block.get("sub") else ""
    return (
        f'<div class="p"><div class="lbl">{esc(block["title"])}</div>{lbl2}'
        f'<div class="rows">{"".join(rows)}</div></div>'
    )
def build_anchor_pane(block: dict) -> str:
    lines = "".join(f'<div class="a">{emphasise(l)}</div>' for l in block.get("lines", []))
    lbl2 = f'<div class="lbl2">{esc(block["sub"])}</div>' if block.get("sub") else ""
    return (
        f'<div class="p grow"><div class="lbl">{esc(block["title"])}</div>{lbl2}'
        f'<div class="anchor">{lines}</div></div>'
    )


# ---------------------------------------------------------------- diagramme
# form nach aufgabe, nicht nach geschmack. eine reihe plus grundlinie ist eine
# linie mit betonung. zwoelf perioden nebeneinander sind saeulen. beides traegt
# genau eine farbe, der rest ist grau, und beschriftet wird nur, was die
# aussage traegt.
CH_W, CH_H, CH_PAD = 916, 250, 18


def _pts(vals, lo, hi):
    n = len(vals)
    if n < 2 or hi <= lo:
        return []
    sx = (CH_W - 2 * CH_PAD) / float(n - 1)
    sy = (CH_H - 2 * CH_PAD) / float(hi - lo)
    return [(CH_PAD + i * sx, CH_H - CH_PAD - (v - lo) * sy)
            for i, v in enumerate(vals)]


def _path(pts):
    return "M " + " L ".join("%.1f %.1f" % p for p in pts)


def build_line_pane(block: dict) -> str:
    ser = [float(v) for v in block.get("series", [])]
    base = [float(v) for v in block.get("baseline", [])] or None
    if len(ser) < 2:
        raise ValueError("line pane braucht mindestens zwei werte")
    allv = ser + (base or [])
    lo, hi = min(allv), max(allv)
    pad = (hi - lo) * 0.12 or (abs(hi) * 0.05 or 1.0)
    lo, hi = lo - pad, hi + pad
    tone = block.get("tone", "teal")
    ps = _pts(ser, lo, hi)
    parts = []
    for f in (0.33, 0.66):
        y = CH_PAD + f * (CH_H - 2 * CH_PAD)
        parts.append('<line class="grid" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>'
                     % (CH_PAD, y, CH_W - CH_PAD, y))
    if base:
        pb = _pts(base, lo, hi)
        # die flaeche zwischen reihe und grundlinie. sie ist die aussage,
        # nicht dekoration, deshalb faerbt sie sich nach der richtung.
        band = _path(ps) + " L " + " L ".join(
            "%.1f %.1f" % p for p in reversed(pb)) + " Z"
        richtung = "red" if ser[-1] < base[-1] else "teal"
        parts.append('<path class="band %s" d="%s" fill-opacity="0.26"/>'
                     % (richtung, band))
        parts.append('<path class="ctx" d="%s"/>' % _path(pb))
        parts.append('<text class="tag dim" x="%d" y="%.1f">%s</text>'
                     % (CH_PAD + 6, max(34, pb[0][1] - 26), esc(block.get("base_label", ""))))
    parts.append('<path class="ser %s" d="%s"/>' % (tone, _path(ps)))
    ex, ey = ps[-1]
    parts.append('<circle class="dot %s" cx="%.1f" cy="%.1f" r="13"/>' % (tone, ex, ey))
    end = esc(block.get("end_label", ""))
    if end:
        anchor = "end" if ex > CH_W * 0.6 else "start"
        dx = -30 if anchor == "end" else 30
        # oberhalb, wenn die reihe unten endet, sonst unterhalb. so liegt die
        # zahl nie auf der linie, die sie beschriftet.
        ey_txt = ey - 30 if ey > CH_H * 0.55 else ey + 46
        parts.append('<text class="tag" x="%.1f" y="%.1f" text-anchor="%s">%s</text>'
                     % (ex + dx, min(CH_H - 10, max(36, ey_txt)), anchor, end))
    lbl2 = f'<div class="lbl2">{esc(block["sub"])}</div>' if block.get("sub") else ""
    return (
        f'<div class="p"><div class="lbl">{esc(block["title"])}</div>{lbl2}'
        f'<svg class="chart" viewBox="0 0 {CH_W} {CH_H}">{"".join(parts)}</svg></div>'
    )


def build_dots_pane(block: dict) -> str:
    """Hundert punkte, davon `lit` in der betonungsfarbe. anteil zum zaehlen."""
    total = int(block.get("total", 100))
    lit = max(0, min(total, int(round(float(block.get("lit", 0))))))
    tone = block.get("tone", "teal")
    cells = "".join('<i class="on %s"></i>' % tone if i < lit else "<i></i>"
                    for i in range(total))
    note = ('<div class="dnote">%s</div>' % emphasise(block["note"])
            if block.get("note") else "")
    lbl2 = f'<div class="lbl2">{esc(block["sub"])}</div>' if block.get("sub") else ""
    return (
        f'<div class="p"><div class="lbl">{esc(block["title"])}</div>{lbl2}'
        f'<div class="dots">{cells}</div>{note}</div>'
    )


def build_columns_pane(block: dict) -> str:
    bars = block.get("bars", [])
    if not bars:
        raise ValueError("columns pane braucht balken")
    vals = [abs(float(b.get("value", 0))) for b in bars]
    hi = max(vals) or 1.0
    on = block.get("highlight", len(bars) - 1)
    tone = block.get("tone", "teal")
    cols = "".join(
        '<div class="b%s" style="height:%.1f%%"></div>'
        % ((" on " + tone) if i == on else "", max(2.5, 100.0 * v / hi))
        for i, v in enumerate(vals))
    labs = "".join(
        '<div class="%s">%s</div>' % ("on" if i == on else "", esc(b.get("label", "")))
        for i, b in enumerate(bars))
    lbl2 = f'<div class="lbl2">{esc(block["sub"])}</div>' if block.get("sub") else ""
    return (
        f'<div class="p"><div class="lbl">{esc(block["title"])}</div>{lbl2}'
        f'<div class="bars">{cols}</div><div class="blabels">{labs}</div></div>'
    )

BUILDERS = {"compare": build_compare_pane, "anchor": build_anchor_pane,
            "line": build_line_pane, "columns": build_columns_pane,
            "dots": build_dots_pane}
def render_html(d: dict, look: str = "dunkel") -> str:
    panes = []
    for block in d.get("panes", []):
        kind = block.get("kind", "anchor")
        if kind not in BUILDERS:
            raise ValueError(f"unknown pane kind {kind!r}")
        panes.append(BUILDERS[kind](block))
    note = f'<div class="note">{esc(d["note"])}</div>' if d.get("note") else ""
    # der generator schreibt "KASPA PULSE · AUG 27 2026" in die issue-zeile.
    # seit die marke selbst kaspa pulse heisst, stuende der name doppelt im
    # kopf. hier bleibt nur das datum stehen, bis der generator nachzieht.
    issue = re.sub(r"^\s*KASPA\s+PULSE\s*[·.]?\s*", "", d.get("issue", ""), flags=re.I)
    import wortmarke
    return PAGE.format(
        wortmarke=wortmarke.html("wm"),
        fonts=look_css(look),
        look=look,
        css=CSS,
        issue=issue,
        eyebrow=esc(d.get("eyebrow", "NUMBER OF THE DAY")),
        value=esc(d["value"]),
        value_label=esc(d["value_label"]),
        headline=emphasise(d["headline"]),
        panes="".join(panes),
        note=note,
        sources=esc(d.get("sources", "")),
        site=esc(d.get("site", "kaspapulse.com")),
    )
# ---------------------------------------------------------------- render
def chromium_start(p):
    launch = {}
    for cand in (
        "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
        "/opt/pw-browsers/chromium/chrome-linux/chrome",
    ):
        if Path(cand).exists():
            launch["executable_path"] = cand
            break
    return p.chromium.launch(**launch)


def shoot(html: str, out_png: Path, browser=None, kanal: str = "x") -> None:
    if browser is None:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = chromium_start(p)
            try:
                return shoot(html, out_png, b, kanal)
            finally:
                b.close()
    tmp = out_png.with_suffix(".html")
    tmp.write_text(html, encoding="utf-8")
    page = browser.new_page(viewport={"width": W, "height": H},
                            device_scale_factor=1)
    try:
        page.goto(tmp.resolve().as_uri())
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(250)
        # ueberlaufwaechter. bei groesserer schrift passt mehr text nicht mehr
        # von allein. wenn der inhalt die leinwand sprengt, wird nicht leise
        # abgeschnitten, sondern der lauf bricht ab und nennt den ueberstand.
        # die antwort darauf ist immer, text zu loeschen, nie schrift zu
        # verkleinern.
        overflow = page.evaluate(
            "Math.max(0, document.body.scrollHeight - %d)" % H
        )
        if overflow > 0:
            raise ValueError(
                f"content overflows the {W}x{H} canvas by {overflow}px. "
                f"shorten the json content (headline, anchor lines or note), "
                f"do not shrink the fonts."
            )
        page.screenshot(path=str(out_png))
        # die gemeinsame wache misst das fertige bild (groessen, rand,
        # sichtbarer text), ein verstoss stoppt den lauf
        import content_wache
        content_wache.stoppen(content_wache.pruefe_seite(page, kanal, out_png), out_png.name)
    finally:
        page.close()


# ---------------------------------------------------------------- look-takt
# die zahl des tages laeuft auf x und discord (telegram bekommt das
# discord-bild). jeder kanal hat seinen takt in data/look-takt.json, serie
# "zahl", einen schritt versetzt zur tagesgrafik (look_takt.VERSATZ).
KANAELE = ("x", "discord")


def kanal_pfad(out: Path, kanal: str) -> Path:
    """x behaelt den alten namen (x_post.py und das archiv nehmen ihn), discord
    bekommt den kanal im namen."""
    return out if kanal == "x" else out.with_name("%s-%s%s" % (out.stem, kanal, out.suffix))


def kanaele_rendern(d: dict, out: Path, tag: str, speicher=None, merken=False):
    """rendert ein bild je kanal im look aus seinem takt. mit merken wird der
    takt im speicher weitergeschoben und geschrieben. gibt {kanal: (pfad, look)}."""
    import look_takt
    from playwright.sync_api import sync_playwright
    sp = look_takt.lesen() if speicher is None else speicher
    looks = look_takt.looks_fuer(sp, "zahl", tag, KANAELE)
    aus = {}
    with sync_playwright() as p:
        b = chromium_start(p)
        try:
            for k in KANAELE:
                ziel = kanal_pfad(out, k)
                shoot(render_html(d, looks[k]), ziel, b, k)
                ziel.with_suffix(".html").unlink(missing_ok=True)
                aus[k] = (ziel, looks[k])
        finally:
            b.close()
    if merken:
        for k in KANAELE:
            look_takt.merken(sp, "zahl", k, tag)
        if speicher is None:
            look_takt.schreiben(sp)
    return aus


def kontaktbogen_bilder(ziel, browser, payloads, looks=("dunkel", "hell", "teal")):
    """[(beschriftung, png)] fuer den kontaktbogen. ein payload, der ueberlaeuft,
    steht als fehler in der liste."""
    aus = []
    Path(ziel).mkdir(parents=True, exist_ok=True)
    for name, d in payloads:
        for lk in looks:
            png = Path(ziel) / ("zahl-%s-%s.png" % (name, lk))
            try:
                shoot(render_html(d, lk), png, browser)
                png.with_suffix(".html").unlink(missing_ok=True)
                aus.append(("zahl des tages %s %s" % (name, lk), png))
            except ValueError as exc:
                aus.append(("zahl des tages %s %s FEHLER %s" % (name, lk, exc), None))
    return aus


def selbsttest() -> int:
    """Die beiden Wachen, ohne Netz und ohne Chromium."""
    fehler = []

    def ok(was, bedingung):
        print(("  ok   " if bedingung else "  FEHL ") + was)
        if not bedingung:
            fehler.append(was)

    def hebt(was, text):
        try:
            assert_punctuation(text, "test")
        except ValueError as exc:
            print("  ok   %s (%s)" % (was, str(exc)[:60]))
            return
        print("  FEHL " + was + "  kein abbruch, obwohl erwartet")
        fehler.append(was)

    print("number of the day, wachen")
    hebt("percent faellt auf", "hashrate up 42 percent against june")
    hebt("auch percentage faellt auf", "down 3 percentage points")
    hebt("auch gross geschrieben", "Percent of the supply")
    hebt("auch in der mitte eines satzes", "that is 99 percent, counted")
    ok("das prozentzeichen geht durch",
       assert_punctuation("hashrate up 42% against june", "test") is None)
    ok("percentile bleibt erlaubt",
       assert_punctuation("the 90th percentile of all blocks", "test") is None)
    ok("percentpoints bleibt erlaubt",
       assert_punctuation("up 3 percentpoints", "test") is None)
    # Abgleich gegen die Liste in tagesgrafik.py, damit die beiden nicht
    # auseinanderlaufen. Die zwei bewusst ausgenommenen Woerter stehen
    # hier beim Namen, nicht als stilles Loch.
    AUSGENOMMEN = ("the second", "the moment")
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from tagesgrafik import ECHTZEIT          # noqa: E402
    except ImportError as exc:
        print("  ok   abgleich mit tagesgrafik uebersprungen (%s)" % exc)
    else:
        fehlend = [w for w in ECHTZEIT
                   if w not in AUSGENOMMEN and not _ECHTZEIT.search(w)]
        ok("jedes echtzeitwort der tagesgrafik faellt auch hier auf, "
           "ausser %s" % " und ".join(AUSGENOMMEN), not fehlend)

    hebt("right now faellt auf", "petahash per second securing the network right now")
    hebt("currently faellt auf", "the network currently runs at 342 PH")
    hebt("at the moment faellt auf", "at the moment the heap is shrinking")
    hebt("live faellt auf", "the live emission numbers are on the halving page")
    hebt("real time faellt auf", "counted in real time")
    hebt("real-time faellt auf", "a real-time reading")
    hebt("around the clock faellt auf", "we watch it around the clock")
    hebt("24/7 faellt auf", "the bot runs 24/7")
    # der threads-post vom 20.10. 17:10, wortgleich (Ben, 21.10.2026)
    hebt("now faellt auf", "294,512 kaspa addresses now hold at least 100 KAS.")
    ok("known faellt nicht auf, now steckt nur drin",
       assert_punctuation("a known address on 16 oct 2026", "test") is None)
    ok("nowhere faellt nicht auf, now steckt nur drin",
       assert_punctuation("the heap went nowhere on 16 oct 2026", "test") is None)
    ok("now steht im treffer, nicht das ganze wort",
       echtzeit_treffer("294,512 kaspa addresses now hold at least 100 KAS.") == "now")
    ok("ein stichtag geht durch",
       assert_punctuation("petahash per second on 16 oct 2026", "test") is None)
    ok("ohne zeitangabe geht durch",
       assert_punctuation("petahash per second securing the network", "test") is None)
    # die beiden woerter aus der tagesgrafik-liste, die hier gewoehnliche
    # sprache sind und deshalb durchgehen muessen
    ok("the second one bleibt erlaubt",
       assert_punctuation("almost nobody posts the second one", "test") is None)
    ok("the moment bleibt erlaubt",
       assert_punctuation("the moment it lands on a block score", "test") is None)
    ok("delivered bleibt erlaubt, live steckt nicht drin",
       assert_punctuation("every block delivered since august", "test") is None)
    hebt("gedankenstrich faellt weiter auf", "hashrate up — the reward fell")
    hebt("doppelpunkt faellt weiter auf", "balance: 1,442 KAS")
    ok("eine uhrzeit stoert nicht",
       assert_punctuation("the close at 23:59 utc", "test") is None)
    ok("eine adresse stoert nicht",
       assert_punctuation("more on kaspapulse.com/halving.html", "test") is None)
    # die wache greift auch tief im payload, nicht nur an der oberflaeche
    try:
        walk_and_check({"panes": [{"kind": "dots",
                                   "note": "*96 percent* mined."}]})
        ok("die wache greift tief im payload", False)
    except ValueError as exc:
        ok("die wache greift tief im payload", "panes[0].note" in str(exc))
    print("%d fehler" % len(fehler))
    return len(fehler)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/number-of-day.json")
    ap.add_argument("--output", default="graphics/number-of-day.png")
    ap.add_argument("--keep-html", action="store_true")
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--takt-merken", action="store_true",
                    help="look-takt in data/look-takt.json weiterschieben (nur der taegliche lauf)")
    args = ap.parse_args()
    if args.selbsttest:
        return 1 if (selbsttest() or look_selbsttest()) else 0
    src = Path(args.input)
    d = json.loads(src.read_text(encoding="utf-8"))
    walk_and_check(d)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.keep_html:
        out.with_suffix(".html").write_text(render_html(d), encoding="utf-8")
    import datetime as dt
    tag = dt.datetime.now(dt.timezone.utc).date().isoformat()
    for kanal, (pfad, look) in kanaele_rendern(d, out, tag, merken=args.takt_merken).items():
        size_kb = pfad.stat().st_size / 1024
        print(f"wrote {pfad} ({W}x{H}, {size_kb:.0f} kB), {kanal} im look {look}")
    return 0


def look_selbsttest() -> int:
    """look-takt der zahl des tages. rendert nur, wenn playwright da ist."""
    fehler = 0

    def ok(was, bedingung):
        nonlocal fehler
        print(("  ok   " if bedingung else "  FEHL ") + was)
        fehler += 0 if bedingung else 1

    print("number of the day, looks")
    d = {"issue": "16 OCT 2026", "value": "96.6%", "value_label": "of all KAS is mined",
         "headline": "almost *all of it* is out", "sources": "source kaspa rest api, 16 oct 2026",
         "panes": [{"kind": "dots", "title": "MINED", "lit": 97, "note": "*97* of 100"}]}
    for lk in LOOK_FARBEN:
        h = render_html(d, lk)
        ok("look %s, farben und schriften eingebettet" % lk,
           LOOK_FARBEN[lk]["bg"] in h and "@font-face" in h and "googleapis" not in h)
    ok("kein hartes hex im css, alles ueber die look-variablen",
       not re.search(r"#[0-9A-Fa-f]{6}", CSS))
    ok("discord-bild traegt den kanal im namen, x den alten",
       kanal_pfad(Path("g/number-of-day.png"), "discord").name == "number-of-day-discord.png"
       and kanal_pfad(Path("g/number-of-day.png"), "x").name == "number-of-day.png")
    try:
        import playwright  # noqa: F401
    except ImportError:
        print("  playwright fehlt, render-probe uebersprungen")
        return fehler
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        sp = {"kanaele": {}}
        r = kanaele_rendern(d, Path(td) / "number-of-day.png", "2026-10-17", sp, merken=True)
        ok("x und discord gerendert", all(p.exists() for p, _ in r.values()))
        ok("zahl startet versetzt, x hell am ersten tag (%s)" % r["x"][1], r["x"][1] == "hell")
        ok("takt im speicher weitergeschoben", sp["kanaele"]["zahl/x"][-1]["datum"] == "2026-10-17")
    return fehler
if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as e:
        print(f"FAILED {e}", file=sys.stderr)
        sys.exit(1)
