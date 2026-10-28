#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kurzlinks.py, kurze Adressen fuer die Profile und die Story.

WARUM ES DAS GIBT
In einer Instagram-Biografie steht bisher der ganze Link:

    kaspapulse.com/?utm_source=instagram&utm_medium=bio&utm_campaign=cheatsheet#subscribe

Das ist die richtige Messung und der falsche Anblick. Wer so etwas sieht,
klickt seltener: es sieht nach Werbung aus, es passt in kein Profilfeld, und
auf dem Handy bricht es mitten im Wort ab. Ab dem 12.10.2026 steht dort

    kaspapulse.com/ig

und die Parameter haengen hinten dran, wo sie niemand liest.

WIE
Je Kurzlink ein Ordner mit einer index.html, die nichts tut als
weiterleiten. Kein eigener Inhalt, noindex, und nicht in der sitemap.xml -
dort landen sie gar nicht erst, weil scripts/seo_seiten.py und
scripts/seo_pruefung.py nur die HTML-Dateien im Wurzelverzeichnis sehen.
Ein Ordner statt einer ig.html im Wurzelverzeichnis ist auch die sichere
Seite bei GitHub Pages: /ig fuehrt zu /ig/ und von dort zur index.html,
ohne sich darauf zu verlassen, dass Pages /ig auf ig.html abbildet.

Weitergeleitet wird mit meta refresh, nicht mit JavaScript. Das ist hier
der Punkt: der Klick kommt aus einer App, oft aus einem eingebauten
Browser, manchmal mit abgeschaltetem Skript. Eine Weiterleitung, die nur
mit JavaScript geht, verliert genau die Besucher, fuer die der Kurzlink
gemacht ist. Darunter steht eine einzige Zeile mit demselben Link, fuer den
Fall, dass ein Browser den refresh verweigert - eine leere Seite waere
sonst eine Sackgasse.

Die Werte kommen aus scripts/utm.py und werden beim Bauen dagegen geprueft.
Eine Quelle oder Gattung, die dort nicht in der Liste steht, bricht den
Lauf ab, statt eine zweite Zeile in der Auswertung zu eroeffnen.

    python3 scripts/kurzlinks.py --bauen
    python3 scripts/kurzlinks.py --pruefen
    python3 scripts/kurzlinks.py --selbsttest
"""
import argparse
import html
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HIER)
sys.path.insert(0, HIER)

ANKER = "#subscribe"
CAMPAIGN = "cheatsheet"

# Ordner -> (utm_source, utm_medium). campaign ist bei den fuenf Profilen
# "cheatsheet": das Cheat Sheet ist das, was am Ende des Klicks wartet.
KURZLINKS = {
    "ig": ("instagram", "bio"),
    "yt": ("youtube", "description"),
    "x": ("x", "bio"),
    "threads": ("threads", "bio"),
    "discord": ("discord", "channel"),
    "story": ("instagram", "story"),
    # Schlussfolie jedes Karussells (Ben, 28.10.2026), eigene Kampagne
    # karussell, damit Anmeldungen aus dem Karussell getrennt zu sehen sind
    "nl": ("instagram", "post"),
}

# Abweichende campaign und Anker je Ordner (Ben, 24.10.2026): /story kommt
# aus dem Link-Sticker der Instagram-Story (scripts/story_vorlage.py) und
# fuehrt auf die Startseite selbst, ohne Anker. Quelle ist "instagram",
# nicht "ig": "ig" steht nicht in utm.QUELLEN und wuerde in der Auswertung
# eine zweite Zeile neben "instagram" eroeffnen.
EIGEN = {
    "story": ("story", ""),
    "nl": ("karussell", ANKER),
}

ORDNER = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")

# Kanal -> Ordner fuer Links in automatischen Posts (Ben, 17.10.2026): keine
# langen UTM-Links mehr im Post, sondern der Kurzlink des Kanals. Die
# Weiterleitung traegt die Quelle, also bleibt die Zuordnung erhalten.
KANAL_ORDNER = {"x": "x", "threads": "threads", "discord": "discord", "instagram": "ig",
                "youtube": "yt"}
SEITE = "https://kaspapulse.com"


def kurzlink(kanal):
    """Der Kurzlink fuer einen Post im Kanal, z. B. https://kaspapulse.com/x."""
    if kanal not in KANAL_ORDNER:
        raise ValueError("kein kurzlink fuer kanal %r, es gibt %s"
                         % (kanal, ", ".join(sorted(KANAL_ORDNER))))
    ordner = KANAL_ORDNER[kanal]
    if ordner not in KURZLINKS:
        raise ValueError("ordner %r steht nicht in KURZLINKS" % ordner)
    return "%s/%s" % (SEITE, ordner)


