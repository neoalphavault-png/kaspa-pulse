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

probe(): Handschlag mit den Adressen aus den DNS-Seeds, nur die gemeldete
Protokollversion, dann trennen. Keine Adresse wird gespeichert oder gedruckt.
"""
import csv
import gzip
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
PROBE_HOECHSTENS = 80
PROBE_THREADS = 20


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
        threading.Thread(target=self._verbinden_schleife, daemon=True).start()

    # ------------------------------------------------------------ verbindungen
    def _verbinden_schleife(self):
        adressen, seeds_zeit, versucht = peers_finden(), time.time(), set()
        while time.time() < self.z.ende:
            if time.time() - seeds_zeit > zcash_lauscher.SEEDS_NEU_S:
                adressen, seeds_zeit, versucht = peers_finden(), time.time(), set()
            try:
                self.z.verbinden(adressen, versucht)
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
        if kern.tip is None:
            self.anker_anstossen(dringend=True)
        elif kern.braucht_anker():
            self.anker_anstossen()
        return n

    # ------------------------------------------------------------ probe
    def probe(self):
        """Protokollversionen erreichbarer Peers (Handschlag, dann trennen)."""
        adressen = peers_finden()[:PROBE_HOECHSTENS]
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

        for i in range(0, len(adressen), PROBE_THREADS):
            ts = [threading.Thread(target=eins, args=(a,), daemon=True) for a in adressen[i:i + PROBE_THREADS]]
            for t in ts:
                t.start()
            for t in ts:
                t.join(40)
        log(f"probe: {len(versionen)} von {len(adressen)} adressen antworteten")
        return versionen
