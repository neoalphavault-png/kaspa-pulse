#!/usr/bin/env python3
"""chipnet_koepfe.py - holt Blockkoepfe des BCH-Chipnets direkt aus dem P2P-Netz.

Ben, 26.10.2026: chipnet und XO. Ab dem Lock-in am 15.11.2026 wird chipnet
der Ort der 1-Minuten-Bloecke (BCHN chainparams: upgrade2027ActivationTime
1794744000). Dieses Skript ist tempnet_koepfe.py fuer chipnet:
- Peers aus BCHN src/chainparams.cpp, Klasse CChipNetParams (vSeeds), zur
  Laufzeit gelesen, nie ausgegeben.
- Start beim hoechsten BCHN-Checkpoint fuer chipnet unter --ab; alle
  spaeteren BCHN-Checkpoints muessen passen.
- Chipnet und Tempnet teilen Magic und Port. Ein Peer zaehlt nur, wenn er nach
  dem letzten gemeinsamen Block 327.988 NICHT den Tempnet-Block 327.989
  liefert (Umkehrung der Tempnet-Pruefung vom 21.10.2026).

Urspruenglicher Kopf von tempnet_koepfe.py:

tempnet_koepfe.py - holt Blockkoepfe des BCH-Tempnets direkt aus dem P2P-Netz.

Wozu: unabhaengige Zaehlung des BCH Tempnet 2027 (CHIP-2025-03 Faster Blocks,
1-Minuten-Bloecke), aktiv ab MTP 1792065600 (2026-10-15 12:00 UTC). Wir
brauchen Hoehe, Hash, Zeitstempel und nBits jedes Blocks seit dem Abzweig von
Chipnet. Kein Explorer als Quelle, kein Konto: wir fragen Tempnet-Knoten mit
getheaders/headers. chaingraph dient nur als Gegenprobe (bch_gegenprobe.py).

Netzdaten (oeffentlich, Repo 9500/bchn-tempnet, TEMPNET.md und
src/chainparams.cpp, Stand 18.10.2026): Magic und Port wie Chipnet,
letzter gemeinsamer Block 327.988, erster Tempnet-Block 327.989.
Die Peer-Adressen stehen NICHT in diesem Repo. Das Skript liest sie zur
Laufzeit aus dieser oeffentlichen Konfiguration (addnode-Zeilen und vSeeds)
und gibt sie nirgends aus.

Ablauf wie beim Zcash-Abrufer (scripts/zcash/testnet_koepfe.py):
  1. Peers aus der oeffentlichen Konfiguration.
  2. Start beim letzten gemeinsamen Block 327.988; der erste Kopf danach muss
     der Tempnet-Block 327.989 sein, sonst steht der Peer auf Chipnet.
  3. getheaders mit Locator, je Antwort bis 2.000 Koepfe.
  4. Jeder Kopf: prev-Hash = Hash des Vorgaengers, Hash <= Ziel aus nBits.
  5. Gegenprobe mit weiteren synchronen Peers.

IPs und Hostnamen von Peers stehen in keiner Ausgabe und in keinem Log.

  python3 scripts/bch/chipnet_koepfe.py --aus chipnet-koepfe.csv.gz --meta chipnet-koepfe-meta.json
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import random
import socket
import struct
import sys
import time
import urllib.request
from datetime import datetime, timezone

MAGIC = bytes.fromhex("e2b7daaf")  # Chipnet und Tempnet
PORT = 48333
# Oeffentliche Konfiguration des Tempnets; daraus kommen die Peers (zur Laufzeit).
BCHN_CHAINPARAMS = os.environ.get(
    "BCH_CHAINPARAMS", "https://gitlab.com/bitcoin-cash-node/bitcoin-cash-node/-/raw/master/src/chainparams.cpp")
# Die Version, die Zebra 7.0.0-rc.0 selbst meldet (Lauf 1, 15.10.2026).
PROTOKOLL = int(os.environ.get("BCH_PROTOKOLL", "70016"))
USER_AGENT = b"/kaspa-pulse-zaehler:0.1/"
LETZTER_GEMEINSAMER = (327_988, "00000000000002bcc82b979f71d827d7788c84b981975101cb9e415ace23c46c")
ERSTER_TEMPNET = (327_989, "00000000e18af2c66d44a1bbfe165acc4b87a625d211a09e33d5ee61d35dcb66")
START_UNTER = 325_000  # Kennzahlen ab 01.10.2026; der Checkpoint davor ist 313.653


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def sha256d(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def varint(n):
    if n < 0xFD:
        return bytes([n])
    if n <= 0xFFFF:
        return b"\xfd" + struct.pack("<H", n)
    if n <= 0xFFFFFFFF:
        return b"\xfe" + struct.pack("<I", n)
    return b"\xff" + struct.pack("<Q", n)


def lies_varint(b, i):
    v = b[i]
    if v < 0xFD:
        return v, i + 1
    if v == 0xFD:
        return struct.unpack_from("<H", b, i + 1)[0], i + 3
    if v == 0xFE:
        return struct.unpack_from("<I", b, i + 1)[0], i + 5
    return struct.unpack_from("<Q", b, i + 1)[0], i + 9


def ziel_aus_nbits(bits):
    exp = bits >> 24
    mant = bits & 0x007FFFFF
    return mant >> (8 * (3 - exp)) if exp <= 3 else mant << (8 * (exp - 3))


class Peer:
    def __init__(self, addr, timeout=12):
        fam = socket.AF_INET6 if ":" in addr[0] else socket.AF_INET
        self.s = socket.socket(fam, socket.SOCK_STREAM)
        self.s.settimeout(timeout)
        self.s.connect(addr)
        self.puffer = b""
        self.agent = "?"
        self.version = 0
        self.hoehe = 0
        self.gesehen = []  # Befehle in Reihenfolge, fuer die Diagnose

    def senden(self, cmd, payload=b""):
        kopf = MAGIC + cmd.encode().ljust(12, b"\0") + struct.pack("<I", len(payload)) + sha256d(payload)[:4]
        self.s.sendall(kopf + payload)

    def _lesen(self, n):
        while len(self.puffer) < n:
            d = self.s.recv(1 << 16)
            if not d:
                raise ConnectionError("peer hat getrennt")
            self.puffer += d
        out, self.puffer = self.puffer[:n], self.puffer[n:]
        return out

    def empfangen(self):
        kopf = self._lesen(24)
        if kopf[:4] != MAGIC:
            raise ConnectionError("falsches netz-magic")
        cmd = kopf[4:16].rstrip(b"\0").decode(errors="replace")
        laenge = struct.unpack("<I", kopf[16:20])[0]
        if laenge > 8 << 20:
            raise ConnectionError("nachricht zu gross")
        payload = self._lesen(laenge)
        self.gesehen.append(cmd)
        if sha256d(payload)[:4] != kopf[20:24]:
            raise ConnectionError("pruefsumme falsch")
        if cmd == "ping":
            self.senden("pong", payload)
        return cmd, payload

    def handschlag(self):
        leer_addr = struct.pack("<Q", 0) + b"\0" * 10 + b"\xff\xff" + b"\0" * 4 + struct.pack(">H", 0)
        payload = (
            struct.pack("<iQq", PROTOKOLL, 0, int(time.time()))
            + leer_addr + leer_addr
            + struct.pack("<Q", random.getrandbits(64))
            + varint(len(USER_AGENT)) + USER_AGENT
            + struct.pack("<i", 0) + b"\0"
        )
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
                i += n
                self.hoehe = struct.unpack_from("<i", p, i)[0]
                self.senden("verack")
                hat_version = True
            elif cmd == "verack":
                hat_verack = True
            elif cmd == "reject":
                raise ConnectionError("version abgelehnt")

    def koepfe(self, locator, warten=60):
        """getheaders mit einem Locator (Liste von Hashes, neueste zuerst, oder
        ein einzelner Hash); liefert Liste roher Koepfe (ohne tx-count).

        Lauf des Zuhoerers 17.10.2026: mit nur EINEM Hash im Locator findet ein
        Peer auf einem anderen Zweig keinen Anschluss; er antwortet mit Koepfen
        von woanders, die wir verwerfen, bis zur Zeitueberschreitung. Mit einem
        Locator wie bei echten Knoten findet er den gemeinsamen Vorfahren.
        """
        if isinstance(locator, bytes):
            locator = [locator]
        bekannt = set(locator)
        payload = struct.pack("<I", PROTOKOLL) + varint(len(locator)) + b"".join(locator) + b"\0" * 32
        self.senden("getheaders", payload)
        frist = time.time() + warten
        while time.time() < frist:
            cmd, p = self.empfangen()
            if cmd != "headers":
                continue
            n, i = lies_varint(p, 0)
            out = []
            for _ in range(n):
                start = i
                i += 80
                out.append(p[start:i])
                _, i = lies_varint(p, i)  # tx-count, immer 0
            # Ein unverlangter headers (Ankuendigung eines neuen Blocks) haengt
            # nicht an unserem Locator; den ueberlesen wir.
            if out and out[0][4:36] not in bekannt:
                continue
            return out
        raise TimeoutError("keine headers-antwort")

    def zu(self):
        try:
            self.s.close()
        except OSError:
            pass


def kopf_lesen(raw):
    version, = struct.unpack_from("<i", raw, 0)
    prev = raw[4:36]
    zeit, bits = struct.unpack_from("<II", raw, 68)
    h = sha256d(raw)
    return {"version": version, "prev": prev, "zeit": zeit, "bits": bits, "hash": h}


_CP_CACHE = {}


def _chipnet_teil():
    if "teil" not in _CP_CACHE:
        with urllib.request.urlopen(BCHN_CHAINPARAMS, timeout=60) as r:
            quelle = r.read().decode()
        teil = quelle[quelle.index("class CChipNetParams"):]
        _CP_CACHE["teil"] = teil[:teil.index("\n};")]
    return _CP_CACHE["teil"]


def peers_finden():
    """Peers aus den vSeeds von CChipNetParams in BCHN src/chainparams.cpp.
    Nichts davon wird geloggt oder gespeichert, nur die Anzahl."""
    import re
    gesehen, seeds = set(), []
    try:
        seeds = re.findall(r'vSeeds\.emplace_back\("([^"]+)"\)', _chipnet_teil())
    except (OSError, ValueError) as e:
        log(f"chainparams.cpp nicht lesbar ({type(e).__name__})")
    for seed in seeds:
        try:
            for fam, _, _, _, sa in socket.getaddrinfo(seed, PORT, proto=socket.IPPROTO_TCP):
                gesehen.add((sa[0], sa[1]))
        except OSError as e:
            log(f"ein seed nicht aufloesbar ({type(e).__name__})")
    liste = list(gesehen)
    random.shuffle(liste)
    log(f"{len(liste)} peer-adressen aus {len(seeds)} chipnet-seeds")
    return liste


def checkpoints_laden():
    """BCHN-Checkpoints fuer chipnet (Hoehe -> Hash)."""
    import re
    cps = {int(h): x for h, x in re.findall(r'\{(\d+),\s*BlockHash::fromHex\("([0-9a-f]{64})"\)\}', _chipnet_teil())}
    log(f"{len(cps)} bchn-checkpoints fuer chipnet, hoechster {max(cps)}")
    return cps


def verbinden(adressen, ausschluss=(), mindesthoehe=0):
    """Erster erreichbarer Peer, der mindestens bis mindesthoehe synchron ist.

    Lauf 2 (15.10.2026): Peers, die selbst noch synchronisieren (gemeldete
    Hoehe 3,1 Mio.), kennen unseren Locator nicht und antworten nie.
    """
    for addr in adressen:
        if addr in ausschluss:
            continue
        try:
            p = Peer(addr)
            p.handschlag()
            log(f"peer verbunden: agent {p.agent}, version {p.version}, meldet hoehe {p.hoehe}")
            if p.hoehe < mindesthoehe:
                log(f"peer liegt zurueck (unter {mindesthoehe}), naechster")
                p.zu()
                if isinstance(ausschluss, set):
                    ausschluss.add(addr)
                continue
            return addr, p
        except (OSError, ConnectionError, TimeoutError, struct.error, IndexError) as e:
            log(f"peer abgelehnt ({type(e).__name__}: {str(e)[:60] if not isinstance(e, OSError) else ''})")
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ab", type=int, default=START_UNTER, help="Start beim hoechsten Checkpoint darunter")
    ap.add_argument("--aus", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--gegenproben", type=int, default=2)
    args = ap.parse_args()

    cps = checkpoints_laden()
    start_h = max(h for h in cps if h <= args.ab)
    start_hash = bytes.fromhex(cps[start_h])[::-1]
    gemeinsam_hash = bytes.fromhex(LETZTER_GEMEINSAMER[1])[::-1]
    log(f"start bei checkpoint {start_h}")

    adressen = peers_finden()
    if not adressen:
        sys.exit("keine peers")

    kette = []  # (hoehe, kopf)
    benutzt, agents = set(), []

    def letzter():
        return (kette[-1][0], kette[-1][1]["hash"]) if kette else (start_h, start_hash)

    def locator():
        # neueste zuerst: 10 einzeln, dann in wachsenden Schritten, zuletzt der Checkpoint
        out, i, schritt = [], len(kette) - 1, 1
        while i >= 0:
            out.append(kette[i][1]["hash"])
            if len(out) >= 10:
                schritt *= 2
            i -= schritt
        return out + [start_hash]

    # Zielhoehe: hoechste Hoehe, die mehrere Peers melden. Ein Peer, der weit
    # darunter liegt, synchronisiert noch oder steht auf einem anderen Zweig
    # (Lauf 17.10.2026: /Zakura:1.5.1/ meldete 4.482.036, die Spitze war 4.511.578).
    # Ben, 21.10.2026: die Zielhoehe zaehlt nur von Peers, die den Abzweig
    # bestaetigen. Am 21.10. standen drei von vier Proben auf Chipnet, und die
    # Zielhoehe kam von dort. Probe: getheaders ab dem letzten gemeinsamen
    # Block; der erste Kopf der Antwort muss der Tempnet-Block 327.989 sein.
    gemeldet, abgelehnt_chipnet, versuche = [], 0, 0
    erster_hash = bytes.fromhex(ERSTER_TEMPNET[1])[::-1]
    while len(gemeldet) < 4 and versuche < 20:
        versuche += 1
        a, p = verbinden(adressen, benutzt, mindesthoehe=ERSTER_TEMPNET[0])
        if p is None:
            break
        benutzt.add(a)
        try:
            probe = p.koepfe([gemeinsam_hash], warten=20)
            if probe and sha256d(probe[0]) != erster_hash:
                gemeldet.append(p.hoehe)
            else:
                abgelehnt_chipnet += 1
                log(f"probe {p.agent}: liefert den tempnet-block {ERSTER_TEMPNET[0]} oder nichts, zaehlt nicht")
        except (OSError, ConnectionError, TimeoutError) as e:
            log(f"probe {p.agent} ohne antwort ({type(e).__name__})")
        p.zu()
    if not gemeldet:
        sys.exit("kein chipnet-peer gefunden")
    ziel = sorted(gemeldet)[-2] if len(gemeldet) >= 2 else gemeldet[0]
    mindest = ziel - 20
    log(f"zielhoehe {ziel} aus {len(gemeldet)} chipnet-peers "
        f"({abgelehnt_chipnet} ohne), hauptpeer ab {mindest}")
    benutzt = set()

    abzweige = []  # verworfene Koepfe, wenn ein Peer auf einem anderen Zweig stand
    addr, peer = verbinden(adressen, benutzt, mindesthoehe=mindest)
    fehler = 0

    def wechseln(grund):
        nonlocal addr, peer, fehler
        log(f"peer {grund}, wechsle")
        peer.zu()
        benutzt.add(addr)
        fehler += 1
        addr, peer = (None, None) if fehler > 12 else verbinden(adressen, benutzt, mindesthoehe=mindest)

    while True:
        if peer is None:
            # Keine Peers mehr. Liegt der Stand nahe am Ziel, ist das die Spitze,
            # die wir kriegen; sonst lieber keine Datei als eine kurze.
            if letzter()[0] >= mindest:
                log(f"WARNUNG: keine peers mehr, ende bei {letzter()[0]} (ziel {ziel})")
                break
            sys.exit("kein peer mehr erreichbar oder zu viele peer-fehler")
        try:
            roh = peer.koepfe(locator())
        except (OSError, ConnectionError, TimeoutError) as e:
            wechseln(f"abgebrochen ({type(e).__name__}: {e}), empfangen: {peer.gesehen[-12:]}")
            continue
        if peer.agent not in agents:
            agents.append(peer.agent)
        if not roh:
            if letzter()[0] < ziel - 3:
                wechseln(f"liefert nichts mehr bei {letzter()[0]}, ziel {ziel}")
                continue
            break
        # Anschluss suchen: der erste Kopf haengt an einem Hash unseres Locators.
        prev = roh[0][4:36]
        if prev != letzter()[1]:
            if prev == start_hash:
                pos = 0
            else:
                pos = next((i + 1 for i in range(len(kette) - 1, -1, -1) if kette[i][1]["hash"] == prev), None)
                if pos is None:
                    wechseln("antwortet ohne anschluss")
                    continue
            weg = kette[pos:]
            abzweige.append({"verworfen": [(h, k["hash"]) for h, k in weg], "neuer_peer": peer.agent})
            log(f"anderer zweig: {len(weg)} koepfe ab hoehe {weg[0][0] if weg else '-'} neu holen")
            del kette[pos:]
        letzte_h, letzter_hash = letzter()
        vorher = len(kette)
        falscher_zweig = False
        for r in roh:
            k = kopf_lesen(r)
            if k["prev"] != letzter_hash:
                sys.exit(f"kette bricht bei hoehe {letzte_h + 1}: prev passt nicht")
            if int.from_bytes(k["hash"], "little") > ziel_aus_nbits(k["bits"]):
                sys.exit(f"arbeitsnachweis fehlt bei hoehe {letzte_h + 1}")
            letzte_h += 1
            letzter_hash = k["hash"]
            if (letzte_h in cps and cps[letzte_h] != k["hash"][::-1].hex()) or \
                    (letzte_h == ERSTER_TEMPNET[0] and k["hash"][::-1].hex() == ERSTER_TEMPNET[1]):
                # Ein Tempnet-Knoten liefert bei 327.989 den Tempnet-Block.
                # Stapel verwerfen, Peer wechseln, kein Abbruch.
                falscher_zweig = True
                break
            kette.append((letzte_h, k))
        if falscher_zweig:
            del kette[vorher:]
            wechseln(f"steht nicht auf chipnet (fixpunkt {letzte_h})")
            continue
        if len(kette) % 8000 < len(roh):
            log(f"... hoehe {letzte_h}")
    letzte_h, letzter_hash = letzter()
    if peer is not None:
        peer.zu()
    # Echter Abzweig: erste Hoehe, an der ein verworfener Kopf nicht dem
    # endgueltigen entspricht (verworfen wird ab dem Locator-Raster, also oft
    # mehr als der Zweig selbst).
    endg = {h: k["hash"] for h, k in kette}
    zweige = []
    for a in abzweige:
        anders = [h for h, x in a["verworfen"] if endg.get(h) != x]
        zweige.append({"abzweig_hoehe": anders[0] if anders else None,
                       "bloecke_auf_anderem_zweig": len(anders), "danach_von": a["neuer_peer"]})
    abzweige = zweige
    abruf = datetime.now(timezone.utc)
    log(f"spitze {letzte_h}, {len(kette)} koepfe")
    if letzte_h < args.ab:
        sys.exit("kette endet vor dem start")

    # Gegenprobe: andere Peers, ab 500 Bloecke vor der Spitze. Nur Peers nahe
    # der Spitze; wir suchen weiter, bis --gegenproben gelungen sind, und
    # nehmen einen Peer anderer Software (Zakura) mit, wenn einer erreichbar ist.
    nach_h = {h: k["hash"] for h, k in kette}
    gp_h = max(start_h, letzte_h - 500)
    gp_hash = nach_h.get(gp_h, start_hash)
    proben, fehlversuche = [], []
    benutzt.add(addr)
    versuche = 0
    # Lauf 4 (15.10.2026) hing ueber 20 min in der Suche nach Zakura-Peers, die
    # auf getheaders nicht antworten. Deshalb ein festes Zeitbudget.
    budget_ende = time.time() + 360
    while len(proben) < args.gegenproben + 1 and versuche < 25 and time.time() < budget_ende:
        versuche += 1
        a2, p2 = verbinden(adressen, benutzt, mindesthoehe=letzte_h - 50)
        if p2 is None:
            break
        benutzt.add(a2)
        if p2.hoehe > ziel + 100:
            # Tempnet-Knoten (gleiches Magic, viel hoehere Kette) taugen nicht als Gegenprobe
            p2.zu()
            continue
        software = {g["agent"].split(":")[0] for g in proben}
        if len(proben) >= args.gegenproben and p2.agent.split(":")[0] in software | {peer.agent.split(":")[0]}:
            p2.zu()
            continue  # genug Proben dieser Software, wir suchen nur noch eine andere
        try:
            roh = []
            h_hash = gp_hash
            for _ in range(5):
                stueck = p2.koepfe(h_hash, warten=20)
                if not stueck:
                    break
                roh += stueck
                h_hash = sha256d(stueck[-1])
            gleich = sum(1 for i, r in enumerate(roh) if nach_h.get(gp_h + 1 + i) == sha256d(r))
            ueberlapp = sum(1 for i in range(len(roh)) if gp_h + 1 + i in nach_h)
            proben.append({"agent": p2.agent, "verglichen": ueberlapp, "gleich": gleich,
                           "spitze_peer": gp_h + len(roh)})
            log(f"gegenprobe {p2.agent}: {gleich}/{ueberlapp} gleich, spitze peer {gp_h + len(roh)}")
        except (OSError, ConnectionError, TimeoutError) as e:
            log(f"gegenprobe abgebrochen ({type(e).__name__})")
            fehlversuche.append({"agent": p2.agent, "fehler": type(e).__name__})
        p2.zu()
        if p2.agent not in agents:
            agents.append(p2.agent)
    abweichend = [g for g in proben if g["gleich"] < g["verglichen"]]
    if abweichend:
        log(f"WARNUNG: {len(abweichend)} gegenproben weichen ab")

    os.makedirs(os.path.dirname(args.aus) or ".", exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["hoehe", "hash", "zeit", "nbits", "version"])
    for h, k in kette:
        w.writerow([h, k["hash"][::-1].hex(), k["zeit"], f"{k['bits']:08x}", k["version"]])
    # mtime=0: dieselben Koepfe ergeben dieselbe Datei.
    with open(args.aus, "wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as g:
            g.write(buf.getvalue().encode())
    meta = {
        "quelle": "BCH-Chipnet P2P (getheaders), Peers aus BCHN chainparams (CChipNetParams)",
        "abruf_utc": abruf.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "start_checkpoint": start_h,
        "erste_hoehe": kette[0][0],
        "spitze_hoehe": letzte_h,
        "spitze_hash": letzter_hash[::-1].hex(),
        "fixpunkte": {"bchn_checkpoints": sorted(h for h in cps if h >= start_h),
                      "nicht_tempnet_bei": ERSTER_TEMPNET[0]},
        "checkpoints_geprueft": sum(1 for h, _ in kette if h in cps),
        "peer_software": agents,
        "peer_fehler": fehler,
        "zielhoehe_gemeldet": ziel,
        "zielhoehe_aus_chipnet_peers": len(gemeldet),
        "proben_tempnet_oder_ohne_antwort": abgelehnt_chipnet,
        "abzweige_verworfen": abzweige,
        "gegenproben": proben,
        "gegenproben_ohne_antwort": fehlversuche,
        "pruefungen": ["prev-hash-kette", "hash <= ziel aus nbits", "bchn-checkpoints chipnet", "nicht der tempnet-block bei 327989"],
        "nicht_geprueft": ["block-inhalt", "asert-schwierigkeitsregel", "konsensregeln jenseits des kopfes"],
    }
    with open(args.meta, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"spitze": letzte_h, "start": start_h, "abruf": meta["abruf_utc"]}))


if __name__ == "__main__":
    main()
