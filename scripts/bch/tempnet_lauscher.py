#!/usr/bin/env python3
"""tempnet_lauscher.py - hoert Block-Ankuendigungen im BCH Tempnet mit.

Ben, 25.10.2026 (Woche 2): bitcoincashautist bat im Tempnet-Thread um alles,
was nicht in der kanonischen Kette landet (Stale-Bloecke), lokale
Empfangszeit gegen Header-Zeit, den Compact-Block-Weg und die Ausbreitung
ueber Ankuendigungen; rufitnes um einen Mitschnitt von einem anderen
Netzwerkpfad. Dieser Zuhoerer ist der Zcash-Zuhoerer
(scripts/zcash/zcash_lauscher.py) fuer das Tempnet, mit drei Ergaenzungen:

1. Nur Peers, die den Abzweig bestaetigen (Ben, 21.10.2026): nach dem
   Handschlag getheaders ab dem letzten gemeinsamen Block 327.988; der erste
   Kopf muss der Tempnet-Block 327.989 sein, sonst wird getrennt.
2. Jede Ankuendigung wird mit Nachrichtentyp mitgeschrieben: inv, headers oder
   cmpctblock. Damit alle drei Wege vorkommen, bitten wir jeden Peer per
   sendcmpct um Compact-Bloecke im High-Bandwidth-Modus (ein Knoten waehlt
   hoechstens drei solche Peers) und jeden zweiten Peer per sendheaders um
   Kopf-Ankuendigungen; die uebrigen kuendigen per inv an.
3. Compact-Block-Weg: fuer jeden neuen Block holen wir beim ersten
   Ankuendiger einen cmpctblock (getdata Typ 4), wenn keiner von selbst kam.
   Wir haben keinen Mempool. Deshalb sammeln wir die Transaktions-IDs, die
   Peers per inv ankuendigen (relay=1 im Handschlag), und rechnen fuer jeden
   cmpctblock aus, wie viele seiner Kurz-IDs (BIP152: SipHash-2-4 mit dem
   Schluessel aus SHA256(Kopf || Nonce), 6 Byte) wir nicht kennen. Das ist
   eine Schaetzung dessen, was ein Knoten mit genau diesen Transaktionen haette
   nachfordern muessen, nicht die Zahl eines echten Knotens.

EIN Zuhoerer an EINEM Ort; die Ankunftszeit enthaelt den Weg vom Knoten zu uns.
Keine IP, kein Hostname, keine Peer-Adresse in Ausgabe oder Log. Peers heissen
peer_1, peer_2 usw., je Lauf neu vergeben.

  python3 scripts/bch/tempnet_lauscher.py --dauer 330 --aus <ordner>
  -> ereignisse.jsonl, koepfe.jsonl, compact.jsonl, meta.json
"""
import argparse
import hashlib
import json
import os
import random
import socket
import struct
import sys
import threading
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tempnet_koepfe as TK  # noqa: E402
from tempnet_koepfe import (ERSTER_TEMPNET, LETZTER_GEMEINSAMER, Peer, kopf_lesen,  # noqa: E402
                            lies_varint, log, peers_finden, sha256d, varint)

MSG_TX, MSG_BLOCK, MSG_CMPCT_BLOCK = 1, 2, 4
NACHFASSEN_S = 60          # so oft fehlende Verbindungen nachholen
QUELLE_NEU_S = 1800        # so oft die oeffentliche Konfiguration neu lesen
TX_HALTEN_S = 3 * 3600     # so lange behalten wir angekuendigte Transaktions-IDs
CMPCT_WARTEN_S = 3         # so lange auf einen cmpctblock von selbst warten, dann holen
START_HASH = bytes.fromhex(LETZTER_GEMEINSAMER[1])[::-1]
ERSTER_HASH = bytes.fromhex(ERSTER_TEMPNET[1])[::-1]


def jetzt_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------- BIP152 Kurz-IDs
def _rotl(x, b):
    return ((x << b) | (x >> (64 - b))) & 0xFFFFFFFFFFFFFFFF


