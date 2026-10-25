#!/usr/bin/env python3
"""Kaspa Pulse, KaspaDollar-Spenden vom eigenen Knoten zaehlen (Ben, 25.10.2026).

Eingaben (alle im Runner, nichts davon mit Adressen im Repo oder Artefakt):
  --adresse DATEI   die Spendenadresse, gelesen von kaspadollar.com
  --bestand         bestand.csv von kp-stichzeit mit KP_SPK (UTXOs des Ziels zur Stichzeit)
  --tx              adr-tx.jsonl dieses Laufs (Ein- und Abgaenge im Knotenfenster)
  --stand           adr-stand.json dieses Laufs (Fenster, DAA-Zeit-Anker)
  --absender        absender.txt dieses Laufs (sha256 der Absender-Skripte, bleibt im Runner)
  --vorher DIR      Artefakte frueherer Laeufe (ereignisse.jsonl und adr-stand.json, ohne Tx-ID)
  --seite           seite.json mit dem Stand laut kaspadollar.com (source)

Ausgaben (Artefakt, ohne Adressen und ohne Tx-IDs):
  ereignisse.jsonl  je Ein- oder Abgang im Fenster: t, daa, art, sompi
  ergebnis.json     Zahlen 1 bis 5
  tage.csv          Summe je UTC-Tag seit 23.10.2026

    python3 scripts/kaspadollar_zaehlung.py --skript-aus DATEI     # Skript-Hex fuer KP_SPK, nur in eine Datei
    python3 scripts/kaspadollar_zaehlung.py --selbsttest
"""
import argparse
import csv
import datetime as dt
import glob
import json
import os
import statistics
import sys
import time
import urllib.request

SOMPI = 100_000_000
START = "2026-10-23"
CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
GEN = (0x98f2bc8e61, 0x79b76d99e2, 0xf33e5fb3c4, 0xae2eabe2a8, 0x1e4f43e470)


# ------------------------------------------------------------------ adresse -> skript

def polymod(werte):
    c = 1
    for d in werte:
        c0 = c >> 35
        c = ((c & 0x07ffffffff) << 5) ^ d
        for i in range(5):
            if (c0 >> i) & 1:
                c ^= GEN[i]
    return c ^ 1


def adresse_zu_skript(adr):
    """Kaspa-Adresse -> (version, skript-hex), wie rusty-kaspa pay_to_address_script."""
    praefix, _, daten = adr.strip().partition(":")
    werte = [CHARSET.index(c) for c in daten]
    nutz, pruef = werte[:-8], werte[-8:]
    soll = polymod([ord(c) & 0x1f for c in praefix] + [0] + nutz + [0] * 8)
    ist = 0
    for v in pruef:
        ist = (ist << 5) | v
    if soll != ist:
        raise ValueError("pruefsumme falsch")
    buf, bits, roh = 0, 0, []
    for v in nutz:
        buf = (buf << 5) | v
        bits += 5
        while bits >= 8:
            bits -= 8
            roh.append((buf >> bits) & 0xff)
            buf &= (1 << bits) - 1
    ver, last = roh[0], bytes(roh[1:])
    if ver == 0 and len(last) == 32:
        return "20" + last.hex() + "ac"
    if ver == 1 and len(last) == 33:
        return "21" + last.hex() + "ab"
    if ver == 8 and len(last) == 32:
        return "aa20" + last.hex() + "87"
    raise ValueError("unbekannte adressversion %d" % ver)


# ------------------------------------------------------------------ zeit aus daa

def zeit_aus_daa(anker, daa):
    """lineare Interpolation zwischen Ankern (daa, ms); ausserhalb mit der Rate der
    naechsten zwei Anker."""
    a = sorted(set((int(d), int(t)) for d, t in anker))
    if len(a) < 2:
        raise ValueError("zu wenige anker")
    for (d0, t0), (d1, t1) in zip(a, a[1:]):
        if d0 <= daa <= d1:
            return t0 + (daa - d0) * (t1 - t0) / (d1 - d0)
    (d0, t0), (d1, t1) = (a[0], a[1]) if daa < a[0][0] else (a[-2], a[-1])
    return t0 + (daa - d0) * (t1 - t0) / (d1 - d0)


