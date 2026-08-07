#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""haelt die wochenzahlen des dashboards aktuell, ohne dass jemand die
index.html anfassen muss.

quelle der wahrheit ist data/weekly.json. dieses skript schreibt den
DATA-block in der index.html zwischen den markern WEEKLY-DATA-START und
WEEKLY-DATA-END neu. kommentare zur herkunft der zahlen leben in
data/weekly-notes.md, nicht im code.

zwei betriebsarten:

  --autofill      holt alles, was eine offene api hat (defillama, coingecko,
                  api.kaspa.org), legt die zeile der laufenden woche an oder
                  aktualisiert sie, rechnet die fenster (d7/d30/d90, dex) und
                  schreibt json plus index.html. handwerte bleiben null, bis
                  sie per --apply-input kommen. jede quelle darf einzeln
                  ausfallen, dann behaelt das feld seinen alten wert (regel 42,
                  lieber eine alte echte zahl als eine frische geratene).

  --apply-input   liest data/dashboard-input.json und mischt die handwerte in
                  die zeile der laufenden woche. format:
                      {"row": {"tps": 0.91, "holders": 50.6, ...},
                       "top": {"exchange_baselines": {...}},
                       "note": "freitext fuer weekly-notes"}
                  "row" geht in history[-1].m, "top" wird tief in die
                  wurzel gemischt, "note" wird an data/weekly-notes.md
                  angehaengt.

lokal:
    python3 scripts/dashboard_weekly.py --selftest
    DRY_RUN=1 python3 scripts/dashboard_weekly.py --autofill
in github actions:
    python3 scripts/dashboard_weekly.py --autofill
    python3 scripts/dashboard_weekly.py --apply-input
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEEKLY_PATH = os.path.join(ROOT, "data", "weekly.json")
INPUT_PATH = os.path.join(ROOT, "data", "dashboard-input.json")
NOTES_PATH = os.path.join(ROOT, "data", "weekly-notes.md")
INDEX_PATH = os.path.join(ROOT, "index.html")

MARK_START = "// WEEKLY-DATA-START"
MARK_END = "// WEEKLY-DATA-END"

ENTITY_X = ("kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a")

UA = {"User-Agent": "kaspa-pulse-bot/1.0 (+https://kaspapulse.com)"}
TIMEOUT = 30

# felder, die nur per hand kommen. autofill fasst sie nie an.
MANUAL_FIELDS = ("tps", "covenant_tx", "igra_tx", "kasplex_tx", "holders",
                 "active_addr", "holder_addr", "exchange_kas", "fees_day")


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


# ---------------------------------------------------------------- quellen

def fetch_auto():
    """holt alle api-werte. liefert dict mit None fuer alles, was nicht
    geklappt hat, plus eine liste der probleme fuers log."""
    out = {"tvl_kasplex": None, "tvl_igra": None, "kasplex_dex": None,
           "igra_dex": None, "price_usd": None, "mcap_usd": None,
           "circ_supply": None, "mined_pct": None, "hashrate": None,
           "block_reward": None, "entityx_kas": None}
    problems = []

    try:
        for c in get_json("https://api.llama.fi/v2/chains"):
            n = (c.get("name") or "").lower()
            if n == "kasplex":
                out["tvl_kasplex"] = round(float(c["tvl"]))
            elif n == "igra":
                out["tvl_igra"] = round(float(c["tvl"]))
        if out["tvl_kasplex"] is None or out["tvl_igra"] is None:
            problems.append("defillama chains ohne kasplex oder igra")
    except Exception as exc:  # noqa: BLE001
        problems.append("defillama chains: %s" % exc)

    for chain, key in (("kasplex", "kasplex_dex"), ("igra", "igra_dex")):
        try:
            j = get_json("https://api.llama.fi/overview/dexs/%s"
                         "?excludeTotalDataChart=true"
                         "&excludeTotalDataChartBreakdown=true" % chain)
            v = j.get("total24h")
            out[key] = round(float(v)) if v is not None else None
        except Exception as exc:  # noqa: BLE001
            problems.append("defillama dexs %s: %s" % (chain, exc))

    try:
        j = get_json("https://api.coingecko.com/api/v3/simple/price"
                     "?ids=kaspa&vs_currencies=usd&include_market_cap=true")
        k = j.get("kaspa") or {}
        if "usd" in k:
            out["price_usd"] = round(float(k["usd"]), 6)
        if "usd_market_cap" in k:
            out["mcap_usd"] = round(float(k["usd_market_cap"]))
    except Exception as exc:  # noqa: BLE001
        problems.append("coingecko: %s" % exc)

    try:
        j = get_json("https://api.kaspa.org/info/coinsupply")
        circ = float(j["circulatingSupply"]) / 1e8
        mx = float(j["maxSupply"]) / 1e8
        out["circ_supply"] = round(circ)
        out["mined_pct"] = round(100.0 * circ / mx, 2)
    except Exception as exc:  # noqa: BLE001
        problems.append("coinsupply: %s" % exc)

    try:
        j = get_json("https://api.kaspa.org/info/hashrate?stringOnly=false")
        # gleiche umrechnung wie im dashboard, api liefert TH/s
        out["hashrate"] = round(float(j["hashrate"]) / 1e3, 1)
    except Exception as exc:  # noqa: BLE001
        problems.append("hashrate: %s" % exc)

    try:
        j = get_json("https://api.kaspa.org/info/blockreward?stringOnly=false")
        out["block_reward"] = round(float(j["blockreward"]), 2)
    except Exception as exc:  # noqa: BLE001
        problems.append("blockreward: %s" % exc)

    try:
        j = get_json("https://api.kaspa.org/addresses/%s/balance" % ENTITY_X)
        out["entityx_kas"] = round(float(j["balance"]) / 1e8)
    except Exception as exc:  # noqa: BLE001
        problems.append("entity x balance: %s" % exc)

    return out, problems


