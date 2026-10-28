#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""weekly_verteilung.py, den Hinweis auf das neue Weekly in unsere Kanaele bringen
(Ben, 26.10.2026).

ABLAUF AM MONTAG (scharf)
  16:00 bis 18:00 Berlin   alle 5 Minuten der oeffentliche RSS-Feed des Kanals
                           (scripts/yt_live_check.py, ohne Schluessel). Gilt
                           nur ein Video, das heute erschien, kein Short ist
                           und dessen Titel zum Uploadpaket passt.
  Fund + 5 Minuten         Discord #weekly-numbers (DISCORD_WEBHOOK_WEEKLY)
  Fund + 10 Minuten        unser Telegram-Kanal (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
  18:00 Berlin             #moderator-only (DISCORD_WEBHOOK_OPS), beginnend mit
                           "📤 VON HAND": der fertige Text je fremder Gruppe.
                           Fremde Gruppen bekommen NIE etwas automatisch.

TEXT
  Der Telegram- und der Discord-Block aus dem Uploadpaket der Sonntagsroutine
  (pulse-studio, kw/<montag>/uploadpaket.md, Abschnitt 6a). VIDEO_URL wird der
  echte Link, die Wochenseite bekommt UTM je Kanal (utm_source tg oder
  discord, utm_medium chat, utm_campaign weekly<nummer>; fremde Gruppen
  weekly<nummer>-gruppe, deutsche Gruppe weekly<nummer>-gruppe-de). Vor jedem Senden laufen die Textregeln.

SPERREN
  Merkdatei data/weekly-verteilung.json: je Kanal und Woche hoechstens ein Post.
  Veto: Variable WEEKLY_VERTEILUNG_STOPP (JJJJ-MM-TT oder immer), zusaetzlich
  die Datei data/weekly-verteilung-stopp auf main, die vor jedem Post frisch
  gelesen wird (wirkt auch in einem laufenden Lauf).
  Probe: schickt alles nur nach #moderator-only, ohne Warten, ohne Merkdatei.

    python3 scripts/weekly_verteilung.py --modus scharf --paket-dir studio/kw
    python3 scripts/weekly_verteilung.py --modus probe --paket-dir studio/kw [--datum 2026-10-26]
    python3 scripts/weekly_verteilung.py --selbsttest
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import utm  # noqa: E402
import yt_live_check as yt  # noqa: E402

MERK = "data/weekly-verteilung.json"
STOPP_DATEI = "data/weekly-verteilung-stopp"
GRUPPEN = "data/weekly-verteilung-gruppen.json"
WOCHENSEITE = "https://kaspapulse.com/kaspa-weekly.html"
WOCHENSEITE_RE = re.compile(r"https://kaspapulse\.com/kaspa-weekly\.html(?:\?[^\s)]*)?")
LINK_RE = re.compile(r'<link rel="alternate" href="([^"]+)"')
START, ENDE, TAKT_S = (16, 0), (18, 0), 300
ABSTAND_DISCORD, ABSTAND_TELEGRAM = 5 * 60, 10 * 60
HINWEIS_GRUPPEN = "höchstens einmal pro Woche und Gruppe, nur wo Teilen erlaubt ist"
ECHTZEIT = ("live", "now", "right now", "real time", "realtime", "real-time", "instantly", "every minute",
            "around the clock", "jetzt", "gerade eben", "in echtzeit")


# ------------------------------------------------------------------ zeit

def jetzt():
    return dt.datetime.now(dt.timezone.utc)


def berlin(t):
    return t + yt.berlin_offset(t)


def berlin_zeit(tag, hm):
    """UTC-Zeitpunkt zu einer Berliner Uhrzeit an einem Kalendertag."""
    naiv = dt.datetime.combine(tag, dt.time(*hm), dt.timezone.utc)
    return naiv - yt.berlin_offset(naiv - dt.timedelta(hours=2))


def hm(t):
    return berlin(t).strftime("%H:%M")


# ------------------------------------------------------------------ paket

def block(md, kopf_re):
    """Den eingerueckten Textblock unter einer Ueberschrift, ohne die Einrueckung."""
    m = re.search(r"^##\s+%s[^\n]*\n" % kopf_re, md, re.M | re.I)
    if not m:
        return None
    zeilen, drin = [], False
    for z in md[m.end():].split("\n"):
        if z.startswith("## ") or z.strip() == "---":
            break
        if z.startswith("    "):
            zeilen.append(z[4:].rstrip())
            drin = True
        elif not z.strip():
            if drin:
                zeilen.append("")
        elif drin:
            break
    return "\n".join(zeilen).strip() or None


def paket_lesen(pfad):
    md = open(pfad, encoding="utf-8").read()
    tg = block(md, r"Telegram \(englisch")
    dc = block(md, r"Discord \(englisch")
    titel = block(md, r"Titel")
    m = re.search(r"kaspa weekly (\d+) is out", (tg or "") + (dc or ""), re.I)
    return {"telegram": tg, "discord": dc, "titel": (titel or "").split("\n")[0].strip(),
            "nummer": int(m.group(1)) if m else None}


# ------------------------------------------------------------------ text

def wochenseite(quelle, kampagne):
    if quelle not in utm.QUELLEN or not utm.SLUG.match(kampagne):
        raise ValueError("utm ungueltig: %s %s" % (quelle, kampagne))
    return WOCHENSEITE + "?" + urllib.parse.urlencode(
        [("utm_source", quelle), ("utm_medium", "chat"), ("utm_campaign", kampagne)])


def einsetzen(text, video_url, quelle, kampagne):
    t = text.replace("VIDEO_URL", video_url)
    return WOCHENSEITE_RE.sub(wochenseite(quelle, kampagne), t)


def text_deutsch(nummer, tag, video_url):
    monate = ("januar", "februar", "märz", "april", "mai", "juni", "juli", "august", "september", "oktober",
              "november", "dezember")
    return ("kaspa weekly %d ist erschienen, montag %d. %s, 16:00 uhr berliner zeit\n\n"
            "die zahl der woche, was sie bedeutet und die schwelle für nächste woche stehen im video "
            "und auf der wochenseite.\n\nvideo, 4 minuten\n%s\n\nzahlen und methode\n%s\n\nkeine anlageberatung."
            % (nummer, tag.day, monate[tag.month - 1], video_url, wochenseite("tg", "weekly%d-gruppe-de" % nummer)))


def regeln(text):
    """Textregeln. Doppelpunkte nur in Uhrzeiten und Links."""
    fehler = []
    ohne = re.sub(r"https?://\S+", "", text)
    ohne = re.sub(r"\b\d{1,2}:\d{2}\b", "", ohne)
    for z, name in ((":", "doppelpunkt"), ("—", "gedankenstrich"), ("–", "gedankenstrich"),
                    (" - ", "gedankenstrich"), ("->", "pfeil"), ("=>", "pfeil"), ("→", "pfeil")):
        if z in ohne:
            fehler.append(name)
    klein = " %s " % re.sub(r"[^a-zäöüß0-9 ]", " ", ohne.lower())
    for w in ECHTZEIT:
        if " %s " % w in klein:
            fehler.append("echtzeitwort %s" % w)
    if "VIDEO_URL" in text:
        fehler.append("platzhalter VIDEO_URL")
    if len(text) > 1900:
        fehler.append("zu lang")
    return fehler


# ------------------------------------------------------------------ youtube

def feed_eintraege(xml):
    aus = []
    for chunk in yt.ENTRY_RE.findall(xml):
        vid, pub = yt.ID_RE.search(chunk), yt.PUB_RE.search(chunk)
        if not vid or not pub:
            continue
        titel = yt.TITLE_RE.search(chunk)
        link = LINK_RE.search(chunk)
        aus.append({"video_id": vid.group(1), "titel": titel.group(1).strip() if titel else "",
                    "link": link.group(1) if link else "",
                    "published": dt.datetime.fromisoformat(pub.group(1).replace("Z", "+00:00"))})
    return aus


def norm(t):
    t = t.replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
    return " ".join(re.sub(r"[^a-z0-9%| ]", " ", t.lower()).split())


def passendes_video(eintraege, tag, paket_titel):
    """(video, grund). Nur ein Langvideo von heute (Berlin), dessen Titel zum
    Paket passt: gleich, oder gleicher Teil vor dem '|'."""
    kandidaten = [e for e in eintraege if yt.berlin_date(e["published"].astimezone(dt.timezone.utc)) == tag
                  and "/shorts/" not in e["link"]]
    if not kandidaten:
        return None, "kein langvideo von heute im feed"
    soll = norm(paket_titel)
    vor = soll.split("|")[0].strip()
    for e in sorted(kandidaten, key=lambda x: x["published"], reverse=True):
        ist = norm(e["titel"])
        if soll and (ist == soll or (vor and ist.split("|")[0].strip() == vor)):
            return e, None
    return None, "titel passt nicht zum paket (%d kandidaten von heute)" % len(kandidaten)


# ------------------------------------------------------------------ senden

def post_json(url, daten):
    req = urllib.request.Request(url, data=json.dumps(daten).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "kaspa-pulse-weekly"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:                               # noqa: BLE001
        return 0


def discord(env_name, text):
    if os.environ.get("WEEKLY_TROCKEN") == "1":
        print("---- %s ----\n%s" % (env_name, text))
        return True
    hook = os.environ.get(env_name, "").strip()
    if not hook:
        print("kein %s" % env_name)
        return False
    code = post_json(hook, {"content": text, "allowed_mentions": {"parse": []}})
    print("discord %s http %s" % (env_name, code))
    return code in (200, 204)


def telegram(text):
    if os.environ.get("WEEKLY_TROCKEN") == "1":
        print("---- TELEGRAM ----\n%s" % text.replace("**", ""))
        return True
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(), os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not tok or not chat:
        print("kein telegram secret")
        return False
    code = post_json("https://api.telegram.org/bot%s/sendMessage" % tok,
                     {"chat_id": chat, "text": text.replace("**", ""), "disable_web_page_preview": False})
    print("telegram http %s" % code)
    return code == 200


# ------------------------------------------------------------------ merkdatei und veto

def merk_lesen():
    try:
        return json.load(open(MERK, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def merken(woche, kanal, wert, commit=True):
    d = merk_lesen()
    d.setdefault(woche, {})[kanal] = wert
    with open(MERK, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    if commit:
        for _ in range(4):
            r = subprocess.run("git add %s && git commit -qm 'weekly verteilung %s %s' && "
                               "git pull -q --rebase origin main && git push -q origin HEAD:main" % (MERK, woche, kanal),
                               shell=True)
            if r.returncode == 0:
                return True
            time.sleep(5)
        print("WARNUNG merkdatei nicht gepusht")
    return False


def stopp_aktiv(woche, variable=None):
    werte = [(variable if variable is not None else os.environ.get("WEEKLY_VERTEILUNG_STOPP", "")).strip()]
    try:
        subprocess.run(["git", "fetch", "-q", "origin", "main"], timeout=60)
        r = subprocess.run(["git", "show", "origin/main:%s" % STOPP_DATEI], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            werte.append(r.stdout.strip())
    except Exception:                               # noqa: BLE001
        pass
    return any(w and (w.lower() == "immer" or w == woche) for w in werte)


def gruppen():
    try:
        d = json.load(open(GRUPPEN, encoding="utf-8"))
        return [g for g in d.get("gruppen", []) if g.get("name")]
    except (OSError, ValueError):
        return []


# ------------------------------------------------------------------ moderator

def moderator_nachrichten(woche, paket, video, status, probe=False):
    """Kopf mit VON HAND und je Gruppe eine kopierbare Nachricht."""
    tag = dt.date.fromisoformat(woche)
    n = paket["nummer"]
    kopf = ["%s📤 VON HAND, Weekly %s, fremde Gruppen" % ("PROBE " if probe else "", n),
            "Regel %s. Fremde Gruppen und fremde Discords bekommen nie etwas automatisch." % HINWEIS_GRUPPEN]
    kopf += status
    if not video:
        return ["\n".join(kopf + ["Kein passendes Video gefunden, deshalb keine Texte für Gruppen."])]
    url = "https://www.youtube.com/watch?v=" + video["video_id"]
    liste = gruppen() or [{"name": "jede fremde englische Telegram-Gruppe", "sprache": "en", "art": "telegram"},
                          {"name": "die deutsche Gruppe", "sprache": "de", "art": "telegram"}]
    kopf.append("Je Gruppe die Nachricht darunter lange drücken, kopieren, in der Gruppe einfügen.")
    aus = ["\n".join(kopf)]
    for g in liste:
        if g.get("sprache") == "de":
            t = text_deutsch(n, tag, url)
        else:
            quelle = "discord" if g.get("art") == "discord" else "tg"
            basis = paket["discord"] if quelle == "discord" else paket["telegram"]
            t = einsetzen(basis, url, quelle, "weekly%d-gruppe" % n)
        f = regeln(t)
        aus.append("für %s (%s)\n\n%s%s" % (g["name"], "deutsch" if g.get("sprache") == "de" else "englisch", t,
                                            ("\n\nACHTUNG Textregeln %s" % ", ".join(f)) if f else ""))
    return aus


# ------------------------------------------------------------------ lauf

def warte_bis(t, schlafen=time.sleep):
    s = (t - jetzt()).total_seconds()
    if s > 0:
        schlafen(s)


def lauf_scharf(paket_dir, heute=None, abruf=yt.fetch, schlafen=time.sleep, commit=True):
    heute = heute or berlin(jetzt()).date()
    woche = heute.isoformat()
    start, ende = berlin_zeit(heute, START), berlin_zeit(heute, ENDE)
    if heute.weekday() != 0:
        print("heute ist kein montag, nichts zu tun")
        return 0
    if jetzt() > ende + dt.timedelta(minutes=30):
        print("fenster vorbei (nach 18:30 Berlin), nichts zu tun")
        return 0
    merk = merk_lesen().get(woche, {})
    if merk.get("moderator"):
        print("diese woche schon erledigt")
        return 0
    status = []
    pfad = os.path.join(paket_dir, woche, "uploadpaket.md")
    paket = paket_lesen(pfad) if os.path.exists(pfad) else None
    if not paket or not paket["telegram"] or not paket["discord"] or not paket["nummer"]:
        status.append("Uploadpaket kw/%s fehlt auf main oder ist unvollständig, nichts automatisch gepostet." % woche)
        warte_bis(ende, schlafen)
        discord("DISCORD_WEBHOOK_OPS", "\n".join(["Weekly-Verteilung %s" % woche] + status))
        merken(woche, "moderator", jetzt().isoformat(), commit)
        return 1
    warte_bis(start, schlafen)
    video, grund = merk.get("video") and {"video_id": merk["video"]}, None
    while not video and jetzt() <= ende:
        try:
            video, grund = passendes_video(feed_eintraege(abruf(yt.FEED % yt.KANAL_ID)), heute, paket["titel"])
        except Exception as exc:                    # noqa: BLE001
            grund = "feed nicht lesbar (%s)" % type(exc).__name__
        print("%s %s" % (hm(jetzt()), "gefunden " + video["video_id"] if video else grund))
        if not video:
            schlafen(TAKT_S)
    if video:
        gefunden = jetzt()
        merken(woche, "video", video["video_id"], commit)
        url = "https://www.youtube.com/watch?v=" + video["video_id"]
        status.append("Weekly %d gefunden um %s Berlin." % (paket["nummer"], hm(gefunden)))
        for kanal, abstand, quelle, basis in (("discord", ABSTAND_DISCORD, "discord", paket["discord"]),
                                              ("telegram", ABSTAND_TELEGRAM, "tg", paket["telegram"])):
            if merk.get(kanal):
                status.append("%s schon gepostet, kein zweiter Post." % kanal)
                continue
            warte_bis(gefunden + dt.timedelta(seconds=abstand), schlafen)
            text = einsetzen(basis, url, quelle, "weekly%d" % paket["nummer"])
            f = regeln(text)
            if f:
                status.append("%s NICHT gepostet, Textregeln %s." % (kanal, ", ".join(f)))
                continue
            if stopp_aktiv(woche):
                status.append("%s NICHT gepostet, Veto aktiv." % kanal)
                continue
            ok = discord("DISCORD_WEBHOOK_WEEKLY", text) if kanal == "discord" else telegram(text)
            if ok:
                merken(woche, kanal, jetzt().isoformat(), commit)
            status.append("%s %s um %s Berlin." % (kanal, "gepostet" if ok else "FEHLGESCHLAGEN", hm(jetzt())))
    else:
        status.append("Bis 18:00 Berlin kein passendes Weekly im Feed (%s). Nichts gepostet." % grund)
    warte_bis(ende, schlafen)
    for m in moderator_nachrichten(woche, paket, video, status):
        discord("DISCORD_WEBHOOK_OPS", m)
        schlafen(1)
    merken(woche, "moderator", jetzt().isoformat(), commit)
    return 0


def lauf_probe(paket_dir, datum=None, abruf=yt.fetch):
    """Alles nur nach #moderator-only, ohne Warten und ohne Merkdatei."""
    if not datum:
        tage = sorted(d for d in os.listdir(paket_dir) if re.match(r"^\d{4}-\d{2}-\d{2}$", d))
        datum = tage[-1] if tage else None
    pfad = os.path.join(paket_dir, datum or "", "uploadpaket.md")
    if not datum or not os.path.exists(pfad):
        discord("DISCORD_WEBHOOK_OPS", "PROBE Weekly-Verteilung, kein Uploadpaket gefunden.")
        return 1
    paket = paket_lesen(pfad)
    try:
        e = feed_eintraege(abruf(yt.FEED % yt.KANAL_ID))
        video, grund = passendes_video(e, dt.date.fromisoformat(datum), paket["titel"])
    except Exception as exc:                        # noqa: BLE001
        video, grund = None, "feed nicht lesbar (%s)" % type(exc).__name__
    print("probe paket %s weekly %s, video %s" % (datum, paket["nummer"], video["video_id"] if video else "nicht gefunden (%s)" % grund))
    url = "https://www.youtube.com/watch?v=" + video["video_id"] if video else "https://www.youtube.com/watch?v=PROBE"
    nachrichten = ["PROBE Weekly-Verteilung %s, Weekly %s. Video %s. So sähen die Posts aus, gesendet wird nur hierher."
                   % (datum, paket["nummer"], "gefunden" if video else "nicht gefunden (%s), Platzhalter-Link" % grund)]
    for kanal, quelle, basis in (("Discord #weekly-numbers", "discord", paket["discord"]),
                                 ("Telegram-Kanal", "tg", paket["telegram"])):
        t = einsetzen(basis or "", url, quelle, "weekly%s" % paket["nummer"])
        f = regeln(t)
        nachrichten.append("PROBE %s\n\n%s%s" % (kanal, t, ("\n\nTextregeln %s" % ", ".join(f)) if f else ""))
    nachrichten += moderator_nachrichten(datum, paket, video or {"video_id": "PROBE"},
                                         ["Probe, keine Merkdatei, kein Warten."], probe=True)
    for m in nachrichten:
        discord("DISCORD_WEBHOOK_OPS", m)
        time.sleep(1)
    return 0


# ------------------------------------------------------------------ selbsttest

PAKET = """# KASPA WEEKLY Folge 9 Uploadpaket

## Titel

    Kaspa Analysis | Up 2% And Back Over The 50 Week Line

**vidIQ 90**

## Telegram (englisch, offizieller Kanal)

    kaspa weekly 9 is out, monday 26 october, 16:00 Berlin time

    the weekly close of 24 october 2026 is 0.03605 usd.

    watch, 4 minutes
    VIDEO_URL

    numbers and method
    https://kaspapulse.com/kaspa-weekly.html

    week 52, above or below the 50 week line?

    Not financial advice.

**414 Zeichen ohne die Links** (erlaubt 450).

---

## Discord (englisch)

    kaspa weekly 9 is out, monday 26 october, 16:00 Berlin time

    the weekly close of 24 october 2026 is **0.03605 usd**.

    watch, 4 minutes
    VIDEO_URL

    numbers and method
    https://kaspapulse.com/kaspa-weekly.html

    Not financial advice.

---
"""

FEED = """<feed>
 <entry><yt:videoId>SHORT000001</yt:videoId><title>kaspa in 30 seconds</title>
  <link rel="alternate" href="https://www.youtube.com/shorts/SHORT000001"/>
  <published>2026-11-02T15:02:00+00:00</published></entry>
 <entry><yt:videoId>LONG0000001</yt:videoId><title>Kaspa Analysis | Something Else</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=LONG0000001"/>
  <published>2026-11-02T15:00:10+00:00</published></entry>
 <entry><yt:videoId>ALT00000001</yt:videoId><title>Kaspa Analysis | Old</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=ALT00000001"/>
  <published>2026-10-26T15:00:10+00:00</published></entry>
</feed>"""


def selbsttest():
    import tempfile
    fehler = []

    def ok(name, bed, ist=None):
        if not bed:
            fehler.append(name)
            print("FEHLER", name, ist)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "uploadpaket.md")
        open(p, "w", encoding="utf-8").write(PAKET)
        pk = paket_lesen(p)
    ok("paket gelesen", pk["nummer"] == 9 and pk["titel"].startswith("Kaspa Analysis |")
       and pk["telegram"].startswith("kaspa weekly 9 is out") and "**0.03605 usd**" in pk["discord"]
       and "414 Zeichen" not in pk["telegram"], pk)
    t = einsetzen(pk["telegram"], "https://www.youtube.com/watch?v=LONG0000001", "tg", "weekly9")
    ok("video und utm eingesetzt", "VIDEO_URL" not in t and
       "kaspa-weekly.html?utm_source=tg&utm_medium=chat&utm_campaign=weekly9" in t, t)
    ok("textregeln gruen fuer den paket-text", regeln(t) == [], regeln(t))
    ok("textregeln fangen doppelpunkt, strich und echtzeitwort",
       set(regeln("watch now: it is live — x")) >= {"doppelpunkt", "gedankenstrich", "echtzeitwort now",
                                                          "echtzeitwort live"}, regeln("watch now: it is live — x"))
    ok("platzhalter wird gefangen", "platzhalter VIDEO_URL" in regeln(pk["telegram"]))
    e = feed_eintraege(FEED)
    v, g = passendes_video(e, dt.date(2026, 11, 2), "Kaspa Analysis | 3 Weeks Up")
    ok("short ausgeschlossen, gleicher titelanfang passt", v and v["video_id"] == "LONG0000001", (v, g))
    v, g = passendes_video(e, dt.date(2026, 11, 2), "Something | Else")
    ok("fremder titel passt nicht", v is None and "titel passt nicht" in g, g)
    v, g = passendes_video(e, dt.date(2026, 11, 3), "Kaspa Analysis | x")
    ok("anderer tag nichts", v is None, g)
    ok("16:00 berlin im winter ist 15:00 utc", berlin_zeit(dt.date(2026, 11, 2), (16, 0)).hour == 15)
    ok("16:00 berlin im sommer ist 14:00 utc", berlin_zeit(dt.date(2026, 10, 19), (16, 0)).hour == 14)
    de = text_deutsch(9, dt.date(2026, 10, 26), "https://www.youtube.com/watch?v=X")
    ok("deutscher text regelkonform mit utm gruppe", regeln(de) == [] and "utm_campaign=weekly9-gruppe-de" in de,
       (regeln(de), de))
    try:
        wochenseite("telegram", "weekly9")
        ok("unbekannte quelle abgelehnt", False)
    except ValueError:
        pass
    ok("veto immer", stopp_aktiv("2026-11-02", "immer") and stopp_aktiv("2026-11-02", "2026-11-02")
       and not stopp_aktiv("2026-11-02", "2026-11-09"))
    # ganzer scharfer lauf mit falscher uhr: video gefunden, discord nach 5, telegram nach 10, moderator um 18:00
    gesendet, uhr = [], [berlin_zeit(dt.date(2026, 11, 2), (15, 50))]
    global jetzt, discord, telegram
    alt = (jetzt, discord, telegram)
    jetzt = lambda: uhr[0]  # noqa: E731

    def schlaf(s):
        uhr[0] = uhr[0] + dt.timedelta(seconds=s)
    discord = lambda n, t: gesendet.append((n, hm(uhr[0]), t)) or True  # noqa: E731
    telegram = lambda t: gesendet.append(("TELEGRAM", hm(uhr[0]), t)) or True  # noqa: E731
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "kw", "2026-11-02"))
        open(os.path.join(d, "kw", "2026-11-02", "uploadpaket.md"), "w").write(
            PAKET.replace("Up 2% And Back Over The 50 Week Line", "Something Else"))
        cwd = os.getcwd()
        os.chdir(d)
        os.makedirs("data")
        try:
            os.environ["WEEKLY_VERTEILUNG_STOPP"] = ""
            rc = lauf_scharf(os.path.join(d, "kw"), dt.date(2026, 11, 2), abruf=lambda u: FEED, schlafen=schlaf,
                             commit=False)
            merk = json.load(open(MERK))
            rc2 = lauf_scharf(os.path.join(d, "kw"), dt.date(2026, 11, 2), abruf=lambda u: FEED, schlafen=schlaf,
                              commit=False)
        finally:
            os.chdir(cwd)
    jetzt, discord, telegram = alt
    reihen = [(n, z) for n, z, _t in gesendet]
    ok("reihenfolge und zeiten", reihen[:3] == [("DISCORD_WEBHOOK_WEEKLY", "16:05"), ("TELEGRAM", "16:10"),
                                                ("DISCORD_WEBHOOK_OPS", "18:00")], reihen)
    ok("moderator beginnt mit von hand und nennt die regel", gesendet[2][2].startswith("📤 VON HAND")
       and HINWEIS_GRUPPEN in gesendet[2][2], gesendet[2][2][:120])
    ok("fremde gruppen englisch und deutsch", any("utm_campaign=weekly9-gruppe" in t and "englisch" in t
                                                  for _n, _z, t in gesendet[3:])
       and any("deutsch" in t and "ist erschienen" in t for _n, _z, t in gesendet[3:]), [t[:60] for _n, _z, t in gesendet])
    ok("merkdatei je kanal", set(merk["2026-11-02"]) >= {"video", "discord", "telegram", "moderator"} and rc == 0, merk)
    ok("zweiter lauf postet nichts", rc2 == 0 and len(gesendet) == len(reihen), len(gesendet))
    ok("probe: umgebung nur mit ops-webhook sauber", probe_umgebung_sauber({"DISCORD_WEBHOOK_OPS": "x"}) == [])
    ok("probe: telegram- und weekly-schluessel erkannt", probe_umgebung_sauber(
        {"DISCORD_WEBHOOK_WEEKLY": "x", "TELEGRAM_BOT_TOKEN": "y", "TELEGRAM_CHAT_ID": " "})
       == ["DISCORD_WEBHOOK_WEEKLY", "TELEGRAM_BOT_TOKEN"])
    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


NUR_SCHARF = ("DISCORD_WEBHOOK_WEEKLY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")


def probe_umgebung_sauber(umgebung=None):
    """Im Probe-Modus duerfen die Schluessel fuer #weekly-numbers und den
    Telegram-Kanal gar nicht in der Umgebung stehen (Ben, 27.10.2026). Gibt
    die Namen zurueck, die trotzdem da sind, nie die Werte."""
    u = os.environ if umgebung is None else umgebung
    return [n for n in NUR_SCHARF if (u.get(n) or "").strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modus", choices=("scharf", "probe"))
    ap.add_argument("--paket-dir", default="studio/kw")
    ap.add_argument("--datum")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    if a.modus == "probe":
        da = probe_umgebung_sauber()
        if da:
            print("probe abgebrochen, in der umgebung steht: %s" % ", ".join(da))
            return 2
        return lauf_probe(a.paket_dir, a.datum)
    if a.modus == "scharf":
        if stopp_aktiv(berlin(jetzt()).date().isoformat()):
            print("veto aktiv, nichts gepostet")
            return 0
        return lauf_scharf(a.paket_dir)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
