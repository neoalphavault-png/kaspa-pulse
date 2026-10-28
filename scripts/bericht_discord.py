#!/usr/bin/env python3
"""Kaspa Pulse, Teil eines Berichts in den privaten Ops-Kanal (Ben, 26.10.2026).

Ein Bericht unter berichte/ kann einen Abschnitt zwischen <!-- discord --> und
<!-- /discord --> tragen, unterteilt mit <!-- teil -->. Seit 28.10.2026 gehen
die Teile ueber scripts/ops_melden.py in zwei Kanaele:

    log   eine Kopfzeile mit Bericht, Link und den gezaehlten Teilen, dann
          alle Teile, die nicht mit "📤 VON HAND" beginnen, nach #ops-log
          (DISCORD_WEBHOOK_LOG)
    hand  jeder Teil, der mit "📤 VON HAND" beginnt, einzeln nach
          #moderator-only (DISCORD_WEBHOOK_OPS), mit dem Link zum Bericht

Die Zahlen in der Kopfzeile werden aus der fertigen Liste gezaehlt. Vor dem
Senden wird der ganze Text geprueft: keine IP, keine Kaspa-Adresse, kein
Hostname ausser github.com und kaspapulse.com, kein Schluessel. Bei einem Fund
geht nichts raus.

Absicherung gegen doppelten Versand (Ben, 26.10.2026, nachdem der STP-Rat
zweimal kam):
  1. Im Workflow kommen nur Berichte in Frage, die in den Commits dieses
     Pushes geaendert wurden, und nur in Commits, die mit diesem Push zum
     ersten Mal ins Repo kamen (distinct). Berichte aus einem Eltern-Branch
     fallen damit heraus.
  2. Je Bericht wird die Pruefsumme des Discord-Abschnitts in einer Merkdatei
     festgehalten (Branch ops/bericht-gesendet). Derselbe Abschnitt desselben
     Berichts geht nie ein zweites Mal raus, auf keinem Branch. Ein Rebase
     oder Force-Push mit gleichem Inhalt sendet also nichts.

Die Webhooks kommen nur aus der Umgebung und werden nie ausgegeben.

    python3 scripts/bericht_discord.py --datei berichte/2026-10-27-stp-rat.md --link URL [--trocken]
    python3 scripts/bericht_discord.py --ereignis "$GITHUB_EVENT_PATH" --branch NAME \\
        --merkdatei gesendet.json --link-basis URL [--trocken]
    python3 scripts/bericht_discord.py --vereinen A B     # zwei Merkdateien zu A
    python3 scripts/bericht_discord.py --selbsttest
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ops_melden  # noqa: E402

AUF, ZU, TEIL = "<!-- discord -->", "<!-- /discord -->", "<!-- teil -->"
GRENZE = 1900
VERBOTEN = (
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "ip"),
    (re.compile(r"\b(?:kaspa|kaspatest):[a-z0-9]{20,}"), "adresse"),
    # erlaubt sind github.com und unsere eigene, oeffentliche Domain kaspapulse.com: Ben
    # muss Links wie die Ziel-URL einer Anzeige kopieren koennen (Ben, 26.10.2026).
    # Unterdomains davon bleiben gesperrt, sie koennten Infrastruktur sein.
    (re.compile(r"(?i)(?<![a-z0-9.-])(?!(?:github|kaspapulse)\.com(?![.\w-]))(?:[a-z0-9-]+\.)+(?:com|io|org|net|de|blue|red|green|stream|xyz|app|dev)\b"), "hostname"),
    (re.compile(r"ghp_|github_pat_|xox[bap]-|sk-[A-Za-z0-9]{20}|BEGIN [A-Z ]*PRIVATE KEY|discord(?:app)?\.com/api/webhooks"), "schluessel"),
)


def teile(text):
    if AUF not in text or ZU not in text:
        return []
    innen = text[text.index(AUF) + len(AUF):text.index(ZU)]
    return [t.strip() for t in innen.split(TEIL) if t.strip()]


def pruefsumme(t):
    """sha256 ueber genau die Teile, die gesendet wuerden."""
    return hashlib.sha256(("\n" + TEIL + "\n").join(t).encode("utf-8")).hexdigest()


def pruefen(texte):
    funde = []
    for i, t in enumerate(texte):
        for rx, art in VERBOTEN:
            if rx.search(t):
                funde.append("teil %d: %s" % (i, art))
        if len(t) > GRENZE:
            funde.append("teil %d: %d zeichen, hoechstens %d" % (i, len(t), GRENZE))
    return funde


def kopf(datei, n_log, n_hand, link):
    """Die Kopfzeile in #ops-log. Sie traegt kein "📤 VON HAND", die
    Handlungen stehen einzeln in #moderator-only."""
    return ("**Bericht %s**\n%d %s hier, %d %s in #moderator-only.\nBericht: %s"
            % (os.path.basename(datei), n_log, "teil" if n_log == 1 else "teile",
               n_hand, "handlung" if n_hand == 1 else "handlungen", link or datei))


