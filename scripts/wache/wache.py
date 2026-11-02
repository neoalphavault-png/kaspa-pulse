#!/usr/bin/env python3
"""wache.py - Upgrade-Wache: startet Quelle und Kern fuer eine Chain-Konfiguration.

Ben, 29.10.2026 (Prototyp "Upgrade-Wache Zcash NU7"). Laeuft auf c2 als
Dauerdienst (deploy/c2/upgrade-wache/), Takt aus der Konfiguration (60 s).
Ausserhalb des Fensters (Aktivierung minus vor_h bis plus nach_h) ruht die
Wache: keine Verbindungen, nur eine Logzeile je Stunde. Zehn Minuten vor dem
Fenster verbindet sie sich, damit die Hoehen zum Fensterbeginn verankert sind.

  python3 scripts/wache/wache.py --kette scripts/wache/ketten/zcash-mainnet.json \\
      --ablage /var/lib/kaspa-pulse/wache/zcash-mainnet [--trocken] [--test] [--fenster-offen] [--dauer-min N]

--trocken      Meldungen nur ausgeben, nichts senden
--test         jeder Meldung "TEST" voranstellen
--fenster-offen  Fenster ab jetzt (fuer den Probelauf), Aktivierung bleibt wie konfiguriert
--dauer-min N  nach N Minuten beenden (Probelauf); ohne: bis zum Ende des Fensters
--probe        nur die Peer-Probe (Signal d) einmal ausfuehren und den Anteil zeigen
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
from wache_kern import Kern, Melder, Uhr, utc  # noqa: E402

VORLAUF_S = 600


def quelle_bauen(cfg, roh):
    art = cfg["quelle"]["art"]
    if art == "zcash_p2p":
        from quelle_zcash import QuelleZcash
        return QuelleZcash(cfg, roh)
    raise SystemExit(f"quelle {art!r} ist noch nicht gebaut")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kette", required=True)
    ap.add_argument("--ablage", required=True)
    ap.add_argument("--trocken", action="store_true")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--fenster-offen", action="store_true")
    ap.add_argument("--dauer-min", type=float)
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()

    cfg = json.load(open(args.kette))
    if args.probe:
        q = quelle_bauen(cfg, os.path.join(args.ablage, "roh"))
        v = q.probe()
        alt = sum(1 for x in v if x < cfg["min_protokoll"])
        print(json.dumps({"peers": len(v), "unter_min_protokoll": alt,
                          "anteil_prozent": round(100 * alt / len(v), 1) if v else None,
                          "versionen": {str(x): v.count(x) for x in sorted(set(v))}}), flush=True)
        return
    if args.fenster_offen:
        # Fenster ab jetzt: erwartete Aktivierung so legen, dass jetzt = Fensterbeginn
        vor = cfg["fenster"]["vor_h"]
        cfg["aktivierung"]["erwartet_utc"] = (datetime.now(timezone.utc) + timedelta(hours=vor)).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
    os.makedirs(args.ablage, exist_ok=True)
    melder = Melder(cfg["meldung"]["webhook_env"], scharf=cfg["scharf"] and not args.trocken, test=args.test)
    kern = Kern(cfg, Uhr(), melder, os.path.join(args.ablage, "wache-log.csv"),
                os.path.join(args.ablage, "zustand.json"))
    takt = cfg["takt_s"]
    schluss = time.time() + args.dauer_min * 60 if args.dauer_min else None
    quelle, letzte_ruhe, letzter_lauf = None, 0, 0
    offen, start, ende = kern.fenster(time.time())
    print(f"wache {cfg['kette']}: fenster {utc(start)} bis {utc(ende)} UTC, "
          f"{'scharf' if melder.scharf else 'trocken'}{', test' if args.test else ''}", flush=True)
    kern.log(None, "wache", 0, 0, "start")

    while schluss is None or time.time() < schluss:
        jetzt = time.time()
        offen, start, ende = kern.fenster(jetzt)
        if jetzt >= ende:
            if jetzt - letzte_ruhe >= 3600:
                kern.log(None, "wache", 0, 0, "fenster_zu")
                print(f"{utc(jetzt)} fenster zu, wache ruht", flush=True)
                letzte_ruhe = jetzt
            time.sleep(takt)
            continue
        if jetzt < start - VORLAUF_S:
            if jetzt - letzte_ruhe >= 3600:
                kern.log(None, "wache", round((start - jetzt) / 3600, 1), 0, "ruht")
                print(f"{utc(jetzt)} ruht, fenster ab {utc(start)} UTC", flush=True)
                letzte_ruhe = jetzt
            time.sleep(min(takt, max(1, start - VORLAUF_S - jetzt)))
            continue
        if quelle is None:
            quelle = quelle_bauen(cfg, os.path.join(args.ablage, "roh"))
            kern.quelle = quelle
        quelle.abholen(kern)
        kern.takt()
        if jetzt - letzter_lauf >= 3600:
            st = kern.stand()
            kern.log(st["hoehe"], "wache", st["verbunden"], cfg["signale"]["eigene_sicht"]["min_verbindungen"], "lauf")
            letzter_lauf = jetzt
        if int(jetzt) % 600 < takt:
            print(f"{utc(jetzt)} {json.dumps(kern.stand())}", flush=True)
        time.sleep(max(1, takt - (time.time() - jetzt)))
    kern.log(kern.stand()["hoehe"], "wache", 0, 0, "ende")
    print(json.dumps({"stand": kern.stand(), "meldungen": len(melder.gesendet)}), flush=True)


if __name__ == "__main__":
    main()
