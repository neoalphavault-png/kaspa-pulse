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
                   email   die Weiterleiten-Zeile oben in einer Ausgabe
                           (seit 12.10.2026, source newsletter, campaign
                           forward). Bewusst neben "mail": so trennt die
                           Auswertung weitergeleitete Mails von den
                           Abonnenten, die den Link in der eigenen Ausgabe
                           anklicken.
                   site    eine eigene Seite
                   reply   eine Selbstantwort unter einem Post (Tagesgrafik,
                           seit 30.09.2026, campaign form1 bis form10)
                   bio     die dauerhafte Stelle in einem Profil, also der
                           Kurzlink in einer Biografie (seit 12.10.2026,
                           scripts/kurzlinks.py)
                   description  die Beschreibung unter einem Video, als
                           Dauerlink, nicht unter einem einzelnen Stueck
                   channel die feste Stelle in einem Discord-Kanal
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
    # Die Profile selbst (Ben, 12.10.2026, fuer die Kurzlinks in
    # scripts/kurzlinks.py). Ein Klick aus einer Biografie ist etwas anderes
    # als einer unter einem einzelnen Stueck, darum eigene Quellen und eigene
    # Gattungen. x, discord und youtube gab es schon; dort unterscheidet erst
    # das medium den Biografie-Klick vom Klick unter einem Beitrag.
    "instagram": "bio",
    "threads": "bio",
    # Anzeigen auf Instagram (Ben, 26.10.2026): eigene Quelle, damit sie nicht
    # mit der Biografie unter "instagram" zusammenfallen.
    "ig": "paid",
}

# Gattungen, die es gibt. Ein Tippfehler im medium ist genauso teuer wie
# einer in der Quelle: er eroeffnet eine zweite Zeile in der Auswertung.
#
# bio, description und channel kamen am 12.10.2026 mit den Kurzlinks dazu:
# die dauerhafte Stelle im Profil, in der Videobeschreibung und im
# Discord-Kanal. Sie sind absichtlich nicht "post" oder "video" - ein
# Biografie-Link liegt Monate, ein Beitrag einen Tag.
#
# story kam am 24.10.2026 dazu: der Link-Sticker in der Instagram-Story
# (Kurzlink /story). Eine Story liegt 24 Stunden, ein Profil-Link Monate.
#
# paid kam am 26.10.2026 mit der Landingpage /whales dazu: der Klick aus einer
# bezahlten Anzeige (Ben, ad1-whales-v3). Ohne den Eintrag kaeme er als
# "other" an, und die Anzeige liesse sich in Brevo nicht abgrenzen.
MEDIEN = ("shorts", "video", "post", "chat", "mail", "email", "site", "reply",
          "bio", "description", "channel", "story", "paid")

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


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
    gezaehlt = 0

    def pruefe(name, ist, soll):
        nonlocal gezaehlt
        gezaehlt += 1
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
    pruefe("newsletter, weiterleiten-zeile", link("newsletter", "email", "forward"),
           "https://kaspapulse.com/?utm_source=newsletter&utm_medium=email"
           "&utm_campaign=forward#subscribe")
    pruefe("ohne campaign", link("site"),
           "https://kaspapulse.com/?utm_source=site&utm_medium=site#subscribe")
    pruefe("gattung ueberschreiben geht", link("x", "mail", "weekly"),
           "https://kaspapulse.com/?utm_source=x&utm_medium=mail&utm_campaign=weekly#subscribe")
    pruefe("der anker bleibt hinten", link("x").endswith("#subscribe"), True)
    pruefe("tagesgrafik, antwort unter dem x-post", link("x", "reply", "form4"),
           "https://kaspapulse.com/?utm_source=x&utm_medium=reply&utm_campaign=form4#subscribe")
    pruefe("fuenf quellen aus dem auftrag",
           all(q in QUELLEN for q in ("yt-description", "yt-pinned", "x", "discord", "tg")),
           True)

    # Die Liste steht zweimal: hier und als Spiegel in utm.js, weil der
    # Browser sie braucht. Zweimal heisst irgendwann auseinander, also
    # liest der Selbsttest die js-Zeile und vergleicht (Ben, 12.10.2026).
    import pathlib
    js = (pathlib.Path(__file__).resolve().parent.parent / "utm.js").read_text(encoding="utf-8")
    m = re.search(r"var MEDIEN = \[(.*?)\];", js, re.S)
    if m:
        aus_js = tuple(x.strip().strip('"') for x in m.group(1).replace("\n", " ").split(",")
                       if x.strip())
        pruefe("MEDIEN in utm.js gleich der liste hier", aus_js, MEDIEN)
    else:
        schlecht += 1
        gezaehlt += 1
        print("  FEHL MEDIEN in utm.js nicht gefunden, spiegel geprueft?")

    for falsch, was in ((("youtube-shorts",), "unbekannte quelle"),
                        (("yt-description", "reel"), "unbekannte gattung"),
                        (("x", None, "Weekly Numbers"), "campaign kein slug")):
        gezaehlt += 1
        try:
            link(*falsch)
            schlecht += 1
            print("  FEHL %s haette scheitern muessen" % was)
        except ValueError:
            print("  ok   %s faellt auf" % was)

    # gezaehlt statt einer Zahl im Text: hier stand 17, tatsaechlich sind
    # es 16 Faelle (gesehen am 12.10.2026). Eine Pruefzahl, die nicht
    # zaehlt, ist eine Behauptung.
    print("%d von %d faellen falsch" % (schlecht, gezaehlt))
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
