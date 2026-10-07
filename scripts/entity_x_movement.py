#!/usr/bin/env python3
# Kaspa Pulse - Entity X Movement Report (Einzelabfrage)
# Ablageort im Repo: scripts/entity_x_movement.py
#
# Anlass 07.10.2026: Kaspador meldet eine Bewegung von rund 3.143.758 KAS
# von einer Gate-Adresse an Entity X. Dieses Skript prueft die Meldung auf
# der Kette nach und liefert die Einzelteile, die eine Meldung belegen oder
# widerlegen: Transaktions-ID, Blockzeit UTC, Betrag je Eingang,
# Absenderadresse mit Label, Kontostand vor und nach der Bewegung mit
# Zeitpunkt, und den Umlauf vom selben Abrufzeitpunkt.
#
# Das Skript SCHREIBT NICHTS und POSTET NICHTS. Es liest und druckt.
#
# Labels, Netzzugriff und Seitenlogik kommen aus entity_x_inflows.py, damit
# es nur eine Quelle fuer die Adressbeschriftungen gibt.
#
# Wortregel, wie in den anderen Bots: wir sehen einen Transfer. Nicht den
# Eigentuemer, nicht das Motiv, nicht das Ziel dahinter. Deshalb heisst es
# hier "received" und "left", nie "buy" oder "sell".
#
# Nur Standardbibliothek.

import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entity_x_inflows as x  # noqa: E402  Labels, get_json, fetch_transactions

SOMPI = x.SOMPI
ADDRESS = x.ADDRESS
API = x.API

# Fenster, in dem wir nach Bewegungen suchen. 36 Stunden deckt "heute" und
# den Vortag ab, damit der Stand davor sicher mit drin ist.
HOURS = float(os.environ.get("HOURS", "36"))

# Was Kaspador gemeldet hat. Steht hier, damit die Gegenprobe im Log
# nachvollziehbar ist und nicht aus dem Kopf verglichen wird.
CLAIM_KAS = float(os.environ.get("CLAIM_KAS", "3143758"))
CLAIM_LOCAL = os.environ.get("CLAIM_LOCAL", "2026-10-07 10:15 Europe/Berlin")

# Zweitquelle, wie mit Louka vereinbart. Kandidatenpfade, weil keine
# dokumentierte Route vorliegt. Was nicht antwortet, wird als nicht
# erreichbar gemeldet, nicht geraten.
LOUKA_HOST = os.environ.get("LOUKA_HOST", "louka-txs.com")
LOUKA_PATHS = [
    f"/api/address/{ADDRESS}",
    f"/api/v1/address/{ADDRESS}/transactions",
    f"/address/{ADDRESS}",
    "/api/transactions?limit=50",
    "/",
]


def stamp(ts):
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))


def kas(v):
    return format(v, ",.8f")


def balance_now():
    d = x.get_json(f"{API}/addresses/{ADDRESS}/balance")
    return float(d["balance"]) / SOMPI


def coinsupply():
    d = x.get_json(f"{API}/info/coinsupply")
    return {
        "circulating_kas": float(d["circulatingSupply"]) / SOMPI,
        "max_supply_kas": float(d["maxSupply"]) / SOMPI,
        "raw": d,
    }


def movements(txs, since_ts):
    """Pro Transaktion der Nettofluss an die Adresse, gleiche Logik wie im
    Cost-Basis-Skript: Ausgaenge an uns minus Eingaenge von uns."""
    out = []
    for t in txs:
        bt = (t.get("block_time") or 0) / 1000.0
        if bt < since_ts:
            continue
        gain = 0.0
        for o in t.get("outputs") or []:
            if x.out_addr(o) == ADDRESS:
                gain += float(o.get("amount", 0)) / SOMPI
        spend = 0.0
        senders = {}
        for i in t.get("inputs") or []:
            a = i.get("previous_outpoint_address")
            amt = i.get("previous_outpoint_amount")
            if a is None or amt is None:
                continue
            amt = float(amt) / SOMPI
            if a == ADDRESS:
                spend += amt
            else:
                senders[a] = senders.get(a, 0.0) + amt
        recips = {}
        for o in t.get("outputs") or []:
            a = x.out_addr(o)
            if a and a != ADDRESS:
                recips[a] = recips.get(a, 0.0) + float(o.get("amount", 0)) / SOMPI
        net = gain - spend
        out.append({
            "ts": bt, "utc": stamp(bt), "tx": t.get("transaction_id", ""),
            "net_kas": net, "received_kas": gain, "spent_kas": spend,
            "senders": senders, "recipients": recips,
            "coinbase": not (t.get("inputs") or []),
        })
    out.sort(key=lambda r: r["ts"])
    return out


