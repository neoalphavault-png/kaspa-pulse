#!/usr/bin/env python3
"""roh_export.py - Rohdaten der Upgrade-Wache fuer den Datenbranch (Ben, 02.11.2026).

Nach dem Fenster gehen die Rohdaten auf den Datenbranch der Konfiguration
(Zcash: messung/zcash-mainnet), damit der PulseHawk Upgrade Report v1 aus
ihnen nachrechenbar ist. Dieses Skript schreibt sie in einen Zielordner:

  ereignisse.jsonl.gz  jede Block-Ankuendigung (t_ms, peer, art, hash), nur
                       aus dem Fenster
  koepfe.jsonl.gz      die Koepfe dazu (hash, prev, zeit, nbits, von, quelle)
  peers.json           je Peer unsere Nummer (zebra-3), Software, Protokoll,
                       gemeldete Hoehe, verbunden/getrennt; keine Adresse
  zustand.json         Proben (M5), Zeitpunkt der gesehenen Aktivierung
  wache-log.csv        das Log der Wache
  SHA256SUMS           sha256 jeder Datei

Die gz-Dateien sind deterministisch (ohne Zeitstempel im Kopf): gleiche
Daten, gleiche Bytes, also kein neuer Commit, wenn sich nichts aendert.
Steht irgendwo etwas, das wie eine IPv4- oder IPv6-Adresse aussieht, bricht
das Skript ab und schreibt nichts.

  python3 scripts/wache/roh_export.py --kette scripts/wache/ketten/zcash-mainnet.json \\
      --ablage /var/lib/kaspa-pulse/wache/zcash-mainnet --aus <klon>/wache/roh
"""
import argparse
import glob
import gzip
import hashlib
import io
import json
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
from wache_kern import ts  # noqa: E402

ADRESSE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b|\[[0-9a-fA-F:]{6,}\]|\b(?:[0-9a-fA-F]{1,4}:){4,7}[0-9a-fA-F]{1,4}\b")


def fenster(cfg, zustand):
    f = cfg["fenster"]
    anker = zustand.get("aktiv_gesehen_utc") or cfg["aktivierung"]["erwartet_utc"]
    return ts(cfg["aktivierung"]["erwartet_utc"]) - f["vor_h"] * 3600, ts(anker) + f["nach_h"] * 3600


def jsonl(muster):
    for pfad in sorted(glob.glob(muster)):
        opener = gzip.open if pfad.endswith(".gz") else open
        with opener(pfad, "rt") as f:
            for z in f:
                z = z.strip()
                if z:
                    yield json.loads(z)


def gz_bytes(zeilen):
    roh = io.BytesIO()
    with gzip.GzipFile(fileobj=roh, mode="wb", mtime=0) as g:
        for z in zeilen:
            g.write((json.dumps(z, separators=(",", ":"), sort_keys=True) + "\n").encode())
    return roh.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kette", required=True)
    ap.add_argument("--ablage", required=True)
    ap.add_argument("--aus", required=True)
    args = ap.parse_args()

    cfg = json.load(open(args.kette))
    zp = os.path.join(args.ablage, "zustand.json")
    zustand = json.load(open(zp)) if os.path.exists(zp) else {}
    von, bis = fenster(cfg, zustand)
    roh = os.path.join(args.ablage, "roh")

    ereignisse = [e for e in jsonl(os.path.join(roh, "*-ereignisse.jsonl*")) if von * 1000 <= e["t_ms"] < bis * 1000]
    ereignisse.sort(key=lambda e: (e["t_ms"], e["peer"], e["hash"]))
    gesehen = {e["hash"] for e in ereignisse}
    koepfe, da = [], set()
    for k in jsonl(os.path.join(roh, "*-koepfe.jsonl*")):
        if k["hash"] in da or not (k["hash"] in gesehen or von <= k["zeit"] < bis):
            continue
        da.add(k["hash"])
        koepfe.append(k)
    koepfe.sort(key=lambda k: (k["zeit"], k["hash"]))
    peers = []
    for pfad in sorted(glob.glob(os.path.join(roh, "*-peers.json"))):
        lauf = os.path.basename(pfad).split("-peers.json")[0]
        for p in json.load(open(pfad))["peers"]:
            peers.append({"lauf": lauf, **p})

    dateien = {
        "ereignisse.jsonl.gz": gz_bytes(ereignisse),
        "koepfe.jsonl.gz": gz_bytes(koepfe),
        "peers.json": (json.dumps({"netz": cfg["quelle"]["netz"], "peers": peers}, indent=1, ensure_ascii=False)
                       + "\n").encode(),
        "zustand.json": (json.dumps(zustand, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode(),
    }
    log = os.path.join(args.ablage, "wache-log.csv")
    if os.path.exists(log):
        dateien["wache-log.csv"] = open(log, "rb").read()

    for name, inhalt in dateien.items():
        text = gzip.decompress(inhalt).decode() if name.endswith(".gz") else inhalt.decode()
        if ADRESSE.search(text):
            sys.exit(f"abbruch: adresse in {name}, nichts geschrieben")

    os.makedirs(args.aus, exist_ok=True)
    summen = []
    for name in sorted(dateien):
        with open(os.path.join(args.aus, name), "wb") as f:
            f.write(dateien[name])
        summen.append(f"{hashlib.sha256(dateien[name]).hexdigest()}  {name}")
    with open(os.path.join(args.aus, "SHA256SUMS"), "w") as f:
        f.write("\n".join(summen) + "\n")
    print(json.dumps({"fenster_utc": [von, bis], "ereignisse": len(ereignisse), "koepfe": len(koepfe),
                      "peers": len(peers), "dateien": sorted(dateien)}))


if __name__ == "__main__":
    main()
