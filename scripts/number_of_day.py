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
# ---------------------------------------------------------------- template
# groessen in px bei 1080 breite. als anteil gelesen, damit die regel auch
# gilt, falls jemand die leinwand aendert. heldenzahl 190 (17.6%),
# ueberschrift 78 (7.2%), fliesstext 40 bis 52 (3.7 bis 4.8%),
# kopf und fusszeile 30 (2.8%). nichts darunter.
CSS = """
:root{
  --bg:#080B0F; --card:#0E141A; --line:#1C242D;
  --teal:#49EACB; --teal-dk:#1E9E88; --red:#E36A6A;
  --txt:#FFFFFF; --dim:#9AA2AA; --dimmer:#7C858F; --faint:#4A535E;
}
*{margin:0;padding:0;box-sizing:border-box}
body{
  width:1080px;height:1350px;background:var(--bg);color:var(--txt);
  font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
  padding:46px 52px 38px;display:flex;flex-direction:column;
  -webkit-font-smoothing:antialiased;
}
.top{display:flex;justify-content:space-between;align-items:baseline;
     border-bottom:1px solid var(--line);padding-bottom:14px}
.brand{font-size:30px;letter-spacing:6px;font-weight:700}
.brand span{color:var(--teal)}
.iss{font-size:26px;letter-spacing:2px;color:var(--dimmer)}
.eyebrow{font-size:30px;letter-spacing:5px;color:var(--teal-dk);
         margin:22px 0 10px;font-weight:700}
.value{font-size:190px;font-weight:700;letter-spacing:-7px;line-height:0.88}
.value-label{font-size:44px;color:var(--dim);margin-top:14px;line-height:1.25}
h1{font-size:78px;letter-spacing:-2px;line-height:1.04;margin:20px 0 0}
em{font-style:normal;color:var(--teal);font-weight:700}
.panes{display:flex;flex-direction:column;gap:14px;flex:1;margin-top:24px}
.p{background:var(--card);border:1px solid var(--line);border-radius:20px;
   padding:20px 26px 18px;display:flex;flex-direction:column}
.p.grow{flex:1}
.lbl{font-size:30px;letter-spacing:3px;color:var(--dimmer);margin-bottom:2px}
.lbl2{font-size:34px;color:var(--dimmer);margin-bottom:14px;line-height:1.25}
/* horizontale balken. der laengere balken ist bewusst der langweilige,
   damit das auge zuerst den unterschied sieht und dann erst die frequenz liest. */
.rows{display:flex;flex-direction:column;gap:18px;justify-content:center}
.row{display:flex;flex-direction:column;gap:7px}
.rhead{display:flex;justify-content:space-between;align-items:baseline}
.rname{font-size:46px;font-weight:700}
.rsub{font-size:34px;color:var(--dimmer);margin-left:12px;font-weight:400}
.rval{font-size:52px;font-weight:700}
.track{height:38px;background:#141A21;border-radius:9px;overflow:hidden}
.fill{height:100%;border-radius:9px;background:var(--faint)}
.fill.teal{background:var(--teal)}
.fill.red{background:var(--red)}
.fill.grey{background:#39424C}
.anchor{display:flex;flex-direction:column;gap:12px;flex:1;justify-content:center}
.anchor .a{font-size:46px;line-height:1.28;color:var(--txt)}
.anchor .a em{color:var(--teal);font-weight:700;font-style:normal}
.note{margin-top:12px;font-size:34px;color:var(--dim);line-height:1.3}
.foot{margin-top:14px;padding-top:12px;border-top:1px solid var(--line);
      font-size:30px;color:var(--dimmer);line-height:1.4;
      display:flex;justify-content:space-between;align-items:baseline}
.foot b{color:var(--teal);font-weight:700;font-size:30px}
"""
PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><style>{css}</style></head>
<body>
  <div class="top">
    <div class="brand">KASPA <span>PULSE</span></div>
    <div class="iss">{issue}</div>
  </div>
  <div class="eyebrow">{eyebrow}</div>
  <div class="value">{value}</div>
  <div class="value-label">{value_label}</div>
  <h1>{headline}</h1>
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
BUILDERS = {"compare": build_compare_pane, "anchor": build_anchor_pane}
def render_html(d: dict) -> str:
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
    return PAGE.format(
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
def shoot(html: str, out_png: Path) -> None:
    from playwright.sync_api import sync_playwright
    tmp = out_png.with_suffix(".html")
    tmp.write_text(html, encoding="utf-8")
    launch = {}
    for cand in (
        "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
        "/opt/pw-browsers/chromium/chrome-linux/chrome",
    ):
        if Path(cand).exists():
            launch["executable_path"] = cand
            break
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch)
        page = browser.new_page(viewport={"width": W, "height": H},
                                device_scale_factor=1)
        page.goto(tmp.resolve().as_uri())
        page.wait_for_timeout(350)
        # ueberlaufwaechter. bei groesserer schrift passt mehr text nicht mehr
        # von allein. wenn der inhalt die leinwand sprengt, wird nicht leise
        # abgeschnitten, sondern der lauf bricht ab und nennt den ueberstand.
        # die antwort darauf ist immer, text zu loeschen, nie schrift zu
        # verkleinern.
        overflow = page.evaluate(
            "Math.max(0, document.body.scrollHeight - %d)" % H
        )
        if overflow > 0:
            browser.close()
            raise ValueError(
                f"content overflows the {W}x{H} canvas by {overflow}px. "
                f"shorten the json content (headline, anchor lines or note), "
                f"do not shrink the fonts."
            )
        page.screenshot(path=str(out_png))
        browser.close()
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/number-of-day.json")
    ap.add_argument("--output", default="graphics/number-of-day.png")
    ap.add_argument("--keep-html", action="store_true")
    args = ap.parse_args()
    src = Path(args.input)
    d = json.loads(src.read_text(encoding="utf-8"))
    walk_and_check(d)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    html = render_html(d)
    shoot(html, out)
    if not args.keep_html:
        out.with_suffix(".html").unlink(missing_ok=True)
    size_kb = out.stat().st_size / 1024
    print(f"wrote {out} ({W}x{H}, {size_kb:.0f} kB)")
    return 0
if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as e:
        print(f"FAILED {e}", file=sys.stderr)
        sys.exit(1)
