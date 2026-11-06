#!/usr/bin/env python3
"""nu7_zitat_senden.py - schickt die gepruefte NU7-Karte nach #ph-entwuerfe (Ben, 06.11.2026).

Nur die beiden PNG aus data/ph-nu7-zitat, nur wenn ihre sha256 zu SHA256SUMS
passen. Webhook aus DISCORD_WEBHOOK_PH_DRAFTS, die Adresse wird nie gedruckt.
Nicht gepostet, Ben postet selbst.
"""
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

ORDNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ph-nu7-zitat")
DATEIEN = ["pulsehawk-nu7-expected-counted-1080x1350.png", "pulsehawk-nu7-expected-counted-390.png"]
TEXT = ("grafik fuer den zitatpost auf @pulsehawkio, zcash nu7, heute 16:30 berlin, nicht gepostet\n"
        "expected against counted, 1080x1350, dazu die vorschau 390 px\n"
        "grafik_check bestanden. zahlen aus berichte/2026-11-06-zcash-nu7-mainnet.md")


def main():
    summen = dict(reversed(z.split()) for z in open(os.path.join(ORDNER, "SHA256SUMS")).read().splitlines() if z)
    for d in DATEIEN:
        ist = hashlib.sha256(open(os.path.join(ORDNER, d), "rb").read()).hexdigest()
        if summen.get(d) != ist:
            print(f"{d} passt nicht zu SHA256SUMS, nichts gesendet", file=sys.stderr)
            sys.exit(1)
    hook = os.environ.get("DISCORD_WEBHOOK_PH_DRAFTS", "").strip()
    if not hook.startswith(("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/")):
        print("DISCORD_WEBHOOK_PH_DRAFTS fehlt oder ist keine Discord-Webhook-Adresse", file=sys.stderr)
        sys.exit(1)
    grenze = "----ph" + uuid.uuid4().hex
    teile = []

    def feld(name, wert, dateiname=None, typ=None):
        k = f'Content-Disposition: form-data; name="{name}"'
        if dateiname:
            k += f'; filename="{dateiname}"'
        if typ:
            k += f"\r\nContent-Type: {typ}"
        teile.append(f"--{grenze}\r\n{k}\r\n\r\n".encode() + wert + b"\r\n")
    feld("payload_json", json.dumps({"content": TEXT, "allowed_mentions": {"parse": []}}).encode(),
         typ="application/json")
    for i, d in enumerate(DATEIEN):
        feld(f"files[{i}]", open(os.path.join(ORDNER, d), "rb").read(), d, "image/png")
    body = b"".join(teile) + f"--{grenze}--\r\n".encode()
    req = urllib.request.Request(hook, data=body, headers={
        "Content-Type": f"multipart/form-data; boundary={grenze}", "User-Agent": "pulsehawk-entwurf/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print(f"karte an #ph-entwuerfe geschickt, http {r.status}")
    except urllib.error.HTTPError as e:
        print(f"discord lehnt ab, http {e.code}", file=sys.stderr)
        sys.exit(1)
    except (urllib.error.URLError, OSError) as e:
        print(f"discord nicht erreicht, {type(e).__name__}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