def aufteilen(t):
    """Die Teile mit "📤 VON HAND" vorn sind Handlungen, alle anderen Info."""
    hand = [x for x in t if x.startswith(ops_melden.VON_HAND)]
    return [x for x in t if x not in hand], hand


def mit_link(t, link):
    zusatz = "\nBericht: %s" % link if link else ""
    return t + zusatz if len(t) + len(zusatz) <= GRENZE else t


def nachrichten(datei, t, link):
    """Liste aus (art, text): Kopfzeile und Info nach log, Handlungen nach
    hand. Die Zahlen im Kopf werden aus der fertigen Liste gezaehlt, nicht
    vorgegeben."""
    info, hand = aufteilen(t)
    folgen = [("log", x) for x in info] + [("hand", mit_link(x, link)) for x in hand]
    n_log = sum(1 for art, _ in folgen if art == "log")
    return [("log", kopf(datei, n_log, len(folgen) - n_log, link))] + folgen


def texte(alle):
    return [x for _, x in alle]


def senden(alle, pause=1.0):
    """alle ist eine Liste aus (art, text). Rot ist eine Absage von Discord
    oder eine Handlung ohne DISCORD_WEBHOOK_OPS. Ein fehlendes
    DISCORD_WEBHOOK_LOG laesst die Info nur im Job-Log stehen."""
    for i, (art, t) in enumerate(alle):
        try:
            status = ops_melden.senden(art, t, was="bericht teil %d" % i)
        except ops_melden.Fehler as exc:
            print("nachricht %d nicht gesendet, %s" % (i, ops_melden.sauber(exc)))
            return 1
        if status is None and art == "hand":
            print("nachricht %d ist eine handlung und kein webhook fuer #moderator-only da" % i)
            return 3
        if status is not None:
            time.sleep(pause)
    return 0


# ------------------------------------------------------------ merkdatei

def merk_lesen(pfad):
    if not pfad or not os.path.exists(pfad):
        return {"eintraege": []}
    with open(pfad, encoding="utf-8") as fh:
        m = json.load(fh)
    m.setdefault("eintraege", [])
    return m


