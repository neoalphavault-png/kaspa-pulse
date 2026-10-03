#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""maschinenzahlungen.py, Experiment "100 Zahlungen" fuer den Erklaerer am 08.10.2026.

ZWECK (Ben, 03.10.2026). Ein Runner schickt 100 Zahlungen von einer eigenen
Test-Wallet A an eine zweite eigene Adresse B und misst, wie lange jede bis zur
Bestaetigung braucht, was sie kostet und wie gross der Payload ist. Dazu, in
einem eigenen Job ohne Schluessel, die Blockrate ueber 10 Minuten, die typische
Gebuehr einer einfachen Tx aus genau diesen 10 Minuten und die Covenant-Zahlen
aus data/covenants-log.json.

BESTAETIGT HEISST HIER: von der Kette angenommen, also von einem Block der
ausgewaehlten Kette akzeptiert (accepted). Das ist NICHT final. So steht es in
jeder Ausgabe, und so muss es im Erklaerer stehen.

DER SCHLUESSEL. Nur aus der Umgebung (KASPA_TESTWALLET_PRIVKEY, ein GitHub
Secret im Environment testwallet, jeder Lauf wartet auf Bens Klick). Er wird
gelesen und sofort aus os.environ geloescht. Er wird nie gedruckt, nie
geschrieben, und vor jeder Ausgabe prueft schreibe_json(), dass er in keiner
Schreibweise im Text steht. Fehler im Signierteil melden nur ihren Typ.

    python3 scripts/maschinenzahlungen.py zahlungen --anzahl 3   --out z.json   # probelauf
    python3 scripts/maschinenzahlungen.py zahlungen --anzahl 100 --out z.json   # der lauf
    python3 scripts/maschinenzahlungen.py trocken   --anzahl 100 --out z.json   # ohne schluessel, ohne senden
    python3 scripts/maschinenzahlungen.py messung   --out m.json                # 10 min, ohne schluessel
    python3 scripts/maschinenzahlungen.py bericht   --zahlungen z.json --messung m.json --datum 2026-10-06
    python3 scripts/maschinenzahlungen.py --selbsttest

