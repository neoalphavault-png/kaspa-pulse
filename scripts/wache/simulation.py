#!/usr/bin/env python3
"""simulation.py - Upgrade-Wache gegen aufgezeichnete Daten pruefen (Ben, 29.10.2026, Punkt 6).

Grundlage ist die echte Aufzeichnung unseres Zuhoerers im Zcash-Testnet vom
17.10.2026 (5,5 h, 776 Kettenbloecke, 5 abgehaengte Bloecke der Tiefe 1) und
die geprueften Testnet-Koepfe (messung/zcash-nu7). Der Kern ist derselbe wie
im Betrieb; nur Uhr und Quelle sind simuliert. Die Aktivierungshoehe legt die
Simulation in die Aufzeichnung, damit alle Signale ab der Aktivierung greifen.

Je Signal ein Szenario, gebaut aus der Aufzeichnung:
  grundlage       unveraendert: darf nur die Peer-Anteile melden (info), die
                  fuenf abgehaengten Bloecke der Tiefe 1 duerfen nichts ausloesen
  blockpause      25 min lang keine Ankuendigung und kein Kopf
  kettenspaltung  ein zweiter Zweig von 4 Bloecken ab Aktivierung + 30,
                  angekuendigt von 2 Peers
  reorg           ein Zweig von 2 Bloecken kommt jeweils 3 s vor der Kette an
                  und wird dann von ihr ueberholt (Tiefe 2)
  median_abstand  14 Koepfe mit 120 s Abstand im Zeitstempel (Ziel 25 s)
  eigene_sicht    10 min lang nur 1 Verbindung: Hinweis, keine Blockpause
peers_vor_upgrade laeuft in jedem Szenario (Probe zur Aktivierung und nach 1 h,
in der Simulation statt 6 h, weil die Aufzeichnung 5,5 h lang ist).

  python3 scripts/wache/simulation.py --ereignisse e.jsonl.gz --koepfe k.jsonl.gz --meta m.json \\
      --kette testnet-koepfe.csv.gz --aus ordner [--senden]

--senden: je Signal genau eine Beispielmeldung mit "TEST" an den Webhook der
Konfiguration (DISCORD_WEBHOOK_LOG, #ops-log), dazu eine Entwarnung.
"""
import argparse
import copy
import csv
import gzip
import hashlib
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
from wache_kern import Kern, Melder, SimUhr, ts  # noqa: E402

AKT_VERSATZ_BLOECKE = 60   # Aktivierung so viele Kettenbloecke nach Beginn der Aufzeichnung


def jsonl(pfad):
    with gzip.open(pfad, "rt") as f:
        return [json.loads(z) for z in f if z.strip()]


def kunsthash(text):
    return "0000" + hashlib.sha256(text.encode()).hexdigest()[4:]


class SimQuelle:
    def __init__(self, peers, uhr):
        self.peers, self.uhr = peers, uhr

    def verbunden_zu(self, t):
        return [p for p in self.peers if p["von"] <= t < p["bis"]]

    def probe(self):
        return [p["version"] for p in self.verbunden_zu(self.uhr.jetzt())]


def laden(args):
    ereignisse = jsonl(args.ereignisse)
    koepfe = {k["hash"]: k for k in jsonl(args.koepfe)}
    meta = json.load(open(args.meta))
    with gzip.open(args.kette, "rt") as f:
        kette = [(int(z["hoehe"]), z["hash"], int(z["zeit"]), z["nbits"]) for z in csv.DictReader(f)]
    hoehe_von = {h: hh for hh, h, _, _ in kette}
    ende = ts(meta["ende_utc"])
    peers = [{"label": p["peer"], "version": p["version"], "von": ts(p["verbunden_utc"]),
              "bis": ts(p["getrennt_utc"]) if p.get("getrennt_utc") else ende} for p in meta["peers"]]
    return ereignisse, koepfe, meta, kette, hoehe_von, peers


def ereignisliste(ereignisse, koepfe):
    """(t, art, daten): Ankuendigungen zur Ankunftszeit, Koepfe bei der ersten Ankuendigung."""
    out, gesehen = [], set()
    for e in sorted(ereignisse, key=lambda x: x["t_ms"]):
        out.append((e["t_ms"] / 1000, "ann", (e["t_ms"], e["peer"], e["hash"])))
        if e["hash"] not in gesehen and e["hash"] in koepfe:
            gesehen.add(e["hash"])
            k = koepfe[e["hash"]]
            out.append((e["t_ms"] / 1000 + 0.001, "kopf", (k["hash"], k["prev"], k["zeit"], k["nbits"])))
    return out


def erste_ankunft(liste):
    erst = {}
    for t, art, d in liste:
        if art == "ann":
            erst.setdefault(d[2], t)
    return erst


