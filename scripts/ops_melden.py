#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ops_melden.py, die eine Stelle fuer Nachrichten an Ben und ins Ops-Log (Ben, 28.10.2026).

WARUM
#moderator-only wurde mit Infos ueberschwemmt, Ben uebersah das Wesentliche.
Ab 28.10.2026 gibt es zwei Arten:

    hand  nach #moderator-only (Secret DISCORD_WEBHOOK_OPS). Nur Nachrichten,
          bei denen Ben etwas tun muss. Jede beginnt mit "📤 VON HAND" und
          nennt Uhrzeit, Plattform, direkten Link und alles zum Kopieren.
    log   nach #ops-log (Secret DISCORD_WEBHOOK_LOG). Trockenlaeufe, Proben,
          Kontrollmeldungen, Entwuerfe zur Info, rote Laeufe, die eine
          Sitzung selbst behebt, Berichte an Claude.

Fehlt DISCORD_WEBHOOK_LOG, geht eine Log-Nachricht NICHT nach #moderator-only,
sie steht dann nur im Job-Log. Oeffentliche Kanaele (daily-graphic,
entity-x-alerts) laufen nicht hierueber und bleiben, wie sie sind.

Die Webhooks kommen nur aus der Umgebung und erscheinen nie in einer Ausgabe.

    python3 scripts/ops_melden.py --art log --text "probe, http 200"
    python3 scripts/ops_melden.py --art hand --text "..." --datei bild.png
    python3 scripts/ops_melden.py --selbsttest
"""
import argparse
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

VON_HAND = "📤 VON HAND"
ARTEN = {"hand": "DISCORD_WEBHOOK_OPS", "log": "DISCORD_WEBHOOK_LOG"}
KANAL = {"hand": "#moderator-only", "log": "#ops-log"}
GRENZE = 1990
MAX_DATEIEN = 10
UA = "kaspa-pulse-ops"
WEBHOOK = re.compile(r"https?://(?:\w+\.)?discord(?:app)?\.com/api/webhooks/\S+", re.I)


class Fehler(Exception):
    pass


def sauber(text):
    """Kein Webhook und kein Wert eines der beiden Secrets in einer Nachricht
    oder Ausgabe."""
    t = WEBHOOK.sub("[webhook]", str(text))
    for name in ARTEN.values():
        w = os.environ.get(name, "").strip()
        if w:
            t = t.replace(w, "[webhook]")
    return t


def hand_text(zeit, plattform, was, link="", rest=""):
    """Der Kopf jeder Hand-Nachricht: Uhrzeit, Plattform, was zu tun ist,
    der direkte Link. rest ist alles zum Kopieren."""
    zeilen = ["%s, %s, %s. %s" % (VON_HAND, zeit, plattform, was)]
    if link:
        zeilen.append(link)
    if rest:
        zeilen.append(rest)
    return "\n".join(zeilen)


def _text_fuer(art, text):
    if art not in ARTEN:
        raise Fehler("unbekannte art %r, erlaubt hand oder log" % art)
    t = sauber(text).strip()
    if art == "hand" and not t.startswith(VON_HAND):
        t = VON_HAND + "\n" + t
    return t[:GRENZE]


def _koerper(text, dateien):
    if not dateien:
        return (json.dumps({"content": text, "allowed_mentions": {"parse": []}}).encode(),
                "application/json")
    grenze = "----kp" + uuid.uuid4().hex
    teile = [("--%s\r\nContent-Disposition: form-data; name=\"payload_json\"\r\n"
              "Content-Type: application/json\r\n\r\n" % grenze).encode()
             + json.dumps({"content": text, "allowed_mentions": {"parse": []}}).encode() + b"\r\n"]
    for i, d in enumerate(dateien[:MAX_DATEIEN]):
        pfad, typ = (d if isinstance(d, (tuple, list)) else (d, None))
        pfad = Path(pfad)
        typ = typ or mimetypes.guess_type(pfad.name)[0] or "application/octet-stream"
        teile.append(("--%s\r\nContent-Disposition: form-data; name=\"files[%d]\"; filename=\"%s\"\r\n"
                      "Content-Type: %s\r\n\r\n" % (grenze, i, pfad.name, typ)).encode()
                     + pfad.read_bytes() + b"\r\n")
    return b"".join(teile) + ("--%s--\r\n" % grenze).encode(), "multipart/form-data; boundary=%s" % grenze


def _post(url, body, typ, timeout=60):
    req = urllib.request.Request(url, data=body, headers={"Content-Type": typ, "User-Agent": UA}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code


def senden(art, text, dateien=None, was="meldung"):
    """Schickt eine Nachricht der Art hand oder log. Gibt den HTTP-Status
    zurueck, oder None, wenn das Secret fehlt (dann steht sie im Job-Log).
    Eine Log-Nachricht wird nie nach #moderator-only umgeleitet."""
    t = _text_fuer(art, text)
    url = os.environ.get(ARTEN[art], "").strip()
    if not url:
        print("[%s] kein %s, nur im job-log (%s):\n%s" % (art, ARTEN[art], was, t))
        return None
    body, typ = _koerper(t, list(dateien or []))
    status = _post(url, body, typ)
    print("%s an %s, http %s" % (was, KANAL[art], status))
    if status >= 400:
        raise Fehler("%s an %s abgelehnt, http %s" % (was, KANAL[art], status))
    return status