Freigegeben von Ben am 03.10.2026: 0,15 KAS je Zahlung, nacheinander, jede
wartet auf die Annahme der vorigen, Rest am Ende an B, Payload
"kp-test 017/100", SDK kaspa 2.1.0 mit Version und Pruefsumme, hoechstens 20 KAS
auf A.
"""

import argparse
import asyncio
import datetime as dt
import json
import os
import re
import statistics
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
COVENANTS = REPO / "data" / "covenants-log.json"

NETZ = "mainnet"
SOMPI = 100_000_000
BETRAG = 15_000_000                 # 0,15 KAS je zahlung
HOECHSTENS_AUF_A = 20 * SOMPI       # mehr als 20 KAS auf A: abbruch
GEBUEHR_GRENZE = 1_000_000          # 0,01 KAS je tx: abbruch
WARTEN_S = 60                       # je tx hoechstens so lange auf die annahme warten
FEHLER_IN_FOLGE = 3                 # dann abbruch mit teilergebnis
BLOCKRATE_S = 600                   # 10 minuten
REST = "https://api.kaspa.org"
UA = "kaspa-pulse-bot (+https://kaspapulse.com)"
SDK = "kaspa 2.1.0 (pypi, wheel cp312 manylinux_2_28 x86_64, sha256 1f12fc7467...)"
DEFINITION = ("bestaetigt heisst von der kette angenommen (accepted by a selected chain block), "
              "nicht final")
IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


def jetzt():
    return dt.datetime.now(dt.timezone.utc)


def iso(t):
    return t.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def ohne_ip(text):
    """Bens Regel: keine IP-Adressen in irgendeiner Ausgabe."""
    return IPV4.sub("[ip]", str(text or ""))


def payload_text(nr, anzahl):
    return "kp-test %03d/%03d" % (nr, anzahl)


# ------------------------------------------------------------ der schluessel

class Geheim:
    """Haelt den Schluessel. repr und str verraten nichts. pruefe() wirft,
    wenn ein Text den Schluessel in irgendeiner Schreibweise enthaelt."""

    def __init__(self, hexwert):
        self._h = (hexwert or "").strip()

    def __repr__(self):
        return "Geheim(***)"

    __str__ = __repr__

    def wert(self):
        return self._h

    def pruefe(self, text):
        if not self._h:
            return
        t = str(text).lower()
        h = self._h.lower()
        if h in t or h[:32] in t or h[32:] in t:
            raise SystemExit("ABBRUCH der schluessel stuende in einer ausgabe, nichts geschrieben")


def schluessel_aus_umgebung():
    """Liest den Schluessel und loescht ihn sofort aus der Umgebung, damit
    kein Kindprozess ihn erbt."""
    roh = os.environ.pop("KASPA_TESTWALLET_PRIVKEY", "")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", roh.strip()):
        raise SystemExit("ABBRUCH KASPA_TESTWALLET_PRIVKEY fehlt oder hat nicht 64 hex-zeichen "
                         "(wert wird nicht gezeigt)")
    return Geheim(roh)


def schreibe_json(pfad, daten, geheim=None):
    text = json.dumps(daten, ensure_ascii=False, indent=1) + "\n"
    if geheim:
        geheim.pruefe(text)
    if IPV4.search(text):
        raise SystemExit("ABBRUCH eine ip-adresse stuende in der ausgabe, nichts geschrieben")
    Path(pfad).parent.mkdir(parents=True, exist_ok=True)
    Path(pfad).write_text(text, encoding="utf-8")


def sauber(exc, geheim=None):
    """Fehlertext fuer die JSON: Typ und hoechstens 160 Zeichen, ohne IP, und
    nur, wenn der Schluessel nicht darin steht."""
    text = ohne_ip("%s: %s" % (type(exc).__name__, exc))[:160]
    try:
        if geheim:
            geheim.pruefe(text)
    except SystemExit:
        return type(exc).__name__ + ": [geschwaerzt]"
    return text


# ------------------------------------------------------------ rest

def hole(pfad, daten=None, versuche=3):
    url = pfad if pfad.startswith("http") else REST + pfad
    letzter = None
    for i in range(versuche):
        try:
            body = json.dumps(daten).encode() if daten is not None else None
            req = urllib.request.Request(url, data=body, headers={
                "User-Agent": UA, "Accept": "application/json",
                **({"Content-Type": "application/json"} if body else {})})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:                    # noqa: BLE001
            letzter = exc
            time.sleep(1 + i)
    raise RuntimeError("%s nicht erreichbar, %s" % (pfad.split("?")[0], ohne_ip(letzter)))


# ------------------------------------------------------------ sdk

def sdk():
    import kaspa                                    # noqa: WPS433
    return kaspa


def ref(kaspa, adresse, spk, txid, index, betrag, daa=0):
    return kaspa.UtxoEntryReference.from_dict({
        "address": str(adresse), "outpoint": {"transactionId": txid, "index": index},
        "utxoEntry": {"amount": int(betrag), "scriptPublicKey": {"version": spk.version, "script": spk.script},
                      "blockDaaScore": int(daa), "isCoinbase": False, "covenantId": None}})


def baue(kaspa, eintraege, a, b, nr, anzahl, geheim_key):
    """Eine Zahlung A an B, signiert. Gibt (pending, wechsel_index, payload) zurueck."""
    payload = payload_text(nr, anzahl).encode("ascii")
    g = kaspa.Generator(entries=eintraege, change_address=a, network_id=NETZ,
                        outputs=[kaspa.PaymentOutput(b, BETRAG)], payload=payload, priority_fee=0)
    ps = list(g)
    if len(ps) != 1:
        raise RuntimeError("generator lieferte %d transaktionen statt einer" % len(ps))
    p = ps[0]
    if p.fee_amount > GEBUEHR_GRENZE:
        raise RuntimeError("gebuehr %d sompi ueber der grenze %d" % (p.fee_amount, GEBUEHR_GRENZE))
    try:
        p.sign([geheim_key])
    except Exception as exc:                        # noqa: BLE001
        raise RuntimeError("signieren gescheitert (%s)" % type(exc).__name__) from None
    spk_a = kaspa.pay_to_address_script(a)
    wechsel = None
    for k, o in enumerate(p.transaction.outputs):
        s = o.script_public_key
        if s.script == spk_a.script and o.value == p.change_amount:
            wechsel = k
    return p, wechsel, payload


# ------------------------------------------------------------ zahlungen

class Annahme:
    """Merkt sich, wann eine Tx-ID zum ersten Mal als angenommen gemeldet wurde."""

    def __init__(self):
        self.gesehen = {}

    def ereignis(self, event, *_a, **_k):
        t_wand, t_mono = jetzt(), time.monotonic()
        daten = event.get("data", event) if isinstance(event, dict) else {}
        for blk in daten.get("acceptedTransactionIds") or []:
            for txid in blk.get("acceptedTransactionIds") or []:
                if txid not in self.gesehen:
                    self.gesehen[txid] = (t_wand, t_mono, blk.get("acceptingBlockHash"))


async def zahlungen(anzahl, trocken=False, senden=None, verbinde=None):
    """Der Lauf. trocken: Wegwerf-Schluessel im Speicher, erfundener UTXO, nichts
    wird gesendet, die Annahme wird nachgestellt. senden/verbinde ersetzen im
    Selbsttest das Netz."""
    kaspa = sdk()
    erg = {"experiment": "100 zahlungen", "modus": "trocken" if trocken else "echt",
           "anzahl_geplant": anzahl, "netz": NETZ, "definition_bestaetigt": DEFINITION, "sdk": SDK,
           "betrag_je_zahlung_kas": BETRAG / SOMPI, "start_utc": iso(jetzt()), "zahlungen": []}
    if trocken:
        kp = kaspa.Keypair.random()
        geheim = Geheim(kp.private_key)
        a = kp.to_address(NETZ)
        b = kaspa.Keypair.random().to_address(NETZ)
        erg["hinweis"] = "trockenlauf, wegwerf-schluessel, erfundener utxo, nichts gesendet, zeiten nachgestellt"
    else:
        geheim = schluessel_aus_umgebung()
        a_soll = os.environ.get("KASPA_TESTWALLET_ABSENDER", "").strip()
        b = os.environ.get("KASPA_TESTWALLET_ZIEL", "").strip()
        if not (a_soll.startswith("kaspa:") and b.startswith("kaspa:")):
            raise SystemExit("ABBRUCH KASPA_TESTWALLET_ABSENDER oder KASPA_TESTWALLET_ZIEL fehlt")
        try:
            a = kaspa.PrivateKey(geheim.wert()).to_address(NETZ)
        except Exception as exc:                    # noqa: BLE001
            raise SystemExit("ABBRUCH schluessel nicht lesbar (%s)" % type(exc).__name__) from None
        if str(a) != a_soll:
            raise SystemExit("ABBRUCH der schluessel gehoert nicht zu KASPA_TESTWALLET_ABSENDER")
        if a_soll == b:
            raise SystemExit("ABBRUCH absender und ziel sind gleich")
    schluessel = kaspa.PrivateKey(geheim.wert())
    erg["absender"], erg["ziel"] = str(a), str(b)
    spk_a = kaspa.pay_to_address_script(a)

    annahme = Annahme()
    rpc = None
    if trocken:
        eintraege = [ref(kaspa, a, spk_a, "11" * 32, 0, 20 * SOMPI)]
        erg["bestand_a_vorher_kas"] = 20.0
    else:
        rpc = await (verbinde or verbinden)(annahme)
        erg["knoten"] = ohne_ip(getattr(rpc, "url", "") or "")
        antwort = await rpc.get_utxos_by_addresses({"addresses": [str(a)]})
        eintraege = [kaspa.UtxoEntryReference.from_dict(e) for e in antwort.get("entries") or []]
        bestand = sum(e.amount for e in eintraege)
        erg["bestand_a_vorher_kas"] = bestand / SOMPI
        if bestand > HOECHSTENS_AUF_A + SOMPI // 2:
            raise SystemExit("ABBRUCH auf A liegen %.4f KAS, mehr als 20" % (bestand / SOMPI))
        if bestand < anzahl * (BETRAG + GEBUEHR_GRENZE // 2):
            raise SystemExit("ABBRUCH auf A liegen %.4f KAS, zu wenig fuer %d zahlungen" % (bestand / SOMPI, anzahl))

    in_folge = 0
    for nr in range(1, anzahl + 1):
        z = {"nr": nr}
        try:
            p, wechsel, payload = baue(kaspa, eintraege, a, b, nr, anzahl, schluessel)
            z.update({"tx_id": p.id, "payload_text": payload.decode(), "payload_bytes": len(payload),
                      "masse": p.mass, "gebuehr_sompi": p.fee_amount,
                      "gebuehr_kas": p.fee_amount / SOMPI})
            t0_wand, t0 = jetzt(), time.monotonic()
            z["abgeschickt_utc"] = iso(t0_wand)
            if trocken:
                annahme.gesehen[p.id] = (t0_wand + dt.timedelta(seconds=1), t0 + 1.0, "trocken")
            else:
                await (senden or (lambda pp: pp.submit(rpc)))(p)
            z["sendeaufruf_s"] = round(time.monotonic() - t0, 3)
            while p.id not in annahme.gesehen and time.monotonic() - t0 < WARTEN_S:
                await asyncio.sleep(0.02)
            if p.id not in annahme.gesehen:
                raise RuntimeError("nach %d s nicht als angenommen gemeldet" % WARTEN_S)
            t1_wand, t1, blk = annahme.gesehen[p.id]
            z.update({"angenommen_utc": iso(t1_wand), "sekunden_bis_angenommen": round(t1 - t0, 3),
                      "annehmender_block": blk})
            if wechsel is None:
                raise RuntimeError("kein wechselgeld-ausgang gefunden")
            eintraege = [ref(kaspa, a, spk_a, p.id, wechsel, p.change_amount)]
            in_folge = 0
        except Exception as exc:                    # noqa: BLE001
            z["fehler"] = sauber(exc, geheim)
            in_folge += 1
            if rpc is not None:
                await asyncio.sleep(2)
                antwort = await rpc.get_utxos_by_addresses({"addresses": [str(a)]})
                eintraege = [kaspa.UtxoEntryReference.from_dict(e) for e in antwort.get("entries") or []]
        erg["zahlungen"].append(z)
        print("  %3d  %-16s  %s" % (nr, z.get("payload_text", ""),
                                     "angenommen nach %.3f s" % z["sekunden_bis_angenommen"]
                                     if "sekunden_bis_angenommen" in z else "FEHLER " + z["fehler"]))
        if in_folge >= FEHLER_IN_FOLGE:
            erg["abbruch"] = "%d fehler in folge nach zahlung %d" % (in_folge, nr)
            break

    erg["zusammen"] = zusammenfassen(erg["zahlungen"], anzahl)
    erg["rueckgabe"] = await rueckgabe(kaspa, rpc, eintraege, a, b, schluessel, geheim, trocken, annahme, senden)
    erg["ende_utc"] = iso(jetzt())
    if rpc is not None:
        try:
            await rpc.disconnect()
        except Exception:                           # noqa: BLE001
            pass
    return erg, geheim


async def verbinden(annahme):
    kaspa = sdk()
    rpc = kaspa.RpcClient(resolver=kaspa.Resolver(), network_id=NETZ)
    await rpc.connect()
    rpc.add_event_listener(kaspa.NotificationEvent.VirtualChainChanged, annahme.ereignis)
    await rpc.subscribe_virtual_chain_changed(True)
    return rpc


async def rueckgabe(kaspa, rpc, eintraege, a, b, schluessel, geheim, trocken, annahme, senden):
    """Rest von A an B (Ben: ja). Eine Tx, alle Eingaenge, ein Ausgang an B,
    Gebuehr = Mindestgebuehr laut SDK. Nicht Teil der 100."""
    try:
        if not eintraege:
            return {"hinweis": "kein rest auf A"}
        rest = sum(e.amount for e in eintraege)
        f = 0
        for _ in range(5):
            tx = kaspa.create_transaction(eintraege, [kaspa.PaymentOutput(b, rest - f)], f)
            mind = kaspa.calculate_transaction_fee(NETZ, tx)
            if mind is not None and f >= mind:
                break
            f = int(mind)
        if f > GEBUEHR_GRENZE:
            raise RuntimeError("gebuehr der rueckgabe %d sompi ueber der grenze" % f)
        try:
            tx = kaspa.sign_transaction(tx, [schluessel], True)
        except Exception as exc:                    # noqa: BLE001
            raise RuntimeError("signieren gescheitert (%s)" % type(exc).__name__) from None
        r = {"tx_id": tx.id, "betrag_kas": (rest - f) / SOMPI, "gebuehr_sompi": f, "gebuehr_kas": f / SOMPI,
             "eingaenge": len(eintraege)}
        if not trocken:
            t0 = time.monotonic()
            await (senden or (lambda t: rpc.submit_transaction({"transaction": t, "allowOrphan": False})))(tx)
            while tx.id not in annahme.gesehen and time.monotonic() - t0 < WARTEN_S:
                await asyncio.sleep(0.05)
            r["angenommen"] = tx.id in annahme.gesehen
        return r
    except Exception as exc:                        # noqa: BLE001
        return {"fehler": sauber(exc, geheim)}


def zusammenfassen(zl, anzahl):
    ok = [z for z in zl if "sekunden_bis_angenommen" in z]
    zeiten = sorted(z["sekunden_bis_angenommen"] for z in ok)
    s = {"anzahl_geplant": anzahl, "anzahl_gesendet": len(zl), "anzahl_angenommen": len(ok),
         "fehler": len(zl) - len(ok),
         "gebuehren_gesamt_sompi": sum(z.get("gebuehr_sompi", 0) for z in ok),
         "payload_bytes_je_tx": sorted({z["payload_bytes"] for z in zl if "payload_bytes" in z}),
         "masse_von_bis": [min((z["masse"] for z in ok), default=None), max((z["masse"] for z in ok), default=None)]}
    s["gebuehren_gesamt_kas"] = s["gebuehren_gesamt_sompi"] / SOMPI
    if zeiten:
        erste = dt.datetime.fromisoformat(ok[0]["abgeschickt_utc"].replace("Z", "+00:00"))
        letzte = dt.datetime.fromisoformat(ok[-1]["angenommen_utc"].replace("Z", "+00:00"))
        s.update({"gesamtzeit_s": round((letzte - erste).total_seconds(), 3),
                  "median_s": round(statistics.median(zeiten), 3), "maximum_s": zeiten[-1],
                  "minimum_s": zeiten[0],
                  "gesamtzeit_hinweis": "erste absendung bis letzte annahme, nacheinander, jede wartet auf die vorige"})
    return s


# ------------------------------------------------------------ messung, ohne schluessel

async def messung(sekunden=BLOCKRATE_S):
    kaspa = sdk()
    m = {"start_utc": iso(jetzt())}
    rpc = kaspa.RpcClient(resolver=kaspa.Resolver(), network_id=NETZ)
    await rpc.connect()
    m["knoten"] = ohne_ip(getattr(rpc, "url", "") or "")
    try:
        d0, t0w, t0 = await rpc.get_block_dag_info(), jetzt(), time.monotonic()
        sink0 = (await rpc.get_sink()).get("sink")
        try:
            fe = (await rpc.get_fee_estimate()).get("estimate") or {}
            m["fee_estimate"] = {"priority_feerate": (fe.get("priorityBucket") or {}).get("feerate"),
                                 "normal_feerate": [b.get("feerate") for b in fe.get("normalBuckets") or []][:3],
                                 "einheit": "sompi je gramm masse", "zeit_utc": iso(jetzt())}
        except Exception as exc:                    # noqa: BLE001
            m["fee_estimate"] = {"fehler": sauber(exc)}
        await asyncio.sleep(sekunden)
        d1, t1w, t1 = await rpc.get_block_dag_info(), jetzt(), time.monotonic()
        daa0, daa1 = int(d0["virtualDaaScore"]), int(d1["virtualDaaScore"])
        bps = (daa1 - daa0) / (t1 - t0)
        m["blockrate"] = {"bloecke_je_sekunde": round(bps, 3), "von_utc": iso(t0w), "bis_utc": iso(t1w),
                          "sekunden": round(t1 - t0, 1), "daa_von": daa0, "daa_bis": daa1,
                          "quelle": "virtueller daa-score des knotens (rpc), zuwachs ueber das fenster",
                          "plausibel": 5 < bps < 15}
        m["gebuehr_einfach"] = await gebuehr_einfach(rpc, sink0, t0w, t1w)
        m["rpc_pruefung"] = await rpc_pruefung(rpc)
    finally:
        try:
            await rpc.disconnect()
        except Exception:                           # noqa: BLE001
            pass
    m["covenants"] = covenants()
    m["ende_utc"] = iso(jetzt())
    return m


async def rpc_pruefung(rpc, sekunden=20):
    """Prueft ohne Schluessel die Wege, die der Lauf braucht: Ereignis der
    virtuellen Kette mit angenommenen Tx-IDs, UTXO-Abfrage im Format, das
    UtxoEntryReference.from_dict nimmt. Adresse ist die oeffentliche von Entity X."""
    kaspa = sdk()
    r = {}
    try:
        a = Annahme()
        rpc.add_event_listener(kaspa.NotificationEvent.VirtualChainChanged, a.ereignis)
        await rpc.subscribe_virtual_chain_changed(True)
        await asyncio.sleep(sekunden)
        r["kettenereignis_tx_ids_in_%d_s" % sekunden] = len(a.gesehen)
    except Exception as exc:                        # noqa: BLE001
        r["kettenereignis_fehler"] = sauber(exc)
    try:
        ex = "kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a"
        u = await rpc.get_utxos_by_addresses({"addresses": [ex]})
        e = (u.get("entries") or [])[:3]
        refs = [kaspa.UtxoEntryReference.from_dict(x) for x in e]
        r["utxo_format"] = "ok, %d eintraege umgewandelt" % len(refs)
    except Exception as exc:                        # noqa: BLE001
        r["utxo_format_fehler"] = sauber(exc)
    return r


async def gebuehr_einfach(rpc, sink0, von, bis, stichprobe=300):
    """Median der Gebuehr aller Tx mit 1 Eingang und hoechstens 2 Ausgaengen,
    angenommen in genau diesem Fenster (virtuelle Kette ab dem Sink zu Beginn).
    Eingangsbetraege ueber api.kaspa.org, weil die Kette sie in der Tx nicht traegt."""
    g = {"fenster_von_utc": iso(von), "fenster_bis_utc": iso(bis),
         "definition": "1 eingang, hoechstens 2 ausgaenge, keine coinbase, angenommen im fenster",
         "quelle": "tx-ids aus der virtuellen kette des knotens, betraege aus api.kaspa.org"}
    try:
        vc = await rpc.get_virtual_chain_from_block({"startHash": sink0, "includeAcceptedTransactionIds": True})
        ids = [t for blk in vc.get("acceptedTransactionIds") or [] for t in blk.get("acceptedTransactionIds") or []]
        g["tx_im_fenster"] = len(ids)
        probe = ids[:: max(1, len(ids) // stichprobe)][:stichprobe]
        txs = []
        for i in range(0, len(probe), 50):
            txs += hole("/transactions/search?resolve_previous_outpoints=light",
                        {"transactionIds": probe[i:i + 50]}) or []
        gebuehren = []
        for t in txs:
            ein, aus = t.get("inputs") or [], t.get("outputs") or []
            if len(ein) != 1 or not 1 <= len(aus) <= 2:
                continue
            e = sum(int(x.get("previous_outpoint_amount") or 0) for x in ein)
            a = sum(int(x.get("amount") or 0) for x in aus)
            if e > 0 and e >= a:
                gebuehren.append(e - a)
        gebuehren.sort()
        g.update({"stichprobe": len(probe), "beantwortet": len(txs), "einfach": len(gebuehren)})
        if gebuehren:
            q = statistics.quantiles(gebuehren, n=10) if len(gebuehren) >= 10 else [gebuehren[0]] * 9
            g.update({"median_sompi": int(statistics.median(gebuehren)),
                      "median_kas": statistics.median(gebuehren) / SOMPI,
                      "p10_sompi": int(q[0]), "p90_sompi": int(q[-1])})
    except Exception as exc:                        # noqa: BLE001
        g["fehler"] = sauber(exc)
    return g


def covenants(pfad=COVENANTS):
    """Bestand und Zugang aus unserem Log. Bestand = utxo_count, die
    unverbrauchten Covenant-Outputs am Ende des Tages, mit dem Zeitstempel
    der Quelle (stand_utc). Zugang seit dem Fork = Summe outputs_created."""
    try:
        log = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"fehler": sauber(exc)}
    tage = log.get("tage") or []
    best = [e for e in tage if e.get("utxo_count") is not None]
    if not best:
        return {"fehler": "kein bestand im log"}
    e = best[-1]
    created = [x for x in tage if x.get("outputs_created") is not None and x["datum"] <= e["datum"]]
    return {"bestand_unverbraucht": e["utxo_count"], "bestand_datum": e["datum"],
            "bestand_stand_utc": e.get("stand_utc"), "zugang_am_tag": e.get("outputs_created"),
            "erzeugt_seit_fork": sum(x["outputs_created"] for x in created),
            "erzeugt_bis_datum": e["datum"], "fork": log.get("toccata_aktiv_seit"),
            "formulierung": "%s covenant outputs unspent on chain at the end of %s" % (
                "{:,}".format(e["utxo_count"]), e["datum"]),
            "quelle": "data/covenants-log.json, kaspalytics"}


# ------------------------------------------------------------ bericht

def kette_pruefen(z):
    """Nach dem Lauf, ohne Schluessel: jede Tx bei api.kaspa.org nachschlagen
    und die Gebuehr aus der Kette messen (Summe der Eingaenge minus Summe der
    Ausgaenge). Das ist die Zahl fuer das Video. gebuehr_sompi in den Zahlungen
    ist nur, was das SDK beim Bau gesetzt hat (Ben, 03.10.2026)."""
    ids = [x["tx_id"] for x in z.get("zahlungen") or [] if x.get("tx_id")]
    k = {"quelle": "api.kaspa.org /transactions/search, eingaenge minus ausgaenge", "abgefragt_utc": iso(jetzt())}
    try:
        txs = []
        for i in range(0, len(ids), 50):
            txs += hole("/transactions/search?resolve_previous_outpoints=light",
                        {"transactionIds": ids[i:i + 50]}) or []
        je = {}
        for t in txs:
            e = sum(int(x.get("previous_outpoint_amount") or 0) for x in t.get("inputs") or [])
            a = sum(int(x.get("amount") or 0) for x in t.get("outputs") or [])
            je[t.get("transaction_id")] = {"gebuehr_sompi": e - a if e else None, "angenommen": t.get("is_accepted")}
        gemessen = [v["gebuehr_sompi"] for v in je.values() if v["gebuehr_sompi"] is not None]
        k.update({"gefunden": len(je), "angenommen": sum(1 for v in je.values() if v["angenommen"]),
                  "gebuehr_je_tx_sompi": sorted(set(gemessen)),
                  "gebuehren_gesamt_sompi": sum(gemessen), "gebuehren_gesamt_kas": sum(gemessen) / SOMPI,
                  "abweichung_zum_sdk": [x["nr"] for x in z.get("zahlungen") or []
                                         if x.get("tx_id") in je and je[x["tx_id"]]["gebuehr_sompi"] is not None
                                         and je[x["tx_id"]]["gebuehr_sompi"] != x.get("gebuehr_sompi")]})
    except Exception as exc:                        # noqa: BLE001
        k["fehler"] = sauber(exc)
    return k


def bericht(z, m, datum):
    s = z.get("zusammen", {})
    k = z.get("laut_kette") or {"fehler": "nicht abgefragt (trockenlauf)"}
    b = m.get("blockrate", {})
    g = m.get("gebuehr_einfach", {})
    c = m.get("covenants", {})
    zeilen = [
        "# Experiment 100 Zahlungen, %s" % datum, "",
        "Modus %s. %s." % (z.get("modus"), DEFINITION.capitalize()),
        "Zahlen nur aus dem Runner-Lauf, siehe data/pruefung/maschinenzahlungen-%s.json." % datum, "",
        "## Zahlungen", "",
        "- %s von %s angenommen, %s Fehler%s" % (
            s.get("anzahl_angenommen"), s.get("anzahl_geplant"), s.get("fehler"),
            ", abgebrochen (%s)" % z["abbruch"] if z.get("abbruch") else ""),
        "- Gesamtzeit %s s, Median %s s, Maximum %s s, Minimum %s s" % (
            s.get("gesamtzeit_s"), s.get("median_s"), s.get("maximum_s"), s.get("minimum_s")),
        "- Gebuehr je Zahlung gemessen auf der Kette %s Sompi, gesamt %s KAS (%s von %s Tx gefunden, Quelle %s)" % (
            k.get("gebuehr_je_tx_sompi"), k.get("gebuehren_gesamt_kas"), k.get("gefunden"),
            s.get("anzahl_gesendet"), k.get("quelle")),
        "- Zum Vergleich die Rechnung des SDK beim Bau: gesamt %s KAS. Fuers Video zaehlt nur die gemessene Zahl." % (
            s.get("gebuehren_gesamt_kas")),
        "- Masse je Tx %s" % (s.get("masse_von_bis"),),
        "- Payload je Tx %s Byte, Text wie `%s`" % (s.get("payload_bytes_je_tx"), payload_text(17, 100)),
        "- %s KAS je Zahlung, von %s an %s, Knoten %s" % (z.get("betrag_je_zahlung_kas"), z.get("absender"),
                                                         z.get("ziel"), z.get("knoten", "-")),
        "- Rueckgabe des Rests an B: %s" % json.dumps(z.get("rueckgabe"), ensure_ascii=False), "",
        "## Netz im selben Zeitraum", "",
        "- Blockrate %s Bloecke je Sekunde, gemessen %s bis %s (%s s)" % (
            b.get("bloecke_je_sekunde"), b.get("von_utc"), b.get("bis_utc"), b.get("sekunden")),
        "- Knoten der Messung %s, RPC-Pruefung %s" % (
            m.get("knoten", "-"), json.dumps(m.get("rpc_pruefung"), ensure_ascii=False)),
        "- Gebuehrenschaetzung des Knotens %s" % json.dumps(m.get("fee_estimate"), ensure_ascii=False),
        "- Typische Gebuehr einer einfachen Tx: Median %s KAS (%s Sompi), %s einfache Tx aus %s im Fenster %s bis %s" % (
            g.get("median_kas"), g.get("median_sompi"), g.get("einfach"), g.get("stichprobe"),
            g.get("fenster_von_utc"), g.get("fenster_bis_utc")),
        "- Covenant-Outputs unverbraucht auf der Kette %s am Ende des %s (Quelle gemessen %s), erzeugt seit dem Fork %s bis %s" % (
            c.get("bestand_unverbraucht"), c.get("bestand_datum"), c.get("bestand_stand_utc"),
            c.get("erzeugt_seit_fork"), c.get("erzeugt_bis_datum")),
        "",
    ]
    for f in (z.get("fehler"), k.get("fehler"), g.get("fehler"), c.get("fehler")):
        if f:
            zeilen.append("Fehler: %s" % f)
    return "\n".join(zeilen) + "\n"


# ------------------------------------------------------------ selbsttest

def selbsttest():
    fehler = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            fehler.append(name)

    erg, geheim = asyncio.run(zahlungen(100, trocken=True))
    s = erg["zusammen"]
    ok("100 trockene zahlungen angenommen", s["anzahl_angenommen"] == 100 and s["fehler"] == 0)
    ok("payload 15 byte, text kp-test 017/100",
       s["payload_bytes_je_tx"] == [15] and erg["zahlungen"][16]["payload_text"] == "kp-test 017/100")
    ok("gebuehr je tx unter der grenze", all(z["gebuehr_sompi"] <= GEBUEHR_GRENZE for z in erg["zahlungen"]))
    ok("masse unter 100000", s["masse_von_bis"][1] < 100000)
    r = erg["rueckgabe"]
    ok("rueckgabe des rests, eine tx, gebuehr unter der grenze",
       "fehler" not in r and r.get("tx_id") and 0 < r["gebuehr_sompi"] <= GEBUEHR_GRENZE
       and abs(r["betrag_kas"] + r["gebuehr_kas"] - 20 + 100 * BETRAG / SOMPI + s["gebuehren_gesamt_kas"]) < 1e-8)
    tmp = Path("/tmp/maschinenzahlungen-selbsttest.json")
    schreibe_json(tmp, erg, geheim)
    text = tmp.read_text()
    ok("schluessel steht nicht in der json", geheim.wert().lower() not in text.lower())
    try:
        schreibe_json(tmp, {"x": "abc" + geheim.wert()}, geheim)
        ok("schreibsperre bei schluessel im text", False)
    except SystemExit:
        ok("schreibsperre bei schluessel im text", True)
    try:
        schreibe_json(tmp, {"knoten": "wss://" + ".".join(["10", "1", "2", "3"]) + ":17110"})
        ok("schreibsperre bei ip", False)
    except SystemExit:
        ok("schreibsperre bei ip", True)
    ok("ohne_ip schwaerzt", ohne_ip("wss://" + ".".join(["10", "1", "2", "3"])) == "wss://[ip]")
    ok("repr verraet nichts", "Geheim(***)" == repr(geheim) and geheim.wert() not in repr(geheim))
    ok("sauber schwaerzt", "[geschwaerzt]" in sauber(ValueError("x" + geheim.wert()), geheim))
    alt = os.environ.get("KASPA_TESTWALLET_PRIVKEY")
    os.environ["KASPA_TESTWALLET_PRIVKEY"] = "ab" * 32
    g = schluessel_aus_umgebung()
    ok("schluessel wird aus der umgebung geloescht", "KASPA_TESTWALLET_PRIVKEY" not in os.environ
       and g.wert() == "ab" * 32)
    if alt is not None:
        os.environ["KASPA_TESTWALLET_PRIVKEY"] = alt
    os.environ["KASPA_TESTWALLET_PRIVKEY"] = "kein-schluessel"
    try:
        schluessel_aus_umgebung()
        ok("falscher schluessel bricht ab", False)
    except SystemExit as exc:
        ok("falscher schluessel bricht ab, ohne wert", "kein-schluessel" not in str(exc))
    os.environ.pop("KASPA_TESTWALLET_PRIVKEY", None)
    zf = zusammenfassen([{"sekunden_bis_angenommen": 1.0, "abgeschickt_utc": "2026-10-06T10:00:00.000Z",
                          "angenommen_utc": "2026-10-06T10:00:01.000Z", "payload_bytes": 15, "masse": 1,
                          "gebuehr_sompi": 2},
                         {"fehler": "x", "payload_bytes": 15},
                         {"sekunden_bis_angenommen": 3.0, "abgeschickt_utc": "2026-10-06T10:00:02.000Z",
                          "angenommen_utc": "2026-10-06T10:00:05.000Z", "payload_bytes": 15, "masse": 1,
                          "gebuehr_sompi": 2}], 3)
    ok("zusammenfassung: median, maximum, gesamtzeit, fehler",
       (zf["median_s"], zf["maximum_s"], zf["gesamtzeit_s"], zf["fehler"]) == (2.0, 3.0, 5.0, 1))
    c = covenants()
    ok("covenants aus dem log, bestand mit datum", "bestand_unverbraucht" in c and "erzeugt_seit_fork" in c)
    tmp.unlink()
    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


# ------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("befehl", nargs="?", choices=["zahlungen", "trocken", "messung", "bericht"])
    ap.add_argument("--anzahl", type=int, default=100)
    ap.add_argument("--out")
    ap.add_argument("--zahlungen", dest="z")
    ap.add_argument("--messung", dest="m")
    ap.add_argument("--datum", default=jetzt().date().isoformat())
    ap.add_argument("--sekunden", type=int, default=BLOCKRATE_S)
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.befehl in ("zahlungen", "trocken"):
        if a.anzahl not in (3, 100) and a.befehl == "zahlungen":
            raise SystemExit("ABBRUCH freigegeben sind 3 (probe) oder 100 zahlungen")
        erg, geheim = asyncio.run(zahlungen(a.anzahl, trocken=a.befehl == "trocken"))
        schreibe_json(a.out, erg, geheim)
        print(json.dumps(erg["zusammen"], ensure_ascii=False))
        return 0 if erg["zusammen"]["anzahl_angenommen"] else 1
    if a.befehl == "messung":
        m = asyncio.run(messung(a.sekunden))
        schreibe_json(a.out, m)
        print(json.dumps({k: m.get(k) for k in ("knoten", "fee_estimate", "rpc_pruefung", "blockrate",
                                                 "gebuehr_einfach", "covenants")}, ensure_ascii=False))
        return 0
    if a.befehl == "bericht":
        z = json.loads(Path(a.z).read_text()) if a.z and Path(a.z).exists() else {"fehler": "keine zahlungsdaten"}
        if z.get("modus") == "echt":
            z["laut_kette"] = kette_pruefen(z)
        m = json.loads(Path(a.m).read_text()) if a.m and Path(a.m).exists() else {"fehler": "keine messdaten"}
        gesamt = {"experiment": "100 zahlungen", "datum": a.datum, "definition_bestaetigt": DEFINITION,
                  "zahlungen": z, "netz": m}
        schreibe_json(REPO / "data" / "pruefung" / ("maschinenzahlungen-%s.json" % a.datum), gesamt)
        text = bericht(z, m, a.datum)
        if IPV4.search(text):
            raise SystemExit("ABBRUCH ip im bericht")
        p = REPO / "docs" / "pruefung" / ("maschinenzahlungen-%s.md" % a.datum)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        print(text)
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
