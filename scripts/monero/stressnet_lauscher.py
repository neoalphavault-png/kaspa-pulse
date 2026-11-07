#!/usr/bin/env python3
"""stressnet_lauscher.py - hoert neue Bloecke im Monero-Stressnet mit (Ben, 07.11.2026, Weg b).

Reiner P2P-Zuhoerer ueber das Levin-Protokoll, kein monerod, keine volle
Pruefung (berichte/2026-11-06-monero-stressnet-plan.md). Er haelt Verbindungen
zu Stressnet-Knoten und schreibt fuer jeden neuen Block (NOTIFY_NEW_FLUFFY_BLOCK)
die Ankunftszeit je Peer und den Kopf mit. Den Blockhash rechnet er selbst
nach (Keccak ueber den Hashing-Blob, Inhalts-Hash als Merkle-Baum aus Miner-Tx,
FCMP++-Feldern und Tx-Hashes). Ob die Rechnung stimmt, zeigt die Verkettung:
der Vorgaenger des naechsten Blocks muss unser Hash sein. Den Arbeitsnachweis
(RandomX v2) prueft er nicht.

Das Stressnet nutzt Ports und Netzwerk-ID des Testnets. Ein Peer zaehlt nur,
wenn er im Handschlag top_version >= 17 und eine Hoehe ueber dem Abzweig
3.102.800 meldet. Normale Testnet-Knoten (Version 16) werden getrennt.

Probe (--probe, 15 min): Haelfte der Peers mit ehrlicher Hoehe 1 (wie ein
Knoten, der noch synchronisiert), Haelfte mit der zuletzt gesehenen Spitze.
So zeigt die Probe, ob Knoten einem synchronisierenden Peer neue Bloecke
schicken und ob sie uns verbunden lassen.

Keine IP, kein Hostname, keine Peer-Adresse in Ausgabe, Log oder Datei.
Peers heissen peer_1, peer_2 usw. 64-hex nur fuer Blockhashes. Transaktionen
nur als Zahl. Seeds liest das Skript zur Laufzeit aus dem Quelltext des
Stressnet-Tags (net_node.inl, Liste TESTNET), weitere Peers aus den
Peerlisten der Handschlaege, nur im Speicher.

  python3 scripts/monero/stressnet_lauscher.py --selbsttest
  python3 scripts/monero/stressnet_lauscher.py --probe --dauer 15 --aus <ordner>
  -> meta.json, peers.json, bloecke.csv, ankuendigungen.csv
"""
import argparse
import csv
import json
import os
import random
import re
import socket
import struct
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone

TAG = "v0.19.0.0-beta.3.1"
QUELLE = f"https://raw.githubusercontent.com/seraphis-migration/monero/{TAG}/src/p2p/net_node.inl"
NETWORK_ID = bytes([0x12, 0x30, 0xF1, 0x71, 0x61, 0x04, 0x41, 0x61, 0x17, 0x31, 0x00, 0x82, 0x16, 0xA1, 0xA1, 0x11])
TESTNET_GENESIS = "48ca7cd3c8de5b6a4d53d2861fbdaedca141553559f9be9520068053cda8430b"
GENESIS_TX = ("013c01ff0001ffffffffffff03029b2e4c0281c0b02e7c53291a94d1d0cbff8883f8024f5142ee49"
              "4ffbbd08807121017767aafcde9be00dcfd098715ebcf7f410daebc582fda69d24a28e9d0bc890d1")
ABZWEIG = 3102800
HF_FCMP = 17
SUPPORT_FLAGS = 0x03          # fluffy blocks, tx relay v2
MAX_PEERS = 12
NACHFASSEN_S = 60

# ------------------------------------------------------------------ keccak
_RC = [0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000, 0x000000000000808B,
       0x0000000080000001, 0x8000000080008081, 0x8000000000008009, 0x000000000000008A, 0x0000000000000088,
       0x0000000080008009, 0x000000008000000A, 0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
       0x8000000000008003, 0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
       0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008]