# ---------------------------------------------------------------- rechnen

def parse_date(s):
    return dt.date.fromisoformat(str(s))


def find_anchor(history, today, target_days, min_days):
    """die zeile, deren datum am naechsten an target_days vor heute liegt,
    aber mindestens min_days alt ist. None, wenn keine passt."""
    best, best_off = None, None
    for row in history:
        age = (today - parse_date(row["date"])).days
        if age < min_days:
            continue
        off = abs(age - target_days)
        if best_off is None or off < best_off:
            best, best_off = row, off
    return best


def pct(now, base):
    if now is None or base in (None, 0):
        return None
    return round((now / base - 1.0) * 100.0, 1)


def upsert_row(data, today):
    """zeile der laufenden woche holen oder anlegen (alle felder null)."""
    hist = data.setdefault("history", [])
    if hist and hist[-1]["date"] == str(today):
        return hist[-1]
    keys = set(MANUAL_FIELDS) | {"tvl_total", "tvl_kasplex", "tvl_igra",
                                 "hashrate", "block_reward", "dex_vol",
                                 "kasplex_dex", "igra_dex", "entityx_kas"}
    if hist:
        keys |= set(hist[-1]["m"].keys())
    row = {"date": str(today), "m": {k: None for k in sorted(keys)}}
    hist.append(row)
    return row


def apply_context(data, auto):
    """preis, marketcap, supply, block reward. das ist tageskontext, kein
    wochenwert, darf also an jedem wochentag aufgefrischt werden."""
    if auto["circ_supply"] is not None:
        data["circ_supply"] = auto["circ_supply"]
    cf = data.setdefault("context_fallback", {})
    if auto["price_usd"] is not None:
        cf["price_usd"] = auto["price_usd"]
    if auto["mcap_usd"] is not None:
        cf["mcap_usd"] = auto["mcap_usd"]
    if auto["mined_pct"] is not None:
        cf["mined_pct"] = auto["mined_pct"]
    if auto["block_reward"] is not None:
        data.setdefault("emission", {})["block_reward"] = auto["block_reward"]


def prune_non_mondays(data):
    """wochenzeilen gehoeren auf den montag. testlaeufe an anderen tagen
    (passiert, siehe 07.08.) hinterlassen sonst zeilen, die die d7-fenster
    und den chart verfaelschen. hier fliegen sie wieder raus."""
    hist = data.get("history", [])
    keep = [r for r in hist if parse_date(r["date"]).weekday() == 0]
    dropped = len(hist) - len(keep)
    if dropped:
        print("WARNUNG: %d nicht-montags-zeile(n) entfernt (testlaeufe)"
              % dropped)
        data["history"] = keep
        if keep:
            data["updated"] = keep[-1]["date"]
            data["next_update"] = str(parse_date(keep[-1]["date"])
                                      + dt.timedelta(days=7))
    return dropped


