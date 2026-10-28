#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tn10_contention.py, Covenant-Contention je Minute (Ben, 21.10.2026).

STP-Lauf Do 29.10.2026 19:00 bis 20:00 UTC (Ben, 27.10.: um plus 1 h verschoben), Phase "covenant contention": mehrere Sender
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

FREEZE-FORMAT (STP, tn10-storm-2026-10-29, Plan vom 26.10., Freeze Di 27.10.)
    minute.csv            je UTC-Minute sent, ok, rej_already_spent, rej_orphan,
                          weitere rej_*, winners, hops, include_*, seen_*,
                          families; mit Spalte family auch je Familie
    phase.log             je Ereignis eine Zeile "<utc> TOKEN key=wert ...":
                          GENESIS, START, STEP, GAP, STOP, STALL und, falls STP
                          sie einfuehrt, SENDER_OFF, SENDER_ON, NODE_SKIP,
                          FAMILY_DROP, MINER
    sec.csv               falls geliefert, je Sekunde senders_target, senders_on
    ntp.csv               falls geliefert, utc, machine, offset_ms, source
    post-end-mempool.csv  minute_utc, node, mempool_size
    Schritte laut Plan, Minuten ab T0: 1 (0 bis 14, 1 Familie), Pause, 2 (20
    bis 34, 2 Familien), Pause, 3a und 3b (40 bis 59, 4 Familien). Gezaehlt
    ab Minute 3 eines Schritts. Mit T0 19:00 UTC also 19:03 bis 19:14, 19:23
    bis 19:34, 19:43 bis 19:59. T0, END und die gezaehlten Minuten stehen in
    messung/tn10/lauf-2026-10-29.txt (--lauf); dort gilt STPs Liste, falls sie
    vom Plan abweicht. Familie n bei STP heisst bei uns f<n>. Familie 0 ist
    KNS und wird nie gezaehlt (STP, 26.10.). Jede MINER-Zeile markiert ihre
    Minute. ntp.csv kommt von desk, mini und box zu 16:00, 17:55 und 19:01 UTC.
    Etiketten von Sendern und Knoten gehen nur als kurze Namen (desk, mini,
    muon) in die Ausgabe, alles andere wird zu knoten1, knoten2 und so weiter.
    Zeilen aus STPs Logs werden nie woertlich uebernommen.

Die Covenant-ID steht nirgends, nur ihr Hash in der Zieldatei der Zaehlung
(messung/tn10/nach/covenant.sha256, je Zeile "f<n> sha256"). Den Hash baut
    printf 'f1 <id>\n' | python3 scripts/tn10_contention.py --hash
ohne die ID auszugeben.
Blockzeit ist die Zeit im Blockkopf (Uhr des Miners), Submit-Zeit die Uhr
des Senders; der Uhrversatz aus STPs ntp.csv steht in der Zusammenfassung.

    python3 scripts/tn10_contention.py --zaehlung DIR --stp DIR [--submit CSV] \\
        --lauf messung/tn10/lauf-2026-10-29.txt --out DIR
    python3 scripts/tn10_contention.py --selbsttest
    Mit --plan storm (Vorgabe) gilt die Schritt-Tabelle oben ab --fenster VON,
    mit --plan keiner zaehlt jede Minute im Fenster.
