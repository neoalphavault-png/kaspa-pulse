#!/usr/bin/env python3
"""ph_hand.py - die Aufforderung "📤 VON HAND" zum PulseHawk-Entwurf (Ben, 28.10.2026).

Der Entwurf selbst geht wie bisher ueber ph_entwurf.py nach #ph-entwuerfe
(DISCORD_WEBHOOK_PH_DRAFTS). Gepostet wird von Hand auf X @pulsehawkio. Damit
Ben das nicht verpasst, kommt danach eine Handlung nach #moderator-only (Art
"hand" in scripts/ops_melden.py): Zeit, Plattform, Link, der vollstaendige
Posttext, die Antwort mit weiteren Tags (falls im Entwurf eine antwort.txt
liegt) und der Hinweis, dass die Grafik im #ph-entwuerfe-Post von heute
haengt. Gepostet wird erst nach einem Haken von Claude im Chat.

Bevor etwas rausgeht, prueft dieses Skript den Text noch einmal mit den
Textregeln aus ph_entwurf.regel_pruefen. Fehlt der Entwurf, ist er nicht
nach #ph-entwuerfe gegangen oder verstoesst er gegen eine Regel, geht nichts
nach #moderator-only, nur eine Meldung nach #ops-log.

ph_entwurf.py liegt gleich in kaspa-pulse und pulsehawk-site und bleibt
unveraendert. Diese Datei gibt es nur hier.

    python3 scripts/ph/ph_hand.py --aus entwurf --entwurf success [--probe]
    python3 scripts/ph/ph_hand.py --selbsttest
"""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent))

import ops_melden  # noqa: E402

COMPOSE = "https://x.com/compose/post"
KONTO = "X @pulsehawkio"
ZEIT_MI = "Mi 17:45"
MARKE = "Erst nach ✅ von Claude im Chat posten"


def berlin(jetzt=None):
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return jetzt.astimezone(ZoneInfo("Europe/Berlin"))
    except Exception:                                  # noqa: BLE001
        return jetzt


def zeit_text(jetzt=None):
    """Mittwochs vor 17:45 Berlin heisst es "Mi 17:45", sonst laeuft der
    Entwurf ausser der Reihe und Ben postet, sobald Claude freigibt."""
    b = berlin(jetzt)
    if b.weekday() == 2 and (b.hour, b.minute) <= (17, 45):
        return ZEIT_MI
    return "heute, sobald freigegeben"


def lesen(aus):
    aus = Path(aus)
    text = (aus / "text.txt").read_text(encoding="utf-8").strip() if (aus / "text.txt").exists() else ""
    antwort = (aus / "antwort.txt").read_text(encoding="utf-8").strip() if (aus / "antwort.txt").exists() else ""
    meta = json.loads((aus / "meta.json").read_text(encoding="utf-8")) if (aus / "meta.json").exists() else {}
    return text, antwort, meta


def nachricht(text, antwort, meta, jetzt=None):
    teile = ["%s %s, %s, %s. %s" % (ops_melden.VON_HAND, zeit_text(jetzt), KONTO, COMPOSE, MARKE),
             "posttext\n```\n%s\n```" % text]
    if antwort:
        teile.append("antwort mit weiteren tags\n```\n%s\n```" % antwort)
    teile.append("die grafik haengt im #ph-entwuerfe-post von heute (%s, layout %s)."
                 % (meta.get("quelle", "bch"), meta.get("layout", "?")))
    return "\n".join(teile)


def lauf(aus, entwurf_ergebnis, probe=False, jetzt=None):
    """Gibt die Art zurueck, die gesendet wurde ("hand" oder "log")."""
    import ph_entwurf
    text, antwort, meta = lesen(aus)
    grund = ""
    if entwurf_ergebnis != "success":
        grund = "der entwurf-schritt endete mit %s, nichts in #ph-entwuerfe" % (entwurf_ergebnis or "?")
    elif not text:
        grund = "kein text.txt im entwurf"
    else:
        fehler = ph_entwurf.regel_pruefen(text)
        if fehler:
            grund = "textregeln, %s" % "; ".join(fehler)
    if grund:
        ops_melden.log("pulsehawk bch, keine aufforderung nach #moderator-only. %s" % grund,
                       was="pulsehawk aufforderung")
        return "log"
    inhalt = nachricht(text, antwort, meta, jetzt)
    if probe:
        ops_melden.log("PROBE, nicht posten.\n" + inhalt, was="pulsehawk aufforderung")
        return "log"
    ops_melden.hand(inhalt, was="pulsehawk aufforderung")
    return "hand"


