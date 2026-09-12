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
    python3 scripts/brevo_send.py --mode schedule --send-at 2026-09-14T16:05 --list-id 16
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
import sys
import urllib.error
import urllib.request

API = "https://api.brevo.com/v3"
TIMEOUT = 60
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


# ---------------------------------------------------------------- Modi

def mode_test(a, key, q):
    with open(a.html, encoding="utf-8") as fh:
        html = fh.read()
    if len(html) < 200:
        sys.exit("das HTML ist kuerzer als 200 Zeichen, das kann nicht der Newsletter sein: %s" % a.html)
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


def mode_schedule(a, key, q):
    cid = q.get("campaign_id")
    if not cid:
        sys.exit("keine kampagne in %s, erst --mode test laufen lassen" % a.queue)
    when = to_brevo_time(a.send_at)
    print("plane kampagne %s auf liste %d, scheduledAt %s" % (cid, a.list_id, when))
    call("PUT", "/emailCampaigns/%s" % cid, key,
         {"recipients": {"listIds": [a.list_id]}, "scheduledAt": when})
    call("PUT", "/emailCampaigns/%s/status" % cid, key, {"status": "queued"})
    check = call("GET", "/emailCampaigns/%s" % cid, key)
    print("brevo meldet status %r, scheduledAt %r"
          % (check.get("status"), check.get("scheduledAt")))
    q["status"] = check.get("status") or "queued"
    q["scheduled_at"] = check.get("scheduledAt") or when
    q["list_id"] = a.list_id
    note(q, "schedule", campaign_id=cid, scheduled_at=q["scheduled_at"], list_id=a.list_id)
    save_queue(a.queue, q)
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
    print("selftest ok: berliner zeiten stimmen, vergangenheit wird abgelehnt, "
          "entwurf wird nicht storniert, queue haelt")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("test", "schedule", "cancel"))
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
    if a.mode == "schedule" and not a.send_at.strip():
        sys.exit("--send-at fehlt (ISO, Berliner Zeit)")
    key = key_from_env()
    q = load_queue(a.queue)
    return {"test": mode_test, "schedule": mode_schedule, "cancel": mode_cancel}[a.mode](a, key, q)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print("FEHLER: %s" % exc, file=sys.stderr)
        sys.exit(1)
