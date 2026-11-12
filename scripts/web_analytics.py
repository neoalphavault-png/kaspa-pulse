#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""web_analytics.py, Besuchszaehlung mit Cloudflare Web Analytics auf allen
oeffentlichen Seiten (Ben, 12.11.2026).

WARUM
Die Testphase der bisherigen Zaehlung endet um den 16.11.2026 und wird nicht
gebucht. kaspapulse.com hatte seit dem 26.10. 246 Besucher, dafuer reicht die
kostenlose Zaehlung von Cloudflare. Cloudflare wertet keine UTM-Parameter und
keine eigenen Ereignisse aus. Die Zuordnung von Anmeldungen zu Kampagnen
laeuft deshalb nur noch ueber die versteckten UTM-Felder im Brevo-Formular.

WAS ES TUT
1. Setzt das Snippet von Cloudflare zwischen die Marken
   <!--AUTO:analytics--> und <!--/AUTO:analytics--> direkt vor </body>.
   Das Token ist oeffentlich und kein Secret. Ein zweiter Lauf aendert nichts.
2. Entfernt die alte Zaehlung: den Block im Kopf (alte Marke) und die Zeile
   mit dem Anmelde-Ereignis in jedem Handler, auch in capture.js. Die
   Anmeldung selbst und die UTM-Felder bleiben, wie sie sind.

Die Seitenliste ist dieselbe wie in seo_seiten.py (alle *.html, dazu
Wochenseiten, Archiv und method), plus EXTRA. Wochenseiten, Archiv und
method erben den Block aus dem Rahmen von index.html.

    python3 scripts/web_analytics.py              einsetzen
    python3 scripts/web_analytics.py --pruefen    nur pruefen, Exit 1 wenn etwas fehlt
    python3 scripts/web_analytics.py --selbsttest
