#!/usr/bin/env python3
"""karussell_post.py, Karussell und Meme automatisch auf Instagram (Ben, 25.10.2026).

Bis zum 24.10.2026 baute karussell.yml nur Entwuerfe nach #moderator-only,
gepostet hat sie niemand. Ab jetzt laeuft jeder Termin in zwei Schritten:

  entwurf   2 Stunden vor dem Post. Baut die Seiten im Look aus dem
            gemeinsamen Instagram-Raster (data/look-takt.json), prueft Texte
            und Caption, schickt Bilder und Caption nach #moderator-only mit
            dem Satz "geht um HH:MM raus, Veto: karussell-stopp" und legt
            alles als Artefakt ab (karussell-entwurf-<art>-<datum>), mit
            einer Pruefsumme je Bild.
  posten    zum Postzeitpunkt. Holt GENAU die Bilder aus dem Entwurf (nichts
            wird neu gebaut, das Meme misst sonst eine andere Blockrate),
            macht JPEGs daraus, legt sie kurz als Release-Anhang in
            neoalphavault-png/kaspapulse-media ab (wie die Reels), legt die
            Container an (Karussell bis 10 Seiten, Einzelbild fuer eine
            Seite) und veroeffentlicht nur, wenn alles gruen ist. Danach
            sind die Anhaenge wieder weg, auch wenn vorher etwas scheitert.
  probe     beides in einem Lauf, nie veroeffentlicht, nichts gemerkt. Der
            Vorschau-Lauf, nach dem Ben KARUSSELL_LIVE setzt.

TERMINE (karussell.POSTZEIT): woche Sa 11:00, story Mi 18:00, meme Sa 15:00,
Entwurf jeweils 2 Stunden vorher. Der Takt kommt von c2.

SCHARF nur, wenn alles zusammenkommt:
  - der Lauf kommt vom Takt (--start takt). Von Hand ist immer trocken.
  - die Variable KARUSSELL_LIVE steht auf true (auch ja, yes, 1).
  - kein Stopp: KARUSSELL_STOPP steht weder auf dem Postdatum noch auf
    "immer" (Notbremse wie IG_STOPP bei der Tagesgrafik).
  - der Takt liegt im Fenster, 15 Minuten vor bis 90 Minuten nach der
    Postzeit, und das Postdatum ist heute in Berlin.
  - dieser Termin ist noch nicht gepostet (data/karussell-log.json).
Trocken heisst: Container anlegen und pruefen, nicht veroeffentlichen.

MEME. Ein Motiv geht nur einmal raus. Ist das Motiv aus meme_wahr.MOTIV schon
gepostet, kommt kein Entwurf, nur eine Zeile nach #moderator-only, dass ein
neues Motiv fehlt. Kein Meme ist besser als dasselbe Meme jede Woche.

GEHEIMNISSE nur aus der Umgebung: INSTAGRAM_PAGE_TOKEN, MEDIA_REPO_TOKEN,
DISCORD_WEBHOOK_OPS, GITHUB_TOKEN. Jede Ausgabe laeuft durch sauber().

    python3 scripts/karussell_post.py entwurf --art woche [--fuer 2026-10-31] --out out/k [--probe]
    python3 scripts/karussell_post.py posten --art woche [--fuer 2026-10-31] [--quelle out/k] --start takt
    python3 scripts/karussell_post.py --selbsttest
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

LOG = REPO / "data" / "karussell-log.json"
MEDIA_REPO = "neoalphavault-png/kaspapulse-media"
MEDIA_BRANCH = "main"
ABLAGE_TAG = "karussell-ablage"
UPLOADS = "https://uploads.github.com"
VORLAUF = dt.timedelta(hours=2)
FENSTER = (dt.timedelta(minutes=-15), dt.timedelta(minutes=90))
MAX_SEITEN = 10
ARTEN = ("woche", "story", "meme")
UA = "kaspa-pulse-karussell"
# Zweite Ablage (Ben, 28.10.2026): ohne MEDIA_REPO_TOKEN legt der Lauf die
# JPEGs mit GITHUB_TOKEN unter ig/karussell/ in dieses Repo, wie die Story und
# die Tagesgrafik unter ig/. kaspapulse.com liefert sie dann aus. Sie bleiben
# liegen, wie alle Bilder unter ig/. Geht nur vom Branch main, nur den baut
# GitHub Pages.
SEITE = "https://kaspapulse.com"
SEITEN_ORDNER = "ig/karussell"


class Stopp(Exception):
    """Ein Grund, nicht weiterzumachen. Der Text nennt ihn."""


class NichtFaellig(Exception):
    """Kein Fehler, nur nicht dran (Stopp gesetzt, schon gepostet, kein Motiv)."""


# ------------------------------------------------------------ helfer

def ig():
    import instagram
    return instagram


def sauber(text):
    t = ig().sauber(text)
    w = os.environ.get("MEDIA_REPO_TOKEN", "")
    return t.replace(w, "***") if len(w) >= 8 else t


def sag(*teile):
    print(sauber(" ".join(str(t) for t in teile)))


def berlin_jetzt(now=None):
    return ig().berlin(now or dt.datetime.now(dt.timezone.utc))


def heute(now=None):
    return berlin_jetzt(now).date().isoformat()


def postzeit(art, fuer):
    """Die Postzeit als Berlin-Zeitpunkt (mit Zone)."""
    import karussell
    hh, mm = map(int, karussell.POSTZEIT[art][1].split(":"))
    from zoneinfo import ZoneInfo
    return dt.datetime.combine(dt.date.fromisoformat(fuer), dt.time(hh, mm), ZoneInfo("Europe/Berlin"))


def termin_pruefen(art, fuer):
    import karussell
    tag = karussell.POSTZEIT[art][0]
    if dt.date.fromisoformat(fuer).weekday() != tag:
        raise Stopp("%s postet am %s, der %s ist ein anderer wochentag"
                    % (art, ("montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag",
                             "sonntag")[tag], fuer))


def stopp_gesetzt(fuer):
    s = os.environ.get("KARUSSELL_STOPP", "").strip().lower()
    return s in (fuer, "immer")


def live():
    return os.environ.get("KARUSSELL_LIVE", "").strip().lower() in ("true", "ja", "yes", "1")


def sha(pfad):
    return hashlib.sha256(Path(pfad).read_bytes()).hexdigest()


def log_lesen(pfad=None):
    return ig().json_laden(pfad or LOG, {"posts": []})


def schon_gepostet(log, art, fuer=None, motiv=None):
    for p in log.get("posts", []):
        if p.get("modus") != "scharf" or not p.get("media"):
            continue
        if fuer and p.get("art") == art and p.get("fuer") == fuer:
            return p
        if motiv and p.get("motiv") == motiv:
            return p
    return None


def faellig(art, fuer, start, log, now=None):
    """None, wenn dran, sonst der Grund. Von Hand gibt es kein Fenster."""
    if stopp_gesetzt(fuer):
        return "KARUSSELL_STOPP steht auf %s" % os.environ.get("KARUSSELL_STOPP", "").strip()
    p = schon_gepostet(log, art, fuer=fuer)
    if p:
        return "%s fuer %s ist schon gepostet (%s)" % (art, fuer, p.get("permalink") or p.get("media"))
    if start == "hand":
        return None
    jetzt = berlin_jetzt(now)
    if jetzt.date().isoformat() != fuer:
        return "postdatum %s ist nicht heute (%s)" % (fuer, jetzt.date().isoformat())
    pz = postzeit(art, fuer)
    if not pz + FENSTER[0] <= jetzt <= pz + FENSTER[1]:
        return "%s berlin liegt nicht im fenster um %s" % (jetzt.strftime("%H:%M"), pz.strftime("%H:%M"))
    return None


def fuer_aufloesen(art, fuer, now=None):
    """Ohne Datum: der Termin dieser Art heute oder der naechste."""
    if fuer:
        return fuer
    import karussell
    d = berlin_jetzt(now).date()
    while d.weekday() != karussell.POSTZEIT[art][0]:
        d += dt.timedelta(days=1)
    return d.isoformat()


# ------------------------------------------------------------ entwurf

def bauen(art, fuer, out, look, motiv=None):
    """(seiten-texte, caption, bilder, motiv) im Look aus dem Raster."""
    import karussell
    if art == "meme":
        import meme_wahr
        ss, cap, bilder = meme_wahr.bauen(fuer, out, "messung", (look,), motiv)
        fehler = meme_wahr.pruefen(ss, cap) + karussell.caption_pruefen(cap) + karussell.deckblatt_pruefen(ss)
        motiv = meme_wahr.MOTIV
    else:
        ss, cap = karussell.vorbereiten(art, fuer)
        bilder = karussell.rendern(art, fuer, ss, (look,), out, motiv)
        fehler = karussell.deckblatt_pruefen(ss)
        motiv = ""
    if fehler:
        raise Stopp("wache, %s" % "; ".join(fehler))
    if not 1 <= len(bilder) <= MAX_SEITEN:
        raise Stopp("%d seiten, instagram nimmt 1 bis %d" % (len(bilder), MAX_SEITEN))
    return ss, cap, bilder, motiv


def entwurf(art, fuer, out, probe=False, log_pfad=None, speicher_pfad=None, senden=True):
    """Baut den Entwurf, legt das Manifest ab und schickt ihn nach ops.
    Gibt das Manifest zurueck, oder None, wenn nichts dran ist."""
    import karussell
    import look_takt
    termin_pruefen(art, fuer)
    log = log_lesen(log_pfad)
    if art == "meme":
        import meme_wahr
        alt = schon_gepostet(log, "meme", motiv=meme_wahr.MOTIV)
        if alt:
            raise NichtFaellig("meme, but true: das motiv %s ging am %s raus, ein neues fehlt. "
                               "sa %s bleibt ohne meme." % (meme_wahr.MOTIV, alt.get("fuer"),
                                                            karussell.POSTZEIT["meme"][1]))
    sp = look_takt.lesen(speicher_pfad)
    serie = "meme" if art == "meme" else "karussell"
    look = look_takt.raster_faellig(sp, serie, fuer)[1]
    import hintergrund
    motiv = look_takt.raster_motiv(sp, serie, fuer) if hintergrund.aktiv(fuer) else None
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ss, cap, bilder, motiv_meme = bauen(art, fuer, out, look, motiv)
    m = {"art": art, "fuer": fuer, "postzeit": postzeit(art, fuer).isoformat(), "look": look,
         "caption": cap, "motiv": motiv_meme, "hintergrund": motiv, "probe": probe,
         "bilder": [{"datei": Path(b).name, "sha256": sha(b)} for b in bilder]}
    (out / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sag("entwurf %s fuer %s, look %s, %d seiten" % (art, fuer, look, len(bilder)))
    if senden:
        hook = os.environ.get("DISCORD_WEBHOOK_OPS", "")
        if not hook:
            raise Stopp("kein DISCORD_WEBHOOK_OPS, entwurf nicht geschickt")
        vor = "PROBE, geht nicht raus. " if probe else ""
        if stopp_gesetzt(fuer):
            vor += "STOPP GESETZT (KARUSSELL_STOPP), geht nicht raus. "
        karussell.ops_senden(hook, art, fuer, look, bilder, cap, vor=vor)
    if not probe:
        look_takt.raster_merken(sp, serie, fuer)
        look_takt.schreiben(sp, speicher_pfad)
    return m


# ------------------------------------------------------------ artefakt

def artefakt_holen(art, fuer, ziel):
    """Das Artefakt des Entwurfs aus einem Lauf von karussell.yml."""
    import io
    import zipfile
    name = "karussell-entwurf-%s-%s" % (art, fuer)
    tag0 = (dt.date.fromisoformat(fuer) - dt.timedelta(days=1)).isoformat()
    runs = ig().gh("actions/workflows/karussell.yml/runs?per_page=30&created=%%3E%%3D%s" % tag0)
    for run in runs.get("workflow_runs", []):
        for a in ig().gh("actions/runs/%d/artifacts" % run["id"]).get("artifacts", []):
            if a.get("name") != name or a.get("expired"):
                continue
            z = zipfile.ZipFile(io.BytesIO(ig().gh("actions/artifacts/%d/zip" % a["id"], roh=True)))
            Path(ziel).mkdir(parents=True, exist_ok=True)
            for n in z.namelist():
                if n.endswith((".png", "manifest.json")):
                    (Path(ziel) / Path(n).name).write_bytes(z.read(n))
            if (Path(ziel) / "manifest.json").exists():
                sag("entwurf aus lauf %d" % run["id"])
                return Path(ziel)
    raise Stopp("kein artefakt %s gefunden, ohne entwurf geht nichts raus" % name)


def manifest_lesen(quelle, art, fuer):
    q = Path(quelle)
    m = json.loads((q / "manifest.json").read_text(encoding="utf-8"))
    if (m.get("art"), m.get("fuer")) != (art, fuer):
        raise Stopp("der entwurf ist %s fuer %s, nicht %s fuer %s" % (m.get("art"), m.get("fuer"), art, fuer))
    bilder = []
    for b in m["bilder"]:
        p = q / b["datei"]
        if not p.exists() or sha(p) != b["sha256"]:
            raise Stopp("bild %s fehlt oder weicht vom entwurf ab" % b["datei"])
        bilder.append(p)
    import karussell
    fehler = karussell.caption_pruefen(m["caption"])
    if fehler:
        raise Stopp("caption nicht gruen, %s" % "; ".join(fehler))
    if not 1 <= len(bilder) <= MAX_SEITEN:
        raise Stopp("%d seiten, instagram nimmt 1 bis %d" % (len(bilder), MAX_SEITEN))
    return m, bilder


# ------------------------------------------------------------ ablage

def media_token():
    t = os.environ.get("MEDIA_REPO_TOKEN", "")
    if not t:
        raise Stopp("kein MEDIA_REPO_TOKEN, die bilder haben keinen oeffentlichen ort")
    return t


def gh_media(methode, pfad, rumpf=None, daten=None, typ=None, basis="https://api.github.com"):
    kopf = {"Authorization": "Bearer " + media_token(), "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": UA}
    body = None
    if rumpf is not None:
        body = json.dumps(rumpf).encode()
        kopf["Content-Type"] = "application/json"
    if daten is not None:
        body = daten
        kopf["Content-Type"] = typ or "application/octet-stream"
    status, roh, _ = ig().http(methode, basis + pfad, None, kopf, timeout=120) if body is None else \
        _roh(methode, basis + pfad, body, kopf)
    if status >= 400:
        raise Stopp(sauber("github %s %s, http %s" % (methode, pfad.split("?")[0], status)))
    return json.loads(roh.decode("utf-8")) if roh else {}


def _roh(methode, url, body, kopf):
    req = urllib.request.Request(url, data=body, headers=kopf, method=methode)
    try:
        with ig()._oeffnen(req, timeout=300) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, b"", {}


def ablage_id():
    try:
        return gh_media("GET", "/repos/%s/releases/tags/%s" % (MEDIA_REPO, ABLAGE_TAG))["id"]
    except Stopp as exc:
        if "http 404" not in str(exc):
            raise
    sag("lege die ablage an:", ABLAGE_TAG)
    return gh_media("POST", "/repos/%s/releases" % MEDIA_REPO, {
        "tag_name": ABLAGE_TAG, "name": "Karussell-Ablage", "target_commitish": MEDIA_BRANCH,
        "prerelease": True, "body": "Zwischenablage fuer Karussell und Meme. Jede Datei liegt hier nur "
                                    "die Minuten, die Instagram zum Abholen braucht."})["id"]


def hochladen(jpeg, rid):
    name = "%s-%s.jpg" % (Path(jpeg).stem, uuid.uuid4().hex[:8])
    a = gh_media("POST", "/repos/%s/releases/%d/assets?%s" % (MEDIA_REPO, rid, urllib.parse.urlencode(
        {"name": name})), daten=Path(jpeg).read_bytes(), typ="image/jpeg", basis=UPLOADS)
    if not a.get("browser_download_url"):
        raise Stopp("anhang %s ohne browser_download_url" % name)
    return a["id"], a["browser_download_url"]


def seiten_ablage(jpegs, frist=600, takt=15):
    """Committet die JPEGs ueber die GitHub-API nach ig/karussell/ auf main und
    wartet, bis kaspapulse.com jedes mit genau seiner Laenge ausliefert."""
    import base64
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    gt = os.environ.get("GITHUB_TOKEN", "")
    zweig = os.environ.get("GITHUB_REF_NAME", "main")
    if not repo or not gt:
        raise Stopp("weder MEDIA_REPO_TOKEN noch GITHUB_TOKEN, die bilder haben keinen oeffentlichen ort")
    if zweig != "main":
        raise Stopp("ablage unter ig/ nur vom branch main, nicht von %s" % zweig)
    kopf = {"Authorization": "Bearer " + gt, "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": UA, "Content-Type": "application/json"}
    urls = []
    for j in jpegs:
        name = "%s-%s.jpg" % (Path(j).stem, uuid.uuid4().hex[:8])
        pfad = "%s/%s" % (SEITEN_ORDNER, name)
        body = json.dumps({"message": "karussell ablage %s [bot]" % name, "branch": "main",
                           "content": base64.b64encode(Path(j).read_bytes()).decode()}).encode()
        status, _, _ = _roh("PUT", "https://api.github.com/repos/%s/contents/%s" % (repo, pfad), body, kopf)
        if status not in (200, 201):
            raise Stopp(sauber("ablage %s, github http %s" % (pfad, status)))
        sag("abgelegt", pfad)
        urls.append((SEITE + "/" + pfad, Path(j).stat().st_size))
    for url, laenge in urls:
        try:
            ig().url_warten(url, laenge, frist=frist, takt=takt)
        except Exception as exc:                      # noqa: BLE001
            raise Stopp(sauber(str(exc)))
    return [u for u, _ in urls]


def abholbar(url, soll):
    """GET mit einem Byte, wie bei den Reels. Instagram holt die Datei selbst."""
    req = urllib.request.Request(url, headers={"Range": "bytes=0-0", "User-Agent": UA})
    try:
        with ig()._oeffnen(req, timeout=60) as r:
            bereich = r.headers.get("Content-Range") or ""
            r.read(1)
    except Exception as exc:                          # noqa: BLE001
        raise Stopp(sauber("ablage %s nicht abholbar, %s" % (url, exc)))
    gesamt = bereich.rsplit("/", 1)[-1]
    if gesamt.isdigit() and int(gesamt) != soll:
        raise Stopp("ablage %s hat %s bytes, die datei %d" % (url, gesamt, soll))


def entfernen(ids):
    for i in ids:
        try:
            gh_media("DELETE", "/repos/%s/releases/assets/%d" % (MEDIA_REPO, i))
            sag("anhang %d entfernt" % i)
        except Exception as exc:                      # noqa: BLE001
            sag("anhang %d nicht entfernt, %s" % (i, exc))


# ------------------------------------------------------------ graph

def warten(cid, takt=5, frist=300):
    ende, status = time.time() + frist, ""
    while time.time() < ende:
        status = ig().graph("GET", cid, {"fields": "status_code"}).get("status_code", "")
        if status in ("FINISHED", "ERROR", "EXPIRED", "PUBLISHED"):
            break
        time.sleep(takt)
    if status != "FINISHED":
        raise Stopp("container %s endet mit status %s" % (cid, status or "-"))
    return status


def container(urls, caption, takt=5):
    """Ein Einzelbild oder ein Karussell. Gibt die id des Containers zurueck."""
    u = ig().ig_user()
    if len(urls) == 1:
        cid = str(ig().graph("POST", "%s/media" % u, {"image_url": urls[0], "caption": caption}).get("id", ""))
    else:
        kinder = []
        for url in urls:
            k = str(ig().graph("POST", "%s/media" % u, {"image_url": url, "is_carousel_item": "true"}).get("id", ""))
            if not re.fullmatch(r"\d+", k):
                raise Stopp("seite ohne container-id")
            warten(k, takt)
            kinder.append(k)
        cid = str(ig().graph("POST", "%s/media" % u, {"media_type": "CAROUSEL", "children": ",".join(kinder),
                                                      "caption": caption}).get("id", ""))
    if not re.fullmatch(r"\d+", cid):
        raise Stopp("container ohne id")
    warten(cid, takt)
    return cid


def veroeffentlichen(cid):
    u = ig().ig_user()
    media = str(ig().graph("POST", "%s/media_publish" % u, {"creation_id": cid}).get("id", ""))
    try:
        link = ig().graph("GET", media, {"fields": "permalink"}).get("permalink", "")
    except Exception as exc:                          # noqa: BLE001
        sag("permalink nicht gelesen, %s" % exc)
        link = ""
    return media, link


# ------------------------------------------------------------ posten

def posten(art, fuer, quelle=None, start="hand", probe=False, log_pfad=None, now=None, takt=5):
    """Holt den Entwurf und postet ihn, scharf nur wenn alles stimmt.
    Gibt den Log-Eintrag zurueck."""
    termin_pruefen(art, fuer)
    log = log_lesen(log_pfad)
    grund = faellig(art, fuer, start, log, now)
    if grund:
        raise NichtFaellig(grund)
    if quelle is None:
        quelle = artefakt_holen(art, fuer, tempfile.mkdtemp(prefix="karussell-"))
    m, bilder = manifest_lesen(quelle, art, fuer)
    import look_takt
    scharf = start == "takt" and live() and not probe and not look_takt.trockenlauf()
    sag("%s fuer %s, %d seiten, %s" % (art, fuer, len(bilder), "SCHARF" if scharf else "trocken"))
    jpegs = [ig().jpeg(b, Path(quelle) / "jpg") for b in bilder]
    ids, urls = [], []
    eintrag = {"art": art, "fuer": fuer, "modus": "scharf" if scharf else "trocken", "start": start,
               "seiten": len(bilder), "look": m["look"], "motiv": m.get("motiv", ""),
               "caption_sha": hashlib.sha256(m["caption"].encode()).hexdigest()[:12]}
    try:
        if os.environ.get("MEDIA_REPO_TOKEN"):
            rid = ablage_id()
            for j in jpegs:
                i, url = hochladen(j, rid)
                ids.append(i)
                abholbar(url, Path(j).stat().st_size)
                urls.append(url)
        else:
            urls = seiten_ablage(jpegs)
            eintrag["ablage"] = "ig"
        cid = container(urls, m["caption"], takt)
        eintrag.update(container=cid, status="FINISHED")
        if scharf:
            media, link = veroeffentlichen(cid)
            eintrag.update(media=media, permalink=link)
            sag("veroeffentlicht", media, link)
        else:
            sag("trocken, container %s bleibt unveroeffentlicht" % cid)
    finally:
        entfernen(ids)
    eintrag["zeit_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    if not probe:
        log.setdefault("posts", []).append(eintrag)
        ig().json_schreiben(log_pfad or LOG, log)
    return eintrag


# ------------------------------------------------------------ selbsttest

def selbsttest():
    import karussell
    import instagram
    fehler = 0

    def ok(name, bed):
        nonlocal fehler
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        fehler += 0 if bed else 1

    tmp = Path(tempfile.mkdtemp(prefix="kpost-"))
    os.environ.pop("KARUSSELL_STOPP", None)
    os.environ.pop("KARUSSELL_LIVE", None)
    utc = dt.timezone.utc
    sa_1100 = dt.datetime(2026, 10, 31, 10, 0, tzinfo=utc)       # 11:00 berlin, winterzeit
    ok("postzeiten woche sa 11:00, story mi 18:00, meme sa 15:00",
       karussell.POSTZEIT == {"woche": (5, "11:00"), "story": (2, "18:00"), "meme": (5, "15:00")})
    ok("woche sa 31.10. 11:00 berlin ist 10:00 utc", postzeit("woche", "2026-10-31").astimezone(utc) == sa_1100)
    ok("entwurf 2 stunden vorher", VORLAUF == dt.timedelta(hours=2))
    leer = {"posts": []}
    ok("im fenster faellig", faellig("woche", "2026-10-31", "takt", leer, sa_1100) is None)
    ok("zu frueh nicht faellig", "fenster" in (faellig("woche", "2026-10-31", "takt", leer,
                                                     sa_1100 - dt.timedelta(minutes=30)) or ""))
    ok("zwei stunden zu spaet nicht faellig", "fenster" in (faellig("woche", "2026-10-31", "takt", leer,
                                                                  sa_1100 + dt.timedelta(hours=2)) or ""))
    ok("anderer tag nicht faellig", "nicht heute" in (faellig("woche", "2026-10-31", "takt", leer,
                                                            sa_1100 - dt.timedelta(days=1)) or ""))
    ok("von hand ohne fenster", faellig("woche", "2026-10-31", "hand", leer, sa_1100 - dt.timedelta(days=3)) is None)
    os.environ["KARUSSELL_STOPP"] = "2026-10-31"
    ok("stopp mit datum greift", "STOPP" in (faellig("woche", "2026-10-31", "takt", leer, sa_1100) or ""))
    os.environ["KARUSSELL_STOPP"] = "immer"
    ok("stopp immer greift, auch von hand", bool(faellig("woche", "2026-10-31", "hand", leer, sa_1100)))
    os.environ["KARUSSELL_STOPP"] = "2026-10-24"
    ok("stopp fuer einen anderen tag greift nicht", faellig("woche", "2026-10-31", "takt", leer, sa_1100) is None)
    os.environ.pop("KARUSSELL_STOPP")
    gepostet = {"posts": [{"art": "woche", "fuer": "2026-10-31", "modus": "scharf", "media": "1", "permalink": "p"},
                          {"art": "meme", "fuer": "2026-10-31", "modus": "scharf", "media": "2",
                           "motiv": "kaspa-chemie"},
                          {"art": "story", "fuer": "2026-11-04", "modus": "trocken"}]}
    ok("schon gepostet nicht noch einmal", "schon gepostet" in (faellig("woche", "2026-10-31", "takt",
                                                                       gepostet, sa_1100) or ""))
    ok("ein trockener eintrag sperrt nicht", schon_gepostet(gepostet, "story", fuer="2026-11-04") is None)
    ok("ein meme-motiv nur einmal", schon_gepostet(gepostet, "meme", motiv="kaspa-chemie") is not None)
    for wert, soll in (("true", True), ("JA", True), ("1", True), ("false", False), ("", False), ("scharf", False)):
        os.environ["KARUSSELL_LIVE"] = wert
        ok("KARUSSELL_LIVE=%r ist %s" % (wert, "scharf" if soll else "trocken"), live() is soll)
    os.environ.pop("KARUSSELL_LIVE")
    try:
        termin_pruefen("woche", "2026-10-30")
        ok("woche an einem freitag stoppt", False)
    except Stopp:
        ok("woche an einem freitag stoppt", True)
    ok("ohne datum der naechste samstag", fuer_aufloesen("meme", "", dt.datetime(2026, 10, 25, 12, tzinfo=utc))
       == "2026-10-31")
    ok("am posttag selbst heute", fuer_aufloesen("woche", "", sa_1100) == "2026-10-31")
    os.environ["MEDIA_REPO_TOKEN"] = "ghp_" + "x" * 30
    ok("sauber verbirgt den media-token", "ghp_" not in sauber("fehler bei " + os.environ["MEDIA_REPO_TOKEN"]))

    # ein ganzer posten-lauf gegen eine nachgebaute api: drei seiten werden
    # ein karussell, eine seite ein einzelbild, trocken wird nie veroeffentlicht,
    # die anhaenge sind danach weg, auch wenn graph scheitert
    from PIL import Image
    quelle = tmp / "entwurf"
    quelle.mkdir()
    bilder = []
    for i in range(3):
        p = quelle / ("karussell-woche-2026-10-31-%d-hell.png" % (i + 1))
        Image.new("RGB", (1080, 1350), (238, 243, 241)).save(p)
        bilder.append(p)
    ss = karussell.seiten_woche(*reversed(json.loads((REPO / "data" / "weekly-history.json")
                                                     .read_text(encoding="utf-8"))[-2:]))
    cap = karussell.caption_woche(ss)
    (quelle / "manifest.json").write_text(json.dumps({
        "art": "woche", "fuer": "2026-10-31", "look": "hell", "caption": cap, "motiv": "",
        "bilder": [{"datei": b.name, "sha256": sha(b)} for b in bilder]}), encoding="utf-8")
    aufrufe = []
    zustand = {"asset": 0, "geloescht": [], "graph_kaputt": False}

    def gh_falsch(methode, pfad, rumpf=None, daten=None, typ=None, basis=""):
        aufrufe.append(("gh", methode, pfad))
        if methode == "GET" and "/releases/tags/" in pfad:
            return {"id": 7}
        if methode == "POST" and "/assets?" in pfad:
            zustand["asset"] += 1
            return {"id": zustand["asset"], "browser_download_url": "https://ablage/%d.jpg" % zustand["asset"]}
        if methode == "DELETE":
            zustand["geloescht"].append(int(pfad.rsplit("/", 1)[1]))
            return {}
        return {}

    def graph_falsch(methode, pfad, params=None, versuche=3):
        aufrufe.append(("graph", methode, pfad, dict(params or {})))
        if zustand["graph_kaputt"] and methode == "POST":
            raise Stopp("graph kaputt")
        if methode == "POST" and pfad.endswith("/media"):
            return {"id": str(100 + len(aufrufe))}
        if methode == "POST" and pfad.endswith("/media_publish"):
            return {"id": "999"}
        if "permalink" in (params or {}).get("fields", ""):
            return {"permalink": "https://www.instagram.com/p/x/"}
        return {"status_code": "FINISHED"}

    alt = (globals()["gh_media"], globals()["abholbar"], instagram.graph)
    globals()["gh_media"], globals()["abholbar"] = gh_falsch, lambda url, soll: True
    instagram.graph = graph_falsch
    os.environ["IG_USER_ID"] = "17841400000000000"
    try:
        logp = tmp / "log.json"
        e = posten("woche", "2026-10-31", quelle=quelle, start="hand", log_pfad=logp, takt=0)
        g = [a for a in aufrufe if a[0] == "graph"]
        kinder = [a for a in g if a[3].get("is_carousel_item") == "true"]
        haupt = [a for a in g if a[3].get("media_type") == "CAROUSEL"]
        ok("drei seiten werden drei kinder und ein karussell-container", len(kinder) == 3 and len(haupt) == 1
           and len(haupt[0][3]["children"].split(",")) == 3)
        ok("die caption haengt am karussell, nicht an den seiten",
           haupt[0][3]["caption"] == cap and not any("caption" in a[3] for a in kinder))
        ok("von hand trocken, kein media_publish", e["modus"] == "trocken"
           and not any(a[2].endswith("media_publish") for a in g))
        ok("alle anhaenge danach entfernt", sorted(zustand["geloescht"]) == [1, 2, 3])
        ok("trockener lauf steht im log", log_lesen(logp)["posts"][-1]["modus"] == "trocken")
        # vom takt, live, im fenster: veroeffentlicht
        os.environ["KARUSSELL_LIVE"] = "true"
        aufrufe.clear()
        e = posten("woche", "2026-10-31", quelle=quelle, start="takt", log_pfad=logp, now=sa_1100, takt=0)
        ok("takt plus KARUSSELL_LIVE veroeffentlicht", e["modus"] == "scharf" and e["media"] == "999"
           and any(a[0] == "graph" and a[2].endswith("media_publish") for a in aufrufe))
        try:
            posten("woche", "2026-10-31", quelle=quelle, start="takt", log_pfad=logp, now=sa_1100, takt=0)
            ok("zweiter lauf am selben termin postet nicht", False)
        except NichtFaellig:
            ok("zweiter lauf am selben termin postet nicht", True)
        # probe: nie scharf, nichts im log
        logp2 = tmp / "log2.json"
        e = posten("woche", "2026-10-31", quelle=quelle, start="takt", probe=True, log_pfad=logp2,
                   now=sa_1100, takt=0)
        ok("probe ist nie scharf und schreibt kein log", e["modus"] == "trocken" and not logp2.exists())
        os.environ.pop("KARUSSELL_LIVE")
        # eine seite: einzelbild
        einzel = tmp / "einzel"
        einzel.mkdir()
        b1 = einzel / "meme-wahr-2026-10-31-1-hell.png"
        Image.new("RGB", (1080, 1350), (8, 11, 15)).save(b1)
        import meme_wahr
        mcap = meme_wahr.caption(meme_wahr.seiten("2026-10-31"))
        (einzel / "manifest.json").write_text(json.dumps({
            "art": "meme", "fuer": "2026-10-31", "look": "hell", "caption": mcap, "motiv": "kaspa-chemie",
            "bilder": [{"datei": b1.name, "sha256": sha(b1)}]}), encoding="utf-8")
        aufrufe.clear()
        posten("meme", "2026-10-31", quelle=einzel, start="hand", log_pfad=tmp / "log3.json", takt=0)
        g = [a for a in aufrufe if a[0] == "graph" and a[1] == "POST"]
        ok("eine seite wird ein einzelbild mit caption", len(g) == 1 and g[0][3].get("caption") == mcap
           and "media_type" not in g[0][3])
        # graph scheitert: anhaenge trotzdem weg
        zustand["geloescht"].clear()
        zustand["graph_kaputt"] = True
        try:
            posten("woche", "2026-10-31", quelle=quelle, start="hand", log_pfad=tmp / "log4.json", takt=0)
            ok("graph-fehler stoppt", False)
        except Stopp:
            ok("graph-fehler stoppt, anhaenge trotzdem entfernt", len(zustand["geloescht"]) == 3)
        zustand["graph_kaputt"] = False
        # ein veraendertes bild wird nicht gepostet
        Image.new("RGB", (1080, 1350), (0, 0, 0)).save(bilder[1])
        try:
            manifest_lesen(quelle, "woche", "2026-10-31")
            ok("ein bild, das vom entwurf abweicht, stoppt", False)
        except Stopp:
            ok("ein bild, das vom entwurf abweicht, stoppt", True)
        try:
            manifest_lesen(einzel, "woche", "2026-10-31")
            ok("ein entwurf fuer eine andere art stoppt", False)
        except Stopp:
            ok("ein entwurf fuer eine andere art stoppt", True)
    finally:
        globals()["gh_media"], globals()["abholbar"], instagram.graph = alt
        os.environ.pop("MEDIA_REPO_TOKEN", None)

    # ohne MEDIA_REPO_TOKEN: ablage unter ig/karussell/ auf main
    gesetzt, gewartet = [], []

    def roh_falsch(methode, url, body, kopf):
        gesetzt.append((methode, url, json.loads(body.decode())))
        return 201, b"{}", {}

    alt2 = (globals()["_roh"], instagram.url_warten, instagram.graph)
    globals()["_roh"] = roh_falsch
    instagram.url_warten = lambda url, laenge, frist=600, takt=15: gewartet.append((url, laenge)) or True
    instagram.graph = graph_falsch
    for k, v in (("GITHUB_REPOSITORY", "neoalphavault-png/kaspa-pulse"), ("GITHUB_TOKEN", "x"),
                 ("GITHUB_REF_NAME", "main")):
        os.environ[k] = v
    try:
        Image.new("RGB", (1080, 1350), (238, 243, 241)).save(bilder[1])
        (quelle / "manifest.json").write_text(json.dumps({
            "art": "woche", "fuer": "2026-10-31", "look": "hell", "caption": cap, "motiv": "",
            "bilder": [{"datei": b.name, "sha256": sha(b)} for b in bilder]}), encoding="utf-8")
        aufrufe.clear()
        e = posten("woche", "2026-10-31", quelle=quelle, start="hand", probe=True, log_pfad=tmp / "log5.json",
                   takt=0)
        bilder_urls = [a[3].get("image_url") for a in aufrufe if a[0] == "graph" and a[3].get("image_url")]
        ok("ohne media-token drei bilder unter ig/karussell auf main", len(gesetzt) == 3
           and all(g[0] == "PUT" and "/contents/ig/karussell/" in g[1] and g[2]["branch"] == "main"
                   for g in gesetzt))
        ok("instagram holt die bilder von kaspapulse.com, erst nach dem warten",
           len(gewartet) == 3 and bilder_urls == [u for u, _ in gewartet]
           and all(u.startswith("https://kaspapulse.com/ig/karussell/") for u in bilder_urls))
        ok("probe mit ablage unter ig bleibt trocken", e["modus"] == "trocken" and e.get("ablage") == "ig")
        os.environ["GITHUB_REF_NAME"] = "fix/x"
        try:
            posten("woche", "2026-10-31", quelle=quelle, start="hand", probe=True, log_pfad=tmp / "log6.json",
                   takt=0)
            ok("ablage unter ig nur von main", False)
        except Stopp as exc:
            ok("ablage unter ig nur von main", "branch main" in str(exc))
    finally:
        globals()["_roh"], instagram.url_warten, instagram.graph = alt2
        for k in ("GITHUB_REPOSITORY", "GITHUB_TOKEN", "GITHUB_REF_NAME"):
            os.environ.pop(k, None)

    # meme ohne neues motiv: kein entwurf, nur nicht faellig
    logm = tmp / "logm.json"
    logm.write_text(json.dumps(gepostet), encoding="utf-8")
    try:
        entwurf("meme", "2026-11-07", tmp / "m", log_pfad=logm, senden=False)
        ok("dasselbe meme-motiv kommt kein zweites mal", False)
    except NichtFaellig as exc:
        ok("dasselbe meme-motiv kommt kein zweites mal", "neues fehlt" in str(exc))
    print("%d fehler" % fehler)
    return 1 if fehler else 0


# ------------------------------------------------------------ main

def ausgabe_datei(**werte):
    p = os.environ.get("GITHUB_OUTPUT", "")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            for k, v in werte.items():
                fh.write("%s=%s\n" % (k, v))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("schritt", nargs="?", choices=["entwurf", "posten", "datum"])
    ap.add_argument("--art", choices=ARTEN)
    ap.add_argument("--fuer", default="")
    ap.add_argument("--out", default="graphics/karussell")
    ap.add_argument("--quelle", default="", help="ordner mit manifest.json, ohne: artefakt des entwurfs")
    ap.add_argument("--start", choices=["hand", "takt"], default="hand")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--selbsttest", "--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if not a.schritt or not a.art:
        ap.error("schritt und --art fehlen")
    fuer = fuer_aufloesen(a.art, a.fuer)
    ausgabe_datei(fuer=fuer)
    if a.schritt == "datum":
        print(fuer)
        return 0
    try:
        if a.schritt == "entwurf":
            entwurf(a.art, fuer, a.out, probe=a.probe)
        else:
            e = posten(a.art, fuer, quelle=a.quelle or None, start=a.start, probe=a.probe)
            text = ("karussell %s fuer %s %s%s" % (
                a.art, fuer, "veroeffentlicht " + e.get("permalink", "") if e["modus"] == "scharf"
                else "trocken durchgelaufen, container %s, nicht veroeffentlicht" % e.get("container"),
                " (probe)" if a.probe else ""))
            sag(text)
            ig().ops(text)
    except Stopp as exc:
        sag("STOPP %s" % exc)
        return 1
    except NichtFaellig as exc:
        sag("nicht dran, %s" % exc)
        ig().ops("karussell %s fuer %s nicht dran, %s" % (a.art, fuer, exc))
        ausgabe_datei(gebaut="0")
        return 0
    ausgabe_datei(gebaut="1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
