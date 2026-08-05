#!/usr/bin/env python3
"""
kaspa pulse - number of the day, discord

schiebt die fertige grafik plus zwei zeilen text in den eigenen discord.
laeuft im selben workflow, direkt nach dem rendern.

der text kommt aus derselben json, die auch die grafik gebaut hat, damit
bild und text nie auseinanderlaufen koennen. geprueft wird mit derselben
funktion wie im renderer.

lokal:
    DRY_RUN=1 python3 scripts/post_number_of_day.py
in github actions:
    DISCORD_WEBHOOK aus den repository secrets, sonst bricht der lauf ab.
"""

import argparse
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from number_of_day import walk_and_check  # noqa: E402

DATA_PATH = os.path.join(ROOT, "data", "number-of-day.json")
IMG_PATH = os.path.join(ROOT, "graphics", "number-of-day.png")
UA = {"User-Agent": "kaspa-pulse-bot/1.0 (+https://kaspapulse.com)"}
TIMEOUT = 30
TAIL = "full numbers on kaspapulse.com"

# eigener kanal, eigener absendername. der webhook fuer die zahl des tages
# ist ein anderer als der fuer die alerts. faellt er weg, laeuft der post
# ersatzweise ueber den alten kanal, aber mit sichtbarer warnung im log.
WEBHOOK_ENVS = ("DISCORD_WEBHOOK_NUMBER", "DISCORD_WEBHOOK")
BOT_NAME = "number of the day"


def pick_webhook():
    """nimmt den ersten gesetzten webhook und sagt, welcher es war."""
    for name in WEBHOOK_ENVS:
        url = os.environ.get(name, "").strip()
        if url:
            return name, url
    return None, ""


def clean(text):
    """entfernt die betonungssternchen des renderers, laesst den rest stehen."""
    return str(text).replace("*", "")


def build_message(payload):
    """Discord bekommt exakt den text, der auch auf X laufen soll.

    erste absaetze sind der post, die letzte zeile ist die selbstantwort mit
    dem link. so muss ben nichts umschreiben, nur an der leerzeile trennen.
    """
    post = payload.get("post") or {}
    if post.get("x"):
        lines = [post["x"]]
        if post.get("reply"):
            lines.append(post["reply"])
    else:
        # notnagel, falls die json noch von hand stammt und keinen post hat
        head = clean(payload.get("headline", "")).strip()
        label = clean(payload.get("value_label", "")).strip()
        value = clean(payload.get("value", "")).strip()
        lines = []
        if head:
            lines.append(head.replace("\n", " "))
        if value and label:
            lines.append("%s, %s" % (value, label))
        lines.append(TAIL)
    msg = "\n\n".join(clean(l).strip() for l in lines if l)

    # dieselbe zeichenregel wie in der grafik. lieber hier abbrechen als
    # etwas posten, das gegen die hausregel verstoesst.
    walk_and_check(msg, "discord")
    return msg


def multipart(fields, filename, blob):
    """baut einen multipart body ohne fremdbibliothek."""
    boundary = "----kaspapulse7f3a9c21"
    out = []
    for name, val in fields.items():
        out.append(("--%s\r\n" % boundary).encode())
        out.append(('Content-Disposition: form-data; name="%s"\r\n\r\n'
                    % name).encode())
        out.append(val.encode("utf-8") + b"\r\n")
    out.append(("--%s\r\n" % boundary).encode())
    out.append(('Content-Disposition: form-data; name="files[0]"; '
                'filename="%s"\r\n' % filename).encode())
    out.append(b"Content-Type: image/png\r\n\r\n")
    out.append(blob + b"\r\n")
    out.append(("--%s--\r\n" % boundary).encode())
    return b"".join(out), "multipart/form-data; boundary=%s" % boundary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=DATA_PATH)
    ap.add_argument("--image", default=IMG_PATH)
    args = ap.parse_args()

    with open(args.data, encoding="utf-8") as f:
        payload = json.load(f)
    msg = build_message(payload)

    if os.environ.get("DRY_RUN"):
        print("DRY_RUN, das ginge raus:")
        print("")
        print(msg)
        print("")
        print("anhang %s" % args.image)
        return 0

    which, url = pick_webhook()
    if not url:
        print("ERROR: weder DISCORD_WEBHOOK_NUMBER noch DISCORD_WEBHOOK gesetzt",
              file=sys.stderr)
        return 1
    if which != WEBHOOK_ENVS[0]:
        print("WARNUNG: %s fehlt, der post laeuft ueber %s"
              % (WEBHOOK_ENVS[0], which), file=sys.stderr)

    with open(args.image, "rb") as f:
        blob = f.read()

    fields = {"payload_json": json.dumps(
        {"content": msg,
         "username": BOT_NAME,
         "allowed_mentions": {"parse": []}},
        ensure_ascii=False)}
    body, ctype = multipart(fields, "number-of-day.png", blob)

    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": ctype, **UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        r.read()
    print("gepostet, %d kB bild" % (len(blob) // 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
