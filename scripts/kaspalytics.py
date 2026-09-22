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

  1. Bezugspunkt ist der MONTAG dieser woche, nicht heute. Die wochenzeile
     im dashboard traegt immer das montagsdatum, also gehoert in sie der
     letzte volle tag VOR diesem montag, also der sonntag. Wer stattdessen
     ab heute rechnet, schreibt am dienstag dienstagszahlen in die
     montagszeile, und die seite widerspricht dem post, der schon raus ist.
     Genau das ist am 18.08. passiert, einmal.
  2. Wir lesen nie den laufenden tag. Der ist angebrochen und war schon
     zweimal die ursache fuer einen sprung, den es nie gab.
  3. Jede Zahl faellt durch ein Plausibilitaetsfenster. Lieber ein Feld
     leer als ein falsches. Ein leeres Feld zeigt auf der Seite einen
     Strich, und ein Strich ist ehrlich.
  4. Faellt eine Quelle aus, bleiben die anderen fuenf trotzdem stehen.
  5. tps zaehlt NUR Standardtransaktionen und NUR als Wochenmittel.
     Korrektur vom 16.09.2026, siehe unten.
  6. Eine Tagessumme und eine Momentaufnahme tragen ihr Datum verschieden.
     Korrektur vom 22.09.2026, siehe unten.

DER MITTERNACHTSSCHLUPF, KORREKTUR VOM 22.09.2026
Drei der sechs Felder sind keine Tagessummen, sondern Momentaufnahmen:
holder_addr, holders und exchange_kas. Kaspalytics misst sie einmal am Tag
und trifft dabei die Mitternacht nur ungefaehr:

    2026-09-06T23:59:59.410Z   791880
    2026-09-08T00:00:01.573Z   792179
    2026-09-08T23:59:59.713Z   786714
    2026-09-10T00:00:02.216Z   786880

Wer davon nur das Datum nimmt, bekommt eine Reihe mit Loechern und
Doppeltagen: der 07.09. fehlt, der 08.09. kommt zweimal. In allen drei
Reihen betraf das am 22.09.2026 je 76 Kalendertage. Wo ein Tag doppelt
war, gewann der erste Treffer der Schleife, also die aeltere Messung; wo
er fehlte, fiel der Leser stillschweigend auf den Vortag zurueck. Die
Montagszeile trug dadurch bis zu einen Tag alte Staende, ohne dass es
irgendwo sichtbar wurde.

Ab dem 22.09. gilt deshalb: faellt eine Momentaufnahme in die erste Stunde
nach Mitternacht, ist sie der Stand vom Ende des VORTAGS und wird dort
eingetragen. Tagessummen bleiben unberuehrt, ihr Stempel steht ohnehin auf
00:00:00.000 des gezaehlten Tages. Faellt ein Stichtag trotzdem zweimal an,
gewinnt die spaetere Messung. Dieselbe Rechnung steckt in
scripts/covenants_log.py, dort fuer die Covenant-UTXO-Reihe.

Eine Abweichung zu covenants_log.py ist Absicht. Dort wird pauschal eine
Stunde vorgestellt und ein Tag abgezogen, weil dort JEDE Marke an der
Mitternacht liegt. Diese drei Reihen reichen bis August 2023 zurueck und
wurden bis Anfang 2026 gegen 09:00 UTC gemessen, 196 Punkte je Reihe.
Ein pauschaler Abzug haette die gesamte alte Haelfte um einen Tag
verschoben. Deshalb greift die Korrektur hier nur in der ersten Stunde
nach Mitternacht; fuer die Covenant-Reihe liefern beide Fassungen
Zeichen fuer Zeichen dasselbe.

