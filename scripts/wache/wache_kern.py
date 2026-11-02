"""wache_kern.py - Kern der Upgrade-Wache, ohne Bezug auf eine bestimmte Chain.

Ben, 29.10.2026: Rund um eine Netz-Aktivierung erkennt unser eigener Zuhoerer
Stoerungen und meldet sie intern (#ops-log). Prototyp fuer ein spaeteres Abo
je Chain, deshalb steht hier nichts Chain-Eigenes: Aktivierungshoehe,
Zielabstand, Schwellen und Mindest-Protokollversion kommen aus der
Konfiguration (scripts/wache/ketten/<kette>.json), die Daten aus einer Quelle
(Live-Zuhoerer oder Aufzeichnung), die nur vier Dinge liefert:

  anker(zeilen)                    bekannte Kette: (hoehe, hash, zeit, nbits)
  kopf(hash, prev, zeit, nbits)    ein Blockkopf
  ankuendigung(t_ms, peer, hash)   ein Peer kuendigt einen Block an
  verbindungen(n)                  so viele Peers sind gerade verbunden
  und auf Anfrage probe() -> Liste der Protokollversionen erreichbarer Peers

Signale (Ben, Schwellen in der Konfiguration):
  blockpause      kein neuer Block seit hinweis_s / alarm_s
  kettenspaltung  zwei Zweige ab der Aktivierungshoehe, je Seite mindestens
                  min_peers Peers, beide mehr als min_tiefe Bloecke tief
  reorg           unsere Spitze springt auf einen Zweig, der mindestens
                  min_tiefe Bloecke unter der alten Spitze abzweigt
  peers_vor_upgrade  Anteil erreichbarer Peers mit Protokoll unter dem
                  Mindestwert, zur Aktivierung und nach 6 h (nur Anteil)
  median_abstand  Median der letzten n Abstaende (Kopf-Zeitstempel) ueber
                  faktor x Zielabstand der Hoehe
  eigene_sicht    (zusaetzlich) weniger als min_verbindungen Peers: dann
                  sagt eine Blockpause nichts, wir melden unsere Blindheit

Meldungen: hoechstens eine je Signal und sperre_s (30 min). Ausnahme: der
Aufstieg von Hinweis zu Alarm geht einmal sofort raus. Endet ein Signal,
nach dem gemeldet wurde, folgt eine Entwarnung. Jede Stufenaenderung steht
im Log (utc, hoehe, signal, wert, schwelle, stufe). Keine Adressen.
"""
import csv
import json
import os
import statistics
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

RANG = {None: 0, "info": 1, "hinweis": 2, "alarm": 3}
TITEL = {
    "blockpause": "blockpause",
    "kettenspaltung": "kettenspaltung",
    "reorg": "reorg",
    "peers_vor_upgrade": "peers vor dem upgrade",
    "median_abstand": "median der letzten abstaende",
    "eigene_sicht": "eigene sicht (zu wenige verbindungen)",
    "wache": "wache",
}


