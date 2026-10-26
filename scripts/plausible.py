#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plausible.py, Besuchszaehlung mit Plausible auf allen oeffentlichen Seiten (Ben, 26.10.2026).

WARUM
Die Anzeige ad1-whales-v2 brachte 29 Besucher und keine belegte Anmeldung,
und kaspapulse.com hat bis dahin gar nichts gezaehlt. Plausible zaehlt ohne
Cookies und ohne personenbezogene Daten.

WAS ES TUT
1. Setzt das Snippet aus Plausible (Methode Script) zwischen die Marken
   <!--AUTO:plausible--> und <!--/AUTO:plausible--> direkt vor </head>.
   Das Snippet ist oeffentlich und kein Secret. Ein zweiter Lauf aendert nichts.
2. Prueft, dass jede Seite mit einem Brevo-Anmeldeformular nach j.success das
   Ereignis "Signup" sendet, mit page (Pfad) und utm_campaign (verstecktes
   Feld). Nie die E-Mail-Adresse. Die Zeile selbst steht im Handler der Seite
   (SIGNUP unten), dieses Skript setzt sie nur dort ein, wo sie fehlt.

Die Seitenliste ist dieselbe wie in seo_seiten.py (alle *.html ausser
utm-test.html, dazu Wochenseiten, Archiv und method), plus EXTRA.
Startseite, Wochenseiten, Archiv und method erben den Block aus dem Rahmen
von index.html, startseite.py und archiv.py lassen ihn stehen.

    python3 scripts/plausible.py              einsetzen
    python3 scripts/plausible.py --pruefen    nur pruefen, Exit 1 wenn etwas fehlt
    python3 scripts/plausible.py --selbsttest
"""
import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

A, B = "<!--AUTO:plausible-->", "<!--/AUTO:plausible-->"
SNIPPET = """<!-- Privacy-friendly analytics by Plausible -->
<script async src="https://plausible.io/js/pa-o1R2wMI1l5uanq2mIzp0P.js"></script>
<script>
  window.plausible=window.plausible||function(){(plausible.q=plausible.q||[]).push(arguments)},plausible.init=plausible.init||function(i){plausible.o=i||{}};
  plausible.init()