DIE TPS-KORREKTUR VOM 16.09.2026
Bis zum 14.09. war tps die Summe aus "Standard" UND "Coinbase" eines
EINZELNEN Tages, geteilt durch 86400. Am Zaehltag 06.09. ergab das 2,83.
Kaspalytics selbst meldet fuer dieselbe Woche 1,38. Beides stimmt, gezaehlt
wird nur nicht dasselbe:

  Coinbase ist die Auszahlung, die JEDER akzeptierte Block an sich selbst
  schreibt. Am 16.08. waren das 127.440 Stueck an einem Tag, also rund
  1,48 je Sekunde, gegen 75.050 Standardtransaktionen, also 0,87. Die
  Coinbase-Zahl misst, wie schnell die Kette laeuft, nicht wie sehr sie
  benutzt wird. Auf unserer eigenen Seite steht ueber der Kachel "real
  network usage" und "spam filtered out" - mit der Kettenauszahlung darin
  widerspricht die Zahl ihrer eigenen Beschriftung.

  Dazu war es EIN Tag, kein Wochenmittel. Ein Spitzentag liest hoch, und
  niemand sah ihm an, dass er ein Spitzentag war.

Ab dem 16.09. gilt deshalb: tps ist das MITTEL der sieben vollen Tage vor
dem Wochenanker, nur "Standard". Der hoechste Einzeltag im Fenster wird als
tps_peak mit Datum mitgeliefert; damit steht der Spitzentag kuenftig dabei,
statt sich als Wochenzahl auszugeben.

Die alten Werte der Reihe (0,74 bis 2,83) sind auf der alten Grundlage
gemessen und mit den neuen NICHT vergleichbar. Sie werden nicht
umgerechnet: wir haben die Tagesaufteilung frueherer Wochen nicht
gespeichert, und eine gerechnete Zahl als gemessene auszugeben ist genau
das, was diese Datei sonst verhindert. Der Bruch steht in
data/weekly-notes.md.

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

