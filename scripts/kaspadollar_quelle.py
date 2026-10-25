#!/usr/bin/env python3
"""Kaspa Pulse, KaspaDollar-Spenden, Quelle kaspadollar.com (Ben, 25.10.2026).

Die Spendenadresse kommt NUR von https://kaspadollar.com (Feld neben "Copy").
Sie wird nie ausgegeben, nie in eine Datei im Repo und nie in ein Artefakt
geschrieben. Ausgaben tragen statt jeder Kaspa-Adresse "[adresse <sha256 10>]".

    python3 scripts/kaspadollar_quelle.py --erkunden            # Aufbau der Seite, ohne Adressen
    python3 scripts/kaspadollar_quelle.py --adresse-nach DATEI  # Adresse in eine Datei im Runner, druckt nur den Hash
    python3 scripts/kaspadollar_quelle.py --stand [--um ISO] [--nach DATEI]  # angezeigter Stand, source kaspadollar.com
    python3 scripts/kaspadollar_quelle.py --selbsttest
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request

SEITE = "https://kaspadollar.com/"
UA = "kaspa-pulse-spendenzaehlung (+https://kaspapulse.com)"
ADR = re.compile(r"kaspa:[a-z0-9]{50,70}")


def h(adr):
    return hashlib.sha256(adr.encode()).hexdigest()[:10]


def ohne_adressen(text):
    return ADR.sub(lambda m: "[adresse %s]" % h(m.group(0)), text)


def holen(url, versuche=3):
    letzter = None
    for _ in range(versuche):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace"), r.headers.get("Content-Type", "")
        except Exception as exc:                    # noqa: BLE001
            letzter = type(exc).__name__
    raise RuntimeError("nicht erreichbar (%s)" % letzter)


def text_zeilen(html):
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", "\n", html)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#x27;", "'"), ("&quot;", '"')):
        text = text.replace(a, b)
    return [z for z in (" ".join(x.split()) for x in text.split("\n")) if z]


def adresse_neben_copy(html):
    """Adressen der Seite mit ihrem Umfeld. Gesucht ist die neben 'Copy'."""
    funde = []
    for m in ADR.finditer(html):
        umfeld = html[max(0, m.start() - 400):m.end() + 400]
        funde.append((m.group(0), bool(re.search(r"(?i)\bcopy\b", umfeld))))
    return funde


def erkunden():
    html, typ = holen(SEITE)
    zeilen = text_zeilen(html)
    wort = re.compile(r"(?i)kas|donat|goal|raised|copy|%|progress|target|spend")
    skripte = sorted(set(re.findall(r'(?i)<script[^>]+src="([^"]+)"', html)))
    funde = adresse_neben_copy(html)
    aus = {"quelle": "source kaspadollar.com", "abgerufen_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
           "typ": typ, "bytes": len(html),
           "adressen": [{"hash": h(a), "neben_copy": c} for a, c in funde],
           "adressen_verschieden": len({a for a, _c in funde}),
           "zeilen": [ohne_adressen(z) for z in zeilen if (re.search(r"\d", z) or wort.search(z)) and len(z) <= 200][:120],
           "skripte": skripte[:30]}
    # in den skripten nach abrufen suchen (fetch, api, rpc), nur pfade und domains
    pfade = set()
    for s in skripte[:12]:
        url = urllib.parse.urljoin(SEITE, s)
        try:
            js, _t = holen(url)
        except RuntimeError:
            continue
        for m in re.finditer(r"""["'`](https?://[^"'`\s]{4,200}|/api/[^"'`\s]{0,120}|wss?://[^"'`\s]{4,200})""", js):
            pfade.add(ohne_adressen(m.group(1)))
        aus.setdefault("adressen_in_skripten", 0)
        aus["adressen_in_skripten"] += len(set(ADR.findall(js)))
    aus["abrufe_in_skripten"] = sorted(pfade)[:80]
    print(ohne_adressen(json.dumps(aus, indent=1, ensure_ascii=False)))
    return 0


def adresse_nach(pfad):
    html, _t = holen(SEITE)
    neben = sorted({a for a, c in adresse_neben_copy(html) if c})
    if len(neben) != 1:
        print("keine eindeutige adresse neben copy (%d)" % len(neben))
        return 2
    with open(pfad, "w", encoding="utf-8") as fh:
        fh.write(neben[0])
    print("adresse gelesen, sha256 %s, abgerufen %s" % (h(neben[0]), dt.datetime.now(dt.timezone.utc).isoformat()))
    return 0


def stand_aus(html):
    """angezeigter Spendenstand: '<zahl>' 'of <ziel> KAS has' ... '<prozent>%'."""
    text = " ".join(text_zeilen(html))
    m = re.search(r"([\d][\d,\.]*)\s+of\s+([\d][\d,\.]*)\s*KAS", text)
    p = re.search(r"([\d]+(?:\.\d+)?)\s*%", text)
    if not m:
        return None
    zahl = lambda x: float(x.replace(",", ""))  # noqa: E731
    return {"kas": zahl(m.group(1)), "ziel_kas": zahl(m.group(2)), "prozent": float(p.group(1)) if p else None}


def stand(um=None, nach=None):
    """Stand laut kaspadollar.com; mit --um erst zu dieser Zeit (UTC) abrufen."""
    if um:
        ziel = dt.datetime.fromisoformat(um.replace("Z", "+00:00"))
        warte = (ziel - dt.datetime.now(dt.timezone.utc)).total_seconds()
        if warte > 0:
            import time
            time.sleep(warte)
    html, _t = holen(SEITE)
    d = stand_aus(html) or {}
    d.update({"quelle": "source kaspadollar.com", "abgerufen_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "adresse_neben_copy_sha256": [h(a) for a, c in adresse_neben_copy(html) if c]})
    if nach:
        with open(nach, "w", encoding="utf-8") as fh:
            json.dump(d, fh)
    print(json.dumps(d))
    return 0


def selbsttest():
    fehler = []

    def ok(name, bed, ist=None):
        if not bed:
            fehler.append(name)
            print("FEHLER", name, ist)
    a = "kaspa:" + "q" * 61
    ok("adresse wird ersetzt", a not in ohne_adressen("x %s y" % a) and "[adresse " in ohne_adressen(a))
    html = "<div>Donate <span>%s</span><button>Copy</button></div>" % a + "x" * 900 + "kaspa:" + "p" * 61
    f = adresse_neben_copy(html)
    ok("adresse neben copy erkannt, die ferne nicht", f == [(a, True), ("kaspa:" + "p" * 61, False)], f)
    st = stand_aus("<p>91,352</p><p>of 5,000,000 KAS has</p><p>been raised so far</p><p>1.8%</p>")
    ok("stand gelesen", st == {"kas": 91352.0, "ziel_kas": 5000000.0, "prozent": 1.8}, st)
    ok("textzeilen ohne skript", text_zeilen("<p>91,352 KAS</p><script>x</script>") == ["91,352 KAS"])
    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--erkunden", action="store_true")
    ap.add_argument("--adresse-nach")
    ap.add_argument("--stand", action="store_true")
    ap.add_argument("--um")
    ap.add_argument("--nach")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    if a.erkunden:
        return erkunden()
    if a.stand:
        return stand(a.um, a.nach)
    if a.adresse_nach:
        return adresse_nach(a.adresse_nach)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
