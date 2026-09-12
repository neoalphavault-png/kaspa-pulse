#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yt_live_check.py - ist die Montagsfolge schon oeffentlich?

Liest den oeffentlichen Kanal-Feed von YouTube
(https://www.youtube.com/feeds/videos.xml?channel_id=...) und sagt, ob das
neueste Video HEUTE veroeffentlicht wurde, plus dessen URL. Nur
Standardbibliothek, kein OAuth, kein API-Key, keine Quota.

    python3 scripts/yt_live_check.py                       # Kanal aus YT_CHANNEL_ID oder Handle
    python3 scripts/yt_live_check.py --channel-id UC...    # Kanal fest
    python3 scripts/yt_live_check.py --date 2026-09-14     # gegen ein anderes Datum pruefen
    python3 scripts/yt_live_check.py --selftest            # ohne Netz

Ausgabe: eine Zeile JSON auf stdout, Exit 0.

    {"date": "2026-09-14", "live_today": true,
     "video_url": "https://www.youtube.com/watch?v=XXXX",
     "video_id": "XXXX", "title": "...", "published": "2026-09-14T14:00:12+00:00",
     "channel_id": "UC...", "error": null}

Fail closed, mit Absicht: kann der Feed nicht gelesen werden, ist die Antwort
live_today = false plus error. Bens Regel lautet, der Newsletter darf nie vor
oder ohne das Video rausgehen. Ein unlesbarer Feed ist kein Beweis fuer ein
Video, also gilt er als kein Video. Der Aufrufer bricht dann ab, statt blind
zu senden.

"Heute" ist der Kalendertag in Europe/Berlin, nicht in UTC. Ein Video, das um
16:00 Berlin erscheint, traegt im Feed 14:00 UTC; an einem Montagabend waeren
das in UTC noch derselbe Tag, an einem spaeten Sonntag nicht mehr.
"""
import argparse
import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.request

FEED = "https://www.youtube.com/feeds/videos.xml?channel_id=%s"
CHANNEL_PAGE = "https://www.youtube.com/%s"
DEFAULT_HANDLE = "@gokugalax3000"        # Kaspa Pulse, wie in monday_briefing.py
UA = {"User-Agent": "kaspa-pulse-bot/1.0 (+https://kaspapulse.com)"}
TIMEOUT = 30

ENTRY_RE = re.compile(r"<entry>(.*?)</entry>", re.S)
ID_RE = re.compile(r"<yt:videoId>([\w-]+)</yt:videoId>")
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
PUB_RE = re.compile(r"<published>([^<]+)</published>")


# ---------------------------------------------------------------- Zeitzone

def berlin_offset(when):
    """Sommerzeit in Europe/Berlin ohne tzdata: letzter Sonntag im Maerz
    01:00 UTC bis letzter Sonntag im Oktober 01:00 UTC ist +02:00."""
    def last_sunday(year, month):
        d = dt.date(year, month, 31)
        return d - dt.timedelta(days=(d.weekday() + 1) % 7)
    y = when.year
    start = dt.datetime.combine(last_sunday(y, 3), dt.time(1), dt.timezone.utc)
    end = dt.datetime.combine(last_sunday(y, 10), dt.time(1), dt.timezone.utc)
    return dt.timedelta(hours=2) if start <= when < end else dt.timedelta(hours=1)


def berlin_date(when_utc):
    """Kalendertag in Berlin zu einem Zeitpunkt in UTC."""
    return (when_utc + berlin_offset(when_utc)).date()


# ---------------------------------------------------------------- Netz

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", "replace")


def resolve_channel_id(handle):
    """Kanal-ID aus der oeffentlichen Kanalseite, falls YT_CHANNEL_ID fehlt."""
    html = fetch(CHANNEL_PAGE % handle.lstrip("/"))
    m = (re.search(r'"channelId"\s*:\s*"(UC[\w-]{20,})"', html)
         or re.search(r'"externalId"\s*:\s*"(UC[\w-]{20,})"', html))
    if not m:
        raise RuntimeError("keine Kanal-ID auf der Seite von %s gefunden" % handle)
    return m.group(1)


# ---------------------------------------------------------------- Feed

def newest_entry(xml):
    """Neuester Eintrag des Feeds. YouTube sortiert absteigend, wir sortieren
    trotzdem selbst nach published, damit die Antwort nicht von der
    Reihenfolge im Feed abhaengt."""
    best = None
    for chunk in ENTRY_RE.findall(xml):
        vid = ID_RE.search(chunk)
        pub = PUB_RE.search(chunk)
        if not vid or not pub:
            continue
        published = dt.datetime.fromisoformat(pub.group(1).replace("Z", "+00:00"))
        title = TITLE_RE.search(chunk)
        item = {"video_id": vid.group(1),
                "title": (title.group(1).strip() if title else ""),
                "published": published}
        if best is None or item["published"] > best["published"]:
            best = item
    return best


def check(channel_id, day):
    xml = fetch(FEED % channel_id)
    item = newest_entry(xml)
    if not item:
        return {"live_today": False, "error": "feed ohne eintraege"}
    published_utc = item["published"].astimezone(dt.timezone.utc)
    return {
        "live_today": berlin_date(published_utc) == day,
        "video_id": item["video_id"],
        "video_url": "https://www.youtube.com/watch?v=" + item["video_id"],
        "title": item["title"],
        "published": published_utc.isoformat(),
        "error": None,
    }


# ---------------------------------------------------------------- Selbsttest

SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015">
 <entry><yt:videoId>aaaaaaaaaaa</yt:videoId><title>alte folge</title>
  <published>2026-09-07T14:00:03+00:00</published></entry>
 <entry><yt:videoId>bbbbbbbbbbb</yt:videoId><title>kaspa weekly</title>
  <published>2026-09-14T14:00:12+00:00</published></entry>
</feed>"""


def selftest():
    e = newest_entry(SAMPLE)
    assert e["video_id"] == "bbbbbbbbbbb", e
    assert e["title"] == "kaspa weekly", e
    # Sommerzeit: 14:00 UTC am 14.09. ist 16:00 Berlin, also derselbe Tag.
    assert berlin_offset(dt.datetime(2026, 9, 14, 14, 0, tzinfo=dt.timezone.utc)) == dt.timedelta(hours=2)
    # Winterzeit: Ende Oktober faellt Berlin auf +01:00 zurueck.
    assert berlin_offset(dt.datetime(2026, 11, 2, 14, 0, tzinfo=dt.timezone.utc)) == dt.timedelta(hours=1)
    assert berlin_date(dt.datetime(2026, 9, 14, 22, 30, tzinfo=dt.timezone.utc)) == dt.date(2026, 9, 15)
    assert berlin_date(dt.datetime(2026, 9, 14, 14, 0, tzinfo=dt.timezone.utc)) == dt.date(2026, 9, 14)
    # letzter Sonntag im Maerz 2026 ist der 29., im Oktober der 25.
    assert berlin_offset(dt.datetime(2026, 3, 29, 2, 0, tzinfo=dt.timezone.utc)) == dt.timedelta(hours=2)
    assert berlin_offset(dt.datetime(2026, 10, 25, 2, 0, tzinfo=dt.timezone.utc)) == dt.timedelta(hours=1)
    print("selftest ok: feed wird gelesen, berliner kalendertag stimmt")
    return 0


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--channel-id", default="", help="UC..., sonst aus dem Handle geholt")
    ap.add_argument("--handle", default=DEFAULT_HANDLE, help="Fallback, wenn keine Kanal-ID gesetzt ist")
    ap.add_argument("--date", default="", help="Tag, gegen den geprueft wird (Berlin), Vorgabe heute")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    now = dt.datetime.now(dt.timezone.utc)
    day = dt.date.fromisoformat(a.date) if a.date else berlin_date(now)
    out = {"date": str(day), "live_today": False, "video_id": None, "video_url": None,
           "title": None, "published": None, "channel_id": a.channel_id or None,
           "error": None}
    try:
        cid = a.channel_id.strip() or resolve_channel_id(a.handle)
        out["channel_id"] = cid
        out.update(check(cid, day))
    except (urllib.error.URLError, RuntimeError, ValueError, OSError) as exc:
        # fail closed: ohne Beweis kein Video, der Aufrufer bricht ab
        out["error"] = "%s: %s" % (type(exc).__name__, exc)
        print("WARNUNG: feed nicht lesbar, gilt als kein video: %s" % out["error"],
              file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
