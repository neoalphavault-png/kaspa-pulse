#!/usr/bin/env python3
"""Kaspa Pulse, Teil eines Berichts in den privaten Ops-Kanal (Ben, 26.10.2026).

Ein Bericht unter berichte/ kann einen Abschnitt zwischen <!-- discord --> und
<!-- /discord --> tragen, unterteilt mit <!-- teil -->. Dieses Skript schickt
zuerst eine Kopfzeile "📤 VON HAND" mit der Anweisung zum Kopieren, dann je
Teil eine Nachricht. Vor dem Senden wird der ganze Text geprueft: keine IP,
keine Kaspa-Adresse, kein Hostname ausser github.com, kein Schluessel. Bei einem
Fund geht nichts raus.

Der Webhook kommt nur aus der Umgebung (DISCORD_WEBHOOK_OPS) und wird nie
ausgegeben.

    python3 scripts/bericht_discord.py --datei berichte/2026-10-27-stp-rat.md --link URL [--trocken]
    python3 scripts/bericht_discord.py --selbsttest
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

AUF, ZU, TEIL = "<!-- discord -->", "<!-- /discord -->", "<!-- teil -->"
GRENZE = 1900
VERBOTEN = (
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "ip"),
    (re.compile(r"\b(?:kaspa|kaspatest):[a-z0-9]{20,}"), "adresse"),
    # erlaubt sind github.com und unsere eigene, oeffentliche Domain kaspapulse.com: Ben
    # muss Links wie die Ziel-URL einer Anzeige kopieren koennen (Ben, 26.10.2026).
    # Unterdomains davon bleiben gesperrt, sie koennten Infrastruktur sein.
    (re.compile(r"(?i)(?<![a-z0-9.-])(?!(?:github|kaspapulse)\.com(?![.\w-]))(?:[a-z0-9-]+\.)+(?:com|io|org|net|de|blue|red|green|stream|xyz|app|dev)\b"), "hostname"),
    (re.compile(r"ghp_|github_pat_|xox[bap]-|sk-[A-Za-z0-9]{20}|BEGIN [A-Z ]*PRIVATE KEY|discord(?:app)?\.com/api/webhooks"), "schluessel"),
)


def teile(text):
    if AUF not in text or ZU not in text:
        return []
    innen = text[text.index(AUF) + len(AUF):text.index(ZU)]
    return [t.strip() for t in innen.split(TEIL) if t.strip()]


def pruefen(texte):
    funde = []
    for i, t in enumerate(texte):
        for rx, art in VERBOTEN:
            if rx.search(t):
                funde.append("teil %d: %s" % (i, art))
        if len(t) > GRENZE:
            funde.append("teil %d: %d zeichen, hoechstens %d" % (i, len(t), GRENZE))
    return funde


def kopf(datei, n, link):
    return ("📤 VON HAND\n**%s**\nBitte die folgenden %d Nachrichten in dieser Reihenfolge kopieren und an den "
            "Empfänger schicken. Jede Nachricht lange drücken, Text kopieren, einfügen.\nBericht: %s"
            % (os.path.basename(datei), n, link or datei))


def senden(texte, webhook, pause=1.0):
    for i, t in enumerate(texte):
        req = urllib.request.Request(webhook, data=json.dumps({"content": t, "allowed_mentions": {"parse": []}}).encode(),
                                     headers={"Content-Type": "application/json", "User-Agent": "kaspa-pulse-bericht"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                print("nachricht %d gesendet (http %d)" % (i, r.status))
        except urllib.error.HTTPError as exc:
            print("nachricht %d nicht gesendet (http %d)" % (i, exc.code))
            return 1
        time.sleep(pause)
    return 0


def lauf(datei, link, trocken, vorher=None):
    text = open(datei, encoding="utf-8").read()
    t = teile(text)
    if not t:
        print("kein discord-abschnitt in %s" % datei)
        return 0
    if vorher and os.path.exists(vorher) and teile(open(vorher, encoding="utf-8").read()) == t:
        print("discord-abschnitt unveraendert, nichts gesendet")
        return 0
    alle = [kopf(datei, len(t), link)] + t
    funde = pruefen(alle)
    if funde:
        print("nicht gesendet: " + "; ".join(funde))
        return 2
    if trocken:
        print("trocken, %d nachrichten, laengste %d zeichen" % (len(alle), max(len(x) for x in alle)))
        return 0
    webhook = os.environ.get("DISCORD_WEBHOOK_OPS", "").strip()
    if not webhook:
        print("kein webhook in der umgebung")
        return 3
    return senden(alle, webhook)


def selbsttest():
    fehler = []

    def ok(name, bed, ist=None):
        if not bed:
            fehler.append(name)
            print("FEHLER", name, ist)
    md = "# x\n%s\neins\n%s\nzwei\n%s\nrest" % (AUF, TEIL, ZU)
    ok("zwei teile", teile(md) == ["eins", "zwei"], teile(md))
    ok("ohne abschnitt leer", teile("# nur text") == [])
    ok("sauberer text ohne fund", pruefen(["see github.com/x and 18:03 to 18:14"]) == [])
    ok("eigene domain erlaubt", pruefen(["https://kaspapulse.com/whales?utm_source=ig&utm_medium=paid"]) == [],
       pruefen(["https://kaspapulse.com/whales?utm_source=ig"]))
    ok("unterdomain der eigenen domain gesperrt", any("hostname" in f for f in pruefen(["x." + "kaspapulse" + ".com"])))
    ok("fremde domain mit kaspapulse im namen gesperrt", any("hostname" in f for f in pruefen(["kaspapulse" + ".com.evil.io"])))
    # testwerte erst zur laufzeit zusammengesetzt, kein echter host und keine echte ip in der datei
    ip = ".".join(["192", "0", "2", "7"])
    host = "-".join(["knoten", "1"]) + "." + "beispiel" + ".blue"
    for bad, art in (("node " + ip, "ip"), ("kaspatest:" + "q" * 61, "adresse"), (host, "hostname"),
                     ("ghp" + "_abc", "schluessel")):
        ok("fund %s" % art, any(art in f for f in pruefen([bad])), pruefen([bad]))
    ok("zu lang", any("zeichen" in f for f in pruefen(["x" * 2000])))
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "a.md"), os.path.join(d, "b.md")
        open(a, "w").write(md)
        open(b, "w").write(md + "\nanderer rest")
        ok("unveraenderter abschnitt sendet nichts", lauf(b, "", False, a) == 0)
    ok("kopf traegt von hand", kopf("berichte/a.md", 3, "").startswith("📤 VON HAND"))
    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datei")
    ap.add_argument("--link", default="")
    ap.add_argument("--trocken", action="store_true")
    ap.add_argument("--vorher", help="stand der datei vor dem push; gleicher abschnitt wird nicht erneut gesendet")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    return lauf(a.datei, a.link, a.trocken, a.vorher)


if __name__ == "__main__":
    sys.exit(main())
