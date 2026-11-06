"""quelle_zcash.py - Live-Quelle der Upgrade-Wache fuer Zcash (art "zcash_p2p").

Nutzt den vorhandenen Zuhoerer (scripts/zcash/zcash_lauscher.py): Verbindungen
zu Zebra- und Zakura-Knoten, jede Block-Ankuendigung mit Ankunftszeit, fuer
jeden neuen Hash der Kopf per getdata. Die Zeilen, die der Zuhoerer sonst nur
in Dateien schreibt, gehen zusaetzlich in eine Warteschlange, aus der der Kern
im Takt liest. So laeuft der Kern in einem einzigen Thread.

Hoehen: Der Zuhoerer kennt nur Hashes und Vorgaenger. Die Hoehe kommt aus
einem kurzen Abruf mit dem eigenen Header-Client (zcash_koepfe.py, geprueft auf
Verkettung, Arbeitsnachweis und Zebra-Checkpoints), beim Start und wieder,
wenn Koepfe ohne bekannten Vorgaenger auflaufen (Luecke), hoechstens alle
10 Minuten.
Probelauf 29.10.2026: der erste Anker brauchte gut 4 Minuten (Abruf ab dem
letzten Zebra-Checkpoint). Bis dahin kennt die Wache keine Hoehe.

probe(): Handschlag mit den Adressen aus den DNS-Seeds, nur die gemeldete
Protokollversion, dann trennen. Keine Adresse wird gedruckt.

Nach dem Haenger in der NU7-Nacht (6.11.2026: DNS-Seeds auf c2 ab 02:50 UTC
nicht aufloesbar, eigene Spitze stand ab 3.543.431) zusaetzlich:
- adressen(): jeder Seed-Abruf bis zu dreimal mit Abstand (5, 15, 45 s); kommt
  nichts, gilt die Liste des letzten erfolgreichen Abrufs aus
  <ablage>/peers-cache.json. Die Datei bleibt auf c2 (Rechte 600), liegt nicht
  unter roh/ und geht nie ins Repo; der Roh-Export bricht ohnehin ab, wenn
  er eine Adresse findet. Gedruckt wird nur die Zahl der Adressen.
- kette-cache.json: die letzten 300 Koepfe unserer Kette (Hoehe, Hash, Zeit,
  nBits, keine Adressen); nach einem Neustart verankert die Wache sich daraus
  sofort, auch wenn der Header-Client keinen Seed erreicht.
- nachziehen_anstossen(): die Koepfe ab unserer Spitze per getheaders direkt
  von einem Peer holen (Locator aus unserer Kette), geprueft auf Verkettung
  und Arbeitsnachweis aus nBits, und als Koepfe an den Kern geben. Ohne
  Subprozess und ohne DNS, wenn der Cache Adressen hat.
- hoehe_gemeldet: hoechste Hoehe, die ein Peer beim Handschlag meldet; ein
  Hinweis fuer die Eigenwache im Kern.
"""
import csv
import gzip
import json
import os
import queue
import struct
import subprocess
import sys
import tempfile
import threading
import time

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "zcash"))
import zcash_koepfe  # noqa: E402
import zcash_lauscher  # noqa: E402
from zcash_koepfe import Peer, log, peers_finden  # noqa: E402

ANKER_ABSTAND_S = 600
NACHZIEHEN_ABSTAND_S = 120
PROBE_HOECHSTENS = 80
PROBE_THREADS = 20
DNS_VERSUCHE_S = (5, 15, 45)    # Abstand vor dem 2., 3. und 4. Versuch
KETTE_CACHE_BLOECKE = 300
KETTE_CACHE_ABSTAND_S = 600


def adressen(cache_pfad, finden=None, schlafen=time.sleep, versuche=DNS_VERSUCHE_S):
    """Peer-Adressen aus den Seeds, mit Wiederholung; sonst der Cache des letzten Erfolgs.

    Gibt (liste, herkunft) zurueck, herkunft "seeds", "cache" oder "keine".
    Druckt nie eine Adresse.
    """
    finden = finden or peers_finden
    liste = finden()
    for warte in versuche:
        if liste:
            break
        log(f"seeds ohne antwort, neuer versuch in {warte} s")
        schlafen(warte)
        liste = finden()
    if liste:
        try:
            tmp = cache_pfad + ".tmp"
            with open(tmp, "w") as f:
                json.dump([[a, p] for a, p in liste[:200]], f)
            os.chmod(tmp, 0o600)
            os.replace(tmp, cache_pfad)
        except OSError as e:
            log(f"peers-cache nicht geschrieben ({type(e).__name__})")
        return liste, "seeds"
    try:
        with open(cache_pfad) as f:
            alt = [(a, int(p)) for a, p in json.load(f)]
        if alt:
            log(f"seeds nicht erreichbar, {len(alt)} adressen aus dem cache des letzten erfolgs")
            return alt, "cache"
    except (OSError, ValueError):
        pass
    log("seeds nicht erreichbar und kein cache")
    return [], "keine"


