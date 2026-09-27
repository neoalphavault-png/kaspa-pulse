#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""node_zaehler.py, von aussen erreichbare Kaspa-Nodes zaehlen (Pruefbranch).

Frage vom 26.09.2026. Freigabe Ben 27.09.2026, nur auf pruefung/nodes-2026-09-26,
nie mergen. Die Regeln aus der Freigabe stehen hier, damit sie mit dem Code
wandern:

  - Der Zaehler verhaelt sich wie ein gewoehnlicher Node: Version, Verack,
    Ready, RequestAddresses, danach wird die Verbindung geschlossen. Keine
    weiteren Nachrichten, keine Blockanfragen, keine Antwort auf Anfragen des
    Gegenuebers. Eine Verbindung je Adresse und Lauf, hoechstens 100
    gleichzeitig, 5 Sekunden je Adresse. User-Agent /kaspa-pulse-counter:0.1/,
    nicht als kaspad ausgegeben.
  - Nachrichtenbeschreibungen aus rusty-kaspa protocol/p2p/proto, fester
    Commit, Hash und sha256 der Dateien stehen im Log.
  - Gezaehlt wird nur, wer im Version-Handshake "kaspa-mainnet" meldet.
  - IP-ADRESSEN ERSCHEINEN NIRGENDS. Das Repo ist oeffentlich, Logs und
    Artifacts damit auch. Deshalb gibt es keine Rohliste, und Fehlertexte von
    gRPC werden nie gedruckt (sie enthalten die Adresse), nur ihre Klasse.
    Im Log stehen ausschliesslich Zaehlwerte.

    python3 scripts/node_zaehler.py handshake   ein Seeder-Node, Schritt 1
    python3 scripts/node_zaehler.py crawl       voller Lauf, Schritt 2
