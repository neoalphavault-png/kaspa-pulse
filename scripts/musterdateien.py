#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""musterdateien.py, zwei CSV fuer Firmengespraeche (Ben, 30.09.2026).

    samples/entity-x-ledger.csv      jede Bewegung der Entity-X-Adresse
    samples/miner-economics.csv      je Tag Hashrate, Reward, neue KAS, Gebuehren

Was drinsteht und wie gezaehlt wird, steht in den METHOD-Dateien daneben.
Die Arbeitsumgebung kommt an api.kaspa.org und kaspalytics.com nicht heran,
deshalb laeuft das Zaehlen im Runner (quellen-probe.yml auf einem
pruefung/-Branch) und druckt jede Zeile ins Log. Aus dem Log baut
--aus die Dateien, Zeichen fuer Zeichen.

    python3 scripts/musterdateien.py --drucken            im runner: zaehlen, drucken
    python3 scripts/musterdateien.py --aus lauf.log       lokal: samples/ schreiben
    python3 scripts/musterdateien.py --selftest

REGELN
  Nur Zahlen aus der Kette (api.kaspa.org), aus Kaspalytics oder aus dem
  Protokoll. Eine Luecke bleibt eine leere Zelle, nichts wird interpoliert.
  Keine Adresse in voller Laenge ausser Entity X selbst.