def merk_schreiben(pfad, m):
    m["eintraege"].sort(key=lambda e: (e.get("utc", ""), e["datei"], e["branch"]))
    with open(pfad, "w", encoding="utf-8") as fh:
        json.dump(m, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def schon_gesendet(m, datei, summe):
    """derselbe Abschnitt desselben Berichts, auf irgendeinem Branch."""
    return next((e for e in m["eintraege"] if e["datei"] == datei and e["sha256"] == summe), None)


def merken(m, branch, datei, summe, jetzt=None):
    m["eintraege"].append({"branch": branch, "datei": datei, "sha256": summe,
                           "utc": jetzt or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})


FELDER = {"branch", "datei", "sha256", "utc", "hinweis"}


def merk_pruefen(m):
    """Liste der Fehler in einer Merkdatei. Erlaubt sind nur Branch, Pfad
    unter berichte/, sha256 und Zeit (dazu ein Hinweis), damit der
    Schreib-Job nichts anderes auf ops/bericht-gesendet legt."""
    fehler = []
    if not isinstance(m, dict) or set(m) != {"eintraege"} or not isinstance(m["eintraege"], list):
        return ["kopf: nur der schluessel eintraege erlaubt"]
    for i, e in enumerate(m["eintraege"]):
        if not isinstance(e, dict) or not {"branch", "datei", "sha256", "utc"} <= set(e) or set(e) - FELDER:
            fehler.append("eintrag %d: felder" % i)
            continue
        if not re.fullmatch(r"[A-Za-z0-9._/-]{1,100}", str(e["branch"])):
            fehler.append("eintrag %d: branch" % i)
        if not re.fullmatch(r"berichte/[A-Za-z0-9._-]{1,100}\.md", str(e["datei"])):
            fehler.append("eintrag %d: datei" % i)
        if not re.fullmatch(r"[0-9a-f]{64}", str(e["sha256"])):
            fehler.append("eintrag %d: sha256" % i)
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?", str(e["utc"])):
            fehler.append("eintrag %d: utc" % i)
        if len(str(e.get("hinweis", ""))) > 200 or pruefen([str(e.get("hinweis", ""))]):
            fehler.append("eintrag %d: hinweis" % i)
    return fehler


def vereinen(a, b):
    """Eintraege aus b, die in a fehlen, kommen dazu."""
    schluessel = {(e["branch"], e["datei"], e["sha256"]) for e in a["eintraege"]}
    for e in b["eintraege"]:
        if (e["branch"], e["datei"], e["sha256"]) not in schluessel:
            a["eintraege"].append(e)
    return a


# ------------------------------------------------------------ push-ereignis

def geaenderte_berichte(ereignis):
    """Berichte (berichte/*.md), die in den Commits dieses Pushes hinzukamen
    oder geaendert wurden. Nur Commits mit distinct = true, also zum ersten
    Mal ins Repo gekommen; Commits aus einem Eltern-Branch zaehlen nicht."""
    dateien = []
    for c in ereignis.get("commits") or []:
        if not c.get("distinct", True):
            continue
        for f in (c.get("added") or []) + (c.get("modified") or []):
            if f.startswith("berichte/") and f.endswith(".md") and f not in dateien:
                dateien.append(f)
    for f in [f for c in ereignis.get("commits") or [] for f in c.get("removed") or []]:
        if f in dateien:
            dateien.remove(f)
    return dateien


def lage(ereignis):
    """Eine Zeile fuer das Job-Log: was das Ereignis an Commits mitbringt.
    Nur Zahlen, kein Inhalt."""
    commits = ereignis.get("commits") or []
    mit_liste = sum(1 for c in commits if any(k in c for k in ("added", "modified")))
    neu = set(str(ereignis.get("before") or "0")) == {"0"}
    return "ereignis: %d commits, %d mit dateiliste, %s" % (
        len(commits), mit_liste, "neuer branch" if neu else "branch gab es schon")


def _ist_bericht(f):
    return f.startswith("berichte/") and f.endswith(".md")


def berichte_aus_vergleich(ereignis, holer=None, git=None):
    """Rueckfall, wenn die Commits im Ereignis keinen Bericht nennen (leere
    Liste oder ohne Dateilisten, gesehen am 28.10.2026). Zuerst der Vergleich
    before...after ueber die oeffentliche GitHub-API, bei einem neuen Branch
    gegen den Standard-Branch. Geht das nicht, die Dateien des HEAD-Commits.
    Doppelten Versand verhindert weiter die Merkdatei."""
    import subprocess
    import urllib.request
    repo = (ereignis.get("repository") or {}).get("full_name", "")
    after = str(ereignis.get("after") or "")
    before = str(ereignis.get("before") or "")
    basis = (ereignis.get("repository") or {}).get("default_branch") or "main"
    if before and set(before) != {"0"}:
        basis = before
    if repo and re.fullmatch(r"[0-9a-f]{40}", after) and re.fullmatch(r"[A-Za-z0-9._/-]{1,100}", basis):
        url = "https://api.github.com/repos/%s/compare/%s...%s" % (repo, basis, after)

        def holen(u):
            req = urllib.request.Request(u, headers={"Accept": "application/vnd.github+json",
                                                     "User-Agent": "kaspa-pulse-bericht"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        try:
            d = (holer or holen)(url)
            dateien = [f["filename"] for f in d.get("files") or []
                       if f.get("status") in ("added", "modified", "renamed", "changed")
                       and _ist_bericht(f.get("filename", ""))]
            print("vergleich %s...%s, %d bericht(e)" % (basis[:12], after[:12], len(dateien)))
            return dateien
        except Exception as exc:  # noqa: BLE001
            print("vergleich ging nicht (%s), nehme den head-commit" % type(exc).__name__)

    def git_show():
        return subprocess.run(["git", "show", "--name-only", "--diff-filter=AMR", "--pretty=format:", "HEAD"],
                              capture_output=True, text=True).stdout
    dateien = [z.strip() for z in (git or git_show)().splitlines() if _ist_bericht(z.strip())]
    print("head-commit, %d bericht(e)" % len(dateien))
    return dateien


def lauf(datei, link, trocken, vorher=None):
    text = open(datei, encoding="utf-8").read()
    t = teile(text)
    if not t:
        print("kein discord-abschnitt in %s" % datei)
        return 0
    if vorher and os.path.exists(vorher) and teile(open(vorher, encoding="utf-8").read()) == t:
        print("discord-abschnitt unveraendert, nichts gesendet")
        return 0
    alle = nachrichten(datei, t, link)
    funde = pruefen(texte(alle))
    if funde:
        print("nicht gesendet: " + "; ".join(funde))
        return 2
    if trocken:
        n_hand = sum(1 for art, _ in alle if art == "hand")
        print("trocken, %d nachrichten nach #ops-log, %d nach #moderator-only, laengste %d zeichen"
              % (len(alle) - n_hand, n_hand, max(len(x) for x in texte(alle))))
        return 0
    return senden(alle)


def lauf_ereignis(ereignis_pfad, branch, merkdatei, link_basis, trocken, senden_fn=None):
    """Alle Berichte dieses Pushes, je Abschnitt hoechstens einmal. Ein
    gesendeter Abschnitt wird sofort in der Merkdatei vermerkt."""
    with open(ereignis_pfad, encoding="utf-8") as fh:
        ereignis = json.load(fh)
    m = merk_lesen(merkdatei)
    rc = 0
    print(lage(ereignis))
    dateien = geaenderte_berichte(ereignis)
    if not dateien:
        dateien = berichte_aus_vergleich(ereignis)
    if not dateien:
        print("keine berichte in den neuen commits dieses pushes")
    for f in dateien:
        print("== %s" % f)
        if not os.path.exists(f):
            print("datei fehlt im stand, uebersprungen")
            continue
        t = teile(open(f, encoding="utf-8").read())
        if not t:
            print("kein discord-abschnitt")
            continue
        summe = pruefsumme(t)
        alt = schon_gesendet(m, f, summe)
        if alt:
            print("abschnitt schon gesendet (%s, branch %s), nichts gesendet" % (alt["utc"], alt["branch"]))
            continue
        alle = nachrichten(f, t, link_basis.rstrip("/") + "/" + f if link_basis else "")
        funde = pruefen(texte(alle))
        if funde:
            print("nicht gesendet: " + "; ".join(funde))
            rc = 2
            continue
        if trocken:
            print("trocken, %d nachrichten (kopf plus %d), pruefsumme %s" % (len(alle), len(alle) - 1, summe[:12]))
            continue
        if senden_fn is None:
            ergebnis = senden(alle)
        else:
            ergebnis = senden_fn(alle)
        if ergebnis == 0:
            merken(m, branch, f, summe)
            merk_schreiben(merkdatei, m)
            print("gemerkt, pruefsumme %s" % summe[:12])
        else:
            rc = 1
    return rc


def selbsttest():
    fehler = []

    def ok(name, bed, ist=None):
        if not bed:
            fehler.append(name)
            print("FEHLER", name, ist)
    md = "# x\n%s\neins\n%s\nzwei\n%s\nrest" % (AUF, TEIL, ZU)
    ok("zwei teile", teile(md) == ["eins", "zwei"], teile(md))
    ok("ohne abschnitt leer", teile("# nur text") == [])
    ok("sauberer text ohne fund", pruefen(["see github.com/x and 18:03 to 18:14"]) == [])
    ok("eigene domain erlaubt", pruefen(["https://kaspapulse.com/whales?utm_source=ig&utm_medium=paid"]) == [],
       pruefen(["https://kaspapulse.com/whales?utm_source=ig"]))
    ok("unterdomain der eigenen domain gesperrt", any("hostname" in f for f in pruefen(["x." + "kaspapulse" + ".com"])))
    ok("fremde domain mit kaspapulse im namen gesperrt", any("hostname" in f for f in pruefen(["kaspapulse" + ".com.evil.io"])))
    # testwerte erst zur laufzeit zusammengesetzt, kein echter host und keine echte ip in der datei
    ip = ".".join(["192", "0", "2", "7"])
    host = "-".join(["knoten", "1"]) + "." + "beispiel" + ".blue"
    for bad, art in (("node " + ip, "ip"), ("kaspatest:" + "q" * 61, "adresse"), (host, "hostname"),
                     ("ghp" + "_abc", "schluessel")):
        ok("fund %s" % art, any(art in f for f in pruefen([bad])), pruefen([bad]))
    ok("zu lang", any("zeichen" in f for f in pruefen(["x" * 2000])))
    # kopfzeile zaehlt die nachrichten, die wirklich folgen, je kanal
    vh = ops_melden.VON_HAND + ": **x**"
    for n_info, n_hand in ((1, 0), (3, 1), (2, 5)):
        t = ["t%d" % i for i in range(n_info)] + [vh + str(i) for i in range(n_hand)]
        alle = nachrichten("berichte/a.md", t, "")
        z = re.search(r"(\d+) teile? hier, (\d+) handlung", alle[0][1])
        arten = [art for art, _ in alle[1:]]
        ok("kopf nennt %d und %d, es folgen %d und %d" % (n_info, n_hand, arten.count("log"), arten.count("hand")),
           (int(z.group(1)), int(z.group(2))) == (arten.count("log"), arten.count("hand")) == (n_info, n_hand), alle[0])
    ok("kopf geht nach log und traegt kein von hand",
       alle[0][0] == "log" and not alle[0][1].startswith(ops_melden.VON_HAND))
    info, hand = aufteilen(["ueberblick", vh, "noch info"])
    ok("von-hand-teile getrennt", info == ["ueberblick", "noch info"] and hand == [vh], (info, hand))
    ok("handlung traegt den link zum bericht", nachrichten("berichte/a.md", [vh], "https://github.com/x")[-1]
       == ("hand", vh + "\nBericht: https://github.com/x"))
    # versand ueber ops_melden, beide kanaele, ohne netz
    gesendet = []
    echt_post = ops_melden._post
    alt_env = {k: os.environ.get(k) for k in ops_melden.ARTEN.values()}
    ops_melden._post = lambda url, body, typ, timeout=60: gesendet.append(url.rsplit("/", 1)[1]) or 204
    basis = "https://discord.com/api/" + "webhooks/"
    try:
        os.environ["DISCORD_WEBHOOK_OPS"] = basis + "1/hand"
        os.environ["DISCORD_WEBHOOK_LOG"] = basis + "2/log"
        ok("senden in beide kanaele", senden(nachrichten("berichte/a.md", ["a", vh], ""), 0) == 0
           and gesendet == ["log", "log", "hand"], gesendet)
        del os.environ["DISCORD_WEBHOOK_LOG"]
        gesendet.clear()
        ok("ohne log-webhook info nur im job-log, handlung geht",
           senden(nachrichten("berichte/a.md", ["a", vh], ""), 0) == 0 and gesendet == ["hand"], gesendet)
        del os.environ["DISCORD_WEBHOOK_OPS"]
        ok("handlung ohne ops-webhook ist rot", senden(nachrichten("berichte/a.md", [vh], ""), 0) == 3)
    finally:
        ops_melden._post = echt_post
        for k, v in alt_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    # nur distinct commits, nur berichte/*.md, entfernte nicht
    ev = {"commits": [
        {"distinct": False, "added": ["berichte/eltern.md"], "modified": [], "removed": []},
        {"distinct": True, "added": ["berichte/neu.md", "scripts/x.py"], "modified": ["berichte/alt.md"], "removed": []},
        {"distinct": True, "added": [], "modified": ["berichte/neu.md"], "removed": ["berichte/alt.md"]}]}
    ok("nur berichte aus neuen commits", geaenderte_berichte(ev) == ["berichte/neu.md"], geaenderte_berichte(ev))
    ok("ohne commits nichts", geaenderte_berichte({"commits": []}) == [] and geaenderte_berichte({}) == [])
    # rueckfall ueber den vergleich, wenn die commits nichts nennen (28.10.2026)
    sha_a, sha_b = "a" * 40, "b" * 40
    urls = []

    def holer(u):
        urls.append(u)
        return {"files": [{"filename": "berichte/x.md", "status": "added"},
                          {"filename": "berichte/weg.md", "status": "removed"},
                          {"filename": "scripts/y.py", "status": "modified"}]}
    ev2 = {"before": "0" * 40, "after": sha_b, "commits": [],
           "repository": {"full_name": "o/r", "default_branch": "main"}}
    ok("lage nennt neuen branch ohne dateiliste", lage(ev2) == "ereignis: 0 commits, 0 mit dateiliste, neuer branch")
    ok("neuer branch vergleicht gegen main", berichte_aus_vergleich(ev2, holer) == ["berichte/x.md"]
       and urls[-1].endswith("/repos/o/r/compare/main..." + sha_b), urls)
    berichte_aus_vergleich(dict(ev2, before=sha_a), holer)
    ok("bestehender branch vergleicht before...after", urls[-1].endswith("/compare/%s...%s" % (sha_a, sha_b)))

    def kaputt_holer(u):
        raise OSError("kein netz")
    ok("ohne netz der head-commit", berichte_aus_vergleich(ev2, kaputt_holer,
       lambda: "\nberichte/h.md\nscripts/z.py\n") == ["berichte/h.md"])
    ok("komische werte gehen nicht in die adresse", berichte_aus_vergleich(dict(ev2, after="x y"), holer,
       lambda: "") == [] and len(urls) == 2)
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "a.md"), os.path.join(d, "b.md")
        open(a, "w").write(md)
        open(b, "w").write(md + "\nanderer rest")
        ok("unveraenderter abschnitt sendet nichts", lauf(b, "", False, a) == 0)
        # push mit bericht, dann force-push mit gleichem abschnitt, dann anderer branch, dann neuer inhalt
        alt_cwd = os.getcwd()
        os.chdir(d)
        try:
            os.makedirs("berichte")
            open("berichte/r.md", "w").write(md)
            evp, merk = os.path.join(d, "ev.json"), os.path.join(d, "gesendet.json")
            json.dump({"commits": [{"distinct": True, "added": ["berichte/r.md"], "modified": []}]}, open(evp, "w"))
            gesendet = []

            def fake(alle):
                gesendet.append(len(alle))
                return 0
            r1 = lauf_ereignis(evp, "bericht/x", merk, "", False, fake)
            r2 = lauf_ereignis(evp, "bericht/x", merk, "", False, fake)
            r3 = lauf_ereignis(evp, "bericht/y", merk, "", False, fake)
            ok("erster push sendet kopf plus 2", r1 == 0 and gesendet == [3], gesendet)
            ok("gleicher inhalt nie zweimal, auch nicht auf anderem branch", r2 == 0 and r3 == 0 and gesendet == [3],
               gesendet)
            open("berichte/r.md", "w").write(md.replace("zwei", "zwei neu"))
            lauf_ereignis(evp, "bericht/x", merk, "", False, fake)
            ok("neuer inhalt geht einmal raus", gesendet == [3, 3], gesendet)
            m = merk_lesen(merk)
            ok("merkdatei zwei eintraege mit pruefsumme", len(m["eintraege"]) == 2
               and all(len(e["sha256"]) == 64 for e in m["eintraege"]), m)

            def kaputt(alle):
                return 1
            open("berichte/r.md", "w").write(md.replace("eins", "eins neu"))
            ok("fehlgeschlagener versand wird nicht gemerkt", lauf_ereignis(evp, "bericht/x", merk, "", False, kaputt) == 1
               and len(merk_lesen(merk)["eintraege"]) == 2)
            v = vereinen({"eintraege": [{"branch": "a", "datei": "d", "sha256": "1"}]},
                         {"eintraege": [{"branch": "a", "datei": "d", "sha256": "1"},
                                        {"branch": "b", "datei": "d", "sha256": "2"}]})
            ok("vereinen ohne doppelte", len(v["eintraege"]) == 2)
            ok("echte merkdatei gueltig", merk_pruefen(merk_lesen(merk)) == [], merk_pruefen(merk_lesen(merk)))
            ok("fremder schluessel ungueltig", merk_pruefen({"eintraege": [], "x": 1}) != [])
            gut = {"branch": "bericht/x", "datei": "berichte/r.md", "sha256": "a" * 64, "utc": "2026-10-26"}
            for feld, wert in (("datei", "scripts/x.py"), ("sha256", "nein"), ("branch", "a b"), ("utc", "gestern")):
                ok("ungueltig: %s" % feld, merk_pruefen({"eintraege": [dict(gut, **{feld: wert})]}) != [])
            ok("ungueltig: hinweis mit ip", merk_pruefen({"eintraege": [dict(gut, hinweis="node " + ip)]}) != [])
            ok("ungueltig: zusatzfeld", merk_pruefen({"eintraege": [dict(gut, webhook="x")]}) != [])
        finally:
            os.chdir(alt_cwd)
    print("%d fehler" % len(fehler))
    return 1 if fehler else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datei")
    ap.add_argument("--link", default="")
    ap.add_argument("--trocken", action="store_true")
    ap.add_argument("--vorher", help="stand der datei vor dem push; gleicher abschnitt wird nicht erneut gesendet")
    ap.add_argument("--ereignis", help="push-ereignis (GITHUB_EVENT_PATH)")
    ap.add_argument("--branch", default="")
    ap.add_argument("--merkdatei", default="gesendet.json")
    ap.add_argument("--link-basis", default="")
    ap.add_argument("--vereinen", nargs=2, metavar=("A", "B"))
    ap.add_argument("--merk-pruefen", metavar="DATEI", help="merkdatei pruefen, rc 1 bei einem fehler")
    ap.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args()
    if a.selbsttest:
        return selbsttest()
    if a.merk_pruefen or a.vereinen:
        for pfad in ([a.merk_pruefen] if a.merk_pruefen else a.vereinen):
            f = merk_pruefen(merk_lesen(pfad))
            if f:
                print("merkdatei %s ungueltig: %s" % (os.path.basename(pfad), "; ".join(f)))
                return 1
        if a.merk_pruefen:
            print("merkdatei gueltig")
            return 0
        merk_schreiben(a.vereinen[0], vereinen(merk_lesen(a.vereinen[0]), merk_lesen(a.vereinen[1])))
        return 0
    if a.ereignis:
        return lauf_ereignis(a.ereignis, a.branch, a.merkdatei, a.link_basis, a.trocken)
    return lauf(a.datei, a.link, a.trocken, a.vorher)


if __name__ == "__main__":
    sys.exit(main())
