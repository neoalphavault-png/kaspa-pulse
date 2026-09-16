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
    utm_medium     die Gattung: shorts, video, post, chat, mail.
    utm_campaign   WELCHE Serie oder Ausgabe ihn gebracht hat.

Und die Seite reicht utm_source ins Brevo-Formular durch (scripts/utm_fields.py
und utm.js), damit die Anmeldung ihre Quelle mitbringt, statt sie im Klick
zu verlieren.

    from utm import link
    link("yt-pinned", "shorts", "blocks-while-you-watched")
    python3 scripts/utm.py --selftest
"""
import argparse
import re
import sys
import urllib.parse

BASIS = "https://kaspapulse.com/"
ANKER = "#subscribe"

# Feste Liste. Wer eine sechste Quelle braucht, traegt sie hier ein und
# nirgends sonst; ein Tippfehler im Aufruf faellt dann sofort auf, statt
# eine eigene Zeile in der Auswertung zu erzeugen ("youtube" neben "yt").
QUELLEN = {
    "yt-description": "shorts",   # Videobeschreibung
    "yt-pinned": "shorts",        # angepinnter Kommentar
    "youtube": "shorts",          # im Video gesprochen oder eingeblendet
    "x": "post",
    "discord": "chat",
    "tg": "chat",
    "newsletter": "mail",
    "site": "site",
}

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def link(source, medium=None, campaign=None):
    """Der Anmeldelink fuer eine Quelle. medium faellt auf die Gattung der
    Quelle zurueck, campaign ist Pflicht, sobald es eine Serie gibt."""
    if source not in QUELLEN:
        raise ValueError("unbekannte quelle %r, erlaubt: %s"
                         % (source, ", ".join(sorted(QUELLEN))))
    medium = medium or QUELLEN[source]
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

    pruefe("beschreibung", link("yt-description", campaign="the-line"),
           "https://kaspapulse.com/?utm_source=yt-description&utm_medium=shorts"
           "&utm_campaign=the-line#subscribe")
    pruefe("pin", link("yt-pinned", campaign="entity-x"),
           "https://kaspapulse.com/?utm_source=yt-pinned&utm_medium=shorts"
           "&utm_campaign=entity-x#subscribe")
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
    pruefe("eigenes medium", link("x", medium="bio", campaign="weekly"),
           "https://kaspapulse.com/?utm_source=x&utm_medium=bio&utm_campaign=weekly#subscribe")
    pruefe("der anker bleibt hinten", link("x").endswith("#subscribe"), True)
    pruefe("fuenf quellen aus dem auftrag",
           all(q in QUELLEN for q in ("yt-description", "yt-pinned", "x", "discord", "tg")),
           True)

    for falsch, was in ((("youtube-shorts",), "unbekannte quelle"),
                        (("x", None, "Weekly Numbers"), "campaign kein slug")):
        try:
            link(*falsch)
            schlecht += 1
            print("  FEHL %s haette scheitern muessen" % was)
        except ValueError:
            print("  ok   %s faellt auf" % was)

    print("%d von 11 faellen falsch" % schlecht)
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
