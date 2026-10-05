#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
brevo_send.py - der Newsletter-Versand fuer die Montagsroutine (Brevo API v3).

Drei Modi, immer derselbe Kampagnen-Datensatz:

    --mode test      Kampagne aus dem HTML anlegen (Entwurf, nichts geht an die
                     Liste) und eine Testmail an eine einzelne Adresse schicken.
                     Die Kampagnen-ID landet in data/newsletter-queue.json.
    --mode schedule  Genau diese Kampagne auf die Liste planen, scheduledAt =
                     --send-at. Brevo plant serverseitig; danach muss kein
                     Runner mehr um 16:05 laufen.
Vor jedem Aufruf, der HTML an Brevo gibt, laufen zwei Pruefungen: jede
gedruckte Differenz muss zur Differenz ihrer gedruckten Endpunkte passen
(weekly_facts), und die Ausgabennummer muss die der letzten Ausgabe plus eins
sein (newsletter_issue). Ein stehengebliebenes {{ISSUE}} haelt den Versand an.

    --mode update    Das HTML (und auf Wunsch den Betreff) der Kampagne aus der
                     Queue ersetzen und eine neue Testmail schicken. Nur fuer
                     einen Entwurf. Es wird nichts geplant und nichts geht an
                     die Liste. Dafuer gedacht, dass eine Korrektur die schon
                     angelegte Kampagne erreicht, statt nur im Repo zu stehen.
    --mode fix       Eine schon GEPLANTE Kampagne korrigieren: storniert sie,
                     bestueckt sie mit dem HTML und plant sie auf denselben
                     Zeitpunkt zurueck, den Brevo nennt. Der Termin wird nie
                     erfunden, und liegt er weniger als zehn Minuten entfernt,
                     passiert nichts.
    --mode cancel    Die Kampagne aus der Queue auf suspended setzen. Storniert
                     wird nur, was wirklich auf Abschuss steht (queued,
                     inProcess). Entwurf, schon storniert, schon versendet oder
                     gar keine Kampagne heisst: nichts anfassen, Lauf bleibt
                     gruen. Der Veto-Knopf darf nie rot werden, nur weil nichts
                     zu stoppen war.

Absender wird NIE geraten: GET /v3/senders, und daraus der aktive Absender
(oder der, dessen Adresse in BREVO_SENDER_EMAIL steht).

Secret (Umgebung): BREVO_API_KEY. Wird nie gedruckt.

    python3 scripts/brevo_send.py --mode test --html newsletter/2026-09-14.html \
        --subject "TEST" --test-to ben@example.com
    python3 scripts/brevo_send.py --mode schedule --send-at 2026-09-28T18:00 --list-id 16
    python3 scripts/brevo_send.py --mode cancel
    python3 scripts/brevo_send.py --selftest

Der Testmodus plant nichts und sendet an niemanden ausser --test-to. Die
einzige Stelle, die je an die Liste plant, ist --mode schedule; sie verlangt
--send-at und schreibt vorher in den Lauf, an welche Liste und wann.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request

API = "https://api.brevo.com/v3"
TIMEOUT = 60
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import weekly_facts  # noqa: E402  (Rechenregeln und der Differenz-Waechter)
import newsletter_issue  # noqa: E402  (Ausgabennummer, zaehlt sich selbst hoch)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "data", "newsletter-queue.json")
DEFAULT_LIST_ID = 16


# ---------------------------------------------------------------- Zeit

def berlin_offset(when):
    """Sommerzeit in Europe/Berlin ohne tzdata (siehe yt_live_check.py)."""
    def last_sunday(year, month):
        d = dt.date(year, month, 31)
        return d - dt.timedelta(days=(d.weekday() + 1) % 7)
    y = when.year
    start = dt.datetime.combine(last_sunday(y, 3), dt.time(1), dt.timezone.utc)
    end = dt.datetime.combine(last_sunday(y, 10), dt.time(1), dt.timezone.utc)
    return dt.timedelta(hours=2) if start <= when < end else dt.timedelta(hours=1)


def to_brevo_time(iso_berlin):
    """'2026-09-14T16:05' (Berliner Ortszeit) wird zu '2026-09-14T16:05:00+02:00'.
    Traegt die Eingabe schon eine Zone, bleibt sie unangetastet."""
    s = (iso_berlin or "").strip()
    if not s:
        raise ValueError("send_at fehlt")
    parsed = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        # Offset am gemeinten Zeitpunkt, nicht am heutigen Tag
        guess = parsed.replace(tzinfo=dt.timezone.utc)
        parsed = parsed.replace(tzinfo=dt.timezone(berlin_offset(guess)))
    if parsed <= dt.datetime.now(dt.timezone.utc):
        raise ValueError("send_at liegt in der Vergangenheit: %s" % parsed.isoformat())
    return parsed.isoformat(timespec="seconds")


