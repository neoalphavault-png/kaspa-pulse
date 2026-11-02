#!/usr/bin/env python3
"""kcc20_vergleich.py, KCC-20-Tx ab einem Zeitpunkt zaehlen, nur Summen (Ben, 02.11.2026).

Liest kcc20-tx-liste.jsonl (aus kcc20_zaehlung.py) und zaehlt je Art (transfer,
kcc20_ausgang, transfer_unbewiesen) und Quelle (eigener knoten, api.kaspa.org)
die Tx mit Blockzeit ab dem Zeitpunkt. Gibt keine Tx-ID aus.

    python3 scripts/kcc20_vergleich.py kcc20-tx-liste.jsonl 2026-10-26T12:00:00Z vergleich.json
    python3 scripts/kcc20_vergleich.py --selbsttest
"""
import collections
import datetime as dt
import json
import os
import sys
import tempfile


def ms(text):
    return int(dt.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp() * 1000) if text else 0


def zaehlen(zeilen, ab_ms):
    z = collections.Counter()
    for t in zeilen:
        if (t.get("t") or 0) >= ab_ms:
            z["%s|%s" % (t.get("art"), t.get("quelle"))] += 1
    return dict(sorted(z.items()))


def selbsttest():
    zl = [{"id": "a", "t": 10, "art": "transfer", "quelle": "eigener knoten"},
          {"id": "b", "t": 20, "art": "transfer", "quelle": "api.kaspa.org"},
          {"id": "c", "t": 5, "art": "transfer", "quelle": "eigener knoten"}]
    z = zaehlen(zl, 10)
    f = 0 if z == {"transfer|api.kaspa.org": 1, "transfer|eigener knoten": 1} else 1
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "l.jsonl")
        open(p, "w").write("".join(json.dumps(x) + "\n" for x in zl))
        main([p, "", os.path.join(d, "v.json")])
        f += 0 if json.load(open(os.path.join(d, "v.json")))["je_art_und_quelle"]["transfer|eigener knoten"] == 2 else 1
        f += 0 if "\"a\"" not in open(os.path.join(d, "v.json")).read() else 1
    print("%d fehler" % f)
    return 1 if f else 0


def main(argv):
    if argv and argv[0] == "--selbsttest":
        return selbsttest()
    liste, ab_text, out = argv
    zl = [json.loads(z) for z in open(liste, encoding="utf-8")] if os.path.exists(liste) else []
    erg = {"ab_utc": ab_text or None, "liste_gelesen": os.path.exists(liste), "je_art_und_quelle": zaehlen(zl, ms(ab_text))}
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(erg, fh, indent=1)
    print(json.dumps(erg))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
