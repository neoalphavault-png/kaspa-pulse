#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tn10_gebuehren.py, Gebuehrenleser fuer TN10 (Ben, 13.10.2026).

Liest jede Minute zur Sekunde 0 GetFeeEstimate an einem TN10-Knoten und
schreibt je Minute eine Zeile. Zwei Prozesse, je einer pro Knoten, zwei
voneinander unabhaengige Knoten ueber den Resolver (k2 meidet den Knoten von
k1). Nur lesend.

WERTE, ALLE IN SOMPI/GRAMM, SO WIE DER KNOTEN SIE MELDET
    priority   priorityBucket.feerate
    normal     normalBuckets[0].feerate, der erste (hoechste) Normal-Eimer
    low        lowBuckets[0].feerate, der erste (hoechste) Niedrig-Eimer
Es wird nichts gerundet, aufgefuellt oder geglaettet. Fehlt ein Wert, bleibt
das Feld leer und status sagt warum.

AUSGABE
    <out>/gebuehren-k1.csv, gebuehren-k2.csv
        utc_minute, priority, normal, low, status
        utc_minute ist die UTC-Sekunde der Lesung, im Normalfall hh:mm:00.
    <out>/gebuehren-nebeneinander.csv
        je Minute des Fensters beide Knoten nebeneinander, auch Minuten ohne
        Zeile, dann mit Grund.
    <out>/gebuehren-k1.json, -k2.json
        Kennung des Knotens (kurzer Hash der p2p-Id), Version, Verbindungen.
Keine IP, kein Hostname, keine p2p-Id in Dateien oder Log.

    python3 scripts/tn10_gebuehren.py --plan --start DATEI --dauer S
    python3 scripts/tn10_gebuehren.py --lesen --von S --bis S --rolle k1 --partner P --out DIR
    python3 scripts/tn10_gebuehren.py --nebeneinander DIR --von S --bis S
    python3 scripts/tn10_gebuehren.py --selbsttest