def koepfe_pruefen(roh_liste, bekannte_hoehe, prev_hash):
    """Rohe Koepfe einer headers-Antwort pruefen: Verkettung ab prev_hash und
    Arbeitsnachweis (Hash <= Ziel aus nBits). Gibt [(hoehe, hash, prev, zeit, nbits)]."""
    out, prev, hoehe = [], prev_hash, bekannte_hoehe
    for raw in roh_liste:
        k = zcash_koepfe.kopf_lesen(raw)
        if k["prev"] != prev:
            break
        if int.from_bytes(k["hash"], "little") > zcash_koepfe.ziel_aus_nbits(k["bits"]):
            raise ValueError("arbeitsnachweis passt nicht zu nbits")
        hoehe += 1
        out.append((hoehe, k["hash"][::-1].hex(), k["prev"][::-1].hex(), k["zeit"], f"{k['bits']:08x}"))
        prev = k["hash"]
    return out


class _Zuhoerer(zcash_lauscher.Zuhoerer):
    """Wie der Zuhoerer, schreibt aber jede Zeile zusaetzlich in die Warteschlange."""
    def __init__(self, ende, ereignisse_pfad, koepfe_pfad, q):
        super().__init__(ende, ereignisse_pfad, koepfe_pfad)
        self.q = q

    def schreiben(self, datei, obj):
        super().schreiben(datei, obj)
        self.q.put(("ereignis" if datei is self.ereignisse else "kopf", obj))


