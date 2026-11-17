#!/usr/bin/env python3
"""peer_kennung.py - Software-Kennung fremder Peers fuer Log und Dateien kuerzen.

Genutzt von scripts/bch/tempnet_koepfe.py, scripts/bch/tempnet_lauscher.py,
scripts/zcash/zcash_koepfe.py und scripts/zcash/zcash_lauscher.py.

  python3 scripts/peer_kennung.py --selbsttest
"""
import re
import sys

# Ben, 17.11.2026: ein Peer trug am 15.11. einen Hostnamen in seiner
# Software-Kennung, und die stand ungekuerzt im Job-Log. Die Kennung kommt
# vom Peer selbst, er kann hineinschreiben, was er will. Deshalb behalten wir
# nur den Teil vor der ersten Klammer und ersetzen darin alles, was wie ein
# Hostname oder eine IP aussieht, durch "[entfernt]". Das gilt fuer Log und
# alle Dateien, denn die Kennung wird nur hier gelesen.
_RE_IP4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_RE_IP6 = re.compile(r"\[?\b(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}\b\]?")
_RE_HOST = re.compile(r"\b(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z][A-Za-z0-9-]{1,62}\b")


def kennung(roh):
    s = str(roh).split("(")[0]
    for r in (_RE_IP4, _RE_IP6, _RE_HOST):
        s = r.sub("[entfernt]", s)
    s = "".join(c if c.isprintable() else "?" for c in s)
    return s[:80] or "?"


def selbsttest():
    faelle = [
        ("/Bitcoin Cash Node:29.2.1(chipnet.example.org)/", "/Bitcoin Cash Node:29.2.1"),
        ("/Bitcoin Cash Node:29.2.1(tempnet-20261015)/", "/Bitcoin Cash Node:29.2.1"),
        ("/Bitcoin Cash Node:29.2.1(EB32.0)/", "/Bitcoin Cash Node:29.2.1"),
        ("/Bitcoin Cash Node:29.2.1/", "/Bitcoin Cash Node:29.2.1/"),
        ("/Vcash:0.1/", "/Vcash:0.1/"),
        ("/Zebra:7.0.0/", "/Zebra:7.0.0/"),
        ("/Rapids:2026-11.88096962/", "/Rapids:2026-11.88096962/"),
        ("/mein knoten node7.example.net:8333/", "/mein knoten [entfernt]:8333/"),
        ("/x:1 192.0.2.17/", "/x:1 [entfernt]/"),
        ("/x:1 2001:db8::1/", "/x:1 [entfernt]/"),
        ("(nur.klammer.example.com)", "?"),
    ]
    falsch = 0
    for roh, soll in faelle:
        ist = kennung(roh)
        ok = ist == soll
        falsch += not ok
        # ausgegeben wird nur das ergebnis, nie die rohe kennung
        print("  %s  %s" % ("ok  " if ok else "FEHL", ist))
    print("%d von %d faellen falsch" % (falsch, len(faelle)))
    return 1 if falsch else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--selbsttest"]:
        sys.exit(selbsttest())
    sys.exit("aufruf: --selbsttest")