# ---------------------------------------------------------------- szenarien
def sz_blockpause(liste, ctx):
    """Das Netz liefert 25 min lang nichts: alles ab t0 kommt 25 min spaeter an."""
    t0, pause = ctx["t_akt"] + 2 * 3600, 25 * 60
    out = []
    for t, art, d in liste:
        if t >= t0:
            t += pause
            if art == "ann":
                d = (d[0] + pause * 1000, d[1], d[2])
        out.append((t, art, d))
    return out, {}


def sz_kettenspaltung(liste, ctx):
    kette, erst = ctx["kette_im_fenster"], ctx["erst"]
    i0 = ctx["i_akt"] + 30
    neu, prev = [], kette[i0 - 1][1]
    for j in range(4):
        hh, h, zeit, nbits = kette[i0 + j]
        if h not in erst:
            break
        b = kunsthash(f"spaltung-{j}")
        t = erst[h] + 5
        neu.append((t, "kopf", (b, prev, zeit + 3, nbits)))
        for p in ("zakura-1", "zakura-2"):
            neu.append((t + 0.01, "ann", (int(t * 1000) + 10, p, b)))
        prev = b
    return sorted(liste + neu, key=lambda e: e[0]), {}


def sz_reorg(liste, ctx):
    kette, erst = ctx["kette_im_fenster"], ctx["erst"]
    i0 = ctx["i_akt"] + 120
    neu, prev = [], kette[i0 - 1][1]
    for j in range(2):
        hh, h, zeit, nbits = kette[i0 + j]
        b = kunsthash(f"reorg-{j}")
        t = erst[h] - 3
        neu.append((t - 0.001, "ann", (int(t * 1000), "zebra-1", b)))
        neu.append((t, "kopf", (b, prev, zeit - 1, nbits)))
        prev = b
    return sorted(liste + neu, key=lambda e: e[0]), {}


def sz_median(liste, ctx):
    kette = ctx["kette_im_fenster"]
    i0 = ctx["i_akt"] + 200
    basis = kette[i0 - 1][2]
    neue_zeit = {kette[i0 + j][1]: basis + 120 * (j + 1) for j in range(14)}
    out = []
    for t, art, d in liste:
        if art == "kopf" and d[0] in neue_zeit:
            d = (d[0], d[1], neue_zeit[d[0]], d[3])
        out.append((t, art, d))
    return out, {}


def sz_eigene_sicht(liste, ctx):
    t0 = ctx["t_akt"] + 3 * 3600
    return liste, {"blind": (t0, t0 + 10 * 60)}


SZENARIEN = {
    "grundlage": (lambda l, c: (l, {}), {("peers_vor_upgrade", "info")}),
    "blockpause": (sz_blockpause, {("blockpause", "alarm"), ("blockpause", "entwarnung")}),
    "kettenspaltung": (sz_kettenspaltung, {("kettenspaltung", "alarm")}),
    "reorg": (sz_reorg, {("reorg", "alarm")}),
    "median_abstand": (sz_median, {("median_abstand", "alarm")}),
    "eigene_sicht": (sz_eigene_sicht, {("eigene_sicht", "hinweis")}),
}

ERWARTET = {
    "grundlage": {"alarm": set(), "hinweis": set()},
    "blockpause": {"alarm": {"blockpause"}, "hinweis": {"blockpause"}},
    "kettenspaltung": {"alarm": {"kettenspaltung"}, "hinweis": set()},
    "reorg": {"alarm": {"reorg"}, "hinweis": set()},
    "median_abstand": {"alarm": {"median_abstand"}, "hinweis": set()},
    "eigene_sicht": {"alarm": set(), "hinweis": {"eigene_sicht"}},
}


