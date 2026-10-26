#!/usr/bin/env python3
"""chipnet_wbch.py - zaehlt chipnet-Transaktionen mit der wBCH-Kategorie aus dem XO-Template.

Ben, 26.10.2026, Schritt 3: Lassen sich XO-Transaktionen auf chipnet erkennen?
XO (General Protocols, gitlab.com/GeneralProtocols/xo) ist eine Wallet- und
Engine-Schicht, die Transaktionen aus Wallet-Templates baut. Die veroeffentlichten
Templates (@xo-cash/templates 0.0.11) sind P2PKH, 2-von-3-Multisig, faucet.cash
und Wrapped BCH (mainnet und chipnet). Nur das Template "Wrapped BCH (chipnet)"
hat einen festen Fingerabdruck:
- die Token-Kategorie wbchTokenCategory
  bb61cd7a6c8a3a3742d965dc7ac73c1117382a5c8930b68338deb881f75c0214
- das Covenant-Skript ohne Parameter (wrapBCHLockingBytecode):
  OP_INPUTINDEX OP_OUTPUTBYTECODE OP_INPUTINDEX OP_UTXOBYTECODE OP_EQUALVERIFY
  OP_INPUTINDEX OP_OUTPUTTOKENCATEGORY OP_INPUTINDEX OP_UTXOTOKENCATEGORY OP_EQUALVERIFY
  OP_INPUTINDEX OP_UTXOTOKENAMOUNT OP_INPUTINDEX OP_UTXOVALUE OP_ADD
  OP_INPUTINDEX OP_OUTPUTTOKENAMOUNT OP_INPUTINDEX OP_OUTPUTVALUE OP_ADD OP_NUMEQUAL
Das ist der wrapped.cash-Covenant; jede Wallet kann ihn benutzen. Gezaehlt
werden also wBCH-Transaktionen auf chipnet, nicht XO-Transaktionen.

Wir holen die vollen Bloecke seit --ab bei einem chipnet-Peer (getdata) und
suchen Ausgaben mit dem Token-Praefix 0xef und dieser Kategorie sowie Ausgaben,
die den Covenant als P2SH20 oder P2SH32 sperren. Keine Adressen in der Ausgabe;
Transaktions-IDs sind oeffentliche Kettendaten.

  python3 scripts/bch/chipnet_wbch.py --koepfe koepfe.csv.gz --ab 2026-10-01 --aus wbch.json
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
import struct
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chipnet_koepfe as CK  # noqa: E402

KATEGORIE = "bb61cd7a6c8a3a3742d965dc7ac73c1117382a5c8930b68338deb881f75c0214"
# wrapBCHLockingBytecode aus @xo-cash/templates, wrapped_cash_chipnet.ts, Opcodes nach CHIP-2022-02 (Introspection)
OP = {"OP_INPUTINDEX": 0xC0, "OP_UTXOVALUE": 0xC6, "OP_UTXOBYTECODE": 0xC7, "OP_OUTPUTVALUE": 0xCC,
      "OP_OUTPUTBYTECODE": 0xCD, "OP_UTXOTOKENCATEGORY": 0xCE, "OP_UTXOTOKENAMOUNT": 0xD0,
      "OP_OUTPUTTOKENCATEGORY": 0xD1, "OP_OUTPUTTOKENAMOUNT": 0xD3, "OP_EQUALVERIFY": 0x88, "OP_ADD": 0x93,
      "OP_NUMEQUAL": 0x9C}
COVENANT = ("OP_INPUTINDEX OP_OUTPUTBYTECODE OP_INPUTINDEX OP_UTXOBYTECODE OP_EQUALVERIFY "
            "OP_INPUTINDEX OP_OUTPUTTOKENCATEGORY OP_INPUTINDEX OP_UTXOTOKENCATEGORY OP_EQUALVERIFY "
            "OP_INPUTINDEX OP_UTXOTOKENAMOUNT OP_INPUTINDEX OP_UTXOVALUE OP_ADD "
            "OP_INPUTINDEX OP_OUTPUTTOKENAMOUNT OP_INPUTINDEX OP_OUTPUTVALUE OP_ADD OP_NUMEQUAL")
REDEEM = bytes(OP[w] for w in COVENANT.split())
P2SH32 = b"\xaa\x20" + CK.sha256d(REDEEM) + b"\x87"
P2SH20 = b"\xa9\x14" + hashlib.new("ripemd160", hashlib.sha256(REDEEM).digest()).digest() + b"\x87"
KAT_INTERN, KAT_ANZEIGE = bytes.fromhex(KATEGORIE)[::-1], bytes.fromhex(KATEGORIE)
MSG_BLOCK = 2


class GrossPeer(CK.Peer):
    """Wie CK.Peer, aber volle Bloecke bis 64 MB (chipnet kennt grosse Testbloecke)."""

    def empfangen(self):
        kopf = self._lesen(24)
        if kopf[:4] != CK.MAGIC:
            raise ConnectionError("falsches netz-magic")
        cmd = kopf[4:16].rstrip(b"\0").decode(errors="replace")
        laenge = struct.unpack("<I", kopf[16:20])[0]
        if laenge > 64 << 20:
            raise ConnectionError("nachricht zu gross")
        payload = self._lesen(laenge)
        if CK.sha256d(payload)[:4] != kopf[20:24]:
            raise ConnectionError("pruefsumme falsch")
        if cmd == "ping":
            self.senden("pong", payload)
        return cmd, payload


def txs_lesen(block):
    """Liefert je Transaktion (txid, [Ausgabe-Skripte])."""
    n, i = CK.lies_varint(block, 80)
    out = []
    for _ in range(n):
        start = i
        i += 4
        nin, i = CK.lies_varint(block, i)
        for _ in range(nin):
            i += 36
            sl, i = CK.lies_varint(block, i)
            i += sl + 4
        nout, i = CK.lies_varint(block, i)
        skripte = []
        for _ in range(nout):
            i += 8
            sl, i = CK.lies_varint(block, i)
            skripte.append(block[i:i + sl])
            i += sl
        i += 4
        out.append((CK.sha256d(block[start:i])[::-1].hex(), skripte))
    return out


def treffer(skript):
    """(kategorie_intern, kategorie_anzeige, covenant) fuer ein Ausgabe-Skript mit Token-Praefix."""
    kat_i = kat_a = False
    rest = skript
    if skript[:1] == b"\xef" and len(skript) >= 34:
        kat = skript[1:33]
        kat_i, kat_a = kat == KAT_INTERN, kat == KAT_ANZEIGE
        bitfeld = skript[33]
        j = 34
        if bitfeld & 0x40:  # Commitment
            cl, j = CK.lies_varint(skript, j)
            j += cl
        if bitfeld & 0x10:  # Menge
            _, j = CK.lies_varint(skript, j)
        rest = skript[j:]
    return kat_i, kat_a, rest in (P2SH32, P2SH20)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--koepfe", required=True)
    ap.add_argument("--ab", default="2026-10-01")
    ap.add_argument("--aus", required=True)
    args = ap.parse_args()
    ab = datetime.strptime(args.ab, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
    with gzip.open(args.koepfe, "rt") as f:
        bl = [(int(z["hoehe"]), z["hash"], int(z["zeit"])) for z in csv.DictReader(f) if int(z["zeit"]) >= ab]
    bl.sort()
    spitze = bl[-1][0]
    gemeinsam = bytes.fromhex(CK.LETZTER_GEMEINSAMER[1])[::-1]
    tempnet = bytes.fromhex(CK.ERSTER_TEMPNET[1])[::-1]

    adressen, benutzt = CK.peers_finden(), set()
    gelesen, fehler_bloecke, gefunden = {}, [], []
    agents = []
    while len(gelesen) < len(bl) and len(benutzt) < len(adressen):
        peer = None
        for a in adressen:
            if a in benutzt:
                continue
            benutzt.add(a)
            try:
                p = GrossPeer(a, timeout=30)
                p.handschlag()
                probe = p.koepfe([gemeinsam], warten=20)
                if probe and CK.sha256d(probe[0]) != tempnet and spitze - 5 <= p.hoehe <= spitze + 100:
                    peer = p
                    break
                p.zu()
            except (OSError, ConnectionError, TimeoutError, struct.error, IndexError):
                continue
        if peer is None:
            break
        agents.append(peer.agent)
        CK.log(f"bloecke von {peer.agent}")
        offen = [x for x in bl if x[1] not in gelesen]
        try:
            for k in range(0, len(offen), 16):
                stueck = offen[k:k + 16]
                peer.senden("getdata", CK.varint(len(stueck)) + b"".join(
                    struct.pack("<I", MSG_BLOCK) + bytes.fromhex(x[1])[::-1] for x in stueck))
                warte = {x[1]: x for x in stueck}
                frist = time.time() + 120
                while warte and time.time() < frist:
                    cmd, p = peer.empfangen()
                    if cmd != "block":
                        continue
                    h = CK.sha256d(p[:80])[::-1].hex()
                    if h not in warte:
                        continue
                    hoehe, _, zeit = warte.pop(h)
                    n_tx = 0
                    for txid, skripte in txs_lesen(p):
                        n_tx += 1
                        try:
                            t = [treffer(s) for s in skripte]
                        except IndexError:
                            t = []  # unlesbares Token-Praefix, zaehlt nicht
                        if any(any(x) for x in t):
                            gefunden.append({"txid": txid, "hoehe": hoehe,
                                             "zeit_utc": datetime.fromtimestamp(zeit, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                             "ausgaben_kategorie": sum(1 for x in t if x[0] or x[1]),
                                             "kategorie_byte_reihenfolge": "intern" if any(x[0] for x in t) else (
                                                 "anzeige" if any(x[1] for x in t) else None),
                                             "covenant_ausgaben": sum(1 for x in t if x[2])})
                    gelesen[h] = n_tx
                if warte:
                    raise TimeoutError(f"{len(warte)} bloecke ohne antwort")
                if len(gelesen) % 800 < 16:
                    CK.log(f"... {len(gelesen)} von {len(bl)} bloecken")
        except (OSError, ConnectionError, TimeoutError, struct.error, IndexError) as e:
            CK.log(f"peer abgebrochen ({type(e).__name__}), naechster")
            fehler_bloecke.append(type(e).__name__)
        peer.zu()

    wochen = {}
    for g in gefunden:
        j, k, _ = datetime.strptime(g["zeit_utc"], "%Y-%m-%dT%H:%M:%SZ").isocalendar()
        wochen[f"{j}-W{k:02d}"] = wochen.get(f"{j}-W{k:02d}", 0) + 1
    out = {
        "was": "chipnet-transaktionen mit der wBCH-kategorie oder dem wBCH-covenant aus @xo-cash/templates "
               "(wrapped_cash_chipnet.ts); wrapped.cash-covenant, nicht XO-spezifisch",
        "kategorie": KATEGORIE, "covenant_redeem_hex": REDEEM.hex(),
        "bloecke_im_fenster": len(bl), "bloecke_gelesen": len(gelesen),
        "transaktionen_gelesen": sum(gelesen.values()),
        "von_hoehe": bl[0][0], "bis_hoehe": spitze,
        "treffer_transaktionen": len(gefunden), "je_woche": dict(sorted(wochen.items())),
        "treffer": gefunden, "peer_software": agents, "abbrueche": fehler_bloecke,
    }
    with open(args.aus, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({k: out[k] for k in ("bloecke_im_fenster", "bloecke_gelesen", "transaktionen_gelesen",
                                          "treffer_transaktionen")}))
    if len(gelesen) < len(bl):
        sys.exit(f"nur {len(gelesen)} von {len(bl)} bloecken gelesen")


if __name__ == "__main__":
    main()
