#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tn10_contention.py, Covenant-Contention je Minute (Ben, 21.10.2026).

STP-Lauf Do 29.10.2026 18:00 UTC, Phase "covenant contention": mehrere Sender
geben denselben Covenant-Output mit steigender Rate aus. Diese Datei setzt
unsere Nachzaehlung (tn10_nachzaehlung.py mit --covenant-datei, zwei Knoten)
und STPs Sender-Logs zu einer Zeile je Minute zusammen. Sie fragt keinen
Knoten und sendet nichts.

JE MINUTE
    phase                 grundlast_vor, fenster, grundlast_nach (je 30 min)
    cov_angenommen        angenommene Ausgaben des Covenants, zur Blockzeit des
                          annehmenden Kettenblocks (unsere Zaehlung, k1, k2 gleich)
    cov_in_bloecken       Ausgaben in Bloecken nach dem ersten Block
    cov_nie_angenommen    davon nie angenommen (Konkurrenten im DAG)
    abgelehnt_konflikt    wegen Konflikt abgelehnte Ausgaben laut STPs
                          Sender-Logs, alle Seiten zusammen (source STP)
    bis_block_ms_median, _p90, _n
                          erster Block minus Submit-Zeit in ms, nur fuer
                          angenommene Ausgaben mit bekannter Submit-Zeit
                          (Submit-Zeiten aus STPs Logs, source STP)
    bis_annahme_ms_median annehmender Kettenblock minus Submit-Zeit
    sender_luecke         ja, nein oder unbekannt, mit Grund
    miner_wechsel         ja, nein oder unbekannt, mit Grund
    gueltig               1 nur fuer eine volle Minute (beide Knoten voll und
                          gleich) ohne Sender-Luecke und ohne Miner-Wechsel

Die Covenant-ID steht nirgends, nur ihr Hash in der Zieldatei der Zaehlung.
Blockzeit ist die Zeit im Blockkopf (Uhr des Miners), Submit-Zeit die Uhr
des Senders; der Uhrversatz aus STPs ntp.csv steht in der Zusammenfassung.

    python3 scripts/tn10_contention.py --zaehlung DIR --stp DIR [--submit CSV] \\
        --fenster 2026-10-29T18:00:00Z 2026-10-29T19:00:00Z --out DIR
    python3 scripts/tn10_contention.py --selbsttest
