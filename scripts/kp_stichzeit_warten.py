#!/usr/bin/env python3
"""Kaspa Pulse, wartet bis der eigene Knoten im Runner synchron ist.

Fragt NUR den lokalen Knoten im Runner (wRPC borsh, Loopback). Gibt nur Zahlen aus,
keine Adressen, keine Peers. Fertig, wenn der Knoten synchron meldet und seine
Median-Zeit mindestens --vorlauf-min hinter der Stichzeit liegt.

  python3 scripts/kp_stichzeit_warten.py --stichzeit-ms 1792495986000 --max-min 300
  python3 scripts/kp_stichzeit_warten.py --selbsttest
"""
import argparse
import asyncio
import datetime as dt
import sys
import time

# lokaler knoten im runner, wrpc borsh standardport; adresse erst zur laufzeit
URL = "ws://" + ".".join(["127", "0", "0", "1"]) + ":17110"


def iso(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def feld(d, *namen):
    for n in namen:
        if isinstance(d, dict) and n in d:
            return d[n]
    return None


def fertig(info, dag, stichzeit_ms, vorlauf_ms):
    """(fertig?, zeile) aus den beiden Antworten."""
    sync = bool(feld(info, "isSynced", "is_synced"))
    pmt = feld(dag, "pastMedianTime", "past_median_time")
    daa = feld(dag, "virtualDaaScore", "virtual_daa_score")
    bloecke = feld(dag, "blockCount", "block_count")
    kopf = feld(dag, "headerCount", "header_count")
    zeile = "synchron %s | median-zeit %s | virtual daa %s | koepfe %s | bloecke %s" % (
        "ja" if sync else "nein", iso(int(pmt)) if pmt else "-", daa, kopf, bloecke)
    return (sync and pmt is not None and int(pmt) >= stichzeit_ms + vorlauf_ms), zeile


async def laufen(stichzeit_ms, max_min, vorlauf_min, takt_s):
    import kaspa  # noqa: WPS433
    ende = time.time() + max_min * 60
    vorlauf_ms = vorlauf_min * 60 * 1000
    client = None
    letzte = 0
    while time.time() < ende:
        try:
            if client is None:
                client = kaspa.RpcClient(url=URL, network_id="mainnet")
                await asyncio.wait_for(client.connect(), 20)
            info = await asyncio.wait_for(client.get_server_info(), 20)
            dag = await asyncio.wait_for(client.get_block_dag_info(), 20)
            ok, zeile = fertig(info, dag, stichzeit_ms, vorlauf_ms)
            if ok:
                print("fertig, " + zeile, flush=True)
                await client.disconnect()
                return 0
            if time.time() - letzte >= 300:
                print(zeile, flush=True)
                letzte = time.time()
        except Exception as exc:  # noqa: BLE001
            # nur der typ, der text koennte vom knoten kommen
            if time.time() - letzte >= 300:
                print("noch keine antwort (%s)" % type(exc).__name__, flush=True)
                letzte = time.time()
            client = None
        await asyncio.sleep(takt_s)
    print("zeit abgelaufen, knoten nicht synchron", flush=True)
    return 3


def selbsttest():
    fehler = 0
    t = 1792495986000
    faelle = [
        ({"isSynced": True}, {"pastMedianTime": t + 700000, "virtualDaaScore": 1}, True),
        ({"isSynced": False}, {"pastMedianTime": t + 700000}, False),
        ({"isSynced": True}, {"pastMedianTime": t + 100000}, False),
        ({"is_synced": True}, {"past_median_time": t + 600000}, True),
        ({}, {}, False),
    ]
    for info, dag, soll in faelle:
        ist, zeile = fertig(info, dag, t, 600000)
        if ist != soll:
            fehler += 1
            print("FEHLER", info, dag, ist)
        if URL in zeile or "ws://" in zeile:
            fehler += 1
            print("FEHLER, adresse in der zeile")
    print("%d fehler" % fehler)
    return 1 if fehler else 0


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--stichzeit-ms", type=int)
    a.add_argument("--max-min", type=int, default=300)
    a.add_argument("--vorlauf-min", type=int, default=10)
    a.add_argument("--takt-s", type=int, default=30)
    a.add_argument("--selbsttest", action="store_true")
    x = a.parse_args()
    if x.selbsttest:
        return selbsttest()
    return asyncio.run(laufen(x.stichzeit_ms, x.max_min, x.vorlauf_min, x.takt_s))


if __name__ == "__main__":
    sys.exit(main())