def apply_auto(data, auto, today):
    row = upsert_row(data, today)
    m = row["m"]
    prev_rows = [r for r in data["history"] if r["date"] != str(today)]
    prev = prev_rows[-1] if prev_rows else None

    def put(key, val):
        if val is not None:
            m[key] = val

    put("tvl_kasplex", auto["tvl_kasplex"])
    put("tvl_igra", auto["tvl_igra"])
    if auto["tvl_kasplex"] is not None and auto["tvl_igra"] is not None:
        m["tvl_total"] = auto["tvl_kasplex"] + auto["tvl_igra"]
    put("kasplex_dex", auto["kasplex_dex"])
    put("igra_dex", auto["igra_dex"])
    if auto["kasplex_dex"] is not None and auto["igra_dex"] is not None:
        m["dex_vol"] = auto["kasplex_dex"] + auto["igra_dex"]
    put("hashrate", auto["hashrate"])
    put("block_reward", auto["block_reward"])
    put("entityx_kas", auto["entityx_kas"])

    # kopfdaten
    data["updated"] = str(today)
    data["next_update"] = str(today + dt.timedelta(days=7))
    apply_context(data, auto)

    # fenster. ein fenster ohne anker behaelt seinen alten wert,
    # ein fenster mit anker wird frisch gerechnet.
    hw = data.setdefault("hashrate_windows", {})
    if m.get("hashrate") is not None:
        if prev and prev["m"].get("hashrate"):
            v = pct(m["hashrate"], prev["m"]["hashrate"])
            if v is not None:
                hw["d7"] = v
        a30 = find_anchor(prev_rows, today, 28, 21)
        if a30 and a30["m"].get("hashrate"):
            v = pct(m["hashrate"], a30["m"]["hashrate"])
            if v is not None:
                hw["d30"] = v
        a90 = find_anchor(prev_rows, today, 84, 70)
        if a90 and a90["m"].get("hashrate"):
            v = pct(m["hashrate"], a90["m"]["hashrate"])
            if v is not None:
                hw["d90"] = v

    dw = data.setdefault("dex_windows", {})
    if prev:
        v = pct(m.get("kasplex_dex"), prev["m"].get("kasplex_dex"))
        if v is not None:
            dw["kasplex_w"] = v
        v = pct(m.get("igra_dex"), prev["m"].get("igra_dex"))
        if v is not None:
            dw["igra_w"] = v
    return row


def deep_merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_merge(dst[k], v)
        else:
            dst[k] = v


def apply_input(data, inp, today):
    # handwerte gehoeren zur aktuellen lesung, also in die letzte zeile.
    # ein upsert auf "heute" wuerde am dienstag eine neue zeile anlegen.
    hist = data.get("history")
    row = hist[-1] if hist else upsert_row(data, today)
    for k, v in (inp.get("row") or {}).items():
        # None heisst "diese woche nicht geliefert" und ueberschreibt nichts.
        # eine reihe bewusst leeren geht ueber den wert "leer".
        if v is None:
            continue
        row["m"][k] = None if v == "leer" else v
    deep_merge(data, inp.get("top") or {})
    note = (inp.get("note") or "").strip()
    if note:
        stamp = "\n## Woche %s, handwerte\n\n%s\n" % (today, note)
        with open(NOTES_PATH, "a", encoding="utf-8") as f:
            f.write(stamp)


# ---------------------------------------------------------------- schreiben

def render_index(data):
    src = open(INDEX_PATH, encoding="utf-8").read()
    a = src.index(MARK_START)
    b = src.index(MARK_END) + len(MARK_END)
    block = (MARK_START + "  wird von scripts/dashboard_weekly.py erzeugt.\n"
             "// nichts von hand aendern, quelle ist data/weekly.json, "
             "herkunft der\n"
             "// einzelnen reihen steht in data/weekly-notes.md\n"
             "const DATA = "
             + json.dumps(data, ensure_ascii=False, indent=2)
             + ";\n" + MARK_END)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(src[:a] + block + src[b:])