# ---------------------------------------------------------------- HTTP

def key_from_env():
    key = os.environ.get("BREVO_API_KEY", "").strip()
    if not key:
        sys.exit("FEHLT: BREVO_API_KEY nicht gesetzt (Repo-Secret)")
    return key


def call(method, path, key, body=None):
    url = API + path
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    headers = {"api-key": key, "accept": "application/json",
               "User-Agent": "kaspa-pulse brevo_send/1.0"}
    if data is not None:
        headers["content-type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")[:800]
        raise RuntimeError("brevo antwortet HTTP %d auf %s %s: %s" % (e.code, method, path, text))


# ---------------------------------------------------------------- Absender

def pick_sender(key, wanted_email=""):
    """Absender aus GET /v3/senders holen, nie raten. Mit BREVO_SENDER_EMAIL
    laesst sich einer von mehreren festnageln."""
    senders = (call("GET", "/senders", key) or {}).get("senders") or []
    if not senders:
        sys.exit("FEHLT: das Brevo-Konto hat keinen Absender, /v3/senders ist leer")
    if wanted_email:
        for s in senders:
            if (s.get("email") or "").lower() == wanted_email.lower():
                return s
        sys.exit("FEHLT: kein Absender mit der Adresse %s in Brevo (%d vorhanden)"
                 % (wanted_email, len(senders)))
    active = [s for s in senders if s.get("active")]
    chosen = (active or senders)[0]
    if len(senders) > 1:
        print("HINWEIS: %d Absender im Konto, genommen wird %s. Anderen Absender "
              "ueber BREVO_SENDER_EMAIL festnageln."
              % (len(senders), chosen.get("email")))
    return chosen


# ---------------------------------------------------------------- Queue

def load_queue(path):
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {"campaign_id": None, "history": []}


