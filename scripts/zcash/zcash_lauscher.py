#!/usr/bin/env python3
"""zcash_lauscher.py - hoert Block-Ankuendigungen im Zcash-Netz mit (Testnet oder Mainnet).

Entstanden als testnet_lauscher.py (Ersatzmessung D, Ben 15.10.2026, Lauf
17.10.2026 auf messung/zcash-nu7). Seit 23.10.2026 auch fuer das Mainnet
(--netz mainnet): Ben will nach der NU7-Aktivierung 48 Stunden lang wissen,
wie viele angekuendigte Bloecke bei 25 s nicht in die Kette kommen. Ein
GitHub-Job laeuft hoechstens 6 h; die 48 h sind deshalb eine Kette von
Laeufen (.github/workflows/zcash-mainnet-lauscher.yml).

Wir haben keinen eigenen Knoten.
Dieser Zuhoerer haelt bis zu --dauer Minuten Verbindungen zu mehreren
Zebra- und Zakura-Knoten und schreibt jede Block-Ankuendigung (inv oder
headers) mit Ankunftszeit mit. Fuer jeden neu gesehenen Block-Hash holt er
den Block einmal beim ersten Ankuendiger (getdata) und behaelt nur den Kopf:
so kennen wir auch von Bloecken, die nicht in der Kette landen, Vorgaenger,
Zeitstempel und nBits.

Was das ist und was nicht: EIN Zuhoerer an EINEM Ort. Er sieht nur, was die
verbundenen Knoten ihm ankuendigen, und die Ankunftszeit enthaelt den Weg
vom Knoten zu uns. Kein eigener Knoten, keine Validierung der Bloecke.

Keine IP und kein Hostname in Ausgabe oder Log. Peers heissen zebra-1,
zakura-2 usw., dazu ihr User-Agent.

  python3 scripts/zcash/zcash_lauscher.py --netz mainnet --dauer 330 \
      --ereignisse lauscher.jsonl --koepfe lauscher-koepfe.jsonl --meta lauscher-meta.json
"""
import argparse
import json
import os
import socket
import struct
import sys
import threading
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zcash_koepfe  # noqa: E402
from zcash_koepfe import NETZE, Peer, kopf_lesen, lies_varint, log, peers_finden, varint  # noqa: E402

MSG_BLOCK = 2
ZIEL_JE_SOFTWARE = 8      # so viele Verbindungen je Software halten
NACHFASSEN_S = 60          # so oft fehlende Verbindungen nachholen
SEEDS_NEU_S = 1800         # so oft die DNS-Seeds neu fragen


def software(agent):
    a = agent.lower()
    if "zakura" in a:
        return "zakura"
    if "zebra" in a:
        return "zebra"
    return "andere"


