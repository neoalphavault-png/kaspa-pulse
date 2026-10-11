#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mainnet_pruefung.py, wie weit reichen zwei Mainnet-Knoten zurueck.

Nur lesend. Zwei voneinander unabhaengige Knoten ueber den Resolver, wie bei
der TN10-Nachzaehlung. Je Knoten: Version, synchron, UTXO-Index, Zeit des
Pruning-Punkts und wie viele Stunden er hinter der Spitze liegt. Bloecke vor
dem Pruning-Punkt hat ein normaler Knoten nicht mehr.

Gibt keine Adresse, keine Tx-ID und keinen Covenant aus. Optional prueft
--vor ZEIT nur, ob ZEIT vor dem Pruning-Punkt liegt (ja/nein), ohne zu sagen,
wofuer die Zeit steht.

Keine Wallet, keine Schluessel, keine Secrets.

    python3 scripts/mainnet_pruefung.py --vor 2026-10-09T05:25:39Z
    python3 scripts/mainnet_pruefung.py --selbsttest
"""

import argparse
import asyncio
import datetime as dt
import hashlib
import sys

NETZ = "mainnet"


def feld(d, *namen):
    """ein feld aus dict oder objekt, in camelCase oder snake_case."""
    for n in namen:
        if isinstance(d, dict) and n in d:
            return d[n]
        if hasattr(d, n):
            return getattr(d, n)
    return None


def iso_ms(ms):
    return dt.datetime.fromtimestamp(ms / 1000, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def zeit_ms(text):
    t = dt.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    return int(t.timestamp() * 1000)


def kennung(p2p):
    """nur ein kurzer hash der p2p-id, nie die id selbst und nie eine adresse."""
    return hashlib.sha256(str(p2p).encode()).hexdigest()[:10] if p2p else ""


async def knoten(meide=""):
    import kaspa                                         # noqa: WPS433
    for versuch in range(8):
        url = await kaspa.Resolver().get_url("borsh", kaspa.NetworkId(NETZ))
        rpc = kaspa.RpcClient(url=url, network_id=NETZ)
        await rpc.connect()
        info = await rpc.get_info()
        p2p = str(feld(info, "p2pId") or "")
        if meide and kennung(p2p) == meide and versuch < 7:
            await rpc.disconnect()
            await asyncio.sleep(2)
            continue
        return rpc, info, kennung(p2p)
    raise RuntimeError("kein zweiter knoten")


async def lesen(rpc, info, ken, vor_ms):
    dag = await rpc.get_block_dag_info()
    pp = feld(dag, "pruningPointHash")
    b = await rpc.get_block({"hash": pp, "includeTransactions": False})
    blk = feld(b, "block") or b
    pp_ms = int(feld(feld(blk, "header") or {}, "timestamp") or 0)
    jetzt = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
    z = {
        "kennung": ken,
        "version": str(feld(info, "serverVersion") or ""),
        "synchron": bool(feld(info, "isSynced")),
        "utxo_index": bool(feld(info, "isUtxoIndexed")),
        "pruning_punkt_utc": iso_ms(pp_ms) if pp_ms else "",
        "pruning_punkt_stunden_zurueck": round((jetzt - pp_ms) / 3.6e6, 1) if pp_ms else None,
        "gelesen_utc": iso_ms(jetzt),
    }
    if vor_ms is not None and pp_ms:
        z["zeit_vor_pruning_punkt"] = "ja" if vor_ms < pp_ms else "nein"
    return z


async def lauf(vor):
    vor_ms = zeit_ms(vor) if vor else None
    rpc1, info1, k1 = await knoten()
    rpc2, info2, k2 = await knoten(meide=k1)
    try:
        for name, (rpc, info, ken) in (("k1", (rpc1, info1, k1)), ("k2", (rpc2, info2, k2))):
            z = await lesen(rpc, info, ken, vor_ms)
            print(name, " ".join("%s %s" % (k, v) for k, v in z.items()))
        print("zwei verschiedene knoten", "ja" if k1 != k2 else "nein")
    finally:
        await rpc1.disconnect()
        await rpc2.disconnect()


def selbsttest():
    fehler = 0

    def ok(name, wahr):
        nonlocal fehler
        if not wahr:
            fehler += 1
        print(("ok    " if wahr else "FEHLER"), name)

    ok("zeit hin und zurueck", iso_ms(zeit_ms("2026-10-09T05:25:39Z")) == "2026-10-09T05:25:39Z")
    ok("kennung ist kurz und nicht die id", len(kennung("abc")) == 10 and kennung("abc") != "abc")
    ok("leere id gibt leere kennung", kennung("") == "")
    ok("feld aus dict", feld({"isSynced": True}, "isSynced") is True)
    print("selbsttest", fehler, "fehler")
    return fehler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vor", default="", help="UTC-Zeit, nur ja/nein ob vor dem Pruning-Punkt")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args()
    if a.selbsttest:
        sys.exit(1 if selbsttest() else 0)
    asyncio.run(lauf(a.vor))


if __name__ == "__main__":
    main()