def save(data):
    with open(WEEKLY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    render_index(data)


# ---------------------------------------------------------------- selbsttest

def run_selftest():
    fails = []

    def ok(what, cond, extra=""):
        if cond:
            print("  ok   %s" % what)
        else:
            fails.append(what)
            print("  FEHL %s %s" % (what, extra))

    today = dt.date(2026, 8, 10)
    data = {
        "updated": "2026-08-03", "next_update": "2026-08-10",
        "history": [
            {"date": "2026-07-13", "m": {"hashrate": 319.3, "kasplex_dex": None,
                                         "igra_dex": None}},
            {"date": "2026-08-03", "m": {"hashrate": 342.5, "kasplex_dex": 99061,
                                         "igra_dex": 10139, "holders": 50.6}},
        ],
        "hashrate_windows": {"d7": 30.6, "d30": -12.1, "d90": -10.2},
        "dex_windows": {"kasplex_w": -4.8, "igra_w": -65.0},
    }
    auto = {"tvl_kasplex": 340000, "tvl_igra": 1500000, "kasplex_dex": 88000,
            "igra_dex": 12000, "price_usd": 0.027, "mcap_usd": 745000000,
            "circ_supply": 27650000000, "mined_pct": 96.33, "hashrate": 351.2,
            "block_reward": 2.31, "entityx_kas": 1548084255}

    print("autofill")
    row = apply_auto(data, auto, today)
    ok("neue zeile angelegt", data["history"][-1]["date"] == "2026-08-10")
    ok("tvl summiert", row["m"]["tvl_total"] == 1840000)
    ok("dex summiert", row["m"]["dex_vol"] == 100000)
    ok("handwerte bleiben null", row["m"].get("holders") is None)
    ok("kopfdatum stimmt", data["updated"] == "2026-08-10"
       and data["next_update"] == "2026-08-17")
    ok("d7 frisch gerechnet",
       abs(data["hashrate_windows"]["d7"] - 2.5) < 0.11,
       data["hashrate_windows"]["d7"])
    ok("d30 nimmt den 4-wochen-anker",
       abs(data["hashrate_windows"]["d30"] - 10.0) < 0.1,
       data["hashrate_windows"]["d30"])
    ok("d90 ohne anker bleibt stehen",
       data["hashrate_windows"]["d90"] == -10.2)
    ok("dex fenster gegen vorwoche",
       abs(data["dex_windows"]["kasplex_w"] - (-11.2)) < 0.1,
       data["dex_windows"]["kasplex_w"])

    print("zweiter lauf am selben tag")
    auto2 = dict(auto, hashrate=352.0)
    apply_auto(data, auto2, today)
    ok("keine doppelte zeile", len(data["history"]) == 3)
    ok("wert aktualisiert", data["history"][-1]["m"]["hashrate"] == 352.0)

    print("ausfall einer quelle")
    auto3 = {k: None for k in auto}
    before = json.loads(json.dumps(data["history"][-1]["m"]))
    apply_auto(data, auto3, today)
    ok("alte werte ueberleben den ausfall",
       data["history"][-1]["m"]["hashrate"] == before["hashrate"])

    print("handwerte")
    apply_input(data, {"row": {"holders": 50.9, "tps": 0.95}}, today)
    ok("handwert gesetzt", data["history"][-1]["m"]["holders"] == 50.9)
    ok("autowert unberuehrt", data["history"][-1]["m"]["hashrate"] == 352.0)
    apply_input(data, {"top": {"exchange_baselines": {"m3": {"n": 1}}}}, today)
    ok("top tief gemischt",
       data["exchange_baselines"]["m3"]["n"] == 1)
    apply_input(data, {"row": {"holders": None, "tps": "leer"}}, today)
    ok("null im input ueberschreibt nichts",
       data["history"][-1]["m"]["holders"] == 50.9)
    ok("'leer' leert die reihe bewusst",
       data["history"][-1]["m"]["tps"] is None)
    apply_input(data, {"row": {"holders": 51.0}}, dt.date(2026, 8, 11))
    ok("dienstags-input landet in der montagszeile",
       data["history"][-1]["date"] == "2026-08-10"
       and data["history"][-1]["m"]["holders"] == 51.0)

    print("montags-schutz")
    data["history"].append({"date": "2026-08-14", "m": {"hashrate": 999.0}})
    data["updated"] = "2026-08-14"
    dropped = prune_non_mondays(data)
    ok("freitags-testzeile entfernt", dropped == 1
       and data["history"][-1]["date"] == "2026-08-10")
    ok("kopfdatum zurueckgesetzt", data["updated"] == "2026-08-10"
       and data["next_update"] == "2026-08-17")
    ok("montagszeilen ueberleben das aufraeumen",
       [r["date"] for r in data["history"]]
       == ["2026-07-13", "2026-08-03", "2026-08-10"])

    print("")
    if fails:
        print("%d testfaelle GESCHEITERT" % len(fails))
        return 1
    print("alle testfaelle bestanden")
    return 0


# ---------------------------------------------------------------- hauptlauf

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--autofill", action="store_true")
    ap.add_argument("--apply-input", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return run_selftest()

    with open(WEEKLY_PATH, encoding="utf-8") as f:
        data = json.load(f)
    today = dt.date.today()

    if args.autofill:
        auto, problems = fetch_auto()
        prune_non_mondays(data)
        if today.weekday() == 0:
            apply_auto(data, auto, today)
        else:
            apply_context(data, auto)
            print("kein montag, nur preis/kontext aufgefrischt, "
                  "keine neue wochenzeile")
        for p in problems:
            print("WARNUNG %s" % p)
        got = sum(1 for v in auto.values() if v is not None)
        print("autofill, %d von %d werten geholt" % (got, len(auto)))
    elif args.apply_input:
        if not os.path.exists(INPUT_PATH):
            print("kein %s, nichts zu tun" % INPUT_PATH)
            return 0
        with open(INPUT_PATH, encoding="utf-8") as f:
            inp = json.load(f)
        apply_input(data, inp, today)
        print("handwerte eingemischt")
    else:
        print("nichts zu tun, --autofill oder --apply-input angeben")
        return 1

    if os.environ.get("DRY_RUN"):
        print("DRY_RUN, nichts geschrieben")
        print(json.dumps(data["history"][-1], ensure_ascii=False, indent=2))
        return 0

    save(data)
    print("geschrieben, data/weekly.json und index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