def ziel(ordner):
    """Der Pfad, auf den weitergeleitet wird, relativ zur Wurzel."""
    quelle, medium = KURZLINKS[ordner]
    campaign, anker = EIGEN.get(ordner, (CAMPAIGN, ANKER))
    import utm
    if quelle not in utm.QUELLEN:
        raise SystemExit("ABBRUCH quelle %r steht nicht in utm.QUELLEN" % quelle)
    if medium not in utm.MEDIEN:
        raise SystemExit("ABBRUCH gattung %r steht nicht in utm.MEDIEN" % medium)
    if not utm.SLUG.match(campaign):
        raise SystemExit("ABBRUCH campaign %r ist kein slug" % campaign)
    return "/?utm_source=%s&utm_medium=%s&utm_campaign=%s%s" % (
        quelle, medium, campaign, anker)


def seite(ordner):
    """Die ganze Datei. Kein Inhalt, kein Skript, keine Marke."""
    if not ORDNER.match(ordner):
        raise SystemExit("ABBRUCH ordnername %r" % ordner)
    z = ziel(ordner)
    # Im Attribut muss das kaufmaennische Und als Entitaet stehen, sonst ist
    # es kein gueltiges HTML. Der Browser liest daraus wieder ein &.
    attr = html.escape(z, quote=True)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        '<meta name="robots" content="noindex, nofollow">\n'
        '<meta http-equiv="refresh" content="0; url=%s">\n'
        '<link rel="canonical" href="https://kaspapulse.com/">\n'
        "<title>kaspapulse.com</title>\n"
        "<!--\n"
        "  Kurzlink /%s, gebaut von scripts/kurzlinks.py. Nicht von Hand\n"
        "  aendern: der Lauf schreibt die Datei neu, und --pruefen faellt\n"
        "  auf jede Abweichung. Die UTM-Werte stehen in scripts/utm.py.\n"
        "\n"
        "  Keine eigene Seite, kein Inhalt, noindex, nicht in der\n"
        "  sitemap.xml. Weitergeleitet wird ohne JavaScript.\n"
        "-->\n"
        "</head>\n"
        '<body><a href="%s">kaspapulse.com</a></body>\n'
        "</html>\n" % (attr, ordner, attr))


def pfad(ordner):
    return os.path.join(REPO, ordner, "index.html")


def bauen(schreiben=True):
    """Legt die Dateien an. Liefert die Liste der geaenderten."""
    anders = []
    for ordner in sorted(KURZLINKS):
        soll = seite(ordner)
        p = pfad(ordner)
        ist = ""
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                ist = fh.read()
        if ist == soll:
            continue
        anders.append(ordner)
        if schreiben:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(soll)
    return anders