def siphash24(k0, k1, daten):
    """SipHash-2-4 ueber Bytes, Schluessel als zwei 64-bit-Zahlen (BIP152)."""
    m64 = 0xFFFFFFFFFFFFFFFF
    v0, v1 = k0 ^ 0x736F6D6570736575, k1 ^ 0x646F72616E646F6D
    v2, v3 = k0 ^ 0x6C7967656E657261, k1 ^ 0x7465646279746573

    def runde():
        nonlocal v0, v1, v2, v3
        v0 = (v0 + v1) & m64; v1 = _rotl(v1, 13) ^ v0; v0 = _rotl(v0, 32)
        v2 = (v2 + v3) & m64; v3 = _rotl(v3, 16) ^ v2
        v0 = (v0 + v3) & m64; v3 = _rotl(v3, 21) ^ v0
        v2 = (v2 + v1) & m64; v1 = _rotl(v1, 17) ^ v2; v2 = _rotl(v2, 32)
    n = len(daten)
    ende = n - n % 8
    for i in range(0, ende, 8):
        m = int.from_bytes(daten[i:i + 8], "little")
        v3 ^= m; runde(); runde(); v0 ^= m
    letzt = (n & 0xFF) << 56 | int.from_bytes(daten[ende:].ljust(8, b"\0")[:7], "little")
    v3 ^= letzt; runde(); runde(); v0 ^= letzt
    v2 ^= 0xFF
    for _ in range(4):
        runde()
    return (v0 ^ v1 ^ v2 ^ v3) & m64


def kurz_id(k0, k1, txid_intern):
    return siphash24(k0, k1, txid_intern) & 0xFFFFFFFFFFFF


def cmpct_lesen(p):
    """cmpctblock: Kopf (80), Nonce (8), Kurz-IDs (6 Byte je), vorbefuellte TX.
    Liefert Kopf, Schluessel und Kurz-IDs; die vorbefuellten TX zaehlen wir nur."""
    kopf, nonce = p[:80], p[80:88]
    n, i = lies_varint(p, 88)
    ids = [int.from_bytes(p[i + 6 * j:i + 6 * j + 6], "little") for j in range(n)]
    i += 6 * n
    vor, _ = lies_varint(p, i)
    h = hashlib.sha256(kopf + nonce).digest()
    return kopf, int.from_bytes(h[:8], "little"), int.from_bytes(h[8:16], "little"), ids, vor


# ------------------------------------------------------------- Zuhoerer
class TempnetPeer(Peer):
    """Peer aus tempnet_koepfe mit relay=1 im Handschlag (sonst kuendigt uns
    niemand Transaktionen an) und den Wuenschen sendheaders/sendcmpct."""

    def handschlag(self):
        leer_addr = struct.pack("<Q", 0) + b"\0" * 10 + b"\xff\xff" + b"\0" * 4 + struct.pack(">H", 0)
        payload = (struct.pack("<iQq", TK.PROTOKOLL, 0, int(time.time())) + leer_addr + leer_addr
                   + struct.pack("<Q", random.getrandbits(64)) + varint(len(TK.USER_AGENT)) + TK.USER_AGENT
                   + struct.pack("<i", 0) + b"\x01")
        self.senden("version", payload)
        hat_version = hat_verack = False
        frist = time.time() + 30
        while not (hat_version and hat_verack):
            if time.time() > frist:
                raise TimeoutError("handschlag dauert zu lange")
            cmd, p = self.empfangen()
            if cmd == "version":
                self.version = struct.unpack_from("<i", p, 0)[0]
                i = 4 + 8 + 8 + 26 + 26 + 8
                n, i = lies_varint(p, i)
                self.agent = p[i:i + n].decode(errors="replace")
                self.hoehe = struct.unpack_from("<i", p, i + n)[0]
                self.senden("verack")
                hat_version = True
            elif cmd == "verack":
                hat_verack = True
            elif cmd == "reject":
                raise ConnectionError("version abgelehnt")


