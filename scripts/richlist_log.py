#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""richlist_log.py, der woechentliche Schnappschuss der Rangliste.

STUFE 1, die Uhr starten. Ab dem 24.09.2026 wird jede Woche einmal
festgehalten, wer wie viel haelt und welche Adressen ein Label tragen.
Veroeffentlicht wird davon nichts: kein Post, keine Seite, kein Eintrag im
Dashboard. Die Reihe soll erst lang werden, bevor jemand sie liest.

    GET https://api.kaspa.org/addresses/top     die rangliste
    GET https://api.kaspa.org/addresses/names   das label-verzeichnis
    GET https://api.kaspa.org/info/coinsupply   circ_supply, dieselbe
                                                quelle wie dashboard_weekly

DIE ZWEI ERSTEN SIND EXPERIMENTELL
Beide sind ausdruecklich als "EXPECT BREAKING CHANGES" markiert und lassen
sich auf der Gegenseite per Umgebungsvariable abschalten, dann antworten
sie mit http 503. Deshalb gilt hier Bot-Regel 10 ohne Ausnahme: jede
Antwort faellt durch eine Formpruefung und ein Plausibilitaetsfenster, und
wenn irgendetwas nicht passt, bricht der Lauf ab und schreibt NICHTS. Eine
Luecke im Log ist ehrlich, eine falsche Zeile nicht.

DIE EINHEIT, GEMESSEN UND NICHT ANGENOMMEN
Am 24.09.2026 im Runner nachgesehen (Lauf 36016758837):

    /addresses/top      rang 0 "amount": 1524392806
    /addresses/{adr}/balance        152439280677607262

Die Rangliste nennt ganze KAS, abgeschnitten, der Kontostand nennt Sompi.
Dieselbe API, zwei Einheiten. Wer eine davon voraussetzt, liegt bei der
anderen um den Faktor hundert Millionen daneben. Deshalb wird Rang 0 jede
Woche gegen den Kontostand von Entity X gestellt, den wir ueber den
stabilen /balance-Endpunkt kennen. Weicht er um mehr als ein Prozent ab,
bricht der Lauf ab. Passt er nur, wenn man durch 1e8 teilt, hat die Quelle
ihre Einheit gewechselt, und auch dann bricht er ab und sagt genau das.

WO DIE ROHDATEN LIEGEN
Die Rangliste hat 10.000 Eintraege und ist 1,1 MB gross. In einer einzigen
Logdatei, die jede Woche neu geschrieben wird, wuerde das Repo quadratisch
wachsen: Woche n schreibt n MB, nach einem Jahr laegen weit ueber ein
Gigabyte an Versionen in der Historie. Deshalb:

    data/richlist-log.json                  eine zeile je woche, klein
    data/richlist/JJJJ-MM-TT.top.json.gz    die rangliste, byte fuer byte
    data/richlist/JJJJ-MM-TT.names.json     das verzeichnis, byte fuer byte

Jede Zeile nennt beide Dateien und ihre sha256 ueber die ROHEN Bytes, so
wie sie von der API kamen. Entpackt ergibt die .gz-Datei exakt die Antwort.

EINE ZEILE JE WOCHE
Schluessel ist die ISO-Woche. Laeuft der Job in derselben Woche zweimal,
etwa von Hand am Donnerstag und planmaessig am Sonntag, ersetzt der
spaetere Lauf den frueheren, und die ersetzten Rohdateien verschwinden
mit. Die Zeile nennt dann, wessen Stelle sie eingenommen hat.

    python3 scripts/richlist_log.py             holen, pruefen, schreiben
    python3 scripts/richlist_log.py --trocken   holen, pruefen, nichts schreiben
    python3 scripts/richlist_log.py --selftest  ohne netz