"""
import argparse
import csv
import datetime as dt
import glob
import io
import json
import os
import statistics
import sys
import tempfile

GRUNDLAST_MIN = 30
KONFLIKT = ("double_spend", "double-spend", "doublespend", "conflict")
LUECKE_EREIGNIS = ("gap", "pause", "paused", "stall", "freeze", "node-dead", "sender-stop", "stop", "relaunch")
SPALTEN = ["minute_utc", "phase", "voll", "knoten_gleich", "cov_angenommen", "cov_in_bloecken",
           "cov_nie_angenommen", "abgelehnt_konflikt", "bis_block_ms_median", "bis_block_ms_p90", "bis_block_n",
           "bis_annahme_ms_median", "sender_luecke", "miner_wechsel", "gueltig", "grund"]


def ms(text):
    """ISO-Zeit mit oder ohne Sekunden und Millisekunden, immer UTC."""
    t = text.strip().rstrip("Z")
    for f in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return int(dt.datetime.strptime(t, f).replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
        except ValueError:
            pass
    raise ValueError("keine zeit: %r" % text)


def minute(m):
    return dt.datetime.fromtimestamp(m * 60, dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def csv_lesen(pfad):
    with open(pfad, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def perzentil(werte, p):
    w = sorted(werte)
    if not w:
        return ""
    k = (len(w) - 1) * p
    a, b = int(k), min(int(k) + 1, len(w) - 1)
    return round(w[a] + (w[b] - w[a]) * (k - a))


def stp_dateien(ordner, name):
    """alle Dateien dieses Namens unter STPs Log-Ordner (bot, build, ...)."""
    return sorted(glob.glob(os.path.join(ordner, "**", name), recursive=True))


def zeit_spalte(z):
    return z.get("utc") or z.get("minute_utc") or z.get("t") or ""


def konflikte(ordner):
    """je Minute die wegen Konflikt abgelehnten Ausgaben, alle Seiten. Quelle
    bevorzugt rejects.csv (je Sekunde mit Grund), sonst die rej_*-Spalten der
    Minutendateien. Doppelt gezaehlt wird nichts: je Seite eine Quelle."""
    je, quelle = {}, []
    seiten_mit_rejects = set()
    for p in stp_dateien(ordner, "rejects.csv"):
        for z in csv_lesen(p):
            if any(k in (z.get("reason") or "").lower() for k in KONFLIKT):
                m = ms(zeit_spalte(z)) // 60000
                je[m] = je.get(m, 0) + int(float(z.get("count") or 1))
            seiten_mit_rejects.add(z.get("side") or p)
        quelle.append(os.path.relpath(p, ordner))
    for name in ("pulse-minute.csv", "minute.csv", "desk-sender.csv"):
        for p in stp_dateien(ordner, name):
            zeilen = csv_lesen(p)
            if not zeilen:
                continue
            seite = zeilen[0].get("side") or os.path.basename(os.path.dirname(os.path.dirname(p)))
            if seite in seiten_mit_rejects:
                continue
            spalten = [s for s in zeilen[0] if s.startswith("rej_") and any(k in s for k in KONFLIKT)]
            if not spalten:
                continue
            seiten_mit_rejects.add(seite)
            quelle.append(os.path.relpath(p, ordner))
            for z in zeilen:
                m = ms(zeit_spalte(z)) // 60000
                je[m] = je.get(m, 0) + sum(int(float(z.get(s) or 0)) for s in spalten)
    return je, quelle


def luecken(ordner, von_m, bis_m):
    """je Minute (ja/unbekannt, grund). Sender-Luecke heisst: in sec.csv fehlt
    eine Sekunde, in der die Seite senden sollte, oder senders_live ist 0 bei
    target > 0, oder events.csv meldet in der Minute eine Pause."""
    je = {}
    sec = stp_dateien(ordner, "sec.csv")
    if not sec:
        return {m: ("unbekannt", "keine sec.csv von STP") for m in range(von_m, bis_m)}
    for p in sec:
        zeilen = csv_lesen(p)
        seite = os.path.relpath(p, ordner).split(os.sep)[0]
        sekunden, soll = {}, set()
        for z in zeilen:
            t = ms(zeit_spalte(z)) // 1000
            sekunden[t] = z
            if float(z.get("target_tx_s") or 0) > 0:
                soll.add(t // 60)
        for m in range(von_m, bis_m):
            if m not in soll:
                continue
            fehlt = [s for s in range(m * 60, m * 60 + 60) if s not in sekunden]
            tot = [s for s in range(m * 60, m * 60 + 60) if s in sekunden
                   and float(sekunden[s].get("target_tx_s") or 0) > 0
                   and str(sekunden[s].get("senders_live", "1")).strip() in ("0", "0.0")]
            if fehlt:
                je.setdefault(m, []).append("%s: %d sekunden fehlen in sec.csv" % (seite, len(fehlt)))
            if tot:
                je.setdefault(m, []).append("%s: %d sekunden ohne sender" % (seite, len(tot)))
    for p in stp_dateien(ordner, "events.csv"):
        seite = os.path.relpath(p, ordner).split(os.sep)[0]
        for z in csv_lesen(p):
            ev = (z.get("event") or "").lower()
            if any(k in ev for k in LUECKE_EREIGNIS):
                m = ms(zeit_spalte(z)) // 60000
                je.setdefault(m, []).append("%s: ereignis %s" % (seite, ev))
    return {m: ("ja", "; ".join(g)) for m, g in je.items()}


def miner_wechsel(ordner):
    """je Minute (ja, grund), wenn in STPs Miner-Dateien Zustand, Threads oder
    Worker sich gegenueber der Lesung davor aendern."""
    je, quelle = {}, []
    for name in ("miner.csv", "miners.csv"):
        for p in stp_dateien(ordner, name):
            zeilen = csv_lesen(p)
            if not zeilen:
                continue
            quelle.append(os.path.relpath(p, ordner))
            felder = [f for f in ("miner_state", "threads", "workers") if f in zeilen[0]]
            vorher = None
            for z in sorted(zeilen, key=lambda r: ms(zeit_spalte(r))):
                jetzt = tuple(z.get(f, "") for f in felder)
                if vorher is not None and jetzt != vorher:
                    m = ms(zeit_spalte(z)) // 60000
                    je.setdefault(m, []).append("%s: %s -> %s" % (
                        os.path.relpath(p, ordner), "/".join(vorher), "/".join(jetzt)))
                vorher = jetzt
    return {m: "; ".join(g) for m, g in je.items()}, quelle


def submit_lesen(pfad):
    """tx_id -> submit-zeit in ms. Spalten tx_id (oder txid) und submit_ms
    (oder submit_utc als ISO mit Millisekunden)."""
    aus = {}
    if not pfad:
        return aus
    for z in csv_lesen(pfad):
        t = (z.get("tx_id") or z.get("txid") or "").strip().lower()
        if not t:
            continue
        if z.get("submit_ms"):
            aus[t] = int(float(z["submit_ms"]))
        elif z.get("submit_utc"):
            aus[t] = ms(z["submit_utc"])
    return aus


def zaehlung_lesen(ordner):
    """kombinierte minuten und die tx-listen je knoten, auch aus mehreren
    stuecken (tn10-miner): jede csv mit k1_cov_angenommen im kopf zaehlt als
    minutendatei, jede *k1-covenant.csv und *k2-covenant.csv als tx-liste.
    eine tx aus zwei stuecken wird vereint: fruehester erster block, summe der
    bloecke nur aus dem stueck mit dem fruehesten block, annahme wenn ein
    stueck sie gesehen hat."""
    kom = {}
    for p in sorted(glob.glob(os.path.join(ordner, "**", "*.csv"), recursive=True)):
        with open(p, encoding="utf-8") as fh:
            kopf = fh.readline()
        if "k1_cov_angenommen" not in kopf:
            continue
        for z in csv_lesen(p):
            kom.setdefault(ms(z["minute_utc"]) // 60000, z)
    tx = {}
    for n in ("k1", "k2"):
        for q in sorted(glob.glob(os.path.join(ordner, "**", "*%s-covenant.csv" % n), recursive=True)):
            for z in csv_lesen(q):
                alt = tx.setdefault(n, {}).get(z["tx_id"])
                if alt is None:
                    tx[n][z["tx_id"]] = z
                    continue
                if int(z["erster_block_ms"]) < int(alt["erster_block_ms"]):
                    alt["erster_block_ms"], alt["bloecke"] = z["erster_block_ms"], z["bloecke"]
                if z.get("angenommen") == "1" and alt.get("angenommen") != "1":
                    alt["angenommen"], alt["annehmender_block_ms"] = "1", z["annehmender_block_ms"]
    return kom, tx


def zusammensetzen(zaehlung, stp, submit, von_ms, bis_ms):
    kom, tx = zaehlung_lesen(zaehlung)
    sub = submit_lesen(submit)
    rej, rej_quelle = konflikte(stp) if stp else ({}, [])
    m0, m1 = von_ms // 60000, -(-bis_ms // 60000)
    a, e = m0 - GRUNDLAST_MIN, m1 + GRUNDLAST_MIN
    lue = luecken(stp, m0, m1) if stp else {m: ("unbekannt", "keine STP-logs") for m in range(m0, m1)}
    mw, mw_quelle = miner_wechsel(stp) if stp else ({}, [])
    k1 = tx.get("k1", {})
    je_bis, je_an = {}, {}
    for t, z in k1.items():
        if z.get("angenommen") != "1" or t.lower() not in sub:
            continue
        s = sub[t.lower()]
        mm = int(z["annehmender_block_ms"]) // 60000
        je_bis.setdefault(mm, []).append(int(z["erster_block_ms"]) - s)
        je_an.setdefault(mm, []).append(int(z["annehmender_block_ms"]) - s)
    aus = []
    for m in range(a, e):
        z = kom.get(m, {})
        phase = "grundlast_vor" if m < m0 else "grundlast_nach" if m >= m1 else "fenster"
        voll = z.get("k1_voll") == "1" and z.get("k2_voll") == "1"
        gleich = z.get("knoten_gleich") == "1"
        sl = lue.get(m, ("nein", "")) if phase == "fenster" else ("", "")
        mwg = mw.get(m)
        miner = ("ja", mwg) if mwg else (("nein", "") if mw_quelle else ("unbekannt", "keine miner-datei von STP"))
        grund = []
        if not voll:
            grund.append("minute nicht voll in beiden knoten")
        elif not gleich:
            grund.append("knoten nicht gleich")
        if sl[0] in ("ja", "unbekannt"):
            grund.append("sender: " + sl[1])
        if miner[0] in ("ja", "unbekannt"):
            grund.append("miner: " + miner[1])
        b = je_bis.get(m, [])
        aus.append({
            "minute_utc": minute(m), "phase": phase, "voll": int(voll), "knoten_gleich": z.get("knoten_gleich", ""),
            "cov_angenommen": z.get("k1_cov_angenommen", ""), "cov_in_bloecken": z.get("k1_cov_in_bloecken", ""),
            "cov_nie_angenommen": z.get("k1_cov_nie_angenommen", ""),
            "abgelehnt_konflikt": rej.get(m, 0) if rej_quelle else "",
            "bis_block_ms_median": round(statistics.median(b)) if b else "",
            "bis_block_ms_p90": perzentil(b, 0.9) if b else "", "bis_block_n": len(b) if sub else "",
            "bis_annahme_ms_median": round(statistics.median(je_an[m])) if je_an.get(m) else "",
            "sender_luecke": sl[0], "miner_wechsel": miner[0] if phase == "fenster" else "",
            "gueltig": int(phase == "fenster" and not grund), "grund": "; ".join(grund)})
    zus = {"fenster": [minute(m0), minute(m1)], "grundlast_min": GRUNDLAST_MIN,
           "konflikt_quelle": rej_quelle, "miner_quelle": mw_quelle,
           "submit_zeiten": len(sub), "tx_k1": len(k1), "tx_k2": len(tx.get("k2", {})),
           "tx_k1_gleich_k2": (set(k1) == set(tx.get("k2", {}))) if "k2" in tx else "",
           "gueltige_minuten": sum(r["gueltig"] for r in aus),
           "minuten_im_fenster": m1 - m0}
    ntp = []
    for p in stp_dateien(stp, "ntp.csv") if stp else []:
        ntp += [dict(z, datei=os.path.relpath(p, stp)) for z in csv_lesen(p)]
    zus["uhrversatz_stp"] = ntp
    return aus, zus


def schreiben(out, aus, zus):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "contention-je-minute.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SPALTEN)
        w.writeheader()
        w.writerows(aus)
    with open(os.path.join(out, "contention.json"), "w", encoding="utf-8") as fh:
        json.dump(zus, fh, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- selbsttest

def selbsttest():
    fehler = 0

    def ok(name, bed, ist=None):
        nonlocal fehler
        print("%-4s %s" % ("ok" if bed else "FEHL", name) + ("" if bed or ist is None else "  %r" % (ist,)))
        fehler += 0 if bed else 1

    def schreib(pfad, kopf, zeilen):
        os.makedirs(os.path.dirname(pfad), exist_ok=True)
        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write(",".join(kopf) + "\n")
            for z in zeilen:
                fh.write(",".join(str(x) for x in z) + "\n")

    t0 = ms("2026-10-29T18:00:00Z")
    with tempfile.TemporaryDirectory() as d:
        za, st = os.path.join(d, "zaehlung"), os.path.join(d, "stp")
        # zaehlung: 18:00 bis 18:03 fenster, dazu grundlast; 18:02 bei k2 nicht voll
        kopf = ["minute_utc", "k1_voll", "k2_voll", "knoten_gleich", "k1_cov_angenommen", "k1_cov_in_bloecken",
                "k1_cov_nie_angenommen"]
        zeilen = []
        for i in range(-30, 33):
            mm = minute(t0 // 60000 + i)
            voll2 = 0 if i == 2 else 1
            zeilen.append([mm, 1, voll2, "1" if voll2 else "", 5 if 0 <= i < 3 else 0, 8 if 0 <= i < 3 else 0,
                           3 if 0 <= i < 3 else 0])
        schreib(os.path.join(za, "nach.csv"), kopf, zeilen)
        txk = ["tx_id", "erster_block_ms", "bloecke", "angenommen", "annehmender_block_ms"]
        schreib(os.path.join(za, "k1-covenant.csv"), txk,
                [["aa", t0 + 1500, 1, 1, t0 + 2500], ["bb", t0 + 61000, 2, 1, t0 + 61800], ["cc", t0 + 3000, 1, 0, ""]])
        schreib(os.path.join(za, "k2-covenant.csv"), txk,
                [["aa", t0 + 1500, 1, 1, t0 + 2500], ["bb", t0 + 61000, 2, 1, t0 + 61800], ["cc", t0 + 3000, 1, 0, ""]])
        sub = os.path.join(d, "submit.csv")
        schreib(sub, ["tx_id", "submit_ms"], [["AA", t0 + 1000], ["bb", t0 + 60100]])
        # stp: bot sendet 18:00 bis 18:02, in 18:01 fehlen zwei sekunden; build ohne luecke
        sec_kopf = ["utc", "step", "target_tx_s", "senders_live", "sent"]
        bot = [[dt.datetime.fromtimestamp((t0 + s * 1000) / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "C1", 10, 1, 10] for s in range(0, 180) if s not in (70, 71)]
        schreib(os.path.join(st, "bot", "sec.csv"), sec_kopf, bot)
        build = [[dt.datetime.fromtimestamp((t0 + s * 1000) / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "C1", 10, 1, 10] for s in range(0, 180)]
        schreib(os.path.join(st, "build", "sec.csv"), sec_kopf, build)
        schreib(os.path.join(st, "bot", "rejects.csv"), ["utc", "side", "step", "reason", "count"],
                [["2026-10-29T18:00:05Z", "bot", "C1", "double-spend", 4], ["2026-10-29T18:00:06Z", "bot", "C1", "mass", 9]])
        schreib(os.path.join(st, "build", "desk-sender.csv"),
                ["minute_utc", "side", "sent", "rej_double_spend", "rej_other"],
                [["2026-10-29T18:00Z", "build", 600, 7, 50], ["2026-10-29T18:01Z", "build", 600, 2, 0]])
        schreib(os.path.join(st, "build", "miners.csv"), ["minute_utc", "workers", "hashrate_hs"],
                [["2026-10-29T17:59Z", 20, 1], ["2026-10-29T18:00Z", 20, 1], ["2026-10-29T18:01Z", 16, 1],
                 ["2026-10-29T18:02Z", 16, 1]])
        schreib(os.path.join(st, "bot", "ntp.csv"), ["utc", "offset_ms"], [["2026-10-29T17:30:00Z", 3]])
        aus, zus = zusammensetzen(za, st, sub, t0, t0 + 180000)
        r = {x["minute_utc"][11:16]: x for x in aus}
    ok("63 zeilen, 30 grundlast davor und danach", len(aus) == 63 and r["17:30"]["phase"] == "grundlast_vor"
       and r["18:03"]["phase"] == "grundlast_nach" and r["18:32"]["phase"] == "grundlast_nach")
    ok("18:00 gueltig, konflikte bot 4 plus build 7", r["18:00"]["gueltig"] == 1
       and r["18:00"]["abgelehnt_konflikt"] == 11, r["18:00"])
    ok("andere ablehnungen zaehlen nicht", r["18:01"]["abgelehnt_konflikt"] == 2)
    ok("18:01 ungueltig: zwei sekunden fehlen und miner 20 auf 16", r["18:01"]["gueltig"] == 0
       and r["18:01"]["sender_luecke"] == "ja" and "2 sekunden fehlen" in r["18:01"]["grund"]
       and r["18:01"]["miner_wechsel"] == "ja", r["18:01"])
    ok("18:02 ungueltig: k2 nicht voll", r["18:02"]["gueltig"] == 0 and "nicht voll" in r["18:02"]["grund"])
    ok("zeit bis block 500 ms und bis annahme 1500 ms in 18:00", r["18:00"]["bis_block_ms_median"] == 500
       and r["18:00"]["bis_annahme_ms_median"] == 1500 and r["18:00"]["bis_block_n"] == 1, r["18:00"])
    ok("18:01 bis block 900 ms", r["18:01"]["bis_block_ms_median"] == 900)
    ok("nie angenommene tx ohne zeit", all(x["bis_block_n"] in (0, 1, "") for x in aus))
    ok("grundlast nie gueltig, keine sender-spalte", r["17:45"]["gueltig"] == 0 and r["17:45"]["sender_luecke"] == "")
    ok("zusammenfassung: gueltig 1, k1 gleich k2, uhrversatz da", zus["gueltige_minuten"] == 1
       and zus["tx_k1_gleich_k2"] is True and zus["uhrversatz_stp"] and zus["submit_zeiten"] == 2)
    with tempfile.TemporaryDirectory() as d:
        za = os.path.join(d, "z")
        os.makedirs(za)
        aus2, zus2 = zusammensetzen(za, "", "", t0, t0 + 120000)
    ok("ohne stp-logs: sender und miner unbekannt, nichts gueltig", all(x["gueltig"] == 0 for x in aus2)
       and all(x["sender_luecke"] == "unbekannt" for x in aus2 if x["phase"] == "fenster")
       and all(x["abgelehnt_konflikt"] == "" for x in aus2))
    buf = io.StringIO()
    csv.DictWriter(buf, fieldnames=SPALTEN).writerows(aus)
    ok("keine adresse in der ausgabe", "://" not in buf.getvalue())
    print("%d fehler" % fehler)
    return 1 if fehler else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zaehlung", help="ordner mit nach.csv, k1-covenant.csv, k2-covenant.csv")
    ap.add_argument("--stp", default="", help="ordner mit STPs logs (bot/, build/)")
    ap.add_argument("--submit", default="", help="csv tx_id,submit_ms aus STPs logs, falls vorhanden")
    ap.add_argument("--fenster", nargs=2, metavar=("VON", "BIS"))
    ap.add_argument("--out", default="out/contention")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    aus, zus = zusammensetzen(a.zaehlung, a.stp, a.submit, ms(a.fenster[0]), ms(a.fenster[1]))
    schreiben(a.out, aus, zus)
    print("minuten %d, im fenster %d, gueltig %d, submit-zeiten %d" % (
        len(aus), zus["minuten_im_fenster"], zus["gueltige_minuten"], zus["submit_zeiten"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