def save_queue(path, q):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(q, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def now_z():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def note(q, what, **kw):
    entry = {"at": now_z(), "step": what}
    entry.update(kw)
    q.setdefault("history", []).append(entry)
    q["history"] = q["history"][-40:]


# ---------------------------------------------------------------- Pruefung

BILD_RE = re.compile(r'src="(?:https?://(?:www\.)?kaspapulse\.com)?/([^"?#]+\.(?:png|jpg|jpeg|gif|webp))"', re.I)


def fehlende_bilder(html):
    """Bilder, die auf kaspapulse.com zeigen und im Repo nicht liegen."""
    fehlt = []
    for rel in sorted(set(BILD_RE.findall(newsletter_issue.nur_inhalt(html)))):
        if not os.path.isfile(os.path.join(ROOT, rel)):
            fehlt.append(rel)
    return fehlt


def html_lesen_und_pruefen(pfad):
    """HTML laden und die eine Rechnung pruefen, die am 05.10.2026 falsch war:
    eine gedruckte Differenz, die nicht zur Differenz ihrer gedruckten
    Endpunkte passt (1 578 043 statt 1 578 042). Findet der Waechter etwas,
    geht nichts an Brevo."""
    with open(pfad, encoding="utf-8") as fh:
        html = fh.read()
    if len(html) < 200:
        sys.exit("das HTML ist kuerzer als 200 Zeichen, das kann nicht der Newsletter sein: %s" % pfad)
    befunde = weekly_facts.pruefe_text(html, ist_html=True)
    for b in befunde:
        print("FEHLER %s minus %s ist %s, gedruckt steht %s\n  %r"
              % (weekly_facts.zahl(b["von"]), weekly_facts.zahl(b["bis"]),
                 weekly_facts.zahl(b["richtig"]), weekly_facts.zahl(b["gedruckt"]),
                 b["segment"]), file=sys.stderr)
    if befunde:
        sys.exit("%s traegt %d Differenz(en), die nicht zu den gedruckten Endpunkten "
                 "passen. Regel: erst runden, dann abziehen. Nichts an Brevo geschickt."
                 % (pfad, len(befunde)))
    print("waechter ok: jede gedruckte Differenz in %s passt zu ihren Endpunkten" % pfad)

    # Ausgabennummer. Ein stehengebliebener Platzhalter haelt den Versand an,
    # er waere im Postfach nicht zu reparieren. Eine abweichende Nummer ist
    # nur eine Warnung: eine Sonderausgabe darf aus der Reihe fallen, und ein
    # blockierter Montag kostet mehr als eine schiefe Zahl.
    offen = newsletter_issue.offene_platzhalter(html)
    if offen:
        sys.exit("%s traegt noch %s. Eine Vorlage mit offenem Platzhalter geht "
                 "nicht raus: {{ISSUE}} fuellt "
                 "'python3 scripts/newsletter_issue.py set %s', {{SUBJECT}} und "
                 "VIDEO_URL fuellt die Montagsroutine, und VIDEO_URL erst, wenn "
                 "die Folge wirklich oeffentlich ist."
                 % (pfad, " und ".join(offen), pfad))
    if newsletter_issue.pruefe(pfad) != 0:
        print("WARNUNG: die Ausgabennummer zaehlt nicht wie erwartet weiter. "
              "Gewollt? Dann weiter. Sonst 'newsletter_issue.py set %s'." % pfad)

    # Bilder, die im HTML auf unsere eigene Seite zeigen, muessen im Repo
    # liegen, sonst steht im Postfach ein leeres Kaestchen. Nur eine Warnung:
    # ein fehlendes Icon ist kein Grund, einen Montag anzuhalten.
    for rel in fehlende_bilder(html):
        print("WARNUNG: %s verlinkt %s, die Datei liegt nicht im Repo" % (pfad, rel))

    # Ein Videolink, der schon in einer frueheren Ausgabe stand, ist meistens
    # ein vergessener Link und nicht Absicht.
    try:
        for vid, frueher in newsletter_issue.videolink_schon_benutzt(pfad):
            print("WARNUNG: der videolink %s stand schon in %s. Vergessen?" % (vid, frueher))
    except OSError:
        pass
    return html


# ---------------------------------------------------------------- Modi

def mode_test(a, key, q):
    html = html_lesen_und_pruefen(a.html)
    sender = pick_sender(key, os.environ.get("BREVO_SENDER_EMAIL", "").strip())
    test_to = (a.test_to or "").strip()
    if not test_to:
        # Kein Raten: der eigene, in Brevo verifizierte Absender ist die einzige
        # Adresse, die wir ohne Vorgabe kennen duerfen.
        test_to = sender.get("email") or ""
        if not test_to:
            sys.exit("FEHLT: keine Testadresse (vars.NEWSLETTER_TEST_TO oder --test-to)")
        print("WARNUNG: keine Testadresse gesetzt (vars.NEWSLETTER_TEST_TO fehlt), "
              "die Testmail geht an den eigenen Absender %s" % test_to)
    name = a.name or "kaspa pulse %s %s" % (a.subject, dt.date.today().isoformat())
    body = {
        "name": name,
        "subject": a.subject,
        "sender": {"name": sender.get("name") or "Kaspa Pulse", "email": sender["email"]},
        "type": "classic",
        "htmlContent": html,
        "recipients": {"listIds": [a.list_id]},
        "inlineImageActivation": False,
    }
    res = call("POST", "/emailCampaigns", key, body)
    cid = res.get("id")
    if not cid:
        raise RuntimeError("kampagne ohne id: %s" % json.dumps(res)[:300])
    print("kampagne angelegt: id %s, betreff %r, absender %s, liste %d, ENTWURF"
          % (cid, a.subject, sender["email"], a.list_id))
    q["campaign_id"] = cid
    q["subject"] = a.subject
    q["html_path"] = os.path.relpath(os.path.abspath(a.html), ROOT)
    q["list_id"] = a.list_id
    q["sender"] = sender["email"]
    q["status"] = "draft"
    q["scheduled_at"] = None
    q["created_at"] = now_z()
    note(q, "test", campaign_id=cid, test_to=test_to)
    save_queue(a.queue, q)          # ID sofort merken, bevor irgendetwas anderes passiert
    call("POST", "/emailCampaigns/%s/sendTest" % cid, key, {"emailTo": [test_to]})
    print("testmail an %s raus. an die liste geht nichts, die kampagne bleibt entwurf." % test_to)
    return 0


def mode_update(a, key, q):
    """Eine Korrektur in die schon angelegte Kampagne nachziehen.

    Angefasst wird nur ein Entwurf. Ist die Kampagne geplant, muss sie erst
    storniert werden: eine scharfe Kampagne still umzuschreiben wuerde an der
    Entscheidung vorbeigehen, die das Planen war. Geplant oder gesendet wird
    hier nichts, nur das HTML ersetzt und eine Testmail geschickt."""
    cid = q.get("campaign_id")
    if not cid:
        sys.exit("keine kampagne in %s, erst --mode test laufen lassen" % a.queue)
    pfad = a.html or q.get("html_path")
    if not pfad or not os.path.isfile(pfad):
        sys.exit("kein HTML: --html fehlt und %r aus der queue zeigt ins Leere" % pfad)
    html = html_lesen_und_pruefen(pfad)
    state = call("GET", "/emailCampaigns/%s" % cid, key)
    if state.get("status") not in ("draft", "suspended"):
        sys.exit("kampagne %s hat den status %r. Bestueckt wird nur ein Entwurf "
                 "oder eine stornierte Kampagne, denn beide gehen nicht von selbst "
                 "raus. Fuer eine geplante Kampagne ist --mode fix da: storniert, "
                 "bestueckt und plant auf denselben Zeitpunkt zurueck."
                 % (cid, state.get("status")))
    body = {"htmlContent": html}
    if a.subject.strip():
        body["subject"] = a.subject.strip()
    call("PUT", "/emailCampaigns/%s" % cid, key, body)
    print("kampagne %s neu bestueckt aus %s%s"
          % (cid, pfad, (", betreff %r" % a.subject.strip()) if a.subject.strip() else ""))
    q["html_path"] = os.path.relpath(os.path.abspath(pfad), ROOT)
    if a.subject.strip():
        q["subject"] = a.subject.strip()
    test_to = (a.test_to or "").strip() or q.get("sender") or ""
    if not test_to:
        sys.exit("FEHLT: keine Testadresse (vars.NEWSLETTER_TEST_TO oder --test-to)")
    note(q, "update", campaign_id=cid, html_path=q["html_path"], test_to=test_to)
    save_queue(a.queue, q)
    call("POST", "/emailCampaigns/%s/sendTest" % cid, key, {"emailTo": [test_to]})
    print("testmail an %s raus. an die liste geht nichts, die kampagne bleibt entwurf." % test_to)
    return 0


# Seit dem 25.09.2026 nur noch EIN schreibender Aufruf. Der PUT mit
# scheduledAt plant die Kampagne bereits. Der zweite Aufruf, PUT .../status
# mit "queued", ist am 21.09.2026 mit HTTP 400 gescheitert ("queued is an
# invalid status for scheduled campaign"), der Lauf wurde rot und die Queue
# blieb auf "draft" stehen, obwohl Kampagne 31 laut Ben um 18:00 rausging.
# Ob geplant ist, wird jetzt nur noch GELESEN.
GEPLANT = ("queued", "scheduled", "inProcess", "in_process")


def pruefe_geplant(check, when):
    """None, wenn die gelesene Kampagne auf den gewuenschten Zeitpunkt
    geplant ist, sonst der Grund. Verglichen wird der Zeitpunkt, nicht der
    Text: Brevo liefert ihn in UTC zurueck ("...T16:00:00.000Z")."""
    status = (check or {}).get("status")
    zurueck = (check or {}).get("scheduledAt")
    if status not in GEPLANT:
        return "status %r ist kein geplanter status (%s)" % (status, ", ".join(GEPLANT))
    if not zurueck:
        return "status %r, aber kein scheduledAt" % status
    try:
        ist = dt.datetime.fromisoformat(str(zurueck).replace("Z", "+00:00"))
        soll = dt.datetime.fromisoformat(str(when).replace("Z", "+00:00"))
    except ValueError:
        return "scheduledAt %r nicht lesbar" % zurueck
    if abs((ist - soll).total_seconds()) > 60:
        return "geplant auf %s, gewollt war %s" % (ist.isoformat(), soll.isoformat())
    return None


def mode_schedule(a, key, q, call_fn=None):
    call_fn = call_fn or call
    cid = q.get("campaign_id")
    if not cid:
        sys.exit("keine kampagne in %s, erst --mode test laufen lassen" % a.queue)
    when = to_brevo_time(a.send_at)
    print("plane kampagne %s auf liste %d, scheduledAt %s" % (cid, a.list_id, when))
    call_fn("PUT", "/emailCampaigns/%s" % cid, key,
            {"recipients": {"listIds": [a.list_id]}, "scheduledAt": when})
    check = call_fn("GET", "/emailCampaigns/%s" % cid, key)
    print("brevo meldet status %r, scheduledAt %r"
          % (check.get("status"), check.get("scheduledAt")))
    grund = pruefe_geplant(check, when)
    q["status"] = check.get("status")
    q["scheduled_at"] = check.get("scheduledAt")
    q["list_id"] = a.list_id
    note(q, "schedule", campaign_id=cid, scheduled_at=q["scheduled_at"],
         list_id=a.list_id, result="geplant" if grund is None else grund)
    save_queue(a.queue, q)
    if grund:
        sys.exit("FEHLER: kampagne %s ist nicht nachweislich geplant: %s" % (cid, grund))
    print("kampagne %s ist geplant, gelesen, nicht angenommen" % cid)
    return 0


def mode_fix(a, key, q, call_fn=None):
    """Eine schon GEPLANTE Kampagne korrigieren, ohne ihren Termin zu verlieren.

    Brevo laesst eine geplante Kampagne nicht bestuecken, und Bens Termin darf
    nicht verloren gehen. Also in dieser Reihenfolge:

        1. lesen, Status und scheduledAt merken
        2. HTML lesen und pruefen, BEVOR irgendetwas angefasst wird
        3. stornieren (nur wenn sie geplant war)
        4. bestuecken
        5. auf denselben scheduledAt zurueckplanen und das Ergebnis lesen
        6. eine Testmail, damit die korrigierte Fassung im Postfach nachweisbar ist

    Der Termin wird NIE erfunden, er kommt aus Brevo. Liegt er weniger als
    zehn Minuten entfernt, passiert nichts: so kurz vorher ist ein Storno das
    groessere Risiko als der Fehler im Text."""
    call_fn = call_fn or call
    cid = q.get("campaign_id")
    if not cid:
        sys.exit("keine kampagne in %s" % a.queue)
    pfad = a.html or q.get("html_path")
    if not pfad or not os.path.isfile(pfad):
        sys.exit("kein HTML: --html fehlt und %r aus der queue zeigt ins Leere" % pfad)

    state = call_fn("GET", "/emailCampaigns/%s" % cid, key)
    status, when = state.get("status"), state.get("scheduledAt")
    print("kampagne %s: status %r, scheduledAt %r" % (cid, status, when))
    if status == "sent":
        sys.exit("kampagne %s ist schon raus. Nichts mehr zu korrigieren." % cid)
    if status in GEPLANT and not when:
        sys.exit("kampagne %s ist geplant, aber Brevo nennt kein scheduledAt. "
                 "Von Hand ansehen, hier wird nichts angefasst." % cid)
    if status in GEPLANT:
        rest = (dt.datetime.fromisoformat(str(when).replace("Z", "+00:00"))
                - dt.datetime.now(dt.timezone.utc)).total_seconds()
        print("bis zum versand sind es %.0f minuten" % (rest / 60))
        if rest < 600:
            sys.exit("der versand liegt in weniger als zehn Minuten (%.0f min). "
                     "Ein Storno waere jetzt das groessere Risiko. Nichts angefasst." % (rest / 60))

    html = html_lesen_und_pruefen(pfad)       # erst pruefen, dann anfassen

    if status in GEPLANT:
        call_fn("PUT", "/emailCampaigns/%s/status" % cid, key, {"status": "suspended"})
        print("storniert, um bestuecken zu koennen")
    body = {"htmlContent": html}
    if a.subject.strip():
        body["subject"] = a.subject.strip()
    try:
        call_fn("PUT", "/emailCampaigns/%s" % cid, key, body)
    except RuntimeError:
        if status in GEPLANT:
            # zurueck in den Zustand, in dem Ben sie uebergeben hat
            call_fn("PUT", "/emailCampaigns/%s" % cid, key, {"scheduledAt": when})
            print("bestuecken fehlgeschlagen, alter Termin wieder gesetzt: %s" % when)
        raise
    print("kampagne %s neu bestueckt aus %s" % (cid, pfad))
    q["html_path"] = os.path.relpath(os.path.abspath(pfad), ROOT)
    if a.subject.strip():
        q["subject"] = a.subject.strip()

    if status in GEPLANT:
        call_fn("PUT", "/emailCampaigns/%s" % cid, key, {"scheduledAt": when})
        check = call_fn("GET", "/emailCampaigns/%s" % cid, key)
        grund = pruefe_geplant(check, when)
        q["status"] = check.get("status")
        q["scheduled_at"] = check.get("scheduledAt")
        note(q, "fix", campaign_id=cid, scheduled_at=q["scheduled_at"],
             result="wieder geplant" if grund is None else grund)
        save_queue(a.queue, q)
        if grund:
            sys.exit("ACHTUNG: kampagne %s ist bestueckt, aber NICHT nachweislich "
                     "wieder geplant: %s. Von Hand nachsehen." % (cid, grund))
        print("kampagne %s ist wieder geplant auf %s, gelesen, nicht angenommen"
              % (cid, check.get("scheduledAt")))
    else:
        q["status"] = status
        note(q, "fix", campaign_id=cid, result="bestueckt, war nicht geplant")
        save_queue(a.queue, q)

    test_to = (a.test_to or "").strip() or q.get("sender") or ""
    if test_to:
        call_fn("POST", "/emailCampaigns/%s/sendTest" % cid, key, {"emailTo": [test_to]})
        print("testmail an %s raus, damit die korrigierte Fassung nachweisbar ist" % test_to)
    return 0


# Brevo nimmt "suspended" nur fuer eine Kampagne, die wirklich auf Abschuss
# steht. Ein Entwurf ist kein Abschuss, und der Aufruf antwortet mit
# HTTP 400 "suspended is an invalid status for draft campaign" (gesehen im
# Trockenlauf am 12.09.2026). Deshalb entscheidet diese Tabelle, ob ueberhaupt
# storniert wird. Alles, was nicht rausgehen kann, ist bereits gestoppt und
# haelt den Veto-Knopf gruen.
def cancel_decision(status):
    """('suspend', None) oder ('skip', grund)."""
    s = (status or "").strip()
    if s in ("queued", "inProcess", "in_process"):
        return "suspend", None
    if s == "sent":
        return "skip", "kampagne ist schon raus, storno nicht mehr moeglich"
    if s == "suspended":
        return "skip", "kampagne ist schon storniert"
    if s == "draft":
        return "skip", "kampagne ist ein entwurf, sie kann nicht von selbst rausgehen"
    return "skip", "unbekannter status %r, es wird nichts angefasst" % s


def mode_cancel(a, key, q):
    cid = q.get("campaign_id")
    if not cid:
        print("nichts zu stornieren: keine kampagne in %s" % a.queue)
        note(q, "cancel", campaign_id=None, result="nichts geplant")
        save_queue(a.queue, q)
        return 0
    state = call("GET", "/emailCampaigns/%s" % cid, key)
    what, why = cancel_decision(state.get("status"))
    if what == "skip":
        print("kampagne %s, status %r: %s" % (cid, state.get("status"), why))
        if state.get("status") == "sent":
            print("WARNUNG: %s" % why)
        q["status"] = state.get("status")
        if q["status"] != "sent":
            q["scheduled_at"] = None
        note(q, "cancel", campaign_id=cid, result=why)
        save_queue(a.queue, q)
        return 0
    call("PUT", "/emailCampaigns/%s/status" % cid, key, {"status": "suspended"})
    check = call("GET", "/emailCampaigns/%s" % cid, key)
    print("kampagne %s storniert, brevo meldet status %r" % (cid, check.get("status")))
    q["status"] = check.get("status") or "suspended"
    q["scheduled_at"] = None
    note(q, "cancel", campaign_id=cid, result=q["status"])
    save_queue(a.queue, q)
    return 0


# ---------------------------------------------------------------- Selbsttest

def selftest():
    import tempfile
    got = to_brevo_time("2126-09-14T16:05")
    assert got == "2126-09-14T16:05:00+02:00", got
    got = to_brevo_time("2126-11-16T16:05")
    assert got == "2126-11-16T16:05:00+01:00", got
    got = to_brevo_time("2126-09-14T16:05:00+00:00")
    assert got == "2126-09-14T16:05:00+00:00", got
    for bad in ("", "2020-01-01T10:00", "morgen frueh"):
        try:
            to_brevo_time(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("haette abbrechen muessen: %r" % bad)
    assert cancel_decision("queued") == ("suspend", None)
    assert cancel_decision("inProcess")[0] == "suspend"
    for st in ("draft", "sent", "suspended", "archive", "", None):
        assert cancel_decision(st)[0] == "skip", st
    tmp = os.path.join(tempfile.mkdtemp(), "q.json")
    q = load_queue(tmp)
    assert q["campaign_id"] is None
    q["campaign_id"] = 42
    note(q, "test", campaign_id=42)
    save_queue(tmp, q)
    again = load_queue(tmp)
    assert again["campaign_id"] == 42 and again["history"][-1]["step"] == "test"
    # planung: ein PUT, ein GET, kein zweiter statusaufruf (25.09.2026)
    soll = "2126-09-28T18:00:00+02:00"
    assert pruefe_geplant({"status": "queued",
                           "scheduledAt": "2126-09-28T16:00:00.000Z"}, soll) is None
    assert pruefe_geplant({"status": "draft",
                           "scheduledAt": "2126-09-28T16:00:00.000Z"}, soll)
    assert pruefe_geplant({"status": "queued", "scheduledAt": None}, soll)
    assert "gewollt" in pruefe_geplant({"status": "queued",
                                        "scheduledAt": "2126-09-28T14:05:00Z"}, soll)
    aufrufe = []

    def attrappe(method, path, key, body=None):
        aufrufe.append((method, path))
        if method == "GET":
            return {"status": "queued", "scheduledAt": "2126-09-28T16:00:00.000Z"}
        return {}

    class A:
        send_at = "2126-09-28T18:00"
        list_id = 16
        queue = os.path.join(tempfile.mkdtemp(), "q.json")
    q2 = {"campaign_id": 31, "history": []}
    assert mode_schedule(A, "k", q2, call_fn=attrappe) == 0
    assert aufrufe == [("PUT", "/emailCampaigns/31"), ("GET", "/emailCampaigns/31")], aufrufe
    assert not any(p.endswith("/status") for _, p in aufrufe)
    assert load_queue(A.queue)["status"] == "queued"
    assert load_queue(A.queue)["history"][-1]["result"] == "geplant"

    def entwurf(method, path, key, body=None):
        return {"status": "draft", "scheduledAt": None} if method == "GET" else {}
    q3 = {"campaign_id": 32, "history": []}
    try:
        mode_schedule(A, "k", q3, call_fn=entwurf)
    except SystemExit as e:
        assert "nicht nachweislich geplant" in str(e)
    else:
        raise AssertionError("ein entwurf haette rot werden muessen")
    assert load_queue(A.queue)["status"] == "draft"
    # mode fix: storniert, bestueckt, plant auf DENSELBEN termin zurueck
    weit = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=5)
            ).strftime("%Y-%m-%dT%H:%M:00.000Z")
    import tempfile as _tf2
    htmldir = _tf2.mkdtemp()
    hpfad = os.path.join(htmldir, "2026-10-05.html")
    with open(hpfad, "w", encoding="utf-8") as fh:
        fh.write("<html><body><td>1,525,975,596 to 1,524,397,554 kas, 1,578,042 less</td>"
                 "<p>issue 13 " + "x" * 250 + "</p></body></html>")
    fixe = []

    def attrappe_fix(method, path, key, body=None):
        fixe.append((method, path, tuple(sorted((body or {}).keys()))))
        if method == "GET":
            return {"status": "queued", "scheduledAt": weit}
        return {}

    class F:
        html = hpfad
        subject = ""
        test_to = "ben@example.com"
        queue = os.path.join(_tf2.mkdtemp(), "q.json")
    qf = {"campaign_id": 36, "history": [], "html_path": hpfad}
    assert mode_fix(F, "k", qf, call_fn=attrappe_fix) == 0
    wege = [(m, p) for m, p, _ in fixe]
    assert wege == [("GET", "/emailCampaigns/36"),
                    ("PUT", "/emailCampaigns/36/status"),
                    ("PUT", "/emailCampaigns/36"),
                    ("PUT", "/emailCampaigns/36"),
                    ("GET", "/emailCampaigns/36"),
                    ("POST", "/emailCampaigns/36/sendTest")], wege
    assert fixe[2][2] == ("htmlContent",), fixe[2]
    assert fixe[3][2] == ("scheduledAt",), fixe[3]
    assert load_queue(F.queue)["history"][-1]["result"] == "wieder geplant"
    assert load_queue(F.queue)["scheduled_at"] == weit

    # kurz vor dem versand wird nichts angefasst
    gleich = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=4)
              ).strftime("%Y-%m-%dT%H:%M:00.000Z")

    def attrappe_knapp(method, path, key, body=None):
        if method == "GET":
            return {"status": "queued", "scheduledAt": gleich}
        raise AssertionError("haette nichts anfassen duerfen")
    try:
        mode_fix(F, "k", {"campaign_id": 36, "history": [], "html_path": hpfad},
                 call_fn=attrappe_knapp)
    except SystemExit as e:
        assert "zehn Minuten" in str(e), str(e)
    else:
        raise AssertionError("knapp vor dem versand haette abbrechen muessen")

    # eine schon versendete kampagne wird nicht angefasst
    try:
        mode_fix(F, "k", {"campaign_id": 36, "history": [], "html_path": hpfad},
                 call_fn=lambda m, pth, k, body=None: {"status": "sent"})
    except SystemExit as e:
        assert "schon raus" in str(e)
    else:
        raise AssertionError("eine versendete kampagne haette abbrechen muessen")

    # offene platzhalter halten den versand an, fehlende bilder warnen nur
    assert fehlende_bilder('<img src="https://kaspapulse.com/graphics/social/x.png">') == \
        ["graphics/social/x.png"]
    assert fehlende_bilder('<img src="/graphics/number-of-day.png">') == []
    assert fehlende_bilder('<img src="https://example.com/fremd.png">') == []
    import tempfile as _tf3
    vorl = os.path.join(_tf3.mkdtemp(), "2026-10-12.html")
    with open(vorl, "w", encoding="utf-8") as fh:
        fh.write("<html><body><td>issue 14</td><a href=\"VIDEO_URL\">v</a>"
                 "<p>" + "x" * 250 + "</p></body></html>")
    try:
        html_lesen_und_pruefen(vorl)
    except SystemExit as e:
        assert "VIDEO_URL" in str(e), str(e)
    else:
        raise AssertionError("eine vorlage mit VIDEO_URL haette abbrechen muessen")

    # der Waechter haengt mit drin: ein HTML mit krummer Differenz geht nicht raus
    import tempfile as _tf
    rumpf = "<p>" + "x" * 250 + "</p></body></html>"
    bad = os.path.join(_tf.mkdtemp(), "n.html")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("<html><body><td>1,525,975,596 to 1,524,397,554 kas, 1,578,043 less</td>" + rumpf)
    try:
        html_lesen_und_pruefen(bad)
    except SystemExit:
        pass
    else:
        raise AssertionError("der waechter haette das html ablehnen muessen")
    gut = bad.replace("n.html", "g.html")
    with open(gut, "w", encoding="utf-8") as fh:
        fh.write("<html><body><td>1,525,975,596 to 1,524,397,554 kas, 1,578,042 less</td>" + rumpf)
    assert html_lesen_und_pruefen(gut)

    print("selftest ok: berliner zeiten stimmen, vergangenheit wird abgelehnt, "
          "entwurf wird nicht storniert, queue haelt, planung ist ein PUT plus "
          "ein lesender GET, ein nicht geplanter stand wird rot, und ein HTML "
          "mit krummer Differenz geht nicht an Brevo, und fix plant auf denselben "
          "termin zurueck")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("test", "update", "fix", "schedule", "cancel"))
    ap.add_argument("--html", help="Pfad zum fertigen Newsletter-HTML (mode test)")
    ap.add_argument("--subject", default="", help="Betreff (mode test)")
    ap.add_argument("--send-at", default="", help="ISO, Berliner Zeit, z. B. 2026-09-14T16:05")
    ap.add_argument("--test-to", default=os.environ.get("NEWSLETTER_TEST_TO", ""),
                    help="Empfaenger der Testmail, Vorgabe aus NEWSLETTER_TEST_TO")
    ap.add_argument("--list-id", type=int,
                    default=int(os.environ.get("NEWSLETTER_LIST_ID") or DEFAULT_LIST_ID),
                    help="Brevo-Liste, Vorgabe %d" % DEFAULT_LIST_ID)
    ap.add_argument("--name", default="", help="Kampagnenname in Brevo")
    ap.add_argument("--queue", default=QUEUE)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.mode:
        sys.exit("--mode fehlt (test, schedule oder cancel)")
    if a.mode == "test":
        if not a.html or not os.path.isfile(a.html):
            sys.exit("--html fehlt oder zeigt ins Leere: %r" % a.html)
        if not a.subject.strip():
            sys.exit("--subject fehlt")
    if a.mode in ("update", "fix") and a.html and not os.path.isfile(a.html):
        sys.exit("--html zeigt ins Leere: %r" % a.html)
    if a.mode == "schedule" and not a.send_at.strip():
        sys.exit("--send-at fehlt (ISO, Berliner Zeit)")
    key = key_from_env()
    q = load_queue(a.queue)
    return {"test": mode_test, "update": mode_update, "fix": mode_fix,
            "schedule": mode_schedule, "cancel": mode_cancel}[a.mode](a, key, q)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print("FEHLER: %s" % exc, file=sys.stderr)
        sys.exit(1)