class Zuhoerer:
    def __init__(self, ende, ereignisse_pfad, koepfe_pfad):
        self.ende = ende
        self.lock = threading.Lock()
        self.ereignisse = open(ereignisse_pfad, "w")
        self.koepfe = open(koepfe_pfad, "w")
        self.gesehen = set()          # Hashes, fuer die getdata schon raus ist
        self.koepfe_da = set()
        self.aktiv = {}               # label -> software
        self.zaehler = {"zebra": 0, "zakura": 0, "andere": 0}
        self.peers = []               # Meta je Verbindung, ohne Adresse
        self.hoechste = 0

    def schreiben(self, datei, obj):
        with self.lock:
            datei.write(json.dumps(obj, separators=(",", ":")) + "\n")
            datei.flush()

    def kopf_ablegen(self, raw, label, quelle):
        k = kopf_lesen(raw)
        h = k["hash"][::-1].hex()
        with self.lock:
            if h in self.koepfe_da:
                return h
            self.koepfe_da.add(h)
        self.schreiben(self.koepfe, {"hash": h, "prev": k["prev"][::-1].hex(), "zeit": k["zeit"],
                                     "nbits": f"{k['bits']:08x}", "von": label, "quelle": quelle})
        return h

    def peer_lauf(self, p, label, info):
        p.s.settimeout(90)
        try:
            while time.time() < self.ende:
                try:
                    cmd, payload = p.empfangen()
                except socket.timeout:
                    continue
                t_ms = int(time.time() * 1000)
                if cmd == "inv":
                    n, i = lies_varint(payload, 0)
                    neu = []
                    for _ in range(n):
                        typ = struct.unpack_from("<I", payload, i)[0]
                        h_intern = payload[i + 4:i + 36]
                        i += 36
                        if typ != MSG_BLOCK:
                            continue
                        h = h_intern[::-1].hex()
                        self.schreiben(self.ereignisse, {"t_ms": t_ms, "peer": label, "art": "inv", "hash": h})
                        info["ankuendigungen"] += 1
                        with self.lock:
                            if h not in self.gesehen:
                                self.gesehen.add(h)
                                neu.append(h_intern)
                    if neu:
                        p.senden("getdata", varint(len(neu)) + b"".join(struct.pack("<I", MSG_BLOCK) + x for x in neu))
                elif cmd == "headers":
                    n, i = lies_varint(payload, 0)
                    for _ in range(n):
                        start = i
                        i += 4 + 32 + 32 + 32 + 4 + 4 + 32
                        sl, i = lies_varint(payload, i)
                        i += sl
                        h = self.kopf_ablegen(payload[start:i], label, "headers")
                        _, i = lies_varint(payload, i)
                        self.schreiben(self.ereignisse, {"t_ms": t_ms, "peer": label, "art": "headers", "hash": h})
                        info["ankuendigungen"] += 1
                elif cmd == "block":
                    # Nur der Kopf: 140 Byte fest, dann die Equihash-Loesung.
                    i = 140
                    sl, i = lies_varint(payload, i)
                    self.kopf_ablegen(payload[:i + sl], label, "block")
        except (OSError, ConnectionError, TimeoutError, struct.error, IndexError) as e:
            info["ende_grund"] = type(e).__name__
        finally:
            info["getrennt_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            p.zu()
            with self.lock:
                self.aktiv.pop(label, None)

    def verbinden(self, adressen, versucht):
        for addr in adressen:
            if time.time() >= self.ende:
                return
            with self.lock:
                stand = {s: sum(1 for x in self.aktiv.values() if x == s) for s in ("zebra", "zakura")}
            if all(v >= ZIEL_JE_SOFTWARE for v in stand.values()):
                return
            if addr in versucht:
                continue
            versucht.add(addr)
            try:
                p = Peer(addr, timeout=12)
                p.handschlag()
            except (OSError, ConnectionError, TimeoutError, struct.error, IndexError):
                continue
            sw = software(p.agent)
            # Knoten, die selbst noch synchronisieren, kuendigen nichts Aktuelles an.
            if sw == "andere" or p.hoehe < self.hoechste - 100:
                p.zu()
                continue
            if stand.get(sw, 0) >= ZIEL_JE_SOFTWARE:
                p.zu()
                versucht.discard(addr)  # nur gerade voll, spaeter wieder fragen
                continue
            self.hoechste = max(self.hoechste, p.hoehe)
            with self.lock:
                self.zaehler[sw] += 1
                label = f"{sw}-{self.zaehler[sw]}"
                self.aktiv[label] = sw
            info = {"peer": label, "software": p.agent, "version": p.version, "gemeldete_hoehe": p.hoehe,
                    "verbunden_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "ankuendigungen": 0}
            self.peers.append(info)
            log(f"verbunden: {label} {p.agent} hoehe {p.hoehe}")
            threading.Thread(target=self.peer_lauf, args=(p, label, info), daemon=True).start()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--netz", choices=sorted(NETZE), default="testnet")
    ap.add_argument("--dauer", type=float, required=True, help="Minuten")
    ap.add_argument("--ereignisse", required=True)
    ap.add_argument("--koepfe", required=True)
    ap.add_argument("--meta", required=True)
    args = ap.parse_args()
    zcash_koepfe.netz_setzen(args.netz)

    start = time.time()
    ende = start + args.dauer * 60
    z = Zuhoerer(ende, args.ereignisse, args.koepfe)
    adressen, seeds_zeit = peers_finden(), time.time()
    versucht = set()
    letzte_meldung = 0
    while time.time() < ende:
        if time.time() - seeds_zeit > SEEDS_NEU_S:
            adressen, seeds_zeit = peers_finden(), time.time()
            versucht = set()  # getrennte Knoten duerfen wieder
        z.verbinden(adressen, versucht)
        if time.time() - letzte_meldung > 600:
            with z.lock:
                stand = dict(sorted({s: sum(1 for x in z.aktiv.values() if x == s) for s in ("zebra", "zakura")}.items()))
            log(f"{datetime.now(timezone.utc):%H:%M} UTC verbunden {stand}, block-hashes {len(z.gesehen)}")
            letzte_meldung = time.time()
        time.sleep(min(NACHFASSEN_S, max(0, ende - time.time())))
    tatsaechliches_ende = time.time()
    time.sleep(2)  # laufende Threads schreiben ihr Ende

    meta = {
        "art": f"ein Zuhoerer (kein eigener Knoten), Verbindungen zu {args.netz.capitalize()}-Knoten aus den DNS-Seeds",
        "netz": args.netz,
        "protokoll": zcash_koepfe.PROTOKOLL,
        # Tatsaechliches Fenster (Ben, 17.10.2026): Start und Ende, wie sie
        # waren, nicht wie geplant. Das geplante Ende steht daneben.
        "start_utc": datetime.fromtimestamp(start, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ende_utc": datetime.fromtimestamp(tatsaechliches_ende, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "geplantes_ende_utc": datetime.fromtimestamp(ende, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dauer_min": args.dauer,
        "ziel_verbindungen_je_software": ZIEL_JE_SOFTWARE,
        "peers": z.peers,
        "block_hashes_gesehen": len(z.gesehen | z.koepfe_da),
        "koepfe_geholt": len(z.koepfe_da),
        "zeitquelle": "Uhr des Runners (NTP), Millisekunden",
    }
    with open(args.meta, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"peers": len(z.peers), "hashes": meta["block_hashes_gesehen"]}))


if __name__ == "__main__":
    main()