def tag(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d")


def iso(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).isoformat()


# ------------------------------------------------------------------ auswertung

def ereignisse_aus_tx(zeilen):
    """Einzahlung: Tx mit Ausgang an das Ziel und ohne Eingang vom Ziel.
    Abgang: Tx mit Eingang vom Ziel, Betrag netto (von_ziel minus Rueckgeld an das Ziel)."""
    aus = []
    for t in zeilen:
        if t["n_von"] == 0 and t["an_ziel"] > 0:
            aus.append({"t": t["t"], "daa": t["daa"], "art": "ein", "sompi": t["an_ziel"]})
        elif t["n_von"] > 0:
            aus.append({"t": t["t"], "daa": t["daa"], "art": "aus", "sompi": t["von_ziel"] - t["an_ziel"]})
    return aus


def laeufe_zusammen(laeufe):
    """laeufe: [(fenster_von_daa, fenster_bis_daa, ereignisse)]. Ueberlappungen fallen weg:
    jeder Lauf zaehlt nur ab seinem Fensterbeginn bis zum Beginn des naechsten.
    Gibt Ereignisse, das lueckenlose Fenster (von, bis) und gefundene Luecken."""
    laeufe = sorted(laeufe, key=lambda x: x[0])
    aus, luecken = [], []
    for i, (von, bis, ev) in enumerate(laeufe):
        ende = laeufe[i + 1][0] if i + 1 < len(laeufe) else bis + 1
        if i + 1 < len(laeufe) and laeufe[i + 1][0] > bis + 1:
            luecken.append((bis, laeufe[i + 1][0]))
            ende = bis + 1
        aus += [e for e in ev if von <= e["daa"] < ende]
    return aus, (laeufe[0][0], laeufe[-1][1]) if laeufe else (None, None), luecken


def api_absender(txids, abruf):
    """Absender-Adressen aelterer Einzahlungen ueber api.kaspa.org, nur im Speicher."""
    menge, offen = set(), 0
    ids = sorted(txids)
    for i in range(0, len(ids), 50):
        for t in abruf(ids[i:i + 50]) or []:
            for x in t.get("inputs") or []:
                a = x.get("previous_outpoint_address")
                if a:
                    menge.add(a)
                else:
                    offen += 1
        time.sleep(0.2)
    return menge, offen


def api_abruf(ids):
    req = urllib.request.Request("https://api.kaspa.org/transactions/search?resolve_previous_outpoints=light",
                                 data=json.dumps({"transactionIds": ids}).encode(),
                                 headers={"Content-Type": "application/json", "Accept": "application/json",
                                          "User-Agent": "kaspa-pulse-spendenzaehlung (+https://kaspapulse.com)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def auswerten(bestand, tx_zeilen, stand, absender, vorher, seite, stichzeit_ms, abruf=api_abruf):
    eigene_ev = ereignisse_aus_tx(tx_zeilen)
    anker = [tuple(x) for x in stand.get("anker_daa_ms") or []]
    laeufe = [(stand["von_daa"], stand["bis_daa"], eigene_ev)]
    for v in vorher:
        anker += [tuple(x) for x in v["stand"].get("anker_daa_ms") or []]
        laeufe.append((v["stand"]["von_daa"], v["stand"]["bis_daa"], v["ereignisse"]))
    fenster_ev, (f_von, f_bis), luecken = laeufe_zusammen(laeufe)

    # einzahlungen vor dem ersten fenster: aus dem utxo-bestand zur stichzeit (je tx gebuendelt)
    je_tx = {}
    for r in bestand:
        txid = r["outpoint"].split(":")[0]
        e = je_tx.setdefault(txid, {"sompi": 0, "daa": int(r["block_daa_score"])})
        e["sompi"] += int(r["sompi"])
    alt = {k: v for k, v in je_tx.items() if v["daa"] < f_von}
    ein = [{"t": zeit_aus_daa(anker, v["daa"]), "daa": v["daa"], "sompi": v["sompi"], "quelle": "utxo"}
           for v in alt.values()]
    ein += [dict(e, quelle="fenster") for e in fenster_ev if e["art"] == "ein"]
    ab = [e for e in fenster_ev if e["art"] == "aus"]
    ein = [e for e in ein if e["t"] <= stichzeit_ms]
    summe = sum(e["sompi"] for e in ein)
    betraege = sorted(e["sompi"] for e in ein)
    bestand_summe = sum(int(r["sompi"]) for r in bestand)
    abgaenge = sum(e["sompi"] for e in ab)

    # absender: eigenes fenster aus dem knoten (sha256), aeltere einzahlungen ueber die api
    try:
        api_menge, api_offen = api_absender(alt.keys(), abruf) if alt else (set(), 0)
        api_fehler = None
    except Exception as exc:                        # noqa: BLE001
        api_menge, api_offen, api_fehler = set(), 0, type(exc).__name__
    tage = {}
    d = dt.date.fromisoformat(START)
    while d.isoformat() <= tag(stichzeit_ms):
        tage[d.isoformat()] = [0, 0]
        d += dt.timedelta(days=1)
    for e in ein:
        k = tag(e["t"])
        if k in tage:
            tage[k][0] += e["sompi"]
            tage[k][1] += 1
    erg = {
        "stichzeit_utc": iso(stichzeit_ms),
        "quelle": "counted by kaspa pulse, eigener knoten",
        "einzahlungen_kas": round(summe / SOMPI, 8),
        "einzahlungen_anzahl": len(ein),
        "einzahlungen_aus_utxo_bestand_vor_fenster": len(alt),
        "einzahlungen_im_fenster": sum(1 for e in ein if e["quelle"] == "fenster"),
        "fenster_utc": [iso(zeit_aus_daa(anker, f_von)), iso(zeit_aus_daa(anker, f_bis))],
        "fenster_luecken": len(luecken),
        "absender_eigenes_fenster": len(absender),
        "absender_aeltere_ueber_api_kaspa_org": len(api_menge),
        "absender_eingaenge_ohne_adresse_api": api_offen,
        "absender_api_fehler": api_fehler,
        "median_spende_kas": round(statistics.median(betraege) / SOMPI, 8) if betraege else None,
        "groesste_spende_anteil_prozent": round(100 * betraege[-1] / summe, 2) if summe else None,
        "abgaenge_kas": round(abgaenge / SOMPI, 8),
        "abgaenge_anzahl": len(ab),
        "bestand_zur_stichzeit_kas": round(bestand_summe / SOMPI, 8),
        "pruefung_einzahlungen_minus_abgaenge_gleich_bestand": summe - abgaenge == bestand_summe,
        "tage": {k: {"kas": round(v[0] / SOMPI, 8), "einzahlungen": v[1]} for k, v in tage.items()},
    }
    if seite and seite.get("kas") is not None:
        diff = summe / SOMPI - seite["kas"]
        erg["seite"] = dict(seite, quelle="source kaspadollar.com")
        erg["abweichung_kas"] = round(diff, 8)
        erg["abweichung_prozent"] = round(100 * diff / seite["kas"], 3) if seite["kas"] else None
        erg["abweichung_ueber_1_prozent"] = abs(erg["abweichung_prozent"] or 0) > 1
    return erg, eigene_ev


def lesen_jsonl(p):
    return [json.loads(z) for z in open(p, encoding="utf-8")] if os.path.exists(p) else []


def main_lauf(a):
    stand = json.load(open(a.stand, encoding="utf-8"))
    with open(a.bestand, encoding="utf-8") as fh:
        bestand = list(csv.DictReader(fh))
    absender = {z.strip() for z in open(a.absender, encoding="utf-8") if z.strip()} if a.absender else set()
    vorher = []
    for d in sorted(glob.glob(os.path.join(a.vorher, "*"))) if a.vorher else []:
        sp = os.path.join(d, "adr-stand.json")
        if os.path.exists(sp):
            vorher.append({"stand": json.load(open(sp, encoding="utf-8")),
                           "ereignisse": lesen_jsonl(os.path.join(d, "ereignisse.jsonl"))})
    seite = json.load(open(a.seite, encoding="utf-8")) if a.seite and os.path.exists(a.seite) else None
    stich = int(dt.datetime.fromisoformat(a.stichzeit.replace("Z", "+00:00")).timestamp() * 1000)
    erg, ev = auswerten(bestand, lesen_jsonl(a.tx), stand, absender, vorher, seite, stich)
    erg["laeufe_vorher"] = len(vorher)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "ereignisse.jsonl"), "w", encoding="utf-8") as fh:
        for e in sorted(ev, key=lambda x: x["daa"]):
            fh.write(json.dumps({"t": e["t"], "daa": e["daa"], "art": e["art"], "sompi": e["sompi"]}) + "\n")
    with open(os.path.join(a.out, "tage.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["tag_utc", "kas", "einzahlungen"])
        for k, v in erg["tage"].items():
            w.writerow([k, v["kas"], v["einzahlungen"]])
    with open(os.path.join(a.out, "ergebnis.json"), "w", encoding="utf-8") as fh:
        json.dump(erg, fh, indent=1)
    print(json.dumps(erg, indent=1))
    return 0


def selbsttest():
    fehler = []

    def ok(name, bed, ist=None):
        if not bed:
            fehler.append(name)
            print("FEHLER", name, ist)
    # testvektoren aus rusty-kaspa crypto/addresses (v2.1.0)
    ok("pubkey null", adresse_zu_skript("kaspa:qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqkx9awp4e") == "20" + "00" * 32 + "ac")
    ok("pubkey vektor", adresse_zu_skript("kaspa:qp0l70zd5x85ttwd6jv7g3s3a8llzj96d8dncn4zmhv4tlzx5k2jyqh70xmfj")
       == "20" + "5fff3c4da18f45adcdd499e44611e9fff148ba69db3c4ea2ddd955fc46a59522" + "ac")
    ok("ecdsa vektor", adresse_zu_skript("kaspatest:qxaqrlzlf6wes72en3568khahq66wf27tuhfxn5nytkd8tcep2c0vrse6gdmpks")
       == "21" + "ba01fc5f4e9d9879599c69a3dafdb835a7255e5f2e934e9322ecd3af190ab0f60e" + "ab")
    try:
        adresse_zu_skript("kaspa:qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqkx9awp4l")
        ok("falsche pruefsumme erkannt", False)
    except ValueError:
        pass
    ok("zeit aus daa", zeit_aus_daa([(100, 10000), (200, 20000)], 150) == 15000
       and zeit_aus_daa([(100, 10000), (200, 20000)], 50) == 5000)
    tx = [{"t": 5000, "daa": 300, "an_ziel": 7 * SOMPI, "n_von": 0, "von_ziel": 0},
          {"t": 6000, "daa": 400, "an_ziel": 1 * SOMPI, "n_von": 1, "von_ziel": 3 * SOMPI}]
    ev = ereignisse_aus_tx(tx)
    ok("ein und abgang netto", ev == [{"t": 5000, "daa": 300, "art": "ein", "sompi": 7 * SOMPI},
                                      {"t": 6000, "daa": 400, "art": "aus", "sompi": 2 * SOMPI}], ev)
    l1 = (100, 250, [{"daa": 120, "art": "ein", "sompi": 1}, {"daa": 230, "art": "ein", "sompi": 2}])
    l2 = (200, 500, [{"daa": 230, "art": "ein", "sompi": 2}, {"daa": 450, "art": "ein", "sompi": 3}])
    zs, f, lu = laeufe_zusammen([l2, l1])
    ok("ueberlappung einmal gezaehlt", sorted(e["sompi"] for e in zs) == [1, 2, 3] and f == (100, 500) and not lu, zs)
    zs, f, lu = laeufe_zusammen([(100, 150, l1[2]), (200, 500, l2[2])])
    ok("luecke erkannt", lu == [(150, 200)], lu)
    # gesamt: zwei alte einzahlungen im utxo-bestand vor dem fenster, eine im fenster, ein abgang
    stand = {"von_daa": 1000, "bis_daa": 2000, "anker_daa_ms": [[1000, 1792713600000], [2000, 1792713700000]]}
    bestand = [{"outpoint": "aa:0", "sompi": str(4 * SOMPI), "block_daa_score": "500"},
               {"outpoint": "aa:1", "sompi": str(1 * SOMPI), "block_daa_score": "500"},
               {"outpoint": "bb:0", "sompi": str(10 * SOMPI), "block_daa_score": "900"},
               {"outpoint": "cc:0", "sompi": str(6 * SOMPI), "block_daa_score": "1500"}]
    txz = [{"t": 1792713650000, "daa": 1500, "an_ziel": 6 * SOMPI, "n_von": 0, "von_ziel": 0}]
    rufe = []

    def abruf(ids):
        rufe.append(sorted(ids))
        return [{"inputs": [{"previous_outpoint_address": "kaspa:x%s" % i}]} for i in ids]
    erg, _ev = auswerten(bestand, txz, stand, {"h1"}, [], {"kas": 21.0}, 1792800000000, abruf)
    ok("summe 21 kas, 3 einzahlungen, je tx gebuendelt", erg["einzahlungen_kas"] == 21 and erg["einzahlungen_anzahl"] == 3, erg)
    ok("median 6, groesste 10 von 21", erg["median_spende_kas"] == 6 and erg["groesste_spende_anteil_prozent"] == 47.62, erg)
    ok("absender: fenster 1, api 2 (nur alte tx gefragt)", erg["absender_eigenes_fenster"] == 1
       and erg["absender_aeltere_ueber_api_kaspa_org"] == 2 and rufe == [["aa", "bb"]], (erg, rufe))
    ok("bestand passt, keine abweichung", erg["pruefung_einzahlungen_minus_abgaenge_gleich_bestand"]
       and erg["abweichung_kas"] == 0 and erg["abweichung_ueber_1_prozent"] is False, erg)
    ok("tageskurve ab 23.10.", list(erg["tage"])[0] == "2026-10-23", list(erg["tage"]))
    text = json.dumps(erg)
    ok("keine tx-id und keine adresse im ergebnis", "aa" not in text.replace("kaspa", "") and "kaspa:" not in text)
    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skript-aus")
    ap.add_argument("--adresse")
    ap.add_argument("--bestand")
    ap.add_argument("--tx")
    ap.add_argument("--stand")
    ap.add_argument("--absender")
    ap.add_argument("--vorher")
    ap.add_argument("--seite")
    ap.add_argument("--stichzeit")
    ap.add_argument("--out", default="aus")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    if a.skript_aus:
        adr = open(a.adresse, encoding="utf-8").read().strip()
        with open(a.skript_aus, "w", encoding="utf-8") as fh:
            fh.write(adresse_zu_skript(adr))
        print("skript geschrieben (%d hex-zeichen)" % len(open(a.skript_aus).read()))
        return 0
    return main_lauf(a)


if __name__ == "__main__":
    sys.exit(main())
