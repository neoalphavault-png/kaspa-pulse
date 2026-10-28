#!/usr/bin/env python3
"""testnet_stall.py - lief die Zcash-Testnet-Kette ueber eine Hoehe hinaus? (Ben, 28.10.2026)

Anlass: ein zebrad 7.0.0 blieb oeffentlich gemeldet bei Testnet-Hoehe 4.548.314
stehen. Eingang: eigene Koepfe aus zcash_koepfe.py --netz testnet (Verkettung,
Arbeitsnachweis, Zebra-Checkpoints geprueft). Ausgang:
- Hash und Zeit der Hoehe und der 20 Bloecke danach,
- Abstaende im Fenster +-500 Bloecke (Median, laengste Luecke),
- Abzweig-Probe: weitere Peers liefern je ab 50 Bloecke vor der Hoehe bis
  550 danach; verglichen wird Hash fuer Hash mit unserer Kette. Weicht ein
  Peer ab, steht die erste abweichende Hoehe und seine Software in der Ausgabe.
Keine Adressen in Ausgabe oder Log, nur die Software der Peers.

  python3 scripts/zcash/testnet_stall.py --koepfe k.csv.gz --meta m.json --hoehe 4548314 --json s.json --md s.md
"""
import argparse
import csv
import gzip
import json
import os
import statistics
import struct
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zcash_koepfe as Z  # noqa: E402


def utc(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def abzweig_probe(kette, hoehe, n_peers=3, budget_s=420):
    """Fragt weitere Peers nach dem Stueck hoehe-50 bis hoehe+550 und vergleicht."""
    nach_h = {h: bytes.fromhex(x)[::-1] for h, (x, _) in kette.items()}
    von = hoehe - 50
    loc = [nach_h[von - i] for i in (0, 1, 2, 3, 5, 10, 20, 50) if von - i in nach_h]
    adressen, benutzt, proben = Z.peers_finden(), set(), []
    ende = time.time() + budget_s
    while len(proben) < n_peers and time.time() < ende:
        a, p = Z.verbinden(adressen, benutzt, mindesthoehe=hoehe)
        if p is None:
            break
        benutzt.add(a)
        try:
            roh, h_loc = [], loc
            while len(roh) < 600:
                stueck = p.koepfe(h_loc, warten=45)
                if not stueck:
                    break
                roh += stueck
                h_loc = [Z.sha256d(stueck[-1])]
            hoehe_von = {x: h for h, x in nach_h.items()}
            ab = hoehe_von.get(roh[0][4:36], von) + 1 if roh else von + 1
            paare = [(ab + i, Z.sha256d(r)) for i, r in enumerate(roh) if ab + i in nach_h]
            gleich = sum(1 for h, x in paare if x == nach_h[h])
            erste_abw = next((h for h, x in paare if x != nach_h[h]), None)
            proben.append({"software": p.agent, "von": ab, "bis": ab + len(roh) - 1, "verglichen": len(paare),
                           "gleich": gleich, "erste_abweichung": erste_abw, "gemeldete_hoehe": p.hoehe})
            Z.log(f"probe {p.agent}: {gleich}/{len(paare)} gleich")
        except (OSError, ConnectionError, TimeoutError, struct.error, IndexError) as e:
            Z.log(f"probe {p.agent} ohne antwort ({type(e).__name__})")
        p.zu()
    return proben


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--koepfe", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--hoehe", type=int, required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--md", required=True)
    args = ap.parse_args()
    Z.netz_setzen("testnet")
    H = args.hoehe
    meta = json.load(open(args.meta))
    with gzip.open(args.koepfe, "rt") as f:
        kette = {int(z["hoehe"]): (z["hash"], int(z["zeit"])) for z in csv.DictReader(f)}
    spitze = max(kette)
    folge = [{"hoehe": h, "hash": kette[h][0], "zeit_utc": utc(kette[h][1]),
              "abstand_s": kette[h][1] - kette[h - 1][1] if h - 1 in kette else None}
             for h in range(H, min(H + 22, spitze + 1))]
    fenster = [(h, kette[h][1] - kette[h - 1][1]) for h in range(H - 500, H + 501) if h in kette and h - 1 in kette]
    lang = max(fenster, key=lambda x: x[1]) if fenster else None
    r = {
        "hoehe": H, "spitze": spitze, "spitze_utc": utc(kette[spitze][1]), "abruf_utc": meta["abruf_utc"],
        "lief_weiter": spitze > H, "bloecke_danach": spitze - H,
        "folge": folge,
        "fenster": {"von": fenster[0][0] if fenster else None, "bis": fenster[-1][0] if fenster else None,
                    "abstaende": len(fenster), "median_s": statistics.median([a for _, a in fenster]) if fenster else None,
                    "mittel_s": round(statistics.fmean([a for _, a in fenster]), 2) if fenster else None,
                    "laengste_luecke_s": lang[1] if lang else None, "laengste_luecke_vor_block": lang[0] if lang else None,
                    "laengste_luecke_utc": utc(kette[lang[0]][1]) if lang else None},
        "abruf": {k: meta.get(k) for k in ("peer_software", "peer_fehler", "abzweige_verworfen", "gegenproben",
                                           "checkpoints_geprueft", "zielhoehe_gemeldet")},
    }
    r["abzweig_probe"] = abzweig_probe(kette, H) if spitze >= H else []
    with open(args.json, "w") as f:
        json.dump(r, f, indent=2, ensure_ascii=False)
        f.write("\n")
    F = r["fenster"]
    z = [f"Spitze {spitze:,} ({r['spitze_utc']} UTC), Abruf {r['abruf_utc']}. Kette lief weiter: {'ja' if r['lief_weiter'] else 'nein'}, "
         f"{r['bloecke_danach']:,} Blöcke nach {H:,}.", "",
         "| Höhe | Hash | Zeit UTC | Abstand |", "|---:|---|---|---:|"]
    z += [f"| {b['hoehe']:,} | `{b['hash']}` | {b['zeit_utc']} | {b['abstand_s'] if b['abstand_s'] is not None else ''} s |" for b in folge]
    z += ["", f"Fenster {F['von']:,} bis {F['bis']:,}: {F['abstaende']} Abstände, Median {F['median_s']} s, Mittel {F['mittel_s']} s, "
          f"längste Lücke {F['laengste_luecke_s']} s vor Block {F['laengste_luecke_vor_block']:,} ({F['laengste_luecke_utc']} UTC).", "",
          "Abzweig-Probe: " + "; ".join(f"{p['software']} {p['gleich']}/{p['verglichen']} gleich ({p['von']:,} bis {p['bis']:,})"
                                         + (f", erste Abweichung {p['erste_abweichung']:,}" if p["erste_abweichung"] else "")
                                         for p in r["abzweig_probe"]),
          "Abruf: verworfene Zweige " + json.dumps(r["abruf"]["abzweige_verworfen"], ensure_ascii=False)
          + ", Gegenproben " + "; ".join(f"{g['agent']} {g['gleich']}/{g['verglichen']}" for g in r["abruf"]["gegenproben"] or [])]
    with open(args.md, "w") as f:
        f.write("\n".join(z) + "\n")
    print("\n".join(z))


if __name__ == "__main__":
    main()
