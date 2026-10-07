#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kohorte.py, die Wochenzahl der 100 groessten Adressen ohne Boersen, Pools und Bruecken.

Auftrag Ben, 07.10.2026. Wie viel Prozent des Umlaufs halten die 100 groessten
Adressen, wenn man alle Boersen, Mining-Pools und Bruecken herausnimmt, und
wie bewegt sich das von Woche zu Woche. Entity X steht getrennt da. Erste
Veroeffentlichung im Weekly am Mo 19.10.2026, bis dahin wird nur gerechnet.

GRUNDLAGE, OHNE NETZ
Gerechnet wird nur aus dem, was scripts/richlist_log.py jeden Sonntag ablegt:

    data/richlist-log.json                  eine zeile je woche
    data/richlist/JJJJ-MM-TT.top.json.gz    /addresses/top, ganze KAS, abgeschnitten
    data/richlist/JJJJ-MM-TT.names.json     /addresses/names, die labels

Den Umlauf nimmt jeder Messpunkt aus seiner eigenen Zeile (circ_supply_sompi,
im selben Lauf geholt), nie eine feste Zahl. Vor dem Rechnen wird die sha256
beider Rohdateien gegen die Zeile geprueft.

WER RAUSFAELLT
Die Zuordnung Label -> Kategorie steht in data/label-kategorien.json, von
Hand gepflegt, jede Zeile mit Datum. Entfernt werden boerse, pool, bruecke.
Alles andere bleibt drin, auch Adressen ohne Label. Ein Label, das nicht in
der Tabelle steht, wird nicht geraten: es bleibt drin und erzeugt eine
Warnung. Ein Label, das einen Vorwurf enthaelt, wird nie ausgegeben, auch
nicht in einer Warnung; es steht in der Tabelle nur als sha256 und zaehlt
zu sonstige.

    kohorte                die 100 groessten verbleibenden adressen, Entity X eingeschlossen
    anteil_pct             kohorte / umlauf
    anteil_ohne_ex_pct     dieselbe kohorte ohne Entity X (99 adressen) / umlauf
    entity_x_pct           Entity X / umlauf

VERAENDERUNG ZUR VORWOCHE
Erst runden, dann abziehen (Regel aus scripts/weekly_facts.py). Beide
gerundeten Endpunkte stehen in der Zeile, damit jeder die Differenz selbst
nachrechnen kann.

WAS NIE HERAUSGEHT
Keine Adresse, keine Rangliste, kein Label einer anderen Adresse. In
data/kohorte.json stehen nur Summen, Anteile und Zaehler je Kategorie.
Fuer Texte: "the address the explorer calls Entity X", und immer der Satz
"only labelled exchanges, pools and bridges are removed; unlabelled ones stay in."

    python3 scripts/kohorte.py                 rechnen, data/kohorte.json schreiben
    python3 scripts/kohorte.py --pruefen       rechnen, mit der datei vergleichen, nichts schreiben
    python3 scripts/kohorte.py --git REV       messpunkte aus einem alten git-stand nachrechnen, nur ausgeben
    python3 scripts/kohorte.py --selbsttest    ohne netz
    python3 scripts/kohorte.py --live          einheitenprobe gegen den live-kontostand von Entity X (netz)
