#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stufe_schaetzung.py, die naechste Reward-Stufe nur als Schaetzung (Ben, 12.11.2026).

WARUM
Die Stufe faellt auf einen DAA-Score, nicht auf eine Uhrzeit. Der Tag aus
dem Emissionsplan ist deshalb eine Schaetzung, die Minute erst recht. Bis
zum 12.11.2026 stand oeffentlich "on 5 dec" und "on 5 December 2026 around
00:15 UTC". Ab jetzt nennt jeder Text eine kuenftige Stufe nur so:

    kurz            around 5 dec, estimate
    im fliesstext   around 5 December 2026, an estimate, because the step is set by DAA score

Keine Uhrzeit auf die Minute. Alle Textskripte holen die beiden Formen
hier ab, damit es eine Stelle gibt.

DIE WACHE
verstoesse(text, heute) findet jeden Satz, der von einer Reward-Stufe
spricht (reward, step, cut, halving, emission, KAS a day) und ein Datum nach
heute nennt, aber "around" oder "estimate" nicht traegt, oder der eine
Uhrzeit auf die Minute nennt. seite_verstoesse(html) prueft eine fertige
Seite, Block fuer Block, dazu JSON-LD und Meta-Beschreibungen.
preis_wache.seite_pruefen ruft sie auf, damit seo_pruefung sie in jedem PR
mitnimmt.

    python3 scripts/stufe_schaetzung.py              alle oeffentlichen seiten, Exit 1 bei Treffer
    python3 scripts/stufe_schaetzung.py index.html
    python3 scripts/stufe_schaetzung.py --selbsttest