"""

import asyncio
import collections
import contextlib
import datetime as dt
import hashlib
import importlib
import ipaddress
import os
import random
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

RUSTY_COMMIT = "01b532e8b553523216471682649693af92f0fd16"   # 22.09.2026
PROTO_URL = ("https://raw.githubusercontent.com/kaspanet/rusty-kaspa/%s/"
             "protocol/p2p/proto/%s")
PROTO_DATEIEN = ("p2p.proto", "messages.proto")
# rusty-kaspa consensus/core/src/config/params.rs, MAINNET_PARAMS.dns_seeders
DNS_SEEDER = [
    "mainnet-dnsseed-1.kaspanet.org", "mainnet-dnsseed-2.kaspanet.org",
    "seeder1.kaspad.net", "seeder2.kaspad.net", "seeder3.kaspad.net",
    "seeder4.kaspad.net", "kaspadns.kaspacalc.net", "n-mainnet.kaspa.ws",
    "dnsseeder-kaspa-mainnet.x-con.at",
]
NETZ = "kaspa-mainnet"
PORT = 16111
PROTOKOLL = 11            # flow_context.rs PROTOCOL_VERSION im selben Commit
USER_AGENT = "/kaspa-pulse-counter:0.1/"
GLEICHZEITIG = 100
ZEITLIMIT = 5.0
HOECHSTENS = 30000        # obergrenze an adressen je lauf, reine sicherung

pb = None                 # messages_pb2, nach dem Uebersetzen
grpc_pb = None            # messages_pb2_grpc


def vorbereiten():
    """grpcio installieren, Protos am festen Commit holen und uebersetzen."""
    global pb, grpc_pb
    ziel = tempfile.mkdtemp(prefix="kp-proto-")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check",
                    "grpcio", "grpcio-tools", "--target", ziel + "/lib"], check=True)
    sys.path.insert(0, ziel + "/lib")
    import grpc
    print("grpcio %s" % grpc.__version__)
    print("rusty-kaspa commit %s" % RUSTY_COMMIT)
    for name in PROTO_DATEIEN:
        with urllib.request.urlopen(PROTO_URL % (RUSTY_COMMIT, name), timeout=30) as r:
            daten = r.read()
        open(os.path.join(ziel, name), "wb").write(daten)
        print("  %-16s sha256 %s" % (name, hashlib.sha256(daten).hexdigest()))
    from grpc_tools import protoc
    code = protoc.main(["protoc", "-I", ziel, "--python_out", ziel,
                        "--grpc_python_out", ziel] + [os.path.join(ziel, n) for n in PROTO_DATEIEN])
    if code != 0:
        raise SystemExit("FEHLER protoc %s" % code)
    sys.path.insert(0, ziel)
    pb = importlib.import_module("messages_pb2")
    grpc_pb = importlib.import_module("messages_pb2_grpc")


def version_nachricht():
    p2p = importlib.import_module("p2p_pb2")
    return pb.KaspadMessage(version=p2p.VersionMessage(
        protocolVersion=PROTOKOLL,
        services=0,
        timestamp=int(time.time() * 1000),
        id=os.urandom(16),
        userAgent=USER_AGENT,
        disableRelayTx=True,
        network=NETZ,
    ))


def fehlerklasse(exc):
    """Klasse eines Fehlers ohne seinen Text. Der Text traegt die Adresse."""
    if isinstance(exc, asyncio.TimeoutError):
        return "zeitlimit"
    code = getattr(exc, "code", None)
    if callable(code):
        try:
            return "grpc_%s" % code().name.lower()
        except Exception:                          # noqa: BLE001
            pass
    return type(exc).__name__


async def besuche(ip, port):
    """Eine Verbindung, ein Handshake, eine Adressanfrage, dann zu.
    Gibt ein Ergebnis ohne Adresse zurueck, plus die gelieferten Adressen."""
    import grpc
    erg = {"stufe": "keine", "netz": None, "protokoll": None, "agent": None,
           "adressen": 0, "fehler": None}
    neu = []
    ziel = "[%s]:%d" % (ip, port) if ":" in ip else "%s:%d" % (ip, port)
    kanal = grpc.aio.insecure_channel(ziel, options=[
        ("grpc.max_receive_message_length", 64 * 1024 * 1024),
        ("grpc.enable_retries", 0),
        # kein neuer verbindungsversuch innerhalb des zeitlimits: eine
        # verbindung je adresse und lauf
        ("grpc.initial_reconnect_backoff_ms", 60000),
        ("grpc.min_reconnect_backoff_ms", 60000),
        ("grpc.max_reconnect_backoff_ms", 60000)])
    ruf = None
    try:
        async def ablauf():
            nonlocal ruf
            await kanal.channel_ready()
            erg["stufe"] = "verbindung"
            ruf = grpc_pb.P2PStub(kanal).MessageStream()
            await ruf.write(version_nachricht())
            hat_version = hat_verack = False
            while not (hat_version and hat_verack):
                m = await ruf.read()
                if m is grpc.aio.EOF:
                    return
                art = m.WhichOneof("payload")
                if art == "version":
                    erg["netz"] = m.version.network
                    erg["protokoll"] = m.version.protocolVersion
                    erg["agent"] = m.version.userAgent
                    hat_version = True
                    if m.version.network != NETZ:
                        erg["stufe"] = "anderes_netz"
                        return
                    await ruf.write(pb.KaspadMessage(verack=importlib.import_module("p2p_pb2").VerackMessage()))
                elif art == "verack":
                    hat_verack = True
            erg["stufe"] = "version"
            await ruf.write(pb.KaspadMessage(ready=importlib.import_module("p2p_pb2").ReadyMessage()))
            while True:
                m = await ruf.read()
                if m is grpc.aio.EOF:
                    return
                if m.WhichOneof("payload") == "ready":
                    break
            erg["stufe"] = "handshake"
            await ruf.write(pb.KaspadMessage(requestAddresses=importlib.import_module("p2p_pb2").RequestAddressesMessage(
                includeAllSubnetworks=False)))
            while True:
                m = await ruf.read()
                if m is grpc.aio.EOF:
                    return
                if m.WhichOneof("payload") == "addresses":
                    for a in m.addresses.addressList:
                        roh = bytes(a.ip)
                        try:
                            addr = ipaddress.ip_address(roh)
                        except ValueError:
                            continue
                        if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
                            addr = addr.ipv4_mapped
                        neu.append((str(addr), int(a.port)))
                    erg["adressen"] = len(m.addresses.addressList)
                    erg["stufe"] = "adressen"
                    return
        await asyncio.wait_for(ablauf(), ZEITLIMIT)
    except Exception as exc:                       # noqa: BLE001
        erg["fehler"] = fehlerklasse(exc)
    finally:
        try:
            if ruf is not None:
                ruf.cancel()
            await kanal.close()
        except Exception:                          # noqa: BLE001
            pass
    return erg, neu


def seeder_adressen():
    alle, je = set(), {}
    for s in DNS_SEEDER:
        n = set()
        try:
            for _, _, _, _, sa in socket.getaddrinfo(s, PORT, proto=socket.IPPROTO_TCP):
                n.add((sa[0], PORT))
        except OSError:
            pass
        je[s] = len(n)
        alle |= n
    return alle, je


def agent_gruppe(agent):
    """name:version je Teil, Kommentare in Klammern weg (koennen Namen tragen)."""
    if not agent:
        return "(leer)"
    teile = [re.sub(r"\(.*?\)", "", t) for t in agent.strip("/").split("/") if t]
    return "/" + "/".join(teile) + "/"


def ist_v6(ip):
    return ":" in ip


# ------------------------------------------------------------------ befehle

async def handshake_probe():
    start = dt.datetime.now(dt.timezone.utc)
    seeds, je = seeder_adressen()
    print("seeder: %s" % ", ".join("%s %d" % (s, n) for s, n in je.items()))
    v4 = sorted(a for a in seeds if not ist_v6(a[0]))
    random.shuffle(v4)
    print("ipv4-adressen aus den seedern: %d, versucht werden hoechstens 5 nacheinander" % len(v4))
    for i, (ip, port) in enumerate(v4[:5], 1):
        erg, neu = await besuche(ip, port)
        n4 = sum(1 for a in neu if not ist_v6(a[0]))
        print("versuch %d: stufe %s, netz %s, protokoll %s, agent %s, adressen %d "
              "(ipv4 %d, ipv6 %d), fehlerklasse %s"
              % (i, erg["stufe"], erg["netz"], erg["protokoll"], agent_gruppe(erg["agent"]),
                 erg["adressen"], n4, len(neu) - n4, erg["fehler"]))
        if erg["stufe"] == "adressen":
            print("\nSCHRITT 1 STEHT: handshake im mainnet und adressanfrage vom runner aus")
            break
    else:
        print("\nSCHRITT 1 GESCHEITERT: kein handshake in 5 versuchen. stoppen, nicht crawlen.")
        return 1
    print("start %s, ende %s utc" % (start.strftime("%H:%M:%S"),
                                   dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S")))
    return 0


async def crawl():
    start = dt.datetime.now(dt.timezone.utc)
    t0 = time.monotonic()
    seeds, je = seeder_adressen()
    print("seeder: %s" % ", ".join("%s %d" % (s, n) for s, n in je.items()))
    gesehen = set(seeds)
    offen = collections.deque(sorted(seeds))
    ergebnisse = []
    sperre = asyncio.Semaphore(GLEICHZEITIG)
    laufend = set()

    async def eins(ip, port):
        async with sperre:
            erg, neu = await besuche(ip, port)
        erg["v6"] = ist_v6(ip)
        erg["port"] = "16111" if port == PORT else "anderer"
        ergebnisse.append(erg)
        for a in neu:
            if a not in gesehen and len(gesehen) < HOECHSTENS:
                gesehen.add(a)
                offen.append(a)

    while offen or laufend:
        while offen and len(laufend) < GLEICHZEITIG * 2:
            ip, port = offen.popleft()
            laufend.add(asyncio.create_task(eins(ip, port)))
        fertig, laufend = await asyncio.wait(laufend, return_when=asyncio.FIRST_COMPLETED)
    ende = dt.datetime.now(dt.timezone.utc)

    def z(filt):
        return sum(1 for e in ergebnisse if filt(e))

    stufen = ("verbindung", "version", "handshake", "adressen")
    erreicht = lambda e, s: e["stufe"] in stufen[stufen.index(s):]   # noqa: E731
    mainnet_hs = lambda e: e["netz"] == NETZ and erreicht(e, "handshake")   # noqa: E731

    print("\nMESSZEIT start %s utc, ende %s utc, laufzeit %.0f s"
          % (start.strftime("%Y-%m-%d %H:%M:%S"), ende.strftime("%Y-%m-%d %H:%M:%S"),
             time.monotonic() - t0))
    print("regeln: %d gleichzeitig, %.0f s je adresse, eine verbindung je adresse, "
          "agent %s, protokoll %d" % (GLEICHZEITIG, ZEITLIMIT, USER_AGENT, PROTOKOLL))
    print("\n%-44s %8s %8s %8s" % ("", "gesamt", "ipv4", "ipv6"))
    for name, f in [
        ("gesehene adressen (versucht)", lambda e: True),
        ("verbindungsaufbau ok", lambda e: erreicht(e, "verbindung")),
        ("version erhalten", lambda e: e["netz"] is not None),
        ("  davon anderes netz", lambda e: e["netz"] not in (None, NETZ)),
        ("HANDSHAKE OK, MAINNET", mainnet_hs),
        ("  davon adressen geliefert", lambda e: mainnet_hs(e) and e["stufe"] == "adressen"),
    ]:
        print("%-44s %8d %8d %8d" % (name, z(f), z(lambda e: f(e) and not e["v6"]),
                                     z(lambda e: f(e) and e["v6"])))
    print("\nhandshake ok mainnet nach port: 16111 %d, anderer %d"
          % (z(lambda e: mainnet_hs(e) and e["port"] == "16111"),
             z(lambda e: mainnet_hs(e) and e["port"] == "anderer")))
    print("\nprotokollversionen (handshake ok mainnet): %s" % dict(sorted(
        collections.Counter(e["protokoll"] for e in ergebnisse if mainnet_hs(e)).items())))
    agenten = collections.Counter(agent_gruppe(e["agent"]) for e in ergebnisse if mainnet_hs(e))
    print("user-agent-versionen (handshake ok mainnet, kommentare entfernt):")
    for a, n in agenten.most_common(15):
        print("  %5d  %s" % (n, a))
    rest = sum(agenten.values()) - sum(n for _, n in agenten.most_common(15))
    if rest:
        print("  %5d  (uebrige)" % rest)
    print("\nfehlerklassen (nicht erreicht): %s" % dict(collections.Counter(
        e["fehler"] for e in ergebnisse if e["fehler"]).most_common(10)))
    if len(gesehen) >= HOECHSTENS:
        print("HINWEIS obergrenze %d adressen erreicht, lauf unvollstaendig" % HOECHSTENS)
    print("\nBESCHRIFTUNG: von aussen erreichbare Nodes (Handshake im Mainnet), von uns gezaehlt: %d"
          % z(mainnet_hs))
    return 0


@contextlib.contextmanager
def stumm_stderr():
    """grpc schreibt Verbindungsfehler mit Adresse nach stderr. Waehrend der
    Verbindungen geht stderr deshalb ins Leere, auf Ebene des Dateideskriptors,
    damit auch die C-Bibliothek nichts durchreicht."""
    sys.stderr.flush()
    alt = os.dup(2)
    leer = os.open(os.devnull, os.O_WRONLY)
    os.dup2(leer, 2)
    try:
        yield
    finally:
        sys.stderr.flush()
        os.dup2(alt, 2)
        os.close(leer)
        os.close(alt)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in ("handshake", "crawl"):
        raise SystemExit("aufruf: node_zaehler.py handshake|crawl")
    os.environ["GRPC_VERBOSITY"] = "NONE"
    os.environ.pop("GRPC_TRACE", None)
    vorbereiten()
    with stumm_stderr():
        return asyncio.run(handshake_probe() if argv[0] == "handshake" else crawl())


if __name__ == "__main__":
    sys.exit(main())
