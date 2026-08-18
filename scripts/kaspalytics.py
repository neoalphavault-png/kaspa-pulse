#!/usr/bin/env python3
"""
holt die sechs handzahlen bei kaspalytics selbst

Bis zum 17.08.2026 hat Ben diese Zahlen jede Woche von Hand aus Diagrammen
abgelesen und mir als Screenshot geschickt. Sechs Seitenaufrufe, zwei Runden
hin und her, und jedes Mal die Gefahr, dass ein Wert aus dem falschen
Diagramm stammt. Am 18.08. haben wir im Netzwerk-Tab gesehen, dass die
Seite ihre Diagramme selbst per JSON laedt, oeffentlich, ohne Anmeldung.

    /app/covenants/transactions   ist die seite
    /api/charts/covenants/transactions   sind die daten dazu

Jede Antwort hat dieselbe Form.

    { "labels": ["2026-08-17T00:00:00.000Z", ...],
      "datasets": [ {"label": "Transactions", "data": [...]}, ... ] }

Regeln, die hier drinstecken und nicht verhandelbar sind.

  1. Wir lesen IMMER den letzten VOLLEN tag, also nie den laufenden.
     Der laufende Tag ist angebrochen und war schon zweimal die Ursache
     fuer einen Sprung, den es nie gab (siehe Serien-Entscheidung 2).
  2. Jede Zahl faellt durch ein Plausibilitaetsfenster. Lieber ein Feld
     leer als ein falsches. Ein leeres Feld zeigt auf der Seite einen
     Strich, und ein Strich ist ehrlich.
  3. Faellt eine Quelle aus, bleiben die anderen fuenf trotzdem stehen.

    python3 scripts/kaspalytics.py            # zahlen holen und drucken
    python3 scripts/kaspalytics.py --json     # nur der block fuer die eingabedatei
    python3 scripts/kaspalytics.py --selftest
"""

import datetime as dt
import json
import sys
import urllib.request

BASIS = "https://www.kaspalytics.com/api/charts/"
TIMEOUT = 25
VERSUCHE = 3

# feld -> (pfad, reihe, umrechnung)
# die reihe ist der "label"-eintrag im datasets-array. Preis ignorieren wir,
# den holen wir woanders sauberer.
QUELLEN = {
    "active_addr":  ("transactions/accepted/addresses/all", ["Addresses"], "int"),
    "holder_addr":  ("address/count/meaningful-balance", ["Addresses"], "int"),
    "holders":      ("supply/inactive?minAge=1year", ["CSPERCENT"], "pct"),
    "exchange_kas": ("supply/exchange-holdings", ["Balance"], "int"),
    "covenant_tx":  ("covenants/transactions", ["Transactions"], "int"),
    # tps ist die einzige rechnung. akzeptierte transaktionen am tag,
    # standard plus coinbase, geteilt durch die sekunden eines tages.
    # NICHT die tps-kachel auf kaspa.stream, die zaehlt die bloecke mit
    # und steht deshalb bei elf statt bei zwei.
    "tps":          ("transactions/accepted/count", ["Standard", "Coinbase"], "tps"),
}

# Bot-Regel 10, um jeden fremdwert ein fenster
FENSTER = {
    "active_addr":  (100, 5e7),
    "holder_addr":  (10000, 5e8),
    "holders":      (0.0, 100.0),
    "exchange_kas": (1e6, 3e10),
    "covenant_tx":  (0, 1e7),
    "tps":          (0.0, 3000.0),
}

SEKUNDEN_TAG = 86400


def hole(pfad):
    """eine antwort holen. drei versuche, dann ehrlich scheitern."""
    url = BASIS + pfad
    letzter = None
    for _ in range(VERSUCHE):
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/json",
                "User-Agent": "kaspa-pulse-bot (+https://kaspapulse.com)",
            })
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:      # noqa: BLE001
            letzter = exc
    raise RuntimeError("%s nicht erreichbar, %s" % (pfad, letzter))


def tag_von(label):
    """aus dem zeitstempel den kalendertag in UTC."""
    s = str(label).replace("Z", "").split("T")[0]
    return dt.date.fromisoformat(s)


def reihe(daten, name):
    for d in daten.get("datasets") or []:
        if str(d.get("label", "")).strip().lower() == name.strip().lower():
            return d.get("data") or []
    raise RuntimeError("reihe %s nicht gefunden" % name)


def letzter_voller(daten, namen, heute):
    """
    Der juengste eintrag, dessen tag VOR heute liegt und in dem jede
    gefragte reihe einen wert hat. Die labels sind nicht garantiert
    sortiert, deshalb wird nach datum gesucht und nicht nach position.
    """
    labels = daten.get("labels") or []
    reihen = [reihe(daten, n) for n in namen]
    best_i, best_tag = None, None
    for i, lab in enumerate(labels):
        try:
            tag = tag_von(lab)
        except ValueError:
            continue
        if tag >= heute:
            continue
        werte = []
        for r in reihen:
            if i >= len(r) or r[i] is None:
                werte = None
                break
            werte.append(r[i])
        if werte is None:
            continue
        if best_tag is None or tag > best_tag:
            best_i, best_tag = i, tag
    if best_i is None:
        raise RuntimeError("kein vollstaendiger tag vor %s" % heute)
    return best_tag, [float(r[best_i]) for r in reihen]


def rechne(art, werte):
    if art == "tps":
        return round(sum(werte) / SEKUNDEN_TAG, 2)
    if art == "pct":
        return round(werte[0], 2)
    return int(round(werte[0]))


