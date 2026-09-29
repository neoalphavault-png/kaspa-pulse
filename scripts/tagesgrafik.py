#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tagesgrafik.py, eine Grafik pro Tag fuer X und Discord.

ZWECK (Ben, 29.09.2026). Eine Grafik, die ein Kaspa-Halter teilt, um damit
anzugeben. Hype ueber Fakten, nie ueber den Kurs. Jede Grafik hat drei
Zutaten: eine Zahl, die stolz macht, einen Kontrast, der sie sofort
verstaendlich macht, und eine Zeile Absender.

Vorlage ist die Entity-X-Grafik vom 29.09. (pruefung_entityx_grafik.py auf
dem Pruef-Branch pruefung/entity-x-2026-09-28): 1080x1350, #080B0F, #49EACB,
Falke und Schriftzug oben und unten, keine Domain, kein Link.

ZEHN FORMEN, jede mit eigener Vorlage (FORMEN unten) und eigener Messung:

   1  Wochenzahl        montags fest. Adressen mit nennenswertem Guthaben
                        oder Hashrate gegen die Vorwoche, im Lauf gemessen
                        (week-input.json steht um 07:30 noch auf der Vorwoche)
   2  Entity X          Anteil am Umlauf plus letzte Bewegung, von der Kette
   3  Countdown         Tage bis zur naechsten Reward-Senkung, Anker-Arithmetik
   4  Massstab          Bloecke in Alltagsgroessen, Blockrate im Lauf gemessen
   5  Miner-Oekonomie   neue Coins gegen Gebuehren, dieselben 30 Tage
   6  Aus der Kette     ein Fakt aus der Historie
   7  Community         Frage aus #data-requests, von Hand
                        (data/tagesgrafik-community.json)
   8  Sicherheit        Hashrate und Sicherheitsbudget, nie ein Angriff
   9  Adressen          Adressen ueber Schwellen mit Wochenbewegung
  10  Herkunft          kein Premine, kein Presale, kein Dev-Fund, gemint-Anteil
  11  Nodes             vorbereitet, gesperrt bis die Tagesreihe beschlossen ist

LUECKE BEI FORM 9. Ben wollte 1k, 10k, 100k und 1M KAS. Kaspalytics hat
Schwellen nur fuer 0,01, 1 und 100 KAS, 1000+ antwortet mit http 400
(address_thresholds_log.py, 22.09.2026). Die Rangliste (richlist_log.py)
reicht bis 284.576 KAS und ist Stufe 1, nur Archiv. Form 9 zeigt deshalb
100 und 1 KAS. Lieber eine Luecke als eine falsche Zeile.

FORM 5 LIVE STATT CSV. Die Monats-CSV liegt nur auf dem Pruef-Branch und
waere eingefroren. Gerechnet wird mit derselben Methode im selben Lauf:
Gebuehren je Tag von Kaspalytics, neue Coins je Tag aus dem Emissionsplan,
fuer genau dieselben Tage, Hashrate aus api.kaspa.org fuer dieselben Tage.

REGELN, vor jedem Rendern erzwungen (textpruefung()):
  jede Grafik traegt ein Datum im Inhalt und "as of <tag>, <zeit> utc" im Fuss
  "%" statt "percent", Ziffern statt Zahlwoertern
  kein Doppelpunkt ausser in Uhrzeiten, kein Gedankenstrich, kein Pfeil
  keine Domain, kein Link (einzige Ausnahme ist das Explorer-Label gate.io)
  kein Kursziel, kein Dollar- oder Kurswert
  Wortliste: sold, buy, bought, purchase, dump, whale, because, motive ...
  Form 8 ohne Angreifer-Szenario (attack, 51, attacker ...)
  kein "never" und kein "record", "highest", "lowest" ohne Zeitraum
  X-Text ohne Link und unter 240 Zeichen

ROTATION (waehle_form()). Ereignis schlaegt Plan: Reward-Senkung in hoechstens
3 Tagen gibt Form 3, eine Entity-X-Bewegung ab 500.000 KAS in den letzten
24 Stunden Form 2, Montag Form 1. Sonst die Form, die in dieser Woche noch
nicht lief und in den letzten 30 Tagen am seltensten, bei Gleichstand die,
deren letzter Lauf am laengsten her ist. data/tagesgrafik-log.json haelt,
welche Form wann lief.