def selbsttest():
    schlecht = 0

    def ok(name, bedingung, *mehr):
        nonlocal schlecht
        print("%s %s%s" % ("ok  " if bedingung else "FEHL", name,
                           (" " + " ".join(str(m) for m in mehr)) if mehr and not bedingung else ""))
        if not bedingung:
            schlecht += 1

    ok("fuenf profile, die story und die karussell-schlussfolie",
       sorted(KURZLINKS) == ["discord", "ig", "nl", "story", "threads", "x", "yt"], sorted(KURZLINKS))
    ok("nl fuehrt mit kampagne karussell auf den anmeldebereich",
       ziel("nl") == "/?utm_source=instagram&utm_medium=post&utm_campaign=karussell#subscribe", ziel("nl"))
    ok("jedes profil-ziel geht auf den anmeldebereich der startseite",
       all(ziel(k).startswith("/?utm_source=") and ziel(k).endswith(ANKER) for k in KURZLINKS
           if k not in EIGEN))
    ok("story geht auf die startseite mit utm_medium=story (Ben, 24.10.2026)",
       ziel("story") == "/?utm_source=instagram&utm_medium=story&utm_campaign=story", ziel("story"))
    ok("die werte je kurzlink",
       [ziel(k) for k in ("ig", "yt", "x", "threads", "discord")] == [
           "/?utm_source=instagram&utm_medium=bio&utm_campaign=cheatsheet#subscribe",
           "/?utm_source=youtube&utm_medium=description&utm_campaign=cheatsheet#subscribe",
           "/?utm_source=x&utm_medium=bio&utm_campaign=cheatsheet#subscribe",
           "/?utm_source=threads&utm_medium=bio&utm_campaign=cheatsheet#subscribe",
           "/?utm_source=discord&utm_medium=channel&utm_campaign=cheatsheet#subscribe"],
       [ziel(k) for k in ("ig", "yt", "x", "threads", "discord")])

    s = seite("ig")
    ok("weiterleitung ohne javascript", '<meta http-equiv="refresh" content="0; url=/?' in s
       and "<script" not in s)
    # im Attribut muss jedes & als &amp; stehen, sonst ist es kein
    # gueltiges HTML. Also: drei Entitaeten je Vorkommen, kein nacktes &.
    # zwei parameter je adresse, zwei adressen in der datei
    ok("das kaufmaennische und steht als entitaet",
       s.count("&amp;utm_") == 4 and s.count("&utm_") == 0,
       s.count("&amp;utm_"), s.count("&utm_"))
    ok("noindex und nofollow", '<meta name="robots" content="noindex, nofollow">' in s)
    ok("canonical auf die startseite",
       '<link rel="canonical" href="https://kaspapulse.com/">' in s)
    ok("kein eigener inhalt, nur die eine zeile als auffang",
       s.count("<a ") == 1 and "<h1" not in s and "<p" not in s and "<img" not in s)
    ok("anker bleibt hinten", s.split('url=')[1].split('"')[0].endswith(ANKER))

    # jede Seite nennt ihren eigenen Ordner, keine Kopie der ersten
    ok("jede seite nennt ihren kurzlink",
       all(("Kurzlink /%s," % k) in seite(k) for k in KURZLINKS))
    # wiederholbar: zweimal bauen aendert beim zweiten Mal nichts
    ok("der bau ist wiederholbar", seite("yt") == seite("yt"))

    import utm
    ok("alle quellen stehen in der utm-liste",
       all(q in utm.QUELLEN for q, _ in KURZLINKS.values()))
    ok("alle gattungen stehen in der utm-liste",
       all(m in utm.MEDIEN for _, m in KURZLINKS.values()))
    ok("campaign ist ein slug", bool(utm.SLUG.match(CAMPAIGN))
       and all(utm.SLUG.match(c) for c, _ in EIGEN.values()))
    ok("story-seite leitet ohne anker weiter", 'url=/?utm_source=instagram&amp;utm_medium=story'
       '&amp;utm_campaign=story">' in seite("story"))

    offen = bauen(schreiben=False)
    ok("die dateien im repo stimmen mit der tabelle ueberein", not offen, offen)
    ok("keine der seiten steht in der sitemap",
       all(("/%s/" % k) not in _sitemap() and ("/%s<" % k) not in _sitemap() for k in KURZLINKS))
    # kurzlinks fuer posts (Ben, 17.10.2026)
    ok("kurzlink je kanal",
       [kurzlink(k) for k in ("x", "threads", "discord", "instagram")]
       == ["https://kaspapulse.com/x", "https://kaspapulse.com/threads",
           "https://kaspapulse.com/discord", "https://kaspapulse.com/ig"])
    try:
        kurzlink("tg")
        ok("kanal ohne kurzlink stoppt", False)
    except ValueError:
        ok("kanal ohne kurzlink stoppt", True)
    print("%d fehler" % schlecht)
    return 1 if schlecht else 0


def _sitemap():
    p = os.path.join(REPO, "sitemap.xml")
    if not os.path.exists(p):
        return ""
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bauen", action="store_true")
    ap.add_argument("--pruefen", action="store_true",
                    help="nur melden, was von der tabelle abweicht")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.pruefen:
        offen = bauen(schreiben=False)
        if offen:
            print("weicht von der tabelle ab: %s" % ", ".join(offen))
            return 1
        print("kurzlinks: alle %d stimmen" % len(KURZLINKS))
        return 0
    if a.bauen:
        anders = bauen()
        print("geschrieben: %s" % (", ".join(anders) if anders else "nichts, alles stand schon"))
        for k in sorted(KURZLINKS):
            print("   kaspapulse.com/%-8s -> %s" % (k, ziel(k)))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