def lauf(name, cfg, liste, ctx, peers, aus, senden):
    bau, beispiele = SZENARIEN[name]
    liste, extra = bau(liste, ctx)
    uhr = SimUhr(liste[0][0])
    melder = Melder(cfg["meldung"]["webhook_env"], scharf=senden, test=True,
                    nur=set(beispiele) if senden else None)
    log_pfad = os.path.join(aus, f"{name}-wache-log.csv")
    if os.path.exists(log_pfad):
        os.remove(log_pfad)
    quelle = SimQuelle(peers, uhr)
    kern = Kern(cfg, uhr, melder, log_pfad, quelle=quelle)
    kern.anker(ctx["anker"])
    takt = cfg["takt_s"]
    naechster = liste[0][0] + takt
    blind = extra.get("blind")
    for t, art, d in liste:
        while t >= naechster:
            uhr.t = naechster
            n = len(quelle.verbunden_zu(naechster))
            kern.verbindungen(1 if blind and blind[0] <= naechster < blind[1] else n)
            kern.takt()
            naechster += takt
        uhr.t = t
        if art == "ann":
            kern.ankuendigung(*d)
        else:
            kern.kopf(*d)
    # nach dem letzten Ereignis noch 40 min weiterlaufen lassen (Entwarnungen, Ruhezeiten)
    for _ in range(40):
        uhr.t = naechster
        kern.verbindungen(len(quelle.verbunden_zu(ctx["t_letzt"] - 1)))
        kern.takt()
        naechster += takt

    with open(log_pfad) as f:
        alle = list(csv.DictReader(f))
    # Gewertet wird nur bis zum Ende der Aufzeichnung. Danach kommen keine
    # Ereignisse mehr, die Wache meldet dann zu Recht Blockpause und Blindheit.
    zeilen = [z for z in alle if z["utc"] < ctx["ende_utc"]]
    stufen = {s: {z["signal"] for z in zeilen if z["stufe"] == s} for s in ("alarm", "hinweis", "entwarnung", "info")}
    soll = ERWARTET[name]
    ok = (stufen["alarm"] == soll["alarm"] and stufen["hinweis"] == soll["hinweis"]
          and all(s in stufen["entwarnung"] for s in soll["alarm"] | soll["hinweis"]))
    fehl_pausen = [z for z in zeilen if z["signal"] == "blockpause" and z["stufe"] in ("hinweis", "alarm")] \
        if name != "blockpause" else []
    return {"szenario": name, "ok": ok, "alarm": sorted(stufen["alarm"]), "hinweis": sorted(stufen["hinweis"]),
            "entwarnung": sorted(stufen["entwarnung"]), "info": sorted(stufen["info"]),
            "meldungen": melder.gesendet, "fehl_blockpausen": len(fehl_pausen),
            "reorg_gesehen": [(z["utc"], z["hoehe"], z["wert"]) for z in zeilen if z["signal"] == "reorg_gesehen"],
            "log": os.path.basename(log_pfad)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ereignisse", required=True)
    ap.add_argument("--koepfe", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--kette", required=True, help="gepruefte Koepfe (zcash_koepfe.py) fuer die Hoehen")
    ap.add_argument("--konfig", default=os.path.join(HIER, "ketten", "zcash-mainnet.json"))
    ap.add_argument("--aus", required=True)
    ap.add_argument("--senden", action="store_true")
    ap.add_argument("--nur")
    args = ap.parse_args()
    os.makedirs(args.aus, exist_ok=True)

    ereignisse, koepfe, meta, kette, hoehe_von, peers = laden(args)
    liste = ereignisliste(ereignisse, koepfe)
    erst = erste_ankunft(liste)
    t_start = liste[0][0]
    # Kettenbloecke, die in der Aufzeichnung angekuendigt wurden
    im_fenster = [z for z in kette if z[1] in erst]
    i_erst = kette.index(im_fenster[0])
    kette_ab = kette[i_erst:]
    akt = kette_ab[AKT_VERSATZ_BLOECKE]
    anker = [z for z in kette[max(0, i_erst - 300):i_erst]]

    cfg = copy.deepcopy(json.load(open(args.konfig)))
    cfg["kette"] = cfg["kette"] + "-simulation"
    cfg["aktivierung"].update(hoehe=akt[0], erwartet_utc=meta["start_utc"])
    cfg["fenster"]["vor_h"] = 0
    # Testnet laeuft seit NU7 (04.10.2026) mit 25 s; die Simulation rechnet beide Seiten mit 25 s.
    cfg["ziel_s"] = cfg["ziel_nach_s"] = 25
    cfg["signale"]["peers_vor_upgrade"]["zeitpunkte_h"] = [0, 1]
    ctx = {"kette_im_fenster": kette_ab, "erst": erst, "i_akt": AKT_VERSATZ_BLOECKE, "anker": anker,
           "t_akt": erst[akt[1]], "t_letzt": liste[-1][0], "ende_utc": meta["ende_utc"].replace("T", " ")[:19]}

    ergebnisse = []
    for name in SZENARIEN:
        if args.nur and name not in args.nur.split(","):
            continue
        r = lauf(name, cfg, liste, ctx, peers, args.aus, args.senden)
        ergebnisse.append(r)
        print(f"{'ok  ' if r['ok'] else 'FEHL'} {name}: alarm {r['alarm']} hinweis {r['hinweis']} "
              f"entwarnung {r['entwarnung']} info {r['info']}", flush=True)
    zus = {"grundlage": {"aufzeichnung": f"{meta['start_utc']} bis {meta['ende_utc']}", "netz": "zcash testnet",
                         "kettenbloecke": len(im_fenster), "aktivierung_simuliert": akt[0],
                         "peers": len(peers)},
           "alle_ok": all(r["ok"] for r in ergebnisse), "szenarien": ergebnisse}
    with open(os.path.join(args.aus, "simulation.json"), "w") as f:
        json.dump(zus, f, indent=1, ensure_ascii=False)
    print(json.dumps({"alle_ok": zus["alle_ok"], "szenarien": len(ergebnisse)}))
    sys.exit(0 if zus["alle_ok"] else 1)


if __name__ == "__main__":
    main()