"""

import argparse
import asyncio
import csv
import datetime as dt
import hashlib
import io
import json
import os
import sys
import time

NETZ = "testnet-10"
SPALTEN = ["utc_minute", "priority", "normal", "low", "status"]
WARTE_JOB_S = 20400       # ein wartejob schlaeft hoechstens so lange
WARTE_JOBS = 12
VORLAUF_S = 240           # so viel vor dem start verbinden
MAX_DAUER = 6 * 3600 - 1800
ABFRAGE_TIMEOUT_S = 15
SPAET_S = 5               # spaeter als das gilt eine lesung als spaet, steht im status


def iso(s):
    return dt.datetime.fromtimestamp(s, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def startzeit(text):
    t = " ".join(z.split("#", 1)[0].strip() for z in (text or "").splitlines()).strip()
    if not t:
        return None
    return int(dt.datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp())


def plan(dauer, jetzt, start):
    """t0 auf die volle minute, ende, los = t0 - VORLAUF_S, wn = noetige wartejobs."""
    if not 60 <= dauer <= MAX_DAUER:
        raise ValueError("dauer %d ausserhalb 60 bis %d" % (dauer, MAX_DAUER))
    if start is None:
        raise ValueError("keine startzeit")
    t0 = -(-int(start) // 60) * 60
    if t0 < int(jetzt) + 60:
        raise ValueError("startzeit liegt zu nah oder in der vergangenheit")
    rest = max(0, t0 - VORLAUF_S - int(jetzt))
    wn = -(-rest // WARTE_JOB_S) if rest > 60 else 0
    if wn > WARTE_JOBS:
        raise ValueError("startzeit zu weit weg, hoechstens %d h warten" % (WARTE_JOBS * WARTE_JOB_S // 3600))
    return {"t0": t0, "ende": t0 + dauer, "los": t0 - VORLAUF_S, "wn": wn}


def feld(d, *namen):
    for n in namen:
        if isinstance(d, dict) and n in d:
            return d[n]
        if hasattr(d, n):
            return getattr(d, n)
    return None


def ohne_adressen(text):
    """fehlertext ohne url, hostname oder ip, hoechstens 120 zeichen."""
    import re
    t = re.sub(r"[a-z]+://\S+", "<url>", str(text))
    t = re.sub(r"\b\d{1,3}(\.\d{1,3}){3}(:\d+)?\b", "<ip>", t)
    t = re.sub(r"\[?[0-9a-fA-F:]{6,}\]?(:\d+)?", "<ip>", t)
    t = re.sub(r"\b[\w-]+(\.[\w-]+)+\.[a-z]{2,}\b", "<host>", t)
    return t.strip()[:120]


def kennung(p2p):
    return hashlib.sha256(str(p2p).encode()).hexdigest()[:10] if p2p else ""


def werte(fe):
    """(priority, normal, low, fehlend) aus der antwort von get_fee_estimate."""
    est = feld(fe, "estimate") or fe
    pb = feld(est, "priorityBucket") or {}
    nb = feld(est, "normalBuckets") or []
    lb = feld(est, "lowBuckets") or []
    p = feld(pb, "feerate")
    n = feld(nb[0], "feerate") if nb else None
    lo = feld(lb[0], "feerate") if lb else None
    fehlend = [name for name, w in (("priority", p), ("normal", n), ("low", lo)) if w is None]
    return p, n, lo, fehlend


def zahl_text(x):
    return "" if x is None else repr(x) if isinstance(x, float) else str(x)


def csv_text(zeilen, spalten):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=spalten, lineterminator="\n")
    w.writeheader()
    for z in zeilen:
        w.writerow({k: z.get(k, "") for k in spalten})
    return buf.getvalue()


# ---------------------------------------------------------------- lesen

async def lesen(von, bis, rolle, partner, out):
    import kaspa                                         # noqa: WPS433
    zeilen, meta = [], {"rolle": rolle, "verbindungen": [], "meldungen": []}
    rpc, p2p = None, ""

    andere_rolle = "k2" if rolle == "k1" else "k1"
    je_minute = {}

    def meiden():
        """p2p-id des anderen prozesses, beide meiden sich gegenseitig."""
        if not partner:
            return ""
        try:
            with open("%s.%s" % (partner, andere_rolle), encoding="utf-8") as fh:
                return json.load(fh).get("p2p", "")
        except (OSError, ValueError):
            return ""

    async def verbinde():
        nonlocal rpc, p2p
        for versuch in range(6):
            andere = meiden()
            url = await asyncio.wait_for(kaspa.Resolver().get_url("borsh", kaspa.NetworkId(NETZ)), ABFRAGE_TIMEOUT_S)
            neu = kaspa.RpcClient(url=url, network_id=NETZ)
            await asyncio.wait_for(neu.connect(), ABFRAGE_TIMEOUT_S)
            info = await asyncio.wait_for(neu.get_info(), ABFRAGE_TIMEOUT_S)
            pid = str(feld(info, "p2pId") or "")
            if andere and pid == andere and versuch < 5:
                await neu.disconnect()
                await asyncio.sleep(2)
                continue
            rpc, p2p = neu, pid
            meta["verbindungen"].append({"zeit": iso(int(time.time())), "kennung": kennung(pid),
                                         "version": str(feld(info, "serverVersion") or ""),
                                         "gleich_wie_partner": bool(andere and pid == andere)})
            if partner:
                eigene = "%s.%s" % (partner, rolle)
                with open(eigene + ".neu", "w", encoding="utf-8") as fh:
                    json.dump({"p2p": pid}, fh)
                os.replace(eigene + ".neu", eigene)
            return
        raise RuntimeError("kein knoten")

    async def trennen():
        nonlocal rpc
        try:
            if rpc is not None:
                await rpc.disconnect()
        except Exception:                                # noqa: BLE001
            pass
        rpc = None

    t0 = -(-int(von) // 60) * 60
    # vor dem start verbinden, bei k2 erst wenn k1 seinen knoten geschrieben hat
    if rolle == "k2" and partner:
        for _ in range(90):
            if meiden():
                break
            await asyncio.sleep(1)
    async def nachverbinden(bis_s):
        """verbinden versuchen, solange vor bis_s noch zeit ist, alle 10 s."""
        while rpc is None and time.time() < bis_s - 5:
            try:
                await asyncio.wait_for(verbinde(), bis_s - time.time() - 2)
            except Exception as exc:                     # noqa: BLE001
                meta["meldungen"].append("%s verbinden: %s" % (iso(int(time.time())), type(exc).__name__))
                await asyncio.sleep(10)

    await nachverbinden(t0)
    m = t0
    while m < bis:
        rest = m - time.time()
        if rest > 0:
            await asyncio.sleep(rest)
        elif rest < -50:                                 # minute verpasst, ehrlich als fehlend schreiben
            zeilen.append({"utc_minute": iso(m), "status": "fehlt: minute verpasst"})
            m += 60
            continue
        grund = ""
        if rpc is None:
            try:
                await verbinde()
            except Exception as exc:                     # noqa: BLE001
                grund = "fehlt: kein knoten, verbinden gescheitert (%s)" % type(exc).__name__
        versuch2 = ""
        if not grund:
            try:
                try:
                    fe = await asyncio.wait_for(rpc.get_fee_estimate(), ABFRAGE_TIMEOUT_S)
                except Exception as exc1:                # noqa: BLE001
                    # einmal neu verbinden und in derselben minute noch einmal lesen
                    versuch2 = type(exc1).__name__
                    meta["meldungen"].append("%s erster versuch %s: %s" % (
                        iso(m), versuch2, ohne_adressen(exc1)))
                    await trennen()
                    await nachverbinden(m + 45)
                    if rpc is None:
                        raise RuntimeError("kein knoten fuer den zweiten versuch")
                    fe = await asyncio.wait_for(rpc.get_fee_estimate(), ABFRAGE_TIMEOUT_S)
                gelesen = int(time.time())
                p, n, lo, fehlend = werte(fe)
                st = "ok" if not fehlend else "fehlt: " + ", ".join(fehlend) + " nicht in der antwort"
                if versuch2:
                    st += ", zweiter versuch nach %s" % versuch2
                if gelesen - m > SPAET_S:
                    st += ", spaet %d s" % (gelesen - m)
                try:
                    info = await asyncio.wait_for(rpc.get_info(), ABFRAGE_TIMEOUT_S)
                    if feld(info, "isSynced") is False:
                        st += ", knoten nicht synchron"
                except Exception:                        # noqa: BLE001
                    st += ", synchron nicht gelesen"
                zeilen.append({"utc_minute": iso(gelesen), "priority": zahl_text(p), "normal": zahl_text(n),
                               "low": zahl_text(lo), "status": st})
                je_minute[iso(m)[:16]] = kennung(p2p)
            except Exception as exc:                     # noqa: BLE001
                grund = "fehlt: get_fee_estimate %s%s" % (type(exc).__name__, ", auch im zweiten versuch" if versuch2 else "")
                meta["meldungen"].append("%s %s: %s" % (iso(m), type(exc).__name__, ohne_adressen(exc)))
                await trennen()
        if grund:
            zeilen.append({"utc_minute": iso(m), "status": grund})
            meta["meldungen"].append("%s %s" % (iso(m), grund))
        m += 60
        if m < bis:
            await nachverbinden(m)                       # luecke vor der naechsten sekunde 0 nutzen
    await trennen()
    meta["kennung"] = kennung(p2p)
    meta["knoten_je_minute"] = je_minute
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "gebuehren-%s.csv" % rolle), "w", encoding="utf-8") as fh:
        fh.write(csv_text(zeilen, SPALTEN))
    with open(os.path.join(out, "gebuehren-%s.json" % rolle), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    ok = sum(1 for z in zeilen if z["status"].startswith("ok"))
    print("%s kennung %s minuten %d, mit werten %d, ohne %d, verbindungen %d" % (
        rolle, meta["kennung"] or "-", len(zeilen), ok, len(zeilen) - ok, len(meta["verbindungen"])))
    return 0 if zeilen else 1


# ---------------------------------------------------------------- nebeneinander

def minute_von(text):
    return text[:16] if text else ""


def nebeneinander(ordner, von, bis):
    t0 = -(-int(von) // 60) * 60
    je = {}
    for r in ("k1", "k2"):
        pfad = os.path.join(ordner, "gebuehren-%s.csv" % r)
        zeilen = {}
        if os.path.exists(pfad):
            with open(pfad, encoding="utf-8") as fh:
                for z in csv.DictReader(fh):
                    zeilen.setdefault(minute_von(z["utc_minute"]), z)
        je[r] = (os.path.exists(pfad), zeilen)
    knoten = {}
    for r in ("k1", "k2"):
        try:
            with open(os.path.join(ordner, "gebuehren-%s.json" % r), encoding="utf-8") as fh:
                knoten[r] = json.load(fh).get("knoten_je_minute", {})
        except (OSError, ValueError):
            knoten[r] = {}
    spalten = (["minute_utc"] + ["%s_%s" % (r, s) for r in ("k1", "k2") for s in SPALTEN]
               + ["k1_knoten", "k2_knoten", "gleicher_knoten"])
    aus = []
    m = t0
    while m < bis:
        key = iso(m)[:16]
        z = {"minute_utc": key + "Z"}
        for r in ("k1", "k2"):
            da, zeilen = je[r]
            q = zeilen.get(key)
            if q is None:
                z["%s_status" % r] = "fehlt: keine zeile" if da else "fehlt: keine datei von %s" % r
            else:
                for s in SPALTEN:
                    z["%s_%s" % (r, s)] = q.get(s, "")
            z["%s_knoten" % r] = knoten[r].get(key, "")
        z["gleicher_knoten"] = ("ja" if z["k1_knoten"] and z["k1_knoten"] == z["k2_knoten"]
                                else "nein" if z["k1_knoten"] and z["k2_knoten"] else "")
        aus.append(z)
        m += 60
    with open(os.path.join(ordner, "gebuehren-nebeneinander.csv"), "w", encoding="utf-8") as fh:
        fh.write(csv_text(aus, spalten))
    beide = sum(1 for z in aus if z.get("k1_status", "").startswith("ok") and z.get("k2_status", "").startswith("ok"))
    gleich = sum(1 for z in aus if z.get("gleicher_knoten") == "ja")
    print("nebeneinander: minuten %d, beide mit werten %d, davon auf demselben knoten %d" % (len(aus), beide, gleich))
    return aus


# ---------------------------------------------------------------- selbsttest

def selbsttest():
    import tempfile
    fehler = 0

    def ok(name, wahr):
        nonlocal fehler
        if not wahr:
            fehler += 1
        print(("ok    " if wahr else "FEHLER"), name)

    jetzt = int(dt.datetime(2026, 10, 13, 12, 0, tzinfo=dt.timezone.utc).timestamp())
    s17 = startzeit("# kommentar\n2026-10-17T13:30:00Z\n")
    ok("startzeit liest iso und ueberspringt kommentar", iso(s17) == "2026-10-17T13:30:00Z")
    ok("zu weit weg wird abgelehnt", _wirft(lambda: plan(10800, jetzt, s17)))
    p = plan(10800, int(dt.datetime(2026, 10, 16, 14, 0, tzinfo=dt.timezone.utc).timestamp()), s17)
    ok("plan sa 13:30 ab fr 14:00, ende 16:30", iso(p["t0"]) == "2026-10-17T13:30:00Z"
       and iso(p["ende"]) == "2026-10-17T16:30:00Z" and p["wn"] == 5)
    ok("vergangenheit abgelehnt", _wirft(lambda: plan(1800, jetzt, jetzt - 600)))
    ok("startzeit wird auf die volle minute gehoben", iso(plan(1800, jetzt, jetzt + 3601)["t0"]) == "2026-10-13T13:01:00Z")
    fe = {"estimate": {"priorityBucket": {"feerate": 1.0, "estimatedSeconds": 0.2},
                       "normalBuckets": [{"feerate": 1.0}, {"feerate": 0.9}],
                       "lowBuckets": [{"feerate": 1.0}]}}
    ok("werte aus der antwort", werte(fe) == (1.0, 1.0, 1.0, []))
    ok("fehlende eimer werden benannt", werte({"priorityBucket": {"feerate": 2}})[3] == ["normal", "low"])
    ok("zahl ungerundet", zahl_text(1.0000123) == "1.0000123" and zahl_text(None) == "")
    # beispieladressen erst zur laufzeit, damit im quelltext keine steht
    ok("fehlertext ohne url, ip und host", ohne_adressen(
        "Unable to connect to wss://" + ".".join(["node", "example", "net"]) + ":17210/x at "
        + ".".join(["10", "1", "2", "3"]) + ":16110 or " + ".".join(["abc", "kaspa", "red"])) ==
        "Unable to connect to <url> at <ip> or <host>")
    ok("kennung kurz und nicht die id", len(kennung("abc")) == 10 and kennung("abc") != "abc")
    with tempfile.TemporaryDirectory() as d:
        t0 = int(dt.datetime(2026, 10, 16, 13, 30, tzinfo=dt.timezone.utc).timestamp())
        with open(os.path.join(d, "gebuehren-k1.csv"), "w", encoding="utf-8") as fh:
            fh.write(csv_text([{"utc_minute": "2026-10-16T13:30:00Z", "priority": "1.0", "normal": "1.0",
                                "low": "1.0", "status": "ok"},
                               {"utc_minute": "2026-10-16T13:31:00Z", "status": "fehlt: get_fee_estimate Exception"}],
                              SPALTEN))
        with open(os.path.join(d, "gebuehren-k1.json"), "w", encoding="utf-8") as fh:
            json.dump({"knoten_je_minute": {"2026-10-16T13:30": "aaaa"}}, fh)
        with open(os.path.join(d, "gebuehren-k2.json"), "w", encoding="utf-8") as fh:
            json.dump({"knoten_je_minute": {"2026-10-16T13:30": "aaaa"}}, fh)
        aus = nebeneinander(d, t0, t0 + 180)
        ok("derselbe knoten wird markiert", aus[0]["gleicher_knoten"] == "ja" and aus[1]["gleicher_knoten"] == "")
        ok("drei minuten im fenster", len(aus) == 3)
        ok("k1 wert uebernommen", aus[0]["k1_normal"] == "1.0")
        ok("k1 grund uebernommen, nichts aufgefuellt",
           aus[1]["k1_status"].startswith("fehlt") and aus[1].get("k1_normal", "") == "")
        ok("k1 minute ohne zeile benannt", aus[2]["k1_status"] == "fehlt: keine zeile")
        ok("k2 ohne datei benannt", aus[0]["k2_status"] == "fehlt: keine datei von k2")
    # Bens Regel 15.10.2026: beide rollen lesen eine minute von erfundenen
    # knoten, der erste versuch scheitert mit der adresse im fehlertext. danach
    # steht in dateien und ausgabe nur die zehnstellige kennung, nie host oder ip
    import contextlib
    import types
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from tn10_zaehler import adressfrei, fake_kaspa  # noqa: WPS433
    global time
    fk, echt = fake_kaspa(fehler_bei="get_fee_estimate", nur_einmal=True), time
    alt = sys.modules.get("kaspa")
    versatz = 61 - time.time() % 60                     # die uhr steht 1 s nach einer vollen minute
    sys.modules["kaspa"] = fk
    time = types.SimpleNamespace(time=lambda: echt.time() + versatz)
    puffer = io.StringIO()
    try:
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(puffer):
            m0 = int(time.time()) // 60 * 60
            ordner, partner = os.path.join(d, "out"), os.path.join(d, "partner.json")

            async def beide():
                return await asyncio.gather(lesen(m0, m0 + 60, "k1", partner, ordner),
                                            lesen(m0, m0 + 60, "k2", partner, ordner))
            rc = asyncio.run(beide())
            texte = {n: open(os.path.join(ordner, n), encoding="utf-8").read() for n in sorted(os.listdir(ordner))}
    finally:
        time = echt
        if alt is None:
            sys.modules.pop("kaspa", None)
        else:
            sys.modules["kaspa"] = alt
    metas = [json.loads(texte["gebuehren-%s.json" % r]) for r in ("k1", "k2")]
    alles = "\n".join(list(texte.values()) + [puffer.getvalue()])
    kennungen = [v["kennung"] for m in metas for v in m["verbindungen"]] + \
        [k for m in metas for k in m["knoten_je_minute"].values()]
    ok("lauf gegen erfundene knoten: nur kennung, nie host oder ip in dateien und ausgabe",
       rc == [0, 0] and len(texte) == 4 and fk.zustand["fehler"] == 1 and len(fk.zustand["hosts"]) >= 3
       and adressfrei(alles) and "beispiel" not in alles and len(kennungen) >= 5
       and all(len(k) == 10 and all(c in "0123456789abcdef" for c in k) for k in kennungen)
       and "<url>" in " ".join(metas[0]["meldungen"] + metas[1]["meldungen"])
       and "zweiter versuch" in alles)
    print("selbsttest", fehler, "fehler")
    return fehler


def _wirft(f):
    try:
        f()
    except ValueError:
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--start", default="", help="datei mit der startzeit in utc")
    ap.add_argument("--dauer", type=int, default=0)
    ap.add_argument("--lesen", action="store_true")
    ap.add_argument("--von", type=int, default=0)
    ap.add_argument("--bis", type=int, default=0)
    ap.add_argument("--rolle", choices=["k1", "k2"])
    ap.add_argument("--partner", default="")
    ap.add_argument("--out", default="out/gebuehren")
    ap.add_argument("--nebeneinander", metavar="ORDNER")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args()
    if a.selbsttest:
        sys.exit(1 if selbsttest() else 0)
    if a.plan:
        with open(a.start, encoding="utf-8") as fh:
            p = plan(a.dauer, time.time(), startzeit(fh.read()))
        for k, v in p.items():
            print("%s=%s" % (k, v))
        return
    if a.lesen:
        sys.exit(asyncio.run(lesen(a.von, a.bis, a.rolle, a.partner, a.out)))
    if a.nebeneinander:
        nebeneinander(a.nebeneinander, a.von, a.bis)
        return
    ap.print_help()


if __name__ == "__main__":
    main()