"""
import argparse
import csv
import datetime as dt
import glob
import hashlib
import io
import json
import os
import re
import statistics
import sys
import tempfile

GRUNDLAST_MIN = 30
KONFLIKT = ("double_spend", "double-spend", "doublespend", "conflict", "already_spent", "already-spent")
LUECKE_EREIGNIS = ("gap", "pause", "paused", "stall", "freeze", "node-dead", "sender-stop", "stop", "relaunch")
# Schritte des Storm-Plans, Minuten ab T0: (name, von, bis, familien, gezaehlt ab)
STORM = [("1", 0, 15, 1, 3), ("pause", 15, 20, 0, None), ("2", 20, 35, 2, 23), ("pause", 35, 40, 0, None),
         ("3a", 40, 55, 4, 43), ("3b", 55, 60, 4, 43)]
SOLL_ANTEIL = 0.95
UNTERBRECHEN = ("GAP", "GAP_START", "STOP", "STALL")
WEITER = ("START", "STEP", "GAP_END")
RAUS = ("NODE_SKIP", "NODE_DROP")               # Sender fuer den Rest der Phase draussen
STP_ZAHLEN = ("sent", "ok", "winners", "hops")
STP_LAGE = ("include_p50_ms", "include_p95_ms", "seen_p50_ms", "seen_p95_ms")
SUMME = ("", "all", "total", "sum", "*")
# Familie 0 ist KNS (STP, 26.10.2026) und wird nie gezaehlt, weder bei uns
# noch in STPs Spalten. Fuer die Soll-Pruefung der Sender bleibt sie in sent_alle.
AUSGESCHLOSSEN = ("f0",)
NTP_MASCHINEN = ("desk", "mini", "box")
# Messpunkte relativ zu T0 (STP, Freeze 27.10.): T0-2h, T0-5min, END+1min.
# So bleibt die Pruefung richtig, falls T0 um eine Stunde wandert.
NTP_PUNKTE_MIN = (-120, -5, 61)
NTP_SPIEL_MIN = 5
SPALTEN = ["minute_utc", "phase", "schritt", "zaehlminute", "familien", "voll", "knoten_gleich", "cov_angenommen", "cov_in_bloecken",
           "cov_nie_angenommen", "abgelehnt_konflikt", "bis_block_ms_median", "bis_block_ms_p90", "bis_block_n",
           "bis_annahme_ms_median", "sender_luecke", "sender_beleg", "sender_aktiv", "miner_wechsel",
           "stp_sent", "stp_ok", "stp_rej_already_spent", "stp_rej_orphan", "stp_rej_andere", "stp_summe_stimmt",
           "stp_f0_trennbar",
           "stp_winners", "stp_hops", "stp_include_p50_ms", "stp_seen_p50_ms", "abgleich_winners",
           "gueltig", "grund"]


def ms(text):
    """ISO-Zeit mit oder ohne Sekunden und Millisekunden, immer UTC."""
    t = text.strip().rstrip("Z").replace(" ", "T")
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
    return z.get("utc") or z.get("utc_second") or z.get("minute_utc") or z.get("t") or ""


def zahl(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def familie_norm(x):
    """STPs Familie "1" oder "family1" heisst bei uns f1; leer oder all ist
    die Summe ueber alle Familien."""
    x = (x or "").strip().lower()
    if x in SUMME:
        return ""
    d = re.fullmatch(r"(?:f|family|fam)?_?(\d{1,2})", x)
    return "f%d" % int(d.group(1)) if d else "f_" + hashlib.sha256(x.encode()).hexdigest()[:6]


class Etiketten:
    """Kurze Namen wie desk, mini, muon bleiben, alles andere (Hostname, IP,
    Pfad) wird knoten1, knoten2 in der Reihenfolge des ersten Auftretens."""

    def __init__(self):
        self.fremd = {}

    def __call__(self, x):
        x = (x or "").strip().lower()
        if re.fullmatch(r"[a-z][a-z0-9_]{0,15}", x):
            return x
        return self.fremd.setdefault(x, "knoten%d" % (len(self.fremd) + 1))


def grund_norm(x):
    """Grund-Token wie node_dead oder END, sonst "anderer"."""
    x = (x or "").strip().lower()
    return x if re.fullmatch(r"[a-z0-9_]{1,24}", x) else ("anderer" if x else "")


def cov_hash(cid):
    """wie tn10_nachzaehlung.cov_hash: sha256 der kleingeschriebenen Hex-ID."""
    return hashlib.sha256(str(cid).strip().lower().encode()).hexdigest()


def hash_zeilen(text):
    """Zeilen "f<n> <covenant-id>" zu "f<n> <sha256>". Die ID wird nie
    ausgegeben, auch nicht im Fehlerfall."""
    aus = []
    for i, z in enumerate(text.splitlines(), 1):
        z = z.strip()
        if not z or z.startswith("#"):
            continue
        teile = z.split()
        if len(teile) != 2 or not re.fullmatch(r"f\d{1,2}", teile[0]):
            raise ValueError("zeile %d: erwartet \"f<n> <covenant-id>\"" % i)
        if teile[0] in AUSGESCHLOSSEN:
            raise ValueError("zeile %d: familie 0 ist KNS und wird nicht gezaehlt" % i)
        cid = teile[1].lower()
        cid = cid[2:] if cid.startswith("0x") else cid
        if not re.fullmatch(r"[0-9a-f]{64}", cid):
            raise ValueError("zeile %d: covenant-id ist nicht 64 hex-zeichen" % i)
        aus.append("%s %s" % (teile[0], cov_hash(cid)))
    if len({a.split()[0] for a in aus}) != len(aus):
        raise ValueError("familie doppelt")
    return aus


def lauf_lesen(pfad):
    """Laufdatei: t0, ende, gezaehlt (HH:MM-HH:MM, kommagetrennt, UTC am Tag
    von t0). Ergibt (t0_ms, ende_ms, menge der gezaehlten minuten)."""
    werte = {}
    for z in open(pfad, encoding="utf-8"):
        z = z.strip()
        if z and not z.startswith("#") and "=" in z:
            k, v = z.split("=", 1)
            werte[k.strip()] = v.strip()
    t0, ende = ms(werte["t0"]), ms(werte["ende"])
    tag = werte["t0"][:10]
    lauf_lesen.ntp = [ms("%sT%s:00Z" % (tag, x.strip())) for x in werte.get("ntp", "").split(",") if x.strip()]
    gez = set()
    for teil in werte.get("gezaehlt", "").split(","):
        if not teil.strip():
            continue
        a, b = [ms("%sT%s:00Z" % (tag, x.strip())) // 60000 for x in teil.split("-")]
        if b < a:
            raise ValueError("gezaehlt: ende vor anfang in %r" % teil)
        gez |= set(range(a, b + 1))
    if gez and not all(t0 // 60000 <= m < -(-ende // 60000) for m in gez):
        raise ValueError("gezaehlte minute ausserhalb t0 bis ende")
    return t0, ende, gez


def plan_schritte(von_ms, plan, gezaehlt=None):
    """je Minute (schritt, zaehlminute, familien laut plan)."""
    if plan != "storm":
        return {}
    m0 = von_ms // 60000
    aus = {}
    for name, a, b, fam, ab in STORM:
        for i in range(a, b):
            aus[m0 + i] = (name, int(ab is not None and i >= ab), fam)
    if gezaehlt:
        # STPs Liste gilt (Ben, 27.10.2026), die Schrittnamen bleiben
        aus = {m: (n, int(m in gezaehlt), f) for m, (n, _, f) in aus.items()}
    return aus


def summe_stimmt(w):
    """sent = ok + Summe aller rej_*; leer, wenn sent fehlt."""
    if w.get("sent") is None:
        return ""
    return int(w["sent"] == (w.get("ok") or 0) + sum(v for k, v in w.items() if k.startswith("rej_") and v is not None))


def stp_minuten(ordner):
    """minute.csv aus dem Freeze-Format: je Minute die Summe und, mit Spalte
    family, je Familie. Familie 0 (KNS) wird ausgeschlossen. Gibt es fuer eine
    Minute Familienzeilen, ist die Summe deren Summe ohne Familie 0; nur ohne
    Familienzeilen gilt eine Summenzeile, und dann ist Familie 0 nicht
    trennbar (vermerkt). sent_alle ist sent mit Familie 0, fuer die
    Soll-Pruefung der Sender."""
    zeile_summe, fam, aus_f0, quelle = {}, {}, {}, []
    for p in stp_dateien(ordner, "minute.csv"):
        zeilen = csv_lesen(p)
        if not zeilen or "sent" not in zeilen[0]:
            continue
        quelle.append(os.path.relpath(p, ordner))
        for z in zeilen:
            m = ms(zeit_spalte(z)) // 60000
            f = familie_norm(z.get("family"))
            werte = {k: zahl(v) for k, v in z.items() if k in STP_ZAHLEN or k.startswith("rej_") or k == "families"}
            werte.update({k: zahl(z.get(k)) for k in STP_LAGE if (z.get(k) or "").strip()})
            if f in AUSGESCHLOSSEN:
                aus_f0.setdefault(m, {})[f] = werte
            elif f:
                fam.setdefault(m, {})[f] = werte
            else:
                zeile_summe[m] = werte
    summe = {}
    for m in set(zeile_summe) | set(fam) | set(aus_f0):
        je = fam.get(m, {})
        if not je and m in zeile_summe:
            s = dict(zeile_summe[m])
            s["f0_trennbar"] = 0 if not aus_f0.get(m) else 1
            s["sent_alle"] = s.get("sent")
            summe[m] = s
            continue
        s = {}
        for w in je.values():
            for k, v in w.items():
                if k in STP_LAGE or v is None:
                    continue
                if k == "families":
                    continue
                s[k] = s.get(k, 0) + v
        if len(je) == 1:
            s.update({k: v for k, v in list(je.values())[0].items() if k in STP_LAGE})
        s["families"] = len(je)
        alle = (zeile_summe.get(m) or {}).get("sent")
        if alle is None:
            alle = (s.get("sent") or 0) + sum((w.get("sent") or 0) for w in aus_f0.get(m, {}).values())
        s["sent_alle"], s["f0_trennbar"] = alle, 1
        summe[m] = s
    return summe, fam, quelle


ZEILE = re.compile(r"^(\S+)\s+([A-Z][A-Z_]*)\b(.*)$")


def phase_lesen(ordner):
    """phase.log zu einer Liste (sekunde, token, {key: wert}), sortiert."""
    aus, unlesbar = [], 0
    for p in stp_dateien(ordner, "phase.log"):
        with open(p, encoding="utf-8", errors="replace") as fh:
            for z in fh:
                z = z.strip()
                if not z:
                    continue
                t = ZEILE.match(z)
                try:
                    sek = ms(t.group(1)) // 1000 if t else None
                except ValueError:
                    sek = None
                if sek is None:
                    unlesbar += 1
                    continue
                aus.append((sek, t.group(2), dict(re.findall(r"(\w+)=(\S+)", t.group(3)))))
    return sorted(aus, key=lambda e: e[0]), unlesbar


def phase_auswerten(ereignisse, von_m, bis_m, etikett):
    """je Minute im Fenster: Gruende fuer eine Sender-Luecke, Miner-Wechsel,
    aktive Sender und Soll-Rate. Eine Minute mit einem Wechsel (START, STEP,
    GAP, STOP, STALL, SENDER_OFF, SENDER_ON, NODE_SKIP) ist nie sauber; eine
    Minute, in der ein geplanter Sender aus ist oder nicht gesendet wird, auch
    nicht. NODE_SKIP nimmt den Sender fuer den Rest der Phase heraus."""
    luecke, miner, aktiv_je, rate_je = {}, {}, {}, {}
    zus = {"genesis": [], "family_drop": [], "start": "", "stop": [], "node_skip": [], "sender_off": [], "main": "",
           "miner_zeilen": 0, "tokens": {}}
    aktiv, geplant, rate, laeuft, miner_vorher = set(), set(), None, False, None
    i = 0
    if not ereignisse:
        return luecke, miner, aktiv_je, rate_je, zus
    for m in range(min([von_m] + [e[0] // 60 for e in ereignisse]), max([bis_m] + [e[0] // 60 + 1 for e in ereignisse])):
        aus_in_minute = []
        while i < len(ereignisse) and ereignisse[i][0] // 60 == m:
            sek, tok, kv = ereignisse[i]
            i += 1
            zus["tokens"][tok] = zus["tokens"].get(tok, 0) + 1
            uhr = dt.datetime.fromtimestamp(sek, dt.timezone.utc).strftime("%H:%M:%S")
            if tok == "GENESIS":
                f = familie_norm(kv.get("family"))
                zus["genesis"].append({"utc": uhr, "familie": f, "gezaehlt": int(f not in AUSGESCHLOSSEN)})
            elif tok == "FAMILY_DROP":
                zus["family_drop"].append({"utc": uhr, "familie": familie_norm(kv.get("family")),
                                           "grund": grund_norm(kv.get("reason"))})
            elif tok == "MINER":
                zus["miner_zeilen"] += 1
                # jede MINER-Zeile markiert ihre Minute (STP, 26.10.2026: kleiner
                # CPU-Miner, Neustarts per Watchdog), nicht nur ein Wechsel
                jetzt = "/".join(x for x in (kv.get("state", ""), kv.get("workers", ""),
                                             etikett(kv.get("miner")) if kv.get("miner") else "",
                                             grund_norm(kv.get("reason"))) if x)
                miner.setdefault(m, []).append("miner %s um %s" % (jetzt or "zeile", uhr))
                miner_vorher = jetzt
            elif tok in WEITER:
                if kv.get("senders"):
                    geplant = {etikett(x) for x in kv["senders"].split(",") if x}
                    aktiv = set(geplant)
                if tok == "START":
                    zus["start"] = zus["start"] or uhr
                rate = zahl(kv.get("rate")) or rate
                laeuft = True
                aus_in_minute.append("%s um %s" % (tok, uhr))
            elif tok in UNTERBRECHEN:
                laeuft = False
                grund = grund_norm(kv.get("reason"))
                if tok != "GAP":
                    zus["stop"].append({"utc": uhr, "token": tok, "grund": grund})
                aus_in_minute.append("%s %s um %s" % (tok, grund, uhr))
            elif tok == "MAIN":
                zus["main"] = etikett(kv.get("node"))
            elif tok in ("SENDER_OFF", "SENDER_ON") + RAUS:
                wer = etikett(kv.get("sender") or kv.get("node"))
                if tok == "SENDER_ON":
                    aktiv.add(wer)
                else:
                    aktiv.discard(wer)
                    if tok in RAUS:
                        geplant.discard(wer)
                    zus["node_skip" if tok in RAUS else "sender_off"].append(
                        {"utc": uhr, "wer": wer, "grund": grund_norm(kv.get("reason"))})
                aus_in_minute.append("%s %s um %s" % (tok, wer, uhr))
        if m < von_m or m >= bis_m:
            continue
        aktiv_je[m], rate_je[m] = len(aktiv) if laeuft else 0, rate
        if aus_in_minute:
            luecke.setdefault(m, []).extend(aus_in_minute)
        elif not laeuft:
            luecke.setdefault(m, []).append("keine versuche laut phase.log")
        elif geplant - aktiv:
            luecke.setdefault(m, []).append("sender aus: " + ",".join(sorted(geplant - aktiv)))
    return luecke, miner, aktiv_je, rate_je, zus


def ntp_lesen(ordner, etikett):
    aus = []
    for p in stp_dateien(ordner, "ntp.csv") if ordner else []:
        for z in csv_lesen(p):
            q = (z.get("source") or "").strip()
            aus.append({"utc": zeit_spalte(z), "maschine": etikett(z.get("machine") or z.get("label")),
                        "offset_ms": zahl(z.get("offset_ms")),
                        "quelle": q if re.fullmatch(r"[a-z][a-z0-9_]{0,15}", q) else ("server" if q else ""),
                        "datei": os.path.basename(p)})
    return aus


def ntp_pruefen(ntp, von_ms, punkte_ms=None):
    """je Maschine (desk, mini, box) und Messpunkt (T0-2h, T0-5min,
    END+1min, bei T0 18:00 also 16:00, 17:55, 19:01 UTC) die naechste Messung im Abstand bis NTP_SPIEL_MIN; fehlt eine,
    steht sie unter fehlt."""
    aus, fehlt = {}, []
    for mas in NTP_MASCHINEN:
        for soll in (punkte_ms or [von_ms + rel * 60000 for rel in NTP_PUNKTE_MIN]):
            pkt = dt.datetime.fromtimestamp(soll / 1000, dt.timezone.utc).strftime("%H:%M")
            kandidaten = []
            for x in ntp:
                if x["maschine"] != mas or x["offset_ms"] is None:
                    continue
                try:
                    abstand = abs(ms(x["utc"]) - soll)
                except ValueError:
                    continue
                if abstand <= NTP_SPIEL_MIN * 60000:
                    kandidaten.append((abstand, x["offset_ms"]))
            if kandidaten:
                aus.setdefault(mas, {})[pkt] = min(kandidaten)[1]
            else:
                fehlt.append("%s %s" % (mas, pkt))
    fremd = sorted({x["maschine"] for x in ntp} - set(NTP_MASCHINEN))
    return {"offset_ms": aus, "fehlt": fehlt, "andere_maschinen": fremd, "vollstaendig": not fehlt}


def post_end_lesen(ordner, etikett):
    aus = []
    for p in stp_dateien(ordner, "post-end-mempool.csv") if ordner else []:
        for z in csv_lesen(p):
            aus.append({"minute_utc": zeit_spalte(z), "knoten": etikett(z.get("node")),
                        "mempool": zahl(z.get("mempool_size"))})
    return aus


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
    if not quelle:
        summe, _, q = stp_minuten(ordner)
        for m, w in summe.items():
            n = [v for k, v in w.items() if k.startswith("rej_") and any(x in k for x in KONFLIKT) and v is not None]
            if n:
                je[m] = je.get(m, 0) + sum(n)
        if any(any(k.startswith("rej_") and any(x in k for x in KONFLIKT) for k in w) for w in summe.values()):
            quelle += q
            seiten_mit_rejects.add("minute.csv")
    for name in ("pulse-minute.csv", "desk-sender.csv"):
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


def sender_fehlt(z):
    """eine Sekunde, in der weniger Sender liefen als geplant."""
    if (z.get("senders_target") or "").strip():
        return (zahl(z.get("senders_on")) or 0) < (zahl(z["senders_target"]) or 0)
    return float(z.get("target_tx_s") or 0) > 0 and str(z.get("senders_live", "1")).strip() in ("0", "0.0")


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
        seite = "stp" if seite in ("sec.csv", "logs") else seite
        sekunden, soll = {}, set()
        for z in zeilen:
            t = ms(zeit_spalte(z)) // 1000
            sekunden[t] = z
            if float(z.get("senders_target") or z.get("target_tx_s") or 0) > 0:
                soll.add(t // 60)
        for m in range(von_m, bis_m):
            if m not in soll:
                continue
            fehlt = [s for s in range(m * 60, m * 60 + 60) if s not in sekunden]
            tot = [s for s in range(m * 60, m * 60 + 60) if s in sekunden and sender_fehlt(sekunden[s])]
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


def familien_aus(kom):
    """Familiennamen aus den Minutenspalten k1_cov_<familie>_angenommen."""
    aus = []
    for z in list(kom.values())[:1]:
        for c in z:
            if c.startswith("k1_cov_") and c.endswith("_angenommen") and not c.endswith("_nie_angenommen") \
                    and c != "k1_cov_angenommen":
                aus.append(c[len("k1_cov_"):-len("_angenommen")])
    return aus


def mempool_lesen(ordner):
    """mempool-k1.json und mempool-k2.json aus tn10_nachzaehlung --mempool-um."""
    aus = {}
    for n in ("k1", "k2"):
        for p in glob.glob(os.path.join(ordner or "", "**", "mempool-%s.json" % n), recursive=True)[:1]:
            with open(p, encoding="utf-8") as fh:
                m = json.load(fh)
            aus[n] = {k: m.get(k) for k in ("status", "gelesen_utc", "kennung", "synchron", "eintraege", "orphans",
                                           "familien")}
    return aus


def zusammensetzen(zaehlung, stp, submit, von_ms, bis_ms, mempool="", plan="keiner", miner_aussage="",
                   gezaehlt=None, ntp_punkte=None):
    etikett = Etiketten()
    kom, tx = zaehlung_lesen(zaehlung)
    fam = familien_aus(kom)
    sub = submit_lesen(submit)
    rej, rej_quelle = konflikte(stp) if stp else ({}, [])
    m0, m1 = von_ms // 60000, -(-bis_ms // 60000)
    a, e = m0 - GRUNDLAST_MIN, m1 + GRUNDLAST_MIN
    plan_m = plan_schritte(von_ms, plan, gezaehlt)
    plan_gez = {m for m, (_, z, _) in plan_schritte(von_ms, plan).items() if z}
    sec_da = bool(stp and stp_dateien(stp, "sec.csv"))
    lue_sec = luecken(stp, m0, m1) if sec_da else {}
    ereignisse, unlesbar = phase_lesen(stp) if stp else ([], 0)
    lue_ph, mw_ph, aktiv_je, rate_je, ph_zus = phase_auswerten(ereignisse, m0, m1, etikett)
    beleg = "+".join(x for x, da in (("sec.csv", sec_da), ("phase.log", bool(ereignisse))) if da)
    mw, mw_quelle = miner_wechsel(stp) if stp else ({}, [])
    for m, g in mw_ph.items():
        mw[m] = "; ".join(x for x in (mw.get(m), "; ".join(g)) if x)
    if ph_zus["miner_zeilen"]:
        mw_quelle.append("phase.log")
    if miner_aussage and not mw_quelle:
        mw_quelle.append("plan")
    stp_sum, stp_fam, stp_q = stp_minuten(stp) if stp else ({}, {}, [])
    stp_fnamen = sorted({f for je in stp_fam.values() for f in je}, key=lambda f: (len(f), f))
    k1 = tx.get("k1", {})
    je_bis, je_an, je_fam = {}, {}, {}
    for t, z in k1.items():
        if z.get("angenommen") != "1" or t.lower() not in sub:
            continue
        s = sub[t.lower()]
        mm = int(z["annehmender_block_ms"]) // 60000
        je_bis.setdefault(mm, []).append(int(z["erster_block_ms"]) - s)
        je_an.setdefault(mm, []).append(int(z["annehmender_block_ms"]) - s)
        for f in (z.get("familie") or "").split("+"):
            if f:
                je_fam.setdefault((f, mm), []).append(int(z["erster_block_ms"]) - s)
    aus = []
    for m in range(a, e):
        z = kom.get(m, {})
        phase = "grundlast_vor" if m < m0 else "grundlast_nach" if m >= m1 else "fenster"
        schritt, zm, fam_plan = (plan_m.get(m, ("", 0, "")) if plan_m else ("", 1, "")) if phase == "fenster" \
            else ("", 0, "")
        w = stp_sum.get(m, {})
        voll = z.get("k1_voll") == "1" and z.get("k2_voll") == "1"
        gleich = z.get("knoten_gleich") == "1"
        if phase != "fenster":
            sl = ("", "")
        elif schritt == "pause":
            sl = ("pause", "")
        elif not beleg:
            sl = ("unbekannt", "keine sec.csv und kein phase.log von STP")
        else:
            g = []
            if m in lue_sec:
                g.append(lue_sec[m][1])
            g += lue_ph.get(m, [])
            soll = (aktiv_je.get(m) or 0) * (rate_je.get(m) or 0) * 60
            if zm and stp_q and not w:
                g.append("minute fehlt in minute.csv")
            elif zm and soll and w.get("sent_alle") is not None and w["sent_alle"] < SOLL_ANTEIL * soll:
                g.append("sent %d unter soll %d" % (w["sent_alle"], soll))
            sl = ("ja", "; ".join(g)) if g else ("nein", "")
        mwg = mw.get(m)
        miner = ("ja", mwg) if mwg else (("nein", "") if mw_quelle else ("unbekannt", "keine miner-angabe von STP"))
        grund = []
        if phase == "fenster" and not zm:
            grund.append("pause laut plan" if schritt == "pause" else "anlauf, nicht gezaehlt laut plan")
        if not voll:
            grund.append("minute nicht voll in beiden knoten")
        elif not gleich:
            grund.append("knoten nicht gleich")
        if sl[0] in ("ja", "unbekannt"):
            grund.append("sender: " + sl[1])
        if miner[0] in ("ja", "unbekannt"):
            grund.append("miner: " + miner[1])
        b = je_bis.get(m, [])
        rej_alle = {k: v for k, v in w.items() if k.startswith("rej_") and v is not None}
        cov = z.get("k1_cov_angenommen", "")
        aus.append({
            "minute_utc": minute(m), "phase": phase, "schritt": schritt, "zaehlminute": zm,
            "familien": (w.get("families") if w.get("families") is not None else fam_plan) if phase == "fenster" else "",
            "voll": int(voll), "knoten_gleich": z.get("knoten_gleich", ""),
            "cov_angenommen": cov, "cov_in_bloecken": z.get("k1_cov_in_bloecken", ""),
            "cov_nie_angenommen": z.get("k1_cov_nie_angenommen", ""),
            "abgelehnt_konflikt": rej.get(m, 0) if rej_quelle else "",
            "bis_block_ms_median": round(statistics.median(b)) if b else "",
            "bis_block_ms_p90": perzentil(b, 0.9) if b else "", "bis_block_n": len(b) if sub else "",
            "bis_annahme_ms_median": round(statistics.median(je_an[m])) if je_an.get(m) else "",
            "sender_luecke": sl[0], "sender_beleg": beleg if phase == "fenster" else "",
            "sender_aktiv": aktiv_je.get(m, "") if ereignisse and phase == "fenster" else "",
            "miner_wechsel": miner[0] if phase == "fenster" else "",
            "stp_sent": w.get("sent", ""), "stp_ok": w.get("ok", ""),
            "stp_rej_already_spent": w.get("rej_already_spent", ""), "stp_rej_orphan": w.get("rej_orphan", ""),
            "stp_rej_andere": sum(v for k, v in rej_alle.items() if k not in ("rej_already_spent", "rej_orphan"))
            if w else "",
            "stp_summe_stimmt": summe_stimmt(w),
            "stp_f0_trennbar": w.get("f0_trennbar", ""),
            "stp_winners": w.get("winners", ""), "stp_hops": w.get("hops", ""),
            "stp_include_p50_ms": w.get("include_p50_ms", ""), "stp_seen_p50_ms": w.get("seen_p50_ms", ""),
            "abgleich_winners": int(cov) - w["winners"] if str(cov).isdigit() and w.get("winners") is not None else "",
            "gueltig": int(phase == "fenster" and not grund), "grund": "; ".join(grund)})
        for f in fam:
            an = z.get("k1_cov_%s_angenommen" % f, "")
            bf = je_fam.get((f, m), [])
            aus[-1].update({
                "cov_%s_angenommen" % f: an,
                "cov_%s_pro_s" % f: round(int(an) / 60, 3) if str(an).isdigit() else "",
                "cov_%s_nie_angenommen" % f: z.get("k1_cov_%s_nie_angenommen" % f, ""),
                "cov_%s_bis_block_ms_median" % f: round(statistics.median(bf)) if bf else ""})
        for f in stp_fnamen:
            wf = stp_fam.get(m, {}).get(f, {})
            aus[-1].update({"stp_%s_%s" % (f, k): ("" if wf.get(k) is None else wf[k])
                            for k in ("sent", "ok", "rej_already_spent", "winners", "hops")})
            aus[-1]["stp_%s_summe_stimmt" % f] = summe_stimmt(wf) if wf else ""
    zus = {"fenster": [minute(m0), minute(m1)], "grundlast_min": GRUNDLAST_MIN, "plan": plan,
           "zaehlminuten_quelle": ("lauf-datei" if gezaehlt else "plan"),
           "zaehlminuten_weichen_vom_plan_ab": bool(gezaehlt) and set(gezaehlt) != plan_gez,
           "konflikt_quelle": rej_quelle, "miner_quelle": mw_quelle, "miner_aussage_plan": miner_aussage,
           "sender_beleg": beleg, "phase_log": dict(ph_zus, unlesbare_zeilen=unlesbar),
           "stp_minute_quelle": stp_q, "stp_familien": stp_fnamen,
           "submit_zeiten": len(sub), "tx_k1": len(k1), "tx_k2": len(tx.get("k2", {})),
           "tx_k1_gleich_k2": (set(k1) == set(tx.get("k2", {}))) if "k2" in tx else "",
           "gueltige_minuten": sum(r["gueltig"] for r in aus),
           "minuten_im_fenster": m1 - m0, "familien": fam, "mempool_nach_end": mempool_lesen(mempool),
           "je_schritt": je_schritt(aus, fam, stp_fnamen)}
    zus["familie_ausgeschlossen"] = list(AUSGESCHLOSSEN)
    zus["summe_falsch"] = [
        "%s %s" % (r["minute_utc"][11:16], k[4:-len("_summe_stimmt")] if k != "stp_summe_stimmt" else "summe")
        for r in aus if r["zaehlminute"] for k in r if k.startswith("stp_") and k.endswith("summe_stimmt") and r[k] == 0]
    zus["f0_nicht_trennbar"] = [r["minute_utc"][11:16] for r in aus if r["zaehlminute"] and r["stp_f0_trennbar"] == 0]
    ntp = ntp_lesen(stp, etikett)
    zus["uhrversatz_stp"] = ntp
    zus["ntp_pruefung"] = ntp_pruefen(ntp, von_ms, ntp_punkte)
    werte = [abs(x["offset_ms"]) for x in ntp if x["offset_ms"] is not None]
    zus["uhrversatz_max_ms"] = max(werte) if werte else ""
    zus["mempool_nach_end_stp"] = post_end_lesen(stp, etikett)
    return aus, zus


def je_schritt(aus, fam, stp_fnamen):
    """Kopfzahl je Schritt (3a und 3b zusammen als 3): Hops je Sekunde aus
    unserer Zaehlung (counted, nur gueltige Minuten), je Familie, und STPs
    winners in denselben Minuten (source STP)."""
    gruppen = {}
    for r in aus:
        if r["phase"] == "fenster" and r["zaehlminute"]:
            gruppen.setdefault(r["schritt"][:1] or "fenster", []).append(r)
    erg = {}
    for g, rs in gruppen.items():
        ok = [r for r in rs if r["gueltig"]]
        n = len(ok)
        e = {"minuten_gezaehlt": len(rs), "minuten_gueltig": n,
             "von": rs[0]["minute_utc"], "bis": rs[-1]["minute_utc"]}
        if n:
            e["hops_je_s_counted"] = round(sum(int(r["cov_angenommen"] or 0) for r in ok) / (60 * n), 3)
            e["je_familie_counted"] = {f: round(sum(int(r.get("cov_%s_angenommen" % f) or 0) for r in ok) / (60 * n), 3)
                                       for f in fam}
            w = [r["stp_winners"] for r in ok if r["stp_winners"] != ""]
            if len(w) == n:
                e["winners_je_s_source_stp"] = round(sum(w) / (60 * n), 3)
                e["je_familie_source_stp"] = {
                    f: round(sum(r.get("stp_%s_winners" % f) or 0 for r in ok) / (60 * n), 3) for f in stp_fnamen}
        erg[g] = e
    return erg


def spalten(aus):
    return SPALTEN + [c for c in (aus[0] if aus else {}) if c not in SPALTEN]


def schreiben(out, aus, zus):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "contention-je-minute.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=spalten(aus))
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
                "k1_cov_nie_angenommen", "k1_cov_f1_angenommen", "k1_cov_f1_nie_angenommen",
                "k1_cov_f2_angenommen", "k1_cov_f2_nie_angenommen"]
        zeilen = []
        for i in range(-30, 33):
            mm = minute(t0 // 60000 + i)
            voll2 = 0 if i == 2 else 1
            im = 0 <= i < 3
            zeilen.append([mm, 1, voll2, "1" if voll2 else "", 5 if im else 0, 8 if im else 0,
                           3 if im else 0, 42 if im else 0, 3 if im else 0, 0, 0])
        schreib(os.path.join(za, "nach.csv"), kopf, zeilen)
        txk = ["tx_id", "familie", "erster_block_ms", "bloecke", "angenommen", "annehmender_block_ms"]
        txz = [["aa", "f1", t0 + 1500, 1, 1, t0 + 2500], ["bb", "f1", t0 + 61000, 2, 1, t0 + 61800],
               ["cc", "f1", t0 + 3000, 1, 0, ""]]
        schreib(os.path.join(za, "k1-covenant.csv"), txk, txz)
        schreib(os.path.join(za, "k2-covenant.csv"), txk, txz)
        mpd = os.path.join(d, "mempool")
        os.makedirs(mpd)
        for n in ("k1", "k2"):
            with open(os.path.join(mpd, "mempool-%s.json" % n), "w", encoding="utf-8") as fh:
                json.dump({"status": "gelesen", "kennung": "0123456789", "eintraege": 7, "orphans": 2,
                           "familien": {"f1": {"orphans": 1, "wartend": 0}}}, fh)
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
        aus, zus = zusammensetzen(za, st, sub, t0, t0 + 180000, mpd)
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
    csv.DictWriter(buf, fieldnames=spalten(aus)).writerows(aus)
    ok("keine adresse in der ausgabe", "://" not in buf.getvalue())
    ok("familien: f1 42 angenommen, 0.7 je sekunde, f2 0", zus["familien"] == ["f1", "f2"]
       and r["18:00"]["cov_f1_angenommen"] == "42" and r["18:00"]["cov_f1_pro_s"] == 0.7
       and r["18:00"]["cov_f2_angenommen"] == "0" and r["18:00"]["cov_f1_bis_block_ms_median"] == 500, r["18:00"])
    ok("familien: spalten in der csv", "cov_f2_pro_s" in spalten(aus))
    ok("mempool nach end in der zusammenfassung", zus["mempool_nach_end"]["k1"]["orphans"] == 2
       and zus["mempool_nach_end"]["k2"]["familien"]["f1"]["orphans"] == 1)
    selbsttest_freeze(ok, schreib)
    selbsttest_eingefroren(ok, schreib)
    selbsttest_lauf(ok, schreib)
    print("%d fehler" % fehler)
    return 1 if fehler else 0


def selbsttest_freeze(ok, schreib):
    """eine Storm-Stunde im Freeze-Format: minute.csv je Familie, phase.log
    mit Schritten, Pausen und Luecken, ntp.csv, post-end-mempool.csv."""
    t0 = ms("2026-10-29T18:00:00Z")
    m0 = t0 // 60000
    # erfundene namen, erst zur laufzeit gebaut, kein echter host in der datei
    host = "-".join(["knoten", "7"]) + "." + "beispiel" + ".blue"
    plan = {m0 + i: (n, f) for n, a, b, f, _ in STORM for i in range(a, b)}
    with tempfile.TemporaryDirectory() as d:
        za, st = os.path.join(d, "zaehlung"), os.path.join(d, "stp", "logs")
        kopf = ["minute_utc", "k1_voll", "k2_voll", "knoten_gleich", "k1_cov_angenommen", "k1_cov_in_bloecken",
                "k1_cov_nie_angenommen"]
        for f in ("f1", "f2", "f3", "f4"):
            kopf += ["k1_cov_%s_angenommen" % f, "k1_cov_%s_nie_angenommen" % f]
        zeilen, mzeilen = [], []
        for i in range(-30, 90):
            m = m0 + i
            name, fams = plan.get(m, ("", 0))
            je = 42 if name not in ("", "pause") else 0
            zeilen.append([minute(m), 1, 1, 1, je * fams, je * fams, 0] + sum([[je if k < fams else 0, 0]
                                                                                for k in range(4)], []))
            if name and name != "pause":
                zeit = minute(m)[:16] + ":00Z"
                if m == m0 + 44:
                    # nur eine summenzeile, familie 0 darin nicht trennbar
                    mzeilen.append([zeit, name, "all", fams, 3900, 210, 3450, 170, 0, 0, 0, 0, 0, 70, 168, 168,
                                    1000, 2000, 900, 1800])
                    continue
                for k in range(fams):
                    sent = 900 if m != m0 + 25 else 400
                    falsch = 5 if (m == m0 + 33 and k == 1) else 0
                    mzeilen.append([zeit, name, k + 1, fams, sent, 50, 800, 40, 0, 0, 0, 0, 0,
                                    sent - 890 - falsch, 42, 42, 1000, 2000, 900, 1800])
                if m != m0 + 25:
                    # familie 0 ist KNS: grosse zahlen, die nirgends mitzaehlen duerfen
                    mzeilen.append([zeit, name, 0, fams, 300, 10, 250, 30, 0, 0, 0, 0, 0, 10, 9, 9,
                                    500, 900, 400, 800])
        schreib(os.path.join(za, "nach.csv"), kopf, zeilen)
        schreib(os.path.join(st, "minute.csv"),
                ["minute_utc", "step", "family", "families", "sent", "ok", "rej_already_spent", "rej_orphan",
                 "rej_fee", "rej_mass", "rej_mempool_full", "rej_route", "rej_rpc", "rej_other", "winners", "hops",
                 "include_p50_ms", "include_p95_ms", "seen_p50_ms", "seen_p95_ms"], mzeilen)
        log = ["2026-10-29T17:40:00Z MINER state=off workers=0",
               "2026-10-29T17:48:00Z GENESIS family=0 included",
               "2026-10-29T17:49:12Z GENESIS family=1 included",
               "2026-10-29T17:55:00Z FAMILY_DROP family=5 reason=no_genesis",
               "2026-10-29T18:00:01Z START senders=desk,mini,%s families=1 rate=5" % host,
               "2026-10-29T18:15:00Z GAP reason=sender_off",
               "2026-10-29T18:20:00Z STEP step=2 families=2 rate=5",
               "2026-10-29T18:28:10Z SENDER_OFF sender=desk reason=node_dead",
               "2026-10-29T18:30:05Z SENDER_ON sender=desk",
               "2026-10-29T18:35:00Z GAP reason=sender_off",
               "2026-10-29T18:40:00Z STEP step=3a families=4 rate=5",
               "2026-10-29T18:47:30Z NODE_SKIP node=%s reason=mempool_90k" % host,
               "2026-10-29T18:52:00Z MINER state=restart reason=watchdog",
               "2026-10-29T18:57:30Z MINER state=restart reason=watchdog",
               "2026-10-29T18:55:00Z STEP step=3b families=4 rate=5",
               "kaputte zeile ohne zeit",
               "2026-10-29T19:00:00Z STOP reason=END"]
        with open(os.path.join(st, "phase.log"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(log) + "\n")
        ntp_z = [["2026-10-29T16:00:00Z", "desk", -12, "zeit." + "beispiel" + ".net"]]
        for i, mas in enumerate(("desk", "mini", "box")):
            for pkt in ("16:00:20", "17:55:00", "19:01:00"):
                if mas == "desk" and pkt.startswith("16"):
                    continue
                ntp_z.append(["2026-10-29T%sZ" % pkt, mas, 31 if mas == "mini" else -4 - i, "w32tm"])
        schreib(os.path.join(st, "ntp.csv"), ["utc", "machine", "offset_ms", "source"], ntp_z)
        schreib(os.path.join(st, "post-end-mempool.csv"), ["minute_utc", "node", "mempool_size"],
                [["2026-10-29T19:00Z", "mini", 120], ["2026-10-29T19:00Z", host, 4000]])
        aus, zus = zusammensetzen(za, os.path.join(d, "stp"), "", t0, t0 + 3600000, "", "storm")
        buf = io.StringIO()
        csv.DictWriter(buf, fieldnames=spalten(aus)).writerows(aus)
        roh = buf.getvalue() + json.dumps(zus)
    r = {x["minute_utc"][11:16]: x for x in aus}
    ok("freeze: schritte und zaehlminuten laut plan", r["18:02"]["zaehlminute"] == 0 and r["18:03"]["zaehlminute"] == 1
       and r["18:15"]["schritt"] == "pause" and r["18:23"]["zaehlminute"] == 1 and r["18:55"]["schritt"] == "3b"
       and r["18:43"]["zaehlminute"] == 1 and r["18:59"]["zaehlminute"] == 1, [r["18:03"], r["18:55"]])
    ok("freeze: gezaehlt 12 + 12 + 17 minuten", sum(x["zaehlminute"] for x in aus) == 41)
    ok("freeze: 18:05 gueltig, konflikt 800 aus rej_already_spent", r["18:05"]["gueltig"] == 1
       and r["18:05"]["abgelehnt_konflikt"] == 800 and r["18:05"]["stp_winners"] == 42
       and r["18:05"]["abgleich_winners"] == 0 and r["18:05"]["sender_aktiv"] == 3, r["18:05"])
    ok("freeze: konflikte je familie summiert", r["18:45"]["abgelehnt_konflikt"] == 3200
       and r["18:45"]["stp_f4_rej_already_spent"] == 800 and r["18:45"]["familien"] == 4, r["18:45"])
    ok("freeze: sent = ok + rej geprueft", r["18:05"]["stp_summe_stimmt"] == 1 and r["18:05"]["stp_rej_andere"] == 10)
    ok("freeze: sender aus 18:28 bis 18:30 ungueltig, 18:31 wieder gueltig",
       all(r["18:%d" % k]["sender_luecke"] == "ja" for k in (28, 29, 30)) and r["18:31"]["gueltig"] == 1
       and "sender aus: desk" in r["18:29"]["grund"], [r["18:29"]["grund"], r["18:31"]["grund"]])
    ok("freeze: sent unter soll erkannt", "unter soll" in r["18:25"]["grund"], r["18:25"]["grund"])
    ok("freeze: node_skip nur in seiner minute, danach 2 sender", r["18:47"]["gueltig"] == 0
       and r["18:48"]["gueltig"] == 1 and r["18:48"]["sender_aktiv"] == 2, [r["18:47"]["grund"], r["18:48"]])
    ok("freeze: jede MINER-zeile markiert ihre minute, auch gleicher zustand", r["18:52"]["miner_wechsel"] == "ja"
       and r["18:57"]["miner_wechsel"] == "ja" and r["18:51"]["miner_wechsel"] == "nein" and r["18:53"]["gueltig"] == 1
       and "watchdog" in r["18:57"]["grund"], [r["18:57"]["grund"]])
    gez = [x["minute_utc"][11:16] for x in aus if x["zaehlminute"]]
    soll_min = ["18:%02d" % k for k in list(range(3, 15)) + list(range(23, 35)) + list(range(43, 60))]
    ok("freeze: gezaehlte minuten genau 18:03-18:14, 18:23-18:34, 18:43-18:59", gez == soll_min, gez)
    ok("freeze: familie 0 nie gezaehlt", "stp_f0_sent" not in r["18:05"] and r["18:05"]["stp_sent"] == 900
       and r["18:05"]["stp_winners"] == 42 and r["18:05"]["familien"] == 1 and r["18:05"]["stp_rej_orphan"] == 40
       and "f0" not in zus["stp_familien"], r["18:05"])
    ok("freeze: genesis familie 0 als nicht gezaehlt vermerkt", zus["phase_log"]["genesis"][0] == {
        "utc": "17:48:00", "familie": "f0", "gezaehlt": 0})
    ok("freeze: soll-pruefung mit familie 0, 18:05 kein fehlalarm", "unter soll" not in r["18:05"]["grund"])
    ok("freeze: summe je familie geprueft", r["18:33"]["stp_f2_summe_stimmt"] == 0
       and r["18:33"]["stp_f1_summe_stimmt"] == 1 and r["18:33"]["stp_summe_stimmt"] == 0
       and r["18:05"]["stp_f1_summe_stimmt"] == 1 and zus["summe_falsch"] == ["18:33 summe", "18:33 f2"],
       zus["summe_falsch"])
    ok("freeze: nur summenzeile, familie 0 nicht trennbar", r["18:44"]["stp_f0_trennbar"] == 0
       and r["18:44"]["stp_f1_sent"] == "" and zus["f0_nicht_trennbar"] == ["18:44"], r["18:44"])
    np_ = zus["ntp_pruefung"]
    ok("freeze: ntp drei maschinen, drei punkte, vollstaendig", np_["vollstaendig"] and np_["fehlt"] == []
       and np_["offset_ms"]["mini"]["17:55"] == 31 and np_["offset_ms"]["desk"]["16:00"] == -12
       and np_["offset_ms"]["box"]["19:01"] == -6, np_)
    ok("freeze: ntp ohne box 19:01 meldet die luecke", ntp_pruefen([x for x in zus["uhrversatz_stp"]
       if not (x["maschine"] == "box" and x["utc"].endswith("19:01:00Z"))], t0)["fehlt"] == ["box 19:01"])
    ok("freeze: step 3b um 18:55:00 ist eine wechsel-minute", r["18:55"]["gueltig"] == 0 and r["18:56"]["gueltig"] == 1)
    ok("freeze: pause ohne sender-luecke", r["18:17"]["sender_luecke"] == "pause" and r["18:17"]["gueltig"] == 0)
    js = zus["je_schritt"]
    ok("freeze: kopfzahl je schritt", js["1"]["hops_je_s_counted"] == 0.7 and js["2"]["hops_je_s_counted"] == 1.4
       and js["3"]["hops_je_s_counted"] == 2.8 and js["3"]["minuten_gezaehlt"] == 17
       and js["3"]["winners_je_s_source_stp"] == 2.8 and js["2"]["je_familie_counted"]["f2"] == 0.7, js)
    ok("freeze: phase.log in der zusammenfassung", zus["phase_log"]["unlesbare_zeilen"] == 1
       and zus["phase_log"]["family_drop"][0]["familie"] == "f5" and zus["phase_log"]["genesis"][1]["familie"] == "f1"
       and zus["phase_log"]["stop"][-1]["grund"] == "end", zus["phase_log"])
    ok("freeze: uhrversatz max 31 ms, quelle ohne hostname", zus["uhrversatz_max_ms"] == 31
       and zus["uhrversatz_stp"][0]["quelle"] == "server")
    ok("freeze: kein hostname, keine ip in der ausgabe", host not in roh and ".blue" not in roh
       and "beispiel" not in roh and "knoten1" in roh, roh[:200])
    hs = hash_zeilen("# kommentar\nf1 0x" + "AB" * 32 + "\nf2 " + "cd" * 32 + "\n")
    ok("hash: zwei familien, gleich wie nachzaehlung", hs == ["f1 " + cov_hash("ab" * 32), "f2 " + cov_hash("cd" * 32)])
    try:
        hash_zeilen("f1 " + "zz" * 32)
        ok("hash: falsche id bricht ab ohne die id zu zeigen", False)
    except ValueError as exc:
        ok("hash: falsche id bricht ab ohne die id zu zeigen", "zz" not in str(exc))
    try:
        hash_zeilen("f0 " + "ab" * 32)
        ok("hash: familie 0 abgelehnt", False)
    except ValueError as exc:
        ok("hash: familie 0 abgelehnt", "KNS" in str(exc))
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import tn10_nachzaehlung
        ok("hash: gleiche formel wie tn10_nachzaehlung", tn10_nachzaehlung.cov_hash("ab" * 32) == cov_hash("ab" * 32))
        n = tn10_nachzaehlung.familien_lesen("\n".join(hs))
        ok("hash: nachzaehlung liest die datei", list(n.values()) == ["f1", "f2"])
    except ImportError:
        ok("hash: tn10_nachzaehlung nicht gefunden", False)


def selbsttest_eingefroren(ok, schreib):
    """Format aus STPs eingefrorenem LOGGING.md (Freeze Di 27.10.2026, 18:00
    UTC): das Beispiel-phase.log mit GAP_START/GAP_END, MINER miner=, NTP und
    MAIN, minute.csv je Familie mit Pausenzeilen sent=0, sec.csv je Sekunde
    17:55 bis 18:59:59. Dazu derselbe Lauf mit T0 eine Stunde spaeter."""
    server = "zeit." + "beispiel" + ".org"
    for t0_txt in ("2026-10-29T18:00:00Z", "2026-10-29T19:00:00Z"):
        t0 = ms(t0_txt)
        m0 = t0 // 60000
        hm = lambda rel_s: dt.datetime.fromtimestamp(t0 / 1000 + rel_s, dt.timezone.utc).strftime(  # noqa: E731
            "%Y-%m-%dT%H:%M:%SZ")
        plan = {m0 + i: (n, f) for n, a, b, f, _ in STORM for i in range(a, b)}
        with tempfile.TemporaryDirectory() as d:
            za, st = os.path.join(d, "z"), os.path.join(d, "stp", "logs")
            kopf = ["minute_utc", "k1_voll", "k2_voll", "knoten_gleich", "k1_cov_angenommen", "k1_cov_in_bloecken",
                    "k1_cov_nie_angenommen"] + sum([["k1_cov_f%d_angenommen" % k, "k1_cov_f%d_nie_angenommen" % k]
                                                    for k in (1, 2, 3)], [])
            zeilen, mz, sec = [], [], []
            for i in range(-30, 90):
                m = m0 + i
                name, fams = plan.get(m, ("", 0))
                fams = min(fams, 3)                      # familie 4 im beispiel gedroppt
                an = 60 if name not in ("", "pause") else 0
                zeilen.append([minute(m), 1, 1, 1, an * fams, an * fams, 0] + sum(
                    [[an if k < fams else 0, 0] for k in range(3)], []))
                if name:
                    vorher = 1 if m < m0 + 20 else 2 if m < m0 + 40 else 3
                    for k in range(fams if name != "pause" else vorher):
                        sent = 0 if name == "pause" else 900
                        mz.append([minute(m), name if name != "pause" else "gap", k + 1, fams, sent,
                                   0 if not sent else 50, 0 if not sent else 800, 0 if not sent else 40,
                                   0, 0, 0, 0, 0, 0 if not sent else 10, an, an, "", "", "", ""])
            for sek in range(-300, 3600):
                name = plan.get((t0 // 1000 + sek) // 60, ("pre", 0))[0] if sek >= 0 else "pre"
                ziel = 0 if name in ("pre", "pause") else (3 if sek < 1531 else 2)
                an = ziel - (1 if 1550 <= sek < 1555 else 0)          # 18:25:50-54 ein sender aus
                sec.append([hm(sek), "gap" if name == "pause" else name, 0, ziel, an, an * 5, an])
            schreib(os.path.join(za, "nach.csv"), kopf, zeilen)
            schreib(os.path.join(st, "minute.csv"),
                    ["minute_utc", "step", "family", "families", "sent", "ok", "rej_already_spent", "rej_orphan",
                     "rej_fee", "rej_mass", "rej_mempool_full", "rej_route", "rej_rpc", "rej_other", "winners", "hops",
                     "include_p50_ms", "include_p95_ms", "seen_p50_ms", "seen_p95_ms"], mz)
            schreib(os.path.join(st, "sec.csv"),
                    ["utc_second", "step", "families", "senders_target", "senders_on", "sent", "ok"], sec)
            ntp = [[hm(rel * 60), mas, 12, server] for mas in ("desk", "mini", "box") for rel in (-120, -5, 61)]
            schreib(os.path.join(st, "ntp.csv"), ["utc", "machine", "offset_ms", "source"], ntp)
            log = [hm(-7196) + " NTP machine=mini offset_ms=125 source=" + server,
                   hm(-7000) + " MAIN node=mini reason=synced",
                   hm(-648) + " GENESIS family=1 included",
                   hm(-300) + " FAMILY_DROP family=4 reason=no_genesis",
                   hm(0) + " MINER state=on workers=3 miner=box",
                   hm(0) + " START senders=desk,mini,muon families=1 rate=5",
                   hm(0) + " STEP step=1 families=1 rate=5",
                   hm(451) + " NODE_DROP node=boson reason=redeem_shape",
                   hm(900) + " GAP_START", hm(1200) + " GAP_END",
                   hm(1200) + " STEP step=2 families=2 rate=5",
                   hm(1531) + " NODE_SKIP node=muon reason=mempool_90k",
                   hm(2100) + " GAP_START", hm(2400) + " GAP_END",
                   hm(2400) + " STEP step=3a families=3 rate=5",
                   hm(3300) + " STEP step=3b families=3 rate=5",
                   hm(3600) + " STOP reason=END"]
            with open(os.path.join(st, "phase.log"), "w", encoding="utf-8") as fh:
                fh.write("\n".join(log) + "\n")
            aus, zus = zusammensetzen(za, os.path.join(d, "stp"), "", t0, t0 + 3600000, "", "storm")
            buf = io.StringIO()
            csv.DictWriter(buf, fieldnames=spalten(aus)).writerows(aus)
            roh = buf.getvalue() + json.dumps(zus)
        r = {x["minute_utc"]: x for x in aus}
        mm = lambda k: minute(m0 + k)  # noqa: E731
        t = t0_txt[11:16]
        ok("eingefroren %s: 41 gezaehlte minuten" % t, sum(x["zaehlminute"] for x in aus) == 41)
        ok("eingefroren %s: minute 3 bis 14 sauber ausser der node_drop-minute 7" % t,
           [k for k in range(3, 15) if not r[mm(k)]["gueltig"]] == [7]
           and "NODE_DROP boson" in r[mm(7)]["grund"], [r[mm(k)]["grund"] for k in range(3, 15)])
        ok("eingefroren %s: pause mit sent=0-zeilen ohne fehlalarm" % t, r[mm(17)]["sender_luecke"] == "pause"
           and r[mm(17)]["stp_sent"] == 0 and r[mm(17)]["gueltig"] == 0)
        ok("eingefroren %s: node_skip-minute ungueltig, danach 2 sender sauber" % t,
           r[mm(25)]["gueltig"] == 0 and r[mm(26)]["gueltig"] == 1 and r[mm(26)]["sender_aktiv"] == 2,
           [r[mm(25)]["grund"], r[mm(26)]["grund"]])
        ok("eingefroren %s: sec.csv-luecke 5 sekunden erkannt" % t, "1 sekunden ohne sender" in r[mm(25)]["grund"]
           or "5 sekunden ohne sender" in r[mm(25)]["grund"], r[mm(25)]["grund"])
        ok("eingefroren %s: 3a und 3b mit 3 familien, step 3b-minute ungueltig" % t, r[mm(43)]["familien"] == 3
           and r[mm(55)]["gueltig"] == 0 and r[mm(56)]["gueltig"] == 1 and r[mm(59)]["gueltig"] == 1)
        ok("eingefroren %s: miner an ab t0, nur minute 0 markiert" % t, r[mm(0)]["miner_wechsel"] == "ja"
           and r[mm(3)]["miner_wechsel"] == "nein")
        ok("eingefroren %s: node_drop eines nicht geplanten knotens laesst 3 sender" % t,
           r[mm(8)]["sender_aktiv"] == 3 and r[mm(8)]["gueltig"] == 1
           and zus["phase_log"]["node_skip"][0]["grund"] == "redeem_shape")
        ok("eingefroren %s: ntp vollstaendig, punkte relativ zu t0" % t, zus["ntp_pruefung"]["vollstaendig"]
           and sorted(zus["ntp_pruefung"]["offset_ms"]["box"]) == sorted(
               dt.datetime.fromtimestamp(t0 / 1000 + rel * 60, dt.timezone.utc).strftime("%H:%M")
               for rel in (-120, -5, 61)), zus["ntp_pruefung"])
        ok("eingefroren %s: main und kopfzahl" % t, zus["phase_log"]["main"] == "mini"
           and zus["je_schritt"]["3"]["hops_je_s_counted"] == 3.0 and zus["je_schritt"]["1"]["minuten_gueltig"] == 11
           and zus["je_schritt"]["2"]["minuten_gueltig"] == 11 and zus["je_schritt"]["3"]["minuten_gueltig"] == 16,
           zus["je_schritt"])
        ok("eingefroren %s: kein zeitserver-name in der ausgabe" % t, "beispiel" not in roh)


def selbsttest_lauf(ok, schreib):
    """Laufdatei fuer Do 29.10. (19:00 bis 20:00 UTC) und eine abweichende
    Liste von STP, die dann gilt."""
    pfad = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "messung", "tn10", "lauf-2026-10-29.txt")
    t0, ende, gez = lauf_lesen(pfad)
    plan = {m for m, (_, z, _) in plan_schritte(t0, "storm").items() if z}
    ok("lauf 29.10.: t0 19:00, ende 20:00 utc", t0 == ms("2026-10-29T19:00:00Z") and ende == ms("2026-10-29T20:00:00Z"))
    ok("lauf 29.10.: ntp 17:00, 18:55, 20:01 utc", [minute(x // 60000)[11:16] for x in lauf_lesen.ntp]
       == ["17:00", "18:55", "20:01"], lauf_lesen.ntp)
    ok("lauf 29.10.: gezaehlt 19:03-19:14, 19:23-19:34, 19:43-19:59, gleich dem plan",
       sorted(minute(m)[11:16] for m in gez) == ["19:%02d" % k for k in
                                                  list(range(3, 15)) + list(range(23, 35)) + list(range(43, 60))]
       and gez == plan, sorted(minute(m)[11:16] for m in gez))
    with tempfile.TemporaryDirectory() as d:
        lf = os.path.join(d, "lauf.txt")
        with open(lf, "w", encoding="utf-8") as fh:
            fh.write("t0=2026-10-29T19:00:00Z\nende=2026-10-29T20:00:00Z\ngezaehlt=19:04-19:14,19:24-19:34,19:44-19:59\n")
        t0b, endeb, gezb = lauf_lesen(lf)
        za = os.path.join(d, "z")
        os.makedirs(za)
        aus, zus = zusammensetzen(za, "", "", t0b, endeb, "", "storm", "", gezb)
        r = {x["minute_utc"][11:16]: x for x in aus}
        ok("abweichende liste von stp gilt", r["19:03"]["zaehlminute"] == 0 and r["19:04"]["zaehlminute"] == 1
           and sum(x["zaehlminute"] for x in aus) == 38 and zus["zaehlminuten_weichen_vom_plan_ab"] is True
           and zus["zaehlminuten_quelle"] == "lauf-datei")
        with open(lf, "w", encoding="utf-8") as fh:
            fh.write("t0=2026-10-29T19:00:00Z\nende=2026-10-29T20:00:00Z\ngezaehlt=20:03-20:14\n")
        with open(lf, "w", encoding="utf-8") as fh:
            fh.write("t0=2026-10-29T19:00:00Z\nende=2026-10-29T20:00:00Z\nntp=16:00,17:55,19:01\n")
        lauf_lesen(lf)
        alt = [{"utc": "2026-10-29T%s:00Z" % p, "maschine": m, "offset_ms": 5} for m in NTP_MASCHINEN
               for p in ("16:00", "17:55", "19:01")]
        ok("ntp-zeiten aus der laufdatei", ntp_pruefen(alt, t0b, lauf_lesen.ntp)["vollstaendig"]
           and not ntp_pruefen(alt, t0b)["vollstaendig"])
        with open(lf, "w", encoding="utf-8") as fh:
            fh.write("t0=2026-10-29T19:00:00Z\nende=2026-10-29T20:00:00Z\ngezaehlt=20:03-20:14\n")
        try:
            lauf_lesen(lf)
            ok("minute ausserhalb des fensters bricht ab", False)
        except ValueError:
            ok("minute ausserhalb des fensters bricht ab", True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zaehlung", help="ordner mit nach.csv, k1-covenant.csv, k2-covenant.csv")
    ap.add_argument("--stp", default="", help="ordner mit STPs logs (bot/, build/)")
    ap.add_argument("--submit", default="", help="csv tx_id,submit_ms aus STPs logs, falls vorhanden")
    ap.add_argument("--fenster", nargs=2, metavar=("VON", "BIS"))
    ap.add_argument("--lauf", default="", help="laufdatei mit t0, ende, gezaehlt (statt --fenster)")
    ap.add_argument("--mempool", default="", help="ordner mit mempool-k1.json und mempool-k2.json")
    ap.add_argument("--plan", choices=["storm", "keiner"], default="storm",
                    help="storm: schritte und zaehlminuten laut STPs plan ab VON")
    ap.add_argument("--miner-aussage", default="",
                    help="kurzer satz aus dem eingefrorenen plan, etwa \"kein eigener miner\"")
    ap.add_argument("--out", default="out/contention")
    ap.add_argument("--hash", action="store_true",
                    help="zeilen \"f<n> <covenant-id>\" von stdin, ausgabe \"f<n> <sha256>\" fuer covenant.sha256")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.hash:
        try:
            print("\n".join(hash_zeilen(sys.stdin.read())))
        except ValueError as exc:
            print("abbruch: %s" % exc, file=sys.stderr)
            return 2
        return 0
    gez, ntp_punkte = None, None
    if a.lauf:
        von, bis, gez = lauf_lesen(a.lauf)
        ntp_punkte = lauf_lesen.ntp or None
    else:
        von, bis = ms(a.fenster[0]), ms(a.fenster[1])
    aus, zus = zusammensetzen(a.zaehlung, a.stp, a.submit, von, bis, a.mempool, a.plan, a.miner_aussage, gez, ntp_punkte)
    schreiben(a.out, aus, zus)
    print("minuten %d, im fenster %d, gueltig %d, submit-zeiten %d" % (
        len(aus), zus["minuten_im_fenster"], zus["gueltige_minuten"], zus["submit_zeiten"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