# feld -> (pfad, reihe, umrechnung, art)
# die reihe ist der "label"-eintrag im datasets-array. Preis ignorieren wir,
# den holen wir woanders sauberer.
#
# die ART entscheidet, wie der zeitstempel gelesen wird, siehe stichtag():
#   "fluss"   tagessumme, der stempel traegt den gezaehlten tag
#   "bestand" momentaufnahme, der stempel faellt um mitternacht
QUELLEN = {
    "active_addr":  ("transactions/accepted/addresses/all", ["Addresses"], "int", "fluss"),
    "holder_addr":  ("address/count/meaningful-balance", ["Addresses"], "int", "bestand"),
    "holders":      ("supply/inactive?minAge=1year", ["CSPERCENT"], "pct", "bestand"),
    "exchange_kas": ("supply/exchange-holdings", ["Balance"], "int", "bestand"),
    "covenant_tx":  ("covenants/transactions", ["Transactions"], "int", "fluss"),
    # tps ist die einzige rechnung: akzeptierte STANDARD-transaktionen je
    # sekunde, gemittelt ueber die sieben vollen tage vor dem wochenanker.
    # Coinbase bleibt draussen (siehe Kopf), und die tps-kachel auf
    # kaspa.stream bleibt es auch, die zaehlt die bloecke mit und steht
    # deshalb bei elf statt bei eins.
    "tps":          ("transactions/accepted/count", ["Standard"], "tps", "fluss"),
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
FENSTER_TAGE = 7        # wochenmittel, dasselbe fenster, das kaspalytics zeigt


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
    """aus dem zeitstempel den kalendertag in UTC, ohne jede korrektur."""
    s = str(label).replace("Z", "").split("T")[0]
    return dt.date.fromisoformat(s)


def zeit_von(label):
    """aus dem zeitstempel den zeitpunkt in UTC, mit uhrzeit."""
    s = str(label).replace("Z", "+00:00")
    t = dt.datetime.fromisoformat(s)
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t.astimezone(dt.timezone.utc)


def stichtag(label, art):
    """Welchen Kalendertag dieser Messpunkt traegt. Siehe Kopf, Abschnitt
    MITTERNACHTSSCHLUPF.

    fluss     die tagessumme traegt den tag, den sie zaehlt. der stempel
              steht auf 00:00:00.000 dieses tages, das datum stimmt also
              unveraendert.
    bestand   eine momentaufnahme. faellt sie in die erste stunde nach
              mitternacht, ist sie der stand vom ende des VORTAGS und
              gehoert dorthin. alles andere behaelt seinen tag.

    Die Bedingung ist bewusst an die erste Stunde geknuepft und nicht
    pauschal an "einen Tag zurueck". Die Versorgungsreihen wurden bis
    Anfang 2026 gegen 09:00 UTC gemessen, 196 Punkte je Reihe liegen dort;
    ein pauschaler Abzug wuerde die gesamte alte Haelfte der Reihe um einen
    Tag verschieben, ohne dass es je jemandem auffiele.
    """
    if art != "bestand":
        return tag_von(label)
    t = zeit_von(label)
    if t.hour == 0:
        return t.date() - dt.timedelta(days=1)
    return t.date()


def reihe(daten, name):
    for d in daten.get("datasets") or []:
        if str(d.get("label", "")).strip().lower() == name.strip().lower():
            return d.get("data") or []
    raise RuntimeError("reihe %s nicht gefunden" % name)


def letzter_voller(daten, namen, heute, art="fluss"):
    """
    Der juengste eintrag, dessen tag VOR heute liegt und in dem jede
    gefragte reihe einen wert hat. Die labels sind nicht garantiert
    sortiert, deshalb wird nach datum gesucht und nicht nach position.

    Landen zwei messpunkte auf demselben stichtag, gewinnt der spaetere
    zeitstempel. Vorher gewann der erste, den die schleife sah: am 06.09.
    standen in der holder-reihe 791.880 und 792.098 auf demselben
    kalendertag, und die aeltere der beiden messungen ging in die
    montagszeile.
    """
    labels = daten.get("labels") or []
    reihen = [reihe(daten, n) for n in namen]
    best_i, best_tag, best_zeit = None, None, None
    for i, lab in enumerate(labels):
        try:
            tag = stichtag(lab, art)
            zeit = zeit_von(lab)
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
        if best_tag is None or tag > best_tag or (tag == best_tag and zeit > best_zeit):
            best_i, best_tag, best_zeit = i, tag, zeit
    if best_i is None:
        raise RuntimeError("kein vollstaendiger tag vor %s" % heute)
    return best_tag, [float(r[best_i]) for r in reihen]


def fenster(daten, namen, heute, n=FENSTER_TAGE, art="fluss"):
    """Die letzten n vollen Tage VOR heute, als Liste (tag, werte).
    Fehlende Tage werden uebersprungen, nicht geraten; gibt es weniger als
    die Haelfte, ist das Fenster unbrauchbar und die Funktion scheitert.
    Faellt ein tag zweimal an, gewinnt auch hier die spaetere messung."""
    labels = daten.get("labels") or []
    reihen = [reihe(daten, x) for x in namen]
    nach_tag = {}
    for i, lab in enumerate(labels):
        try:
            tag = stichtag(lab, art)
            zeit = zeit_von(lab)
        except ValueError:
            continue
        if tag >= heute or (heute - tag).days > n:
            continue
        w = []
        for r in reihen:
            if i >= len(r) or r[i] is None:
                w = None
                break
            w.append(float(r[i]))
        if w is None:
            continue
        if tag not in nach_tag or zeit > nach_tag[tag][0]:
            nach_tag[tag] = (zeit, w)
    treffer = [(tag, w) for tag, (_, w) in nach_tag.items()]
    treffer.sort(key=lambda x: x[0])
    if len(treffer) * 2 < n:
        raise RuntimeError("nur %d von %d tagen vor %s vollstaendig"
                           % (len(treffer), n, heute))
    return treffer


def rechne(art, werte):
    if art == "tps":
        return round(sum(werte) / SEKUNDEN_TAG, 2)
    if art == "pct":
        return round(werte[0], 2)
    return int(round(werte[0]))


def plausibel(feld, wert):
    lo, hi = FENSTER[feld]
    return lo <= wert <= hi


def wochenanker(tag):
    """
    Der montag dieser woche. Die wochenzeile im dashboard traegt immer
    dieses datum, und alles was in sie hineingeschrieben wird, muss sich
    darauf beziehen. Dadurch liefert der holer am montag, am dienstag und
    am freitag dieselben zahlen fuer dieselbe zeile.
    """
    return tag - dt.timedelta(days=tag.weekday())


def hole_feld(feld, heute=None, holer=None):
    """EIN feld holen, mit denselben regeln wie sammle(): wochenanker,
    nie der laufende tag, stichtag nach art, plausibilitaetsfenster.

    Dafuer gibt es diesen weg: scripts/weekly_numbers.py braucht seit dem
    22.09.2026 nur holder_addr und soll nicht sechs abfragen ausloesen, um
    eine zahl zu bekommen. Gibt (wert, tag) zurueck und scheitert laut,
    wenn der wert nicht zu holen oder nicht plausibel ist. Ein stiller
    rueckfall waere hier falsch: der aufrufer hat einen override, und der
    hilft ihm nur, wenn er von dem problem erfaehrt.
    """
    if feld not in QUELLEN:
        raise RuntimeError("unbekanntes feld %s" % feld)
    pfad, namen, rechenart, messart = QUELLEN[feld]
    if rechenart == "tps":
        raise RuntimeError("tps geht nur ueber sammle(), es ist ein wochenmittel")
    heute = wochenanker(heute or dt.datetime.now(dt.timezone.utc).date())
    daten = (holer or hole)(pfad)
    tag, roh = letzter_voller(daten, namen, heute, art=messart)
    wert = rechne(rechenart, roh)
    if not plausibel(feld, wert):
        raise RuntimeError("%s = %s liegt ausserhalb des fensters" % (feld, wert))
    return wert, tag


def sammle(heute=None, holer=None):
    """alle sechs felder. gibt werte, tage und probleme zurueck."""
    heute = heute or dt.datetime.now(dt.timezone.utc).date()
    heute = wochenanker(heute)
    holer = holer or hole
    werte, tage, probleme = {}, {}, []
    # rechenart sagt, WIE der wert umgerechnet wird (int, pct, tps),
    # messart sagt, WELCHEN tag der zeitstempel traegt (fluss, bestand).
    for feld, (pfad, namen, rechenart, messart) in QUELLEN.items():
        try:
            daten = holer(pfad)
            if rechenart == "tps":
                # Wochenmittel statt Einzeltag (Korrektur 16.09.2026, Kopf).
                # Der Spitzentag faellt dabei nicht unter den Tisch, er wird
                # benannt.
                tage_werte = fenster(daten, namen, heute, art=messart)
                tps = [(t, sum(w) / SEKUNDEN_TAG) for t, w in tage_werte]
                v = round(sum(x for _, x in tps) / len(tps), 2)
                hoch_tag, hoch = max(tps, key=lambda x: x[1])
                werte["tps_peak"] = round(hoch, 2)
                werte["tps_peak_date"] = str(hoch_tag)
                werte["tps_days"] = len(tps)
                tag = "%s..%s" % (tps[0][0], tps[-1][0])
            else:
                tag, roh = letzter_voller(daten, namen, heute, art=messart)
                v = rechne(rechenart, roh)
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
    """zehn tage. sieben davon (10.08. bis 16.08.) sind das tps-fenster vor
    dem wochenanker montag 17.08.; die letzten zwei tage liegen dahinter und
    duerfen nie mitgezaehlt werden."""
    labels = ["2026-08-%02dT00:00:00.000Z" % d for d in range(9, 19)]

    # Die Bestandsreihen tragen ihre Marken so, wie die echte Quelle sie
    # traegt: mal 23:59:5x des tages, mal 00:00:0x des naechsten. Index i
    # gehoert in beiden faellen zum 9.+i august, und genau das muss
    # stichtag() herausrechnen.
    labels_bestand = [
        ("2026-08-%02dT23:59:59.400Z" % (9 + i) if i % 2 == 0
         else "2026-08-%02dT00:00:02.100Z" % (10 + i))
        for i in range(10)
    ]

    def bau(paare, marken=None):
        return {"labels": marken or labels,
                "datasets": [{"label": k, "data": v} for k, v in paare]}

    # index          9      10     11     12     13     14     15     16     17     18
    if pfad.startswith("transactions/accepted/addresses"):
        return bau([("Addresses", [6800, 6850, 6900, 6950, 7000, 7020, 7050, 7100, 6960, 3200]),
                    ("Price", [1] * 10)])
    if pfad.startswith("transactions/accepted/count"):
        # das fenster 10.08. bis 16.08. mittelt auf 60480 standard am tag,
        # also genau 0,70 je sekunde; der 16.08. ist mit 75050 der spitzentag.
        return bau([("Standard", [50000, 52000, 54000, 56000, 58000, 60000, 68310, 75050,
                                  30000, 30000]),
                    ("Coinbase", [118000, 119000, 120000, 121000, 122000, 123000, 125000,
                                  127440, 50000, 50000]),
                    ("Price", [1] * 10)])
    if pfad.startswith("address/count"):
        return bau([("Price", [1] * 10),
                    ("Addresses", [788000, 788200, 788400, 788600, 788800, 789000,
                                   789200, 789500, 789980, 790100])],
                   labels_bestand)
    if pfad.startswith("supply/inactive"):
        return bau([("Price", [1] * 10),
                    ("CSPERCENT", [50.7, 50.72, 50.75, 50.78, 50.8, 50.84, 50.88, 50.9,
                                   50.95, 50.96])],
                   labels_bestand)
    if pfad.startswith("supply/exchange-holdings"):
        return bau([("Balance", [3.88e9, 3.89e9, 3.90e9, 3.90e9, 3.91e9, 3.91e9,
                                 3.92e9, 3.93e9, 3.94e9, 3.94e9]),
                    ("Price", [1] * 10)], labels_bestand)
    if pfad.startswith("covenants/transactions"):
        return bau([("Transactions", [900, 950, 980, 1000, 1050, 1100, 1200, 454, 450, 1133]),
                    ("Price", [1] * 10)])
    raise RuntimeError("unbekannter pfad im stub")


def _i(daten, tag):
    """index eines tages im stub. die tests zeigen auf den TAG, nicht auf
    eine position; sonst zerlegt jede laengere reihe die testfaelle."""
    return [str(tag_von(x)) for x in daten["labels"]].index(tag)


def run_selftest():
    fails = []

    def check(name, got, want):
        if got != want:
            fails.append("%s\n    ist  %r\n    soll %r" % (name, got, want))

    # dienstag. der bezugspunkt ist trotzdem montag der 17., gelesen wird
    # der letzte volle tag davor, also sonntag der 16.
    werte, tage, probleme = sammle(heute=dt.date(2026, 8, 18), holer=_stub)
    check("active addresses", werte["active_addr"], 7100)
    check("holder adressen", werte["holder_addr"], 789500)
    check("ruhender anteil", werte["holders"], 50.9)
    check("boersenbestand", werte["exchange_kas"], 3930000000)
    check("covenants", werte["covenant_tx"], 454)
    # NUR "Standard", und als mittel der sieben tage 10.08. bis 16.08.
    fenster_std = [52000, 54000, 56000, 58000, 60000, 68310, 75050]
    check("tps ist das wochenmittel der standardreihe", werte["tps"],
          round(sum(fenster_std) / len(fenster_std) / 86400, 2))
    check("sieben tage im fenster", werte["tps_days"], 7)
    check("spitzentag steht dabei", werte["tps_peak"], round(75050 / 86400, 2))
    check("spitzentag mit datum", werte["tps_peak_date"], "2026-08-16")
    check("das fenster steht als spanne im tagesfeld", tage["tps"], "2026-08-10..2026-08-16")
    # der spitzentag liegt ueber dem mittel, und genau deshalb steht er dabei
    check("spitzentag ueber dem mittel", werte["tps_peak"] > werte["tps"], True)
    # die coinbase-reihe darf die zahl nicht mehr anheben
    check("coinbase zaehlt nicht mehr mit", werte["tps"] < 1.0, True)
    check("gelesener tag", tage["active_addr"], "2026-08-16")
    check("keine probleme", probleme, [])

    # derselbe wochentag-test. montag, mittwoch und freitag muessen
    # dieselbe zahl fuer dieselbe zeile liefern, sonst widerspricht die
    # seite mitten in der woche dem post, der schon raus ist.
    for tag, name in [(dt.date(2026, 8, 17), "montag"),
                      (dt.date(2026, 8, 19), "mittwoch"),
                      (dt.date(2026, 8, 21), "freitag")]:
        w, t, _ = sammle(heute=tag, holer=_stub)
        check("%s liest denselben tag" % name, t["active_addr"], "2026-08-16")
        check("%s liest denselben wert" % name, w["active_addr"], 7100)
    check("wochenanker", str(wochenanker(dt.date(2026, 8, 21))), "2026-08-17")

    # ein loch in der reihe faellt auf den vortag zurueck statt abzubrechen
    def loch(pfad):
        d = _stub(pfad)
        if pfad.startswith("covenants"):
            d["datasets"][0]["data"][_i(d, "2026-08-16")] = None
        return d
    w2, t2, _ = sammle(heute=dt.date(2026, 8, 18), holer=loch)
    check("luecke faellt auf den vortag", w2["covenant_tx"], 1200)
    check("und nennt den richtigen tag", t2["covenant_tx"], "2026-08-15")

    # unplausibler wert wird verworfen, nicht gemeldet
    def kaputt(pfad):
        d = _stub(pfad)
        if pfad.startswith("supply/inactive"):
            d["datasets"][1]["data"][_i(d, "2026-08-16")] = 4200.0
        return d
    w3, _, p3 = sammle(heute=dt.date(2026, 8, 18), holer=kaputt)
    check("unplausibel wird verworfen", w3["holders"], None)
    check("und steht als problem drin", len(p3), 1)

    # eine tote quelle laesst die anderen leben
    def tot(pfad):
        if pfad.startswith("supply/exchange-holdings"):
            raise RuntimeError("503")
        return _stub(pfad)
    w4, _, p4 = sammle(heute=dt.date(2026, 8, 18), holer=tot)
    check("tote quelle, feld leer", w4["exchange_kas"], None)
    check("tote quelle, rest steht", w4["active_addr"], 7100)
    check("tote quelle, ein problem", len(p4), 1)

    # ------------------------------------------------ einzelabruf
    # scripts/weekly_numbers.py holt sich holder_addr hierueber
    w_e, t_e = hole_feld("holder_addr", heute=dt.date(2026, 8, 18), holer=_stub)
    check("einzelabruf liefert den wert", w_e, 789500)
    check("einzelabruf liefert den tag", str(t_e), "2026-08-16")
    w_e2, _ = hole_feld("exchange_kas", heute=dt.date(2026, 8, 18), holer=_stub)
    check("einzelabruf auch fuer den boersenbestand", w_e2, 3930000000)

    # unplausibel scheitert laut, statt still etwas zurueckzugeben
    def kaputt_einzel(pfad):
        d = json.loads(json.dumps(_stub(pfad)))
        if pfad.startswith("address/count"):
            d["datasets"][1]["data"] = [9e9] * 10
        return d
    try:
        hole_feld("holder_addr", heute=dt.date(2026, 8, 18), holer=kaputt_einzel)
        check("einzelabruf scheitert bei unplausibel", True, False)
    except RuntimeError:
        check("einzelabruf scheitert bei unplausibel", True, True)
    try:
        hole_feld("tps", heute=dt.date(2026, 8, 18), holer=_stub)
        check("tps geht nicht einzeln", True, False)
    except RuntimeError:
        check("tps geht nicht einzeln", True, True)

    # ------------------------------------------------ mitternachtsschlupf
    # Korrektur vom 22.09.2026. Die faelle hier sind keine erfundenen
    # beispiele: die marken stammen eins zu eins aus der holder-reihe,
    # gelesen im runner am 22.09. (lauf 35707239828).

    # eine tagessumme bleibt unberuehrt, auch wenn ihr stempel auf
    # mitternacht steht. genau das tut er naemlich immer.
    check("tagessumme behaelt ihren tag",
          str(stichtag("2026-09-21T00:00:00.000Z", "fluss")), "2026-09-21")
    # eine momentaufnahme kurz VOR mitternacht gehoert diesem tag
    check("23:59:59 gehoert dem tag, der endet",
          str(stichtag("2026-09-06T23:59:59.410Z", "bestand")), "2026-09-06")
    # eine momentaufnahme kurz NACH mitternacht gehoert dem vortag
    check("00:00:01 gehoert dem vortag",
          str(stichtag("2026-09-08T00:00:01.573Z", "bestand")), "2026-09-07")
    check("00:00:02 auch",
          str(stichtag("2026-09-10T00:00:02.216Z", "bestand")), "2026-09-09")
    # die alte messzeit gegen 09:00 UTC bleibt, wo sie ist. ein pauschaler
    # abzug wuerde 196 punkte je reihe um einen tag verschieben.
    check("09:00 bleibt an seinem tag",
          str(stichtag("2023-08-27T08:59:59.000Z", "bestand")), "2023-08-27")
    check("08:59 ebenso",
          str(stichtag("2024-03-11T08:59:58.000Z", "bestand")), "2024-03-11")

    # das echte stueck reihe vom 06. bis 10.09.: vorher zwei tage auf dem
    # 08.09. und keiner auf dem 07. und 09., nachher fuenf saubere tage.
    echt = ["2026-09-06T23:59:59.410Z", "2026-09-08T00:00:01.573Z",
            "2026-09-08T23:59:59.713Z", "2026-09-10T00:00:02.216Z",
            "2026-09-11T00:00:01.646Z"]
    check("ohne korrektur zwei tage auf dem 08.09.",
          [str(tag_von(x)) for x in echt],
          ["2026-09-06", "2026-09-08", "2026-09-08", "2026-09-10", "2026-09-11"])
    check("mit korrektur fuenf tage am stueck",
          [str(stichtag(x, "bestand")) for x in echt],
          ["2026-09-06", "2026-09-07", "2026-09-08", "2026-09-09", "2026-09-10"])

    # und der lesefall, der am 21.09. schiefging: zwei messungen auf
    # demselben kalendertag, die aeltere hat gewonnen.
    doppelt = {"labels": ["2026-09-06T23:59:59.410Z", "2026-09-07T00:00:01.000Z"],
               "datasets": [{"label": "Addresses", "data": [791880, 792098]}]}
    tag_d, werte_d = letzter_voller(doppelt, ["Addresses"],
                                    dt.date(2026, 9, 8), art="bestand")
    check("bei zwei messungen am selben tag gewinnt die spaetere",
          werte_d[0], 792098.0)
    check("und der tag stimmt", str(tag_d), "2026-09-06")

    # die bestandsreihen im stub liefern trotz verschobener marken
    # dieselben tage wie vorher
    w_b, t_b, _ = sammle(heute=dt.date(2026, 8, 18), holer=_stub)
    check("holder adressen nach der korrektur", w_b["holder_addr"], 789500)
    check("und traegt den sonntag", t_b["holder_addr"], "2026-08-16")
    check("boersenbestand nach der korrektur", w_b["exchange_kas"], 3930000000)
    check("ruhender anteil nach der korrektur", w_b["holders"], 50.9)
    # die tagessummen daneben duerfen sich dabei nicht bewegt haben
    check("tagessumme unveraendert", t_b["active_addr"], "2026-08-16")

    if fails:
        print("selftest FEHLGESCHLAGEN")
        for f in fails:
            print("  " + f)
        return 1
    print("selftest ok, 50 faelle")
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
