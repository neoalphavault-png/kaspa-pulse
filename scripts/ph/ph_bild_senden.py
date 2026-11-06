#!/usr/bin/env python3
"""ph_bild_senden.py - schickt fertig gepruefte Bilder eines Ordners nach #ph-entwuerfe.

Der Ordner enthaelt text.txt (die Nachricht), die PNG und SHA256SUMS. Es geht
nur raus, was in SHA256SUMS steht und dazu passt, in dieser Reihenfolge,
hoechstens 10 Dateien. Webhook aus DISCORD_WEBHOOK_PH_DRAFTS, die Adresse wird
nie gedruckt. Nicht gepostet, Ben postet selbst.

    python3 scripts/ph/ph_bild_senden.py <ordner>
"""
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
import uuid


def main(ordner):
    zeilen = [z.split() for z in open(os.path.join(ordner, "SHA256SUMS")).read().splitlines() if z.strip()]
    dateien = []
    for summe, name in zeilen:
        name = name.lstrip("*")
        if "/" in name or not name.endswith(".png"):
            sys.exit(f"{name}: nur png im ordner, nichts gesendet")
        ist = hashlib.sha256(open(os.path.join(ordner, name), "rb").read()).hexdigest()
        if ist != summe:
            sys.exit(f"{name} passt nicht zu SHA256SUMS, nichts gesendet")
        dateien.append(name)
    if not 1 <= len(dateien) <= 10:
        sys.exit("1 bis 10 dateien, nichts gesendet")
    text = open(os.path.join(ordner, "text.txt")).read().strip()[:1900]
    hook = os.environ.get("DISCORD_WEBHOOK_PH_DRAFTS", "").strip()
    if not hook.startswith(("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/")):
        sys.exit("DISCORD_WEBHOOK_PH_DRAFTS fehlt oder ist keine Discord-Webhook-Adresse")
    grenze = "----ph" + uuid.uuid4().hex
    teile = []

    def feld(name, wert, dateiname=None, typ=None):
        k = f'Content-Disposition: form-data; name="{name}"'
        if dateiname:
            k += f'; filename="{dateiname}"'
        if typ:
            k += f"\r\nContent-Type: {typ}"
        teile.append(f"--{grenze}\r\n{k}\r\n\r\n".encode() + wert + b"\r\n")
    feld("payload_json", json.dumps({"content": text, "allowed_mentions": {"parse": []}}).encode(),
         typ="application/json")
    for i, d in enumerate(dateien):
        feld(f"files[{i}]", open(os.path.join(ordner, d), "rb").read(), d, "image/png")
    body = b"".join(teile) + f"--{grenze}--\r\n".encode()
    req = urllib.request.Request(hook, data=body, headers={
        "Content-Type": f"multipart/form-data; boundary={grenze}", "User-Agent": "pulsehawk-entwurf/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print(f"{len(dateien)} bilder an #ph-entwuerfe geschickt, http {r.status}")
    except urllib.error.HTTPError as e:
        sys.exit(f"discord lehnt ab, http {e.code}")
    except (urllib.error.URLError, OSError) as e:
        sys.exit(f"discord nicht erreicht, {type(e).__name__}")


if __name__ == "__main__":
    main(sys.argv[1])
