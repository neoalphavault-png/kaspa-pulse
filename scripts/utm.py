#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""utm.py, der Newsletter-Link mit Herkunft. Eine Stelle, ein Link.

WARUM ES DAS GIBT
Der Anmeldelink stand bisher an fuenf Stellen als roher Text:
https://kaspapulse.com/#subscribe. Damit landen alle Anmeldungen in einem
Topf. Wer die Liste waechst, weiss nicht, ob sie aus der Videobeschreibung,
dem angepinnten Kommentar, X, Discord oder Telegram waechst, und kann das
Naechste nicht dorthin legen, wo es wirkt. Follow und Newsletter sind das
Unabhaengigkeitsziel, und ein Ziel ohne Messung ist ein Wunsch.

Ab dem 16.09.2026 traegt JEDER Newsletter-Link drei Parameter:

    utm_source     WO der Klick herkam. Feste Liste, siehe QUELLEN.
    utm_medium     die GATTUNG des Stuecks, nicht der Kanal:
                   shorts  ein Short (bis 60 s, Hochformat)
                   video   ein Langvideo, also KASPA WEEKLY und der
                           Donnerstags-Erklaerer
                   post    ein Beitrag auf X
                   chat    Discord und Telegram
                   mail    eine Newsletter-Ausgabe
                   site    eine eigene Seite
    utm_campaign   WELCHE Serie oder Ausgabe ihn gebracht hat.

Und die Seite reicht utm_source ins Brevo-Formular durch (scripts/utm_fields.py
und utm.js), damit die Anmeldung ihre Quelle mitbringt, statt sie im Klick
zu verlieren.

    from utm import link
    link("yt-pinned", "shorts", "blocks-while-you-watched")
    python3 scripts/utm.py --selftest
