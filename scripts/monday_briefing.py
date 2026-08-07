#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""montags-briefing. sammelt die kanalzahlen ein, die ein roboter holen kann,
rechnet die differenz zur vorwoche und postet alles fertig formatiert in den
privaten briefing-kanal auf discord.

was geholt wird:
    youtube    abos und gesamtviews von der oeffentlichen kanalseite
    discord    mitgliederzahl ueber die oeffentliche invite-api
    brevo      kontaktzahl ueber deren api, nur wenn BREVO_API_KEY gesetzt ist

was bewusst fehlt:
    x          es gibt keine kostenlose schnittstelle, der screenshot von ben
               bleibt der einzige handgriff am montag
    on-chain   laeuft schon im weekly-numbers-workflow, wird hier nicht doppelt
               geholt

jede quelle darf einzeln ausfallen, ohne den lauf zu reissen. eine zahl, die
nicht geholt werden konnte, erscheint im post als "keine messung" und wird in
der historie nicht ueberschrieben (regel 42, eine zahl ohne quelle existiert
nicht, also raten wir auch keine).

lokal:
    DRY_RUN=1 python3 scripts/monday_briefing.py
in github actions:
    python3 scripts/monday_briefing.py
"""

import datetime as dt
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_PATH = os.path.join(ROOT, "data", "channels-history.json")

YOUTUBE_URL = "https://www.youtube.com/@gokugalax3000/about"
DISCORD_INVITE = "h33JBhrPP7"
BREVO_URL = "https://api.brevo.com/v3/contacts?limit=1"

UA = {"User-Agent": "kaspa-pulse-bot/1.0 (+https://kaspapulse.com)"}
TIMEOUT = 30
HISTORY_KEEP = 120


def fetch(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", "replace")


def human_to_int(text):
    """macht aus '1.23K' oder '12,345' eine ganze zahl."""
    t = text.strip().replace(",", "").replace(" ", "")
    m = re.match(r"^([\d.]+)\s*([KMB]?)$", t, re.IGNORECASE)
    if not m:
        raise ValueError("unlesbare zahl %r" % text)
    val = float(m.group(1))
    mult = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    return int(round(val * mult[m.group(2).upper()]))


# ---------------------------------------------------------------- quellen

def get_youtube():
    """abos und gesamtviews aus der kanalseite. youtube aendert sein markup
    gern, deshalb mehrere muster je wert und im zweifel lieber None."""
    html = fetch(YOUTUBE_URL)
    subs = None
    for pat in (
        r'"subscriberCountText"\s*:\s*\{"simpleText"\s*:\s*"([\d.,KMB]+)\s+subscribers?"',
        r'"content"\s*:\s*"([\d.,KMB]+)\s+subscribers?"',
        r'([\d.,]+[KMB]?)\s+subscribers?"',
    ):
        m = re.search(pat, html)
        if m:
            subs = human_to_int(m.group(1))
            break
    views = None
    for pat in (
        r'"viewCountText"\s*:\s*\{"simpleText"\s*:\s*"([\d.,]+)\s+views"',
        r'"viewCount"\s*:\s*\{"simpleText"\s*:\s*"([\d.,]+)\s+views"',
        r'([\d.,]+)\s+views"',
    ):
        m = re.search(pat, html)
        if m:
            views = human_to_int(m.group(1))
            break
    return subs, views


def get_discord():
    """mitgliederzahl ueber die oeffentliche invite-api. mit with_counts
    liefert discord die ungefaehre gesamtzahl des servers."""
    url = ("https://discord.com/api/v9/invites/%s?with_counts=true"
           % DISCORD_INVITE)
    data = json.loads(fetch(url))
    n = data.get("approximate_member_count")
    return int(n) if n is not None else None


def get_brevo():
    """kontaktzahl aus brevo. ohne key wird still uebersprungen, der key
    ist ein repository secret und taucht nirgends im log auf."""
    key = os.environ.get("BREVO_API_KEY", "").strip()
    if not key:
        return None
    data = json.loads(fetch(BREVO_URL, headers={"api-key": key,
                                                "accept": "application/json"}))
    n = data.get("count")
    return int(n) if n is not None else None


# ---------------------------------------------------------------- bericht

FIELDS = [
    ("youtube_subs", "youtube abos"),
    ("youtube_views", "youtube views gesamt"),
    ("discord_members", "discord mitglieder"),
    ("newsletter_contacts", "newsletter kontakte"),
]


def collect():
    entry = {"date": str(dt.date.today())}
    problems = []
    try:
        subs, views = get_youtube()
        entry["youtube_subs"] = subs
        entry["youtube_views"] = views
        if subs is None or views is None:
            problems.append("youtube nur teilweise lesbar")
    except Exception as exc:  # noqa: BLE001
        entry["youtube_subs"] = entry["youtube_views"] = None
        problems.append("youtube nicht erreichbar (%s)" % exc)
    try:
        entry["discord_members"] = get_discord()
    except Exception as exc:  # noqa: BLE001
        entry["discord_members"] = None
        problems.append("discord nicht erreichbar (%s)" % exc)
    try:
        entry["newsletter_contacts"] = get_brevo()
        if entry["newsletter_contacts"] is None \
                and not os.environ.get("BREVO_API_KEY", "").strip():
            problems.append("brevo ohne key, kontakte bleiben leer")
    except Exception as exc:  # noqa: BLE001
        entry["newsletter_contacts"] = None
        problems.append("brevo nicht erreichbar (%s)" % exc)
    return entry, problems


def fmt(n):
    return format(n, ",").replace(",", ".")


def build_message(entry, prev, problems):
    lines = ["**kanalzahlen, montag %s**" % entry["date"], ""]
    for key, label in FIELDS:
        now = entry.get(key)
        if now is None:
            lines.append("%s  keine messung" % label)
            continue
        before = prev.get(key) if prev else None
        if before is None:
            lines.append("%s  %s (erste messung)" % (label, fmt(now)))
        else:
            diff = now - before
            arrow = "plus" if diff >= 0 else "minus"
            lines.append("%s  %s (%s %s seit %s)"
                         % (label, fmt(now), arrow, fmt(abs(diff)),
                            prev.get("date", "letzter messung")))
    lines.append("")
    lines.append("es fehlt nur noch der x screenshot, dann ist der montag komplett")
    if problems:
        lines.append("")
        lines.append("hinweise  " + "; ".join(problems))
    return "\n".join(lines)


def pick_webhook():
    for name in ("DISCORD_WEBHOOK_BRIEFING", "DISCORD_WEBHOOK_WEEKLY"):
        url = os.environ.get(name, "").strip()
        if url:
            return name, url
    return None, ""


def post_discord(msg):
    which, url = pick_webhook()
    if not url:
        print("ERROR: kein briefing webhook gesetzt", file=sys.stderr)
        return 1
    if which != "DISCORD_WEBHOOK_BRIEFING":
        print("WARNUNG: DISCORD_WEBHOOK_BRIEFING fehlt, post laeuft ueber %s"
              % which, file=sys.stderr)
    body = json.dumps({"content": msg, "username": "monday briefing",
                       "allowed_mentions": {"parse": []}},
                      ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json", **UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        r.read()
    print("gepostet")
    return 0


def load_history():
    try:
        with open(HISTORY_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def main():
    history = load_history()
    entry, problems = collect()
    prev = history[-1] if history else None

    msg = build_message(entry, prev, problems)
    print(msg)
    print("")

    if os.environ.get("DRY_RUN"):
        print("DRY_RUN, nichts gepostet, nichts geschrieben")
        return 0

    rc = post_discord(msg)

    # die historie bekommt den eintrag auch dann, wenn einzelne werte
    # fehlen. ein None bleibt None, der naechste vergleich findet ueber
    # build_message trotzdem statt, nur eben als "erste messung".
    history = (history + [entry])[-HISTORY_KEEP:]
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("historie geschrieben, %d eintraege" % len(history))
    return rc


if __name__ == "__main__":
    sys.exit(main())