def utc(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ts(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def arbeit(nbits):
    """Erwartete Hashes je Block aus nBits (kompaktes Ziel), wie im Konsens."""
    b = int(nbits, 16) if isinstance(nbits, str) else nbits
    exp, mant = b >> 24, b & 0x007FFFFF
    ziel = mant << (8 * (exp - 3)) if exp > 3 else mant >> (8 * (3 - exp))
    return (1 << 256) // (ziel + 1) if ziel > 0 else 0


class Uhr:
    """Echte Uhr; die Simulation ersetzt sie durch eine, die sie selbst stellt."""
    def jetzt(self):
        return time.time()


class SimUhr:
    def __init__(self, t):
        self.t = t

    def jetzt(self):
        return self.t


class Melder:
    """Schickt eine Zeile an einen Discord-Webhook aus der Umgebung.

    scharf=False: nur ausgeben (Trockenlauf). Die Webhook-Adresse steht nur in
    der Umgebungsvariable, die die Konfiguration nennt, nie in einer Datei
    oder im Log.
    """
    def __init__(self, webhook_env, scharf, test=False, nur=None):
        self.env, self.scharf, self.test = webhook_env, scharf, test
        self.nur = nur          # Simulation: nur diese (signal, stufe) wirklich senden
        self.gesendet = []

    def senden(self, text, signal=None, stufe=None):
        if self.test:
            text = "TEST " + text
        self.gesendet.append(text)
        echt = self.scharf and (self.nur is None or (signal, stufe) in self.nur)
        if not echt:
            print(f"[trocken] {text}", flush=True)
            return True
        if self.nur is not None:
            self.nur.discard((signal, stufe))
        hook = os.environ.get(self.env, "").strip()
        if not hook.startswith(("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/")):
            print(f"meldung nicht gesendet, {self.env} fehlt oder ist kein discord-webhook", flush=True)
            return False
        body = json.dumps({"content": text, "allowed_mentions": {"parse": []}}).encode()
        req = urllib.request.Request(hook, data=body, headers={
            "Content-Type": "application/json", "User-Agent": "kaspa-pulse-wache/0.1"})
        for versuch in range(3):
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    print(f"meldung gesendet, http {r.status}: {text}", flush=True)
                    return True
            except urllib.error.HTTPError as e:
                print(f"meldung abgelehnt, http {e.code}", flush=True)
                if e.code != 429:
                    return False
            except (urllib.error.URLError, OSError) as e:
                print(f"meldung nicht erreicht, {type(e).__name__}", flush=True)
            time.sleep(5 * (versuch + 1))
        return False


class Kern:
    def __init__(self, cfg, uhr, melder, log_pfad, zustand_pfad=None, quelle=None):
        self.cfg, self.uhr, self.melder = cfg, uhr, melder
        self.log_pfad, self.zustand_pfad, self.quelle = log_pfad, zustand_pfad, quelle
        self.knoten = {}           # hash -> dict(prev, zeit, nbits, hoehe, arbeit, erst_ms, peers)
        self.wartend = {}          # prev -> [hash], Koepfe ohne bekannten Vorgaenger
        self.tip = None
        self.verbunden = 0
        self.wenig_seit = None
        self.reorgs = []           # (zeit, tiefe, hoehe)
        self.letzter_reorg = None
        self.z = {"signale": {}, "aktiv_gesehen_utc": None, "proben": {}}
        if zustand_pfad and os.path.exists(zustand_pfad):
            with open(zustand_pfad) as f:
                self.z.update(json.load(f))
        if log_pfad and not os.path.exists(log_pfad):
            os.makedirs(os.path.dirname(log_pfad) or ".", exist_ok=True)
            with open(log_pfad, "w", newline="") as f:
                csv.writer(f).writerow(["utc", "hoehe", "signal", "wert", "schwelle", "stufe"])

    # ------------------------------------------------------------ eingang
    def anker(self, zeilen):
        """zeilen: (hoehe, hash, zeit, nbits) einer bekannten Kette, aufsteigend."""
        kum = 0
        for hoehe, h, zeit, nbits in zeilen:
            kum += arbeit(nbits)
            k = self.knoten.get(h) or {"prev": None, "erst_ms": None, "peers": set()}
            k.update(zeit=zeit, nbits=nbits, hoehe=hoehe, arbeit=kum)
            self.knoten[h] = k
        # Vorgaenger nachtragen, damit die Kette verknuepft ist
        hs = [z[1] for z in zeilen]
        for a, b in zip(hs, hs[1:]):
            self.knoten[b]["prev"] = a
        if zeilen and (self.tip is None or self.knoten[hs[-1]]["arbeit"] >= self.knoten[self.tip]["arbeit"]):
            self.tip = hs[-1]
            self.knoten[self.tip]["erst_ms"] = self.knoten[self.tip]["erst_ms"] or self.uhr.jetzt() * 1000
        for h in hs:
            self._anhaengen(h)

    def kopf(self, h, prev, zeit, nbits):
        k = self.knoten.get(h)
        if k and k.get("hoehe") is not None:
            return
        k = k or {"erst_ms": None, "peers": set()}
        k.update(prev=prev, zeit=zeit, nbits=nbits, hoehe=None, arbeit=None)
        if k["erst_ms"] is None:
            k["erst_ms"] = self.uhr.jetzt() * 1000
        self.knoten[h] = k
        p = self.knoten.get(prev)
        if p and p.get("hoehe") is not None:
            self._verknuepfen(h)
        else:
            self.wartend.setdefault(prev, []).append(h)

    def ankuendigung(self, t_ms, peer, h):
        k = self.knoten.setdefault(h, {"prev": None, "zeit": None, "nbits": None, "hoehe": None,
                                       "arbeit": None, "erst_ms": None, "peers": set()})
        k["peers"].add(peer)
        if k["erst_ms"] is None or t_ms < k["erst_ms"]:
            k["erst_ms"] = t_ms

    def verbindungen(self, n):
        self.verbunden = n

    def braucht_anker(self):
        """Koepfe, deren Vorgaenger wir nicht kennen: die Quelle soll neu verankern."""
        return any(p not in self.knoten for p in self.wartend)

    # ------------------------------------------------------------ baum
    def _verknuepfen(self, h):
        k, p = self.knoten[h], self.knoten[self.knoten[h]["prev"]]
        k["hoehe"] = p["hoehe"] + 1
        k["arbeit"] = p["arbeit"] + arbeit(k["nbits"])
        self._spitze_pruefen(h)
        self._anhaengen(h)

    def _anhaengen(self, h):
        for kind in self.wartend.pop(h, []):
            if self.knoten[kind].get("hoehe") is None:
                self._verknuepfen(kind)

    def _vorfahren(self, h, n):
        out = []
        while h and len(out) < n and h in self.knoten:
            out.append(h)
            h = self.knoten[h]["prev"]
        return out

    def _abzweig(self, a, b):
        """Gemeinsamer Vorfahre zweier Hashes (ueber die Hoehen)."""
        while a != b:
            ka, kb = self.knoten.get(a), self.knoten.get(b)
            if ka is None or kb is None:
                return None
            if ka["hoehe"] >= kb["hoehe"]:
                a = ka["prev"]
            else:
                b = kb["prev"]
        return a

    def _spitze_pruefen(self, h):
        k = self.knoten[h]
        if self.tip is not None and k["arbeit"] <= self.knoten[self.tip]["arbeit"]:
            return
        alt = self.tip
        self.tip = h
        if alt is None:
            return
        gem = self._abzweig(alt, h)
        if gem is not None and gem != alt:
            # Tiefe: so viele Bloecke der alten Spitze fallen aus unserer Kette.
            tiefe = self.knoten[alt]["hoehe"] - self.knoten[gem]["hoehe"]
            self.reorgs.append((self.uhr.jetzt(), tiefe, k["hoehe"]))

    # ------------------------------------------------------------ fenster
    def fenster(self, jetzt):
        f = self.cfg["fenster"]
        anker = self.z.get("aktiv_gesehen_utc") or self.cfg["aktivierung"]["erwartet_utc"]
        start = ts(self.cfg["aktivierung"]["erwartet_utc"]) - f["vor_h"] * 3600
        ende = ts(anker) + f["nach_h"] * 3600
        return start <= jetzt < ende, start, ende

    def ziel_s(self, hoehe):
        a = self.cfg["aktivierung"]
        if hoehe is not None and hoehe >= a["hoehe"]:
            return self.cfg["ziel_nach_s"]
        return self.cfg["ziel_s"]

    # ------------------------------------------------------------ takt
    def takt(self):
        jetzt = self.uhr.jetzt()
        offen, _, _ = self.fenster(jetzt)
        if not offen:
            return False
        s = self.cfg["signale"]
        tip = self.knoten.get(self.tip) if self.tip else None
        hoehe = tip["hoehe"] if tip else None
        akt = self.cfg["aktivierung"]["hoehe"]

        # Aktivierung gesehen?
        if hoehe is not None and hoehe >= akt and not self.z.get("aktiv_gesehen_utc"):
            blk = self._block_auf_hoehe(akt)
            t = (self.knoten[blk]["erst_ms"] / 1000) if blk and self.knoten[blk]["erst_ms"] else jetzt
            self.z["aktiv_gesehen_utc"] = datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            self.log(hoehe, "wache", akt, akt, "aktivierung_gesehen")

        # eigene Sicht
        e = s["eigene_sicht"]
        if self.verbunden < e["min_verbindungen"]:
            self.wenig_seit = self.wenig_seit or jetzt
        else:
            self.wenig_seit = None
        blind = self.wenig_seit is not None and jetzt - self.wenig_seit >= e["nach_s"]
        self.setzen("eigene_sicht", "hinweis" if blind else None, self.verbunden,
                    e["min_verbindungen"], hoehe, einheit="verbindungen", vergleich="unter")

        # a) Blockpause, nur mit eigener Sicht
        b = s["blockpause"]
        if tip and tip["erst_ms"] and not blind:
            pause = jetzt - tip["erst_ms"] / 1000
            st = "alarm" if pause >= b["alarm_s"] else "hinweis" if pause >= b["hinweis_s"] else None
            schw = b["alarm_s"] if st == "alarm" else b["hinweis_s"]
            self.setzen("blockpause", st, round(pause), schw, hoehe, einheit="s")

        # b) Kettenspaltung ab der Aktivierungshoehe
        k = s["kettenspaltung"]
        tiefe = self._spaltung(akt, k["min_peers"], k["ruhe_s"], jetzt)
        self.setzen("kettenspaltung", "alarm" if tiefe > k["min_tiefe"] else None, tiefe,
                    k["min_tiefe"], hoehe, einheit="bloecke", vergleich="ueber")

        # c) Reorg ab Tiefe min_tiefe; endet nach ende_bloecke stabilen Bloecken
        r = s["reorg"]
        for t, tf, h_neu in self.reorgs:
            # Jeder Spitzenwechsel steht im Log, auch Tiefe 1 (fuer den Bericht danach).
            self.log(h_neu, "reorg_gesehen", tf, r["min_tiefe"], "info", zeit=t)
            if tf >= r["min_tiefe"]:
                self.letzter_reorg = (tf, h_neu)
        self.reorgs = []
        if self.letzter_reorg and hoehe is not None and hoehe - self.letzter_reorg[1] >= r["ende_bloecke"]:
            self.letzter_reorg = None
        self.setzen("reorg", "alarm" if self.letzter_reorg else None,
                    self.letzter_reorg[0] if self.letzter_reorg else 0, r["min_tiefe"], hoehe, einheit="bloecke")

        # e) Median der letzten n Abstaende
        m = s["median_abstand"]
        if self.tip:
            kette = self._vorfahren(self.tip, m["n"] + 1)
            zeiten = [self.knoten[x]["zeit"] for x in reversed(kette) if self.knoten[x].get("zeit") is not None]
            if len(zeiten) == m["n"] + 1:
                med = statistics.median(b2 - a2 for a2, b2 in zip(zeiten, zeiten[1:]))
                schw = m["faktor"] * self.ziel_s(hoehe)
                self.setzen("median_abstand", "alarm" if med > schw else None, round(med, 1), schw, hoehe,
                            einheit="s")

        # d) Peers vor dem Upgrade, zur Aktivierung und nach den Versaetzen
        p = s["peers_vor_upgrade"]
        if self.z.get("aktiv_gesehen_utc") and self.quelle is not None:
            t_akt = ts(self.z["aktiv_gesehen_utc"])
            for vers_h in p["zeitpunkte_h"]:
                schl = str(vers_h)
                if schl in self.z["proben"] or jetzt < t_akt + vers_h * 3600:
                    continue
                versionen = self.quelle.probe()
                if not versionen:
                    continue
                alt = sum(1 for v in versionen if v < self.cfg["min_protokoll"])
                anteil = round(100 * alt / len(versionen), 1)
                self.z["proben"][schl] = {"utc": utc(jetzt), "peers": len(versionen), "vor_upgrade": alt,
                                          "anteil_prozent": anteil}
                titel = f"aktivierung + {vers_h} h" if vers_h else "aktivierung"
                self.log(hoehe, "peers_vor_upgrade", anteil, self.cfg["min_protokoll"], "info")
                self.melden("info", "peers_vor_upgrade", hoehe, jetzt,
                            f"{anteil} % ({alt} von {len(versionen)} erreichbaren peers)",
                            f"protokoll unter {self.cfg['min_protokoll']}, {titel}")
        self.speichern()
        return True

    def _block_auf_hoehe(self, hoehe):
        for h in self._vorfahren(self.tip, 100000):
            if self.knoten[h]["hoehe"] == hoehe:
                return h
            if self.knoten[h]["hoehe"] < hoehe:
                return None
        return None

    def _spaltung(self, ab_hoehe, min_peers, ruhe_s, jetzt):
        """Tiefe des kuerzeren Zweigs der tiefsten aktiven Spaltung ab ab_hoehe, sonst 0."""
        kinder = {}
        for h, k in self.knoten.items():
            if k.get("hoehe") is not None and k["hoehe"] >= ab_hoehe and k["prev"]:
                kinder.setdefault(k["prev"], []).append(h)
        if not kinder:
            return 0

        def zweig(h):
            """(tiefe, peers, letzte erst_ms) des Teilbaums ab h, laengster Pfad."""
            stapel, tiefe, peers, letzte = [(h, 1)], 0, set(), 0
            while stapel:
                x, d = stapel.pop()
                tiefe = max(tiefe, d)
                peers |= self.knoten[x]["peers"]
                letzte = max(letzte, self.knoten[x]["erst_ms"] or 0)
                stapel.extend((c, d + 1) for c in kinder.get(x, []))
            return tiefe, peers, letzte

        beste = 0
        for vater, ks in kinder.items():
            if len(ks) < 2:
                continue
            zweige = sorted((zweig(c) for c in ks), key=lambda z: z[0], reverse=True)
            a, b = zweige[0], zweige[1]
            if len(a[1]) >= min_peers and len(b[1]) >= min_peers and jetzt - b[2] / 1000 < ruhe_s:
                beste = max(beste, b[0])
        return beste

    # ------------------------------------------------------------ zustand und meldung
    def setzen(self, signal, stufe, wert, schwelle, hoehe, einheit="", vergleich="ab"):
        jetzt = self.uhr.jetzt()
        z = self.z["signale"].setdefault(signal, {"stufe": None, "seit": None, "gemeldet_utc": None,
                                                  "gemeldet_stufe": None, "episode_gemeldet": False})
        alt = z["stufe"]
        if stufe == alt:
            return
        sperre = self.cfg["meldung"]["sperre_s"]
        if stufe is None:
            self.log(hoehe, signal, wert, schwelle, "entwarnung")
            if z["episode_gemeldet"]:
                dauer = round((jetzt - (z["seit"] or jetzt)) / 60)
                self.melden("entwarnung", signal, hoehe, jetzt, f"{wert} {einheit}".strip(),
                            f"{vergleich} {schwelle} {einheit}".strip(), extra=f"dauer {dauer} min")
            z.update(stufe=None, seit=None, episode_gemeldet=False)
            return
        self.log(hoehe, signal, wert, schwelle, stufe)
        if alt is None:
            z["seit"] = jetzt
        z["stufe"] = stufe
        letzte = ts(z["gemeldet_utc"]) if z["gemeldet_utc"] else None
        frei = letzte is None or jetzt - letzte >= sperre
        aufstieg = RANG[stufe] > RANG[z["gemeldet_stufe"]] and z["episode_gemeldet"]
        if frei or aufstieg:
            self.melden(stufe, signal, hoehe, jetzt, f"{wert} {einheit}".strip(),
                        f"{vergleich} {schwelle} {einheit}".strip())
            z.update(gemeldet_utc=datetime.fromtimestamp(jetzt, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                     gemeldet_stufe=stufe, episode_gemeldet=True)

    def melden(self, stufe, signal, hoehe, jetzt, wert, schwelle, extra=None):
        h = f"{hoehe:,}" if hoehe is not None else "unbekannt"
        teile = [f"upgrade-wache {self.cfg['kette']}", f"{stufe.upper()} {TITEL.get(signal, signal)}",
                 f"hoehe {h}", f"{utc(jetzt)} UTC", f"wert {wert}", f"schwelle {schwelle}"]
        if extra:
            teile.append(extra)
        self.melder.senden(" | ".join(teile), signal=signal, stufe=stufe)

    def log(self, hoehe, signal, wert, schwelle, stufe, zeit=None):
        if not self.log_pfad:
            return
        with open(self.log_pfad, "a", newline="") as f:
            csv.writer(f).writerow([utc(zeit or self.uhr.jetzt()), hoehe if hoehe is not None else "",
                                    signal, wert, schwelle, stufe])

    def speichern(self):
        if self.zustand_pfad:
            tmp = self.zustand_pfad + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.z, f, indent=1)
            os.replace(tmp, self.zustand_pfad)

    def stand(self):
        tip = self.knoten.get(self.tip) if self.tip else None
        return {"hoehe": tip["hoehe"] if tip else None, "verbunden": self.verbunden,
                "knoten": len(self.knoten), "aktiv": {k: v["stufe"] for k, v in self.z["signale"].items() if v["stufe"]}}
