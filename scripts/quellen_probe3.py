#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quellen_probe3.py, die dritte und letzte Runde der Machbarkeitsfrage.

Stand nach Runde zwei (Lauf 35702050358):

  Kaspalytics. In der Seitenleiste steht der Eintrag "Covenant UTXO Count"
  und zeigt auf /app/utxo/covenant-count. Die Chart-Adresse ist bei dieser
  Seite bisher immer der Seitenpfad unter /api/charts/, also lautet die
  Vermutung /api/charts/utxo/covenant-count. Diese Runde prueft sie.

  kaspa.stream. Das Buendel ist verschleiert (String-Array-Obfuskator,
  a0wC(0x...)), im Klartext steht keine einzige Adresse. Mitgeliefert ist
  aber der socket.io-Client, und die Seite nennt ihr eigenes Quellrepo
  github.com/kaspa-stream/explorer. Zwei Wege also: die \\xNN-Escapes im
  Buendel zurueckrechnen und den entstehenden Klartext nach Adressen
  durchsuchen, und den socket.io-Handschlag direkt anklopfen.

    python3 scripts/quellen_probe3.py
"""

import json
import re
import sys
import urllib.error
import urllib.request

TIMEOUT = 30
KOPF = {"Accept": "*/*", "User-Agent": "kaspa-pulse-bot (+https://kaspapulse.com)"}

KASPALYTICS = "https://www.kaspalytics.com"
BUENDEL = "https://kaspa.stream/assets/index-D6QnIeBA.js"


def hole(url, kopf=None):
    try:
        req = urllib.request.Request(url, headers=kopf or KOPF)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read()[:300].decode("utf-8", "replace")
        except Exception:                          # noqa: BLE001
            return e.code, ""
    except Exception as exc:                       # noqa: BLE001
        return 0, "%s: %s" % (type(exc).__name__, exc)


def kurz(t, n=700):
    t = " ".join(str(t).split())
    return t if len(t) <= n else t[:n] + " …[gekuerzt]"


def form(text):
    try:
        d = json.loads(text)
    except Exception:                              # noqa: BLE001
        return None, "kein JSON"
    if isinstance(d, dict):
        return d, "objekt, schluessel %s" % sorted(d.keys())[:16]
    if isinstance(d, list):
        e = d[0] if d else None
        return d, "liste, %d eintraege, erster %s" % (
            len(d), sorted(e.keys())[:16] if isinstance(e, dict) else type(e).__name__)
    return d, type(d).__name__


def spanne(d):
    if not isinstance(d, dict):
        return None
    lab, ds = d.get("labels") or [], d.get("datasets") or []
    if not lab or not ds:
        return None
    return "%d tage, %s bis %s, reihen %s" % (
        len(lab), lab[0], lab[-1], [x.get("label") for x in ds])


def probiere(urls, ueberschrift, kopf=None):
    print("\n  %s" % ueberschrift)
    treffer = []
    for u in urls:
        st, txt = hole(u, kopf)
        if st != 200:
            print("    %-62s http %s" % (u[:62], st))
            continue
        d, f = form(txt)
        sp = spanne(d)
        print("    %-62s http 200  %s" % (u[:62], f))
        if sp:
            print("        %s" % sp)
        print("        roh: %s" % kurz(txt, 700))
        treffer.append(u)
    return treffer


ESC = re.compile(r"\\x([0-9a-fA-F]{2})")


def entschluessle(text):
    """Die \\xNN-Escapes zurueckrechnen. Der Obfuskator legt seine
    Zeichenketten so ab; danach steht jede Adresse wieder im Klartext."""
    return ESC.sub(lambda m: chr(int(m.group(1), 16)), text)


def umfeld(text, muster, spanne_=200, hoechstens=25):
    aus = []
    for m in re.finditer(muster, text, re.I):
        a = max(0, m.start() - spanne_ // 2)
        aus.append(text[a:m.end() + spanne_ // 2])
        if len(aus) >= hoechstens:
            break
    return aus


def main():
    print("=" * 78)
    print("RUNDE 3 A  KASPALYTICS, DIE UTXO-ANZAHL")
    print("=" * 78)
    st, txt = hole(KASPALYTICS + "/app/utxo/covenant-count")
    print("  seite /app/utxo/covenant-count  http %s, %d zeichen" % (st, len(txt)))
    if st == 200:
        for u in umfeld(txt, r"covenant-bound|Covenant UTXO|description", 320, 4):
            print("    … %s" % kurz(u, 400))
    probiere([KASPALYTICS + p for p in [
        "/api/charts/utxo/covenant-count",
        "/api/charts/utxo/circulating-supply",
        "/api/charts/utxo/count",
    ]], "kandidaten aus dem seitenpfad:")

    print("\n" + "=" * 78)
    print("RUNDE 3 B  KASPA.STREAM, ADRESSEN AUS DEM VERSCHLEIERTEN BUENDEL")
    print("=" * 78)
    st, js = hole(BUENDEL)
    print("  buendel http %s, %d zeichen" % (st, len(js)))
    if st == 200:
        klar = entschluessle(js)
        print("  nach dem zurueckrechnen %d zeichen" % len(klar))
        adressen = sorted(set(re.findall(r"https?://[A-Za-z0-9_.\-]+[A-Za-z0-9_\-./]*", klar)))
        print("\n  adressen im klartext (%d):" % len(adressen))
        for a in adressen[:60]:
            print("      %s" % a)
        pfade = sorted(set(re.findall(r"['\"](/(?:api|v1|v2|socket)[A-Za-z0-9_\-/.]*)['\"]", klar)))
        print("\n  pfade im klartext (%d):" % len(pfade))
        for p in pfade[:60]:
            print("      %s" % p)
        print("\n  umfeld von 'distribution' im klartext:")
        for u in umfeld(klar, r"distribution", 240, 8):
            print("      … %s" % kurz(u, 300))
        print("\n  umfeld von 'socket' / 'io(' im klartext:")
        for u in umfeld(klar, r"socket\.io|io\(|VITE_|import\.meta\.env", 240, 12):
            print("      … %s" % kurz(u, 300))
        print("\n  umfeld von 'PLANKTON' (die stufenliste):")
        for u in umfeld(klar, r"PLANKTON", 700, 2):
            print("      … %s" % kurz(u, 900))

    probiere([
        "https://kaspa.stream/socket.io/?EIO=4&transport=polling",
        "https://api.kaspa.stream/",
        "https://api.kaspa.stream/distribution",
        "https://api.kaspa.stream/addresses/top",
        "https://api.kaspa.stream/info",
        "https://kaspa.stream/api/v1/distribution",
    ], "handschlag und naheliegende hosts:")
    print("\nfertig.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
