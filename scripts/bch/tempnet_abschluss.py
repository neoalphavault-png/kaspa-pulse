#!/usr/bin/env python3
"""tempnet_abschluss.py - Zahlen fuer den Abschlussbericht des BCH Tempnet
(Ben, 09.11.2026, Teil C; Zusage im Forum #38).

1. Stale-Anteil getrennt nach Hochlast- und ruhigen Stunden (Wunsch rufitnes).
   Eine Stunde ist die UTC-Stunde der ersten Ankuendigung bei uns. Zwei
   Festlegungen, beide gezaehlt, beide werden genannt:
   - Blocklast: Stunden mit mindestens 2 x so vielen Kettenbloecken wie der
     Median aller abgedeckten Stunden.
   - Transaktionslast: Stunden, deren Transaktionen (Kurz-IDs plus
     vorbefuellte TX der Compact-Bloecke) im oberen Zehntel aller Stunden
     liegen (ab dem 90. Perzentil).
   Stale-Anteil wie in Woche 2 und 3: stale / (Kettenbloecke + stale),
   stale nach 6 Bestaetigungen.
2. Uhr des Messpunkts je Lauf aus meta.json ("uhr", chronyc tracking oder
   timedatectl), und welche Laeufe keinen Wert haben.
3. Abdeckung: Laeufe, Luecken zwischen Laeufen.

Eingang je Messpunkt: bloecke.csv und zusammenfassung.json von
lauscher_auswertung.py und die Lauf-Ordner mit meta.json.

  python3 scripts/bch/tempnet_abschluss.py --bloecke bloecke.csv --zusammenfassung zusammenfassung.json \\
      --laeufe <ordner>... --aus abschluss.json
  python3 scripts/bch/tempnet_abschluss.py --selbsttest
"""
import argparse
import csv
import json
import os
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone


def stunde(iso):
    return iso[:13] if iso else None


def zeit(iso):
    return datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def perzentil(werte, p):
    w = sorted(werte)
    if not w:
        return None
    k = (len(w) - 1) * p
    u = int(k)
    return w[u] + (w[min(u + 1, len(w) - 1)] - w[u]) * (k - u)


def stunden_zaehlen(bloecke, stale):
    kette, tx, st = defaultdict(int), defaultdict(int), defaultdict(int)
    for r in bloecke:
        h = stunde(r.get("first_seen_utc"))
        if not h:
            continue
        kette[h] += 1
        if r.get("short_ids"):
            tx[h] += int(r["short_ids"]) + int(r.get("prefilled") or 0)
    for s in stale:
        h = stunde(s.get("first_seen_utc"))
        if h:
            st[h] += 1
    return kette, tx, st


def anteil(stunden, kette, st):
    k = sum(kette[h] for h in stunden)
    s = sum(st[h] for h in stunden)
    return {"stunden": len(stunden), "kettenbloecke": k, "stale": s,
            "anteil_prozent": round(100 * s / (k + s), 3) if k + s else None}


def nach_last(kette, tx, st):
    stunden = sorted(kette)
    med = statistics.median(kette[h] for h in stunden)
    p90 = perzentil([tx[h] for h in stunden], 0.9)
    blocklast = [h for h in stunden if kette[h] >= 2 * med]
    txlast = [h for h in stunden if tx[h] >= p90]
    rest = lambda auswahl: [h for h in stunden if h not in set(auswahl)]  # noqa: E731
    return {
        "stunden_abgedeckt": len(stunden),
        "gesamt": anteil(stunden, kette, st),
        "blocklast": {"regel": f"kettenbloecke je stunde mindestens 2 x median ({med:g}), also ab {2 * med:g}",
                      "hochlast": anteil(blocklast, kette, st), "ruhig": anteil(rest(blocklast), kette, st),
                      "hochlast_stunden": blocklast},
        "transaktionslast": {"regel": f"transaktionen je stunde ab dem 90. perzentil ({p90:.0f})",
                             "hochlast": anteil(txlast, kette, st), "ruhig": anteil(rest(txlast), kette, st),
                             "hochlast_stunden": txlast},
    }


SEK = re.compile(r"([0-9.]+) seconds (slow|fast)")


def versatz_s(messung):
    """Systemzeit minus NTP-Zeit in Sekunden, positiv heisst die Uhr ging vor."""
    if not isinstance(messung, dict) or "werte" not in messung:
        return None
    w = messung["werte"]
    if "System time" in w:
        m = SEK.search(w["System time"])
        if m:
            return float(m.group(1)) * (1 if m.group(2) == "fast" else -1)
    if "Offset" in w:
        m = re.match(r"([+-]?[0-9.]+)(us|ms|s)", w["Offset"].replace("µs", "us").replace("+", ""))
        if m:
            return float(m.group(1)) * {"us": 1e-6, "ms": 1e-3, "s": 1.0}[m.group(2)]
    return None