def fetch_text(url, limit=400000, timeout=25):
    req = urllib.request.Request(
        url, headers={"User-Agent": "kaspapulse-crosscheck/1.0",
                      "Accept": "application/json, text/html, */*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read(limit).decode("utf-8", "replace")


def discover_louka():
    """Die Adressseite ist eine JS-Anwendung, das HTML tragt keine Zahlen.
    Also die Skriptbuendel holen und darin nach der API-Route suchen.

    Fremder Code wird NICHT ausgefuehrt, nur nach Mustern durchsucht.
    """
    import re
    cands = set()
    try:
        _, html = fetch_text(f"https://{LOUKA_HOST}/")
    except Exception as e:  # noqa: BLE001
        print(f"  startseite nicht lesbar: {e}")
        return []
    bundles = re.findall(r'(?:src|href)="([^"]+\.js)"', html)
    print(f"  {len(bundles)} skriptdateien im html: {bundles[:6]}")
    for b in bundles[:6]:
        url = b if b.startswith("http") else f"https://{LOUKA_HOST}/{b.lstrip('/')}"
        try:
            _, js = fetch_text(url)
        except Exception as e:  # noqa: BLE001
            print(f"  {url} nicht lesbar: {e}")
            continue
        print(f"  {url}: {len(js)} zeichen")
        trim = '"\'`,);'
        for m in re.findall(r'https?://[A-Za-z0-9._-]*louka[A-Za-z0-9._/-]*', js):
            cands.add(m.rstrip(trim))
        for m in re.findall(r'https?://api[A-Za-z0-9._-]*\.[a-z]{2,}[A-Za-z0-9._/-]*', js):
            cands.add(m.rstrip(trim))
        for m in re.findall(r'(/(?:api|rest)/[A-Za-z0-9._/-]{2,60})', js):
            cands.add("https://" + LOUKA_HOST + m.rstrip(trim))
    out = sorted(c for c in cands if len(c) < 160)
    print(f"  {len(out)} kandidaten gefunden")
    for c in out[:40]:
        print(f"    {c}")
    return out


def probe_louka():
    res = []
    for path in LOUKA_PATHS:
        url = f"https://{LOUKA_HOST}{path}"
        row = {"url": url}
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "kaspapulse-crosscheck/1.0",
                              "Accept": "application/json, text/html"})
            with urllib.request.urlopen(req, timeout=20) as r:
                body = r.read(60000).decode("utf-8", "replace")
            row["status"] = r.status
            row["bytes"] = len(body)
            # Fremde Antwort ist Datenmaterial, nichts wird ausgefuehrt.
            try:
                row["json_keys"] = list(json.loads(body))[:15]
            except ValueError:
                row["snippet"] = body[:400].replace("\n", " ")
        except urllib.error.HTTPError as e:
            row["status"] = e.code
            row["error"] = f"HTTP {e.code} {e.reason}"
        except Exception as e:  # noqa: BLE001
            row["error"] = f"{type(e).__name__}: {e}"[:200]
        res.append(row)
        print(f"  {url}")
        print(f"    {json.dumps({k: v for k, v in row.items() if k != 'url'})[:500]}")
    return res