"""
import argparse
import os
import re
import sys
import urllib.parse

BASIS = "https://kaspapulse.com/"
ANKER = "#subscribe"

# Feste Liste. Wer eine sechste Quelle braucht, traegt sie hier ein und
# nirgends sonst; ein Tippfehler im Aufruf faellt dann sofort auf, statt
# eine eigene Zeile in der Auswertung zu erzeugen ("youtube" neben "yt").
#
# Der Wert je Quelle ist nur die VORGABE fuer utm_medium. Die drei
# YouTube-Quellen stehen unter einem Short genauso wie unter einem
# Langvideo; welche Gattung es ist, sagt der Aufrufer:
#     Short:     link("yt-description", "shorts", "week-in-30")
#     Langvideo: link("yt-description", "video",  "weekly3")
# So steht es seit dem 16.09.2026 in der Beschreibung von KASPA WEEKLY
# Folge 3, und so gilt es (docs/routinen.md, Routine 3 und 4).
QUELLEN = {
    "yt-description": "video",    # Videobeschreibung, Vorgabe Langvideo
    "yt-pinned": "video",         # angepinnter Kommentar, Vorgabe Langvideo
    "youtube": "video",           # im Video gesprochen oder eingeblendet
    "x": "post",
    "discord": "chat",
    "tg": "chat",
    "newsletter": "mail",
    "site": "site",
}

# Gattungen, die es gibt. Ein Tippfehler im medium ist genauso teuer wie
# einer in der Quelle: er eroeffnet eine zweite Zeile in der Auswertung.
MEDIEN = ("shorts", "video", "post", "chat", "mail", "site")

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

# utm.js prueft die Adresse gegen eine wortgleiche Kopie von QUELLEN und
# MEDIEN. Wer hier eine sechste Quelle eintraegt und dort nicht, bekommt
# keinen Fehler, sondern still ein "other" am Kontakt: sauber gemessener
# Datensalat. Der Selbsttest vergleicht deshalb beide Seiten.
UTM_JS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "utm.js")


def js_liste(text, name):
    """Die Werte einer 'var NAME = [...]'-Zeile aus utm.js, oder None."""
    m = re.search(r"var %s = \[(.*?)\];" % name, text, re.S)
    if not m:
        return None
    return [s.strip().strip('"') for s in m.group(1).split(",") if s.strip()]


def link(source, medium=None, campaign=None):
    """Der Anmeldelink fuer eine Quelle. medium faellt auf die Gattung der
    Quelle zurueck, campaign ist Pflicht, sobald es eine Serie gibt."""
    if source not in QUELLEN:
        raise ValueError("unbekannte quelle %r, erlaubt: %s"
                         % (source, ", ".join(sorted(QUELLEN))))
    medium = medium or QUELLEN[source]
    if medium not in MEDIEN:
        raise ValueError("unbekannte gattung %r, erlaubt: %s"
                         % (medium, ", ".join(MEDIEN)))
    q = [("utm_source", source), ("utm_medium", medium)]
    if campaign:
        if not SLUG.match(campaign):
            raise ValueError("campaign muss ein slug sein (a-z, 0-9, minus): %r" % campaign)
        q.append(("utm_campaign", campaign))
    return BASIS + "?" + urllib.parse.urlencode(q) + ANKER


def selftest():
    schlecht = 0

    def pruefe(name, ist, soll):
        nonlocal schlecht
        if ist != soll:
            schlecht += 1
            print("  FEHL %s\n    ist  %r\n    soll %r" % (name, ist, soll))
        else:
            print("  ok   %s" % name)

    # Langvideo ist die Vorgabe der drei YouTube-Quellen: so steht der Link
    # seit dem 16.09. in der Beschreibung von KASPA WEEKLY Folge 3.
    pruefe("langvideo, beschreibung", link("yt-description", campaign="weekly3"),
           "https://kaspapulse.com/?utm_source=yt-description&utm_medium=video"
           "&utm_campaign=weekly3#subscribe")
    pruefe("langvideo, angehefteter kommentar", link("yt-pinned", campaign="weekly3"),
           "https://kaspapulse.com/?utm_source=yt-pinned&utm_medium=video"
           "&utm_campaign=weekly3#subscribe")
    pruefe("short, beschreibung", link("yt-description", "shorts", "week-in-30"),
           "https://kaspapulse.com/?utm_source=yt-description&utm_medium=shorts"
           "&utm_campaign=week-in-30#subscribe")
    pruefe("short, angehefteter kommentar", link("yt-pinned", "shorts", "claim-vs-calculator"),
           "https://kaspapulse.com/?utm_source=yt-pinned&utm_medium=shorts"
           "&utm_campaign=claim-vs-calculator#subscribe")
    pruefe("x", link("x", campaign="weekly"),
           "https://kaspapulse.com/?utm_source=x&utm_medium=post&utm_campaign=weekly#subscribe")
    pruefe("discord", link("discord", campaign="weekly"),
           "https://kaspapulse.com/?utm_source=discord&utm_medium=chat"
           "&utm_campaign=weekly#subscribe")
    pruefe("telegram", link("tg", campaign="weekly"),
           "https://kaspapulse.com/?utm_source=tg&utm_medium=chat"
           "&utm_campaign=weekly#subscribe")
    pruefe("ohne campaign", link("site"),
           "https://kaspapulse.com/?utm_source=site&utm_medium=site#subscribe")
    pruefe("gattung ueberschreiben geht", link("x", "mail", "weekly"),
           "https://kaspapulse.com/?utm_source=x&utm_medium=mail&utm_campaign=weekly#subscribe")
    pruefe("der anker bleibt hinten", link("x").endswith("#subscribe"), True)
    pruefe("fuenf quellen aus dem auftrag",
           all(q in QUELLEN for q in ("yt-description", "yt-pinned", "x", "discord", "tg")),
           True)

    # beide Seiten derselben Liste
    with open(UTM_JS, encoding="utf-8") as fh:
        js = fh.read()
    pruefe("utm.js kennt dieselben quellen",
           js_liste(js, "QUELLEN"), list(QUELLEN))
    pruefe("utm.js kennt dieselben gattungen", js_liste(js, "MEDIEN"), list(MEDIEN))

    for falsch, was in ((("youtube-shorts",), "unbekannte quelle"),
                        (("yt-description", "reel"), "unbekannte gattung"),
                        (("x", None, "Weekly Numbers"), "campaign kein slug")):
        try:
            link(*falsch)
            schlecht += 1
            print("  FEHL %s haette scheitern muessen" % was)
        except ValueError:
            print("  ok   %s faellt auf" % was)

    print("%d von 16 faellen falsch" % schlecht)
    return 1 if schlecht else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("source", nargs="?")
    ap.add_argument("campaign", nargs="?")
    a = ap.parse_args()
    if a.selftest or not a.source:
        sys.exit(selftest())
    print(link(a.source, campaign=a.campaign))