"""
import argparse
import gzip
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOG = "data/richlist-log.json"
TABELLE = "data/label-kategorien.json"
AUSGABE = "data/kohorte.json"
GROESSE = 100
RAUS = ("boerse", "pool", "bruecke")
KATEGORIEN = RAUS + ("entity_x", "sonstige", "offen")
EX_LABEL = "Entity X"
SOMPI = 100_000_000
TOLERANZ_PCT = 1.0
API = "https://api.kaspa.org"
EINSCHRAENKUNG = "only labelled exchanges, pools and bridges are removed; unlabelled ones stay in."
NAME_EX = "the address the explorer calls Entity X"
VORWURF = re.compile(r"scam|launder|fraud|hack|exploit|stolen|theft|phish|ponzi", re.I)


class Abbruch(RuntimeError):
    pass


def sha(b):
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------- lesen

def lies_bytes(pfad, rev=None):
    if rev is None:
        return (REPO / pfad).read_bytes()
    r = subprocess.run(["git", "show", "%s:%s" % (rev, pfad)], cwd=REPO, capture_output=True)
    if r.returncode != 0:
        raise Abbruch("%s fehlt in %s" % (pfad, rev))
    return r.stdout


def lade_tabelle(daten=None):
    t = daten if daten is not None else json.loads(lies_bytes(TABELLE))
    klar, hashes = {}, {}
    for z in t["labels"]:
        if z["kategorie"] not in KATEGORIEN or not z.get("datum"):
            raise Abbruch("label-tabelle: zeile ohne gueltige kategorie oder datum: %r" % z.get("label"))
        if VORWURF.search(z["label"]):
            raise Abbruch("label-tabelle: ein label mit vorwurf steht im klartext, es gehoert nach labels_als_hash")
        klar[z["label"]] = z["kategorie"]
    for z in t.get("labels_als_hash") or []:
        if z["kategorie"] not in KATEGORIEN or not z.get("datum"):
            raise Abbruch("label-tabelle: hash-zeile ohne gueltige kategorie oder datum")
        hashes[z["label_sha256"]] = z["kategorie"]
    return klar, hashes


def kategorie(label, tabelle):
    """(kategorie, bekannt). Unbekannt heisst: nicht raten, drin lassen."""
    klar, hashes = tabelle
    if label in klar:
        return klar[label], True
    h = sha(label.encode("utf-8"))
    if h in hashes:
        return hashes[h], True
    if VORWURF.search(label):
        return "sonstige", False
    return None, False


def zeige_label(label):
    """Fuer Warnungen. Ein Label mit Vorwurf erscheint nie, auch nicht im Log."""
    return "[label mit vorwurf, nicht ausgegeben]" if VORWURF.search(label) else repr(label)


def lade_messpunkt(zeile, rev=None):
    roh = zeile["roh"]
    top_b = gzip.decompress(lies_bytes(roh["top"], rev))
    names_b = lies_bytes(roh["names"], rev)
    if sha(top_b) != roh["top_sha256"] or sha(names_b) != roh["names_sha256"]:
        raise Abbruch("%s: sha256 der rohdaten passt nicht zur zeile im log" % zeile["datum"])
    top = json.loads(top_b)
    top = top[0] if isinstance(top, list) else top
    if top.get("timestamp") != zeile["timestamp"]:
        raise Abbruch("%s: zeitstempel der rangliste passt nicht zur zeile" % zeile["datum"])
    ranking = sorted(top["ranking"], key=lambda e: e["rank"])
    names = {e["address"]: e["name"] for e in json.loads(names_b)}
    return ranking, names


# ---------------------------------------------------------------- rechnen

def rechne(ranking, names, circ_sompi, tabelle, groesse=GROESSE):
    circ_kas = int(circ_sompi) / SOMPI
    warnungen, unbekannt = [], set()
    ex = [a for a, n in names.items() if n == EX_LABEL]
    if len(ex) != 1:
        raise Abbruch("Entity X: %d adressen mit diesem label, erwartet genau eine" % len(ex))
    ex = ex[0]

    def kat(adr):
        if adr not in names:
            return "ohne_label"
        k, bekannt = kategorie(names[adr], tabelle)
        if not bekannt:
            unbekannt.add(names[adr])
        return k or "unbekannt"

    roh_top = ranking[:groesse]
    raus_roh = {k: 0 for k in RAUS}
    for e in roh_top:
        k = kat(e["address"])
        if k in raus_roh:
            raus_roh[k] += 1

    kohorte, uebersprungen_kas = [], 0
    for e in ranking:
        if len(kohorte) == groesse:
            break
        if kat(e["address"]) in RAUS:
            uebersprungen_kas += e["amount"]
            continue
        kohorte.append(e)
    if len(kohorte) < groesse:
        raise Abbruch("rangliste zu kurz fuer %d adressen" % groesse)
    if ex not in {e["address"] for e in kohorte}:
        raise Abbruch("Entity X steht nicht in der kohorte, das passt nicht zur rangliste")

    kohorte_kas = sum(e["amount"] for e in kohorte)
    ex_kas = next(e["amount"] for e in kohorte if e["address"] == ex)
    letzter_rang = kohorte[-1]["rank"]
    bis_letzter = sum(e["amount"] for e in ranking if e["rank"] <= letzter_rang)
    if bis_letzter != kohorte_kas + uebersprungen_kas:
        raise Abbruch("summenprobe: kohorte plus ausgeschlossene ergibt nicht die rangliste bis rang %d" % letzter_rang)

    for lab in set(names.values()):
        if not kategorie(lab, tabelle)[1]:
            unbekannt.add(lab)
    in_kohorte = {k: 0 for k in ("ohne_label", "sonstige", "offen", "unbekannt")}
    for e in kohorte:
        k = kat(e["address"])
        if k in in_kohorte:
            in_kohorte[k] += 1
    for lab in sorted(unbekannt):
        warnungen.append("label nicht in %s, bleibt drin: %s" % (TABELLE, zeige_label(lab)))
    if in_kohorte["offen"]:
        warnungen.append("%d adressen der kohorte tragen ein label der kategorie offen" % in_kohorte["offen"])

    return {
        "kohorte_kas": kohorte_kas,
        "entity_x_kas": ex_kas,
        "circ_supply_kas": round(circ_kas, 2),
        "anteil_pct": round(kohorte_kas / circ_kas * 100, 4),
        "anteil_ohne_ex_pct": round((kohorte_kas - ex_kas) / circ_kas * 100, 4),
        "entity_x_pct": round(ex_kas / circ_kas * 100, 4),
        "letzter_rohrang_der_kohorte": letzter_rang,
        "ausgeschlossen_in_roh_top100": raus_roh,
        "ausgeschlossen_kas_bis_letzter_rang": uebersprungen_kas,
        "kohorte_nach_label": in_kohorte,
    }, warnungen, ex


def veraenderung(alt, neu, feld):
    """Erst runden, dann abziehen. Beide Endpunkte stehen dabei."""
    von, bis = round(alt[feld], 2), round(neu[feld], 2)
    return {"von": von, "bis": bis, "pp": round(bis - von, 2)}


def reihe(rev=None, tabelle=None):
    log = json.loads(lies_bytes(LOG, rev))
    tabelle = tabelle or lade_tabelle()
    aus, warnungen, vorher = [], [], None
    for zeile in sorted(log["wochen"], key=lambda z: z["timestamp"]):
        ranking, names = lade_messpunkt(zeile, rev)
        if sum(e["amount"] for e in ranking) != zeile["summe_rangliste_kas"]:
            raise Abbruch("%s: summe der rangliste passt nicht zur zeile im log" % zeile["datum"])
        r, w, ex = rechne(ranking, names, zeile["circ_supply_sompi"], tabelle)
        ref = zeile.get("einheitspruefung") or {}
        if ref.get("rang0_adresse") == ex and ref.get("referenz_kas"):
            abw = abs(r["entity_x_kas"] - ref["referenz_kas"]) / ref["referenz_kas"] * 100
            if abw > TOLERANZ_PCT:
                raise Abbruch("%s: Entity X in der rangliste weicht %.2f%% vom kontostand des laufs ab" % (zeile["datum"], abw))
        p = {"datum": zeile["datum"], "woche": zeile["woche"], "schnappschuss_utc": zeile["timestamp_utc"],
             "umlauf_abgerufen_utc": zeile["abgerufen_utc"]}
        p.update({"anteil_pct": round(r["anteil_pct"], 2), "anteil_ohne_ex_pct": round(r["anteil_ohne_ex_pct"], 2),
                  "entity_x_pct": round(r["entity_x_pct"], 2)})
        p["genau"] = {k: r[k] for k in ("anteil_pct", "anteil_ohne_ex_pct", "entity_x_pct", "kohorte_kas",
                                        "entity_x_kas", "circ_supply_kas")}
        p["veraenderung_pp"] = None if vorher is None else {
            f: veraenderung(vorher, p, f) for f in ("anteil_pct", "anteil_ohne_ex_pct", "entity_x_pct")}
        p["ausgeschlossen_in_roh_top100"] = r["ausgeschlossen_in_roh_top100"]
        p["kohorte_nach_label"] = r["kohorte_nach_label"]
        p["letzter_rohrang_der_kohorte"] = r["letzter_rohrang_der_kohorte"]
        aus.append(p)
        warnungen += ["%s: %s" % (zeile["datum"], x) for x in w]
        vorher = p
    return aus, warnungen


def text(punkte):
    kopf = {
        "zweck": "anteil der 100 groessten adressen am umlauf, ohne gelabelte boersen, pools und bruecken. "
                 "Entity X bleibt drin und steht getrennt da. noch nicht veroeffentlicht, erst ab dem weekly vom 19.10.2026.",
        "einschraenkung": EINSCHRAENKUNG,
        "entity_x_im_text": NAME_EX,
        "quelle": "data/richlist-log.json und data/richlist/, api.kaspa.org /addresses/top und /addresses/names, "
                  "umlauf aus /info/coinsupply desselben laufs",
        "rechnung": "scripts/kohorte.py, labels nach data/label-kategorien.json",
    }
    zeilen = ["{"] + ['  %s: %s,' % (json.dumps(k), json.dumps(v, ensure_ascii=False)) for k, v in kopf.items()]
    zeilen.append('  "messpunkte": [')
    zeilen.append(",\n".join("    " + json.dumps(p, ensure_ascii=False, sort_keys=True) for p in punkte))
    zeilen += ["  ]", "}"]
    return "\n".join(zeilen) + "\n"


# ---------------------------------------------------------------- live

def live_probe():
    """Einheitenprobe gegen den live-kontostand (sompi). Bricht bei mehr als 1 % ab."""
    log = json.loads(lies_bytes(LOG))
    zeile = max(log["wochen"], key=lambda z: z["timestamp"])
    ranking, names = lade_messpunkt(zeile)
    ex = next(a for a, n in names.items() if n == EX_LABEL)
    rang = next(e["amount"] for e in ranking if e["address"] == ex)
    req = urllib.request.Request("%s/addresses/%s/balance" % (API, ex),
                                 headers={"User-Agent": "kaspa-pulse-bot (+https://kaspapulse.com)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        sompi = int(json.loads(r.read().decode("utf-8"))["balance"])
    live_kas = sompi / SOMPI
    abw = abs(rang - live_kas) / live_kas * 100
    print("einheitenprobe: Entity X in der rangliste vom %s %d KAS, live %.2f KAS (sompi / 1e8), abweichung %.3f%%"
          % (zeile["datum"], rang, live_kas, abw))
    if abs(rang - sompi) / sompi * 100 <= TOLERANZ_PCT:
        raise Abbruch("die rangliste passt nur ohne die division durch 1e8, die einheit hat gewechselt")
    if abw > TOLERANZ_PCT:
        raise Abbruch("abweichung %.3f%% ueber %.1f%%, abbruch" % (abw, TOLERANZ_PCT))
    return abw


# ---------------------------------------------------------------- selbsttest

def selbsttest():
    f = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            f.append(name)

    tab = lade_tabelle({"labels": [
        {"label": "Entity X", "kategorie": "entity_x", "datum": "x"},
        {"label": "Bourse", "kategorie": "boerse", "datum": "x"},
        {"label": "Pool A", "kategorie": "pool", "datum": "x"},
        {"label": "Bridge", "kategorie": "bruecke", "datum": "x"},
        {"label": "Fund", "kategorie": "sonstige", "datum": "x"}],
        "labels_als_hash": [{"label_sha256": sha("Bad Scam 1".encode()), "kategorie": "sonstige", "datum": "x"}]})
    ranking = [{"rank": i, "address": "a%d" % i, "amount": 1000 - i} for i in range(10)]
    names = {"a0": "Entity X", "a1": "Bourse", "a2": "Bad Scam 1", "a3": "Pool A", "a4": "Bridge", "a5": "Fund",
             "a6": "Other Laundering", "a7": "Neu und unbekannt", "a9": "Spaeter Neu"}
    r, w, ex = rechne(ranking, names, 10_000 * SOMPI, tab, groesse=5)
    # raus: a1, a3, a4. kohorte: a0 a2 a5 a6 a7
    ok("kohorte ueberspringt boerse, pool, bruecke und fuellt auf",
       r["kohorte_kas"] == 1000 + 998 + 995 + 994 + 993 and r["letzter_rohrang_der_kohorte"] == 7)
    ok("Entity X steht in der kohorte und getrennt", ex == "a0" and r["entity_x_kas"] == 1000)
    ok("anteile mit und ohne Entity X", r["anteil_pct"] == round(4980 / 10_000 * 100, 4)
       and r["anteil_ohne_ex_pct"] == round(3980 / 10_000 * 100, 4) and r["entity_x_pct"] == 10.0)
    ok("ausgeschlossene je kategorie in der roh-top", r["ausgeschlossen_in_roh_top100"] == {"boerse": 1, "pool": 1, "bruecke": 1})
    ok("unbekanntes label warnt und bleibt drin", any("Neu und unbekannt" in x for x in w)
       and r["kohorte_nach_label"]["unbekannt"] == 1)
    ok("unbekanntes label warnt auch ausserhalb der kohorte", any("Spaeter Neu" in x for x in w))
    alles = json.dumps(r) + "\n".join(w)
    ok("label mit vorwurf erscheint nie, auch nicht in der warnung", not VORWURF.search(alles)
       and any("nicht ausgegeben" in x for x in w))
    ok("label mit vorwurf zaehlt zu sonstige, bekannt oder neu", r["kohorte_nach_label"]["sonstige"] == 3)
    ok("keine adresse in der ausgabe", "a2" not in json.dumps(r) and "kaspa:" not in json.dumps(r))
    try:
        lade_tabelle({"labels": [{"label": "X Scam", "kategorie": "sonstige", "datum": "x"}]})
        ok("vorwurf im klartext der tabelle bricht ab", False)
    except Abbruch:
        ok("vorwurf im klartext der tabelle bricht ab", True)
    v = veraenderung({"x": 10.004}, {"x": 10.016}, "x")
    ok("erst runden, dann abziehen", v == {"von": 10.0, "bis": 10.02, "pp": 0.02})
    try:
        rechne(ranking, {"a1": "Bourse"}, 10_000 * SOMPI, tab, groesse=5)
        ok("ohne Entity X bricht ab", False)
    except Abbruch:
        ok("ohne Entity X bricht ab", True)

    # echte daten aus dem repo
    log = json.loads(lies_bytes(LOG))
    p1, w1 = reihe()
    p2, _ = reihe()
    ok("wiederholbar, zweimal gerechnet, gleiches ergebnis", text(p1) == text(p2))
    for zeile in log["wochen"]:
        ranking, names = lade_messpunkt(zeile)
        ok("%s summenprobe gegen die rohliste (%d KAS)" % (zeile["datum"], zeile["summe_rangliste_kas"]),
           sum(e["amount"] for e in ranking) == zeile["summe_rangliste_kas"])
        ref = zeile["einheitspruefung"]
        ex_amt = next(e["amount"] for e in ranking if names.get(e["address"]) == EX_LABEL)
        ok("%s einheitenprobe gegen den kontostand des laufs (%.4f%%)" % (
            zeile["datum"], abs(ex_amt - ref["referenz_kas"]) / ref["referenz_kas"] * 100),
           abs(ex_amt - ref["referenz_kas"]) / ref["referenz_kas"] * 100 <= TOLERANZ_PCT)
    ausgabe = text(p1) + "\n".join(w1)
    ok("echte ausgabe ohne adresse und ohne label mit vorwurf", "kaspa:" not in ausgabe and not VORWURF.search(ausgabe))
    datei = REPO / AUSGABE
    if datei.exists():
        ok("data/kohorte.json auf stand", datei.read_text(encoding="utf-8") == text(p1))
    print("%d fehler" % len(f))
    return 1 if f else 0


# ---------------------------------------------------------------- main

def drucke(punkte, warnungen):
    for p in punkte:
        v = p["veraenderung_pp"]
        print("%s  kohorte %.2f%%  ohne Entity X %.2f%%  Entity X %.2f%%  %s  raus in roh-top100 %s" % (
            p["datum"], p["anteil_pct"], p["anteil_ohne_ex_pct"], p["entity_x_pct"],
            ("vorwoche %.2f -> %.2f, %+.2f pp" % (v["anteil_pct"]["von"], v["anteil_pct"]["bis"], v["anteil_pct"]["pp"]))
            if v else "erster messpunkt", json.dumps(p["ausgeschlossen_in_roh_top100"])))
    for w in warnungen:
        print("WARNUNG " + w)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--pruefen", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--git", metavar="REV")
    a = ap.parse_args(argv)
    try:
        if a.selbsttest:
            return selbsttest()
        if a.live:
            live_probe()
            return 0
        punkte, warnungen = reihe(a.git)
        drucke(punkte, warnungen)
        if a.git:
            return 0
        neu = text(punkte)
        datei = REPO / AUSGABE
        if a.pruefen:
            gleich = datei.exists() and datei.read_text(encoding="utf-8") == neu
            print("data/kohorte.json %s" % ("auf stand" if gleich else "weicht ab"))
            return 0 if gleich else 1
        datei.write_text(neu, encoding="utf-8")
        print("geschrieben, %s, %d messpunkte" % (AUSGABE, len(punkte)))
        return 0
    except Abbruch as exc:
        print("ABBRUCH %s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
