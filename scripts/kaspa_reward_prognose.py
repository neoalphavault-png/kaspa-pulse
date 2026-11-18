#!/usr/bin/env python3
"""kaspa_reward_prognose.py - Prognose des naechsten Kaspa-Reward-Schritts (Ben, 16.11.2026).

Track Record, Rubrik "scheduled protocol events", getrennt von den
Upgrade-Prognosen. Kleiner Test ohne Fixkosten bis nach dem Schritt um den
5.12.2026, danach entscheidet Ben.

Das Ereignis
  Kaspa senkt den Blockreward jeden Monat ein Stueck. Ausgeloest wird der
  Schritt durch den DAA score, nicht durch eine Uhr. Nach rusty-kaspa v2.1.0
  (consensus/core/src/config/params.rs, consensus/src/processes/coinbase.rs):
    deflationary_phase_daa_score = 15.778.800 - 259.200 = 15.519.600
    crescendo_activation (DAA)   = 110.165.000, davor 1 BPS, danach 10 BPS
    SECONDS_PER_MONTH            = 2.629.800
    sekunden(d) = (crescendo - deflation) / 1 + (d - crescendo) // 10
    monat(d)    = sekunden(d) // SECONDS_PER_MONTH
  Der Monat k beginnt beim ersten DAA score d mit monat(d) = k, also
    d_k = crescendo + 10 * (k * 2.629.800 - (crescendo - deflation)).
  Gegenprobe: Monat 50 gibt 2,44997148 KAS je Block, der bekannte Schritt
  vom 5.7.2026 (scripts/reward_cut_alert.py). Der naechste Schritt ist Monat
  55 bei DAA score 610.101.000, von 1,94454365 auf 1,83540480 KAS je Block.
  Ereigniszeit ist die Kopfzeit des ersten Blocks der ausgewaehlten Kette mit
  DAA score >= Ziel, gezaehlt vom eigenen Knoten im Runner.

Prognose (Activation Forecast v1, wie PH-M-006)
  Eingang sind Bloecke der ausgewaehlten Kette des eigenen Knotens ab dem
  Pruning-Punkt, je etwa 400 gleich verteilt, mit Kopfzeit und DAA score. Aus
  aufeinanderfolgenden Punkten entstehen Intervalle (Sekunden, DAA). Die
  restlichen DAA bis zum Ziel werden 20.000 mal mit Zuruecklegen aus diesen
  Intervallen gezogen und die Sekunden aufaddiert, ab dem letzten Punkt. Der
  Median ist die Prognose, 10 % bis 90 % das 80-%-Band, 2,5 % bis 97,5 % das
  95-%-Band. Feste Saat, gleiche Eingaenge geben gleiche Zahlen.

Stufen
  14 Tage, 7 Tage, 2 Tage und 24 Stunden vor dem Prognosemedian. Der Lauf alle
  12 h veroeffentlicht eine Stufe, sobald ihr Zeitpunkt in den naechsten 12 h
  liegt oder schon vorbei ist; der tatsaechliche Vorlauf steht dabei. Jede
  Prognose wird vor dem Ereignis auf messung/kaspa-reward committet, der
  Commit ist ihr Zeitstempel.

Wertung nach dem Ereignis: im 80-%-Band, im 95-%-Band oder ausserhalb, dazu
die Abweichung vom Median in Sekunden.

Keine Adresse, kein Peer, kein Secret. Der Knoten laeuft nur im Runner.

  python3 scripts/kaspa_reward_prognose.py plan --zustand Z.json
  python3 scripts/kaspa_reward_prognose.py daten --aus punkte.json
  python3 scripts/kaspa_reward_prognose.py rechnen --zustand Z.json --punkte punkte.json
  python3 scripts/kaspa_reward_prognose.py --selbsttest
"""
import argparse
import asyncio
import bisect
import datetime as dt
import itertools
import json
import math
import os
import random
import sys
import time

DEFLATION = 15_778_800 - 259_200
CRESCENDO = 110_165_000
BPS_VOR, BPS_NACH = 1, 10
SEK_MONAT = 2_629_800
# rusty-kaspa v2.1.0 coinbase.rs SUBSIDY_BY_MONTH_TABLE, je Monat geteilt
# durch 10 und aufgerundet, in sompi je Block (nur die gebrauchten Monate)
REWARD_SOMPI = {49: 259565436, 50: 244997148, 51: 231246515, 54: 194454365, 55: 183540480, 56: 173239145}
QUELLE = ("rusty-kaspa v2.1.0, consensus/core/src/config/params.rs (MAINNET_PARAMS) und "
          "consensus/src/processes/coinbase.rs (subsidy_month, SUBSIDY_BY_MONTH_TABLE)")

