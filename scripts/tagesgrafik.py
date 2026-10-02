#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tagesgrafik.py, eine Grafik pro Tag fuer X und Discord.

ZWECK (Ben, 29.09.2026). Eine Grafik, die ein Kaspa-Halter teilt, um damit
anzugeben. Hype ueber Fakten, nie ueber den Kurs. Jede Grafik hat drei
Zutaten: eine Zahl, die stolz macht, einen Kontrast, der sie sofort
verstaendlich macht, und eine Zeile Absender.

HAUSNORM SEIT 29.09.2026 (Ben, Richtung C). Die Zahl ist das Bild: jede Form
hat genau ein Objekt, das die Daten selbst IST und ohne Lesen verstanden
wird. Der Rahmen ist bei allen gleich, nur das Objekt wechselt: Kopfzeile
oben links, die eine Zahl, das Objekt, eine Bedeutungszeile, eine kleine
Datumszeile mit Messzeit und Herkunft, unten die Signatur (Falke, KASPA
PULSE, Pulslinie mit einer EKG-Zacke in #49EACB). Das Logo steht nur unten.
Hoechstens vier Texte. Farben #080B0F, Akzent #49EACB, dritter Ton #2B7A6C
fuer den Rest der Daten, Weiss nur fuer Kopf und Zahl. Keine Verlaeufe, kein
Glow, keine Rahmen, Balken ab null. Hausschrift wie number_of_day.py
(Liberation Sans auf dem Runner). 1080x1350, Vorschau 390 px.

ELF FORMEN, jede mit eigener Vorlage (FORMEN unten) und eigener Messung:

   1  Wochenzahl        montags fest. Adressen mit nennenswertem Guthaben
                        oder Hashrate gegen die Vorwoche, im Lauf gemessen
                        (week-input.json steht um 07:30 noch auf der Vorwoche)
   2  Entity X          Anteil am Umlauf plus letzte Bewegung, von der Kette
   3  Countdown         Tage bis zur naechsten Reward-Senkung, Anker-Arithmetik
   4  Massstab          Bloecke waehrend 8 Stunden Schlaf, je Herzschlag, aus der
                        einen im Lauf gemessenen Blockrate
   5  Miner-Oekonomie   neue Coins gegen Gebuehren, dieselben 30 Tage
   6  Aus der Kette     ein Fakt aus der Historie
   7  Community         Frage aus #data-requests, von Hand
                        (data/tagesgrafik-community.json)
   8  Sicherheit        Hashrate und Sicherheitsbudget, nie ein Angriff
   9  Adressen          Adressen ueber Schwellen mit Wochenbewegung
  10  Herkunft          kein Premine, kein Presale, kein Dev-Fund, gemint-Anteil
  11  Schlafende Coins  Anteil des Umlaufs, der seit 1 Jahr unbewegt ist, darin
                        seit 2 Jahren (Kaspalytics supply/inactive, Ben 30.09.2026)
  12  Boersen           geparkt, kein Code, bis die Boersensumme geklaert ist
                        (Kaspalytics 3.78B gegen unsere Labels 6.1B, docs/pruefung)
  13  Nodes             vorbereitet, gesperrt bis die Tagesreihe beschlossen ist

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
  die Datumszeile beginnt mit "<tag> <mon> <jahr>, <hh:mm> utc" und endet auf
  "counted by kaspa pulse" (nur eigene Zaehlung) oder "source ..." allein
  "%" statt "percent", Ziffern statt Zahlwoertern
  kein Doppelpunkt ausser in Uhrzeiten, kein Gedankenstrich, kein Pfeil
  keine Domain, kein Link (einzige Ausnahme ist das Explorer-Label gate.io)
  kein Kursziel, kein Dollar- oder Kurswert
  Wortliste: sold, buy, bought, purchase, dump, whale, because, motive ...
  Echtzeit-Woerter: around the clock, real time, every minute, instantly, live ...
  kein Vergleich mit einer anderen Chain (bitcoin, ethereum ...), nie
  "neue KAS" nur aus neue_kas(), immer mit Fenster
  Form 8 ohne Angreifer-Szenario (attack, 51, attacker ...)
  kein "never" und kein "record", "highest", "lowest" ohne Zeitraum
  X-Text in drei Zeilen, ohne Link, unter 240 Zeichen: Zeile 1 ohne
  Dezimalstelle, Zeile 3 eine Frage. Der Link steht nur im Feld antwort
  (utm_source=x, utm_medium=reply, utm_campaign=form<N>).

ROTATION (waehle_form()). Ereignis schlaegt Plan: Reward-Senkung in hoechstens
3 Tagen gibt Form 3, eine Entity-X-Bewegung ab 500.000 KAS in den letzten
24 Stunden Form 2, Montag Form 1. Sonst die Form, die in dieser Woche noch
nicht lief und in den letzten 30 Tagen am seltensten, bei Gleichstand die,
deren letzter Lauf am laengsten her ist. data/tagesgrafik-log.json haelt,
welche Form wann lief.

KOLLISION MIT DER ZAHL DES TAGES (v5, 30.09.2026). Vor der Wahl liest die
Rotation, welche Kennzahl number_of_day heute traegt (aus dem Log oder vorab
mit number_of_day_data.choose() gerechnet), und ueberspringt jede Form mit
derselben Kennzahl (NOTD_KENNZAHL, FORM_KENNZAHL). Ereignisse eingeschlossen.

GEGEN WAS? (v5). Jedes Objekt zeigt den Vergleich selbst: eine zweite Groesse
im selben Massstab, den Rest einer Flaeche oder vorher gegen nachher.

AUSGABE: PNG 1080x1350, Vorschau 390 px, Discord-Text, X-Text, die
Antwort unter dem X-Post und eine Zeile Selbstpruefung. Mit --senden geht alles an DISCORD_WEBHOOK_OPS
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
FREIGESCHALTET = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}   # 13 erst nach Bens Beschluss


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


# Eine Hashrate je Lauf (Ben, 30.09.2026): jede Form nimmt das Tagesmittel aus
# /info/hashrate/history, einmal geholt. Keine Momentmessung daneben, damit
# nie ein Tageswert und ein Momentwert ungekennzeichnet in einem Bild stehen.
_HASHRATE = {}


def m_hashrate_tage():
    """Tagesmittel der Hashrate in TH/s aus api.kaspa.org/info/hashrate/history."""
    if "tage" not in _HASHRATE:
        roh = hole(REST + "/info/hashrate/history")
        je = {}
        for x in roh:
            t = dt.datetime.fromtimestamp(x["timestamp"] / 1000, dt.timezone.utc)
            je.setdefault(t.date().isoformat(), []).append(x["hashrate_kh"] / 1e9)
        _HASHRATE["tage"] = {d: sum(v) / len(v) for d, v in je.items()}
    return _HASHRATE["tage"]


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
# Jede Form: messen(now) -> werte (json-faehig), vorlage(werte, now) -> seite.
# Die Seite hat genau vier Texte (kopf, zahl, bedeutung, datumszeile) und ein
# Objekt, das die Daten IST (objekt(x, y, w, h) -> svg). Rahmen fuer alle
# gleich: Kopf oben links, Zahl, Objekt, Bedeutung, Datumszeile, Signatur.
#
# HERKUNFT (Ben, 29.09.2026). "counted by kaspa pulse" steht nur, wo wir die
# gezeigte Zahl selbst aus Kettendaten oder dem Emissionsplan gerechnet
# haben. Steckt eine Kaspalytics-Zahl darin, steht allein die Quelle.
SELBST = "counted by kaspa pulse"
# Die Datumszeile darf zwei Zeilen fuellen, nicht mehr. 140 Zeichen sind bei
# 30 px gut zwei Zeilen auf 952 px Breite (Form 9 im Selbsttest hat 133).
DATUMSZEILE_MAX = 140

# Farben (Hausnorm seit 29.09.2026): Hintergrund, Akzent, und genau ein
# dritter Ton fuer den "Rest" der Daten. Weiss nur fuer Kopf und Zahl.
BG, AK, RESTTON, WEISS = "#080B0F", "#49EACB", "#2B7A6C", "#FFFFFF"

# Eine Blockrate je Lauf, fuer jede Form, die eine braucht, ueber 10 Minuten
# gemessen (Ben, 30.09.2026). 60 Sekunden schwankten zwischen 9.75 und 9.93.
BLOCKRATE_SEK = 600
_BLOCKRATE = {}


def blockrate():
    if "bps" not in _BLOCKRATE:
        _BLOCKRATE["bps"], _BLOCKRATE["daa"] = m_blockrate(BLOCKRATE_SEK)
    return _BLOCKRATE["bps"], _BLOCKRATE["daa"]