class Zuhoerer:
    def __init__(self, ende, aus):
        self.ende = ende
        self.lock = threading.Lock()
        self.dateien = {n: open(os.path.join(aus, f"{n}.jsonl"), "w") for n in ("ereignisse", "koepfe", "compact")}
        self.bloecke = {}             # hash -> {"erster": label, "cmpct": bool, "geholt": bool}
        self.koepfe_da = set()
        self.tx = {}                  # txid intern -> zeit der ersten ankuendigung
        self.aktiv = {}               # label -> peer-objekt
        self.zaehler = 0
        self.peers = []               # Meta je Verbindung, ohne Adresse
        self.ohne_abzweig = 0
        self.hoechste = 0

    def schreiben(self, name, obj):
        with self.lock:
            f = self.dateien[name]
            f.write(json.dumps(obj, separators=(",", ":")) + "\n")
            f.flush()

    def kopf_ablegen(self, raw, label, quelle):
        k = kopf_lesen(raw[:80])
        h = k["hash"][::-1].hex()
        with self.lock:
            if h in self.koepfe_da:
                return h
            self.koepfe_da.add(h)
        self.schreiben("koepfe", {"hash": h, "prev": k["prev"][::-1].hex(), "zeit": k["zeit"],
                                  "nbits": f"{k['bits']:08x}", "von": label, "quelle": quelle})
        return h

    def ankuendigung(self, t_ms, label, art, h, p, intern=None):
        self.schreiben("ereignisse", {"t_ms": t_ms, "peer": label, "art": art, "hash": h})
        with self.lock:
            neu = h not in self.bloecke
            if neu:
                self.bloecke[h] = {"erster": label, "cmpct": art == "cmpctblock", "geholt": False}
        if neu and intern is not None and art != "cmpctblock":
            # Kommt nicht gleich von selbst ein cmpctblock, holen wir ihn beim ersten Ankuendiger.
            threading.Timer(CMPCT_WARTEN_S, self.cmpct_holen, args=(h, intern, p)).start()

    def cmpct_holen(self, h, intern, p):
        with self.lock:
            b = self.bloecke.get(h)
            if not b or b["cmpct"] or b["geholt"]:
                return
            b["geholt"] = True
        try:
            p.senden("getdata", varint(1) + struct.pack("<I", MSG_CMPCT_BLOCK) + intern)
        except OSError:
            pass

    def compact_auswerten(self, t_ms, label, payload, von_selbst):
        kopf, k0, k1, ids, vor = cmpct_lesen(payload)
        h = self.kopf_ablegen(kopf, label, "cmpctblock")
        with self.lock:
            grenze = time.time() - TX_HALTEN_S
            for t in [t for t, z in self.tx.items() if z < grenze]:
                del self.tx[t]
            bekannt = {kurz_id(k0, k1, t) for t in self.tx}
            if h in self.bloecke:
                self.bloecke[h]["cmpct"] = True
        fehlend = sum(1 for x in ids if x not in bekannt)
        self.schreiben("compact", {"t_ms": t_ms, "peer": label, "hash": h, "von_selbst": von_selbst,
                                   "kurz_ids": len(ids), "vorbefuellt": vor, "fehlend_geschaetzt": fehlend,
                                   "tx_ids_bekannt": len(bekannt)})
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
                    for _ in range(n):
                        typ = struct.unpack_from("<I", payload, i)[0]
                        intern = payload[i + 4:i + 36]
                        i += 36
                        if typ == MSG_TX:
                            with self.lock:
                                self.tx.setdefault(intern, time.time())
                        elif typ == MSG_BLOCK:
                            self.ankuendigung(t_ms, label, "inv", intern[::-1].hex(), p, intern)
                            info["ankuendigungen"] += 1
                elif cmd == "headers":
                    n, i = lies_varint(payload, 0)
                    for _ in range(n):
                        raw = payload[i:i + 80]
                        i += 80
                        _, i = lies_varint(payload, i)
                        h = self.kopf_ablegen(raw, label, "headers")
                        self.ankuendigung(t_ms, label, "headers", h, p, sha256d(raw))
                        info["ankuendigungen"] += 1
                elif cmd == "cmpctblock":
                    with self.lock:
                        h_vorher = sha256d(payload[:80])[::-1].hex()
                        geholt = self.bloecke.get(h_vorher, {}).get("geholt", False) \
                            and self.bloecke[h_vorher]["erster"] == label
                    h = self.compact_auswerten(t_ms, label, payload, von_selbst=not geholt)
                    if not geholt:
                        self.ankuendigung(t_ms, label, "cmpctblock", h, p)
                        info["ankuendigungen"] += 1
                elif cmd == "block":
                    # Statt cmpctblock kam der ganze Block: nur den Kopf behalten.
                    self.kopf_ablegen(payload[:80], label, "block")
                    info["ganze_bloecke"] = info.get("ganze_bloecke", 0) + 1
        except (OSError, ConnectionError, TimeoutError, struct.error, IndexError, ValueError) as e:
            info["ende_grund"] = type(e).__name__
        finally:
            info["getrennt_utc"] = jetzt_utc()
            p.zu()
            with self.lock:
                self.aktiv.pop(label, None)

    def verbinden(self, adressen, versucht):
        for addr in adressen:
            if time.time() >= self.ende:
                return
            if addr in versucht:
                continue
            versucht.add(addr)
            try:
                p = TempnetPeer(addr, timeout=12)
                p.handschlag()
                probe = p.koepfe([START_HASH], warten=20)
            except (OSError, ConnectionError, TimeoutError, struct.error, IndexError):
                continue
            if not probe or sha256d(probe[0]) != ERSTER_HASH:
                # Chipnet-Knoten oder einer, der den Abzweig nicht liefert (Ben, 21.10.2026)
                self.ohne_abzweig += 1
                p.zu()
                continue
            if p.hoehe < self.hoechste - 100:
                p.zu()
                versucht.discard(addr)  # synchronisiert noch, spaeter wieder fragen
                continue
            self.hoechste = max(self.hoechste, p.hoehe)
            with self.lock:
                self.zaehler += 1
                label = f"peer_{self.zaehler}"
                self.aktiv[label] = p
            weg = "headers" if self.zaehler % 2 == 0 else "inv"
            try:
                p.senden("sendcmpct", b"\x01" + struct.pack("<Q", 1))
                if weg == "headers":
                    p.senden("sendheaders")
            except OSError:
                pass
            info = {"peer": label, "software": p.agent, "version": p.version, "gemeldete_hoehe": p.hoehe,
                    "verbunden_utc": jetzt_utc(), "erbeten": ["cmpctblock", weg], "ankuendigungen": 0}
            self.peers.append(info)
            log(f"verbunden: {label} {p.agent} hoehe {p.hoehe}, abzweig bestaetigt, erbeten {weg}")
            threading.Thread(target=self.peer_lauf, args=(p, label, info), daemon=True).start()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dauer", type=float, required=True, help="Minuten")
    ap.add_argument("--aus", required=True, help="Ordner fuer ereignisse/koepfe/compact.jsonl und meta.json")
    args = ap.parse_args()
    os.makedirs(args.aus, exist_ok=True)

    start = time.time()
    ende = start + args.dauer * 60
    z = Zuhoerer(ende, args.aus)
    adressen, quelle_zeit = peers_finden(), time.time()
    versucht = set()
    letzte_meldung = 0
    while time.time() < ende:
        if time.time() - quelle_zeit > QUELLE_NEU_S:
            adressen, quelle_zeit = peers_finden(), time.time()
            versucht = set()
        z.verbinden(adressen, versucht)
        if time.time() - letzte_meldung > 600:
            with z.lock:
                n_aktiv, n_bl, n_tx = len(z.aktiv), len(z.bloecke), len(z.tx)
            log(f"{datetime.now(timezone.utc):%H:%M} UTC verbunden {n_aktiv}, block-hashes {n_bl}, tx-ids {n_tx}")
            letzte_meldung = time.time()
        time.sleep(min(NACHFASSEN_S, max(0, ende - time.time())))
    tatsaechliches_ende = time.time()
    time.sleep(2)

    meta = {
        "art": "ein Zuhoerer (kein eigener Knoten), Verbindungen zu Tempnet-Knoten aus der oeffentlichen Konfiguration",
        "start_utc": datetime.fromtimestamp(start, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ende_utc": datetime.fromtimestamp(tatsaechliches_ende, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "geplantes_ende_utc": datetime.fromtimestamp(ende, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dauer_min": args.dauer,
        "protokoll": TK.PROTOKOLL,
        "peers": z.peers,
        "peers_ohne_abzweig_abgelehnt": z.ohne_abzweig,
        "block_hashes_gesehen": len(z.bloecke),
        "koepfe_geholt": len(z.koepfe_da),
        "zeitquelle": "Uhr des Runners (NTP), Millisekunden",
        "labels": "peer_N je Lauf neu vergeben, nicht lauf-uebergreifend",
    }
    with open(os.path.join(args.aus, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"peers": len(z.peers), "hashes": meta["block_hashes_gesehen"],
                      "ohne_abzweig": z.ohne_abzweig}))


if __name__ == "__main__":
    main()