"""

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LOG = os.path.join(REPO, "data", "richlist-log.json")
ROH_ORDNER = os.path.join(REPO, "data", "richlist")

API = "https://api.kaspa.org"
PFAD_TOP = "/addresses/top"
PFAD_NAMES = "/addresses/names"
PFAD_SUPPLY = "/info/coinsupply"
ENTITY_X = "kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a"
PFAD_EX = "/addresses/%s/balance" % ENTITY_X
EX_STATE = os.path.join(HERE, "entity_x_state.json")   # rueckfall, siehe referenz()

SOMPI = 100_000_000
TIMEOUT = 60
VERSUCHE = 3

# Bot-Regel 10, die fenster. Beobachtet am 24.09.2026 in klammern.
FENSTER_RANGLISTE = (100, 100_000)       # (10.000 eintraege)
FENSTER_NAMES = (1, 10_000)              # (138 labels)
FENSTER_UMLAUF_KAS = (2.0e10, 2.9e10)    # (27.718.894.232, max 28.704.035.605)
TOLERANZ_EINHEIT = 0.01                  # rang 0 gegen entity x, ein prozent
MAX_ALTER_TAGE = 8                       # zeitstempel der rangliste
MAX_ZUKUNFT_STUNDEN = 1


class Abbruch(Exception):
    """Etwas passt nicht. Der Lauf schreibt dann nichts."""


# ------------------------------------------------------------------ holen

def hole_roh(pfad):
    """Rohe Bytes einer Antwort. Drei Versuche, dann ehrlich scheitern.
    503 heisst: die Gegenseite hat den Endpunkt abgeschaltet. Das wird
    beim Namen genannt und nicht wiederholt."""
    url = API + pfad
    letzter = None
    for _ in range(VERSUCHE):
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/json",
                "User-Agent": "kaspa-pulse-bot (+https://kaspapulse.com)",
            })
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 503:
                raise Abbruch("%s antwortet 503, der endpunkt ist auf der "
                              "gegenseite abgeschaltet" % pfad)
            letzter = "http %s" % e.code
        except Exception as exc:      # noqa: BLE001
            letzter = exc
    raise Abbruch("%s nicht erreichbar, %s" % (pfad, letzter))


def als_json(roh, pfad):
    try:
        return json.loads(roh.decode("utf-8"))
    except Exception as exc:          # noqa: BLE001
        raise Abbruch("%s liefert kein JSON, %s" % (pfad, exc))


# ------------------------------------------------------------------ pruefen

def pruefe_rangliste(d):
    """Die Form der Rangliste, wie sie am 24.09.2026 war:

        [ {"timestamp": <ms>, "ranking": [ {"rank": 0, "address": "kaspa:...",
                                            "amount": <ganze KAS>}, ... ]} ]

    Weicht die Form ab, ist das eine Formaenderung auf der Gegenseite, und
    dann wird nicht geraten, wie sie gemeint sein koennte."""
    if not isinstance(d, list) or len(d) != 1 or not isinstance(d[0], dict):
        raise Abbruch("rangliste hat nicht mehr die form [ {timestamp, ranking} ]")
    kopf = d[0]
    if "timestamp" not in kopf or "ranking" not in kopf:
        raise Abbruch("rangliste ohne timestamp oder ranking, schluessel sind %s"
                      % sorted(kopf))
    ts, liste = kopf["timestamp"], kopf["ranking"]
    if not isinstance(ts, int):
        raise Abbruch("timestamp ist keine ganze zahl, sondern %s" % type(ts).__name__)
    if not isinstance(liste, list):
        raise Abbruch("ranking ist keine liste")
    lo, hi = FENSTER_RANGLISTE
    if not lo <= len(liste) <= hi:
        raise Abbruch("rangliste hat %d eintraege, erwartet %d bis %d"
                      % (len(liste), lo, hi))
    vorher = None
    for i, e in enumerate(liste):
        if not isinstance(e, dict):
            raise Abbruch("eintrag %d ist kein objekt" % i)
        if e.get("rank") != i:
            raise Abbruch("eintrag %d traegt rank %r" % (i, e.get("rank")))
        adr, betrag = e.get("address"), e.get("amount")
        if not isinstance(adr, str) or not adr.startswith("kaspa:"):
            raise Abbruch("eintrag %d hat keine kaspa-adresse" % i)
        if not isinstance(betrag, int) or betrag < 0:
            raise Abbruch("eintrag %d hat keinen betrag als ganze zahl >= 0" % i)
        if vorher is not None and betrag > vorher:
            raise Abbruch("rangliste nicht absteigend, rang %d haelt mehr als rang %d"
                          % (i, i - 1))
        vorher = betrag
    return ts, liste


def pruefe_names(d):
    if not isinstance(d, list):
        raise Abbruch("label-verzeichnis ist keine liste")
    lo, hi = FENSTER_NAMES
    if not lo <= len(d) <= hi:
        raise Abbruch("label-verzeichnis hat %d eintraege, erwartet %d bis %d"
                      % (len(d), lo, hi))
    zuordnung = {}
    for i, e in enumerate(d):
        if not isinstance(e, dict):
            raise Abbruch("label %d ist kein objekt" % i)
        adr, name = e.get("address"), e.get("name")
        if not isinstance(adr, str) or not adr.startswith("kaspa:"):
            raise Abbruch("label %d hat keine kaspa-adresse" % i)
        if not isinstance(name, str) or not name.strip():
            raise Abbruch("label %d hat keinen namen" % i)
        zuordnung[adr] = name
    return zuordnung


def pruefe_umlauf(d):
    try:
        sompi = int(d["circulatingSupply"])
    except Exception as exc:          # noqa: BLE001
        raise Abbruch("coinsupply ohne circulatingSupply, %s" % exc)
    kas = sompi / SOMPI
    lo, hi = FENSTER_UMLAUF_KAS
    if not lo <= kas <= hi:
        raise Abbruch("circ_supply %.0f KAS liegt ausserhalb %.2g bis %.2g" % (kas, lo, hi))
    return sompi, kas


def pruefe_einheit(liste, referenz_kas):
    """Rang 0 muss Entity X sein, und sein Betrag muss auf ein Prozent an
    unserer Entity-X-Zahl liegen. Die Richtung des Fehlers wird benannt:
    passt der Betrag erst nach Division durch 1e8, stehen die Betraege
    jetzt in Sompi, und das ist eine Einheitenaenderung, keine Rundung."""
    erster = liste[0]
    if erster["address"] != ENTITY_X:
        raise Abbruch("rang 0 ist nicht mehr entity x, sondern %s. ohne diesen "
                      "anker laesst sich die einheit nicht pruefen" % erster["address"])
    betrag = erster["amount"]
    abw = betrag / referenz_kas - 1
    if abs(abw) <= TOLERANZ_EINHEIT:
        return abw
    if abs(betrag / SOMPI / referenz_kas - 1) <= TOLERANZ_EINHEIT:
        raise Abbruch("einheit gewechselt: rang 0 passt erst durch 1e8 geteilt. "
                      "die rangliste nennt jetzt sompi statt KAS")
    raise Abbruch("rang 0 haelt %d, entity x steht bei %.0f KAS, abweichung %+.2f%%, "
                  "erlaubt sind %.0f%%" % (betrag, referenz_kas, abw * 100,
                                           TOLERANZ_EINHEIT * 100))


def pruefe_zeit(ts_ms, jetzt):
    t = dt.datetime.fromtimestamp(ts_ms / 1000, dt.timezone.utc)
    if t > jetzt + dt.timedelta(hours=MAX_ZUKUNFT_STUNDEN):
        raise Abbruch("zeitstempel %s liegt in der zukunft" % t.isoformat())
    if t < jetzt - dt.timedelta(days=MAX_ALTER_TAGE):
        raise Abbruch("zeitstempel %s ist aelter als %d tage, die rangliste "
                      "wird nicht mehr nachgefuehrt" % (t.isoformat(), MAX_ALTER_TAGE))
    return t


def referenz(holer):
    """Unsere Entity-X-Zahl. Zuerst live ueber /balance, den stabilen
    Endpunkt, den auch entity-x.html und entity_x_alert.py lesen (Sompi).
    Faellt der aus, der letzte Stand aus scripts/entity_x_state.json.
    Entity X bewegt sich um rund 0,03 Prozent am Tag; ein Stand von einer
    Woche liegt damit weit innerhalb der Toleranz."""
    try:
        d = als_json(holer(PFAD_EX), PFAD_EX)
        if d.get("address") != ENTITY_X:
            raise Abbruch("balance-antwort fuer die falsche adresse")
        return int(d["balance"]) / SOMPI, "live /addresses/{entity x}/balance"
    except Abbruch as exc:
        live_fehler = str(exc)
    except Exception as exc:          # noqa: BLE001
        live_fehler = str(exc)
    try:
        with open(EX_STATE, encoding="utf-8") as fh:
            return float(json.load(fh)["balance_kas"]), \
                "scripts/entity_x_state.json (live fiel aus: %s)" % live_fehler
    except Exception as exc:          # noqa: BLE001
        raise Abbruch("keine entity-x-zahl zum vergleichen, live: %s, datei: %s"
                      % (live_fehler, exc))


# ------------------------------------------------------------------ bauen

def schnappschuss(holer=None, jetzt=None):
    """Alles holen und pruefen. Gibt (zeile, roh_top, roh_names) zurueck
    oder wirft Abbruch. Geschrieben wird hier nichts."""
    holer = holer or hole_roh
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc).replace(microsecond=0)

    roh_top = holer(PFAD_TOP)
    ts_ms, liste = pruefe_rangliste(als_json(roh_top, PFAD_TOP))
    roh_names = holer(PFAD_NAMES)
    labels = pruefe_names(als_json(roh_names, PFAD_NAMES))
    umlauf_sompi, umlauf_kas = pruefe_umlauf(als_json(holer(PFAD_SUPPLY), PFAD_SUPPLY))
    ref_kas, ref_quelle = referenz(holer)
    abw = pruefe_einheit(liste, ref_kas)
    t = pruefe_zeit(ts_ms, jetzt)

    summe = sum(e["amount"] for e in liste)
    if summe > umlauf_kas * 1.001:
        raise Abbruch("die rangliste haelt %.0f KAS, mehr als im umlauf sind (%.0f)"
                      % (summe, umlauf_kas))

    mit_label = sum(1 for e in liste if e["address"] in labels)
    iso = t.isocalendar()
    datum = t.date().isoformat()
    zeile = {
        "woche": "%d-W%02d" % (iso[0], iso[1]),
        "datum": datum,
        "timestamp": ts_ms,
        "timestamp_utc": t.isoformat(),
        "abgerufen_utc": jetzt.isoformat(),
        "adressen": len(liste),
        "mit_label": mit_label,
        "labels_im_verzeichnis": len(labels),
        "summe_rangliste_kas": summe,
        "circ_supply_kas": round(umlauf_kas),
        "circ_supply_sompi": str(umlauf_sompi),
        "anteil_rangliste_pct": round(100.0 * summe / umlauf_kas, 4),
        "einheit": "ganze KAS, abgeschnitten",
        "einheitspruefung": {
            "rang0_adresse": liste[0]["address"],
            "rang0_betrag": liste[0]["amount"],
            "referenz_kas": round(ref_kas, 2),
            "referenz_quelle": ref_quelle,
            # die abweichung in KAS ist lesbarer als in prozent: am 24.09.
            # waren es -0,78 KAS, genau die nachkommastelle, die die
            # rangliste abschneidet. in prozent waere das -0,00000005.
            "abweichung_kas": round(liste[0]["amount"] - ref_kas, 2),
            "abweichung_pct": round(abw * 100, 6) + 0.0 if abs(abw) >= 5e-9 else 0.0,
            "toleranz_pct": TOLERANZ_EINHEIT * 100,
        },
        "roh": {
            "top": "data/richlist/%s.top.json.gz" % datum,
            "names": "data/richlist/%s.names.json" % datum,
            "top_bytes": len(roh_top),
            "names_bytes": len(roh_names),
            "top_sha256": hashlib.sha256(roh_top).hexdigest(),
            "names_sha256": hashlib.sha256(roh_names).hexdigest(),
        },
    }
    return zeile, roh_top, roh_names, liste, labels


def lade(pfad):
    if not os.path.exists(pfad):
        return {"wochen": []}
    with open(pfad, encoding="utf-8") as fh:
        return json.load(fh)


def eintragen(zeile, roh_top, roh_names, log_pfad=LOG, repo=REPO):
    """Die Zeile ins Log, die Rohdaten daneben. Eine Zeile je ISO-Woche; ein
    spaeterer Lauf derselben Woche ersetzt den frueheren samt Rohdateien."""
    log = lade(log_pfad)
    wochen = log.get("wochen", [])
    alt = next((w for w in wochen if w["woche"] == zeile["woche"]), None)
    if alt is not None:
        zeile["ersetzt"] = alt["abgerufen_utc"]
        for k in ("top", "names"):
            p = os.path.join(repo, alt["roh"][k])
            if alt["roh"][k] != zeile["roh"][k] and os.path.exists(p):
                os.remove(p)
        wochen = [w for w in wochen if w["woche"] != zeile["woche"]]
    wochen.append(zeile)
    wochen.sort(key=lambda w: w["woche"])

    os.makedirs(os.path.join(repo, "data", "richlist"), exist_ok=True)
    # mtime=0, damit dieselben bytes dieselbe datei ergeben
    with open(os.path.join(repo, zeile["roh"]["top"]), "wb") as fh:
        fh.write(gzip.compress(roh_top, compresslevel=9, mtime=0))
    with open(os.path.join(repo, zeile["roh"]["names"]), "wb") as fh:
        fh.write(roh_names)

    log["quelle"] = "api.kaspa.org, experimentell"
    log["endpunkte"] = {"top": API + PFAD_TOP, "names": API + PFAD_NAMES,
                        "circ_supply": API + PFAD_SUPPLY,
                        "referenz_entity_x": API + PFAD_EX}
    log["hinweis"] = ("stufe 1, nur archiv. nichts davon ist veroeffentlicht. "
                      "die rangliste nennt ganze KAS, abgeschnitten; der "
                      "kontostand-endpunkt nennt sompi. rohdaten liegen je woche "
                      "unter data/richlist/, byte fuer byte, sha256 in der zeile.")
    log["wochen"] = wochen
    os.makedirs(os.path.dirname(log_pfad), exist_ok=True)
    with open(log_pfad, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return alt is not None


# ------------------------------------------------------------------ selftest

EX_SOMPI_2409 = 152439280677607262          # /balance am 24.09.2026, echt
EX_KAS_2109 = 1523915192                    # Bens zahl vom 21.09.2026
TS_2409 = 1790259907000                     # rangliste am 24.09.2026, echt
JETZT_2409 = dt.datetime(2026, 9, 24, 15, 0, tzinfo=dt.timezone.utc)


def _stub(**aenderung):
    """Die Antworten vom 24.09.2026 in klein. aenderung verbiegt einzelne
    Teile, damit jeder Abbruchgrund einzeln geprueft werden kann."""
    ranking = [{"rank": 0, "address": ENTITY_X, "amount": 1524392806},
               {"rank": 1, "address": "kaspa:qpzpfw" + "a" * 50, "amount": 845900885},
               {"rank": 2, "address": "kaspa:qrvum2" + "b" * 50, "amount": 759425168}]
    # der rest klein und absteigend, zusammen weit unter dem umlauf
    ranking += [{"rank": i, "address": "kaspa:q%05d" % i + "c" * 50,
                 "amount": 10_000_000 - i * 1000} for i in range(3, 150)]
    top = [{"timestamp": TS_2409, "ranking": ranking}]
    names = [{"address": "kaspa:qrvum2" + "b" * 50, "name": "Bybit"},
             {"address": "kaspa:qqywx2" + "d" * 50, "name": "Bitget"}]
    supply = {"circulatingSupply": "2771889423183447277", "maxSupply": "2870403560500000000"}
    balance = {"address": ENTITY_X, "balance": EX_SOMPI_2409}
    antworten = {PFAD_TOP: top, PFAD_NAMES: names, PFAD_SUPPLY: supply, PFAD_EX: balance}
    antworten.update(aenderung.get("json", {}))

    def holer(pfad):
        if pfad in aenderung.get("fehler", {}):
            raise aenderung["fehler"][pfad]
        return json.dumps(antworten[pfad]).encode("utf-8")
    return holer


def run_selftest():
    fails = []

    def check(name, ist, soll):
        if ist != soll:
            fails.append("%s\n    ist  %r\n    soll %r" % (name, ist, soll))

    def bricht_ab(name, holer, wort, jetzt=JETZT_2409):
        try:
            schnappschuss(holer=holer, jetzt=jetzt)
            fails.append("%s\n    kein abbruch" % name)
        except Abbruch as exc:
            if wort not in str(exc):
                fails.append("%s\n    abbruch, aber '%s' fehlt in: %s" % (name, wort, exc))

    # ---- die einheitspruefung, festgehalten an den echten zahlen

    zeile, _, _, liste, labels = schnappschuss(holer=_stub(), jetzt=JETZT_2409)
    check("24.09., rang 0 gegen live /balance passt", zeile["einheitspruefung"]["rang0_betrag"],
          1524392806)
    check("die abweichung ist die abgeschnittene nachkommastelle",
          zeile["einheitspruefung"]["abweichung_kas"], -0.78)
    check("und in prozent steht keine negative null",
          str(zeile["einheitspruefung"]["abweichung_pct"]), "0.0")
    check("die einheit steht in der zeile", zeile["einheit"], "ganze KAS, abgeschnitten")

    # Bens zahl vom 21.09. als referenz: drei tage alt, 0,03 prozent weg,
    # muss durchgehen
    abw = pruefe_einheit(liste, EX_KAS_2109)
    check("21.09. als referenz liegt im prozent", abs(abw) < TOLERANZ_EINHEIT, True)
    check("und zwar um rund 0,03 prozent", round(abw * 100, 2), 0.03)

    # nennt die rangliste ploetzlich sompi, faellt das als einheitswechsel auf
    sompi_ranking = [dict(e, amount=e["amount"] * SOMPI) for e in liste]
    try:
        pruefe_einheit(sompi_ranking, EX_SOMPI_2409 / SOMPI)
        fails.append("sompi in der rangliste\n    kein abbruch")
    except Abbruch as exc:
        check("sompi in der rangliste heisst einheitswechsel", "einheit gewechselt" in str(exc), True)

    # zwei prozent daneben ist zu viel
    try:
        pruefe_einheit(liste, 1524392806 / 1.02)
        fails.append("zwei prozent daneben\n    kein abbruch")
    except Abbruch as exc:
        check("zwei prozent daneben bricht ab", "abweichung" in str(exc), True)
    # knapp unter einem prozent geht durch
    check("0,9 prozent geht durch",
          abs(pruefe_einheit(liste, 1524392806 / 1.009)) < TOLERANZ_EINHEIT, True)

    # ---- die form, jede abweichung ein abbruch

    top = json.loads(_stub()(PFAD_TOP))
    bricht_ab("503 auf der rangliste",
              _stub(fehler={PFAD_TOP: Abbruch("/addresses/top antwortet 503, der endpunkt ist "
                                              "auf der gegenseite abgeschaltet")}), "503")
    bricht_ab("leere rangliste",
              _stub(json={PFAD_TOP: [{"timestamp": TS_2409, "ranking": []}]}), "eintraege")
    bricht_ab("leere antwort", _stub(json={PFAD_TOP: []}), "form")
    bricht_ab("ranking fehlt",
              _stub(json={PFAD_TOP: [{"timestamp": TS_2409, "rows": top[0]["ranking"]}]}),
              "ranking")
    bricht_ab("betrag als text",
              _stub(json={PFAD_TOP: [{"timestamp": TS_2409, "ranking":
                    [dict(e, amount=str(e["amount"])) for e in top[0]["ranking"]]}]}),
              "betrag")
    kaputt = json.loads(json.dumps(top))
    kaputt[0]["ranking"][5]["amount"] = 999999999
    bricht_ab("nicht absteigend", _stub(json={PFAD_TOP: kaputt}), "absteigend")
    fremd = json.loads(json.dumps(top))
    fremd[0]["ranking"][0]["address"] = "kaspa:qanderer" + "e" * 50
    bricht_ab("rang 0 ist nicht entity x", _stub(json={PFAD_TOP: fremd}), "nicht mehr entity x")
    bricht_ab("label ohne namen",
              _stub(json={PFAD_NAMES: [{"address": ENTITY_X, "name": ""}]}), "namen")
    bricht_ab("umlauf unplausibel",
              _stub(json={PFAD_SUPPLY: {"circulatingSupply": "5"}}), "circ_supply")
    bricht_ab("zeitstempel veraltet", _stub(),
              "aelter", jetzt=JETZT_2409 + dt.timedelta(days=9))
    bricht_ab("zeitstempel in der zukunft", _stub(),
              "zukunft", jetzt=JETZT_2409 - dt.timedelta(hours=3))
    groesser = json.loads(json.dumps(top))
    groesser[0]["ranking"][1]["amount"] = 1524392806
    groesser[0]["ranking"].append({"rank": 150, "address": "kaspa:qriese" + "f" * 50,
                                   "amount": 0})
    for e in groesser[0]["ranking"][2:150]:
        e["amount"] = 1524392806
    bricht_ab("mehr in der rangliste als im umlauf", _stub(json={PFAD_TOP: groesser}),
              "mehr als im umlauf")

    # faellt /balance aus, springt der gespeicherte stand ein
    ref, quelle = referenz(_stub(fehler={PFAD_EX: Abbruch("503")}))
    check("rueckfall auf entity_x_state.json", "entity_x_state.json" in quelle, True)
    check("der rueckfall liefert eine zahl", ref > 1e9, True)

    # ---- das log: eine zeile je woche, rohdaten byte fuer byte

    tmp = tempfile.mkdtemp()
    log = os.path.join(tmp, "data", "richlist-log.json")
    zeile, roh_top, roh_names, _, _ = schnappschuss(holer=_stub(), jetzt=JETZT_2409)
    check("erster eintrag ersetzt nichts", eintragen(zeile, roh_top, roh_names, log, tmp), False)
    gz = os.path.join(tmp, zeile["roh"]["top"])
    with open(gz, "rb") as fh:
        zurueck = gzip.decompress(fh.read())
    check("die rangliste kommt byte fuer byte zurueck", zurueck, roh_top)
    check("und ihr sha256 stimmt", hashlib.sha256(zurueck).hexdigest(),
          zeile["roh"]["top_sha256"])
    with open(os.path.join(tmp, zeile["roh"]["names"]), "rb") as fh:
        check("das verzeichnis byte fuer byte", fh.read(), roh_names)
    check("woche 39", lade(log)["wochen"][0]["woche"], "2026-W39")

    # derselbe lauf am sonntag derselben woche ersetzt die zeile
    sonntag = JETZT_2409 + dt.timedelta(days=3)
    ts_so = TS_2409 + 3 * 86400 * 1000
    top_so = json.loads(json.dumps(top))
    top_so[0]["timestamp"] = ts_so
    z2, r2, n2, _, _ = schnappschuss(holer=_stub(json={PFAD_TOP: top_so}), jetzt=sonntag)
    check("sonntag ersetzt donnerstag", eintragen(z2, r2, n2, log, tmp), True)
    wochen = lade(log)["wochen"]
    check("eine zeile je woche", len(wochen), 1)
    check("die zeile nennt, wen sie ersetzt hat", wochen[0]["ersetzt"],
          JETZT_2409.isoformat())
    check("die alte rohdatei ist weg", os.path.exists(gz), False)

    # die naechste woche haengt an
    naechste = sonntag + dt.timedelta(days=7)
    top_n = json.loads(json.dumps(top))
    top_n[0]["timestamp"] = ts_so + 7 * 86400 * 1000
    z3, r3, n3, _, _ = schnappschuss(holer=_stub(json={PFAD_TOP: top_n}), jetzt=naechste)
    eintragen(z3, r3, n3, log, tmp)
    check("zwei wochen, zwei zeilen", [w["woche"] for w in lade(log)["wochen"]],
          ["2026-W39", "2026-W40"])

    # bei abbruch wird nichts geschrieben
    vorher = open(log, encoding="utf-8").read()
    try:
        schnappschuss(holer=_stub(json={PFAD_TOP: []}), jetzt=JETZT_2409)
    except Abbruch:
        pass
    check("ein abbruch laesst das log unberuehrt", open(log, encoding="utf-8").read(), vorher)

    if fails:
        print("selftest FEHLGESCHLAGEN")
        for f in fails:
            print("  " + f)
        return 1
    print("selftest ok, 34 faelle")
    return 0


# ------------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trocken", action="store_true",
                    help="holen und pruefen, nichts schreiben")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return run_selftest()

    try:
        zeile, roh_top, roh_names, liste, labels = schnappschuss()
    except Abbruch as exc:
        print("ABBRUCH, nichts geschrieben: %s" % exc)
        return 1

    e = zeile["einheitspruefung"]
    print("richlist, schnappschuss vom %s" % zeile["timestamp_utc"])
    print("  adressen         %d" % zeile["adressen"])
    print("  mit label        %d  (von %d labels im verzeichnis)"
          % (zeile["mit_label"], zeile["labels_im_verzeichnis"]))
    print("  einheit          %s" % zeile["einheit"])
    print("  rang 0           %s" % e["rang0_adresse"])
    print("                   %d KAS gegen %.2f KAS (%s)"
          % (e["rang0_betrag"], e["referenz_kas"], e["referenz_quelle"]))
    print("                   abweichung %+.2f KAS (%+.6f%%), erlaubt %.0f%%"
          % (e["abweichung_kas"], e["abweichung_pct"], e["toleranz_pct"]))
    print("  rangliste haelt  %d KAS, %.2f%% des umlaufs (%d KAS)"
          % (zeile["summe_rangliste_kas"], zeile["anteil_rangliste_pct"],
             zeile["circ_supply_kas"]))
    print("\n  die ersten zehn:")
    for x in liste[:10]:
        print("    %2d  %15s KAS  %s" % (x["rank"], "{:,}".format(x["amount"]),
                                      labels.get(x["address"], "-")))
    print("\n  gelabelt in der rangliste, nach rang:")
    for x in liste:
        if x["address"] in labels:
            print("    %5d  %15s KAS  %s" % (x["rank"], "{:,}".format(x["amount"]),
                                          labels[x["address"]]))

    if a.trocken:
        print("\ntrocken, nichts geschrieben. die zeile waere:")
        print(json.dumps(zeile, indent=2, ensure_ascii=False))
        return 0
    ersetzt = eintragen(zeile, roh_top, roh_names)
    print("\n%s, woche %s" % ("ersetzt" if ersetzt else "eingetragen", zeile["woche"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
