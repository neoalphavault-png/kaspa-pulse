#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""telegram-spiegel fuer die kaspa-pulse-bots.

alles, was nach discord geht, geht zusaetzlich in den telegram-kanal. der
kanal ist ein broadcast, keine gruppe, der bot braucht dort nur das recht
nachrichten zu posten.

zwei funktionen, beide fehlertolerant. schlaegt telegram fehl, wird eine
warnung ins log geschrieben und der aufrufer laeuft weiter. ein stiller
zweitkanal darf niemals den hauptkanal reissen.

benoetigte secrets:
    TELEGRAM_BOT_TOKEN   vom botfather, format 12345:AA...
    TELEGRAM_CHAT_ID     kanalhandle mit klammeraffe, z.b. @kaspapulse

fehlt eines von beiden, passiert nichts und es gibt eine kurze notiz im log.
"""

import json
import os
import re
import sys
import urllib.request

API = "https://api.telegram.org/bot%s/%s"
TIMEOUT = 30
UA = {"User-Agent": "kaspa-pulse-bot/1.0 (+https://kaspapulse.com)"}


def _creds():
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    return (tok, chat) if tok and chat else (None, None)


def clean(text):
    """discord-eigenheiten rausnehmen, die telegram nicht kennt.

    @everyone gibt es dort nicht, doppelte sternchen sind zwar auch in
    telegram fett, aber nur im markdown-modus, und spitze klammern um
    links unterdrueckt discord die vorschau, telegram zeigt sie als text.
    wir schicken deshalb reinen text ohne auszeichnung.
    """
    t = text.replace("@everyone", "").replace("**", "")
    t = re.sub(r"<(https?://[^>]+)>", r"\1", t)
    return t.strip()


def send_text(message):
    tok, chat = _creds()
    if not tok:
        print("hinweis: kein telegram secret gesetzt, kanal wird uebersprungen")
        return False
    body = json.dumps({
        "chat_id": chat,
        "text": clean(message),
        "disable_web_page_preview": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        API % (tok, "sendMessage"), data=body,
        headers={"Content-Type": "application/json", **UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            r.read()
        print("telegram: text gepostet")
        return True
    except Exception as exc:  # noqa: BLE001
        print("WARNUNG telegram fehlgeschlagen: %s" % exc, file=sys.stderr)
        return False


def send_photo(image_path, caption=""):
    tok, chat = _creds()
    if not tok:
        print("hinweis: kein telegram secret gesetzt, kanal wird uebersprungen")
        return False
    with open(image_path, "rb") as f:
        blob = f.read()
    boundary = "----kaspapulsetg7f3a9c21"
    parts = []
    for name, val in (("chat_id", chat), ("caption", clean(caption)[:1024])):
        parts.append(("--%s\r\n" % boundary).encode())
        parts.append(('Content-Disposition: form-data; name="%s"\r\n\r\n'
                      % name).encode())
        parts.append(val.encode("utf-8") + b"\r\n")
    parts.append(("--%s\r\n" % boundary).encode())
    parts.append(('Content-Disposition: form-data; name="photo"; '
                  'filename="%s"\r\n' % os.path.basename(image_path)).encode())
    parts.append(b"Content-Type: image/png\r\n\r\n")
    parts.append(blob + b"\r\n")
    parts.append(("--%s--\r\n" % boundary).encode())
    body = b"".join(parts)
    req = urllib.request.Request(
        API % (tok, "sendPhoto"), data=body,
        headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary,
                 **UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            r.read()
        print("telegram: bild gepostet")
        return True
    except Exception as exc:  # noqa: BLE001
        print("WARNUNG telegram fehlgeschlagen: %s" % exc, file=sys.stderr)
        return False


if __name__ == "__main__":
    # selbsttest der textaufbereitung, ohne netz
    src = ("@everyone **ENTITY X OUTFLOW DETECTED**\n"
           "balance dropped by **1,234 KAS**\n"
           "verify at <https://kaspapulse.com/entity-x.html>")
    out = clean(src)
    assert "@everyone" not in out
    assert "**" not in out
    assert "<https" not in out and "https://kaspapulse.com/entity-x.html" in out
    print(out)
    print("\nselbsttest bestanden")