def plausibel(feld, wert):
    lo, hi = FENSTER[feld]
    return lo <= wert <= hi


def sammle(heute=None, holer=None):
    """alle sechs felder. gibt werte, tage und probleme zurueck."""
    heute = heute or dt.datetime.now(dt.timezone.utc).date()
    holer = holer or hole
    werte, tage, probleme = {}, {}, []
    for feld, (pfad, namen, art) in QUELLEN.items():
        try:
            daten = holer(pfad)
            tag, roh = letzter_voller(daten, namen, heute)
            v = rechne(art, roh)
            if not plausibel(feld, v):
                probleme.append("%s = %s liegt ausserhalb des fensters, verworfen"
                                % (feld, v))
                werte[feld] = None
                continue
            werte[feld] = v
            tage[feld] = str(tag)
        except Exception as exc:      # noqa: BLE001
            probleme.append("%s, %s" % (feld, exc))
            werte[feld] = None
    return werte, tage, probleme


# ------------------------------------------------------------------ selftest

def _stub(pfad):
    heute = "2026-08-18T00:00:00.000Z"
    gestern = "2026-08-17T00:00:00.000Z"
    vor = "2026-08-16T00:00:00.000Z"
    labels = [vor, gestern, heute]

    def bau(paare):
        return {"labels": labels,
                "datasets": [{"label": k, "data": v} for k, v in paare]}

    if pfad.startswith("transactions/accepted/addresses"):
        return bau([("Addresses", [7100, 6960, 3200]), ("Price", [1, 1, 1])])
    if pfad.startswith("transactions/accepted/count"):
        return bau([("Standard", [70000, 75050, 30000]),
                    ("Coinbase", [120000, 127440, 50000]),
                    ("Price", [1, 1, 1])])
    if pfad.startswith("address/count"):
        return bau([("Price", [1, 1, 1]), ("Addresses", [789500, 789980, 790100])])
    if pfad.startswith("supply/inactive"):
        return bau([("Price", [1, 1, 1]), ("CSPERCENT", [50.9, 50.95, 50.96])])
    if pfad.startswith("supply/exchange-holdings"):
        return bau([("Balance", [3.93e9, 3.94e9, 3.94e9]), ("Price", [1, 1, 1])])
    if pfad.startswith("covenants/transactions"):
        return bau([("Transactions", [454, 450, 1133]), ("Price", [1, 1, 1])])
    raise RuntimeError("unbekannter pfad im stub")


def run_selftest():
    fails = []

    def check(name, got, want):
        if got != want:
            fails.append("%s\n    ist  %r\n    soll %r" % (name, got, want))

    heute = dt.date(2026, 8, 18)
    werte, tage, probleme = sammle(heute=heute, holer=_stub)

    # der laufende tag wird ignoriert, gelesen wird der 17.
    check("active addresses", werte["active_addr"], 6960)
    check("holder adressen", werte["holder_addr"], 789980)
    check("ruhender anteil", werte["holders"], 50.95)
    check("boersenbestand", werte["exchange_kas"], 3940000000)
    check("covenants", werte["covenant_tx"], 450)
    check("tps aus zwei reihen", werte["tps"], round(202490 / 86400, 2))
    check("gelesener tag", tage["active_addr"], "2026-08-17")
    check("keine probleme", probleme, [])

    # ein loch in der reihe darf den tag ueberspringen, nicht abbrechen
    def loch(pfad):
        d = _stub(pfad)
        if pfad.startswith("covenants"):
            d["datasets"][0]["data"][1] = None
        return d
    w2, t2, _ = sammle(heute=heute, holer=loch)
    check("luecke faellt auf den vortag zurueck", w2["covenant_tx"], 454)
    check("und nennt den richtigen tag", t2["covenant_tx"], "2026-08-16")

    # unplausibler wert wird verworfen, nicht gemeldet
    def kaputt(pfad):
        d = _stub(pfad)
        if pfad.startswith("supply/inactive"):
            d["datasets"][1]["data"][1] = 4200.0
        return d
    w3, _, p3 = sammle(heute=heute, holer=kaputt)
    check("unplausibel wird verworfen", w3["holders"], None)
    check("und steht als problem drin", len(p3), 1)

    # eine tote quelle laesst die anderen leben
    def tot(pfad):
        if pfad.startswith("supply/exchange-holdings"):
            raise RuntimeError("503")
        return _stub(pfad)
    w4, _, p4 = sammle(heute=heute, holer=tot)
    check("tote quelle, feld leer", w4["exchange_kas"], None)
    check("tote quelle, rest steht", w4["active_addr"], 6960)
    check("tote quelle, ein problem", len(p4), 1)

    if fails:
        print("selftest FEHLGESCHLAGEN")
        for f in fails:
            print("  " + f)
        return 1
    print("selftest ok, 14 faelle")
    return 0


def main(argv):
    if "--selftest" in argv:
        return run_selftest()
    werte, tage, probleme = sammle()
    if "--json" in argv:
        print(json.dumps({"row": werte}, indent=2))
        return 0
    print("kaspalytics, gelesen am %s UTC\n"
          % dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
    for feld in QUELLEN:
        print("  %-13s %-14s  tag %s" % (feld, werte.get(feld), tage.get(feld, "keiner")))
    if probleme:
        print("\n%d probleme" % len(probleme))
        for p in probleme:
            print("  " + p)
    print("\nblock fuer data/dashboard-input.json")
    print(json.dumps({"row": werte}, indent=2))
    return 0 if not probleme else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