</script>"""
BLOCK = A + "\n" + SNIPPET + "\n" + B

# seiten in eigenem ordner, die nicht von archiv.py kommen
EXTRA = ["whales/index.html"]

# das ereignis nach erfolgreicher anmeldung. FORM ist der name der formular-
# variablen im handler. utm_campaign kommt aus dem versteckten feld des
# formulars, sonst aus dem ersten formular der seite (utm.js), sonst "none".
SIGNUP = ('try { if (window.plausible) plausible("Signup", { props: { page: location.pathname, '
          'utm_campaign: ((FORM.querySelector(\'[name="UTM_CAMPAIGN"]\') || document.getElementById("utmCampaign") || {}).value || "none") } }); } '
          'catch (kpE) {}')
MARKE_SIGNUP = 'plausible("Signup"'

# erfolgszweige der bestehenden handler: (muster, name der formularvariablen)
ZWEIGE = [
    (re.compile(r"if \(j && j\.success\) \{\n"), "form"),     # index.html und alles aus seinem rahmen
    (re.compile(r"if \(j\.success\) \{ "), "form"),           # unterseiten (subForm)
]
ZWEIG_CAPTURE = (re.compile(r"if \(j && j\.success\) \{\n"), "f")


def seiten():
    import seo_seiten
    aus = list(seo_seiten.seiten())
    aus += [p for p in EXTRA if (REPO / p).exists() and p not in aus]
    return aus


def kopf_setzen(s):
    if A in s:
        i, j = s.index(A), s.index(B) + len(B)
        return s[:i] + BLOCK + s[j:]
    if "</head>" not in s:
        raise ValueError("kein </head>")
    return s.replace("</head>", BLOCK + "\n</head>", 1)


def signup_setzen(s, zweige=ZWEIGE):
    """Setzt SIGNUP in jeden Erfolgszweig, der es noch nicht hat."""
    for muster, var in zweige:
        def rein(m):
            rest = s[m.end():m.end() + 400]
            if rest.lstrip().startswith("try { if (window.plausible)"):
                return m.group(0)
            if m.group(0).endswith("\n"):
                z = re.match(r"[ \t]*", rest).group(0)
                return m.group(0) + z + SIGNUP.replace("FORM", var) + "\n"
            return m.group(0) + SIGNUP.replace("FORM", var) + " "
        s = muster.sub(rein, s)
    return s


def hat_formular(s):
    return "sibforms.com" in s and "success" in s


def signup_fehlt(s):
    """Anzahl Erfolgszweige ohne Signup-Ereignis."""
    n = 0
    for muster, _ in ZWEIGE:
        for m in muster.finditer(s):
            if not s[m.end():m.end() + 400].lstrip().startswith("try { if (window.plausible)"):
                n += 1
    return n


def lauf(nur_pruefen=False):
    fehler, neu = [], []
    for p in seiten() + ["capture.js"]:
        pfad = REPO / p
        s = pfad.read_text(encoding="utf-8")
        if p == "capture.js":
            t = signup_setzen(s, [ZWEIG_CAPTURE])
        else:
            t = kopf_setzen(s)
            if hat_formular(s):
                t = signup_setzen(t)
        if t != s:
            if nur_pruefen:
                fehler.append(p)
            else:
                pfad.write_text(t, encoding="utf-8")
                neu.append(p)
    if nur_pruefen:
        for p in fehler:
            print("fehlt oder weicht ab, %s" % p)
        print("plausible auf allen seiten" if not fehler else "%d seite(n) ohne plausible oder signup" % len(fehler))
        return 1 if fehler else 0
    for p in neu:
        print("neu, %s" % p)
    print("%d datei(en) geschrieben" % len(neu) if neu else "alles auf stand")
    return 0


def selbsttest():
    f = []

    def ok(name, bed, info=""):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, ("  " + str(info)) if not bed and info else ""))
        if not bed:
            f.append(name)

    k = "<html><head><title>x</title></head><body></body></html>"
    k1 = kopf_setzen(k)
    ok("block vor </head>", k1.index(A) < k1.index("</head>") and SNIPPET in k1)
    ok("zweiter lauf aendert nichts", kopf_setzen(k1) == k1)
    alt = k1.replace("pa-o1R2wMI1l5uanq2mIzp0P", "pa-alt")
    ok("alter block wird ersetzt", kopf_setzen(alt) == k1)
    ok("nur ein skript von plausible.io", k1.count("plausible.io/js/") == 1 and k1.count("<script") == 2)
    ok("keine cookies, kein weiteres skript", "cookie" not in SNIPPET.lower() and SNIPPET.count("src=") == 1)

    h1 = ('      .then(function (j) {\n          if (j && j.success) {\n            msg.textContent = "ok";\n')
    t1 = signup_setzen(h1)
    ok("signup im rahmen der startseite", MARKE_SIGNUP in t1 and "form.querySelector" in t1)
    ok("signup mit gleichem einzug", '\n            try { if (window.plausible)' in t1)
    ok("signup nur einmal", signup_setzen(t1) == t1 and t1.count(MARKE_SIGNUP) == 1)
    h2 = '      if (j.success) { msg.innerHTML = "ok"; form.reset(); }'
    t2 = signup_setzen(h2)
    ok("signup auf unterseiten", t2.count(MARKE_SIGNUP) == 1 and signup_setzen(t2) == t2 and signup_fehlt(t2) == 0)
    t3 = signup_setzen(h1, [ZWEIG_CAPTURE])
    ok("capture.js nimmt f", "(f.querySelector" in t3)
    ok("keine e-mail im ereignis", "EMAIL" not in SIGNUP and "email" not in SIGNUP.lower())
    ok("eigenschaften page und utm_campaign", "page: location.pathname" in SIGNUP and "utm_campaign:" in SIGNUP)
    ok("fehlendes signup faellt auf", signup_fehlt(h2) == 1)
    ok("seitenliste ohne utm-test", "utm-test.html" not in seiten() and "index.html" in seiten())
    print("")
    print("%d fehler" % len(f) if f else "alle testfaelle bestanden")
    return 1 if f else 0


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