AUSGABE: PNG 1080x1350, Vorschau 390 px, Discord-Text, X-Text und eine
Zeile Selbstpruefung. Mit --senden geht alles an DISCORD_WEBHOOK_OPS
(#moderator-only). Es gibt keinen oeffentlichen Post aus diesem Skript.

    python3 scripts/tagesgrafik.py --out /tmp/tg                 heute, rotiert
    python3 scripts/tagesgrafik.py --out /tmp/tg --form 4        eine Form
    python3 scripts/tagesgrafik.py --messen --form 4 > m.json    nur messen
    python3 scripts/tagesgrafik.py --aus m.json --out /tmp/tg    aus Messung
    python3 scripts/tagesgrafik.py --selftest
"""
import argparse
import base64
import datetime as dt
import json
import math
import os
import re
import sys
import time
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

LOG = REPO / "data" / "tagesgrafik-log.json"
COMMUNITY = REPO / "data" / "tagesgrafik-community.json"
FALKE = REPO / "graphics" / "falcon.b64"
W, H = 1080, 1350
VORSCHAU = 390
REST = "https://api.kaspa.org"
UA = "kaspa-pulse-bot (+https://kaspapulse.com)"
TIMEOUT = 25
EX_ADR = "kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a"
GENESIS = "58c2d4199e21f910d1571d114969cecef48f09f934d42ccb6a281a15868f2999"
MONATE = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
X_ZEIT = "17:00"                     # Ben plant X um 17:00 Berlin
EX_EREIGNIS = 500000                 # KAS in 24 h, dann Form 2
CUT_EREIGNIS_TAGE = 3                # Reward-Senkung in hoechstens 3 Tagen, dann Form 3
FREIGESCHALTET = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}   # 11 erst nach Bens Beschluss


class Stop(Exception):
    """Diese Form kann heute nicht belegt werden. Lieber keine Grafik als
    eine falsche."""


# ------------------------------------------------------------------ werkzeug

def hole(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:                   # noqa: BLE001
            last = exc
            if i + 1 < tries:
                time.sleep(2 * (i + 1))
    raise Stop("abruf fehlgeschlagen %s (%s)" % (url, last))


def jetzt_utc():
    return dt.datetime.now(dt.timezone.utc)


def tag(d):
    """datum als "29 sep 2026"."""
    if isinstance(d, str):
        d = dt.date.fromisoformat(d[:10])
    return "%d %s %d" % (d.day, MONATE[d.month - 1], d.year)


def tag_kurz(d):
    if isinstance(d, str):
        d = dt.date.fromisoformat(d[:10])
    return "%d %s" % (d.day, MONATE[d.month - 1])


def uhr(t):
    return t.strftime("%H:%M") + " utc"


def ganz(n):
    return "{:,}".format(int(round(float(n))))


def kas(v):
    v = float(v)
    if abs(v) >= 1e9:
        return "%.2fB KAS" % (v / 1e9)
    if abs(v) >= 1e6:
        return "%.2fM KAS" % (v / 1e6)
    return "%s KAS" % ganz(v)


def kurz(v):
    v = float(v)
    if abs(v) >= 1e9:
        return "%.2fB" % (v / 1e9)
    if abs(v) >= 1e6:
        return "%.2fM" % (v / 1e6)
    return ganz(v)


def berlin_jetzt():
    from zoneinfo import ZoneInfo
    fest = os.environ.get("TG_JETZT", "").strip()      # nur fuer trockenlaeufe
    if fest:
        return dt.datetime.fromisoformat(fest).astimezone(ZoneInfo("Europe/Berlin"))
    return dt.datetime.now(ZoneInfo("Europe/Berlin"))


# --------------------------------------------------------------- messungen
# Jede Messung gibt ein dict zurueck, das "messzeit_utc" traegt. Alles, was in
# einer Grafik steht, stammt aus genau einem solchen dict, also aus einem Lauf.

def m_supply():
    d = hole(REST + "/info/coinsupply")
    circ = float(d["circulatingSupply"]) / 1e8
    mx = float(d["maxSupply"]) / 1e8
    if not (1e10 < circ < mx <= 3e10):
        raise Stop("coinsupply unplausibel, circ %s max %s" % (circ, mx))
    return circ, mx


def m_balance(adr):
    d = hole(REST + "/addresses/%s/balance" % adr)
    return int(d["balance"]) / 1e8


def m_hashrate_phs():
    d = hole(REST + "/info/hashrate?stringOnly=false")
    ph = float(d["hashrate"]) / 1000.0
    if not 10 < ph < 100000:
        raise Stop("hashrate unplausibel %s PH/s" % ph)
    return ph


def m_blockrate(sekunden=60):
    """Bloecke je Sekunde, gemessen als Zuwachs des virtuellen DAA-Scores."""
    a = hole(REST + "/info/blockdag")
    ta = time.time()
    time.sleep(sekunden)
    b = hole(REST + "/info/blockdag")
    tb = time.time()
    da, db = int(a["virtualDaaScore"]), int(b["virtualDaaScore"])
    bps = (db - da) / (tb - ta)
    if not 5 < bps < 15:
        raise Stop("blockrate unplausibel %.2f" % bps)
    return bps, db


def m_entityx_bewegungen(tage=7):
    """Alle Transaktionen von Entity X der letzten `tage` Tage, netto je
    Transaktion (Eingaenge von Entity X minus Ausgaenge an Entity X), wie
    entity_x_outflows.py."""
    ab_ms = int((jetzt_utc() - dt.timedelta(days=tage)).timestamp() * 1000)
    txs, before = [], 0
    for _ in range(10):
        url = (REST + "/addresses/%s/full-transactions-page?limit=100"
               "&resolve_previous_outpoints=light" % EX_ADR)
        if before:
            url += "&before=%d" % before
        seite = hole(url)
        if not seite:
            break
        txs += seite
        aeltester = min(t.get("block_time") or 0 for t in seite)
        if aeltester < ab_ms:
            break
        before = aeltester
    gesehen, zeilen = set(), []
    for t in txs:
        tid, bt = t.get("transaction_id"), t.get("block_time") or 0
        if tid in gesehen or bt < ab_ms or t.get("is_accepted") is False:
            continue
        gesehen.add(tid)
        rein = sum(float(o.get("amount", 0)) for o in t.get("outputs") or []
                   if (o.get("script_public_key_address") or o.get("address")) == EX_ADR) / 1e8
        raus = 0.0
        for i in t.get("inputs") or []:
            if i.get("previous_outpoint_address") is None:
                raise Stop("eingang ohne adresse in %s, netto nicht belegbar" % tid)
            if i.get("previous_outpoint_address") == EX_ADR:
                raus += float(i.get("previous_outpoint_amount") or 0) / 1e8
        zeilen.append({"zeit_utc": dt.datetime.fromtimestamp(bt / 1000, dt.timezone.utc)
                       .isoformat(timespec="seconds"), "tx": tid, "netto": rein - raus})
    zeilen.sort(key=lambda z: z["zeit_utc"])
    return zeilen


def reward_plan():
    import number_of_day_data as nod
    return nod


def m_kl_reihe(pfad, name, art):
    """Kaspalytics-Tagesreihe {datum: wert}, stichtag wie in kaspalytics.py."""
    import kaspalytics as k
    d = k.hole(pfad)
    werte = k.reihe(d, name) if name else (d.get("datasets") or [{}])[0].get("data") or []
    aus = {}
    for lab, v in zip(d.get("labels") or [], werte):
        if v is None:
            continue
        try:
            aus[k.stichtag(lab, art).isoformat()] = float(v)
        except ValueError:
            continue
    return aus


def m_hashrate_tage():
    """Tagesmittel der Hashrate in TH/s aus api.kaspa.org/info/hashrate/history."""
    roh = hole(REST + "/info/hashrate/history")
    je = {}
    for x in roh:
        t = dt.datetime.fromtimestamp(x["timestamp"] / 1000, dt.timezone.utc)
        je.setdefault(t.date().isoformat(), []).append(x["hashrate_kh"] / 1e9)
    return {d: sum(v) / len(v) for d, v in je.items()}


def emission_am_tag(datum):
    """Neue KAS an einem UTC-Tag aus dem Emissionsplan, eine Senkung innerhalb
    des Tages wird sekundengenau geteilt."""
    nod = reward_plan()
    a = dt.datetime.combine(dt.date.fromisoformat(datum), dt.time(), dt.timezone.utc).timestamp()
    e = a + 86400
    summe, t = 0.0, a
    while t < e:
        cur, _, nxt = nod.reward_state(t)
        bis = min(e, nxt)
        summe += cur * nod.BPS * (bis - t)
        t = bis
    return summe


# ------------------------------------------------------------ die formen
# Jede Form: messen() -> werte (dict, json-faehig), vorlage(werte) -> seite
# (dict mit den Texten der Grafik plus discord, x, pruefung).

def messen_1(now):
    """Wochenzahl. Zwei Kandidaten, beide im Lauf gemessen: Adressen mit
    nennenswertem Guthaben (Kaspalytics, letzter voller Tag gegen 7 Tage
    davor) und Hashrate (api.kaspa.org, Tagesmittel gestern gegen 7 Tage
    davor).

    Nicht aus data/week-input.json: die Montagsroutine schreibt die Datei
    gegen 08:40 Berlin, um 07:30 steht dort noch die Vorwoche (am 28.09.
    committet um 06:42 UTC). Eine Zahl der Vorwoche am Montag waere eine
    Woche alt."""
    kand = []
    try:
        h = m_kl_reihe("address/count/meaningful-balance", "Addresses", "bestand")
        tage = sorted(d for d in h if d < now.date().isoformat())
        d1 = tage[-1]
        d0 = (dt.date.fromisoformat(d1) - dt.timedelta(days=7)).isoformat()
        if d0 in h:
            kand.append({"was": "holders", "jetzt": h[d1], "vorher": h[d0], "d1": d1, "d0": d0})
    except Exception as exc:                        # noqa: BLE001
        print("form 1, holders nicht belegt: %s" % exc)
    try:
        hr = m_hashrate_tage()
        d1 = (now.date() - dt.timedelta(days=1)).isoformat()
        d0 = (now.date() - dt.timedelta(days=8)).isoformat()
        if d1 in hr and d0 in hr:
            kand.append({"was": "hashrate", "jetzt": hr[d1] / 1000, "vorher": hr[d0] / 1000,
                         "d1": d1, "d0": d0})
    except Exception as exc:                        # noqa: BLE001
        print("form 1, hashrate nicht belegt: %s" % exc)
    if not kand:
        raise Stop("keine wochenzahl belegt")
    for k in kand:
        k["pct"] = 100 * (k["jetzt"] / k["vorher"] - 1)
    return {"kandidaten": kand}


def vorlage_1(w):
    for x in w["kandidaten"]:
        x["pct"] = 100 * (x["jetzt"] / x["vorher"] - 1)
    k = max(w["kandidaten"], key=lambda x: x["pct"])
    if k["was"] == "holders":
        plus = k["jetzt"] - k["vorher"]
        je_std = plus / (7 * 24)
        s = {"kopf": "THIS WEEK",
             "wert": ("+" if plus >= 0 else "") + ganz(plus),
             "label": "addresses with a meaningful balance in 7 days, to %s" % tag(k["d1"]),
             "zeilen": [
                 {"num": ganz(k["jetzt"]), "txt": "addresses hold a meaningful balance on %s" % tag_kurz(k["d1"]),
                  "frac": 1.0},
                 {"num": ganz(k["vorher"]), "txt": "on %s, 7 days earlier" % tag_kurz(k["d0"]),
                  "frac": k["vorher"] / k["jetzt"], "ton": "neu"}],
             "satz": "about %s more every hour" % ("%.0f" % je_std) if plus > 0 else
                     "the count moved by %s in 7 days" % ganz(plus),
             "quelle": "sources kaspalytics address counts",
             "x_neugier": "how many will next week add?"}
        gut = plus > 0
    else:
        s = {"kopf": "THIS WEEK",
             "wert": "%.1f PH/s" % k["jetzt"],
             "label": "daily average hashrate on %s" % tag(k["d1"]),
             "zeilen": [
                 {"num": "%+.1f%%" % k["pct"], "txt": "against %s, 7 days earlier" % tag_kurz(k["d0"]),
                  "frac": None},
                 {"num": "%.1f PH/s" % k["vorher"], "txt": "on %s" % tag_kurz(k["d0"]),
                  "frac": None}],
             "satz": "every second, %s quadrillion guesses at the next block" % ganz(k["jetzt"]),
             "quelle": "sources kaspa rest api hashrate history",
             "x_neugier": "that work runs every second of the week."}
        gut = k["pct"] > 0
    s["pruefung"] = ("ja, %s steigt gegen die Vorwoche und die Zahl ist greifbar" % k["was"]
                     if gut else "nein, %s ist gegen die Vorwoche gefallen, damit gibt niemand an"
                     % k["was"])
    return s


def messen_2(now):
    circ, _ = m_supply()
    bal = m_balance(EX_ADR)
    bew = m_entityx_bewegungen(7)
    return {"circ": circ, "bal": bal, "bewegungen": bew}


def ex_24h(w, now):
    grenze = (now - dt.timedelta(hours=24)).isoformat(timespec="seconds")
    return [b for b in w["bewegungen"] if b["zeit_utc"] >= grenze and abs(b["netto"]) >= EX_EREIGNIS]


def vorlage_2(w, now=None):
    now = now or jetzt_utc()
    anteil = 100 * w["bal"] / w["circ"]
    einer_in = w["circ"] / w["bal"]
    gross = [b for b in w["bewegungen"] if abs(b["netto"]) >= 100000]
    ereignis = ex_24h(w, now)
    zeilen = [{"num": kas(w["bal"]), "txt": "held by the largest known wallet", "frac": None},
              {"num": "1 in %d" % round(einer_in), "txt": "KAS in circulation sits in this wallet",
               "frac": None}]
    if ereignis:
        b = max(ereignis, key=lambda x: abs(x["netto"]))
        t = dt.datetime.fromisoformat(b["zeit_utc"])
        richtung = "left the entity x wallet" if b["netto"] < 0 else "came into the entity x wallet"
        s = {"kopf": "ENTITY X MOVED", "wert": kas(abs(b["netto"])),
             "label": "%s in one transaction, %s, %s" % (richtung, tag(t.date()), uhr(t)),
             "zeilen": zeilen,
             "satz": "the wallet now holds %.2f%% of everything in circulation" % anteil}
    else:
        if gross:
            b = gross[-1]
            t = dt.datetime.fromisoformat(b["zeit_utc"])
            satz = "last move %s KAS %s on %s" % (
                kurz(abs(b["netto"])), "left" if b["netto"] < 0 else "came in", tag_kurz(t.date()))
        else:
            satz = "no move above 100,000 KAS in the 7 days to %s" % tag_kurz(now.date())
        s = {"kopf": "ENTITY X", "wert": "%.2f%%" % anteil,
             "label": "of all KAS in circulation sits in one wallet, %s" % tag(now.date()),
             "zeilen": zeilen, "satz": satz}
    s["quelle"] = "sources kaspa rest api"
    s["x_neugier"] = "we check this wallet every day."
    s["pruefung"] = ("nein, eine Wallet-Bewegung wird geteilt, aber als Nachricht, nicht zum "
                     "Angeben. Die Form bleibt, weil Halter sie sehen wollen")
    return s


def messen_3(now):
    nod = reward_plan()
    cur, nxt, nxt_ts = nod.reward_state(now.timestamp())
    return {"cur": cur, "nxt": nxt, "nxt_ts": nxt_ts}


def cut_tage(w, now):
    return (w["nxt_ts"] - now.timestamp()) / 86400


def vorlage_3(w, now=None):
    now = now or jetzt_utc()
    nod = reward_plan()
    t = dt.datetime.fromtimestamp(w["nxt_ts"], dt.timezone.utc)
    tage = math.ceil(cut_tage(w, now))
    wert = "%d day%s" % (tage, "" if tage == 1 else "s")
    return {"kopf": "NEXT REWARD CUT", "wert": wert,
            "label": "until the block reward steps down, %s, %s" % (tag(t.date()), uhr(t)),
            "zeilen": [{"num": "%.2f KAS" % w["cur"], "txt": "per block today", "frac": 1.0},
                       {"num": "%.2f KAS" % w["nxt"], "txt": "per block after the cut",
                        "frac": w["nxt"] / w["cur"], "ton": "neu"}],
            "satz": "%s new KAS a day become %s, set in the code" % (
                kurz(nod.emission_per_day(w["cur"])), kurz(nod.emission_per_day(w["nxt"]))),
            "x_zeile": "%.2f KAS per block today, %.2f KAS after the cut" % (w["cur"], w["nxt"]),
            "quelle": "source kaspa emission schedule, anchored on the cut of 5 jul 2026",
            "x_neugier": "12 of these cuts make a halving.",
            "pruefung": "ja, knappe Terminzahl mit Datum, Halter teilen Countdowns gern"}


ALLTAG = [(8 * 3600, "WHILE YOU SLEPT", "in the 8 hours you slept"),
          (5 * 60, "SINCE YOUR COFFEE", "in the 5 minutes of your coffee"),
          (30 * 60, "YOUR LUNCH BREAK", "in a 30 minute lunch break"),
          (90 * 60, "ONE FOOTBALL MATCH", "in the 90 minutes of a football match")]


def messen_4(now):
    bps, daa = m_blockrate(60)
    tps = None
    try:
        r = m_kl_reihe("transactions/accepted/count", "Standard", "fluss")
        tage = [(now.date() - dt.timedelta(days=i)).isoformat() for i in range(1, 8)]
        if all(d in r for d in tage):
            tps = {"je_tag": sum(r[d] for d in tage) / 7, "bis": tage[0]}
    except Exception as exc:                        # noqa: BLE001
        print("form 4, transfers nicht belegt: %s" % exc)
    return {"bps": bps, "daa": daa, "tps": tps}


def vorlage_4(w, now=None, variante=0):
    now = now or jetzt_utc()
    sek, kopf, wann = ALLTAG[variante % len(ALLTAG)]
    bloecke = round(w["bps"] * sek, -3 if sek >= 3600 else -2)
    btc = sek / 600
    zeilen = [{"num": "%.1f" % w["bps"], "txt": "blocks every second, measured over 60 s", "frac": None},
              {"num": ("%.0f" % btc) if btc >= 1 else "%.1f" % btc,
               "txt": "blocks for bitcoin in the same time, at 1 block every 10 minutes", "frac": None}]
    satz = "every one of them confirmed on chain"
    tps = w.get("tps")
    if isinstance(tps, dict) and tps.get("je_tag"):
        satz = "about %s standard transfers a day, 7 days to %s" % (
            ganz(round(tps["je_tag"], -3)), tag(tps["bis"]))
    return {"kopf": kopf, "wert": ganz(bloecke),
            "label": "blocks added to kaspa %s, measured %s" % (wann, tag(now.date())),
            "zeilen": zeilen, "satz": satz,
            "quelle": "sources kaspa rest api block count, kaspalytics transfers",
            "x_neugier": "how many did your chain add?",
            "pruefung": "ja, riesige Zahl gegen eine Alltagsgroesse, genau der Angeber-Kontrast"}


def messen_5(now):
    """30 volle UTC-Tage bis gestern. Gebuehren und neue Coins fuer dieselben
    Tage; ein Tag ohne Gebuehrenwert faellt aus Zaehler UND Nenner."""
    bis = now.date() - dt.timedelta(days=1)
    tage = [(bis - dt.timedelta(days=i)).isoformat() for i in range(30)]
    fees = m_kl_reihe("transactions/accepted/fees/total", None, "fluss")
    hr = m_hashrate_tage()
    mit = [d for d in tage if d in fees and d in hr]
    if len(mit) < 25:
        raise Stop("nur %d von 30 tagen mit gebuehr und hashrate" % len(mit))
    f = sum(fees[d] for d in mit)
    e = sum(emission_am_tag(d) for d in mit)
    h = sum(hr[d] for d in mit) / len(mit)
    return {"tage": len(mit), "von": min(mit), "bis": max(mit), "fees": f, "emission": e,
            "th": h}


def vorlage_5(w, now=None):
    n = w["tage"]
    fx = w["emission"] / w["fees"]
    je_th = w["emission"] / n / w["th"]
    return {"kopf": "WHAT PAYS THE MINERS", "wert": "%sx" % ganz(fx),
            "label": "more KAS in new coins than in fees, %d days to %s" % (n, tag(w["bis"])),
            "zeilen": [{"num": kas(w["emission"] / n), "txt": "in new coins a day", "frac": 1.0},
                       {"num": kas(w["fees"] / n), "txt": "in fees a day",
                        "frac": max(w["fees"] / w["emission"], 0.004), "ton": "neu"}],
            "satz": "%.2f KAS a day for every TH/s of hashing power" % je_th,
            "quelle": "sources kaspalytics fees, kaspa emission schedule, kaspa rest api hashrate",
            "x_neugier": "the new coins shrink every month. the fees are the part that can grow.",
            "pruefung": "nein, die Zahl ist stark, aber fuer Halter erklaerungsbeduerftig. "
                        "Nerds teilen sie, der Durchschnitt nicht"}


def messen_6(now):
    w = {}
    try:
        b = hole(REST + "/blocks/%s?includeColor=false" % GENESIS)
        ts = int((b.get("header") or {}).get("timestamp") or 0)
        if ts:
            w["genesis_utc"] = dt.datetime.fromtimestamp(ts / 1000, dt.timezone.utc).isoformat()
    except Stop as exc:
        print("form 6, genesis nicht belegt: %s" % exc)
    try:
        d = hole(REST + "/info/blockdag")
        w["daa"] = int(d["virtualDaaScore"])
    except (Stop, KeyError, ValueError) as exc:
        print("form 6, daa nicht belegt: %s" % exc)
    try:
        h = m_kl_reihe("address/count/meaningful-balance", "Addresses", "bestand")
        tage = sorted(d for d in h if d < now.date().isoformat())
        w["holders_start"] = [tage[0], h[tage[0]]]
        w["holders_jetzt"] = [tage[-1], h[tage[-1]]]
    except Exception as exc:                        # noqa: BLE001
        print("form 6, holders nicht belegt: %s" % exc)
    if "daa" not in w and "holders_jetzt" not in w:
        raise Stop("kein fakt belegt")
    return w


def vorlage_6(w, now=None, variante=0):
    now = now or jetzt_utc()
    fakten = []
    if w.get("daa") and w.get("genesis_utc"):
        # Der Genesis-Block der API ist der Neustartpunkt vom 22.11.2021 und
        # traegt schon DAA-Score 1.312.860; die ersten Bloecke liefen ab
        # Anfang November 2021. Genannt wird deshalb der Monat, kein Tag.
        g = dt.datetime.fromisoformat(w["genesis_utc"])
        start = dt.datetime(2021, 11, 7, tzinfo=dt.timezone.utc)
        jahre = (now - start).days / 365.25
        fakten.append({"kopf": "FROM THE CHAIN", "wert": ("%.2fB" % (w["daa"] / 1e9)) if w["daa"] >= 1e9
                       else "%dM" % round(w["daa"] / 1e6),
                       "label": "blocks in kaspa's history, counted %s" % tag(now.date()),
                       "zeilen": [{"num": "nov 2021", "txt": "the first blocks", "frac": None},
                                  {"num": "%.1f years" % jahres_runden(jahre),
                                   "txt": "of blocks since then, without a premine", "frac": None}],
                       "satz": "counted by the network's daa score, every block public",
                       "x_zeile": "the first blocks came in nov 2021",
                       "quelle": "source kaspa rest api",
                       "x_neugier": "every one of them is public. count them yourself.",
                       "pruefung": "ja, Hunderte Millionen Bloecke und Jahre sind ein klarer Angeber-Fakt"})
        assert g.year == 2021
    if w.get("holders_start") and w.get("holders_jetzt"):
        (d0, v0), (d1, v1) = w["holders_start"], w["holders_jetzt"]
        fakten.append({"kopf": "FROM THE CHAIN", "wert": "%.1fx" % (v1 / v0),
                       "label": "more addresses with a meaningful balance than on %s" % tag(d0),
                       "zeilen": [{"num": ganz(v1), "txt": "on %s" % tag(d1), "frac": 1.0},
                                  {"num": ganz(v0), "txt": "on %s, where our series starts" % tag(d0),
                                   "frac": v0 / v1, "ton": "neu"}],
                       "satz": "a meaningful balance as kaspalytics counts it, no dust",
                       "x_zeile": "from %s on %s to %s on %s" % (ganz(v0), tag(d0), ganz(v1), tag(d1)),
                       "quelle": "source kaspalytics address counts",
                       "x_neugier": "where will the next line be?",
                       "pruefung": "ja, Wachstum ueber drei Jahre mit Startdatum, gut zum Angeben"})
    if not fakten:
        raise Stop("kein fakt fuer form 6")
    return fakten[variante % len(fakten)]


def jahres_runden(j):
    return math.floor(j * 10) / 10


def messen_7(now):
    """Von Hand: data/tagesgrafik-community.json, die erste Frage mit
    "offen": true. Ben liefert Frage, Antwort, Zahl, Namen und Messdatum."""
    try:
        d = json.loads(COMMUNITY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise Stop("keine community-datei")
    for e in d.get("fragen") or []:
        if e.get("offen"):
            return {"eintrag": e}
    raise Stop("keine offene community-frage")


def vorlage_7(w, now=None):
    e = w["eintrag"]
    return {"kopf": "YOU ASKED", "wert": e["zahl"],
            "label": "%s, %s" % (e["antwort"], tag(e["stand"])),
            "zeilen": [{"num": e["name"], "txt": "asked in #data-requests, %s" % e["frage"],
                        "frac": None}],
            "satz": e.get("satz") or "we counted it for you",
            "x_zeile": "asked by %s in #data-requests" % e["name"],
            "quelle": e.get("quelle") or "source named in the discord thread",
            "x_neugier": "ask the next one in our discord.",
            "pruefung": "ja, wer gefragt hat, teilt die Antwort mit seinem Namen darauf"}


def messen_8(now):
    ph = m_hashrate_phs()
    nod = reward_plan()
    cur, _, _ = nod.reward_state(now.timestamp())
    fee = None
    try:
        fees = m_kl_reihe("transactions/accepted/fees/total", None, "fluss")
        d = (now.date() - dt.timedelta(days=1)).isoformat()
        if d in fees:
            fee = [d, fees[d]]
    except Exception as exc:                        # noqa: BLE001
        print("form 8, gebuehren nicht belegt: %s" % exc)
    return {"ph": ph, "emission": nod.emission_per_day(cur), "fee": fee}


def vorlage_8(w, now=None):
    now = now or jetzt_utc()
    budget = w["emission"] + (w["fee"][1] if w.get("fee") else 0)
    return {"kopf": "SECURED BY WORK", "wert": "%.1f PH/s" % w["ph"],
            "label": "hashrate, measured %s" % tag(now.date()),
            "zeilen": [{"num": ganz(w["ph"]), "txt": "quadrillion hashes every second", "frac": None},
                       {"num": kas(budget), "txt": "paid to miners a day for that work", "frac": None}],
            "satz": "every block sealed by proof of work, around the clock",
            "quelle": "sources kaspa rest api hashrate, kaspa emission schedule%s" % (
                ", kaspalytics fees" if w.get("fee") else ""),
            "x_neugier": "that is the work behind every block.",
            "pruefung": "ja, Quadrillion pro Sekunde ist ein Angeber-Kontrast ohne Kursbezug"}


def messen_9(now):
    import address_thresholds_log as atl
    roh, probleme = atl.sammle(heute=now.date())
    tage = sorted(roh)
    if not tage:
        raise Stop("keine schwellen: %s" % probleme)
    d1 = tage[-1]
    d0 = (d1 - dt.timedelta(days=7))
    if d0 not in roh:
        raise Stop("kein wert 7 tage vor %s" % d1)
    return {"d1": d1.isoformat(), "d0": d0.isoformat(),
            "jetzt": roh[d1], "vorher": roh[d0]}


def vorlage_9(w, now=None):
    j, v = w["jetzt"], w["vorher"]
    plus = j["holders_100kas"] - v["holders_100kas"]
    satz = ("one more address above 100 KAS every %d minutes" % round(7 * 24 * 60 / plus)
            if plus > 0 else "%s addresses above 100 KAS in 7 days" % ganz(plus))
    return {"kopf": "ADDRESSES", "wert": ganz(j["holders_100kas"]),
            "label": "addresses hold at least 100 KAS, %s" % tag(w["d1"]),
            "zeilen": [{"num": "%+d" % plus, "txt": "in 7 days, since %s" % tag_kurz(w["d0"]),
                        "frac": None},
                       {"num": ganz(j["holders_1kas"]), "txt": "addresses hold at least 1 KAS",
                        "frac": None}],
            "satz": satz,
            "quelle": "source kaspalytics address thresholds",
            "x_neugier": "which side of 100 are you on?",
            "pruefung": ("ja, die Schwelle waechst, und jeder kann sich darin wiederfinden"
                         if plus > 0 else "nein, die Zahl ist in dieser Woche gefallen")}


def messen_10(now):
    circ, mx = m_supply()
    w = {"circ": circ, "max": mx}
    try:
        b = hole(REST + "/blocks/%s?includeColor=false" % GENESIS)
        ts = int((b.get("header") or {}).get("timestamp") or 0)
        if ts:
            w["genesis_utc"] = dt.datetime.fromtimestamp(ts / 1000, dt.timezone.utc).isoformat()
    except Stop:
        pass
    return w


def vorlage_10(w, now=None):
    now = now or jetzt_utc()
    pct = 100 * w["circ"] / w["max"]
    # Monat statt Tag, siehe vorlage_6 (Genesis der API ist der Neustart).
    seit = "since the first blocks in nov 2021"
    return {"kopf": "NO PREMINE", "wert": "%.2f%%" % pct,
            "label": "of all KAS that will ever exist is mined, %s" % tag(now.date()),
            "zeilen": [{"num": "0", "txt": "KAS premined, presold or set aside for developers",
                        "frac": None},
                       {"num": kurz(w["max"]), "txt": "KAS maximum, set in the code", "frac": None}],
            "satz": "every coin came from proof of work %s" % seit,
            "quelle": "source kaspa rest api coin supply",
            "x_neugier": "no one got coins without doing the work.",
            "pruefung": "ja, fairer Start ist der Stolz der Community, und die Zahl belegt ihn"}


def messen_11(now):
    raise Stop("form 11 ist gesperrt, bis die tagesreihe der nodes beschlossen ist")


def vorlage_11(w, now=None):
    return {"kopf": "NODES", "wert": ganz(w["nodes"]),
            "label": "reachable over IPv4, counted by us, %s" % tag(w["stand"]),
            "zeilen": [], "satz": "reachable from outside with a mainnet handshake",
            "quelle": "source our own node count", "x_neugier": "is yours one of them?",
            "pruefung": "offen, erst nach Bens Beschluss"}


FORMEN = {
    1: ("wochenzahl", messen_1, vorlage_1),
    2: ("entity x", messen_2, vorlage_2),
    3: ("countdown", messen_3, vorlage_3),
    4: ("massstab", messen_4, vorlage_4),
    5: ("miner-oekonomie", messen_5, vorlage_5),
    6: ("aus der kette", messen_6, vorlage_6),
    7: ("community", messen_7, vorlage_7),
    8: ("sicherheit", messen_8, vorlage_8),
    9: ("adressen", messen_9, vorlage_9),
    10: ("herkunft", messen_10, vorlage_10),
    11: ("nodes", messen_11, vorlage_11),
}


# ------------------------------------------------------------ textpruefung

WORTLISTE = ("sold", "sell", "sells", "selling", "sale", "bought", "buy", "buys", "buying",
             "purchase", "purchased", "dump", "dumping", "whale", "whales", "because",
             "motive", "panic", "exit", "cash out", "profit", "wants", "intends", "plans",
             "preparing", "moon", "pump", "bullish", "bearish", "target", "to the moon")
ANGRIFF = ("attack", "attacker", "attackers", "51", "hack", "hacked", "rent", "rented",
           "break the chain", "double spend", "double-spend", "take over", "overpower")
ZAHLWORTE = ("two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
             "eleven", "twelve", "twenty", "thirty", "forty", "fifty", "hundred",
             "thousand", "million", "billion")
ZEITRAUM = re.compile(r"since \d{1,2} [a-z]{3}|since (19|20)\d\d|since the first block|since [a-z]{3} (19|20)\d\d|"
                      r"in the \d+ (days|weeks|months)|in \d+ (days|weeks|months)|"
                      r"\d+ days to|where our series starts|in our (log|series) since", re.I)
DATUM = re.compile(r"\b\d{1,2} (jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b")
FUSS = re.compile(r"as of \d{1,2} (jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec) "
                  r"\d{4}, \d\d:\d\d utc")
ERLAUBTE_DOMAIN = {"gate.io"}


def pruefe_eine(t, form=None, feld=""):
    fehler = []
    ohne = re.sub(r"\b\d{1,2}:\d{2}\b", "", t)
    for z, name in ((":", "doppelpunkt"), ("\u2014", "gedankenstrich"), ("\u2013", "gedankenstrich"),
                    (" - ", "bindestrich als satzzeichen"), ("\u2192", "pfeil"), ("->", "pfeil"),
                    ("=>", "pfeil")):
        if z in ohne:
            fehler.append("%s in %s" % (name, feld))
    for m in re.finditer(r"\b[\w-]+\.(com|org|io|net|stream|xyz|app|dev|de|fyi)\b", t, re.I):
        if m.group(0).lower() not in ERLAUBTE_DOMAIN:
            fehler.append("domain %r in %s" % (m.group(0), feld))
    if re.search(r"https?://|www\.|kaspapulse", t, re.I):
        fehler.append("link in %s" % feld)
    klein = " %s " % re.sub(r"[^a-z0-9 ]", " ", t.lower())
    for w in WORTLISTE:
        if " %s " % w in klein:
            fehler.append("wortliste %r in %s" % (w, feld))
    if "percent" in klein:
        fehler.append("'percent' statt %% in %s" % feld)
    for w in ZAHLWORTE:
        if " %s " % w in klein:
            fehler.append("zahlwort %r in %s" % (w, feld))
    if "$" in t or re.search(r"\b(usd|usdt|dollars?|price)\b", t, re.I):
        fehler.append("kurs- oder dollarangabe in %s" % feld)
    if form == 8:
        for w in ANGRIFF:
            if " %s " % w in klein:
                fehler.append("angriffsszenario %r in %s" % (w, feld))
    for w in ("never", "record", "highest", "lowest", "all time", "ever seen"):
        if " %s " % w in klein and not ZEITRAUM.search(t):
            fehler.append("%r ohne zeitraum in %s" % (w, feld))
    return fehler


def textpruefung(s, form):
    """Alle Regeln aus Bens Auftrag. Gibt die Fehlerliste zurueck, leer heisst
    gruen. Die Grafik wird nur gerendert, wenn die Liste leer ist."""
    fehler = []
    felder = {"kopf": s["kopf"], "wert": s["wert"], "label": s["label"], "satz": s["satz"],
              "fuss": s["fuss"], "x": s["x"], "discord": s["discord"]}
    for i, z in enumerate(s["zeilen"]):
        felder["zeile%d" % i] = "%s %s" % (z["num"], z["txt"])
    for k, v in felder.items():
        fehler += pruefe_eine(v, form, k)
    inhalt = " ".join([s["label"], s["satz"]] + [z["txt"] + " " + z["num"] for z in s["zeilen"]])
    if not DATUM.search(inhalt):
        fehler.append("kein datum im inhalt, jede zahl muss datiert sein")
    if not FUSS.search(s["fuss"]):
        fehler.append("fusszeile ohne messzeit 'as of <tag>, <hh:mm> utc'")
    if not DATUM.search(s["x"]):
        fehler.append("x-text ohne datum")
    if len(s["x"]) >= 240:
        fehler.append("x-text hat %d zeichen, erlaubt sind unter 240" % len(s["x"]))
    if "it goes on x at %s" % X_ZEIT not in s["discord"]:
        fehler.append("discord-text ohne 'it goes on x at %s'" % X_ZEIT)
    if not re.match(r"(ja|nein|offen), ", s.get("pruefung", "")):
        fehler.append("selbstpruefung beginnt nicht mit ja oder nein")
    if form == 2 and re.search(r"\$|usd|worth", " ".join(felder.values()), re.I):
        fehler.append("form 2 nennt einen dollarwert")
    return fehler


# ------------------------------------------------------------ texte

def texte(s, form, messzeit):
    s = dict(s)
    s["fuss"] = "counted on chain \u00b7 %s \u00b7 as of %s, %s" % (
        s.pop("quelle"), tag(messzeit.date()), uhr(messzeit))
    satz_x = "%s %s." % (s["wert"], s["label"])
    s["x"] = "%s\n\n%s" % (satz_x, s["x_neugier"])
    zweite = s.pop("x_zeile", None)
    if not zweite and s["zeilen"]:
        zweite = "%s %s" % (s["zeilen"][0]["num"], s["zeilen"][0]["txt"])
    if zweite:
        mit = "%s\n%s.\n\n%s" % (satz_x, zweite.rstrip(".?!"), s["x_neugier"])
        if len(mit) < 240:
            s["x"] = mit
    kontrast = "; ".join("%s %s" % (z["num"], z["txt"]) for z in s["zeilen"][:2])
    s["discord"] = ("%s\n%s. %s.\n\nshare it first, it goes on x at %s."
                    % (satz_x, kontrast, s["satz"], X_ZEIT))
    return s


# ------------------------------------------------------------ rendern

CSS = """
:root{--bg:#080B0F;--line:#1C242D;--teal:#49EACB;--txt:#FFFFFF;--dim:#A7B0B9;--dimmer:#8C97A2}
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1350px;background:var(--bg);color:var(--txt);
  font-family:'Helvetica Neue',Helvetica,Arial,'Liberation Sans',sans-serif;
  padding:34px 52px 26px;display:flex;flex-direction:column;-webkit-font-smoothing:antialiased}
.top{display:flex;align-items:center;gap:16px;border-bottom:2px solid var(--line);padding-bottom:12px;flex:none}
.falc{width:48px;height:auto;display:block}
.brand{font-size:40px;letter-spacing:6px;font-weight:700}
.brand span{color:var(--teal)}
h1{font-size:78px;line-height:1.04;letter-spacing:-1.5px;margin-top:18px;font-weight:700;flex:none}
.value{font-weight:700;letter-spacing:-6px;line-height:0.9;margin-top:14px;flex:none;white-space:nowrap}
.vlabel{font-size:56px;line-height:1.14;color:var(--dim);margin-top:8px;flex:none}
.blocks{display:flex;flex-direction:column;gap:26px;margin-top:34px;flex:none}
.blk .num{font-size:86px;font-weight:700;letter-spacing:-3px;line-height:1}
.blk .track{height:30px;background:#141B22;border-radius:6px;margin-top:14px;overflow:hidden}
.blk .fill{height:100%;background:var(--teal);border-radius:6px}
.blk.neu .fill{background:#E8ECEF}
.blk .txt{font-size:46px;line-height:1.18;color:var(--dim);margin-top:10px}
.body{font-size:46px;line-height:1.2;margin-top:34px;flex:none}
.foot{margin-top:auto;padding-top:12px;flex:none;border-top:2px solid var(--line);
  display:flex;flex-direction:column;align-items:flex-start;gap:12px}
.foot .src{font-size:32px;line-height:1.35;color:var(--dimmer)}
.foot .mark{display:flex;align-items:center;gap:10px;flex:none}
.foot .falc{width:40px}
.foot .brand{font-size:30px;letter-spacing:4px}
"""


def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace(" utc", "\u00a0utc"))


def wertgroesse(wert):
    n = len(wert)
    return 190 if n <= 7 else 168 if n <= 9 else 140 if n <= 12 else 116


def html(s, falke):
    marke = ('<img class="falc" src="%s" alt=""><div class="brand">KASPA <span>PULSE</span></div>'
             % falke)
    bl = []
    for z in s["zeilen"]:
        spur = ""
        if z.get("frac") is not None:
            spur = ("<div class='track'><div class='fill' style='width:%.2f%%'></div></div>"
                    % (100 * max(0.0, min(1.0, z["frac"]))))
        bl.append("<div class='blk %s'><div class='num'>%s</div>%s<div class='txt'>%s</div></div>"
                  % (z.get("ton", ""), esc(z["num"]), spur, esc(z["txt"])))
    return ("<!DOCTYPE html><html><head><meta charset='UTF-8'><style>%s</style></head><body>"
            "<div class='top'>%s</div><h1>%s</h1>"
            "<div class='value' style='font-size:%dpx'>%s</div><div class='vlabel'>%s</div>"
            "<div class='blocks'>%s</div><div class='body'>%s</div>"
            "<div class='foot'><div class='src'>%s</div><div class='mark'>%s</div></div>"
            "</body></html>") % (CSS, marke, esc(s["kopf"]), wertgroesse(s["wert"]), esc(s["wert"]),
                                 esc(s["label"]), "".join(bl), esc(s["satz"]), esc(s["fuss"]), marke)


def rendern(seite, out, vorschau=VORSCHAU):
    from playwright.sync_api import sync_playwright
    launch = {}
    for c in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
              "/opt/pw-browsers/chromium/chrome-linux/chrome"):
        if os.path.exists(c):
            launch["executable_path"] = c
            break
    out = Path(out)
    tmp = out.with_suffix(".html")
    tmp.write_text(seite, encoding="utf-8")
    vpfad = out.with_name(out.stem + "-vorschau-%d.png" % vorschau)
    with sync_playwright() as p:
        b = p.chromium.launch(**launch)
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        pg.goto(tmp.resolve().as_uri())
        pg.wait_for_timeout(400)
        ueber = pg.evaluate("Math.max(0, document.body.scrollHeight - %d)" % H)
        breit = pg.evaluate("Math.max(0, document.body.scrollWidth - %d)" % W)
        if ueber or breit:
            b.close()
            raise Stop("inhalt ist %d px zu hoch und %d px zu breit, text kuerzen" % (ueber, breit))
        pg.screenshot(path=str(out))
        v = b.new_page(viewport={"width": vorschau, "height": round(vorschau * H / W)},
                       device_scale_factor=1)
        v.set_content("<html><body style='margin:0;background:#000'><img src='data:image/png;base64,%s'"
                      " style='width:%dpx;display:block'></body></html>"
                      % (base64.b64encode(out.read_bytes()).decode(), vorschau))
        v.wait_for_timeout(200)
        v.screenshot(path=str(vpfad))
        b.close()
    tmp.unlink()
    return out, vpfad


# ------------------------------------------------------------ rotation

def lade_log():
    try:
        return json.loads(LOG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"laeufe": []}


def waehle_form(heute, log, ereignis_cut=False, ereignis_ex=False, verfuegbar=None):
    """Gibt (form, grund) zurueck. heute ist ein date in Berlin."""
    verfuegbar = set(verfuegbar or FREIGESCHALTET)
    if ereignis_cut and 3 in verfuegbar:
        return 3, "reward-senkung in hoechstens %d tagen" % CUT_EREIGNIS_TAGE
    if ereignis_ex and 2 in verfuegbar:
        return 2, "entity-x-bewegung ab %s KAS in 24 h" % ganz(EX_EREIGNIS)
    if heute.weekday() == 0 and 1 in verfuegbar:
        return 1, "montag"
    woche = heute.isocalendar()[:2]
    laeufe = [(dt.date.fromisoformat(e["datum"]), e["form"]) for e in log.get("laeufe", [])]
    diese_woche = {f for d, f in laeufe if d.isocalendar()[:2] == woche and d < heute}
    kand = [f for f in sorted(verfuegbar) if f != 1 and f not in diese_woche]
    if not kand:
        kand = [f for f in sorted(verfuegbar) if f != 1]
    monat = heute - dt.timedelta(days=30)

    def rang(f):
        n = sum(1 for d, g in laeufe if g == f and monat <= d < heute)
        letzte = max([d for d, g in laeufe if g == f and d < heute], default=dt.date(2000, 1, 1))
        return (n, letzte, f)
    f = min(kand, key=rang)
    return f, "rotation, %d laeufe in 30 tagen" % rang(f)[0]


def variante(log, form):
    return sum(1 for e in log.get("laeufe", []) if e["form"] == form)


# ------------------------------------------------------------ ops

def ops_senden(png, vorschau, s, form, grund, hook):
    inhalt = ("tagesgrafik %s, form %d %s (%s)\nnicht oeffentlich. discord 09:00, x %s.\n\n"
              "DISCORD\n```\n%s\n```\nX, %d zeichen\n```\n%s\n```\nselbstpruefung, wuerde ein halter "
              "das reposten, um anzugeben? %s" % (
                  s["datum"], form, FORMEN[form][0], grund, X_ZEIT, s["discord"], len(s["x"]),
                  s["x"], s["pruefung"]))
    if len(inhalt) > 1990:
        inhalt = inhalt[:1990]
    grenze = "----tg" + uuid.uuid4().hex
    teile = []

    def feld(name, wert, dateiname=None, typ=None):
        kopf = 'Content-Disposition: form-data; name="%s"' % name
        if dateiname:
            kopf += '; filename="%s"' % dateiname
        teile.append(("--%s\r\n%s\r\n%s\r\n" % (grenze, kopf,
                      "Content-Type: %s\r\n" % typ if typ else "")).encode() + wert + b"\r\n")
    feld("payload_json", json.dumps({"content": inhalt, "allowed_mentions": {"parse": []}}).encode(),
         typ="application/json")
    feld("files[0]", Path(png).read_bytes(), Path(png).name, "image/png")
    feld("files[1]", Path(vorschau).read_bytes(), Path(vorschau).name, "image/png")
    body = b"".join(teile) + ("--%s--\r\n" % grenze).encode()
    req = urllib.request.Request(hook, data=body, headers={
        "Content-Type": "multipart/form-data; boundary=%s" % grenze, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        print("an ops geschickt, http %s" % r.status)


# ------------------------------------------------------------ ablauf

def seite_bauen(form, werte, messzeit, log):
    _, _, vorlage = FORMEN[form]
    now = messzeit
    if form in (4, 6):
        s = vorlage(werte, now, variante(log, form))
    elif form == 1:
        s = vorlage(werte)
    else:
        s = vorlage(werte, now)
    s = texte(s, form, messzeit)
    s["datum"] = tag(messzeit.date())
    fehler = textpruefung(s, form)
    if fehler:
        raise Stop("textpruefung form %d, %s" % (form, "; ".join(fehler)))
    return s


def messen(form, now):
    _, m, _ = FORMEN[form]
    werte = m(now)
    return {"form": form, "messzeit_utc": now.isoformat(timespec="seconds"), "werte": werte}


def falke_lesen(pfad=None):
    for p in [pfad, FALKE, Path.home() / "pulse-studio" / "kp" / "falcon.b64"]:
        if p and Path(p).exists():
            return Path(p).read_text().strip()
    raise Stop("falke fehlt (graphics/falcon.b64)")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="graphics/tagesgrafik")
    ap.add_argument("--form", type=int)
    ap.add_argument("--messen", action="store_true", help="nur messen, json auf stdout")
    ap.add_argument("--aus", help="aus einer gespeicherten messung rendern")
    ap.add_argument("--senden", action="store_true", help="an DISCORD_WEBHOOK_OPS schicken")
    ap.add_argument("--zeitplan", action="store_true",
                    help="geplanter lauf, nur ab 07:00 Berlin und einmal am tag")
    ap.add_argument("--log-schreiben", action="store_true")
    ap.add_argument("--falke")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selbsttest()

    log = lade_log()
    b = berlin_jetzt()
    heute = b.date()
    if a.zeitplan:
        if b.hour < 7 or b.hour >= 12:
            print("geplanter lauf um %s Berlin, geliefert wird zwischen 07:00 und 12:00. nichts zu tun"
                  % b.strftime("%H:%M"))
            return 0
        if any(e["datum"] == heute.isoformat() for e in log.get("laeufe", [])):
            print("heute (%s) schon geliefert, nichts zu tun" % heute)
            return 0

    if a.aus:
        m = json.loads(Path(a.aus).read_text(encoding="utf-8"))
        form, grund = m["form"], m.get("grund", "aus gespeicherter messung")
        messzeit = dt.datetime.fromisoformat(m["messzeit_utc"])
    else:
        now = jetzt_utc()
        if a.form:
            form, grund = a.form, "von hand"
            if form not in FREIGESCHALTET and not a.messen:
                raise SystemExit("form %d ist nicht freigeschaltet" % form)
            m = messen(form, now)
        else:
            cut = messen_3(now)
            ereignis_cut = cut_tage(cut, now) <= CUT_EREIGNIS_TAGE
            ereignis_ex = False
            try:
                ereignis_ex = bool(ex_24h({"bewegungen": m_entityx_bewegungen(2)}, now))
            except Stop as exc:
                print("entity-x-pruefung fuer die rotation fehlgeschlagen: %s" % exc)
            ausgeschl, m = set(), None
            while m is None:
                verf = FREIGESCHALTET - ausgeschl
                if not verf:
                    raise SystemExit("ABBRUCH keine form heute belegbar")
                form, grund = waehle_form(heute, log, ereignis_cut, ereignis_ex, verf)
                try:
                    m = messen(form, now)
                except Stop as exc:
                    print("form %d faellt heute aus: %s" % (form, exc))
                    ausgeschl.add(form)
        m["grund"] = grund
        messzeit = dt.datetime.fromisoformat(m["messzeit_utc"])
        if a.messen:
            print(json.dumps(m, ensure_ascii=False))
            return 0

    s = seite_bauen(form, m["werte"], messzeit, log)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    png, vpng = rendern(html(s, falke_lesen(a.falke)),
                        out / ("tagesgrafik-%s-form%02d.png" % (messzeit.date().isoformat(), form)))
    (out / (png.stem + ".txt")).write_text(
        "DISCORD\n%s\n\nX (%d zeichen)\n%s\n\nSELBSTPRUEFUNG\nwuerde ein halter das reposten, um "
        "anzugeben? %s\n" % (s["discord"], len(s["x"]), s["x"], s["pruefung"]), encoding="utf-8")
    (out / (png.stem + ".json")).write_text(json.dumps(m, ensure_ascii=False, indent=1),
                                            encoding="utf-8")
    print("form %d (%s), %s\n%s\n%s" % (form, grund, png, vpng, (out / (png.stem + ".txt")).read_text()))
    if a.senden:
        hook = os.environ.get("DISCORD_WEBHOOK_OPS", "")
        if not hook:
            raise SystemExit("ABBRUCH kein DISCORD_WEBHOOK_OPS, nichts geschickt")
        ops_senden(png, vpng, s, form, grund, hook)
    if a.log_schreiben:
        log.setdefault("laeufe", []).append({"datum": heute.isoformat(), "form": form,
                                             "grund": grund, "messzeit_utc": m["messzeit_utc"]})
        LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


# ------------------------------------------------------------ selbsttest

FAKE_NOW = dt.datetime(2026, 9, 29, 5, 31, tzinfo=dt.timezone.utc)
FAKE = {
    1: {"kandidaten": [{"was": "holders", "jetzt": 799128, "vorher": 796711,
                        "d1": "2026-09-27", "d0": "2026-09-20"},
                       {"was": "hashrate", "jetzt": 347.5, "vorher": 351.0,
                        "d1": "2026-09-28", "d0": "2026-09-21"}]},
    2: {"circ": 27727376907.35, "bal": 1519597995.47,
        "bewegungen": [{"zeit_utc": "2026-09-28T12:26:15+00:00", "tx": "65f1", "netto": -6377600.99}]},
    3: {"cur": 2.18268, "nxt": 2.06023, "nxt_ts": 1791170144},
    4: {"bps": 10.0, "daa": 400000000, "tps": {"je_tag": 103680, "bis": "2026-09-28"}},
    5: {"tage": 30, "von": "2026-08-30", "bis": "2026-09-28", "fees": 76500.0,
        "emission": 57075000.0, "th": 332737.3},
    6: {"genesis_utc": "2021-11-07T00:00:00+00:00", "daa": 400000000,
        "holders_start": ["2023-08-27", 279609], "holders_jetzt": ["2026-09-27", 799128]},
    7: {"eintrag": {"frage": "how many addresses hold at least 100 KAS?", "zahl": "293,458",
                    "antwort": "addresses held at least 100 KAS", "name": "PLATZHALTER",
                    "stand": "2026-09-27", "offen": True}},
    8: {"ph": 347.5, "emission": 1885832.45, "fee": ["2026-09-28", 2549.79]},
    9: {"d1": "2026-09-27", "d0": "2026-09-20",
        "jetzt": {"holders_100kas": 293458, "holders_1kas": 558691},
        "vorher": {"holders_100kas": 293153, "holders_1kas": 557000}},
    10: {"circ": 27727376907.35, "max": 28704026601.0, "genesis_utc": "2021-11-07T00:00:00+00:00"},
}


def selbsttest():
    fehler = 0

    def ok(name, bed):
        nonlocal fehler
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        fehler += 0 if bed else 1

    log = {"laeufe": []}
    for f in sorted(FAKE):
        try:
            s = seite_bauen(f, FAKE[f], FAKE_NOW, log)
            ok("form %d vorlage und textpruefung gruen" % f, True)
            ok("form %d x-text unter 240 (%d)" % (f, len(s["x"])), len(s["x"]) < 240)
        except Stop as exc:
            ok("form %d, %s" % (f, exc), False)
    # die regeln selbst
    probe = lambda t, form=None: pruefe_eine(t, form, "probe")    # noqa: E731
    ok("wortliste sold", bool(probe("entity x sold coins")))
    ok("wortliste bought", bool(probe("the wallet bought more")))
    ok("wortliste whale", bool(probe("a whale moved")))
    ok("pfeil", bool(probe("2.18 \u2192 2.06")))
    ok("doppelpunkt", bool(probe("reward: 2.18")))
    ok("uhrzeit erlaubt", not probe("as of 29 sep 2026, 07:31 utc"))
    ok("domain", bool(probe("see kaspapulse.com")))
    ok("gate.io als label erlaubt", not probe("passed on to a gate.io labelled address"))
    ok("percent", bool(probe("30 percent above")))
    ok("zahlwort", bool(probe("twelve cuts a year")))
    ok("dollar", bool(probe("worth $50M")))
    ok("never ohne zeitraum", bool(probe("never this high")))
    ok("never mit zeitraum", not probe("the highest in our log since 13 aug 2026"))
    ok("record ohne zeitraum", bool(probe("a new record")))
    ok("angriff in form 8", bool(probe("an attacker would need 51 of the hashrate", 8)))
    s = seite_bauen(2, FAKE[2], FAKE_NOW, log)
    ok("form 2 ereignis bei 6.38M in 24 h", s["kopf"] == "ENTITY X MOVED")
    ok("form 2 ohne dollar", "$" not in json.dumps(s))
    # rotation
    mo = dt.date(2026, 10, 5)
    ok("montag gibt form 1", waehle_form(mo, log)[0] == 1)
    ok("reward-senkung schlaegt montag", waehle_form(mo, log, ereignis_cut=True)[0] == 3)
    ok("entity x schlaegt montag", waehle_form(mo, log, ereignis_ex=True)[0] == 2)
    di = dt.date(2026, 10, 6)
    log2 = {"laeufe": [{"datum": "2026-10-05", "form": 1}, {"datum": "2026-10-02", "form": 2}]}
    f, _ = waehle_form(di, log2)
    ok("rotation nimmt keine form 1 am dienstag", f != 1)
    woche = {"laeufe": [{"datum": "2026-10-0%d" % (5 + i), "form": g} for i, g in enumerate((1, 2, 3, 4))]}
    f, _ = waehle_form(dt.date(2026, 10, 9), woche)
    ok("keine form zweimal in derselben woche", f not in (2, 3, 4))
    gezaehlt = {}
    lg = {"laeufe": []}
    d = dt.date(2026, 10, 1)
    for _ in range(90):
        f, _ = waehle_form(d, lg, verfuegbar=FREIGESCHALTET - {7})
        lg["laeufe"].append({"datum": d.isoformat(), "form": f})
        gezaehlt[f] = gezaehlt.get(f, 0) + 1
        d += dt.timedelta(days=1)
    pro_monat = {f: n / 3 for f, n in gezaehlt.items()}
    ok("90 tage, jede form etwa dreimal im monat %s" % {f: round(v, 1) for f, v in sorted(pro_monat.items())},
       all(2 <= v <= 5 for v in pro_monat.values()))
    doppelt = False
    for e in lg["laeufe"]:
        dd = dt.date.fromisoformat(e["datum"])
        gleich = [x for x in lg["laeufe"] if x["form"] == e["form"] and x["form"] != 1
                  and dt.date.fromisoformat(x["datum"]).isocalendar()[:2] == dd.isocalendar()[:2]]
        doppelt |= len(gleich) > 1
    ok("90 tage ohne doppelte form in einer woche", not doppelt)
    ok("form 11 gesperrt", 11 not in FREIGESCHALTET)
    # zeitplan-sperre, ohne netz: vor 07:00 Berlin und nach einer lieferung
    alt = os.environ.get("TG_JETZT")
    os.environ["TG_JETZT"] = "2026-10-01T06:30:00+02:00"
    ok("zeitplan vor 07:00 Berlin liefert nicht", main(["--zeitplan", "--out", "/tmp"]) == 0)
    global LOG
    alt_log, LOG = LOG, Path("/tmp/tagesgrafik-selbsttest-log.json")
    LOG.write_text(json.dumps({"laeufe": [{"datum": "2026-10-01", "form": 4}]}))
    os.environ["TG_JETZT"] = "2026-10-01T08:30:00+02:00"
    ok("zweiter termin am selben tag liefert nicht", main(["--zeitplan", "--out", "/tmp"]) == 0)
    LOG.unlink()
    LOG = alt_log
    if alt is None:
        os.environ.pop("TG_JETZT", None)
    else:
        os.environ["TG_JETZT"] = alt
    ok("selbstpruefung muss mit ja oder nein beginnen",
       any("selbstpruefung" in f for f in textpruefung(dict(seite_bauen(3, FAKE[3], FAKE_NOW, log),
                                                             pruefung="vielleicht"), 3)))
    ok("emission am tag mit senkung geteilt",
       abs(emission_am_tag("2026-10-05") - (2.18268 * 10 * 11744 + 2.06023 * 10 * (86400 - 11744)))
       < 20000)
    print("%d fehler" % fehler)
    return 1 if fehler else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stop as exc:
        print("ABBRUCH %s" % exc)
        sys.exit(1)