"""
import datetime as dt
import html as htmlmod
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

MON_KURZ = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
MON_LANG = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
            "October", "November", "December"]
GRUND = "because the step is set by DAA score"


def _tag(d):
    return d.date() if isinstance(d, dt.datetime) else d


def kurz(d):
    """'around 5 dec, estimate'"""
    d = _tag(d)
    return "around %d %s, estimate" % (d.day, MON_KURZ[d.month - 1])


def lang(d):
    """'around 5 December 2026, an estimate, because the step is set by DAA score'"""
    d = _tag(d)
    return "around %d %s %d, an estimate, %s" % (d.day, MON_LANG[d.month - 1], d.year, GRUND)


# ---------------------------------------------------------------- wache

STUFENWORT = re.compile(r"\b(?:reward|rewards|step|steps|stepping|cut|cuts|halving|emission|minted)\b"
                        r"|\bKAS\s+a\s+day\b", re.I)
_MON = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|" \
       r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
DATUM = re.compile(r"\b(\d{1,2})\s+" + _MON + r"\b(?:\s+(\d{4}))?", re.I)
DATUM_US = re.compile(r"\b" + _MON + r"\s+(\d{1,2})\b(?:,?\s+(\d{4}))?", re.I)
UHRZEIT = re.compile(r"\b\d{1,2}:\d{2}\b")
SATZENDE = re.compile(r"(?<=[.?!])\s+")


def _daten(satz, heute):
    aus = []
    for m in DATUM.finditer(satz):
        aus.append((int(m.group(1)), m.group(2), m.group(3)))
    for m in DATUM_US.finditer(satz):
        aus.append((int(m.group(2)), m.group(1), m.group(3)))
    tage = []
    for tag, mon, jahr in aus:
        k = mon[:3].lower()
        if k not in MON_KURZ:
            continue
        j = int(jahr) if jahr else heute.year
        try:
            d = dt.date(j, MON_KURZ.index(k) + 1, tag)
        except ValueError:
            continue
        # ohne jahr und fast ein jahr zurueck ("5 jan" im dezember): gemeint
        # ist das naechste jahr. "5 aug" auf einer alten wochenseite bleibt
        # in diesem jahr und damit vorbei.
        if not jahr and (heute - d).days > 300:
            d = dt.date(j + 1, d.month, d.day)
        tage.append(d)
    return tage


def satz_verstoss(satz, heute):
    """None oder der Grund, warum der Satz eine kuenftige Stufe ohne Schaetzung nennt."""
    if not STUFENWORT.search(satz):
        return None
    # nach heute. der messtag selbst ("on 12 November 2026 at 15:16 UTC") ist
    # keine kuenftige stufe
    kuenftig = [d for d in _daten(satz, heute) if d > heute]
    if not kuenftig:
        return None
    t = satz.lower()
    if "around" not in t or "estimate" not in t:
        return "kuenftige stufe ohne around und estimate"
    if UHRZEIT.search(satz):
        return "kuenftige stufe mit uhrzeit"
    return None


def verstoesse(text, heute=None):
    heute = heute or dt.datetime.now(dt.timezone.utc).date()
    aus = []
    for zeile in (text or "").split("\n"):
        for satz in SATZENDE.split(zeile):
            satz = " ".join(satz.split())
            g = satz_verstoss(satz, heute)
            if g:
                aus.append("%s: %r" % (g, satz[:160]))
    return aus


BLOCK = re.compile(r"(?i)</?(?:p|li|h[1-6]|tr|div|figcaption|caption|section|article|header|footer|table|"
                   r"ul|ol|dd|dt|br|blockquote|summary|details|figure|svg|main|nav|aside)\b[^>]*>")


def sichtbare_bloecke(s):
    t = re.sub(r"(?is)<template\b.*?</template>", " ", s or "")
    t = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", t)
    t = re.sub(r"(?is)<!--.*?-->", " ", t)
    t = BLOCK.sub("\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return "\n".join(" ".join(z.split()) for z in htmlmod.unescape(t).split("\n") if z.strip())


def _strings(daten):
    if isinstance(daten, dict):
        for v in daten.values():
            yield from _strings(v)
    elif isinstance(daten, list):
        for v in daten:
            yield from _strings(v)
    elif isinstance(daten, str):
        yield daten


def seite_verstoesse(s, heute=None):
    aus = verstoesse(sichtbare_bloecke(s), heute)
    for b in re.findall(r'(?is)<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', s or ""):
        try:
            for v in _strings(json.loads(b)):
                aus += ["schema, " + x for x in verstoesse(v, heute)]
        except ValueError:
            continue
    for m in re.finditer(r'(?is)<meta\s+(?:name|property)="(?:description|og:description|twitter:description)"'
                         r'\s+content="([^"]*)"', s or ""):
        aus += ["meta, " + x for x in verstoesse(htmlmod.unescape(m.group(1)), heute)]
    return aus


# ---------------------------------------------------------------- selbsttest

def selbsttest():
    f = []

    def ok(name, bed, info=""):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, ("  " + str(info)) if not bed and info else ""))
        if not bed:
            f.append(name)

    h = dt.date(2026, 11, 12)
    stufe = dt.datetime(2026, 12, 5, 0, 15, tzinfo=dt.timezone.utc)
    ok("kurzform", kurz(stufe) == "around 5 dec, estimate", kurz(stufe))
    ok("fliesstext", lang(stufe) == "around 5 December 2026, an estimate, because the step is set by DAA score",
       lang(stufe))
    for alt in ("daily emission steps down to 1,585,790 KAS on 5 dec",
                "1,585,790 KAS a day on 5 dec, after 1,680,086 on 4 nov",
                "The next monthly reward step is on 5 December 2026 around 00:15 UTC, when the block reward falls.",
                "Next reward step on 5 December 2026 around 00:15 UTC, block reward from 1.9445 to 1.8354 KAS",
                "The reward falls about 5.6% every month, the next step is on 5 December 2026.",
                "next step 5 Dec 2026, 00:15 UTC, computed by kaspa pulse from the emission schedule",
                "the next cut lands december 24 and changes the emission for everyone.",
                "kaspa block reward, falls on 5 dec"):
        ok("alt ist rot: %s" % alt[:60], bool(verstoesse(alt, h)), verstoesse(alt, h))
    for neu in ("daily emission steps down to 1,585,790 KAS %s" % kurz(stufe),
                "The next monthly reward step is %s." % lang(stufe),
                "the kaspa block reward stepped down on 4 nov, from 2.0602 to 1.9445 KAS per block",
                "296,503 addresses hold at least 100 KAS on 8 nov 2026, source kaspalytics.",
                "6 days to the next block reward cut.",
                "the next step is estimated for around 5 december 2026."):
        ok("gruen: %s" % neu[:60], not verstoesse(neu, h), verstoesse(neu, h))
    ok("schaetzung mit uhrzeit ist rot", bool(verstoesse(
        "next step around 5 Dec 2026 at 00:15 UTC, an estimate", h)))
    ok("vergangene stufe mit uhrzeit ist gruen", not verstoesse(
        "the reward stepped down on 4 nov 2026 at 13:45 UTC", h))
    ok("messtag mit uhrzeit ist keine stufe", not verstoesse(
        "4.91 KAS a day for 1 TH/s on 12 November 2026 at 15:16 UTC, computed from the block reward", h))
    ok("alte wochenseite ohne jahr ist vorbei", not verstoesse(
        "daily emission steps down to 1,997,970 KAS on 5 aug", h))
    ok("5 jan im dezember ist kuenftig", bool(verstoesse(
        "daily emission steps down on 5 jan", dt.date(2026, 12, 20))))
    seite = ('<table><tr><td>block reward</td><td><b>1.9445 KAS</b><small>computed from the emission schedule, '
             'until 5 December 2026 around 00:15 UTC</small></td></tr><tr><td>network hashrate</td><td>342 PH/s'
             '<small>source the Kaspa REST API, 12 November 2026 at 15:16 UTC</small></td></tr></table>'
             '<script type="application/ld+json">{"a":{"text":"The next step is on 5 December 2026."}}</script>')
    v = seite_verstoesse(seite, h)
    ok("seite, tabellenzeile und json-ld rot, hashrate-zeile nicht", len(v) == 2
       and any("schema" in x for x in v) and not any("hashrate" in x for x in v), v)
    ok("neue tabellenzeile gruen", not seite_verstoesse(
        "<table><tr><td>block reward</td><td><b>1.9445 KAS</b><small>computed from the emission schedule, "
        "until %s</small></td></tr></table>" % kurz(stufe), h))
    print("")
    print("%d fehler" % len(f) if f else "alle testfaelle bestanden")
    return 1 if f else 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--selbsttest" in argv:
        return selbsttest()
    sys.path.insert(0, str(REPO / "scripts"))
    if argv:
        namen = argv
    else:
        import seo_pruefung
        namen = seo_pruefung.seiten()
    n = 0
    for name in namen:
        p = REPO / name
        if not p.exists():
            continue
        for v in seite_verstoesse(p.read_text(encoding="utf-8")):
            print("ROT  %s, %s" % (name, v))
            n += 1
    print("%d seiten geprueft, %d verstoesse" % (len(namen), n))
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