def selbsttest():
    import contextlib
    import io
    import tempfile
    f = []

    def ok(name, bed, *mehr):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, (" " + repr(mehr)) if mehr and not bed else ""))
        if not bed:
            f.append(name)

    gut = ("bch tempnet 2027 with one minute blocks.\n"
           "we counted a median block interval of 43.0 s over 7,572 blocks, against 41.6 s computed.\n"
           "that is close to what an ideal 60 s chain shows.\n"
           "window 15 oct 2026, 12:56 to 21 oct 2026, 09:59 utc, blocks 327,989 to 335,560.\n"
           "method on pulsehawk.io")
    gesendet = []
    echt = ops_melden._post
    alt = {k: os.environ.get(k) for k in ops_melden.ARTEN.values()}
    ops_melden._post = lambda url, body, typ, timeout=60: gesendet.append(
        (url.rsplit("/", 1)[1], json.loads(body)["content"])) or 204
    basis = "https://discord.com/api/" + "webhooks/"
    os.environ["DISCORD_WEBHOOK_OPS"] = basis + "1/hand"
    os.environ["DISCORD_WEBHOOK_LOG"] = basis + "2/log"
    mi = dt.datetime(2026, 10, 28, 15, 0, tzinfo=dt.timezone.utc)        # mi 16:00 berlin
    try:
        with tempfile.TemporaryDirectory() as td:
            aus = Path(td)
            (aus / "text.txt").write_text(gut + "\n", encoding="utf-8")
            (aus / "meta.json").write_text(json.dumps({"quelle": "bch", "layout": "verteilung"}), encoding="utf-8")

            def leise(*a, **k):
                with contextlib.redirect_stdout(io.StringIO()):
                    return lauf(*a, **k)
            ok("probe nur nach ops-log", leise(aus, "success", probe=True, jetzt=mi) == "log"
               and gesendet[-1][0] == "log" and gesendet[-1][1].startswith("PROBE"))
            ok("gruener entwurf von hand nach moderator-only", leise(aus, "success", jetzt=mi) == "hand"
               and gesendet[-1][0] == "hand")
            t = gesendet[-1][1]
            ok("kopf wie von ben", t.startswith("📤 VON HAND Mi 17:45, X @pulsehawkio, https://x.com/compose/post. "
                                                 "Erst nach ✅ von Claude im Chat posten"), t[:120])
            ok("vollstaendiger posttext und grafik-hinweis", gut in t and "#ph-entwuerfe-post von heute" in t)
            ok("ohne antwort.txt kein antwort-block", "antwort mit weiteren tags" not in t)
            (aus / "antwort.txt").write_text("more counts on pulsehawk.io\n", encoding="utf-8")
            leise(aus, "success", jetzt=mi)
            ok("mit antwort.txt die antwort dabei", "antwort mit weiteren tags" in gesendet[-1][1])
            (aus / "antwort.txt").unlink()
            ok("nach 17:45 oder an einem anderen tag ohne festen termin",
               zeit_text(dt.datetime(2026, 10, 29, 10, tzinfo=dt.timezone.utc)) == "heute, sobald freigegeben")
            (aus / "text.txt").write_text(gut.replace("bch", "BCH") + "\n", encoding="utf-8")
            n = len([g for g in gesendet if g[0] == "hand"])
            ok("regelverstoss, nur ops-log", leise(aus, "success", jetzt=mi) == "log"
               and "textregeln" in gesendet[-1][1] and len([g for g in gesendet if g[0] == "hand"]) == n)
            ok("entwurf-schritt rot, nur ops-log", leise(aus, "failure", jetzt=mi) == "log"
               and "failure" in gesendet[-1][1])
            (aus / "text.txt").unlink()
            ok("ohne text, nur ops-log", leise(aus, "success", jetzt=mi) == "log")
    finally:
        ops_melden._post = echt
        for k, v in alt.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    print("%d fehler" % len(f))
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--aus", default="entwurf")
    ap.add_argument("--entwurf", default="success", help="ergebnis des entwurf-schritts (steps.<id>.outcome)")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    try:
        lauf(a.aus, a.entwurf, a.probe)
    except ops_melden.Fehler as exc:
        print(ops_melden.sauber(exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