class QuelleZcash:
    def __init__(self, cfg, roh_ordner, laufzeit_h=200):
        self.cfg = cfg
        self.netz = cfg["quelle"]["netz"]
        zcash_koepfe.netz_setzen(self.netz)
        os.makedirs(roh_ordner, exist_ok=True)
        stempel = time.strftime("%Y%m%dT%H%M", time.gmtime())
        self.q = queue.Queue()
        self.z = _Zuhoerer(time.time() + laufzeit_h * 3600,
                           os.path.join(roh_ordner, f"{stempel}-ereignisse.jsonl"),
                           os.path.join(roh_ordner, f"{stempel}-koepfe.jsonl"), self.q)
        self.letzter_anker = 0
        self.anker_laeuft = False
        self.ablage = os.path.dirname(os.path.abspath(roh_ordner))
        self.cache_pfad = os.path.join(self.ablage, "peers-cache.json")
        self.kette_pfad = os.path.join(self.ablage, "kette-cache.json")
        self.letztes_nachziehen = 0
        self.nachziehen_laeuft = False
        self.letzter_kette_cache = 0
        self.hoehe_gemeldet = 0
        self.locator_hashes = []      # neueste zuerst, gesetzt im Thread des Kerns
        self.locator_hoehe = None
        try:
            with open(self.kette_pfad) as f:
                zeilen = [tuple(z) for z in json.load(f)]
            if zeilen:
                self.q.put(("anker", zeilen))
                log(f"anker aus kette-cache: {len(zeilen)} koepfe bis hoehe {zeilen[-1][0]}")
        except (OSError, ValueError):
            pass
        # Software der verbundenen Peers fuer die Rohdaten (Report v1), nur
        # Kennung, Protokoll und unsere Nummer je Peer, keine Adresse
        self.peers_pfad = os.path.join(roh_ordner, f"{stempel}-peers.json")
        self.peers_text = None
        threading.Thread(target=self._verbinden_schleife, daemon=True).start()

    # ------------------------------------------------------------ verbindungen
    def _verbinden_schleife(self):
        liste, herkunft = adressen(self.cache_pfad)
        seeds_zeit, versucht = time.time(), set()
        while time.time() < self.z.ende:
            # ohne Adressen alle 5 min neu fragen, sonst alle 30 min
            neu_s = zcash_lauscher.SEEDS_NEU_S if herkunft == "seeds" else 300
            if time.time() - seeds_zeit > neu_s:
                liste, herkunft = adressen(self.cache_pfad)
                seeds_zeit, versucht = time.time(), set()
            try:
                self.z.verbinden(liste, versucht)
                with self.z.lock:
                    self.hoehe_gemeldet = max([self.hoehe_gemeldet] + [p.get("gemeldete_hoehe") or 0
                                                                      for p in self.z.peers])
            except Exception as e:  # ein Fehler beim Verbinden darf die Wache nicht beenden
                log(f"verbinden: {type(e).__name__}")
            time.sleep(zcash_lauscher.NACHFASSEN_S)

    def verbunden(self):
        with self.z.lock:
            return len(self.z.aktiv)

    # ------------------------------------------------------------ anker
    def anker_anstossen(self, dringend=False):
        if self.anker_laeuft or (not dringend and time.time() - self.letzter_anker < ANKER_ABSTAND_S):
            return
        hoehen = sorted(p["gemeldete_hoehe"] for p in self.z.peers if p.get("gemeldete_hoehe"))
        if not hoehen:
            return
        self.anker_laeuft, self.letzter_anker = True, time.time()
        ab = hoehen[len(hoehen) // 2] - 300
        threading.Thread(target=self._anker_holen, args=(ab,), daemon=True).start()

    def _anker_holen(self, ab):
        try:
            with tempfile.TemporaryDirectory() as d:
                aus, meta = os.path.join(d, "k.csv.gz"), os.path.join(d, "k.json")
                r = subprocess.run([sys.executable, os.path.join(HIER, "..", "zcash", "zcash_koepfe.py"),
                                    "--netz", self.netz, "--ab", str(ab), "--vorlauf", "0", "--gegenproben", "0",
                                    "--aus", aus, "--meta", meta],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=600)
                if r.returncode != 0:
                    log(f"anker: abruf ohne erfolg ({r.stderr.strip().splitlines()[-1:] or ['?']})")
                    return
                with gzip.open(aus, "rt") as f:
                    zeilen = [(int(z["hoehe"]), z["hash"], int(z["zeit"]), z["nbits"])
                              for z in csv.DictReader(f) if int(z["hoehe"]) >= ab]
                if zeilen:
                    self.q.put(("anker", zeilen))
                    log(f"anker: {len(zeilen)} koepfe bis hoehe {zeilen[-1][0]}")
        except Exception as e:
            log(f"anker: {type(e).__name__}")
        finally:
            self.anker_laeuft = False

    # ------------------------------------------------------------ in den kern
    def abholen(self, kern):
        """Alles aus der Warteschlange an den Kern geben, im Thread des Kerns."""
        n = 0
        while True:
            try:
                art, obj = self.q.get_nowait()
            except queue.Empty:
                break
            n += 1
            if art == "anker":
                kern.anker(obj)
            elif art == "kopf":
                kern.kopf(obj["hash"], obj["prev"], obj["zeit"], obj["nbits"])
            else:
                kern.ankuendigung(obj["t_ms"], obj["peer"], obj["hash"])
        kern.verbindungen(self.verbunden())
        self._peers_schreiben()
        if kern.tip:
            kette = kern._vorfahren(kern.tip, KETTE_CACHE_BLOECKE)
            self.locator_hashes = [(kette[i], kern.knoten[kern.tip]["hoehe"] - i)
                                   for i in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 20, 50, 100, 299) if i < len(kette)]
            self.locator_hoehe = kern.knoten[kern.tip]["hoehe"]
            if time.time() - self.letzter_kette_cache >= KETTE_CACHE_ABSTAND_S:
                self._kette_schreiben(kern, kette)
        if kern.tip is None:
            self.anker_anstossen(dringend=True)
        elif kern.braucht_anker():
            self.anker_anstossen()
        return n

    def _peers_schreiben(self):
        with self.z.lock:
            peers = [{k: p.get(k) for k in ("peer", "software", "version", "gemeldete_hoehe", "verbunden_utc",
                                             "getrennt_utc", "ankuendigungen")} for p in self.z.peers]
        text = json.dumps({"netz": self.netz, "peers": peers}, indent=1, ensure_ascii=False)
        if text == self.peers_text:
            return
        self.peers_text = text
        with open(self.peers_pfad + ".tmp", "w") as f:
            f.write(text)
        os.replace(self.peers_pfad + ".tmp", self.peers_pfad)

    def anhalten(self):
        """Nach dem Fenster: keine neuen Verbindungen, die Peer-Schleifen enden."""
        self.z.ende = time.time()
        self._peers_schreiben()

    def _kette_schreiben(self, kern, kette):
        zeilen = [(kern.knoten[h]["hoehe"], h, kern.knoten[h]["zeit"], kern.knoten[h]["nbits"])
                  for h in reversed(kette) if kern.knoten[h].get("zeit") is not None]
        try:
            with open(self.kette_pfad + ".tmp", "w") as f:
                json.dump(zeilen, f)
            os.replace(self.kette_pfad + ".tmp", self.kette_pfad)
            self.letzter_kette_cache = time.time()
        except OSError as e:
            log(f"kette-cache nicht geschrieben ({type(e).__name__})")

    # ------------------------------------------------------------ nachziehen
    def nachziehen_anstossen(self):
        """Koepfe ab unserer Spitze direkt von Peers holen (Eigenwache im Kern)."""
        if self.nachziehen_laeuft or time.time() - self.letztes_nachziehen < NACHZIEHEN_ABSTAND_S:
            return
        if not self.locator_hashes or self.locator_hoehe is None:
            self.anker_anstossen(dringend=True)
            return
        self.nachziehen_laeuft, self.letztes_nachziehen = True, time.time()
        threading.Thread(target=self._nachziehen, args=(list(self.locator_hashes), self.locator_hoehe),
                         daemon=True).start()
        self.anker_anstossen(dringend=True)

    def _nachziehen(self, locator_hex, tip_hoehe):
        try:
            liste, _ = adressen(self.cache_pfad, versuche=(5,))
            locator = [bytes.fromhex(h)[::-1] for h, _ in locator_hex]
            hoehe_von = {bytes.fromhex(h)[::-1]: hh for h, hh in locator_hex}
            for addr in liste[:20]:
                try:
                    p = Peer(addr, timeout=12)
                    p.handschlag()
                except (OSError, ConnectionError, TimeoutError, struct.error, IndexError):
                    continue
                try:
                    if p.hoehe <= tip_hoehe:
                        continue
                    neu = []
                    prev, hoehe = locator[0], tip_hoehe
                    for runde in range(10):
                        roh = p.koepfe(locator if runde == 0 else [prev], warten=30)
                        if runde == 0 and roh:
                            # Anschluss: der Vorgaenger des ersten Kopfs ist einer aus unserem Locator
                            anschluss = roh[0][4:36]
                            if anschluss not in hoehe_von:
                                break
                            prev, hoehe = anschluss, hoehe_von[anschluss]
                        stueck = koepfe_pruefen(roh, hoehe, prev)
                        if not stueck:
                            break
                        neu += stueck
                        hoehe, prev = stueck[-1][0], bytes.fromhex(stueck[-1][1])[::-1]
                        if len(roh) < 160:
                            break
                    for _, h, prv, zeit, nbits in neu:
                        self.q.put(("kopf", {"hash": h, "prev": prv, "zeit": zeit, "nbits": nbits}))
                    log(f"nachziehen: {len(neu)} koepfe von einem peer, bis hoehe {hoehe}")
                    if neu:
                        return
                except (OSError, ConnectionError, TimeoutError, struct.error, IndexError, ValueError) as e:
                    log(f"nachziehen: peer verworfen ({type(e).__name__})")
                finally:
                    p.zu()
            log("nachziehen: kein peer mit neueren koepfen")
        except Exception as e:
            log(f"nachziehen: {type(e).__name__}")
        finally:
            self.nachziehen_laeuft = False

    # ------------------------------------------------------------ probe
    def probe(self):
        """Protokollversionen erreichbarer Peers (Handschlag, dann trennen)."""
        liste = adressen(self.cache_pfad, versuche=(5,))[0][:PROBE_HOECHSTENS]
        versionen, lock = [], threading.Lock()

        def eins(addr):
            try:
                p = Peer(addr, timeout=10)
                p.handschlag()
                with lock:
                    versionen.append(p.version)
                p.zu()
            except (OSError, ConnectionError, TimeoutError, struct.error, IndexError):
                pass

        for i in range(0, len(liste), PROBE_THREADS):
            ts = [threading.Thread(target=eins, args=(a,), daemon=True) for a in liste[i:i + PROBE_THREADS]]
            for t in ts:
                t.start()
            for t in ts:
                t.join(40)
        log(f"probe: {len(versionen)} von {len(liste)} adressen antworteten")
        return versionen