"""
import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

A, B = "<!--AUTO:analytics-->", "<!--/AUTO:analytics-->"
SNIPPET = ("<!-- Cloudflare Web Analytics --><script type='module' "
           "src='https://static.cloudflareinsights.com/beacon.min.js' "
           "data-cf-beacon='{\"token\": \"c995d86f86b541f7bfab7cb07d362bde\"}'></script>"
           "<!-- End Cloudflare Web Analytics -->")
BLOCK = A + "\n" + SNIPPET + "\n" + B

# seiten in eigenem ordner, die nicht von archiv.py kommen
EXTRA = ["whales/index.html"]

# die alte zaehlung (bis 12.11.2026). der name wird zusammengesetzt, damit
# dieser baustein selbst keinen treffer fuer die suche nach dem alten dienst
# liefert (Ben: ausserhalb von berichte/ kein treffer mehr).
_ALT = "pl" + "ausible"
ALT_A, ALT_B = "<!--AUTO:%s-->" % _ALT, "<!--/AUTO:%s-->" % _ALT
# die zeile im erfolgszweig eines anmelde-handlers, mit fuehrendem einzug und
# folgendem zeilenumbruch oder leerzeichen
ALT_SIGNUP = re.compile(r"[ \t]*try \{ if \(window\.%s\) %s\(\"Signup\".*?catch \(kpE\) \{\}(\n| )"
                        % (_ALT, _ALT))


def seiten():
    import seo_seiten
    aus = list(seo_seiten.seiten())
    aus += [p for p in EXTRA if (REPO / p).exists() and p not in aus]
    return aus


def alt_entfernen(s):
    """Block im Kopf und Anmelde-Ereignisse der alten Zaehlung raus."""
    if ALT_A in s and ALT_B in s:
        i, j = s.index(ALT_A), s.index(ALT_B) + len(ALT_B)
        if s[j:j + 1] == "\n":
            j += 1
        s = s[:i] + s[j:]

    # eigene zeile: ganz raus, mit einzug und umbruch; mitten in der zeile:
    # das ereignis raus, ein leerzeichen bleibt zwischen den nachbarn
    return ALT_SIGNUP.sub(lambda m: "" if m.group(1) == "\n" else " ", s)


def block_setzen(s):
    if A in s:
        i, j = s.index(A), s.index(B) + len(B)
        return s[:i] + BLOCK + s[j:]
    if "</body>" not in s:
        raise ValueError("kein </body>")
    k = s.rindex("</body>")
    return s[:k] + BLOCK + "\n" + s[k:]


def setzen(s):
    return block_setzen(alt_entfernen(s))


def lauf(nur_pruefen=False):
    fehler, neu = [], []
    for p in seiten() + ["capture.js"]:
        pfad = REPO / p
        s = pfad.read_text(encoding="utf-8")
        t = alt_entfernen(s) if p == "capture.js" else setzen(s)
        rest = _ALT in t.lower()
        if t != s or rest:
            if nur_pruefen or rest:
                fehler.append(p + (" (alte zaehlung steht noch drin)" if rest else ""))
            if not nur_pruefen:
                pfad.write_text(t, encoding="utf-8")
                neu.append(p)
    for p in neu:
        print("neu, %s" % p)
    if fehler:
        for p in fehler:
            print("fehlt oder weicht ab, %s" % p)
        print("%d datei(en) nicht auf stand" % len(fehler))
        return 1
    print("cloudflare web analytics auf allen seiten" if nur_pruefen or not neu else
          "%d datei(en) geschrieben" % len(neu))
    return 0


def selbsttest():
    f = []

    def ok(name, bed, info=""):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, ("  " + str(info)) if not bed and info else ""))
        if not bed:
            f.append(name)

    alt_kopf = ("<html><head><title>x</title>\n%s\n<script async src=\"https://%s.io/js/pa-x.js\"></script>\n%s\n"
                "</head><body><p>a</p></body></html>" % (ALT_A, _ALT, ALT_B))
    t = setzen(alt_kopf)
    ok("alter block im kopf ist raus", ALT_A not in t and _ALT not in t, t)
    ok("block direkt vor </body>", t.index(A) < t.index("</body>") and t.endswith(B + "\n</body></html>"), t)
    ok("zweiter lauf aendert nichts", setzen(t) == t)
    ok("nur ein skript von cloudflare, mit token", t.count("static.cloudflareinsights.com/beacon.min.js") == 1
       and "c995d86f86b541f7bfab7cb07d362bde" in t and t.count("<script") == 1)
    ok("snippet genau wie von Ben vorgegeben", SNIPPET == (
        "<!-- Cloudflare Web Analytics --><script type='module' src='https://static.cloudflareinsights.com/"
        "beacon.min.js' data-cf-beacon='{\"token\": \"c995d86f86b541f7bfab7cb07d362bde\"}'></script>"
        "<!-- End Cloudflare Web Analytics -->"))
    ereignis = ('try { if (window.%s) %s("Signup", { props: { page: location.pathname, utm_campaign: '
                '((form.querySelector(\'[name="UTM_CAMPAIGN"]\') || {}).value || "none") } }); } catch (kpE) {}'
                % (_ALT, _ALT))
    h1 = ('          if (j && j.success) {\n            %s\n            msg.textContent = "ok";\n' % ereignis)
    t1 = alt_entfernen(h1)
    ok("ereignis im rahmen der startseite raus, rest bleibt", t1 ==
       '          if (j && j.success) {\n            msg.textContent = "ok";\n', repr(t1))
    h2 = '      if (j.success) { %s msg.innerHTML = "ok"; form.reset(); }' % ereignis
    t2 = alt_entfernen(h2)
    ok("ereignis auf unterseiten raus, rest bleibt", t2 ==
       '      if (j.success) { msg.innerHTML = "ok"; form.reset(); }', repr(t2))
    utm = '<input type="hidden" name="UTM_CAMPAIGN" id="utmCampaign" value="none">'
    ok("utm-felder bleiben", utm in setzen("<html><head></head><body>%s</body></html>" % utm))
    ok("ohne </body> stoppt", _stoppt(lambda: block_setzen("<html><head></head></html>")))
    ok("seitenliste mit startseite und whales", "index.html" in seiten() and "whales/index.html" in seiten())
    print("")
    print("%d fehler" % len(f) if f else "alle testfaelle bestanden")
    return 1 if f else 0


def _stoppt(fn):
    try:
        fn()
        return False
    except ValueError:
        return True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pruefen", action="store_true")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    return lauf(a.pruefen)


if __name__ == "__main__":
    sys.exit(main())