def main():
    t0 = time.time()
    print("=" * 74)
    print("ENTITY X MOVEMENT REPORT")
    print(f"lauf gestartet {stamp(t0)}")
    print(f"gemeldet von kaspador: +{CLAIM_KAS:,.0f} KAS, {CLAIM_LOCAL}")
    print("=" * 74)

    print("\n[1] kontostand und umlauf")
    bal = balance_now()
    t_bal = time.time()
    print(f"  kontostand   {kas(bal)} KAS   abgerufen {stamp(t_bal)}")
    sup = coinsupply()
    t_sup = time.time()
    print(f"  umlauf       {kas(sup['circulating_kas'])} KAS   "
          f"abgerufen {stamp(t_sup)}")
    print(f"  maxSupply    {kas(sup['max_supply_kas'])} KAS (laut knoten)")

    print(f"\n[2] bewegungen der letzten {HOURS:.0f} stunden")
    txs = x.fetch_transactions(ADDRESS, max_pages=3)
    print(f"  {len(txs)} transaktionen geholt")
    since = t0 - HOURS * 3600
    mv = movements(txs, since)
    print(f"  {len(mv)} transaktionen im fenster seit {stamp(since)}")

    # Rueckwaerts vom aktuellen Stand: Stand vor jeder Bewegung.
    netto_fenster = sum(m["net_kas"] for m in mv)
    stand_vor = bal - netto_fenster
    print(f"\n  stand vor dem fenster      {kas(stand_vor)} KAS")
    lauf = stand_vor
    for m in mv:
        vor = lauf
        lauf += m["net_kas"]
        m["balance_before"] = vor
        m["balance_after"] = lauf
        art = "ZUFLUSS" if m["net_kas"] > 0 else "ABFLUSS"
        print(f"\n  {art}  {m['utc']}")
        print(f"    tx            {m['tx']}")
        print(f"    netto         {m['net_kas']:+,.8f} KAS")
        print(f"    davon rein    {kas(m['received_kas'])} KAS")
        print(f"    davon raus    {kas(m['spent_kas'])} KAS")
        print(f"    stand vorher  {kas(vor)} KAS")
        print(f"    stand nachher {kas(lauf)} KAS")
        if m["coinbase"]:
            print("    coinbase, direkt aus einem block reward")
        for a, v in sorted(m["senders"].items(), key=lambda p: -p[1]):
            label = x.KNOWN.get(a)
            print(f"    absender      {kas(v)} KAS  {a}"
                  f"{'  LABEL ' + label if label else '  (kein label)'}")
        for a, v in sorted(m["recipients"].items(), key=lambda p: -p[1]):
            label = x.KNOWN.get(a)
            print(f"    empfaenger    {kas(v)} KAS  {a}"
                  f"{'  LABEL ' + label if label else '  (kein label)'}")
    print(f"\n  stand nach dem fenster     {kas(lauf)} KAS")
    print(f"  kontrolle gegen knoten     {kas(bal)} KAS  "
          f"abweichung {lauf - bal:+,.8f}")

    print("\n[3] gegenprobe der gemeldeten zahl")
    zu = [m for m in mv if m["net_kas"] > 0]
    summe_zu = sum(m["net_kas"] for m in zu)
    print(f"  zufluesse im fenster  {len(zu)}, summe {kas(summe_zu)} KAS")
    treffer = [m for m in zu if abs(m["net_kas"] - CLAIM_KAS) <= 1.0]
    if treffer:
        for m in treffer:
            print(f"  TREFFER auf den coin genau: {m['tx']} am {m['utc']}, "
                  f"{kas(m['net_kas'])} KAS")
    else:
        print(f"  kein einzelzufluss trifft {CLAIM_KAS:,.0f} KAS auf 1 KAS genau")
        for m in zu:
            print(f"    {m['utc']}  {kas(m['net_kas'])} KAS  "
                  f"differenz zur meldung {m['net_kas'] - CLAIM_KAS:+,.2f}")

    print("\n[4] anteil am umlauf, beide staende")
    circ = sup["circulating_kas"]
    for name, v in (("vor der bewegung", stand_vor), ("nach der bewegung", bal)):
        print(f"  {name:<20} {kas(v)} KAS = {v / circ * 100:.6f} % des umlaufs")
    print(f"  umlauf-nenner        {kas(circ)} KAS, abgerufen {stamp(t_sup)}")
    print("  hinweis: der umlauf waechst laufend, der anteil gilt nur zu "
          "dieser abrufzeit")

    print("\n" + "=" * 74)
    print(f"fertig in {time.time() - t0:.1f} sekunden. nichts geschrieben, "
          f"nichts gepostet.")
    print("=" * 74)

    # Maschinenlesbar ins Log, damit die Zahlen ohne Nachtippen weiterwandern.
    print("\nJSON_BEGIN")
    print(json.dumps({
        "fetched_at_utc": stamp(t_bal),
        "supply_fetched_at_utc": stamp(t_sup),
        "balance_now_kas": round(bal, 8),
        "balance_before_window_kas": round(stand_vor, 8),
        "circulating_kas": round(circ, 8),
        "max_supply_kas": round(sup["max_supply_kas"], 8),
        "window_hours": HOURS,
        "claim_kas": CLAIM_KAS,
        "movements": [{
            "utc": m["utc"], "tx": m["tx"],
            "net_kas": round(m["net_kas"], 8),
            "balance_before_kas": round(m["balance_before"], 8),
            "balance_after_kas": round(m["balance_after"], 8),
            "senders": [{"address": a, "kas": round(v, 8),
                         "label": x.KNOWN.get(a)}
                        for a, v in sorted(m["senders"].items(),
                                           key=lambda p: -p[1])],
            "recipients": [{"address": a, "kas": round(v, 8),
                            "label": x.KNOWN.get(a)}
                           for a, v in sorted(m["recipients"].items(),
                                              key=lambda p: -p[1])],
        } for m in mv],
        "louka_probe": louka,
        "label_source": x.KNOWN_SOURCE,
    }, indent=2))
    print("JSON_END")

    # Ganz am Ende noch einmal kurz, damit ein kurzer Blick ins Log reicht.
    print("\n" + "=" * 74)
    print("KURZFASSUNG")
    print("=" * 74)
    print(f"abruf kontostand   {stamp(t_bal)}")
    print(f"abruf umlauf       {stamp(t_sup)}")
    print(f"stand vorher       {kas(stand_vor)} KAS")
    print(f"stand nachher      {kas(bal)} KAS")
    print(f"differenz          {bal - stand_vor:+,.8f} KAS")
    print(f"umlauf             {kas(circ)} KAS")
    print(f"anteil vorher      {stand_vor / circ * 100:.6f} %")
    print(f"anteil nachher     {bal / circ * 100:.6f} %")
    for m in mv:
        art = "zufluss" if m["net_kas"] > 0 else "abfluss"
        quellen = "; ".join(
            f"{kas(v)} KAS von {a[:26]}.. [{x.KNOWN.get(a) or 'kein label'}]"
            for a, v in sorted(m["senders"].items(), key=lambda p: -p[1]))
        ziele = "; ".join(
            f"{kas(v)} KAS an {a[:26]}.. [{x.KNOWN.get(a) or 'kein label'}]"
            for a, v in sorted(m["recipients"].items(), key=lambda p: -p[1]))
        print(f"{art} {m['utc']}  {m['net_kas']:+,.8f} KAS  tx {m['tx']}")
        if quellen:
            print(f"    von: {quellen}")
        if ziele:
            print(f"    an:  {ziele}")

    # Zweitquelle ganz am Ende, damit sie im Log nicht untergeht.
    print("\n" + "=" * 74)
    print("[5] ZWEITQUELLE louka-txs.com")
    print("=" * 74)
    print("  5a feste kandidatenpfade")
    louka = probe_louka()
    print("\n  5b route aus den skriptbuendeln suchen")
    entdeckt = discover_louka()
    print("\n  ERGEBNIS zweitquelle")
    print(f"    feste pfade mit 200: "
          f"{sum(1 for r in louka if r.get('status') == 200)} von {len(louka)}")
    print(f"    json-antworten:      "
          f"{sum(1 for r in louka if r.get('json_keys'))}")
    print(f"    api-kandidaten:      {len(entdeckt)}")
    if not any(r.get("json_keys") for r in louka) and not entdeckt:
        print("    KEINE maschinenlesbare route gefunden. Der Vorgang laesst "
              "sich hier nicht gegenrechnen.")


if __name__ == "__main__":
    main()
