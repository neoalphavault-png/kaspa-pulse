#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""utm_fields.py, haengt die drei versteckten Felder an jedes Brevo-Formular.

Das Anmeldeformular steht auf siebzehn Seiten, jedes Mal derselbe Block.
Wer die Felder von Hand einbaut, hat sie beim naechsten Mal auf sechzehn.
Dieses Skript baut sie ueberall ein, wo ein Formular mit id="subForm" steht,
und bindet utm.js ein, das sie vor dem Absenden fuellt.

Der Lauf ist wiederholbar: was schon da ist, bleibt unveraendert.

⚠️ EINE HAND MUSS BEN ANLEGEN
Brevo nimmt nur Felder an, die im Formular selbst angelegt sind. Die drei
Kontaktattribute UTM_SOURCE, UTM_MEDIUM und UTM_CAMPAIGN (Typ Text) muessen
einmal in Brevo unter Kontakte > Einstellungen > Attribute angelegt und im
Formular-Editor als versteckte Felder ergaenzt werden. Bis dahin schickt die
Seite die Werte mit und Brevo verwirft sie still. Das Formular funktioniert
in beiden Faellen; gemessen wird erst danach.

    python3 scripts/utm_fields.py
    python3 scripts/utm_fields.py --selftest
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

FORM = re.compile(r'<form id="subForm"[\s>]')
EMAIL = re.compile(r'(\s*)(<input type="email" name="EMAIL"[^>]*>)')
SKRIPT = '<script src="/utm.js" defer></script>'
MARKE = 'name="UTM_SOURCE"'

FELDER = (
    '<input type="hidden" name="UTM_SOURCE" id="utmSource" value="direct">',
    '<input type="hidden" name="UTM_MEDIUM" id="utmMedium" value="none">',
    '<input type="hidden" name="UTM_CAMPAIGN" id="utmCampaign" value="">',
)


def setz_felder(html):
    """Fuegt die drei versteckten Felder direkt hinter das E-Mail-Feld ein.
    Gibt (text, zahl der ergaenzten formulare) zurueck."""
    if not FORM.search(html):
        return html, 0
    if MARKE in html:
        return html, 0

    n = [0]

    def ersatz(m):
        n[0] += 1
        einzug = m.group(1)
        block = "".join(einzug + f for f in FELDER)
        return m.group(1) + m.group(2) + block

    html = EMAIL.sub(ersatz, html)
    return html, n[0]


def setz_skript(html):
    """Bindet utm.js vor </body> ein, genau einmal."""
    if SKRIPT in html:
        return html, 0
    i = html.rfind("</body>")
    if i < 0:
        return html, 0
    return html[:i] + SKRIPT + "\n" + html[i:], 1


def seiten():
    return sorted(f for f in os.listdir(REPO) if f.endswith(".html"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selbsttest()

    if not os.path.exists(os.path.join(REPO, "utm.js")):
        print("FEHL utm.js fehlt im Wurzelverzeichnis")
        return 1

    geaendert = 0
    mit_formular = 0
    for datei in seiten():
        pfad = os.path.join(REPO, datei)
        with open(pfad, encoding="utf-8") as fh:
            alt = fh.read()
        if not FORM.search(alt):
            continue
        mit_formular += 1
        neu, nf = setz_felder(alt)
        neu, ns = setz_skript(neu)
        if neu == alt:
            print("  ok   %-32s unveraendert" % datei)
            continue
        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write(neu)
        geaendert += 1
        print("  neu  %-32s %d formular(e), skript %s" % (datei, nf, "ja" if ns else "war da"))
    print("\n%d Seiten mit Formular, %d geaendert" % (mit_formular, geaendert))
    if mit_formular == 0:
        print("FEHL kein Formular gefunden, id=subForm umbenannt?")
        return 1
    return 0


def selbsttest():
    schlecht = 0

    def pruefe(name, ist, soll):
        nonlocal schlecht
        if ist != soll:
            schlecht += 1
            print("  FEHL %s\n    ist  %r\n    soll %r" % (name, ist, soll))
        else:
            print("  ok   %s" % name)

    roh = ('<form id="subForm" action="x" method="POST">\n'
           '      <input type="email" name="EMAIL" placeholder="you@email.com" required>\n'
           '      <button type="submit">get it</button>\n'
           '    </form>')
    neu, n = setz_felder(roh)
    pruefe("ein formular ergaenzt", n, 1)
    pruefe("quelle drin", 'name="UTM_SOURCE" id="utmSource" value="direct"' in neu, True)
    pruefe("gattung drin", 'name="UTM_MEDIUM" id="utmMedium"' in neu, True)
    pruefe("serie drin", 'name="UTM_CAMPAIGN" id="utmCampaign"' in neu, True)
    pruefe("felder sitzen hinter der adresse",
           neu.index('name="EMAIL"') < neu.index('name="UTM_SOURCE"'), True)
    pruefe("felder sitzen noch im formular",
           neu.index('name="UTM_CAMPAIGN"') < neu.index("</form>"), True)
    pruefe("einzug uebernommen", "\n      <input type=\"hidden\" name=\"UTM_SOURCE\"" in neu, True)
    pruefe("zweiter lauf ist ruhig", setz_felder(neu)[0], neu)
    pruefe("zweiter lauf ergaenzt nichts", setz_felder(neu)[1], 0)
    pruefe("seite ohne formular bleibt", setz_felder("<p>nix</p>"), ("<p>nix</p>", 0))

    body = "<html><body><p>x</p></body></html>"
    mit, ns = setz_skript(body)
    pruefe("skript eingebunden", SKRIPT in mit, True)
    pruefe("skript einmal gezaehlt", ns, 1)
    pruefe("skript vor dem body-ende", mit.index(SKRIPT) < mit.index("</body>"), True)
    pruefe("zweiter lauf bindet nicht doppelt", setz_skript(mit)[1], 0)
    pruefe("nur einmal im text", setz_skript(mit)[0].count(SKRIPT), 1)
    pruefe("ohne body-ende passiert nichts", setz_skript("<p>x</p>"), ("<p>x</p>", 0))

    # das echte Repo: jede Seite mit Formular muss beide Teile tragen
    fehlend = []
    for datei in seiten():
        with open(os.path.join(REPO, datei), encoding="utf-8") as fh:
            t = fh.read()
        if FORM.search(t) and not (MARKE in t and SKRIPT in t):
            fehlend.append(datei)
    pruefe("jede formularseite traegt felder und skript", fehlend, [])

    print("%d von 17 faellen falsch" % schlecht)
    return 1 if schlecht else 0


if __name__ == "__main__":
    sys.exit(main())
