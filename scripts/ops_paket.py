#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ops_paket.py, schickt ein Lieferpaket aus dem Repo nach #moderator-only (Ben, 26.10.2026).

WARUM
Auftraege enden mit "Lieferung an Ben nach Discord". Den Webhook gibt es nur
als GitHub Secret (DISCORD_WEBHOOK_OPS), aus einer Arbeitssitzung kommt man
nicht heran, und das ist richtig so. Dieses Skript laeuft im Workflow
ops-paket.yml und schickt eine Markdown-Datei aus berichte/ als Nachrichten.

REGELN
* Nur Dateien unter berichte/ mit Endung .md, nichts anderes.
* Discord nimmt 2000 Zeichen je Nachricht. Geteilt wird an Leerzeilen, und
  ein Codeblock, der ueber eine Grenze laeuft, wird zu- und neu aufgemacht,
  damit jeder Block einzeln kopierbar bleibt.
* Keine Erwaehnungen (allowed_mentions leer), der Webhook wird nie gedruckt.

    python3 scripts/ops_paket.py berichte/2026-10-28-x-discord.md   senden (braucht DISCORD_WEBHOOK_OPS)
    python3 scripts/ops_paket.py --trocken berichte/...             nur zeigen, was ginge
    python3 scripts/ops_paket.py --selbsttest
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GRENZE = 1900
ZAUN = "```"


def erlaubt(pfad):
    p = Path(pfad)
    return (not p.is_absolute() and p.parts[:1] == ("berichte",) and ".." not in p.parts
            and p.suffix == ".md")


def teilen(text, grenze=GRENZE):
    """Teilt an Leerzeilen, Codebloecke bleiben je Nachricht geschlossen."""
    stuecke = []
    for a in text.strip().split("\n\n"):
        # ein absatz ueber der grenze wird an zeilen zerlegt
        while len(a) > grenze:
            schnitt = a.rfind("\n", 0, grenze)
            schnitt = schnitt if schnitt > 0 else grenze
            stuecke.append(a[:schnitt])
            a = a[schnitt:].lstrip("\n")
        stuecke.append(a)
    teile, jetzt = [], ""
    for a in stuecke:
        kand = (jetzt + "\n\n" + a) if jetzt else a
        if len(kand) <= grenze:
            jetzt = kand
        else:
            teile.append(jetzt)
            jetzt = a
    if jetzt:
        teile.append(jetzt)
    # ein codeblock darf nicht ueber zwei nachrichten laufen
    aus, offen = [], False
    for t in teile:
        if offen:
            t = ZAUN + "\n" + t
        offen = t.count(ZAUN) % 2 == 1
        if offen:
            t += "\n" + ZAUN
        aus.append(t)
    return aus


def senden(hook, teile):
    for i, t in enumerate(teile):
        req = urllib.request.Request(hook, data=json.dumps({"content": t, "allowed_mentions": {"parse": []}}).encode(),
                                     headers={"Content-Type": "application/json", "User-Agent": "kaspa-pulse-bot"})
        urllib.request.urlopen(req, timeout=30)
        print("nachricht %d von %d gesendet, %d zeichen" % (i + 1, len(teile), len(t)))
        time.sleep(1.2)


def selbsttest():
    f = []

    def ok(name, bed, info=""):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, ("  " + str(info)) if not bed and info else ""))
        if not bed:
            f.append(name)

    ok("berichte/x.md erlaubt", erlaubt("berichte/2026-10-28-x.md"))
    ok("anderes verboten", not erlaubt("data/x.md") and not erlaubt("berichte/../x.md")
       and not erlaubt("/etc/x.md") and not erlaubt("berichte/x.txt"))
    kurz = "a\n\nb"
    ok("kurz bleibt eins", teilen(kurz) == ["a\n\nb"])
    lang = "\n\n".join("absatz %d " % i + "x" * 300 for i in range(20))
    t = teilen(lang)
    ok("lang wird geteilt", len(t) > 1 and all(len(x) <= GRENZE + 10 for x in t), [len(x) for x in t])
    ok("nichts geht verloren", sum(x.count("absatz") for x in t) == 20)
    code = "kopf\n\n" + ZAUN + "\n" + "\n".join("zeile %d" % i for i in range(400)) + "\n" + ZAUN + "\n\nende"
    t = teilen(code)
    ok("codeblock je nachricht geschlossen", all(x.count(ZAUN) % 2 == 0 for x in t), [x.count(ZAUN) for x in t])
    ok("alle zeilen da", sum(x.count("zeile ") for x in t) == 400)
    ok("unter 2000 zeichen", all(len(x) <= 2000 for x in t), [len(x) for x in t])
    print("")
    print("%d fehler" % len(f) if f else "alle testfaelle bestanden")
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("datei", nargs="?")
    ap.add_argument("--trocken", action="store_true")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if not a.datei or not erlaubt(a.datei):
        print("ABBRUCH nur eine .md unter berichte/")
        return 1
    teile = teilen((REPO / a.datei).read_text(encoding="utf-8"))
    hook = os.environ.get("DISCORD_WEBHOOK_OPS", "")
    if a.trocken or not hook:
        for i, t in enumerate(teile):
            print("---- nachricht %d, %d zeichen\n%s" % (i + 1, len(t), t))
        if not hook and not a.trocken:
            print("kein DISCORD_WEBHOOK_OPS, nur gezeigt")
        return 0
    senden(hook, teile)
    return 0


if __name__ == "__main__":
    sys.exit(main())