def hand(text, dateien=None, was="meldung"):
    return senden("hand", text, dateien, was)


def log(text, dateien=None, was="meldung"):
    return senden("log", text, dateien, was)


def selbsttest():
    import tempfile
    f = []

    def ok(name, bed):
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        if not bed:
            f.append(name)

    alt = {k: os.environ.get(k) for k in ARTEN.values()}
    gesendet = []
    global _post
    echt = _post

    def falsch(url, body, typ, timeout=60):
        gesendet.append((url, body, typ))
        return 204
    _post = falsch
    # testadressen erst zur laufzeit zusammengesetzt, keine webhook-adresse in der datei
    basis = "https://discord.com/api/" + "webhooks/"
    try:
        os.environ["DISCORD_WEBHOOK_OPS"] = basis + "1/hand-test"
        os.environ["DISCORD_WEBHOOK_LOG"] = basis + "2/log-test"
        ok("hand geht an den ops-webhook", hand("x") == 204 and gesendet[-1][0].endswith("hand-test"))
        ok("hand beginnt immer mit von hand", json.loads(gesendet[-1][1])["content"].startswith(VON_HAND))
        hand(VON_HAND + ", 17:00 Berlin, X. posten")
        ok("kein doppelter kopf", json.loads(gesendet[-1][1])["content"].count(VON_HAND) == 1)
        ok("log geht an den log-webhook", log("probe http 200") == 204 and gesendet[-1][0].endswith("log-test"))
        ok("log ohne von-hand-kopf", not json.loads(gesendet[-1][1])["content"].startswith(VON_HAND))
        log("leak " + os.environ["DISCORD_WEBHOOK_OPS"] + " und " + basis + "9/abc")
        inhalt = json.loads(gesendet[-1][1])["content"]
        ok("kein webhook im text", "hand-test" not in inhalt and "/9/abc" not in inhalt)
        ok("niemand wird angepingt", json.loads(gesendet[-1][1])["allowed_mentions"] == {"parse": []})
        ok("text auf 1990 zeichen", len(json.loads((log("x" * 5000), gesendet[-1][1])[1])["content"]) == GRENZE)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bild.png"
            p.write_bytes(b"\x89PNG\r\n")
            log("mit bild", [p])
            ok("anhang als multipart", gesendet[-1][2].startswith("multipart/form-data")
               and b'filename="bild.png"' in gesendet[-1][1] and b"image/png" in gesendet[-1][1])
        n = len(gesendet)
        del os.environ["DISCORD_WEBHOOK_LOG"]
        ok("ohne log-webhook nichts gesendet, auch nicht an ops", log("probe") is None and len(gesendet) == n)
        ok("hand ohne log-webhook geht weiter", hand("x") == 204 and len(gesendet) == n + 1)
        del os.environ["DISCORD_WEBHOOK_OPS"]
        ok("ohne ops-webhook nur job-log", hand("x") is None and len(gesendet) == n + 1)
        try:
            senden("laut", "x")
            ok("unbekannte art stoppt", False)
        except Fehler:
            ok("unbekannte art stoppt", True)
        k = hand_text("17:00 Berlin", "X", "tagesgrafik posten", "https://x.com/compose/post", "text")
        ok("hand-kopf mit zeit, plattform, link", k.startswith(VON_HAND + ", 17:00 Berlin, X. tagesgrafik posten")
           and "https://x.com/compose/post" in k)
    finally:
        _post = echt
        for k, v in alt.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", choices=sorted(ARTEN))
    ap.add_argument("--text")
    ap.add_argument("--text-datei", help="text aus einer datei, - fuer stdin")
    ap.add_argument("--datei", action="append", default=[])
    ap.add_argument("--was", default="meldung")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if not a.art:
        ap.error("--art hand oder log")
    text = a.text
    if a.text_datei:
        text = sys.stdin.read() if a.text_datei == "-" else Path(a.text_datei).read_text(encoding="utf-8")
    if not text:
        ap.error("--text oder --text-datei")
    try:
        senden(a.art, text, a.datei, a.was)
    except Fehler as exc:
        print(sauber(exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