def neue_kas(von, bis):
    """DIE Rechnung fuer "neue KAS" in jeder Form (Ben, 29.09.2026): Summe des
    Emissionsplans ueber die vollen UTC-Tage von..bis (beide eingeschlossen).
    Gibt (summe, tage) zurueck. Eine Tageszahl im Bild ist summe / tage, und
    das Fenster steht immer dabei."""
    a, b = dt.date.fromisoformat(von), dt.date.fromisoformat(bis)
    tage = [(a + dt.timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]
    return sum(emission_am_tag(d) for d in tage), len(tage)


def gestern(now):
    return (now.date() - dt.timedelta(days=1)).isoformat()


# --------------------------------------------------------------- objekte

def o_punkte(x, y, w, h, n, farbe=AK, hervor=0, hervor_farbe=AK, r=0.36):
    """n Punkte im Raster, so gross wie das Feld es erlaubt. Die letzten
    `hervor` Punkte in hervor_farbe."""
    if n <= 0:
        return ""
    best = None
    for spalten in range(1, n + 1):
        zeilen = math.ceil(n / spalten)
        z = min(w / spalten, h / zeilen)
        if best is None or z > best[0]:
            best = (z, spalten, zeilen)
        if spalten * z > w and z < best[0]:
            break
    z, spalten, zeilen = best
    x0 = x + (w - spalten * z) / 2
    s = []
    for i in range(n):
        f = hervor_farbe if i >= n - hervor else farbe
        s.append("<circle cx='%.1f' cy='%.1f' r='%.2f' fill='%s'/>"
                 % (x0 + (i % spalten) * z + z / 2, y + (i // spalten) * z + z / 2, z * r, f))
    return "".join(s)


def o_waffel(x, y, w, h, pct, n=10):
    gap = 8
    feld = min(w, h)
    q = (feld - (n - 1) * gap) / n
    x0 = x + (w - feld) / 2
    s = []
    for i in range(n * n):
        xx, yy = x0 + (i % n) * (q + gap), y + (i // n) * (q + gap)
        anteil = max(0.0, min(1.0, pct - i))
        s.append("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' rx='4' fill='%s'/>"
                 % (xx, yy, q, q, RESTTON))
        if anteil > 0:
            s.append("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' rx='4' fill='%s'/>"
                     % (xx, yy, q * anteil, q, AK))
    return "".join(s)


def o_saeulen(x, y, w, h, werte, hervor_index, zahl_platz=0):
    """Saeulen ab null, alle im Resteton, eine in Akzent. zahl_platz haelt
    rechts Platz frei (Form 3, die Zahl steht neben der Stufe)."""
    n = len(werte)
    gap = 6
    bw = (w - zahl_platz - gap * (n - 1)) / n
    hi = max(werte)
    s = []
    for i, v in enumerate(werte):
        hh = h * v / hi
        s.append("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' rx='4' fill='%s'/>"
                 % (x + i * (bw + gap), y + h - hh, bw, hh, AK if i == hervor_index else RESTTON))
    return "".join(s), bw, gap


def o_zwei_saeulen(x, y, w, h, links, rechts):
    """Zwei Saeulen ab null im selben Massstab, je mit kleiner Beschriftung
    darunter. links und rechts sind (wert, text, farbe). Die Prueffrage
    "gegen was?" (Ben, 30.09.2026): das Bild zeigt die Bezugsgroesse selbst."""
    unter, bw, gap = 60, 300, 120
    x0 = x + (w - 2 * bw - gap) / 2
    hi = max(links[0], rechts[0])
    s = ""
    for i, (v, text, farbe) in enumerate((links, rechts)):
        hs = max((h - unter) * v / hi, 4)
        s += ("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' rx='4' fill='%s'/>"
              % (x0 + i * (bw + gap), y + h - unter - hs, bw, hs, farbe))
        s += ("<text x='%.1f' y='%.1f' fill='%s' font-size='30' text-anchor='middle'>%s</text>"
              % (x0 + i * (bw + gap) + bw / 2, y + h - 12, farbe, text))
    return s


def o_flaeche_linie(x, y, w, h, werte):
    """Flaeche ab null im Resteton, Linie in Akzent, letzter Punkt markiert."""
    hi = max(werte) * 1.08
    n = len(werte)
    pts = [(x + w * i / (n - 1), y + h - h * v / hi) for i, v in enumerate(werte)]
    linie = " ".join("%.1f,%.1f" % p for p in pts)
    return ("<polygon points='%.1f,%.1f %s %.1f,%.1f' fill='%s'/>"
            "<polyline points='%s' fill='none' stroke='%s' stroke-width='3' stroke-linejoin='round'/>"
            "<circle cx='%.1f' cy='%.1f' r='10' fill='%s'/>"
            % (x, y + h, linie, x + w, y + h, RESTTON, linie, AK, pts[-1][0], pts[-1][1], AK))


# --------------------------------------------------------------- form 1

def messen_1(now):
    """Wochenzahl. Zwei Kandidaten, beide im Lauf gemessen: Adressen mit
    nennenswertem Guthaben (Kaspalytics) und Hashrate (api.kaspa.org,
    Tagesmittel). Je 8 Tage, gestern gegen 7 Tage davor.

    Nicht aus data/week-input.json: die Montagsroutine schreibt die Datei
    gegen 08:40 Berlin, um 07:30 steht dort noch die Vorwoche."""
    kand = []
    tage = [(now.date() - dt.timedelta(days=i)).isoformat() for i in range(8, 0, -1)]
    try:
        h = m_kl_reihe("address/count/meaningful-balance", "Addresses", "bestand")
        if all(d in h for d in tage):
            kand.append({"was": "holders", "reihe": [h[d] for d in tage], "tage": tage})
    except Exception as exc:                        # noqa: BLE001
        print("form 1, holders nicht belegt: %s" % exc)
    try:
        if "hashrate" in GESPERRTE_KENNZAHLEN:
            raise Stop("die zahl des tages zeigt heute die hashrate")
        hr = m_hashrate_tage()
        if all(d in hr for d in tage):
            kand.append({"was": "hashrate", "reihe": [hr[d] / 1000 for d in tage], "tage": tage})
    except Exception as exc:                        # noqa: BLE001
        print("form 1, hashrate nicht belegt: %s" % exc)
    if not kand:
        raise Stop("keine wochenzahl belegt")
    return {"kandidaten": kand}


def vorlage_1(w, now):
    for k in w["kandidaten"]:
        k["pct"] = 100 * (k["reihe"][-1] / k["reihe"][0] - 1)
    k = max(w["kandidaten"], key=lambda x: x["pct"])
    r, t = k["reihe"], k["tage"]
    if k["was"] == "holders":
        bed = "addresses with a meaningful balance, %s against %s" % (tag_kurz(t[-1]), tag_kurz(t[0]))
        her = "source kaspalytics address counts"
        zus = "one column per day, from zero"
    else:
        bed = "daily hashrate, %s against %s" % (tag_kurz(t[-1]), tag_kurz(t[0]))
        her = "source kaspa rest api hashrate"
        zus = "daily hashrate, one column per day, from zero"

    def objekt(x, y, ww, hh):
        # nur zwei saeulen, der erste und der letzte tag, ab null, die
        # rechte hell, beide klein beschriftet (Ben, 30.09.2026, v4)
        unter, bw, gap = 52, 300, 120
        x0 = x + (ww - 2 * bw - gap) / 2
        hi = max(r[0], r[-1])
        s = ""
        for i, (v, farbe) in enumerate(((r[0], RESTTON), (r[-1], AK))):
            hs = (hh - unter) * v / hi
            s += ("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' rx='4' fill='%s'/>"
                  % (x0 + i * (bw + gap), y + hh - unter - hs, bw, hs, farbe))
            s += ("<text x='%.1f' y='%.1f' fill='%s' font-size='30' text-anchor='middle'>%s</text>"
                  % (x0 + i * (bw + gap) + bw / 2, y + hh - 10, farbe, tag_kurz(t[-1 if i else 0])))
        return s
    ganzzahl = abs(round(k["pct"]))
    wie = "rose" if k["pct"] > 0 else "fell"
    if k["was"] == "holders":
        n = r[-1] - r[0]
        x1 = "kaspa %s %s addresses with a meaningful balance in one week." % (
            "gained" if n >= 0 else "lost", ganz(abs(n)))
        x2 = "%s against %s, source kaspalytics address counts" % (tag_kurz(t[-1]), tag(t[0]))
        x3 = "how many is that a day?"
        aufl = ("%s in 7 days is about %s a day. kaspalytics counted %s on %s and %s on %s." % (
            ganz(abs(n)), ganz(abs(n) / 7), ganz(r[-1]), tag_kurz(t[-1]), ganz(r[0]), tag_kurz(t[0])))
    else:
        x1 = ("kaspa hashrate %s %d%% in one week." % (wie, ganzzahl) if ganzzahl
              else "kaspa hashrate held within 1% of the week before.")
        x2 = "daily average, %s against %s, source kaspa rest api" % (tag_kurz(t[-1]), tag(t[0]))
        x3 = "how many hashes is that?"
        aufl = ("on %s the network averaged %.1f PH/s, that is %s quadrillion hashes every second. "
                "on %s the average was %.1f PH/s." % (tag_kurz(t[-1]), r[-1], ganz(r[-1]),
                                                      tag_kurz(t[0]), r[0]))
    return {"kopf": "THIS WEEK", "zahl": "%+.1f%%" % k["pct"], "bedeutung": bed,
            "zusatz": zus.replace("one column per day", "first and last day"), "herkunft": her,
            "objekt": objekt, "x1": x1, "x2": x2, "x3": x3, "aufloesung": aufl,
            "pruefung": ("ja, %s steigt gegen die Vorwoche, und die Saeulen zeigen es ab null"
                         % k["was"]) if k["pct"] > 0 else
                        "nein, %s ist gegen die Vorwoche gefallen" % k["was"]}


# --------------------------------------------------------------- form 2

def messen_2(now):
    circ, _ = m_supply()
    bal = m_balance(EX_ADR)
    bew = m_entityx_bewegungen(7)
    return {"circ": circ, "bal": bal, "bewegungen": bew}


def ex_24h(w, now):
    grenze = (now - dt.timedelta(hours=24)).isoformat(timespec="seconds")
    return [b for b in w["bewegungen"] if b["zeit_utc"] >= grenze and abs(b["netto"]) >= EX_EREIGNIS]


STREIFEN_MIN_390 = 3      # px in der 390er vorschau, darunter kein streifen


def streifen_breite(seite, w, netto):
    """Breite des Bewegungsstreifens am Wallet-Quadrat. Flaechentreu im
    Massstab des Umlaufs: Kante des Wallet-Quadrats mal Bewegung / Guthaben
    (Ben, 30.09.2026)."""
    wa = seite * math.sqrt(w["bal"] / w["circ"])
    return wa, wa * abs(netto) / w["bal"]


def vorlage_2(w, now):
    """Die Wallet als Flaeche im Umlauf, beide im selben Flaechenmassstab.
    Die letzte Bewegung ist ein heller Streifen an der Kante des
    Wallet-Quadrats, im selben Massstab. Ist er in der 390er Vorschau unter
    3 px, faellt er weg und die Bewegung steht nur in der Bedeutungszeile.
    Kein Dollarwert."""
    anteil = 100 * w["bal"] / w["circ"]
    gross = [b for b in w["bewegungen"] if abs(b["netto"]) >= 100000]
    ereignis = ex_24h(w, now)
    b = max(ereignis, key=lambda x: abs(x["netto"])) if ereignis else (gross[-1] if gross else None)
    # die seite des umlauf-quadrats haengt nur an der objektzone, siehe html()
    _, oy, ow, oh = objektzone(zahlgroesse("%.2f%%" % anteil))
    seite = min(ow * 0.78, oh)
    streifen = False
    if b:
        _, sb = streifen_breite(seite, w, b["netto"])
        streifen = sb * VORSCHAU / W >= STREIFEN_MIN_390
        t = dt.datetime.fromisoformat(b["zeit_utc"])
        wie = "left" if b["netto"] < 0 else "came in"
        bed = "of all KAS sits in one wallet. %s KAS %s on %s%s" % (
            kurz(abs(b["netto"])), wie, tag_kurz(t.date()), ", the bright strip" if streifen else "")
        x2 = "%s KAS %s it on %s, %s, counted on chain" % (
            kurz(abs(b["netto"])), "left" if b["netto"] < 0 else "came into", tag(t.date()), uhr(t))
    else:
        bed = "of all KAS sits in one wallet, no move above 100,000 KAS in 7 days"
        x2 = "no move above 100,000 KAS in the 7 days to %s, counted on chain" % tag(now.date())

    def objekt(x, y, ww, hh):
        seite = min(ww * 0.78, hh)
        s = ("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' rx='4' fill='%s'/>"
             % (x, y, seite, seite, RESTTON))
        wa = seite * math.sqrt(w["bal"] / w["circ"])
        if streifen:
            # kam etwas herein, ist der streifen teil des guthabens und liegt
            # innen an der rechten kante; ging etwas hinaus, liegt er aussen.
            _, sb = streifen_breite(seite, w, b["netto"])
            innen = b["netto"] > 0
            s += ("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' fill='%s'/>"
                  % (x, y, wa - (sb + 4 if innen else 0), wa, AK))
            s += ("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' fill='%s'/>"
                  % (x + (wa - sb if innen else wa + 4), y, sb, wa, AK))
        else:
            s += ("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' rx='4' fill='%s'/>"
                  % (x, y, wa, wa, AK))
        return s
    return {"kopf": "ENTITY X MOVED" if ereignis else "ENTITY X", "zahl": "%.2f%%" % anteil,
            "bedeutung": bed, "zusatz": "areas to scale, the big square is all KAS in circulation",
            "streifen": streifen, "herkunft": SELBST, "objekt": objekt,
            "x1": "one wallet holds about 1 in %d of all KAS in circulation." % round(w["circ"] / w["bal"]),
            "x2": x2, "x3": "how many KAS is that?",
            "aufloesung": "%s KAS sit in that one wallet on %s, %.2f%% of the %s KAS in circulation. "
                          "its address is public, and we check it several times a day." % (
                              ganz(w["bal"]), tag_kurz(now.date()), anteil, kurz(w["circ"])),
            "pruefung": "nein, eine Wallet-Bewegung wird als Nachricht geteilt, nicht zum Angeben. "
                        "Die Form bleibt, weil Halter sie sehen wollen"}


# --------------------------------------------------------------- form 3

def messen_3(now):
    nod = reward_plan()
    cur, nxt, nxt_ts = nod.reward_state(now.timestamp())
    # fuenf vergangene stufen, die laufende, die naechste
    stufen = [nod.reward_state(nxt_ts - (k + 0.5) * nod.STEP)[0] for k in range(5, -1, -1)]
    if abs(stufen[-1] - cur) > 1e-9:
        raise Stop("treppe passt nicht zur laufenden stufe")
    return {"cur": cur, "nxt": nxt, "nxt_ts": nxt_ts, "stufen": stufen + [nxt]}


def cut_tage(w, now):
    return (w["nxt_ts"] - now.timestamp()) / 86400


def vorlage_3(w, now):
    t = dt.datetime.fromtimestamp(w["nxt_ts"], dt.timezone.utc)
    tage = math.ceil(cut_tage(w, now))
    zahl = "%d day%s" % (tage, "" if tage == 1 else "s")

    def objekt(x, y, ww, hh):
        platz = 330
        s, bw, gap = o_saeulen(x, y, ww, hh, w["stufen"], len(w["stufen"]) - 1, zahl_platz=platz)
        # die zahl steht neben der naechsten stufe, nicht darueber
        xs = x + len(w["stufen"]) * (bw + gap) + 24
        ys = y + hh - hh * w["stufen"][-1] / max(w["stufen"])
        s += ("<text x='%.1f' y='%.1f' fill='%s' font-weight='700' font-size='200' "
              "letter-spacing='-6'>%d</text><text x='%.1f' y='%.1f' fill='%s' font-weight='700' "
              "font-size='64'>day%s</text>" % (xs, ys + 150, WEISS, tage, xs + 6, ys + 222, WEISS,
                                              "" if tage == 1 else "s"))
        # die beiden letzten stufen tragen ihren wert, klein ueber der saeule
        # (Ben, 02.10.2026). kein eigenes textelement der seite, die zahl
        # bleibt die einzige grosse zahl, die fusszeile bleibt.
        n = len(w["stufen"])
        for i, farbe in ((n - 2, RESTTON), (n - 1, AK)):
            v = w["stufen"][i]
            s += ("<text x='%.1f' y='%.1f' fill='%s' font-size='30' font-weight='700' "
                  "text-anchor='middle'>%.2f</text>" % (x + i * (bw + gap) + bw / 2,
                                                       y + hh - hh * v / max(w["stufen"]) - 14, farbe, v))
        return s
    return {"kopf": "NEXT REWARD CUT", "zahl": zahl, "zahl_im_objekt": True,
            "bedeutung": "KAS per block, one step a month. the next step, %s, %s" % (tag(t.date()), uhr(t)),
            "zusatz": "from zero",
            "herkunft": SELBST, "objekt": objekt,
            "x1": "kaspa cuts its block reward again in %s." % zahl,
            "x2": "next step %s, %s, from the emission schedule" % (tag(t.date()), uhr(t)),
            "x3": "how often does that happen?",
            "aufloesung": "once a month, and 12 steps halve the reward. on %s it goes from %.2f "
                          "to %.2f KAS per block." % (tag_kurz(t.date()), w["cur"], w["nxt"]),
            "pruefung": "ja, knappe Terminzahl mit Datum, Halter teilen Countdowns gern"}


# --------------------------------------------------------------- form 4

RUHEPULS, SCHLAF_H = 60, 8


def messen_4(now):
    bps, daa = blockrate()
    return {"bps": bps, "daa": daa, "sek": BLOCKRATE_SEK}


def vorlage_4(w, now):
    """Zwei Balken ab null in denselben 8 Stunden: deine Herzschlaege gegen
    die Bloecke, der Bloecke-Balken hell (Ben, 30.09.2026, v5). Die Bloecke
    aus der einen Blockrate, ueber 10 Minuten gemessen."""
    bloecke = w["bps"] * SCHLAF_H * 3600
    schlaege = RUHEPULS * 60 * SCHLAF_H
    je_schlag = bloecke / schlaege

    def objekt(x, y, ww, hh):
        return o_zwei_saeulen(x, y, ww, hh,
                              (schlaege, "your heartbeats, %s" % ganz(schlaege), RESTTON),
                              (bloecke, "blocks, %s" % ganz(round(bloecke, -3)), AK))
    return {"kopf": "WHILE YOU SLEPT", "zahl": ganz(round(bloecke, -3)),
            "bedeutung": "%.0f blocks for every heartbeat while you slept" % je_schlag,
            "zusatz": "the same %d hours, from zero, resting pulse %d assumed" % (SCHLAF_H, RUHEPULS),
            "herkunft": SELBST, "objekt": objekt,
            "x1": "kaspa added %s blocks while you slept." % ganz(round(bloecke, -3)),
            "x2": "%d hours at the block rate we measured over %d minutes, %s, %s" % (
                SCHLAF_H, w.get("sek", BLOCKRATE_SEK) // 60, tag(now.date()), uhr(now)),
            "x3": "how many did you sleep through?",
            "aufloesung": "about %.0f for every heartbeat, at a resting pulse of %d that is %s beats "
                          "in %d hours. we measured %.2f blocks per second over %d minutes." % (
                              je_schlag, RUHEPULS, ganz(schlaege), SCHLAF_H, w["bps"],
                              w.get("sek", BLOCKRATE_SEK) // 60),
            "pruefung": "ja, die Bloecke stehen im Bild neben dem eigenen Herzschlag"}


# --------------------------------------------------------------- form 5

def messen_5(now):
    """30 volle UTC-Tage bis gestern. Gebuehren und neue Coins fuer dieselben
    Tage; ein Tag ohne Gebuehrenwert faellt aus Zaehler UND Nenner."""
    bis = now.date() - dt.timedelta(days=1)
    tage = [(bis - dt.timedelta(days=i)).isoformat() for i in range(30)]
    fees = m_kl_reihe("transactions/accepted/fees/total", None, "fluss")
    mit = sorted(d for d in tage if d in fees)
    if len(mit) < 25:
        raise Stop("nur %d von 30 tagen mit gebuehr" % len(mit))
    f = sum(fees[d] for d in mit)
    e = sum(neue_kas(d, d)[0] for d in mit)
    return {"tage": len(mit), "von": mit[0], "bis": mit[-1], "fees": f, "emission": e}


def vorlage_5(w, now):
    fx = w["emission"] / w["fees"]
    n = round(fx) + 1
    return {"kopf": "WHAT PAYS THE MINERS", "zahl": "%sx" % ganz(fx),
            "bedeutung": "more KAS in new coins than in fees. the one bright square is the fees",
            "zusatz": "%d days to %s, one square each" % (w["tage"], tag(w["bis"])),
            "herkunft": "source kaspalytics fees, kaspa emission schedule",
            "objekt": lambda x, y, ww, hh: o_punkte(x, y, ww, hh, n, RESTTON, hervor=1, r=0.42),
            "x1": "kaspa miners earned %s times more in new coins than in fees." % ganz(fx),
            "x2": "%d days to %s, source kaspalytics fees and the emission schedule" % (
                w["tage"], tag(w["bis"])),
            "x3": "so what pays the miners?",
            "aufloesung": "mostly new coins, %s KAS in those %d days. fees paid %s KAS in the same days." % (
                kurz(w["emission"]), w["tage"], ganz(w["fees"])),
            "pruefung": "nein, stark, aber fuer Halter erklaerungsbeduerftig. Nerds teilen sie, "
                        "der Durchschnitt nicht"}


# --------------------------------------------------------------- form 6

def messen_6(now):
    w = {}
    d = hole(REST + "/info/blockdag")
    w["daa"] = int(d["virtualDaaScore"])
    return w


# Crescendo, der Wechsel von 1 auf 10 Bloecke je Sekunde. Protokollkonstante
# aus rusty-kaspa v2.1.0, consensus/core/src/config/params.rs, MAINNET_PARAMS
# (crescendo_activation), "roughly 2025-05-05 1500 UTC".
CRESCENDO_DAA = 110165000


def vorlage_6(w, now):
    """Ein waagerechtes Lineal, eine Marke je 100 Millionen Bloecke, der
    Endpunkt mit der Zahl daneben, die Startmarke "nov 2021" (Ben,
    30.09.2026). Nur der Monat, weil der Genesis-Block der API der Neustart
    vom 22.11.2021 ist und schon DAA 1.312.860 traegt.
    v5, "gegen was?": das Lineal ist geteilt, vor Crescendo im dritten Ton,
    danach hell. So steht im Bild, wie viel davon in den letzten Monaten kam."""
    daa = w["daa"]
    mio = round(daa / 1e6)
    danach = 100 * (daa - CRESCENDO_DAA) / daa

    def objekt(x, y, ww, hh):
        platz = 250                      # rechts fuer "553M" neben dem endpunkt
        L = ww - platz
        ym = y + hh * 0.5
        x_ende = x + L
        xc = x + L * CRESCENDO_DAA / daa
        s = ["<rect x='%.1f' y='%.1f' width='%.1f' height='14' rx='3' fill='%s'/>"
             % (x, ym - 7, xc - x, RESTTON),
             "<rect x='%.1f' y='%.1f' width='%.1f' height='14' rx='3' fill='%s'/>"
             % (xc, ym - 7, x + L - xc, AK)]
        # startmarke, dann je 100M eine marke, alle gleich
        for k in range(int(daa // 1e8) + 1):
            mx = x + L * (k * 1e8) / daa
            s.append("<rect x='%.1f' y='%.1f' width='6' height='80' rx='3' fill='%s'/>"
                     % (mx - (0 if k == 0 else 3), ym - 40, RESTTON))
        s.append("<text x='%.1f' y='%.1f' fill='%s' font-size='34'>nov 2021</text>"
                 % (x, ym + 96, RESTTON))
        s.append("<rect x='%.1f' y='%.1f' width='6' height='120' rx='3' fill='%s'/>"
                 % (xc - 3, ym - 60, AK))
        s.append("<text x='%.1f' y='%.1f' fill='%s' font-size='34' text-anchor='middle'>may 2025</text>"
                 % (xc, ym - 84, AK))
        s.append("<circle cx='%.1f' cy='%.1f' r='18' fill='%s'/>" % (x_ende, ym, AK))
        s.append("<text x='%.1f' y='%.1f' fill='%s' font-size='64' font-weight='700'>%dM</text>"
                 % (x_ende + 40, ym + 23, AK, mio))
        return "".join(s)
    jahre = (now - dt.datetime(2021, 11, 7, tzinfo=dt.timezone.utc)).days / 365.25
    return {"kopf": "FROM THE CHAIN", "zahl": "%dM" % mio,
            "bedeutung": "blocks since nov 2021, %d%% of them since may 2025" % math.floor(danach),
            "zusatz": "daa score, a mark every 100 million, 10 blocks a second since may 2025, 1 before",
            "herkunft": SELBST, "objekt": objekt,
            "x1": "the kaspa chain has passed %d million blocks since nov 2021." % (daa // 1000000),
            "x2": "counted by the network's daa score, %s, %s" % (tag(now.date()), uhr(now)),
            "x3": "who keeps that count?",
            "aufloesung": "every kaspa node does, it is the daa score, %s on %s, %s. the same counter "
                          "has run since the first blocks in nov 2021." % (
                              ganz(daa), tag_kurz(now.date()), uhr(now)),
            "pruefung": "ja, das Lineal zeigt vorher gegen nachher, %.1f Jahre Kette" % (
                math.floor(jahre * 10) / 10)}


# --------------------------------------------------------------- form 7

def messen_7(now):
    """Von Hand: data/tagesgrafik-community.json, die erste Frage mit
    "offen": true. Ben liefert Frage, Antwort, Zahl, Namen, Messdatum und
    das Objekt, seit v5 (30.09.2026) immer mit Vergleich im Bild:
    {"art": "anteil", "prozent": p} oder
    {"art": "zwei", "a": {"wert": x, "text": "..."}, "b": {"wert": y, "text": "..."}},
    b ist die Zahl der Frage und steht hell. "punkte" allein zeigt nur die
    eine Zahl in anderer Gestalt und wird abgelehnt."""
    try:
        d = json.loads(COMMUNITY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise Stop("keine community-datei")
    for e in d.get("fragen") or []:
        if e.get("offen"):
            art = (e.get("objekt") or {}).get("art")
            if art not in ("anteil", "zwei"):
                raise Stop("form 7 braucht einen vergleich im bild, objekt anteil oder zwei, nicht %r" % art)
            return {"eintrag": e}
    raise Stop("keine offene community-frage")


def vorlage_7(w, now):
    e = w["eintrag"]
    ob = e.get("objekt") or {}

    def objekt(x, y, ww, hh):
        if ob.get("art") == "anteil":
            return o_waffel(x, y, ww, hh, float(ob["prozent"]))
        return o_zwei_saeulen(x, y, ww, hh,
                              (float(ob["a"]["wert"]), ob["a"]["text"], RESTTON),
                              (float(ob["b"]["wert"]), ob["b"]["text"], AK))
    zusatz = "one square is 1%" if ob.get("art") == "anteil" else "both from zero"
    return {"kopf": "%s ASKED" % e["name"].upper(), "zahl": e["zahl"],
            "bedeutung": "%s, %s" % (e["antwort"], tag(e["stand"])),
            "zusatz": zusatz, "herkunft": e.get("quelle") or SELBST, "objekt": objekt,
            "x1": "%s %s." % (e["zahl"], e["antwort"]),
            "x2": "asked by %s in our discord, %s" % (e["name"], tag(e["stand"])),
            "x3": "what should we count next?",
            "aufloesung": "%s asked, and we counted %s on %s, %s. ask the next one in #data-requests." % (
                e["name"], e["zahl"], tag_kurz(e["stand"]), e.get("quelle") or SELBST),
            "pruefung": "ja, wer gefragt hat, teilt die Antwort mit seinem Namen darauf"}


# --------------------------------------------------------------- form 8

def messen_8(now):
    """Eine Hashrate je Lauf: das Tagesmittel. Die grosse Zahl ist gestern,
    die Flaeche die 90 Tage bis gestern, beide aus derselben Reihe."""
    hr = m_hashrate_tage()
    tage = [(now.date() - dt.timedelta(days=i)).isoformat() for i in range(90, 0, -1)]
    if tage[-1] not in hr:
        raise Stop("kein tagesmittel der hashrate fuer %s" % tage[-1])
    reihe = [hr[d] / 1000 for d in tage if d in hr]
    if len(reihe) < 80:
        raise Stop("hashrate-reihe hat nur %d von 90 tagen" % len(reihe))
    neu, _ = neue_kas(gestern(now), gestern(now))
    return {"ph": hr[tage[-1]] / 1000, "reihe": reihe, "von": tage[0], "bis": tage[-1],
            "neu": neu, "neu_tag": gestern(now)}


def vorlage_8(w, now):
    t = w["bis"]
    return {"kopf": "SECURED BY WORK", "zahl": "%.1f PH/s" % w["ph"],
            "bedeutung": "%s quadrillion hashes every second on %s" % (ganz(w["ph"]), tag_kurz(t)),
            "zusatz": "daily hashrate %s, 90 days, from zero" % tag_kurz(t),
            "herkunft": "source kaspa rest api hashrate",
            "objekt": lambda x, y, ww, hh: o_flaeche_linie(x, y, ww, hh, w["reihe"]),
            "x1": "kaspa miners ran %s quadrillion hashes every second." % ganz(w["ph"]),
            "x2": "daily average %s, source kaspa rest api" % tag(t),
            "x3": "what was that work paid?",
            "aufloesung": "%s new KAS on %s, from the emission schedule. the hashrate that day "
                          "averaged %.1f PH/s." % (kurz(w["neu"]), tag_kurz(w["neu_tag"]), w["ph"]),
            "pruefung": "ja, Quadrillion pro Sekunde ist ein Angeber-Kontrast ohne Kursbezug"}


# --------------------------------------------------------------- form 9

def messen_9(now):
    """Adressen ab 100 KAS, die letzten 8 Tage als Tageswerte, damit das
    Objekt die Zugaenge je Tag zeigen kann."""
    import address_thresholds_log as atl
    roh, probleme = atl.sammle(heute=now.date())
    tage = sorted(d for d in roh if "holders_100kas" in roh[d])
    if not tage:
        raise Stop("keine schwellen: %s" % probleme)
    d1 = tage[-1]
    acht = [d1 - dt.timedelta(days=i) for i in range(7, -1, -1)]
    fehlt = [d.isoformat() for d in acht if d not in tage]
    if fehlt:
        raise Stop("adressen ab 100 KAS fehlen fuer %s" % ", ".join(fehlt))
    return {"d1": d1.isoformat(), "d0": acht[0].isoformat(),
            "tage": {d.isoformat(): roh[d]["holders_100kas"] for d in acht}}


def o_tagesspalten(x, y, w, h, werte, beschriftung):
    """Eine Spalte je Tag, ein Punkt je Adresse, alle Spalten im selben
    Punktabstand. Zugaenge stehen hell ueber der Linie, ein Tag mit
    Rueckgang zeigt seine Punkte im Resteton darunter, die Zahl unten traegt
    das Vorzeichen. So stimmt jede Spalte, auch wenn ein Tag faellt."""
    n = len(werte)
    gap, unter, luft = 24, 52, 14
    cw = (w - gap * (n - 1)) / n
    hoch = h - unter - luft
    auf = max([v for v in werte if v > 0] or [0])
    ab = max([-v for v in werte if v < 0] or [0])
    best = (0, 1)
    for k in range(1, 40):
        zeilen = math.ceil(auf / k) + math.ceil(ab / k)
        pz = min(cw / k, hoch / max(1, zeilen))
        if pz > best[0]:
            best = (pz, k)
    pz, k = best
    yl = y + math.ceil(auf / k) * pz + luft / 2          # die linie
    s = []
    if ab:
        s.append("<rect x='%.1f' y='%.1f' width='%.1f' height='2' fill='%s'/>" % (x, yl - 1, w, RESTTON))
    for i, v in enumerate(werte):
        x0 = x + i * (cw + gap) + (cw - k * pz) / 2
        for j in range(abs(v)):
            cx = x0 + (j % k) * pz + pz / 2
            if v > 0:
                cy, farbe = yl - luft / 2 - (j // k) * pz - pz / 2, AK
            else:
                cy, farbe = yl + luft / 2 + (j // k) * pz + pz / 2, RESTTON
            s.append("<circle cx='%.1f' cy='%.1f' r='%.1f' fill='%s'/>" % (cx, cy, pz * 0.36, farbe))
        s.append("<text x='%.1f' y='%.1f' fill='%s' font-size='30' text-anchor='middle'>%s</text>"
                 % (x + i * (cw + gap) + cw / 2, y + h - 10, RESTTON, beschriftung[i]))
    return "".join(s)


def vorlage_9(w, now):
    """Das Objekt zeigt nur die neuen Adressen, ein Punkt je Adresse, sieben
    Spalten fuer sieben Tage, die Tageszahl klein darunter (Ben, 30.09.2026).
    Die Gesamtzahl bleibt die grosse Zahl oben."""
    reihe = [w["tage"][d] for d in sorted(w["tage"])]
    tage = sorted(w["tage"])[1:]
    neu = [b - a for a, b in zip(reihe, reihe[1:])]
    j = reihe[-1]
    plus = j - reihe[0]
    rueck = any(v < 0 for v in neu)
    return {"kopf": "ADDRESSES", "zahl": ganz(j),
            "bedeutung": "addresses hold at least 100 KAS, %+d in 7 days, one dot each" % plus,
            "zusatz": "one column per day, %s to %s%s" % (
                tag_kurz(tage[0]), tag_kurz(tage[-1]), ", below the line a day that fell" if rueck else ""),
            "herkunft": "source kaspalytics address thresholds",
            "objekt": lambda x, y, ww, hh: o_tagesspalten(x, y, ww, hh, neu, ["%+d" % v for v in neu]),
            "x1": "%s kaspa addresses now hold at least 100 KAS." % ganz(j),
            "x2": "%s, source kaspalytics address thresholds" % tag(w["d1"]),
            "x3": "how many joined this week?",
            "aufloesung": "%+d net in the 7 days to %s. %s came in on the days it grew%s." % (
                plus, tag_kurz(w["d1"]), ganz(sum(v for v in neu if v > 0)),
                "".join(", and it fell by %s on %s" % (ganz(-v), tag_kurz(d))
                        for d, v in zip(tage, neu) if v < 0)),
            "pruefung": ("ja, die Schwelle waechst, und jeder kann sich darin wiederfinden"
                         if plus > 0 else "nein, die Zahl ist in dieser Woche gefallen")}


# --------------------------------------------------------------- form 10

def messen_10(now):
    circ, mx = m_supply()
    return {"circ": circ, "max": mx}


def vorlage_10(w, now):
    pct = 100 * w["circ"] / w["max"]
    return {"kopf": "MINED SO FAR", "zahl": "%.2f%%" % pct, "bedeutung": "0 premine",
            "bedeutung_fett": True,
            "zusatz": "one square is 1% of all KAS that will ever exist",
            "herkunft": SELBST,
            "objekt": lambda x, y, ww, hh: o_waffel(x, y, ww, hh, pct),
            "x1": "%d%% of all KAS that will ever exist is already mined, with 0 premine." % round(pct),
            "x2": "%s, coin supply against max supply" % tag(now.date()),
            "x3": "how much is left?",
            "aufloesung": "%s KAS, %.2f%% of the %s maximum. every coin so far came from proof of "
                          "work since the first blocks in nov 2021." % (
                              kurz(w["max"] - w["circ"]), 100 - pct, kurz(w["max"])),
            "pruefung": "ja, fairer Start ist der Stolz der Community, und die Zahl belegt ihn"}


def messen_11(now):
    """Schlafende Coins. Kaspalytics supply/inactive, Reihe CSPERCENT, fuer
    minAge=1year und minAge=2years. Momentaufnahme, Stichtag nach der
    Mitternachtsregel in kaspalytics.stichtag. Beide Werte vom selben
    Stichtag, sonst keine Grafik."""
    eins = m_kl_reihe("supply/inactive?minAge=1year", "CSPERCENT", "bestand")
    zwei = m_kl_reihe("supply/inactive?minAge=2years", "CSPERCENT", "bestand")
    # nie der laufende tag (regel 2 in kaspalytics.py): am 30.09.2026 um 18:26
    # utc lag schon ein punkt fuer den 30.09. vor (lauf 36758580309)
    heute = now.date().isoformat()
    gemeinsam = sorted(d for d in set(eins) & set(zwei) if d < heute)
    if not gemeinsam:
        raise Stop("kein gemeinsamer stichtag fuer 1 und 2 jahre")
    d = gemeinsam[-1]
    if d < (now.date() - dt.timedelta(days=3)).isoformat():
        raise Stop("letzter stichtag %s ist aelter als 3 tage" % d)
    p1, p2 = eins[d], zwei[d]
    if not 0 < p2 <= p1 < 100:
        raise Stop("anteile unplausibel, 1 jahr %s, 2 jahre %s" % (p1, p2))
    return {"stichtag": d, "p1": p1, "p2": p2}


AK_DUNKEL = "#2FAE96"   # nur form 11: der akzent dunkler abgesetzt (Ben, 30.09.2026)


def vorlage_11(w, now):
    """Ein Balken ueber die volle Breite. Hell der Anteil seit 1 Jahr
    unbewegt, darin dunkler abgesetzt der seit 2 Jahren, der Rest im dritten
    Ton. Kein Motiv, kein dormant, kein hodl."""
    p1, p2, d = w["p1"], w["p2"], w["stichtag"]
    halb = 45 <= p1 <= 55
    bed = ("half of all KAS has not moved in a year" if halb
           else "%d%% of all KAS has not moved in a year" % round(p1))

    def objekt(x, y, ww, hh):
        bh = 200
        yb = y + (hh - bh) / 2 - 90
        s = ("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' rx='6' fill='%s'/>"
             % (x, yb, ww, bh, RESTTON))
        s += ("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' rx='6' fill='%s'/>"
              % (x, yb, ww * p1 / 100, bh, AK))
        s += ("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' rx='6' fill='%s'/>"
              % (x, yb, ww * p2 / 100, bh, AK_DUNKEL))
        # kleine legende in drei zeilen unter dem balken, je ein farbquadrat
        for i, (farbe, text) in enumerate(((AK_DUNKEL, "not moved in 2 years or more, %.2f%%" % p2),
                                           (AK, "not moved in 1 to 2 years, %.2f%%" % (p1 - p2)),
                                           (RESTTON, "moved within a year, %.2f%%" % (100 - p1)))):
            yl = yb + bh + 60 + i * 50
            s += ("<rect x='%.1f' y='%.1f' width='26' height='26' rx='4' fill='%s'/>"
                  "<text x='%.1f' y='%.1f' fill='%s' font-size='30'>%s</text>"
                  % (x, yl - 23, farbe, x + 42, yl, farbe, text))
        return s
    return {"kopf": "SLEEPING COINS", "zahl": "%.2f%%" % p1, "bedeutung": bed,
            "zusatz": "", "herkunft": "source kaspalytics, age estimated by daa score, %s" % tag(d),
            "objekt": objekt,
            "x1": (bed if halb else "%d%% of all KAS in circulation has not moved in a year" % round(p1)) + ".",
            "x2": "%s, source kaspalytics, age estimated by daa score" % tag(d),
            "x3": "how much has not moved in 2 years?",
            "aufloesung": "%.2f%% has not moved in 2 years, and %.2f%% in 1 year, as of %s. kaspalytics "
                          "estimates the age of each coin from the daa score of its last move." % (
                              p2, p1, tag_kurz(d)),
            "pruefung": "ja, die Haelfte des Umlaufs unbewegt ist eine Zahl, die Halter gern zeigen"}


def messen_13(now):
    raise Stop("form 13 ist gesperrt, bis die tagesreihe der nodes beschlossen ist")


def vorlage_13(w, now):
    return {"kopf": "NODES", "zahl": ganz(w["nodes"]),
            "bedeutung": "reachable over IPv4, counted by us", "zusatz": "", "herkunft": SELBST,
            "objekt": lambda x, y, ww, hh: o_punkte(x, y, ww, hh, int(w["nodes"])),
            "x1": "", "x2": "", "x3": "is yours one of them?", "aufloesung": "",
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
    11: ("schlafende coins", messen_11, vorlage_11),
    13: ("nodes", messen_13, vorlage_13),
}


# ------------------------------------------------------------ textpruefung

WORTLISTE = ("sold", "sell", "sells", "selling", "sale", "bought", "buy", "buys", "buying",
             "purchase", "purchased", "dump", "dumping", "whale", "whales", "because",
             "motive", "panic", "exit", "cash out", "profit", "wants", "intends", "plans",
             "preparing", "moon", "pump", "bullish", "bearish", "target", "to the moon",
             "dormant", "hodl", "hodling", "hodlers", "diamond hands")
# Form 11 zeigt, dass Coins nicht bewegt wurden, nie warum (Ben, 30.09.2026).
MOTIV_11 = ("deliberately", "deliberate", "forgotten", "forget", "lost", "conviction", "believe",
            "believers", "faith", "refuse", "refusing", "waiting", "patient", "patience",
            "long term holders", "long-term holders", "strong hands", "weak hands", "never sell")
# Echtzeit-Woerter (Ben, 27.09. und 29.09.2026): unsere Bots pruefen mehrmals
# am Tag, nicht laufend. Die Woerter fallen ueberall, auch wo sie fuer Bloecke
# stimmen wuerden.
ECHTZEIT = ("around the clock", "real time", "realtime", "real-time", "every minute",
            "instantly", "instant", "live", "the second", "the moment", "24/7")
# Kein Vergleich mit einer anderen Chain, in keiner Form (Ben, 29.09.2026).
FREMDE_CHAINS = ("bitcoin", "btc", "ethereum", "eth", "solana", "sol", "cardano", "xrp",
                 "litecoin", "ltc", "dogecoin", "doge", "monero", "xmr", "alephium", "alph",
                 "ergo", "erg", "chain b", "other chain", "other chains")
ANGRIFF = ("attack", "attacker", "attackers", "51", "hack", "hacked", "rent", "rented",
           "break the chain", "double spend", "double-spend", "take over", "overpower")
ZAHLWORTE = ("two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
             "eleven", "twelve", "twenty", "thirty", "forty", "fifty", "hundred",
             "thousand")
ZEITRAUM = re.compile(r"since \d{1,2} [a-z]{3}|since (19|20)\d\d|since the first block|"
                      r"since [a-z]{3} (19|20)\d\d|in the \d+ (days|weeks|months)|"
                      r"in \d+ (days|weeks|months)|\d+ days to|where our series starts|"
                      r"in our (log|series) since", re.I)
DATUM = re.compile(r"\b\d{1,2} (jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b")
DATUMSZEILE = re.compile(r"^\d{1,2} (jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec) \d{4}, "
                         r"\d\d:\d\d utc \u00b7 ")
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
    klein = " %s " % re.sub(r"[^a-z0-9/ ]", " ", t.lower())
    for liste, name in ((WORTLISTE, "wortliste"), (ECHTZEIT, "echtzeit-wort"),
                        (FREMDE_CHAINS, "andere chain")):
        for w in liste:
            if " %s " % w in klein:
                fehler.append("%s %r in %s" % (name, w, feld))
    if "percent" in klein:
        fehler.append("'percent' statt %% in %s" % feld)
    for w in ZAHLWORTE:
        if " %s " % w in klein:
            fehler.append("zahlwort %r in %s" % (w, feld))
    if "$" in t or re.search(r"\b(usd|usdt|dollars?|price)\b", t, re.I):
        fehler.append("kurs- oder dollarangabe in %s" % feld)
    if form == 11:
        for w in MOTIV_11:
            if " %s " % w in klein:
                fehler.append("motiv %r in %s" % (w, feld))
    if form == 8:
        for w in ANGRIFF:
            if " %s " % w in klein:
                fehler.append("angriffsszenario %r in %s" % (w, feld))
    for w in ("never", "record", "highest", "lowest", "all time", "ever seen"):
        if " %s " % w in klein and not ZEITRAUM.search(t):
            fehler.append("%r ohne zeitraum in %s" % (w, feld))
    return fehler


def textpruefung(s, form):
    """Alle Regeln. Leere Liste heisst gruen; nur dann wird gerendert."""
    fehler = []
    felder = {"kopf": s["kopf"], "zahl": s["zahl"], "bedeutung": s["bedeutung"],
              "datumszeile": s["datumszeile"], "x": s["x"], "discord": s["discord"]}
    for k, v in felder.items():
        fehler += pruefe_eine(v, form, k)
    # das feld antwort ist der einzige ort mit link (Ben, 30.09.2026, v4). der
    # link selbst ist von den satzregeln ausgenommen, der rest nicht.
    lk = antwort_link(form)
    if s.get("antwort", "").count(lk) != 1:
        fehler.append("antwort traegt den link %s nicht genau einmal" % lk)
    fehler += pruefe_eine(s.get("antwort", "").replace(lk, ""), form, "antwort")
    # die antwort geht als x-antwort raus, x zaehlt jeden link als 23 zeichen
    lang = len(s.get("antwort", "").replace(lk, "x" * 23))
    if lang > 280:
        fehler.append("antwort hat %d zeichen nach x-zaehlung, erlaubt sind 280" % lang)
    zeilen = s["x"].split("\n")
    if len(zeilen) != 3:
        fehler.append("x-text hat %d zeilen, verlangt sind 3" % len(zeilen))
    else:
        if re.search(r"\d\.\d", zeilen[0]):
            fehler.append("x-zeile 1 hat eine dezimalstelle")
        if not zeilen[2].endswith("?"):
            fehler.append("x-zeile 3 endet nicht mit fragezeichen")
    if MAIL_SATZ not in s["discord"] or MAIL_SATZ not in s.get("antwort", ""):
        fehler.append("sonntagsmail-satz fehlt in discord oder antwort")
    if len(s["datumszeile"]) > DATUMSZEILE_MAX:
        fehler.append("datumszeile %d zeichen, hoechstens %d" % (len(s["datumszeile"]), DATUMSZEILE_MAX))
    if not DATUMSZEILE.match(s["datumszeile"]):
        fehler.append("datumszeile beginnt nicht mit '<tag> <mon> <jahr>, <hh:mm> utc \u00b7'")
    her = s["datumszeile"].split(" \u00b7 ")[-1]
    if not (her == SELBST or her.startswith("source ")):
        fehler.append("datumszeile endet weder auf %r noch auf 'source ...'" % SELBST)
    if "kaspalytics" in s["datumszeile"] and SELBST in s["datumszeile"]:
        fehler.append("counted by kaspa pulse neben einer kaspalytics-zahl")
    if not DATUM.search(s["x"]):
        fehler.append("x-text ohne datum")
    if len(s["x"]) >= 240:
        fehler.append("x-text hat %d zeichen, erlaubt sind unter 240" % len(s["x"]))
    if "it goes on x at %s" % X_ZEIT not in s["discord"]:
        fehler.append("discord-text ohne 'it goes on x at %s'" % X_ZEIT)
    if not re.match(r"(ja|nein|offen), ", s.get("pruefung", "")):
        fehler.append("selbstpruefung beginnt nicht mit ja oder nein")
    # "worth watching" aus dem mail-satz ist kein wert
    if form == 2 and re.search(r"\$|usd|\bworth\b(?! watching)", " ".join(felder.values()), re.I):
        fehler.append("form 2 nennt einen dollarwert")
    return fehler


# ------------------------------------------------------------ texte

# Was nur in der Wochenmail steht (Stand 30.09.2026, geprueft gegen die
# Ausgaben vom 14., 21. und 28.09.): die Bloecke "the take" und "worth
# watching" gibt es in keiner anderen Datei, weder auf kaspa-weekly.html noch
# auf index.html noch in pulse-studio. Ben nennt sie Sonntagsmail; sie geht
# montags 18:00 Berlin raus, deshalb sagt der Satz "weekly mail".
MAIL_SATZ = "the weekly take and what is worth watching next are only in our weekly mail."


def antwort_link(form):
    from utm import link
    return link("x", "reply", "form%d" % form)


def texte(s, form, messzeit):
    """X in drei Zeilen (Ben, 30.09.2026, v4): der Satz zum Nachsprechen, das
    Fenster oder die Quelle, der Haken als Frage. Die Aufloesung steht im
    Feld antwort, dem einzigen Ort mit Link. Discord bekommt Zeile 1 und 2,
    den 17:00-Satz und den Mail-Satz ohne Link."""
    s = dict(s)
    teile = [tag(messzeit.date()) + ", " + uhr(messzeit)]
    if s.get("zusatz"):
        teile.append(s["zusatz"])
    teile.append(s["herkunft"])
    s["datumszeile"] = " \u00b7 ".join(teile)
    x1 = s["x1"].rstrip(".") + "."
    x2 = s["x2"].rstrip(".") + "."
    s["x"] = "%s\n%s\n%s" % (x1, x2, s["x3"])
    s["antwort"] = "%s %s %s" % (s["aufloesung"], MAIL_SATZ, antwort_link(form))
    s["discord"] = "%s\n%s\n\nshare it first, it goes on x at %s.\n%s" % (x1, x2, X_ZEIT, MAIL_SATZ)
    return s


# ------------------------------------------------------------ rendern
# Hausschrift wie number_of_day.py. Auf dem Runner und lokal ist das
# Liberation Sans, deren Ziffern gleich breit sind.

HAUS = "'Helvetica Neue',Helvetica,Arial,sans-serif"
CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1350px;background:%s;position:relative;overflow:hidden;
  font-family:%s;-webkit-font-smoothing:antialiased;font-feature-settings:'tnum' 1}
.kopf{position:absolute;left:64px;top:56px;font-weight:700;font-size:40px;letter-spacing:5px;color:%s}
.zahl{position:absolute;left:60px;top:118px;font-weight:700;color:%s;line-height:0.86;
  letter-spacing:-5px;white-space:nowrap}
.bed{position:absolute;left:64px;right:64px;font-weight:400;font-size:44px;line-height:1.18;color:%s}
.bed.fett{font-weight:700;font-size:60px}
.datum{position:absolute;left:64px;right:64px;bottom:100px;font-weight:400;font-size:30px;
  line-height:1.3;color:%s;letter-spacing:0.3px}
.sig{position:absolute;left:64px;right:0;bottom:36px;height:44px;display:flex;align-items:center;gap:14px}
.sig img{width:34px;height:auto;display:block}
.sig span{font-weight:700;font-size:28px;letter-spacing:3px;color:%s;white-space:nowrap}
.sig svg{flex:1;height:44px;display:block}
.obj{position:absolute;left:0;top:0}
""" % (BG, HAUS, WEISS, WEISS, AK, RESTTON, AK)

# eine ekg-zacke, duenn, sonst flach. breite folgt dem flex-rest.
PULS = "M0,30 L120,30 L140,30 L152,10 L166,44 L178,4 L190,34 L200,30 L2000,30"


def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace(" utc", "\u00a0utc"))


def zahlgroesse(z):
    n = len(z)
    return 210 if n <= 6 else 180 if n <= 8 else 150 if n <= 10 else 120


# Zonen: Zahl 118 bis ~310, Objekt bis 1020, Bedeutung ab 1046,
# Datumszeile ueber der Signatur. Das Objekt hat bei allen Formen dieselbe Zone.
OBJ = (64, 350, 952, 720)


def objektzone(zg, zahl_im_objekt=False):
    x, _, w, _ = OBJ
    if zahl_im_objekt:
        return x, 150, w, 870
    y = 118 + zg * 0.86 + 50
    return x, y, w, 1020 - y


def html(s, falke):
    zg = zahlgroesse(s["zahl"])
    x, y, w, h = objektzone(zg, s.get("zahl_im_objekt"))
    if s.get("zahl_im_objekt"):
        zahl = ""
    else:
        zahl = "<div class='zahl' style='font-size:%dpx'>%s</div>" % (zg, esc(s["zahl"]))
    obj = s["objekt"](x, y, w, h)
    sig = ("<div class='sig'><img src='%s' alt=''><span>KASPA PULSE</span>"
           "<svg viewBox='0 0 900 44' preserveAspectRatio='xMinYMid slice'><path d='%s' fill='none' "
           "stroke='%s' stroke-width='3' stroke-linejoin='round' stroke-linecap='round'/></svg></div>"
           % (falke, PULS, AK))
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s</style></head><body>"
            "<div class='kopf'>%s</div>%s"
            "<svg class='obj' width='1080' height='1350' viewBox='0 0 1080 1350' "
            "font-family=\"%s\">%s</svg>"
            "<div class='bed%s' style='top:1046px'>%s</div>"
            "<div class='datum'>%s</div>%s</body></html>") % (
        CSS, esc(s["kopf"]), zahl, HAUS.replace("'", ""), obj,
        " fett" if s.get("bedeutung_fett") else "", esc(s["bedeutung"]), esc(s["datumszeile"]), sig)


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
        kollision = pg.evaluate("""() => {
          const r = s => { const e = document.querySelector(s); return e ? e.getBoundingClientRect() : null; };
          const bed = r('.bed'), dat = r('.datum'), sig = r('.sig'), zahl = r('.zahl');
          const f = [];
          if (bed && dat && bed.bottom > dat.top - 6) f.push('bedeutung stoesst an die datumszeile');
          if (dat && sig && dat.bottom > sig.top + 4) f.push('datumszeile stoesst an die signatur');
          if (bed && bed.top < 1040) f.push('bedeutung zu hoch');
          // jede textzeile einzeln: rechts hoechstens bis 1080 - 48 px
          for (const [sel, name] of [['.bed', 'bedeutung'], ['.datum', 'datumszeile'], ['.kopf', 'kopf']]) {
            const e = document.querySelector(sel);
            if (!e) continue;
            const rg = document.createRange(); rg.selectNodeContents(e);
            const rs = [...rg.getClientRects()];
            const rechts = Math.max(...rs.map(q => q.right));
            const zeilen = new Set(rs.map(q => Math.round(q.top))).size;
            window.__mass = (window.__mass || []).concat([name + ' ' + zeilen + ' zeile(n), rechts ' + Math.round(rechts) + ' px']);
            if (rechts > 1080 - 48) f.push(name + ' laeuft rechts hinaus (' + Math.round(rechts) + ' px)');
          }
          return f; }""")
        print("layout, " + "; ".join(pg.evaluate("window.__mass || []")))
        if kollision:
            b.close()
            raise Stop("layout, %s. text kuerzen" % ", ".join(kollision))
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

# Kollision mit der Zahl des Tages (Ben, 30.09.2026, v5). Welche Kennzahl
# zeigt number_of_day heute, und welche Formen tragen dieselbe? Die Zahl des
# Tages entsteht erst um 08:42 UTC, die Tagesgrafik um 05:30. Deshalb liest die
# Rotation den heutigen Eintrag aus data/number-of-day-log.json, und wenn es
# ihn noch nicht gibt, rechnet sie die Wahl mit number_of_day_data.choose()
# selbst vorab, mit denselben Live-Daten.
NOTD_KENNZAHL = {
    "cut_today": "reward_cut", "cut_countdown": "reward_cut",
    "mined_left": "mined", "whale_weight": "entity_x",
    "emission_vs_btc": "emission", "blocks_per_day": "blocks",
    "hashrate_move": "hashrate", "hashrate_consequence": "hashrate",
    "tvl_move": "tvl", "weekly_line": "price", "sats_divergence": "price",
}
FORM_KENNZAHL = {
    1: set(),                  # montags fest; bei hashrate nimmt messen_1 die adressen
    2: {"entity_x"}, 3: {"reward_cut"}, 4: {"blocks"}, 5: {"emission"},
    6: {"blocks"}, 7: set(), 8: {"hashrate"}, 9: {"addresses"}, 10: {"mined"},
    11: {"dormant"},
}
GESPERRTE_KENNZAHLEN = set()   # vom zeitplanlauf gesetzt, messen_1 liest es


def notd_heute(now, log_pfad=None):
    """(kandidat, woher) der Zahl des Tages fuer den UTC-Tag von now, oder
    (None, grund), wenn weder Log noch Vorabwahl etwas liefern."""
    import number_of_day_data as nod
    log = nod.load_json(log_pfad or nod.LOG_PATH, [])
    heute = now.date().isoformat()
    for r in reversed(log or []):
        if str(r.get("date")) == heute and r.get("candidate"):
            return r["candidate"], "aus dem log"
    try:
        name, _, _ = nod.choose(nod.build_context(now.timestamp()), log)
        return name, "vorab gerechnet"
    except Exception as exc:                        # noqa: BLE001
        return None, "vorabwahl gescheitert (%s)" % exc


def kollision(kandidat):
    """Formen, die dieselbe Kennzahl tragen wie die Zahl des Tages."""
    k = NOTD_KENNZAHL.get(kandidat)
    return {f for f, ks in FORM_KENNZAHL.items() if k and k in ks}


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
              "DISCORD\n```\n%s\n```\nX, %d zeichen\n```\n%s\n```\nANTWORT unter dem X-Post\n```\n%s\n```\n"
              "selbstpruefung, wuerde ein halter das reposten, um anzugeben? %s" % (
                  s["datum"], form, FORMEN[form][0], grund, X_ZEIT, s["discord"], len(s["x"]),
                  s["x"], s["antwort"], s["pruefung"]))
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

def seite_bauen(form, werte, messzeit, log=None):
    _, _, vorlage = FORMEN[form]
    s = vorlage(werte, messzeit)
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


def log_eintragen(log, eintrag):
    """Ein Eintrag je Tag. Liefert ein Handlauf nach dem Cron noch einmal,
    zaehlt die spaetere Lieferung, sonst steht der Tag doppelt in der
    Rotation (Ben, 01.10.2026: der Handlauf schreibt das Log wie der Cron)."""
    laeufe = [e for e in log.get("laeufe", []) if e["datum"] != eintrag["datum"]]
    laeufe.append(eintrag)
    log["laeufe"] = laeufe
    return log


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
            notd, woher = notd_heute(now)
            ausgeschl = kollision(notd)
            GESPERRTE_KENNZAHLEN.clear()
            if notd in NOTD_KENNZAHL:
                GESPERRTE_KENNZAHLEN.add(NOTD_KENNZAHL[notd])
            print("zahl des tages %s (%s), uebersprungen %s" % (notd, woher, sorted(ausgeschl) or "keine"))
            m = None
            while m is None:
                verf = FREIGESCHALTET - ausgeschl
                if not verf:
                    raise SystemExit("ABBRUCH keine form heute belegbar")
                form, grund = waehle_form(heute, log, ereignis_cut, ereignis_ex, verf)
                if notd:
                    grund += ", zahl des tages %s (%s)%s" % (
                        notd, woher, ", uebersprungen %s" % sorted(ausgeschl) if ausgeschl else "")
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
        "DISCORD\n%s\n\nX (%d zeichen)\n%s\n\nANTWORT unter dem X-Post\n%s\n\nSELBSTPRUEFUNG\n"
        "wuerde ein halter das reposten, um anzugeben? %s\n" % (
            s["discord"], len(s["x"]), s["x"], s["antwort"], s["pruefung"]), encoding="utf-8")
    (out / (png.stem + ".json")).write_text(json.dumps(m, ensure_ascii=False, indent=1),
                                            encoding="utf-8")
    print("form %d (%s), %s\n%s\n%s" % (form, grund, png, vpng, (out / (png.stem + ".txt")).read_text()))
    if a.senden:
        hook = os.environ.get("DISCORD_WEBHOOK_OPS", "")
        if not hook:
            raise SystemExit("ABBRUCH kein DISCORD_WEBHOOK_OPS, nichts geschickt")
        ops_senden(png, vpng, s, form, grund, hook)
    if a.log_schreiben:
        log_eintragen(log, {"datum": heute.isoformat(), "form": form,
                            "grund": grund, "messzeit_utc": m["messzeit_utc"]})
        LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


# ------------------------------------------------------------ selbsttest

FAKE_NOW = dt.datetime(2026, 9, 29, 14, 8, 21, tzinfo=dt.timezone.utc)
_T8 = ["2026-09-%02d" % d for d in range(21, 29)]
FAKE = {
    1: {"kandidaten": [{"was": "holders", "tage": _T8,
                        "reihe": [796711, 797000, 797300, 797800, 798200, 798600, 799128, 799332]},
                       {"was": "hashrate", "tage": _T8,
                        "reihe": [332.5, 335.1, 338.0, 340.2, 339.9, 341.7, 356.6, 342.9]}]},
    2: {"circ": 27728255870.82, "bal": 1521367293.63,
        "bewegungen": [{"zeit_utc": "2026-09-28T12:26:15+00:00", "tx": "65f1", "netto": -6377600.99},
                       {"zeit_utc": "2026-09-29T08:03:36+00:00", "tx": "5e66", "netto": 1769298.16}]},
    3: {"cur": 2.18268, "nxt": 2.06017, "nxt_ts": 1791170144,
        "stufen": [2.60, 2.4499, 2.3124, 2.1827, 2.1827, 2.1827, 2.06017]},
    4: {"bps": 9.750743698561694, "daa": 552706543},
    5: {"tage": 30, "von": "2026-08-30", "bis": "2026-09-28", "fees": 73020.31,
        "emission": 57213980.47},
    6: {"daa": 552706543},
    7: {"eintrag": {"frage": "how many addresses hold at least 100 KAS?", "zahl": "293,501",
                    "antwort": "addresses held at least 100 KAS", "name": "@PLATZHALTER",
                    "stand": "2026-09-28", "offen": True,
                    "quelle": "source kaspalytics address thresholds",
                    "objekt": {"art": "zwei", "a": {"wert": 558856, "text": "at least 1 KAS, 558,856"},
                               "b": {"wert": 293501, "text": "at least 100 KAS, 293,501"}}}},
    8: {"ph": 344.5, "reihe": [300 + i * 0.5 for i in range(90)], "von": "2026-07-01",
        "bis": "2026-09-28", "neu": 1885832.45, "neu_tag": "2026-09-28"},
    9: {"d1": "2026-09-28", "d0": "2026-09-21",
        "tage": {"2026-09-%02d" % d: v for d, v in zip(range(21, 29), (
            293153, 293190, 293241, 293260, 293302, 293371, 293430, 293501))}},
    10: {"circ": 27728257200.07, "max": 28704035605.0},
    11: {"stichtag": "2026-09-28", "p1": 50.57806049611307, "p2": 25.751732530896824},
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
    ok("form 2 ereignis bei 1.77M in 24 h", s["kopf"] == "ENTITY X MOVED")
    ok("andere chain faellt", bool(probe("48 blocks for bitcoin in the same time")))
    ok("echtzeit-wort faellt", bool(probe("sealed by proof of work, around the clock")))
    ok("echtzeit live faellt", bool(probe("tracked live")))
    s4 = seite_bauen(4, FAKE[4], FAKE_NOW, log)
    ok("form 4 heartbeat aus der blockrate", s4["bedeutung"] == "10 blocks for every heartbeat while you slept"
       and "resting pulse 60 assumed" in s4["datumszeile"])
    s9 = seite_bauen(9, FAKE[9], FAKE_NOW, log)
    ok("kaspalytics-form ohne counted by", "counted by" not in s9["datumszeile"]
       and "source kaspalytics" in s9["datumszeile"])
    s8 = seite_bauen(8, FAKE[8], FAKE_NOW, log)
    ok("form 8 ohne around the clock", "around the clock" not in json.dumps(s8, default=str))
    ok("eine rechnung fuer neue kas", abs(neue_kas("2026-09-28", "2026-09-28")[0]
                                          - emission_am_tag("2026-09-28")) < 1e-6)
    ok("form 2 ohne dollar", "$" not in json.dumps(s, default=str))
    ok("form 2, 'worth' mit wert faellt weiter",
       any("dollarwert" in f for f in textpruefung(dict(s, bedeutung="a wallet worth millions"), 2)))
    # objekt-regeln vom 30.09.2026
    ok("form 2, 1.77M von 1.52B ist unter 3 px, kein streifen", not s["streifen"]
       and "strip" not in s["bedeutung"] and "1.77M KAS came in" in s["bedeutung"])
    gross = dict(FAKE[2], bewegungen=[{"zeit_utc": "2026-09-29T08:03:36+00:00", "tx": "x",
                                       "netto": 300e6}])
    s2g = seite_bauen(2, gross, FAKE_NOW, log)
    ok("form 2, 300M gibt einen streifen", s2g["streifen"] and "bright strip" in s2g["bedeutung"])
    o9 = s9["objekt"](*objektzone(zahlgroesse(s9["zahl"])))
    ok("form 9, ein punkt je neuer adresse (348)", o9.count("<circle") == 348)
    ok("form 9, sieben spalten beschriftet", o9.count("<text") == 7)
    fall = dict(FAKE[9], tage=dict(FAKE[9]["tage"], **{"2026-09-23": 293031}))
    s9f = seite_bauen(9, fall, FAKE_NOW, log)
    o9f = s9f["objekt"](*objektzone(zahlgroesse(s9f["zahl"])))
    ok("form 9, tag mit rueckgang unter der linie im resteton",
       o9f.count("fill='%s'/>" % RESTTON) >= 159 and "below the line" in s9f["datumszeile"])
    s1 = seite_bauen(1, FAKE[1], FAKE_NOW, log)
    o1 = s1["objekt"](*objektzone(zahlgroesse(s1["zahl"])))
    ok("form 1, zwei saeulen, 21 sep und 28 sep beschriftet, die rechte hell",
       o1.count("<rect") == 2 and ">21 sep<" in o1 and ">28 sep<" in o1
       and o1.index(RESTTON) < o1.index(AK))
    # v4, texte (Ben, 30.09.2026)
    for f in sorted(FAKE):
        sf = seite_bauen(f, FAKE[f], FAKE_NOW, log)
        z = sf["x"].split("\n")
        ok("form %d, x in drei zeilen, zeile 1 ohne dezimalstelle, zeile 3 eine frage" % f,
           len(z) == 3 and not re.search(r"\d\.\d", z[0]) and z[2].endswith("?"))
        ok("form %d, link nur im feld antwort" % f,
           all("kaspapulse" not in sf[k] and "http" not in sf[k]
               for k in ("x", "discord", "bedeutung", "datumszeile", "kopf", "zahl"))
           and sf["antwort"].endswith(antwort_link(f))
           and "utm_source=x&utm_medium=reply&utm_campaign=form%d" % f in sf["antwort"])
        ok("form %d, discord mit 17:00 und mail-satz ohne link" % f,
           sf["discord"].split("\n")[:2] == z[:2] and sf["discord"].endswith(MAIL_SATZ))
    kaputt = dict(seite_bauen(4, FAKE[4], FAKE_NOW, log))
    kaputt["x"] = "kaspa added 281,000.5 blocks.\n8 hours, 29 sep.\nhow many."
    fk = textpruefung(kaputt, 4)
    ok("dezimalstelle in zeile 1 faellt", any("dezimalstelle" in f for f in fk))
    ok("zeile 3 ohne fragezeichen faellt", any("fragezeichen" in f for f in fk))
    kaputt = dict(seite_bauen(4, FAKE[4], FAKE_NOW, log))
    kaputt["discord"] += " " + antwort_link(4)
    ok("link im discord-text faellt", bool(textpruefung(kaputt, 4)))
    kaputt = dict(seite_bauen(4, FAKE[4], FAKE_NOW, log), antwort="about 10 per heartbeat.")
    ok("antwort ohne link faellt", any("link" in f for f in textpruefung(kaputt, 4)))
    lang = dict(seite_bauen(4, FAKE[4], FAKE_NOW, log))
    lang["antwort"] = "a" * 260 + " " + antwort_link(4)
    ok("antwort ueber 280 nach x-zaehlung faellt", any("280" in f for f in textpruefung(lang, 4)))
    ok("form 8, eine hashrate, als tageswert gekennzeichnet",
       "daily hashrate 28 sep" in s8["datumszeile"] and "measured" not in json.dumps(s8, default=str)
       and abs(FAKE[8]["ph"] - FAKE[8]["reihe"][-1]) < 1e-9)
    o4 = s4["objekt"](*objektzone(zahlgroesse(s4["zahl"])))
    ok("form 4, zwei balken ab null, bloecke hell, beide beschriftet, keine ekg-linie",
       o4.count("<rect") == 2 and "<path" not in o4 and ">your heartbeats, 28,800<" in o4
       and ">blocks, 281,000<" in o4 and o4.index(RESTTON) < o4.index(AK))
    s6 = seite_bauen(6, FAKE[6], FAKE_NOW, log)
    o6 = s6["objekt"](*objektzone(zahlgroesse(s6["zahl"])))
    ok("form 6, lineal vor und nach crescendo", ">may 2025<" in o6 and "80% of them since may 2025"
       in s6["bedeutung"])
    s7 = seite_bauen(7, FAKE[7], FAKE_NOW, log)
    o7 = s7["objekt"](*objektzone(zahlgroesse(s7["zahl"])))
    ok("form 7, zwei groessen im selben massstab", o7.count("<rect") == 2)
    # gegen was? jede form zeigt eine zweite groesse, einen rest oder vorher/nachher
    for f in sorted(FAKE):
        sf = seite_bauen(f, FAKE[f], FAKE_NOW, log)
        of = sf["objekt"](*objektzone(zahlgroesse(sf["zahl"])))
        farben = {c for c in (AK, RESTTON, AK_DUNKEL) if c in of}
        ok("form %d, gegen was, mindestens zwei toene im objekt" % f, len(farben) >= 2)
    # form 3 (Ben, 02.10.2026): die beiden letzten stufen tragen ihren wert,
    # die datumszeile bleibt kurz
    s3 = seite_bauen(3, FAKE[3], FAKE_NOW, log)
    o3 = s3["objekt"](*objektzone(zahlgroesse(s3["zahl"]), True))
    st3 = FAKE[3]["stufen"]
    ok("form 3, helle stufe und die davor beschriftet",
       (">%.2f</text>" % st3[-1]) in o3 and (">%.2f</text>" % st3[-2]) in o3)
    ok("form 3, datumszeile ohne die werte, hoechstens eine zeile lang",
       len(s3["datumszeile"]) <= 70 and "after" not in s3["datumszeile"])
    ok("datumszeile ueber %d zeichen wird abgelehnt" % DATUMSZEILE_MAX,
       any("hoechstens %d" % DATUMSZEILE_MAX in f for f in
           textpruefung(dict(s3, datumszeile=s3["datumszeile"] + " ·" + " x" * 80), 3)))
    # kollision mit der zahl des tages
    ok("zahl des tages blocks_per_day sperrt form 4 und 6", kollision("blocks_per_day") == {4, 6})
    ok("zahl des tages hashrate sperrt form 8", kollision("hashrate_move") == {8})
    ok("zahl des tages kurs sperrt nichts", kollision("weekly_line") == set())
    woche = {"laeufe": [{"datum": "2026-10-06", "form": 2}, {"datum": "2026-10-07", "form": 3}]}
    tag_x = dt.date(2026, 10, 8)
    ohne, _ = waehle_form(tag_x, woche)
    mit, _ = waehle_form(tag_x, woche, verfuegbar=FREIGESCHALTET - kollision("blocks_per_day"))
    ok("heute waere form 4 dran, mit blocks_per_day kommt eine andere", ohne == 4 and mit not in (4, 6))
    lg2 = {"laeufe": [{"datum": "2026-10-01", "form": 3}]}
    log_eintragen(lg2, {"datum": "2026-10-01", "form": 2})
    log_eintragen(lg2, {"datum": "2026-10-02", "form": 4})
    ok("handlauf nach dem cron, ein eintrag je tag, die spaetere lieferung zaehlt",
       [(e["datum"], e["form"]) for e in lg2["laeufe"]] == [("2026-10-01", 2), ("2026-10-02", 4)])
    tmp = Path("/tmp/tagesgrafik-selbsttest-notd.json")
    tmp.write_text(json.dumps([{"date": "2026-09-30", "candidate": "blocks_per_day"}]))
    ok("zahl des tages aus dem log gelesen",
       notd_heute(dt.datetime(2026, 9, 30, 5, 30, tzinfo=dt.timezone.utc), tmp) == ("blocks_per_day", "aus dem log"))
    tmp.unlink()
    GESPERRTE_KENNZAHLEN.add("hashrate")
    alt_reihe = globals()["m_kl_reihe"]
    globals()["m_kl_reihe"] = lambda pfad, name, art: {"2026-09-%02d" % d: 796000.0 + d for d in range(20, 30)}
    try:
        w1 = messen_1(FAKE_NOW)
        ok("montags mit hashrate als zahl des tages nimmt form 1 die adressen",
           [k["was"] for k in w1["kandidaten"]] == ["holders"])
    finally:
        globals()["m_kl_reihe"] = alt_reihe
        GESPERRTE_KENNZAHLEN.clear()
    ok("form 4, blockrate ueber 10 minuten", BLOCKRATE_SEK == 600)
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
    ok("form 13 (nodes) gesperrt", 13 not in FREIGESCHALTET and 12 not in FORMEN)
    s11 = seite_bauen(11, FAKE[11], FAKE_NOW, log)
    o11 = s11["objekt"](*objektzone(zahlgroesse(s11["zahl"])))
    ok("form 11, kopf, zahl und bedeutung", s11["kopf"] == "SLEEPING COINS" and s11["zahl"] == "50.58%"
       and s11["bedeutung"] == "half of all KAS has not moved in a year")
    ok("form 11, balken hell, darin dunkel, rest im dritten ton",
       o11.count("<rect") == 6 and AK in o11 and AK_DUNKEL in o11 and RESTTON in o11)
    ok("form 11, datumszeile nur mit quelle, ohne counted by",
       s11["datumszeile"].endswith("source kaspalytics, age estimated by daa score, 28 sep 2026")
       and SELBST not in s11["datumszeile"])
    ok("form 11, antwort mit der 2-jahres-zahl und form11", "25.75%" in s11["antwort"]
       and s11["antwort"].endswith(antwort_link(11)) and "utm_campaign=form11" in s11["antwort"])
    for wort in ("dormant", "hodl", "diamond hands"):
        ok("form 11, %r faellt" % wort, bool(pruefe_eine("the %s coins stay put" % wort, 11)))
    ok("form 11, motiv faellt", bool(pruefe_eine("holders are waiting deliberately", 11)))
    ok("form 11 laeuft in der rotation", 11 in FREIGESCHALTET)
    alt_reihe = globals()["m_kl_reihe"]
    globals()["m_kl_reihe"] = lambda pfad, name, art: (
        {"2026-09-28": 50.58, "2026-09-29": 50.6, "2026-09-30": 50.53} if "1year" in pfad
        else {"2026-09-28": 25.75, "2026-09-29": 25.77, "2026-09-30": 25.79})
    try:
        w11 = messen_11(dt.datetime(2026, 9, 30, 18, 26, tzinfo=dt.timezone.utc))
        ok("form 11 liest nie den laufenden tag", w11["stichtag"] == "2026-09-29")
    finally:
        globals()["m_kl_reihe"] = alt_reihe
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