def uhr_und_abdeckung(laeufe):
    zeilen, ohne = [], []
    fenster = []
    for o in sorted(laeufe):
        p = os.path.join(o, "meta.json")
        if not os.path.exists(p):
            continue
        meta = json.load(open(p))
        lauf = os.path.basename(os.path.normpath(o))
        start, ende = meta.get("start_utc"), meta.get("ende_utc")
        if start and ende:
            fenster.append((zeit(start), zeit(ende), lauf))
        uhr = meta.get("uhr")
        if not uhr:
            ohne.append(lauf)
            continue
        a, e = versatz_s(uhr.get("anfang")), versatz_s(uhr.get("ende"))
        if a is None and e is None:
            ohne.append(lauf)
        zeilen.append({"lauf": lauf, "anfang_s": a, "ende_s": e,
                       "quelle": (uhr.get("anfang") or {}).get("quelle") or (uhr.get("ende") or {}).get("quelle"),
                       "synchron_beim_start": uhr.get("synchron_beim_start")})
    werte = [abs(v) for z in zeilen for v in (z["anfang_s"], z["ende_s"]) if v is not None]
    luecken = []
    fenster.sort()
    # Laeufe koennen sich ueberlappen (Handlauf neben der Kette), deshalb gegen
    # das spaeteste Ende aller frueheren Laeufe vergleichen
    if fenster:
        e1, l1 = fenster[0][1], fenster[0][2]
        for s2, e2, l2 in fenster[1:]:
            if (s2 - e1).total_seconds() > 60:
                luecken.append({"nach": l1, "vor": l2, "von_utc": e1.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "bis_utc": s2.strftime("%Y-%m-%dT%H:%M:%SZ"), "min": round((s2 - e1).total_seconds() / 60, 1)})
            if e2 > e1:
                e1, l1 = e2, l2
    return {
        "uhr": {"laeufe_mit_wert": len([z for z in zeilen if z["anfang_s"] is not None or z["ende_s"] is not None]),
                "laeufe_ohne_wert": ohne, "betrag_max_s": max(werte) if werte else None,
                "betrag_median_s": statistics.median(werte) if werte else None, "je_lauf": zeilen},
        "abdeckung": {"laeufe": len(fenster),
                      "von_utc": fenster[0][0].strftime("%Y-%m-%dT%H:%M:%SZ") if fenster else None,
                      "bis_utc": fenster[-1][1].strftime("%Y-%m-%dT%H:%M:%SZ") if fenster else None,
                      "luecken_ueber_1_min": luecken},
    }


def auswerten(bloecke_pfad, zus_pfad, laeufe):
    bloecke = list(csv.DictReader(open(bloecke_pfad)))
    zus = json.load(open(zus_pfad))
    kette, tx, st = stunden_zaehlen(bloecke, zus["stale"]["bloecke"])
    out = {"stale_nach_last": nach_last(kette, tx, st)}
    out.update(uhr_und_abdeckung(laeufe))
    return out


def selbsttest():
    fehler = []
    def ok(name, bed):
        print(("ok   " if bed else "FEHL ") + name)
        if not bed:
            fehler.append(name)
    # 10 ruhige Stunden zu 60 Bloecken, eine Stunde mit 300 Bloecken und 30 stale
    bloecke, stale = [], []
    for h in range(11):
        n = 300 if h == 10 else 60
        for i in range(n):
            bloecke.append({"first_seen_utc": f"2026-11-01T{h:02d}:{i % 60:02d}:00.000Z",
                            "short_ids": "500" if h == 3 else "1", "prefilled": "1"})
    stale += [{"first_seen_utc": "2026-11-01T10:05:00.000Z"}] * 30 + [{"first_seen_utc": "2026-11-01T02:00:00.000Z"}]
    k, t, s = stunden_zaehlen(bloecke, stale)
    r = nach_last(k, t, s)
    ok("blocklast findet die stunde 10", r["blocklast"]["hochlast_stunden"] == ["2026-11-01T10"])
    ok("stale hochlast 30 von 330", r["blocklast"]["hochlast"]["anteil_prozent"] == round(100 * 30 / 330, 3))
    ok("stale ruhig 1 von 601", r["blocklast"]["ruhig"]["anteil_prozent"] == round(100 / 601, 3))
    ok("transaktionslast findet stunde 3", "2026-11-01T03" in r["transaktionslast"]["hochlast_stunden"])
    ok("versatz chronyc slow", versatz_s({"werte": {"System time": "0.000007619 seconds slow of NTP time"}}) == -0.000007619)
    ok("versatz chronyc fast", versatz_s({"werte": {"System time": "0.000001277 seconds fast of NTP time"}}) == 0.000001277)
    ok("versatz timedatectl", abs(versatz_s({"werte": {"Offset": "+1.250ms"}}) - 0.00125) < 1e-12)
    ok("ohne wert", versatz_s({"versatz": "nicht verfügbar"}) is None)
    print("alle testfaelle bestanden" if not fehler else f"{len(fehler)} fehler")
    return 1 if fehler else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--bloecke")
    ap.add_argument("--zusammenfassung")
    ap.add_argument("--laeufe", nargs="*", default=[])
    ap.add_argument("--aus")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    out = auswerten(a.bloecke, a.zusammenfassung, a.laeufe)
    json.dump(out, open(a.aus, "w"), indent=1, ensure_ascii=False)
    s = out["stale_nach_last"]
    for art in ("blocklast", "transaktionslast"):
        print(art, s[art]["regel"])
        for k in ("hochlast", "ruhig"):
            print("  ", k, s[art][k])
    print("gesamt", s["gesamt"])
    u = out["uhr"]
    print("uhr", u["laeufe_mit_wert"], "laeufe mit wert, ohne", len(u["laeufe_ohne_wert"]), "betrag max", u["betrag_max_s"])
    print("abdeckung", {k: v for k, v in out["abdeckung"].items() if k != "luecken_ueber_1_min"},
          "luecken", len(out["abdeckung"]["luecken_ueber_1_min"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