"""
import argparse
import csv
import datetime as dt
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
ZIEL = os.path.join(REPO, "samples")
API = "https://api.kaspa.org"
UA = "kaspa-pulse-bot (+https://kaspapulse.com)"
EX = "kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a"
SOMPI = 100000000
REIHE_AB = "2023-10-01"          # erster tag der kaspalytics-gebuehrenreihe

LEDGER_SPALTEN = ["datum_utc", "zeit_utc", "richtung", "betrag_kas", "gegenadresse_gekuerzt",
                  "label_laut_explorer", "tx_hash", "stand_danach_kas", "anteil_umlauf_pct"]
MINER_SPALTEN = ["datum_utc", "hashrate_phs", "block_reward_kas", "neue_kas_tag",
                 "gebuehren_kas_tag", "gebuehren_anteil_pct", "naechste_senkung_utc"]

# ------------------------------------------------------------ protokoll
# Der Block-Subsidy nach DAA-Score, wie ihn der Knoten rechnet. Quelle:
# rusty-kaspa v2.1.0 (01b532e), consensus/src/processes/coinbase.rs
# (SUBSIDY_BY_MONTH_TABLE, calc_block_subsidy, subsidy_month) und
# consensus/core/src/config/params.rs (MAINNET_PARAMS). ISC-Lizenz.
# Die Tabelle nennt den Reward je SEKUNDE (= je Block bei 1 BPS) in Sompi.
DEFLATION_DAA = 15778800 - 259200
PRE_DEFLATION_SUBSIDY = 50000000000
CRESCENDO_DAA = 110165000
BPS_VOR, BPS_NACH = 1, 10
SEKUNDEN_JE_MONAT = 2629800
SUBSIDY_JE_MONAT = [
    44000000000, 41530469757, 39199543598, 36999442271, 34922823143, 32962755691,
    31112698372, 29366476791, 27718263097, 26162556530, 24694165062, 23308188075,
    22000000000, 20765234878, 19599771799, 18499721135, 17461411571, 16481377845,
    15556349186, 14683238395, 13859131548, 13081278265, 12347082531, 11654094037,
    11000000000, 10382617439, 9799885899, 9249860567, 8730705785, 8240688922,
    7778174593, 7341619197, 6929565774, 6540639132, 6173541265, 5827047018,
    5500000000, 5191308719, 4899942949, 4624930283, 4365352892, 4120344461,
    3889087296, 3670809598, 3464782887, 3270319566, 3086770632, 2913523509,
    2750000000, 2595654359, 2449971474, 2312465141, 2182676446, 2060172230,
    1944543648, 1835404799, 1732391443, 1635159783, 1543385316, 1456761754,
    1375000000, 1297827179, 1224985737, 1156232570, 1091338223, 1030086115,
    972271824, 917702399, 866195721, 817579891, 771692658, 728380877,
    687500000, 648913589, 612492868, 578116285, 545669111, 515043057,
    486135912, 458851199, 433097860, 408789945, 385846329, 364190438,
    343750000, 324456794, 306246434, 289058142, 272834555, 257521528,
    243067956, 229425599, 216548930, 204394972, 192923164, 182095219,
    171875000, 162228397, 153123217, 144529071, 136417277, 128760764,
    121533978, 114712799, 108274465, 102197486, 96461582, 91047609,
    85937500, 81114198, 76561608, 72264535, 68208638, 64380382,
    60766989, 57356399, 54137232, 51098743, 48230791, 45523804,
    42968750, 40557099, 38280804, 36132267, 34104319, 32190191,
    30383494, 28678199, 27068616, 25549371, 24115395, 22761902,
    21484375, 20278549, 19140402, 18066133, 17052159, 16095095,
    15191747, 14339099, 13534308, 12774685, 12057697, 11380951,
    10742187, 10139274, 9570201, 9033066, 8526079, 8047547,
    7595873, 7169549, 6767154, 6387342, 6028848, 5690475,
    5371093, 5069637, 4785100, 4516533, 4263039, 4023773,
    3797936, 3584774, 3383577, 3193671, 3014424, 2845237,
    2685546, 2534818, 2392550, 2258266, 2131519, 2011886,
    1898968, 1792387, 1691788, 1596835, 1507212, 1422618,
    1342773, 1267409, 1196275, 1129133, 1065759, 1005943,
    949484, 896193, 845894, 798417, 753606, 711309,
    671386, 633704, 598137, 564566, 532879, 502971,
    474742, 448096, 422947, 399208, 376803, 355654,
    335693, 316852, 299068, 282283, 266439, 251485,
    237371, 224048, 211473, 199604, 188401, 177827,
    167846, 158426, 149534, 141141, 133219, 125742,
    118685, 112024, 105736, 99802, 94200, 88913,
    83923, 79213, 74767, 70570, 66609, 62871,
    59342, 56012, 52868, 49901, 47100, 44456,
    41961, 39606, 37383, 35285, 33304, 31435,
    29671, 28006, 26434, 24950, 23550, 22228,
    20980, 19803, 18691, 17642, 16652, 15717,
    14835, 14003, 13217, 12475, 11775, 11114,
    10490, 9901, 9345, 8821, 8326, 7858,
    7417, 7001, 6608, 6237, 5887, 5557,
    5245, 4950, 4672, 4410, 4163, 3929,
    3708, 3500, 3304, 3118, 2943, 2778,
    2622, 2475, 2336, 2205, 2081, 1964,
    1854, 1750, 1652, 1559, 1471, 1389,
    1311, 1237, 1168, 1102, 1040, 982,
    927, 875, 826, 779, 735, 694,
    655, 618, 584, 551, 520, 491,
    463, 437, 413, 389, 367, 347,
    327, 309, 292, 275, 260, 245,
    231, 218, 206, 194, 183, 173,
    163, 154, 146, 137, 130, 122,
    115, 109, 103, 97, 91, 86,
    81, 77, 73, 68, 65, 61,
    57, 54, 51, 48, 45, 43,
    40, 38, 36, 34, 32, 30,
    28, 27, 25, 24, 22, 21,
    20, 19, 18, 17, 16, 15,
    14, 13, 12, 12, 11, 10,
    10, 9, 9, 8, 8, 7,
    7, 6, 6, 6, 5, 5,
    5, 4, 4, 4, 4, 3,
    3, 3, 3, 3, 2, 2,
    2, 2, 2, 2, 2, 1,
    1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 0,
]


def subsidy_sompi(daa):
    """Reward je Block in Sompi bei diesem DAA-Score, wie calc_block_subsidy."""
    if daa < DEFLATION_DAA:
        return PRE_DEFLATION_SUBSIDY
    if daa < CRESCENDO_DAA:
        sek, bps = (daa - DEFLATION_DAA) // BPS_VOR, BPS_VOR
    else:
        sek = (CRESCENDO_DAA - DEFLATION_DAA) // BPS_VOR + (daa - CRESCENDO_DAA) // BPS_NACH
        bps = BPS_NACH
    v = SUBSIDY_JE_MONAT[min(sek // SEKUNDEN_JE_MONAT, len(SUBSIDY_JE_MONAT) - 1)]
    return -(-v // bps)


# ------------------------------------------------------------ werkzeug

def hole(url, versuche=5):
    letzte = None
    for i in range(versuche):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            letzte = exc
            time.sleep(10 if exc.code == 429 else 3 * (i + 1))
        except Exception as exc:                      # noqa: BLE001
            letzte = exc
            time.sleep(3 * (i + 1))
    raise SystemExit("ABBRUCH abruf %s (%s)" % (url, letzte))


def kuerzen(adr):
    """kaspa:qrelgny7…p3ap8m, nie die volle adresse (ausser entity x)."""
    if adr == EX:
        return EX
    return adr[:14] + "\u2026" + adr[-6:]


def emission(a, b):
    """Neue KAS zwischen zwei Zeitpunkten, dieselbe Rechnung wie
    tagesgrafik.neue_kas (Emissionsplan aus number_of_day_data)."""
    import number_of_day_data as nod
    s, t = 0.0, a
    while t < b:
        cur, _, nxt = nod.reward_state(t)
        e = min(b, nxt)
        s += cur * nod.BPS * (e - t)
        t = e
    return s


def utc(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc)


# ------------------------------------------------------------ ledger

def alle_transaktionen():
    txs, vor = [], 0
    for _ in range(200):
        url = (API + "/addresses/%s/full-transactions-page?limit=100"
               "&resolve_previous_outpoints=light" % EX)
        if vor:
            url += "&before=%d" % vor
        seite = hole(url)
        if not seite:
            break
        txs += seite
        aelteste = min(t.get("block_time") or 0 for t in seite)
        if vor and aelteste >= vor:
            break
        vor = aelteste
        time.sleep(0.5)
    return txs


def ledger():
    roh = alle_transaktionen()
    namen = {n["address"]: n["name"] for n in hole(API + "/addresses/names")}
    gesehen, zeilen, pruef = set(), [], {"roh": len(roh), "nicht_akzeptiert": 0, "netto_null": 0,
                                        "doppelt": 0, "unter_1_kas": 0, "mehrere_gegenadressen": 0}
    for t in roh:
        tid = t.get("transaction_id")
        if tid in gesehen:
            pruef["doppelt"] += 1
            continue
        gesehen.add(tid)
        if t.get("is_accepted") is False:
            pruef["nicht_akzeptiert"] += 1
            continue
        rein, raus = 0, 0
        fremd_ein, fremd_aus = {}, {}
        for i in t.get("inputs") or []:
            a = i.get("previous_outpoint_address")
            if a is None:
                raise SystemExit("ABBRUCH eingang ohne adresse in %s" % tid)
            amt = int(i.get("previous_outpoint_amount") or 0)
            if a == EX:
                raus += amt
            else:
                fremd_ein[a] = fremd_ein.get(a, 0) + amt
        for o in t.get("outputs") or []:
            a = o.get("script_public_key_address")
            amt = int(o.get("amount") or 0)
            if a == EX:
                rein += amt
            else:
                fremd_aus[a] = fremd_aus.get(a, 0) + amt
        netto = rein - raus
        if netto == 0:
            pruef["netto_null"] += 1
            continue
        gegen = fremd_ein if netto > 0 else fremd_aus
        haupt = max(gegen, key=gegen.get) if gegen else ""
        if len(gegen) > 1:
            pruef["mehrere_gegenadressen"] += 1
        if abs(netto) < SOMPI:
            pruef["unter_1_kas"] += 1
        zeilen.append({"ms": t.get("block_time") or 0, "tx": tid, "netto": netto, "haupt": haupt,
                       "weitere": max(0, len(gegen) - 1)})
    zeilen.sort(key=lambda z: (z["ms"], z["tx"]))
    jetzt = time.time()
    umlauf_jetzt = int(hole(API + "/info/coinsupply")["circulatingSupply"]) / SOMPI
    stand_api = int(hole(API + "/addresses/%s/balance" % EX)["balance"])
    stand, aus = 0, []
    for z in zeilen:
        stand += z["netto"]
        t = utc(z["ms"])
        umlauf = umlauf_jetzt - emission(t.timestamp(), jetzt)
        gegen = kuerzen(z["haupt"]) if z["haupt"] else ""
        if z["weitere"]:
            gegen += " +%d" % z["weitere"]
        aus.append([t.date().isoformat(), t.strftime("%H:%M:%S"), "in" if z["netto"] > 0 else "out",
                    "%.8f" % (abs(z["netto"]) / SOMPI), gegen, namen.get(z["haupt"], ""), z["tx"],
                    "%.8f" % (stand / SOMPI), "%.4f" % (100 * stand / SOMPI / umlauf)])
    pruef.update({"zeilen": len(aus), "stand_summe_sompi": stand, "stand_api_sompi": stand_api,
                  "differenz_sompi": stand - stand_api, "umlauf_jetzt_kas": umlauf_jetzt,
                  "gezaehlt_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                  "labels_im_verzeichnis": len(namen)})
    return aus, pruef


# ------------------------------------------------------------ miner

def je_sekunde(daa):
    """Reward je Sekunde in Sompi nach Protokoll (je Block mal Nenn-BPS)."""
    return subsidy_sompi(daa) * (BPS_NACH if daa >= CRESCENDO_DAA else BPS_VOR)


def miner():
    """Je UTC-Tag ab REIHE_AB bis gestern.

    Stufen nach Protokoll: eine Monatsstufe gilt ab dem ersten
    Hashrate-Messpunkt, dessen DAA-Score schon im neuen Monat liegt (hoechstens
    rund eine Stunde nach der Stufe). neue KAS je Tag ist der Reward je Sekunde
    nach Protokoll, ueber den UTC-Tag summiert, mit diesen Stufenzeitpunkten.
    Eine Stufe, die noch kein Messpunkt gesehen hat, kommt aus dem Hausplan."""
    import kaspalytics as k
    import number_of_day_data as nod
    hist = hole(API + "/info/hashrate/history")
    pkte = sorted((x["timestamp"] / 1000, x["hashrate_kh"], int(x["daaScore"])) for x in hist)
    je_tag = {}
    for t, h, d in pkte:
        je_tag.setdefault(utc(t * 1000).date().isoformat(), []).append((t, h, d))
    # beobachtete stufen: (zeit des ersten punkts im neuen monat, reward je sekunde danach)
    stufen = [(pkte[0][0], je_sekunde(pkte[0][2]))]
    for (t0, _, d0), (t1, _, d1) in zip(pkte, pkte[1:]):
        if je_sekunde(d1) != je_sekunde(d0) and subsidy_sompi(d1) * 10 != subsidy_sompi(d0) \
                and not (d0 < CRESCENDO_DAA <= d1):
            stufen.append((t1, je_sekunde(d1)))
    letzte_messung = pkte[-1][0]

    def rate_bei(t):
        r = stufen[0][1]
        for ts, rr in stufen:
            if ts <= t:
                r = rr
        return r

    def neu_am_tag(a):
        grenzen = [a] + [ts for ts, _ in stufen if a < ts < a + 86400] + [a + 86400]
        return sum(rate_bei(x) * (y - x) for x, y in zip(grenzen, grenzen[1:])) / SOMPI

    d = k.hole("transactions/accepted/fees/total")
    gebuehr = {}
    for lab, v in zip(d.get("labels") or [], k.reihe(d, "Fees")):
        if v is not None:
            gebuehr[k.stichtag(lab, "fluss").isoformat()] = float(v)
    gestern = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)
    tag = dt.date.fromisoformat(REIHE_AB)
    aus, pruef = [], {"tage": 0, "ohne_hashrate": 0, "ohne_gebuehr": [], "wenige_messpunkte": [],
                      "stufen_beobachtet": [], "plan_stufe_anderer_tag": [],
                      "max_abstand_stufe_zu_vorpunkt_s": 0}
    for (t0, _, d0), (t1, _, d1) in zip(pkte, pkte[1:]):
        if (t1, je_sekunde(d1)) in stufen:
            pruef["max_abstand_stufe_zu_vorpunkt_s"] = max(pruef["max_abstand_stufe_zu_vorpunkt_s"], round(t1 - t0))
    while tag <= gestern:
        ds = tag.isoformat()
        a = dt.datetime.combine(tag, dt.time(), dt.timezone.utc).timestamp()
        tp = je_tag.get(ds, [])
        hr = reward = ""
        if tp:
            hr = "%.3f" % (sum(p[1] for p in tp) / len(tp) / 1e12)
            if len(tp) < 12:
                pruef["wenige_messpunkte"].append((ds, len(tp)))
            reward = "%.8f" % (subsidy_sompi(tp[0][2]) / SOMPI)
        else:
            pruef["ohne_hashrate"] += 1
        neu = neu_am_tag(a)
        fee = gebuehr.get(ds)
        if fee is None:
            pruef["ohne_gebuehr"].append(ds)
        kommend = [ts for ts, _ in stufen[1:] if ts > a]
        if kommend:
            nxt = dt.datetime.fromtimestamp(kommend[0], dt.timezone.utc)
        else:
            nxt = dt.datetime.fromtimestamp(nod.reward_state(max(a, letzte_messung))[2], dt.timezone.utc)
        plan = dt.datetime.fromtimestamp(nod.reward_state(a)[2], dt.timezone.utc)
        if plan.date() != nxt.date():
            pruef["plan_stufe_anderer_tag"].append((ds, plan.strftime("%Y-%m-%d %H:%M"),
                                                    nxt.strftime("%Y-%m-%d %H:%M")))
        aus.append([ds, hr, reward, "%.2f" % neu, "" if fee is None else "%.8f" % fee,
                    "" if fee is None else "%.4f" % (100 * fee / (fee + neu)),
                    nxt.strftime("%Y-%m-%d %H:%M")])
        pruef["tage"] += 1
        tag += dt.timedelta(days=1)
    pruef["stufen_beobachtet"] = [dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
                                  for ts, _ in stufen[1:] if ts >= a - 86400 * 1200]
    pruef["gezaehlt_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    pruef["hashrate_punkte"] = len(hist)
    pruef["gebuehren_tage"] = len(gebuehr)
    return aus, pruef


# ------------------------------------------------------------ ein- und ausgabe

def drucken():
    zeilen, pruef = ledger()
    print("PRUEFUNG ledger " + json.dumps(pruef, ensure_ascii=False))
    for z in zeilen:
        print("LEDGER " + json.dumps(z, ensure_ascii=False))
    zeilen, pruef = miner()
    print("PRUEFUNG miner " + json.dumps(pruef, ensure_ascii=False))
    for z in zeilen:
        print("MINER " + json.dumps(z, ensure_ascii=False))
    return 0


def csv_text(spalten, zeilen):
    f = io.StringIO()
    w = csv.writer(f, lineterminator="\n")
    w.writerow(spalten)
    w.writerows(zeilen)
    return f.getvalue()


def aus_log(pfad, ziel=ZIEL):
    led, mi = [], []
    for zeile in open(pfad, encoding="utf-8"):
        for marke, liste in (("LEDGER ", led), ("MINER ", mi)):
            i = zeile.find(marke)
            if i >= 0 and zeile[i:].startswith(marke + "["):
                liste.append(json.loads(zeile[i + len(marke):]))
    if not led or not mi:
        raise SystemExit("ABBRUCH im log fehlen ledger- oder miner-zeilen")
    os.makedirs(ziel, exist_ok=True)
    for name, spalten, zeilen in (("entity-x-ledger.csv", LEDGER_SPALTEN, led),
                                  ("miner-economics.csv", MINER_SPALTEN, mi)):
        for z in zeilen:
            if len(z) != len(spalten):
                raise SystemExit("ABBRUCH %s, zeile mit %d statt %d spalten" % (name, len(z), len(spalten)))
        with open(os.path.join(ziel, name), "w", encoding="utf-8") as fh:
            fh.write(csv_text(spalten, zeilen))
        print("%s, %d zeilen" % (name, len(zeilen)))
    return 0


def selftest():
    fehler = 0

    def ok(name, bed):
        nonlocal fehler
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        fehler += 0 if bed else 1
    ok("tabelle hat 426 monate", len(SUBSIDY_JE_MONAT) == 426)
    ok("erster monat 440 KAS je sekunde", SUBSIDY_JE_MONAT[0] == 44000000000)
    ok("vor der deflation 500 KAS", subsidy_sompi(DEFLATION_DAA - 1) == 50000000000)
    ok("vor crescendo je block = je sekunde", subsidy_sompi(CRESCENDO_DAA - 1) == 5827047018)
    ok("nach crescendo ein zehntel, aufgerundet", subsidy_sompi(CRESCENDO_DAA) == 582704702)
    ok("30.09.2026, daa 553.021.575, 2.18267645 KAS wie der hausplan",
       subsidy_sompi(553021575) == 218267645)
    import number_of_day_data as nod
    ok("hausplan und protokoll am 29.09.2026 gleich (unter 0,0001%)",
       abs(nod.reward_state(dt.datetime(2026, 9, 29, 22, tzinfo=dt.timezone.utc).timestamp())[0]
           - 2.18267645) < 2.2e-6)
    ok("gekuerzt, nie voll", kuerzen("kaspa:qrelgny7sr3vahq69yykxx36m65gvmhryxrlwngfzgu8xkdslum2yxjp3ap8m")
       == "kaspa:qrelgny7\u2026p3ap8m")
    ok("entity x bleibt voll", kuerzen(EX) == EX)
    ok("csv mit komma im label wird gequotet", '"a, b"' in csv_text(["x"], [["a, b"]]))
    print("%d fehler" % fehler)
    return 1 if fehler else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--drucken", action="store_true")
    ap.add_argument("--aus")
    ap.add_argument("--ziel", default=ZIEL)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.drucken:
        return drucken()
    if a.aus:
        return aus_log(a.aus, a.ziel)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
