#!/usr/bin/env python3
"""Kaspa Pulse, KCC-20-Zaehlung vom eigenen Knoten (Ben, 23.10.2026).

KCC-20 (kaspanet/kccs, Final seit 21.10.2026) legt den Token-Zustand in das
P2SH-Programm R eines Covenant-Outputs. Ein nicht ausgegebener Output zeigt nur
Blake2b(R). Der Zustand eines Outputs steht aber in der Transaktion, die ihn
erzeugt hat:

  transfer  Dispatch-Tag 79c71c23, Argument next_states (Feld-gruppiert,
            KCC-1 3.4.6), je Covenant-Family-Output ein KCC20State
  mint u.a. ein KCC20State-Record als Argument (KCC-1 3.4.6, je Feld ein Push)

Gezaehlt wird ein Output nur, wenn der Zustand bewiesen ist: aus einem
Template (Praefix, Suffix) des KCC-20-Programms und dem Kandidaten-Zustand wird
R' = Praefix || EncodeState(zustand) || Suffix gebaut, und Blake2b(R') muss
gleich dem Hash im Skript des Outputs sein (KCC-1 3.6, 3.7.5). Templates kommen
aus den Programmen der Eingaenge (Zustand an seiner kodierten Form erkannt) und
aus dem oeffentlichen Referenz-Artefakt. Was sich so nicht beweisen laesst,
zaehlt als "nicht dekodiert", geschaetzt wird nichts.

Eingaben (JSON-Zeilen, eine Tx je Zeile, Felder wie kp-stichzeit KP_TX=1):
  {"id","t","in":[["txid:i","sighex"],...],"out":[[sompi,ver,"spkhex",cov,auth],...]}

    python3 scripts/kcc20_zaehlung.py --bestand bestand.csv --tx tx.jsonl [--tx api-tx.jsonl] \\
        --stichzeit 2026-10-26T12:00:00Z --seit 2026-10-21T00:00:00Z --out aus/
    python3 scripts/kcc20_zaehlung.py --selbsttest
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import os
import sys
import tempfile

TAG_TRANSFER = bytes.fromhex("79c71c23")
TAG_DELEGATOR = bytes.fromhex("fd3ef14a")
STATE_LEN = 112
SCHEMES = set(range(5))
BORROW = set(range(4))

# ------------------------------------------------------------------ script


def pushes(script):
    """Push-only Skript in Datenelemente. OP_0 -> b'', OP_1..OP_16 -> 01..10,
    OP_1NEGATE -> 81. None, wenn ein Nicht-Push-Opcode vorkommt."""
    out, i, n = [], 0, len(script)
    while i < n:
        op = script[i]
        i += 1
        if op == 0x00:
            out.append(b"")
        elif 0x01 <= op <= 0x4b:
            if i + op > n:
                return None
            out.append(script[i:i + op])
            i += op
        elif op in (0x4c, 0x4d, 0x4e):
            w = {0x4c: 1, 0x4d: 2, 0x4e: 4}[op]
            if i + w > n:
                return None
            ln = int.from_bytes(script[i:i + w], "little")
            i += w
            if i + ln > n:
                return None
            out.append(script[i:i + ln])
            i += ln
        elif op == 0x4f:
            out.append(b"\x81")
        elif 0x51 <= op <= 0x60:
            out.append(bytes([op - 0x50]))
        else:
            return None
    return out


def int8(b):
    """achtbyte little-endian signed-magnitude (KCC-1 int state payload)."""
    v = int.from_bytes(b[:7] + bytes([b[7] & 0x7F]), "little")
    return -v if b[7] & 0x80 else v


def enc_int8(v):
    m = abs(v).to_bytes(8, "little")
    return m[:7] + bytes([m[7] | (0x80 if v < 0 else 0)])


def scriptnum(b):
    """minimaler ScriptNum (Argument-int)."""
    if not b:
        return 0
    if len(b) > 8:
        return None
    v = int.from_bytes(b[:-1] + bytes([b[-1] & 0x7F]), "little")
    return -v if b[-1] & 0x80 else v


def encode_state(s):
    amount, owner, osch, bsch, guard, ext = s
    return (b"\x08" + enc_int8(amount) + b"\x20" + owner + b"\x01" + bytes([osch]) + b"\x01" + bytes([bsch])
            + b"\x20" + guard + b"\x20" + ext)


def zustand_gueltig(s):
    amount, owner, osch, bsch, guard, ext = s
    return amount is not None and amount >= 0 and osch in SCHEMES and bsch in BORROW


def blake(b):
    return hashlib.blake2b(b, digest_size=32).digest()


def p2sh_hash(ver, spkhex):
    s = bytes.fromhex(spkhex)
    if ver == 0 and len(s) == 35 and s[0] == 0xAA and s[1] == 0x20 and s[34] == 0x87:
        return s[2:34]
    return None

# ------------------------------------------------------------------ kandidaten


def zustaende_in_r(r):
    """(offset, zustand) fuer jede Stelle in R, an der eine kodierte KCC20State
    steht (sechs PushExplicit-Felder, 112 Byte)."""
    aus = []
    for o in range(0, len(r) - STATE_LEN + 1):
        if not (r[o] == 0x08 and r[o + 9] == 0x20 and r[o + 42] == 0x01 and r[o + 44] == 0x01
                and r[o + 46] == 0x20 and r[o + 79] == 0x20):
            continue
        s = (int8(r[o + 1:o + 9]), r[o + 10:o + 42], r[o + 43], r[o + 45], r[o + 47:o + 79], r[o + 80:o + 112])
        if zustand_gueltig(s):
            aus.append((o, s))
    return aus


def kcc1_aufruf(sig):
    """(args, tag, R) eines KCC-1-Aufrufs: letzter Push R, davor 4-Byte-Tag."""
    p = pushes(sig)
    if not p or len(p) < 2 or len(p[-2]) != 4 or not p[-1]:
        return None
    return p[:-2], p[-2], p[-1]


def transfer_zustaende(args):
    """next_states aus den transfer-Argumenten (feldgruppiert), sonst []."""
    if len(args) < 7:
        return []
    a, o, osch, bsch, g, e = args[0:6]
    if len(a) == 0 or len(a) % 8:
        return []
    k = len(a) // 8
    if len(o) != 32 * k or len(osch) != k or len(bsch) != k or len(g) != 32 * k or len(e) != 32 * k:
        return []
    zs = [(int8(a[8 * i:8 * i + 8]), o[32 * i:32 * i + 32], osch[i], bsch[i], g[32 * i:32 * i + 32],
           e[32 * i:32 * i + 32]) for i in range(k)]
    return zs if all(zustand_gueltig(z) for z in zs) else []


def record_zustaende(args):
    """jeder einzelne KCC20State-Record unter den Argumenten (je Feld ein Push)."""
    aus = []
    for i in range(len(args) - 5):
        a, o, osch, bsch, g, e = args[i:i + 6]
        # byte 00 ist nach KCC-1 OP_DATA_1 00; OP_0 wird trotzdem als 0 gelesen,
        # der hash-beweis entscheidet ohnehin
        if len(o) != 32 or len(osch) > 1 or len(bsch) > 1 or len(g) != 32 or len(e) != 32 or len(a) > 8:
            continue
        z = (scriptnum(a), o, osch[0] if osch else 0, bsch[0] if bsch else 0, g, e)
        if zustand_gueltig(z):
            aus.append(z)
    return aus

# ------------------------------------------------------------------ zaehlung


class Zaehlung:
    def __init__(self, seed_templates=()):
        self.templates = {}             # key -> (prefix, suffix)
        self.je_cov = collections.defaultdict(set)
        for p, s in seed_templates:
            self._tpl(p, s, None)
        self.bewiesen = {}              # "txid:i" -> zustand
        self.tx_info = {}               # txid -> {...}

    def _tpl(self, p, s, cov):
        k = hashlib.sha256(len(p).to_bytes(8, "little") + p + s).hexdigest()
        self.templates[k] = (p, s)
        if cov:
            self.je_cov[cov].add(k)
        return k

    def tx(self, t):
        """eine Tx auswerten: Templates sammeln, Ausgaenge beweisen, Art merken."""
        kand, lokale, tags = [], [], []
        for prev, sighex in t["in"]:
            auf = kcc1_aufruf(bytes.fromhex(sighex))
            if not auf:
                continue
            args, tag, r = auf
            tags.append(tag)
            for o, _z in zustaende_in_r(r):
                lokale.append(self._tpl(r[:o], r[o + STATE_LEN:], None))
            if tag == TAG_TRANSFER:
                kand += transfer_zustaende(args)
            kand += record_zustaende(args)
        covs = {o[3] for o in t["out"] if o[3]}
        for c in covs:
            self.je_cov[c].update(lokale)
        bewiesen = 0
        for i, (sompi, ver, spk, cov, _auth) in enumerate(t["out"]):
            h = p2sh_hash(ver, spk)
            if h is None or not cov or not kand:
                continue
            reihe = list(dict.fromkeys(lokale + sorted(self.je_cov.get(cov, ())))) + list(self.templates)
            gefunden = None
            for k in dict.fromkeys(reihe):
                p, s = self.templates[k]
                for z in kand:
                    if blake(p + encode_state(z) + s) == h:
                        gefunden = z
                        self.je_cov[cov].add(k)
                        break
                if gefunden:
                    break
            if gefunden:
                self.bewiesen["%s:%d" % (t["id"], i)] = gefunden
                bewiesen += 1
        art = "transfer" if TAG_TRANSFER in tags else ("kcc20_ausgang" if bewiesen else "andere")
        self.tx_info[t["id"]] = {"t": t.get("t"), "art": art, "covs": sorted(covs), "bewiesen": bewiesen}


def seed_aus_artefakt(pfad):
    """KCC-20-Templates aus einem oeffentlichen Argent-Artefakt (Referenz)."""
    try:
        d = json.load(open(pfad, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    aus = []
    for tp in (d.get("argent", {}).get("template_plan", {}).get("templates") or []):
        h = (tp.get("actor_type_handle") or {}).get("template") or {}
        if tp.get("actor") == "KCC20" and "prefix" in h and "suffix" in h:
            aus.append((bytes(h["prefix"]), bytes(h["suffix"])))
    return aus


def ms(text):
    return int(dt.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp() * 1000)


def listen_lesen(pfade):
    """kcc20-tx-listen frueherer laeufe: txid, zeit, art, covs (ohne skripte)."""
    aus = {}
    for p in pfade:
        if os.path.exists(p):
            for z in open(p, encoding="utf-8"):
                e = json.loads(z)
                aus.setdefault(e["id"], e)
    return aus


def auswerten(bestand_pfad, tx_pfade, stichzeit_ms, seit_ms, seed=(), fruehere=None, liste_aus=None):
    z = Zaehlung(seed)
    txs, quellen = {}, {}
    for p in tx_pfade:
        if not os.path.exists(p):
            continue
        for zeile in open(p, encoding="utf-8"):
            t = json.loads(zeile)
            if t["id"] not in txs:
                txs[t["id"]] = t
                quellen[t["id"]] = os.path.basename(p)
    # zweimal: der zweite durchgang nutzt templates, die erst spaeter auftauchten
    for _ in range(2):
        for t in sorted(txs.values(), key=lambda x: (x.get("t") or 0, x["id"])):
            z.tx(t)
    lebend, ohne_tx = [], 0
    with open(bestand_pfad, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not r["covenant_id"]:
                continue
            txid = r["outpoint"].split(":")[0]
            if txid not in txs:
                ohne_tx += 1
            lebend.append((r["outpoint"], r["covenant_id"], int(r["sompi"]), z.bewiesen.get(r["outpoint"])))
    tok = collections.defaultdict(lambda: {"outputs": 0, "menge": 0, "halter": set(), "kas_sompi": 0,
                                          "unter_token": set(), "transfers": 0, "kcc20_tx": 0})
    nicht = {"outputs": 0, "kas_sompi": 0, "covenants": set()}
    for op, cov, sompi, zst in lebend:
        if zst is None:
            nicht["outputs"] += 1
            nicht["kas_sompi"] += sompi
            nicht["covenants"].add(cov)
            continue
        t = tok[cov]
        t["outputs"] += 1
        t["menge"] += zst[0]
        t["kas_sompi"] += sompi
        t["halter"].add((zst[2], zst[1].hex()))
        t["unter_token"].add(zst[5].hex())
    alle_info = {k: dict(v, quelle="frueherer lauf") for k, v in (fruehere or {}).items()}
    for k, v in z.tx_info.items():
        alle_info[k] = dict(v, quelle=quellen[k])
    if liste_aus:
        with open(liste_aus, "w", encoding="utf-8") as fh:
            for k, v in sorted(z.tx_info.items(), key=lambda kv: (kv[1]["t"] or 0, kv[0])):
                if v["art"] in ("transfer", "kcc20_ausgang"):
                    fh.write(json.dumps({"id": k, "t": v["t"], "art": v["art"], "covs": v["covs"]}) + "\n")
    seit_quelle = collections.Counter()
    for txid, info in alle_info.items():
        if info["t"] is None or not (seit_ms <= info["t"] <= stichzeit_ms):
            continue
        if info["art"] in ("transfer", "kcc20_ausgang"):
            for c in info["covs"]:
                if info["art"] == "transfer":
                    tok[c]["transfers"] += 1
                tok[c]["kcc20_tx"] += 1
            if info["art"] == "transfer":
                seit_quelle[info["quelle"]] += 1
    zeilen = []
    for cov, t in sorted(tok.items(), key=lambda kv: (-kv[1]["outputs"], kv[0])):
        if t["outputs"] == 0 and t["transfers"] == 0:
            continue
        zeilen.append({"covenant_id": cov, "halter_outputs": t["outputs"], "halter": len(t["halter"]),
                       "menge_basis": t["menge"], "unter_token": len(t["unter_token"]),
                       "kas": round(t["kas_sompi"] / 1e8, 8), "transfers_seit": t["transfers"],
                       "kcc20_tx_seit": t["kcc20_tx"]})
    lebende_tokens = [r for r in zeilen if r["halter_outputs"] > 0]
    zus = {
        "quelle": "counted by kaspa pulse, eigener knoten, zustaende per blake2b-hash bewiesen",
        "tokens_mit_lebenden_outputs": len(lebende_tokens),
        "tokens_mit_aktivitaet_seit": sum(1 for r in zeilen if r["kcc20_tx_seit"] > 0),
        "halter_outputs": sum(r["halter_outputs"] for r in lebende_tokens),
        "halter": sum(r["halter"] for r in lebende_tokens),
        "transfers_seit": sum(r["transfers_seit"] for r in zeilen),
        "transfers_seit_je_quelle": dict(seit_quelle),
        "covenant_utxos_gesamt": len(lebend),
        "covenant_utxos_nicht_dekodiert": nicht["outputs"],
        "covenant_utxos_nicht_dekodiert_kas": round(nicht["kas_sompi"] / 1e8, 8),
        "covenant_ids_nicht_dekodiert": len(nicht["covenants"]),
        "lebende_outputs_ohne_erzeugende_tx": ohne_tx,
        "templates": len(z.templates),
        "tx_gelesen": len(txs),
    }
    return zeilen, zus

# ------------------------------------------------------------------ selbsttest


def selbsttest():
    fehler = []

    def ok(name, bed, ist=None):
        if not bed:
            fehler.append(name)
            print("FEHLER", name, ist)
    hier = os.path.dirname(os.path.abspath(__file__))
    vek_pfad = os.path.join(hier, "..", "kcc20", "vektoren", "kcc-0020-conformance.json")
    v = json.load(open(vek_pfad, encoding="utf-8"))
    se = v["state_encoding"]
    s0 = (se["state"]["amount"], bytes.fromhex(se["state"]["owner_hex"]), int(se["state"]["owner_scheme_hex"], 16),
          int(se["state"]["borrow_scheme_hex"], 16), bytes.fromhex(se["state"]["borrow_guard_hex"]),
          bytes.fromhex(se["state"]["extension_commitment_hex"]))
    enc = encode_state(s0)
    ok("encodeState wie vektor, 112 byte", enc.hex() == "".join(se["encoded_fields_hex"]) and len(enc) == 112, enc.hex())
    ok("dispatch-tags wie vektor", {d["entrypoint"]: d["dispatch_tag_hex"] for d in v["dispatch"]}
       == {"transfer": TAG_TRANSFER.hex(), "transfer_delegator": TAG_DELEGATOR.hex()})
    ta = v["transfer_arguments"]
    erwartet = [(n["amount"], bytes.fromhex(n["owner_hex"]), int(n["owner_scheme_hex"], 16),
                 int(n["borrow_scheme_hex"], 16), bytes.fromhex(n["borrow_guard_hex"]),
                 bytes.fromhex(n["extension_commitment_hex"])) for n in ta["next_states"]]
    arg_hex = "".join(ta["grouped_field_pushes_hex"]) + ta["witness_push_hex"]
    p = pushes(bytes.fromhex(arg_hex))
    ok("transfer-argumente wie vektor dekodiert", p is not None and transfer_zustaende(p) == erwartet,
       p and transfer_zustaende(p))
    ok("int8 signed magnitude", int8(enc_int8(-500)) == -500 and int8(bytes.fromhex("e803000000000000")) == 1000)
    ok("scriptnum minimal", scriptnum(b"\xe8\x03") == 1000 and scriptnum(b"\x81") == -1 and scriptnum(b"") == 0)
    # erfundene kette: template, transfer von 1000 auf 600+400, mint von 5
    pre, suf = b"\x6b\x20" + b"\x97" * 32, b"\x6c\x76\x04" + TAG_TRANSFER + b"\x87" * 40
    r0 = pre + encode_state(s0[:0] + (1000,) + s0[1:]) + suf
    spk = lambda z: "aa20" + blake(pre + encode_state(z) + suf).hex() + "87"  # noqa: E731
    sig = lambda args, tag, r: "".join(  # noqa: E731
        ("%02x" % len(a) + a.hex()) if 0 < len(a) <= 75 else (("4c%02x" % len(a)) + a.hex() if len(a) < 256
                                                               else "4d" + len(a).to_bytes(2, "little").hex() + a.hex())
        for a in list(args) + [tag, r])
    a1, a2 = erwartet
    gruppen = [enc_int8(a1[0]) + enc_int8(a2[0]), a1[1] + a2[1], bytes([a1[2], a2[2]]), bytes([a1[3], a2[3]]),
               a1[4] + a2[4], a1[5] + a2[5], b"\x00" + b"\x44" * 65]
    cov = "c0" * 32
    t1 = {"id": "aa" * 32, "t": ms("2026-10-22T10:00:00Z"),
          "in": [["bb" * 32 + ":0", sig(gruppen, TAG_TRANSFER, r0)]],
          "out": [[100, 0, spk(a1), cov, 0], [100, 0, spk(a2), cov, 0], [5000, 0, "20" + "ab" * 32 + "ac", None, None]]}
    m = (5, b"\x55" * 32, 0, 0, b"\x00" * 32, a1[5])
    minter_r = b"\x51\x52" + b"\x99" * 30
    t2 = {"id": "dd" * 32, "t": ms("2026-10-23T10:00:00Z"),
          "in": [["ee" * 32 + ":0", sig([b"\x05", m[1], b"\x00", b"\x00", m[4], m[5]], b"\x11\x22\x33\x44", minter_r)]],
          "out": [[100, 0, "aa20" + "11" * 32 + "87", cov, 0], [100, 0, spk(m), cov, 0]]}
    t3 = {"id": "ff" * 32, "t": ms("2026-10-20T10:00:00Z"), "in": [],
          "out": [[100, 0, "aa20" + "22" * 32 + "87", "d0" * 32, 0]]}
    with tempfile.TemporaryDirectory() as d:
        txp = os.path.join(d, "tx.jsonl")
        with open(txp, "w", encoding="utf-8") as fh:
            for t in (t1, t2, t3):
                fh.write(json.dumps(t) + "\n")
        bp = os.path.join(d, "bestand.csv")
        with open(bp, "w", encoding="utf-8") as fh:
            fh.write("outpoint,sompi,block_daa_score,is_coinbase,covenant_id,klasse,adresse,spk_version,spk_hex\n")
            for op, c in (("aa" * 32 + ":0", cov), ("aa" * 32 + ":1", cov), ("dd" * 32 + ":1", cov),
                          ("dd" * 32 + ":0", cov), ("ff" * 32 + ":0", "d0" * 32), ("99" * 32 + ":0", "e0" * 32)):
                fh.write("%s,100,1,false,%s,p2sh,,0,aa\n" % (op, c))
        fr = {"77" * 32: {"t": ms("2026-10-21T05:00:00Z"), "art": "transfer", "covs": [cov]},
              "aa" * 32: {"t": t1["t"], "art": "transfer", "covs": [cov]}}
        la = os.path.join(d, "liste.jsonl")
        zl, zs = auswerten(bp, [txp], ms("2026-10-26T12:00:00Z"), ms("2026-10-21T00:00:00Z"), (), fr, la)
        liste = [json.loads(x) for x in open(la, encoding="utf-8")]
    r = {x["covenant_id"]: x for x in zl}
    ok("transfer bewiesen: 600 und 400, mint 5 ueber das template aus dem transfer", r.get(cov, {}).get("menge_basis")
       == 1005 and r[cov]["halter_outputs"] == 3 and r[cov]["halter"] == 3, r.get(cov))
    ok("minter-ausgang ohne bewiesenen zustand bleibt nicht dekodiert", zs["covenant_utxos_nicht_dekodiert"] == 3
       and zs["covenant_ids_nicht_dekodiert"] == 3, zs)
    ok("transfers seit 21.10.: einer eigener plus einer aus frueherem lauf, doppelte einmal", r[cov]["transfers_seit"] == 2
       and r[cov]["kcc20_tx_seit"] == 3 and zs["transfers_seit"] == 2
       and zs["transfers_seit_je_quelle"] == {"tx.jsonl": 1, "frueherer lauf": 1}, (r[cov], zs["transfers_seit_je_quelle"]))
    ok("eigene liste ohne skripte geschrieben", {e["id"] for e in liste} == {"aa" * 32, "dd" * 32}
       and all(set(e) == {"id", "t", "art", "covs"} for e in liste), liste)
    ok("lebender output ohne erzeugende tx gezaehlt", zs["lebende_outputs_ohne_erzeugende_tx"] == 1)
    ok("tokens mit lebenden outputs 1", zs["tokens_mit_lebenden_outputs"] == 1)
    seed = seed_aus_artefakt(os.path.join(hier, "..", "kcc20", "vektoren", "public-mint-artifact.json"))
    ok("referenz-template aus dem artefakt gelesen", len(seed) == 1 and seed[0][0][:2] == b"\x6b\x20", len(seed))
    # mint ohne jeden kcc20-eingang: nur das referenz-template kann ihn beweisen
    sp, ss = seed[0]
    m2 = (7, b"\x66" * 32, 1, 1, b"\x00" * 32, b"\x00" * 32)
    t4 = {"id": "12" * 32, "t": ms("2026-10-24T10:00:00Z"),
          "in": [["34" * 32 + ":0", sig([b"\x07", m2[1], b"\x01", b"\x01", m2[4], m2[5]], b"\x55\x66\x77\x88", b"\x51" * 40)]],
          "out": [[100, 0, "aa20" + blake(sp + encode_state(m2) + ss).hex() + "87", "f0" * 32, 1]]}
    za, zb = Zaehlung(), Zaehlung(seed)
    za.tx(t4)
    zb.tx(t4)
    ok("mint mit referenz-template bewiesen, ohne nicht", "12" * 32 + ":0" in zb.bewiesen
       and zb.bewiesen["12" * 32 + ":0"][0] == 7 and not za.bewiesen)
    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bestand")
    ap.add_argument("--tx", action="append", default=[])
    ap.add_argument("--stichzeit")
    ap.add_argument("--seit", default="2026-10-21T00:00:00Z")
    ap.add_argument("--artefakt", default="")
    ap.add_argument("--out", default="aus")
    ap.add_argument("--liste", action="append", default=[], help="kcc20-tx-listen frueherer laeufe")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    os.makedirs(a.out, exist_ok=True)
    zl, zs = auswerten(a.bestand, a.tx, ms(a.stichzeit), ms(a.seit), seed_aus_artefakt(a.artefakt),
                       listen_lesen(a.liste), os.path.join(a.out, "kcc20-tx-liste.jsonl"))
    with open(os.path.join(a.out, "kcc20-tokens.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(zl[0]) if zl else ["covenant_id"])
        w.writeheader()
        w.writerows(zl)
    zs.update({"stichzeit": a.stichzeit, "transfers_seit_utc": a.seit})
    with open(os.path.join(a.out, "kcc20-zaehlung.json"), "w", encoding="utf-8") as fh:
        json.dump(zs, fh, indent=1)
    print(json.dumps(zs, indent=1))
    w = csv.DictWriter(sys.stdout, fieldnames=list(zl[0]) if zl else ["covenant_id"])
    w.writeheader()
    w.writerows(zl)
    return 0


if __name__ == "__main__":
    sys.exit(main())
