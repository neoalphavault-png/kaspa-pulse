#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""weekly_pruefung.py, die Wochenseite gegen sich selbst pruefen.

WARUM ES DAS GIBT
kaspa-weekly.html rechnet im Browser. Zwei Angaben derselben Karte kamen
dabei auseinander (Ben, 12.10.2026):

    close sits 17.0% above        den 21-Wochen-Schnitt
    5 weeks in a row closing below  den 21-Wochen-Schnitt

Der Zaehler zaehlt die laufende Strecke, also die Wochen auf der Seite, auf
der der Schluss gerade steht. Daneben stand das Wort "below" fest im HTML.
Solange der Schluss unter der Linie lag, stimmte es zufaellig. Ein
Selbsttest in Python haette das nie gefunden: die Zahl war richtig, nur das
Wort daneben nicht.

Also prueft dieses Skript die fertige Seite im Browser, mit erfundenen
Kursdaten in beide Richtungen, und vergleicht die beiden Aussagen
miteinander. Dazu die Navigation: genau ein Punkt darf aktiv aussehen.

    python3 scripts/weekly_pruefung.py --selbsttest   # erfundene daten, beide richtungen
    python3 scripts/weekly_pruefung.py --live         # mit data/kas-candles.json
"""
import argparse
import datetime as dt
import http.server
import json
import os
import shutil
import socketserver
import sys
import tempfile
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEITE = "kaspa-weekly.html"
BEIWERK = ("capture.js", "utm.js", "favicon.png")
TEAL = "rgb(73, 234, 203)"

# Die Seite braucht genug Wochen fuer den 50-Wochen-Schnitt. 60 reichen,
# und der Wert selbst ist gleichgueltig - geprueft wird, ob die beiden
# Aussagen zueinander passen, nicht welche Zahl herauskommt.
WOCHEN = 60


def kerzen(hoch_am_ende):
    """Erfundene Wochenkerzen. hoch_am_ende hebt die letzten vier Wochen
    ueber den Schnitt, sonst drueckt es sie darunter."""
    erst = dt.date(2025, 1, 5)                      # ein sonntag
    kas, btc = [], []
    for i in range(WOCHEN):
        tag = erst + dt.timedelta(weeks=i)
        letzte_vier = i >= WOCHEN - 4
        kurs = 0.030
        if letzte_vier:
            kurs = 0.060 if hoch_am_ende else 0.015
        kas.append([tag.isoformat(), kurs, 1000000.0])
        for d in range(7):
            btc.append([(tag + dt.timedelta(days=d)).isoformat(), 80000.0])
    return {"updated": "2026-01-01 00:00 utc", "source": "erfunden, nur fuer den selbsttest",
            "history_from": erst.isoformat(), "week_rule": "wie im echten file",
            "kas_daily": [], "btc_daily": btc, "kas_weekly": kas}


def wurzel(kerzen_daten=None):
    """Ein Verzeichnis mit der Seite, ihrem Beiwerk und einem Datenfile.
    Ohne kerzen_daten wird das echte genommen."""
    if kerzen_daten is None:
        return REPO, None
    tmp = Path(tempfile.mkdtemp(prefix="weekly-pruefung-"))
    shutil.copy(REPO / SEITE, tmp / SEITE)
    for b in BEIWERK:
        if (REPO / b).exists():
            shutil.copy(REPO / b, tmp / b)
    (tmp / "data").mkdir()
    (tmp / "data" / "kas-candles.json").write_text(json.dumps(kerzen_daten), encoding="utf-8")
    return tmp, tmp


def lesen(wurzel_pfad, seite=SEITE, warten=True):
    """Die Seite rendern und die Angaben zurueckgeben, die zusammenpassen
    muessen."""
    from playwright.sync_api import sync_playwright
    os.chdir(wurzel_pfad)

    class Still(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", 0), Still)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    hafen = srv.server_address[1]
    launch = {}
    for c in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
              "/opt/pw-browsers/chromium/chrome-linux/chrome"):
        if os.path.exists(c):
            launch["executable_path"] = c
            break
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(**launch)
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            pg.goto("http://127.0.0.1:%d/%s" % (hafen, seite))
            if warten:
                pg.wait_for_function(
                    "document.getElementById('vStreak').textContent !== '\\u2014'",
                    timeout=15000)
            else:
                pg.wait_for_timeout(600)
            aus = pg.evaluate("""() => {
              const t = i => (document.getElementById(i) || {}).textContent || "";
              const aktiv = [...document.querySelectorAll('.nav .nc a, .nav .nc .ntop')]
                .filter(e => getComputedStyle(e).color === '%s')
                .map(e => (e.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 24));
              return {g21: t('g21'), g21b: t('g21b'), streak: t('vStreak'), streakB: t('streakB'),
                      seite: t('streakSide'), seiteB: t('streakSideB'), aktiv: aktiv};
            }""" % TEAL)
            b.close()
    finally:
        srv.shutdown()
    return aus


def pruefen(aus, name, ok):
    """Die beiden Aussagen der Karte gegeneinander."""
    luecke_seite = "below" if "below" in aus["g21"] else ("above" if "above" in aus["g21"] else "?")
    ok("%s: die luecke nennt eine seite" % name, luecke_seite in ("below", "above"), aus["g21"])
    ok("%s: strecke und luecke nennen dieselbe seite" % name,
       aus["seite"] == luecke_seite, "luecke %r, strecke %r" % (aus["g21"], aus["seite"]))
    ok("%s: der absatz sagt dasselbe wie die karte" % name,
       aus["seiteB"] == aus["seite"] and aus["g21b"] == aus["g21"],
       "karte %r/%r, absatz %r/%r" % (aus["g21"], aus["seite"], aus["g21b"], aus["seiteB"]))
    ok("%s: dieselbe wochenzahl in karte und absatz" % name,
       aus["streak"] == aus["streakB"] and aus["streak"].isdigit() and int(aus["streak"]) >= 1,
       "karte %r, absatz %r" % (aus["streak"], aus["streakB"]))
    ok("%s: genau ein menuepunkt sieht aktiv aus" % name,
       aus["aktiv"] == ["weekly"], aus["aktiv"])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args(argv)
    fehler = []

    def ok(name, bedingung, *mehr):
        print("%s %s%s" % ("ok  " if bedingung else "FEHL", name,
                           (" " + " ".join(str(m) for m in mehr)) if mehr and not bedingung else ""))
        if not bedingung:
            fehler.append(name)

    hier = os.getcwd()
    try:
        if a.live or not a.selbsttest:
            w, weg = wurzel(None)
            pruefen(lesen(w), "live", ok)
            # Die Navigation haengt an capture.js, nicht an den Kursdaten,
            # also gegen die echten Dateien. Zweite Seite, weil eine Regel
            # fuer "for builders" am 12.10.2026 genau dort die Markierung
            # der eigenen Seite ueberschrieben hat.
            os.chdir(hier)
            fb = lesen(w, "for-builders.html", warten=False)
            ok("live: auf for-builders ist genau dieser punkt aktiv",
               fb["aktiv"] == ["for builders"], fb["aktiv"])
        if a.selbsttest:
            for hoch, name in ((True, "schluss ueber der linie"), (False, "schluss unter der linie")):
                w, weg = wurzel(kerzen(hoch))
                try:
                    aus = lesen(w)
                    pruefen(aus, name, ok)
                    erwartet = "above" if hoch else "below"
                    ok("%s: das wort folgt der richtung" % name, aus["seite"] == erwartet,
                       "erwartet %r, gelesen %r" % (erwartet, aus["seite"]))
                finally:
                    os.chdir(hier)
                    if weg:
                        shutil.rmtree(weg, ignore_errors=True)
    finally:
        os.chdir(hier)
    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