_ROT = [[0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61], [28, 55, 25, 21, 56], [27, 20, 39, 8, 14]]
_M = (1 << 64) - 1


def _rol(v, n):
    return ((v << n) | (v >> (64 - n))) & _M if n else v


def _f(a):
    for rc in _RC:
        c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol(c[(x + 1) % 5], 1) for x in range(5)]
        a = [[a[x][y] ^ d[x] for y in range(5)] for x in range(5)]
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                b[y][(2 * x + 3 * y) % 5] = _rol(a[x][y], _ROT[x][y])
        a = [[b[x][y] ^ ((~b[(x + 1) % 5][y]) & b[(x + 2) % 5][y]) for y in range(5)] for x in range(5)]
        a[0][0] ^= rc
    return a


def keccak256(data):
    """Keccak-256 mit der urspruenglichen Auffuellung 0x01 (Monero cn_fast_hash), nicht SHA3."""
    rate = 136
    if len(data) % rate == rate - 1:         # Sonderfall: 0x01 und 0x80 im selben Byte
        p = bytearray(data) + b"\x81"
    else:
        p = bytearray(data) + b"\x01" + b"\x00" * ((-len(data) - 2) % rate) + b"\x80"
    a = [[0] * 5 for _ in range(5)]
    for i in range(0, len(p), rate):
        blk = p[i:i + rate]
        for j in range(rate // 8):
            x, y = j % 5, j // 5
            a[x][y] ^= int.from_bytes(blk[8 * j:8 * j + 8], "little")
        a = _f(a)
    return b"".join(a[j % 5][j // 5].to_bytes(8, "little") for j in range(4))


def tree_hash(hs):
    """Merkle-Baum wie tree_hash.c von Monero."""
    n = len(hs)
    if n == 1:
        return hs[0]
    if n == 2:
        return keccak256(hs[0] + hs[1])
    cnt = 1
    while cnt * 2 < n:
        cnt *= 2
    ints = list(hs[:2 * cnt - n])
    for i in range(2 * cnt - n, n, 2):
        ints.append(keccak256(hs[i] + hs[i + 1]))
    while cnt > 2:
        cnt //= 2
        ints = [keccak256(ints[2 * i] + ints[2 * i + 1]) for i in range(cnt)]
    return keccak256(ints[0] + ints[1])


# ------------------------------------------------------------------ binaeres format der kette
def varint(b, i):
    v, s = 0, 0
    while True:
        c = b[i]
        i += 1
        v |= (c & 0x7F) << s
        if not c & 0x80:
            return v, i
        s += 7


def varint_bytes(v):
    out = bytearray()
    while True:
        c = v & 0x7F
        v >>= 7
        if v:
            out.append(c | 0x80)
        else:
            out.append(c)
            return bytes(out)


class Unbekannt(Exception):
    pass


def tx_lesen(b, i):
    """Miner-Transaktion ab i. Liefert (ende, tx_hash, hoehe, version)."""
    start = i
    version, i = varint(b, i)
    _unlock, i = varint(b, i)
    n_in, i = varint(b, i)
    hoehe = None
    for _ in range(n_in):
        tag = b[i]
        i += 1
        if tag != 0xFF:
            raise Unbekannt(f"eingang typ {tag:#x} in der miner-tx")
        hoehe, i = varint(b, i)
    n_out, i = varint(b, i)
    for _ in range(n_out):
        _betrag, i = varint(b, i)
        tag = b[i]
        i += 1
        if tag == 0x01:                 # txout_to_carrot_v1: key 32, view tag 3, janus anchor 16
            i += 32 + 3 + 16
        elif tag == 0x02:               # txout_to_key
            i += 32
        elif tag == 0x03:               # txout_to_tagged_key
            i += 33
        else:
            raise Unbekannt(f"ausgang typ {tag:#x}")
    n_extra, i = varint(b, i)
    i += n_extra
    praefix_ende = i
    if version == 1:
        return i, keccak256(b[start:i]), hoehe, version
    rct_typ = b[i]
    i += 1
    if rct_typ != 0:
        raise Unbekannt(f"miner-tx mit rct typ {rct_typ}")
    h = keccak256(keccak256(b[start:praefix_ende]) + keccak256(b[praefix_ende:i]) + b"\x00" * 32)
    return i, h, hoehe, version


def block_lesen(b):
    """Block-Blob -> dict mit Kopf, Hoehe, Zahl der Tx und unserem Hash."""
    i = 0
    major, i = varint(b, i)
    minor, i = varint(b, i)
    zeit, i = varint(b, i)
    prev = b[i:i + 32]
    i += 32
    i += 4                                  # nonce
    kopf = b[:i]
    i, miner_hash, hoehe, _ = tx_lesen(b, i)
    n_tx, i = varint(b, i)
    tx_hashes = [b[i + 32 * k:i + 32 * k + 32] for k in range(n_tx)]
    i += 32 * n_tx
    liste = [miner_hash]
    if major >= HF_FCMP:
        lagen = b[i]
        wurzel = b[i + 1:i + 33]
        i += 33
        liste += [bytes([lagen]) + b"\x00" * 31, wurzel]
    if i != len(b):
        raise Unbekannt(f"blob hat {len(b) - i} byte mehr als gelesen")
    liste += tx_hashes
    hashing_blob = kopf + tree_hash(liste) + varint_bytes(n_tx + 1)
    # get_object_hash serialisiert den Blob als String: Laenge als varint davor
    block_id = keccak256(varint_bytes(len(hashing_blob)) + hashing_blob)
    return {"hoehe": hoehe, "hash": block_id.hex(), "prev": prev.hex(), "zeit": zeit,
            "major": major, "minor": minor, "n_tx": n_tx}


def genesis_hash(tx_hex, nonce):
    blob = varint_bytes(1) + varint_bytes(0) + varint_bytes(0) + b"\x00" * 32 + struct.pack("<I", nonce)
    blob += bytes.fromhex(tx_hex) + varint_bytes(0)
    return block_lesen(blob)["hash"]


# ------------------------------------------------------------------ epee portable storage
SIG = struct.pack("<IIB", 0x01011101, 0x01020101, 1)
T_I64, T_I32, T_I16, T_I8, T_U64, T_U32, T_U16, T_U8, T_DBL, T_STR, T_BOOL, T_OBJ, T_ARR = range(1, 14)
FLAG_ARR = 0x80


def e_varint(v):
    if v < 1 << 6:
        return struct.pack("<B", v << 2)
    if v < 1 << 14:
        return struct.pack("<H", (v << 2) | 1)
    if v < 1 << 30:
        return struct.pack("<I", (v << 2) | 2)
    return struct.pack("<Q", (v << 2) | 3)


def e_varint_lesen(b, i):
    m = b[i] & 3
    n = 1 << m
    v = int.from_bytes(b[i:i + n], "little") >> 2
    return v, i + n


class U:
    """Wert mit festem epee-Typ beim Schreiben."""
    def __init__(self, typ, wert):
        self.typ, self.wert = typ, wert


def _wert_schreiben(typ, w):
    fmt = {T_I64: "<q", T_I32: "<i", T_I16: "<h", T_I8: "<b", T_U64: "<Q", T_U32: "<I", T_U16: "<H",
           T_U8: "<B", T_DBL: "<d"}
    if typ in fmt:
        return struct.pack(fmt[typ], w)
    if typ == T_STR:
        return e_varint(len(w)) + w
    if typ == T_BOOL:
        return b"\x01" if w else b"\x00"
    if typ == T_OBJ:
        return _abschnitt_schreiben(w)
    raise ValueError(typ)


def _abschnitt_schreiben(d):
    out = e_varint(len(d))
    for k, v in d.items():
        kb = k.encode()
        out += struct.pack("<B", len(kb)) + kb
        if isinstance(v, dict):
            out += struct.pack("<B", T_OBJ) + _abschnitt_schreiben(v)
        else:
            out += struct.pack("<B", v.typ) + _wert_schreiben(v.typ, v.wert)
    return out


def epee_schreiben(d):
    return SIG + _abschnitt_schreiben(d)


def _wert_lesen(b, i, typ):
    fmt = {T_I64: "<q", T_I32: "<i", T_I16: "<h", T_I8: "<b", T_U64: "<Q", T_U32: "<I", T_U16: "<H",
           T_U8: "<B", T_DBL: "<d"}
    if typ in fmt:
        n = struct.calcsize(fmt[typ])
        return struct.unpack(fmt[typ], b[i:i + n])[0], i + n
    if typ == T_STR:
        n, i = e_varint_lesen(b, i)
        return bytes(b[i:i + n]), i + n
    if typ == T_BOOL:
        return b[i] != 0, i + 1
    if typ == T_OBJ:
        return _abschnitt_lesen(b, i)
    if typ == T_ARR:
        t = b[i]
        return _feld_lesen(b, i + 1, t)
    raise Unbekannt(f"epee typ {typ}")


def _feld_lesen(b, i, typ):
    if typ & FLAG_ARR:
        n, i = e_varint_lesen(b, i)
        out = []
        for _ in range(n):
            v, i = _wert_lesen(b, i, typ & 0x7F)
            out.append(v)
        return out, i
    return _wert_lesen(b, i, typ)


def _abschnitt_lesen(b, i):
    n, i = e_varint_lesen(b, i)
    d = {}
    for _ in range(n):
        ln = b[i]
        k = bytes(b[i + 1:i + 1 + ln]).decode()
        i += 1 + ln
        typ = b[i]
        d[k], i = _feld_lesen(b, i + 1, typ)
    return d, i


def epee_lesen(b):
    if bytes(b[:9]) != SIG:
        raise Unbekannt("keine epee-signatur")
    d, _ = _abschnitt_lesen(b, 9)
    return d


# ------------------------------------------------------------------ levin
LEVIN_SIG = 0x0101010101012101
HS, TIMED_SYNC, PING, SUPPORT = 1001, 1002, 1003, 1007
FLUFFY, TX_HASH = 2008, 2011
ANFRAGE, ANTWORT = 1, 2


def levin(cmd, nutzlast, erwartet_antwort, flags, rc=0):
    return struct.pack("<QQ?IiII", LEVIN_SIG, len(nutzlast), erwartet_antwort, cmd, rc, flags, 1) + nutzlast


def lesen_genau(s, n):
    teile, rest = [], n
    while rest:
        t = s.recv(min(rest, 1 << 16))
        if not t:
            raise ConnectionError("getrennt")
        teile.append(t)
        rest -= len(t)
    return b"".join(teile)


def sync_daten(hoehe, top_id, version, kum):
    return {"current_height": U(T_U64, hoehe), "cumulative_difficulty": U(T_U64, kum & _M),
            "cumulative_difficulty_top64": U(T_U64, kum >> 64), "top_id": U(T_STR, top_id),
            "top_version": U(T_U8, version), "pruning_seed": U(T_U32, 0)}


def utc(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def utc_ms(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


# ------------------------------------------------------------------ lauscher
class Lauscher:
    def __init__(self, dauer_s):
        self.dauer_s = dauer_s
        self.lock = threading.Lock()
        self.adressen = []          # nur im speicher
        self.versucht = set()
        self.peers = {}             # name -> zustand
        self.bloecke = {}           # hash -> dict
        self.ankuendigungen = []    # (hash, peer, ms)
        self.tx_ankuendigungen = 0
        self.spitze = None          # (hoehe, top_id bytes, version, kum)
        self.gruende = {}
        self.n = 0
        self.sockets = []
        self.ende = time.time() + dauer_s

    def grund(self, g):
        with self.lock:
            self.gruende[g] = self.gruende.get(g, 0) + 1

    def seeds(self):
        txt = urllib.request.urlopen(QUELLE, timeout=30).read().decode()
        a = txt.find("get_ip_seed_nodes")
        t = txt[a:]
        t = t[t.find("TESTNET"):]
        t = t[:t.find("else")]
        return [(h, int(p)) for h, p in re.findall(r'"([0-9.]+):(\d+)"', t)]

    def peer(self, adr):
        with self.lock:
            self.n += 1
            name = f"peer_{self.n}"
            modus = "sync" if self.n % 2 else "spitze"
            self.peers[name] = {"peer": name, "modus": modus, "stressnet": None, "top_version": None,
                                "gemeldete_hoehe": None, "verbunden_utc": None, "getrennt_utc": None,
                                "getrennt_grund": None, "fluffy": 0, "tx_hash_nachrichten": 0, "timed_sync": 0}
        return name

    def senden(self, s, daten):
        s.sendall(daten)

    def lauf(self, adr):
        name = self.peer(adr)
        z = self.peers[name]
        s = None
        try:
            s = socket.create_connection(adr, timeout=10)
            s.settimeout(90)
            with self.lock:
                self.sockets.append(s)
            with self.lock:
                sp = self.spitze
            if z["modus"] == "spitze" and sp:
                sync = sync_daten(*sp)
            else:
                z["modus"] = "sync"
                sync = sync_daten(1, bytes.fromhex(TESTNET_GENESIS), 1, 1)
            hs = epee_schreiben({"node_data": {"network_id": U(T_STR, NETWORK_ID), "peer_id": U(T_U64, random.getrandbits(64)),
                                               "my_port": U(T_U32, 0), "support_flags": U(T_U32, SUPPORT_FLAGS)},
                                 "payload_data": sync})
            self.senden(s, levin(HS, hs, True, ANFRAGE))
            while time.time() < self.ende:
                kopf = lesen_genau(s, 33)
                sig, n, will, cmd, rc, flags, _pv = struct.unpack("<QQ?IiII", kopf)
                if sig != LEVIN_SIG or n > 50_000_000:
                    raise ConnectionError("levin-rahmen ungueltig")
                nl = lesen_genau(s, n)
                jetzt = time.time()
                if cmd == HS and flags == ANTWORT:
                    d = epee_lesen(nl)
                    pd = d.get("payload_data", {})
                    z["top_version"] = pd.get("top_version")
                    z["gemeldete_hoehe"] = pd.get("current_height")
                    z["stressnet"] = bool((pd.get("top_version") or 0) >= HF_FCMP and (pd.get("current_height") or 0) > ABZWEIG)
                    z["verbunden_utc"] = utc(jetzt)
                    for e in d.get("local_peerlist_new", []) or []:
                        ad = e.get("adr", {})
                        if ad.get("type") == 1 and "addr" in ad:
                            ip = socket.inet_ntoa(struct.pack("<I", ad["addr"]["m_ip"]))
                            with self.lock:
                                self.adressen.append((ip, ad["addr"]["m_port"]))
                    if not z["stressnet"]:
                        raise ConnectionAbortedError("kein stressnet")
                    with self.lock:
                        kum = pd.get("cumulative_difficulty", 0) | (pd.get("cumulative_difficulty_top64", 0) << 64)
                        if not self.spitze or pd["current_height"] > self.spitze[0]:
                            self.spitze = (pd["current_height"], pd["top_id"], pd["top_version"], kum)
                elif cmd == TIMED_SYNC and will:
                    z["timed_sync"] += 1
                    d = epee_lesen(nl).get("payload_data", {})
                    if d.get("current_height"):
                        z["gemeldete_hoehe"] = d["current_height"]
                    with self.lock:
                        sp = self.spitze
                    eigen = sync_daten(*sp) if (z["modus"] == "spitze" and sp) else \
                        sync_daten(1, bytes.fromhex(TESTNET_GENESIS), 1, 1)
                    self.senden(s, levin(TIMED_SYNC, epee_schreiben({"payload_data": eigen}), False, ANTWORT, 1))
                elif cmd == SUPPORT and will:
                    self.senden(s, levin(SUPPORT, epee_schreiben({"support_flags": U(T_U32, SUPPORT_FLAGS)}),
                                         False, ANTWORT, 1))
                elif cmd == PING and will:
                    self.senden(s, levin(PING, epee_schreiben({"status": U(T_STR, b"OK"),
                                                               "peer_id": U(T_U64, 0)}), False, ANTWORT, 1))
                elif cmd == FLUFFY:
                    z["fluffy"] += 1
                    d = epee_lesen(nl)
                    self.block(d["b"]["block"], name, jetzt)
                elif cmd == TX_HASH:
                    z["tx_hash_nachrichten"] += 1
                    with self.lock:
                        self.tx_ankuendigungen += len(epee_lesen(nl).get("t", b"")) // 32
        except ConnectionAbortedError as e:
            z["getrennt_grund"] = str(e)
        except (OSError, ConnectionError) as e:
            z["getrennt_grund"] = type(e).__name__ if not isinstance(e, ConnectionError) else str(e)
        except Unbekannt as e:
            z["getrennt_grund"] = "format: " + str(e)[:60]
        except Exception as e:                       # noqa: BLE001, nur der Typ, nie die Meldung
            z["getrennt_grund"] = "fehler: " + type(e).__name__
        finally:
            if time.time() >= self.ende - 1:          # wir haben am Ende selbst getrennt
                z["getrennt_grund"] = None
            z["getrennt_utc"] = utc(time.time())
            if s:
                s.close()
            self.grund(z["getrennt_grund"] or "ende")

    def block(self, blob, name, jetzt):
        try:
            k = block_lesen(blob)
        except (Unbekannt, IndexError) as e:
            with self.lock:
                self.gruende["block nicht lesbar: " + str(e)[:60]] = self.gruende.get("block nicht lesbar: " + str(e)[:60], 0) + 1
            return
        with self.lock:
            if k["hash"] not in self.bloecke:
                k["first_seen_ms"] = int(jetzt * 1000)
                self.bloecke[k["hash"]] = k
                if self.spitze and k["hoehe"] + 1 > self.spitze[0]:
                    sp = self.spitze
                    self.spitze = (k["hoehe"] + 1, bytes.fromhex(k["hash"]), k["major"], sp[3])
            self.ankuendigungen.append((k["hash"], name, int(jetzt * 1000)))

    def start(self):
        for a in self.seeds():
            self.adressen.append(a)
        threads = []
        while time.time() < self.ende - 30:
            with self.lock:
                aktiv = sum(1 for t in threads if t.is_alive())
                neu = [a for a in self.adressen if a not in self.versucht]
            for a in neu[:max(0, MAX_PEERS - aktiv)]:
                self.versucht.add(a)
                t = threading.Thread(target=self.lauf, args=(a,), daemon=True)
                t.start()
                threads.append(t)
            time.sleep(NACHFASSEN_S if aktiv >= MAX_PEERS else 5)
        with self.lock:
            self.ende = time.time()
            for s in self.sockets:
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        for t in threads:
            t.join(timeout=10)


def schreiben(l, aus, start):
    os.makedirs(aus, exist_ok=True)
    with l.lock:                                     # Threads koennen noch laufen
        l.bloecke = dict(l.bloecke)
        l.ankuendigungen = list(l.ankuendigungen)
        l.peers = {k: dict(v) for k, v in l.peers.items()}
        l.gruende = dict(l.gruende)
    bl = sorted(l.bloecke.values(), key=lambda k: (k["hoehe"] or 0))
    nach_hash = {k["hash"]: k for k in bl}
    verkettet = sum(1 for k in bl if k["prev"] in nach_hash)
    with open(os.path.join(aus, "bloecke.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hoehe", "hash", "prev_hash", "header_zeit_utc", "major", "minor", "n_tx", "first_seen_utc",
                    "peers_n", "spread_ms", "prev_ist_unser_hash"])
        for k in bl:
            ms = [m for h, _, m in l.ankuendigungen if h == k["hash"]]
            peers = {p for h, p, _ in l.ankuendigungen if h == k["hash"]}
            w.writerow([k["hoehe"], k["hash"], k["prev"], utc(k["zeit"]), k["major"], k["minor"], k["n_tx"],
                        utc_ms(k["first_seen_ms"] / 1000), len(peers), max(ms) - min(ms),
                        "ja" if k["prev"] in nach_hash else "unbekannt"])
    with open(os.path.join(aus, "ankuendigungen.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hash", "peer", "ankunft_utc"])
        for h, p, m in sorted(l.ankuendigungen, key=lambda x: x[2]):
            w.writerow([h, p, utc_ms(m / 1000)])
    with open(os.path.join(aus, "peers.json"), "w") as f:
        json.dump(sorted(l.peers.values(), key=lambda z: int(z["peer"][5:])), f, indent=1)
    peers = list(l.peers.values())
    sn = [z for z in peers if z["stressnet"]]
    meta = {
        "skript": "scripts/monero/stressnet_lauscher.py", "tag": TAG, "start_utc": utc(start), "ende_utc": utc(time.time()),
        "dauer_min": round((time.time() - start) / 60, 1),
        "peers_versucht": len(peers), "peers_verbunden": sum(1 for z in peers if z["verbunden_utc"]),
        "peers_stressnet": len(sn), "peers_kein_stressnet": sum(1 for z in peers if z["stressnet"] is False),
        "stressnet_modus": {m: {"peers": sum(1 for z in sn if z["modus"] == m),
                                "mit_fluffy_block": sum(1 for z in sn if z["modus"] == m and z["fluffy"]),
                                "bis_ende_verbunden": sum(1 for z in sn if z["modus"] == m and z["getrennt_grund"] is None),
                                "timed_sync": sum(z["timed_sync"] for z in sn if z["modus"] == m)}
                            for m in ("sync", "spitze")},
        "bloecke": len(bl), "bloecke_hash_bestaetigt_durch_nachfolger": verkettet,
        "hoehen": [bl[0]["hoehe"], bl[-1]["hoehe"]] if bl else None,
        "tx_hash_ankuendigungen": l.tx_ankuendigungen,
        "trennungen": l.gruende,
        "hinweis": "ein zuhoerer an einem ort, arbeitsnachweis nicht geprueft; keine adressen in den dateien",
    }
    with open(os.path.join(aus, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    return meta


# ------------------------------------------------------------------ selbsttest
def selbsttest():
    fehler = []

    def ok(name, bed, info=""):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, "" if bed else "  " + str(info)))
        if not bed:
            fehler.append(name)
    ok("keccak leer", keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470")
    ok("keccak abc", keccak256(b"abc").hex() == "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45")
    ok("keccak 135 byte (0x81)", keccak256(b"a" * 135).hex() ==
       "34367dc248bbd832f4e3e69dfaac2f92638bd0bbd18f2912ba4ef454919cf446")
    ok("miner-tx genesis", tx_lesen(bytes.fromhex(GENESIS_TX), 0)[1].hex() ==
       "c88ce9783b4f11190d7b9c17a69c1c52200f9faaee8e98dd07e6811175177139")
    ok("genesis testnet", genesis_hash(GENESIS_TX, 10001) == TESTNET_GENESIS, genesis_hash(GENESIS_TX, 10001))
    ok("genesis mainnet", genesis_hash(GENESIS_TX, 10000) ==
       "418015bb9ae982a1975da7d79277c2705727a56894ba0fb246adaabb1f4632e3", genesis_hash(GENESIS_TX, 10000))
    hs = [keccak256(bytes([i])) for i in range(5)]
    ok("tree hash 3", tree_hash(hs[:3]) == keccak256(hs[0] + keccak256(hs[1] + hs[2])))
    ok("tree hash 4", tree_hash(hs[:4]) == keccak256(keccak256(hs[0] + hs[1]) + keccak256(hs[2] + hs[3])))
    d = {"a": U(T_U64, 2 ** 40), "b": U(T_STR, b"\x00" * 16), "c": {"d": U(T_U8, 7), "e": U(T_BOOL, True)}}
    r = epee_lesen(epee_schreiben(d))
    ok("epee hin und zurueck", r == {"a": 2 ** 40, "b": b"\x00" * 16, "c": {"d": 7, "e": True}}, r)
    for v in (0, 63, 64, 16383, 16384, 2 ** 30 - 1, 2 ** 30):
        ok(f"epee varint {v}", e_varint_lesen(e_varint(v), 0)[0] == v)
    arr = SIG + e_varint(1) + b"\x01t" + bytes([T_STR | FLAG_ARR]) + e_varint(2) + e_varint(2) + b"xy" + e_varint(1) + b"z"
    ok("epee feld als liste", epee_lesen(arr) == {"t": [b"xy", b"z"]})
    k = levin(HS, b"abc", True, ANFRAGE)
    ok("levin kopf 33 byte", len(k) == 36 and struct.unpack("<QQ?IiII", k[:33])[3] == HS)
    # Block mit Fork 17: Kopf, Miner-Tx v2 mit Carrot-Ausgang, rct null, 2 Tx-Hashes, FCMP-Felder
    tx = (varint_bytes(2) + varint_bytes(60) + varint_bytes(1) + b"\xff" + varint_bytes(3102900) + varint_bytes(1)
          + varint_bytes(600000000000) + b"\x01" + b"\x11" * 51 + varint_bytes(2) + b"\x01\x02" + b"\x00")
    kopf = varint_bytes(18) + varint_bytes(18) + varint_bytes(1794000000) + b"\x22" * 32 + struct.pack("<I", 5)
    blob = kopf + tx + varint_bytes(2) + b"\x33" * 64 + b"\x07" + b"\x44" * 32
    k = block_lesen(blob)
    mh = keccak256(keccak256(tx[:-1]) + keccak256(b"\x00") + b"\x00" * 32)
    hb = kopf + tree_hash([mh, b"\x07" + b"\x00" * 31, b"\x44" * 32, b"\x33" * 32, b"\x33" * 32]) + varint_bytes(3)
    soll = keccak256(varint_bytes(len(hb)) + hb)
    ok("block fork 17 gelesen", k["hoehe"] == 3102900 and k["n_tx"] == 2 and k["major"] == 18, k)
    ok("block fork 17 hash", k["hash"] == soll.hex())
    try:
        block_lesen(blob + b"\x00")
        ok("ueberschuss erkannt", False)
    except Unbekannt:
        ok("ueberschuss erkannt", True)
    print("")
    print("%d fehler" % len(fehler) if fehler else "alle testfaelle bestanden")
    return 1 if fehler else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--dauer", type=float, default=15, help="minuten")
    ap.add_argument("--aus")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    if not a.probe or not a.aus:
        ap.error("nur --probe mit --aus, der dauerlauf kommt nach bens ja")
    start = time.time()
    l = Lauscher(a.dauer * 60)
    l.start()
    meta = schreiben(l, a.aus, start)
    print(json.dumps({k: meta[k] for k in ("peers_versucht", "peers_stressnet", "bloecke",
                                           "bloecke_hash_bestaetigt_durch_nachfolger", "stressnet_modus")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