STUFEN = [("14d", 14 * 86400), ("7d", 7 * 86400), ("2d", 2 * 86400), ("24h", 86400)]
TAKT_S = 12 * 3600          # der Workflow laeuft alle 12 h
ZIEHUNGEN = 20000
SAAT = 2027
PUNKTE = 400

URL = "ws://" + ".".join(["127", "0", "0", "1"]) + ":17110"   # nur der Knoten im Runner


def monat(d):
    if d < CRESCENDO:
        sek = (d - DEFLATION) // BPS_VOR
    else:
        sek = (CRESCENDO - DEFLATION) // BPS_VOR + (d - CRESCENDO) // BPS_NACH
    return sek // SEK_MONAT


def schritt_daa(k):
    return CRESCENDO + BPS_NACH * (k * SEK_MONAT - (CRESCENDO - DEFLATION) // BPS_VOR)


def naechster(d):
    k = monat(d) + 1
    return k, schritt_daa(k)


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def von_iso(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()


def quantil(xs, q):
    """lineare Interpolation zwischen den naechsten Raengen, wie report_v1."""
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    p = (len(s) - 1) * q
    lo = math.floor(p)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (p - lo)


def intervalle(punkte):
    """punkte: Liste (zeit_s, daa) nach DAA. Intervalle mit DAA > 0."""
    p = sorted(punkte, key=lambda x: x[1])
    return [(b[0] - a[0], b[1] - a[1]) for a, b in zip(p, p[1:]) if b[1] > a[1]]


def prognose(punkte, ziel, ziehungen=ZIEHUNGEN, saat=SAAT):
    iv = intervalle(punkte)
    if len(iv) < 20:
        raise SystemExit("zu wenig punkte fuer eine prognose")
    ref_t, ref_d = max(punkte, key=lambda x: x[1])
    rest = ziel - ref_d
    if rest <= 0:
        raise SystemExit("ziel schon erreicht")
    rnd = random.Random(saat)
    T = [t for t, _ in iv]
    D = [d for _, d in iv]
    mittel_d = sum(D) / len(D)
    alle = range(len(iv))
    sims = []
    for _ in range(ziehungen):
        acc_d = acc_t = 0.0
        while True:
            # ziehungen in bloecken, die kumulierte summe zeigt den uebergang
            k = int((rest - acc_d) / mittel_d * 1.05) + 16
            idx = rnd.choices(alle, k=k)
            cd = list(itertools.accumulate(D[i] for i in idx))
            if acc_d + cd[-1] < rest:
                acc_d += cd[-1]
                acc_t += sum(T[i] for i in idx)
                continue
            j = bisect.bisect_left(cd, rest - acc_d)
            vor_d = cd[j - 1] if j else 0
            acc_t += sum(T[i] for i in idx[:j]) + T[idx[j]] * (rest - acc_d - vor_d) / D[idx[j]]
            break
        sims.append(ref_t + acc_t)
    gesamt_t = sum(t for t, _ in iv)
    gesamt_d = sum(d for _, d in iv)
    return {"ref_utc": iso(ref_t), "ref_daa": ref_d, "rest_daa": rest,
            "p50_utc": iso(quantil(sims, 0.5)),
            "band80_utc": [iso(quantil(sims, 0.10)), iso(quantil(sims, 0.90))],
            "band95_utc": [iso(quantil(sims, 0.025)), iso(quantil(sims, 0.975))],
            "fenster": {"von_utc": iso(min(t for t, _ in punkte)), "bis_utc": iso(ref_t),
                        "intervalle": len(iv), "daa_je_s": round(gesamt_d / gesamt_t, 4) if gesamt_t > 0 else None},
            "ziehungen": ziehungen, "saat": saat}


def faellig(zustand, jetzt, p50):
    """Die Stufe mit dem kuerzesten Vorlauf, deren Zeitpunkt in den naechsten
    12 h liegt oder vorbei ist und die noch fehlt. None, wenn keine."""
    erledigt = {p["stufe"] for p in zustand.get("prognosen", [])}
    if jetzt >= p50:
        return None
    kandidaten = [(name, vor) for name, vor in STUFEN
                  if name not in erledigt and jetzt + TAKT_S >= p50 - vor]
    return min(kandidaten, key=lambda x: x[1])[0] if kandidaten else None


def werten(ergebnis_t, p):
    lo8, hi8 = (von_iso(x) for x in p["band80_utc"])
    lo9, hi9 = (von_iso(x) for x in p["band95_utc"])
    if lo8 <= ergebnis_t <= hi8:
        st = "in 80 % band"
    elif lo9 <= ergebnis_t <= hi9:
        st = "in 95 % band"
    else:
        st = "outside"
    return {"stufe": p["stufe"], "status": st, "abweichung_s": round(ergebnis_t - von_iso(p["p50_utc"]))}


def plan(zustand, jetzt):
    """Braucht dieser Lauf den Knoten? (ja/nein, grund)"""
    if zustand.get("ergebnis"):
        return False, "ereignis gewertet, nichts zu tun"
    v = zustand.get("vorschau")
    if not v:
        return True, "noch keine vorschau"
    p50 = von_iso(v["p50_utc"])
    if jetzt >= von_iso(v["band95_utc"][0]) - TAKT_S:
        return True, "ereignis nahe oder vorbei, werten oder letzte stufe"
    st = faellig(zustand, jetzt, p50)
    if st:
        return True, "stufe %s faellig" % st
    return False, "keine stufe faellig"


def rechnen(zustand, daten, jetzt):
    ev = zustand.setdefault("ereignis", {})
    if not ev:
        k, ziel = naechster(daten["virtual_daa"])
        ev.update({"art": "kaspa block reward step", "monat": k, "ziel_daa": ziel,
                   "reward_vorher_sompi": REWARD_SOMPI.get(k - 1), "reward_nachher_sompi": REWARD_SOMPI.get(k),
                   "quelle": QUELLE,
                   "definition": "header time of the first selected chain block with DAA score at or above the target"})
    ziel = ev["ziel_daa"]
    if daten.get("ereignis"):
        e = daten["ereignis"]
        t = e["zeit_ms"] / 1000
        zustand["ergebnis"] = {"zeit_utc": iso(t), "daa": e["daa"], "hash": e["hash"], "gezaehlt_utc": iso(jetzt),
                               "wertung": [werten(t, p) for p in zustand.get("prognosen", [])]}
        return "ereignis gezaehlt"
    if daten["virtual_daa"] >= ziel:
        zustand["ergebnis"] = {"fehler": "ziel erreicht, erster block nicht im fenster des knotens",
                               "gezaehlt_utc": iso(jetzt)}
        return "ereignis ohne block"
    punkte = [(x["zeit_ms"] / 1000, x["daa"]) for x in daten["punkte"]]
    pr = prognose(punkte, ziel)
    zustand["vorschau"] = dict(pr, erstellt_utc=iso(jetzt))
    st = faellig(zustand, jetzt, von_iso(pr["p50_utc"]))
    if not st:
        return "keine stufe faellig, vorschau %s" % pr["p50_utc"]
    eintrag = dict(pr, stufe=st, erstellt_utc=iso(jetzt),
                   vorlauf_s=round(von_iso(pr["p50_utc"]) - jetzt), knoten=daten.get("knoten"))
    zustand.setdefault("prognosen", []).append(eintrag)
    return "stufe %s veroeffentlicht, forecast %s" % (st, pr["p50_utc"])


def feld(d, *namen):
    for n in namen:
        if isinstance(d, dict) and n in d:
            return d[n]
    return None


async def daten_holen(ziel=None):
    """Punkte der ausgewaehlten Kette vom Knoten im Runner. Gibt nur Zahlen
    und Block-Hashes aus."""
    import kaspa  # noqa: WPS433
    c = kaspa.RpcClient(url=URL, network_id="mainnet")
    await asyncio.wait_for(c.connect(), 30)
    try:
        info = await c.get_server_info()
        dag = await c.get_block_dag_info()
        virt = int(feld(dag, "virtualDaaScore", "virtual_daa_score"))
        pp = feld(dag, "pruningPointHash", "pruning_point_hash")
        if ziel is None:
            ziel = naechster(virt)[1]

        async def kopf(h):
            b = await c.get_block({"hash": h, "includeTransactions": False})
            k = feld(feld(b, "block") or b, "header") or {}
            return {"hash": h, "zeit_ms": int(feld(k, "timestamp")), "daa": int(feld(k, "daaScore", "daa_score"))}

        sink = feld(await c.get_sink(), "sink")
        # die antwort ist begrenzt (probe 16.11.2026: nur etwa 28 min ab dem
        # pruning-punkt), deshalb seitenweise bis zum sink
        kette, start = [pp], pp
        for _ in range(5000):
            vc = await c.get_virtual_chain_from_block({"startHash": start, "includeAcceptedTransactionIds": False})
            neu = list(feld(vc, "addedChainBlockHashes", "added_chain_block_hashes") or [])
            if not neu:
                break
            kette += neu
            start = neu[-1]
            if start == sink:
                break
        schritt = max(1, len(kette) // PUNKTE)
        wahl = kette[::schritt]
        if wahl[-1] != kette[-1]:
            wahl.append(kette[-1])
        if sink and wahl[-1] != sink:
            wahl.append(sink)
        punkte = [await kopf(h) for h in wahl]
        aus = {"abruf_utc": iso(time.time()), "virtual_daa": virt, "ziel_daa": ziel,
               "knoten": {"version": feld(info, "serverVersion", "server_version"),
                          "synchron": bool(feld(info, "isSynced", "is_synced")), "kettenbloecke": len(kette),
                          "kette_bis_sink": kette[-1] == sink},
               "punkte": punkte}
        if virt >= ziel and punkte and punkte[0]["daa"] < ziel:
            lo, hi = 0, len(kette) - 1     # erster kettenblock mit daa >= ziel, die kette steigt im daa
            while lo < hi:
                mid = (lo + hi) // 2
                if (await kopf(kette[mid]))["daa"] >= ziel:
                    hi = mid
                else:
                    lo = mid + 1
            aus["ereignis"] = await kopf(kette[lo])
        return aus
    finally:
        await c.disconnect()


def lade(pfad):
    if pfad and os.path.exists(pfad):
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    return {}


def schreibe(pfad, d):
    os.makedirs(os.path.dirname(pfad) or ".", exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")


def selbsttest():
    n = 0

    def ok(c, was):
        nonlocal n
        n += 1
        print(("  ok    " if c else "  FEHL  ") + was)
        if not c:
            raise SystemExit("selbsttest fehlgeschlagen")

    ok(DEFLATION == 15_519_600, "deflation daa score")
    for k in (36, 50, 54, 55, 56):
        d = schritt_daa(k)
        ok(monat(d) == k and monat(d - 1) == k - 1, "monat %d beginnt bei %d" % (k, d))
    ok(schritt_daa(50) == 478_611_000, "monat 50 bei 478.611.000")
    ok(schritt_daa(55) == 610_101_000, "monat 55 bei 610.101.000")
    ok(REWARD_SOMPI[50] == 244_997_148, "monat 50 gibt 2,44997148 kas, schritt vom 5.7.2026")
    ok(naechster(600_000_000) == (55, 610_101_000), "naechster schritt ab 600 mio")
    ok(quantil([1, 2, 3, 4], 0.5) == 2.5 and quantil([5], 0.9) == 5, "quantil linear")
    # ideale kette, 10 daa je s mit rauschen: prognose um die erwartete zeit
    rnd = random.Random(1)
    t, d, pk = 1_700_000_000.0, 600_000_000, []
    for _ in range(400):
        pk.append((t, d))
        dt_ = 360 + rnd.uniform(-30, 30)
        t += dt_
        d += int(dt_ * rnd.uniform(9.0, 11.0))
    ziel = d + 10 * 86400 * 10
    pr = prognose(pk, ziel, ziehungen=600)
    erwartet = pk[-1][0] + (ziel - pk[-1][1]) / (sum(b for _, b in intervalle(pk)) / sum(a for a, _ in intervalle(pk)))
    ok(abs(von_iso(pr["p50_utc"]) - erwartet) < 120, "median nahe der erwarteten zeit")
    lo9, hi9 = (von_iso(x) for x in pr["band95_utc"])
    lo8, hi8 = (von_iso(x) for x in pr["band80_utc"])
    ok(lo9 <= lo8 <= von_iso(pr["p50_utc"]) <= hi8 <= hi9, "bander geschachtelt")
    ok(prognose(pk, ziel, ziehungen=600) == pr, "feste saat, gleiche zahlen")
    # stufen
    p50 = 2_000_000_000.0
    z = {"prognosen": []}
    ok(faellig(z, p50 - 15 * 86400, p50) is None, "15 tage vorher keine stufe")
    ok(faellig(z, p50 - 14 * 86400 - 3600, p50) == "14d", "14d 1 h vor ihrem zeitpunkt")
    ok(faellig(z, p50 - 10 * 86400, p50) == "14d", "14d verspaetet, vorlauf 10 tage")
    z["prognosen"].append({"stufe": "14d"})
    ok(faellig(z, p50 - 10 * 86400, p50) is None, "14d erledigt, 7d noch nicht")
    ok(faellig(z, p50 - 30 * 3600, p50) == "24h", "30 h vorher die 24h-stufe, 7d und 2d uebersprungen")
    ok(faellig(z, p50 + 60, p50) is None, "nach dem median keine stufe")
    # wertung
    pp = {"stufe": "7d", "p50_utc": iso(p50), "band80_utc": [iso(p50 - 600), iso(p50 + 600)],
          "band95_utc": [iso(p50 - 1800), iso(p50 + 1800)]}
    ok(werten(p50 + 300, pp)["status"] == "in 80 % band", "wertung im 80 %-band")
    ok(werten(p50 - 1000, pp)["status"] == "in 95 % band", "wertung im 95 %-band")
    ok(werten(p50 + 4000, pp) == {"stufe": "7d", "status": "outside", "abweichung_s": 4000}, "wertung ausserhalb")
    # plan und rechnen
    ok(plan({}, p50)[0] is True, "ohne vorschau braucht der lauf den knoten")
    zz = {"vorschau": {"p50_utc": iso(p50), "band95_utc": [iso(p50 - 1800), iso(p50 + 1800)]}, "prognosen": []}
    ok(plan(zz, p50 - 20 * 86400)[0] is False, "20 tage vorher kein knoten")
    ok(plan(zz, p50 - 14 * 86400 - 3600)[0] is True, "zur 14d-stufe der knoten")
    daten = {"virtual_daa": pk[-1][1], "punkte": [{"zeit_ms": a * 1000, "daa": b} for a, b in pk]}
    z2 = {"ereignis": {"ziel_daa": ziel}}
    jetzt = pk[-1][0] + 60
    msg = rechnen(z2, daten, jetzt)
    ok(msg.startswith("stufe 14d") and len(z2["prognosen"]) == 1, "10 tage vorher die 14d-stufe verspaetet")
    ok(abs(z2["prognosen"][0]["vorlauf_s"] - 10 * 86400) < 600, "vorlauf steht dabei, etwa 10 tage")
    ok(rechnen(z2, daten, jetzt + 60).startswith("keine stufe"), "zweiter lauf ohne neue stufe")
    t_ev = von_iso(z2["prognosen"][0]["p50_utc"]) + 100
    daten_ev = dict(daten, virtual_daa=ziel + 5, ereignis={"zeit_ms": t_ev * 1000, "daa": ziel, "hash": "00" * 32})
    rechnen(z2, daten_ev, t_ev + 3600)
    ok(z2["ergebnis"]["wertung"][0]["status"] == "in 80 % band" and z2["ergebnis"]["wertung"][0]["abweichung_s"] == 100,
       "ereignis gezaehlt und gewertet")
    ok(plan(z2, t_ev + 7200) == (False, "ereignis gewertet, nichts zu tun"), "nach der wertung kein lauf mehr")
    print("%d pruefungen, alle bestanden" % n)


def main():
    if sys.argv[1:] == ["--selbsttest"]:
        return selbsttest()
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("plan")
    a1.add_argument("--zustand", required=True)
    a2 = sub.add_parser("daten")
    a2.add_argument("--aus", required=True)
    a2.add_argument("--zustand")
    a3 = sub.add_parser("rechnen")
    a3.add_argument("--zustand", required=True)
    a3.add_argument("--punkte", required=True)
    a = ap.parse_args()
    jetzt = time.time()
    if a.cmd == "plan":
        brauche, grund = plan(lade(a.zustand), jetzt)
        print(grund)
        gh = os.environ.get("GITHUB_OUTPUT")
        if gh:
            with open(gh, "a") as f:
                f.write("knoten=%s\n" % ("ja" if brauche else "nein"))
        return
    if a.cmd == "daten":
        ziel = (lade(a.zustand).get("ereignis") or {}).get("ziel_daa")
        d = asyncio.run(daten_holen(ziel))
        schreibe(a.aus, d)
        print(json.dumps({"virtual_daa": d["virtual_daa"], "ziel_daa": d["ziel_daa"], "punkte": len(d["punkte"]),
                          "ereignis": bool(d.get("ereignis"))}))
        return
    z = lade(a.zustand)
    msg = rechnen(z, lade(a.punkte), jetzt)
    schreibe(a.zustand, z)
    print(msg)


if __name__ == "__main__":
    main()
