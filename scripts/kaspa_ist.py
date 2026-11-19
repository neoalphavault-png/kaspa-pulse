#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kaspa_ist.py, das Karussell "Kaspa is ___" (Ben, 19.11.2026).

FORMAT
    Folie 1   die Luecke als Frage, "kaspa is" und ein leerer Strich, ohne Zahl
              und ohne Diagramm (im Profilraster steht sie neben der Tagesgrafik)
    2 bis 6   je eine Fortsetzung mit einer datierten Zahl, counted, source oder
              computed, 4 oder 5 Folien
    Schluss   die Newsletter-Folie aus look_motor

Kein Kurs, keine echten Personen, nichts vom Vorbild uebernommen. Die Zahlen
holt jeder Bau frisch. Was die Tagesgrafik am selben Tag zeigt, faellt raus
(dieselbe Zahl hoechstens einmal am Tag auf Instagram). Die naechste
Reward-Stufe steht nur als Schaetzung (stufe_schaetzung.py).

LOOK
    v2          Look v2, Folien abwechselnd A-papier und D-dunkel, die
                Wortmarke unten mittig wie im Wochen-Karussell
    zweifarbig  dieselben Folien, die Headline zweifarbig ("kaspa is" in der
                Grundschrift, die Fortsetzung in Teal), @kaspapulse unten links
                statt der Wortmarke

TAKT
Gepostet wird ueber den bestehenden Mittwochs-Takt (art story, Entwurf Mi
16:00, Post Mi 18:00). data/karussell-story.json sagt, welche Vorlage dran
ist:
    {"mittwoch": "2026-11-25", "vorlage": "kaspa-is", "variante": "v2"}
karussell.vorbereiten und karussell.rendern leiten dann hierher.

    python3 scripts/kaspa_ist.py --probe --fuer 2026-11-25 --out out/kaspa-ist [--variante zweifarbig]
    python3 scripts/kaspa_ist.py --selbsttest
"""
import argparse
import datetime as dt
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

VORLAGE = "kaspa-is"
VARIANTEN = ("v2", "zweifarbig")
MIN_SEITEN, MAX_SEITEN = 4, 5
HASH_TAGE = 7
FRIST_TAGE = 10                        # aelter faellt eine fortsetzung raus
SCHWELLEN_LOG = REPO / "data" / "address-thresholds-log.json"

# welche fortsetzung die tagesgrafik mit welcher form schon zeigt
FORM_IDS = {1: ("holders", "hashrate"), 3: ("reward",), 4: ("blockrate",), 6: ("daa",),
            8: ("hashrate",), 9: ("holders",), 10: ("supply",)}


class Stopp(Exception):
    pass


def tag(d):
    import look_motor
    return look_motor.tag(d)


def ganz(n):
    return "{:,}".format(int(round(n)))


# ------------------------------------------------------------ zahlen

def zahlen(heute=None, holer=None):
    """Alle Kandidaten frisch. holer ersetzt im Selbsttest das Netz:
    {"blockrate": (bps, sek), "supply": (circ, max), "hashrate": {tag: th},
     "daa": int, "holders": (zahl, tag)}."""
    import tagesgrafik as tg
    heute = heute or dt.datetime.now(dt.timezone.utc)
    if holer is None:
        bps, _ = tg.m_blockrate(tg.BLOCKRATE_SEK)
        holer = {"blockrate": (bps, tg.BLOCKRATE_SEK), "supply": tg.m_supply(),
                 "hashrate": tg.m_hashrate_tage(),
                 "daa": int(tg.hole(tg.REST + "/info/blockdag")["virtualDaaScore"]),
                 "holders": letzte_halter()}
    nod = tg.reward_plan()
    cur, nxt, nxt_ts = nod.reward_state(heute.timestamp())
    tage = sorted(d for d in holer["hashrate"] if d < heute.date().isoformat())[-HASH_TAGE:]
    if len(tage) < HASH_TAGE:
        raise Stopp("hashrate, nur %d volle tage" % len(tage))
    return {"zeit": heute, "blockrate": holer["blockrate"], "supply": holer["supply"],
            "reward": (cur, nxt, dt.datetime.fromtimestamp(nxt_ts, dt.timezone.utc)),
            "hashrate": (statistics.mean(holer["hashrate"][d] for d in tage) / 1000.0, tage[0], tage[-1]),
            "daa": holer["daa"], "holders": holer["holders"]}


def letzte_halter(pfad=SCHWELLEN_LOG):
    """(Adressen ab 100 KAS, Stichtag) aus dem Schwellen-Log von kaspalytics."""
    log = json.loads(Path(pfad).read_text(encoding="utf-8"))
    tage = [x for x in log.get("tage", []) if x.get("holders_100kas")]
    if not tage:
        raise Stopp("schwellen-log ohne adressen ab 100 KAS")
    x = max(tage, key=lambda e: e["datum"])
    return int(x["holders_100kas"]), x["datum"]


def kandidaten(z):
    """Die Fortsetzungen in fester Reihenfolge. Jede traegt ihre Zahl, das
    Datum und genau ein Methoden-Wort."""
    import stufe_schaetzung
    t = z["zeit"]
    heute = tag(t.date())
    bps, sek = z["blockrate"]
    circ, mx = z["supply"]
    cur, nxt, stufe = z["reward"]
    ph, von, bis = z["hashrate"]
    halter, halter_tag = z["holders"]
    k = [
        {"id": "blockrate", "wort": "fast", "zahl": "%.1f" % bps, "label": "blocks a second",
         "quelle": "counted by kaspa pulse over %d minute%s, %s, %s utc" % (
             sek // 60, "" if sek // 60 == 1 else "s", heute, t.strftime("%H:%M")),
         "haken": "%.1f blocks a second" % bps, "datum": heute},
        {"id": "supply", "wort": "capped", "zahl": "%.1f%%" % (100 * circ / mx),
         "label": "of the %.1f billion KAS maximum is mined" % (mx / 1e9),
         "quelle": "source kaspa rest api, %s" % heute,
         "haken": "%.1f%% of the %.1f billion KAS maximum mined" % (100 * circ / mx, mx / 1e9), "datum": heute},
        {"id": "reward", "wort": "on a schedule", "zahl": "%.2f" % nxt,
         "label": "KAS per block from %s, down from %.2f" % (stufe_schaetzung.kurz(stufe), cur),
         "quelle": "computed from the emission schedule, as of %s" % heute,
         "haken": "%.2f KAS per block from %s" % (nxt, stufe_schaetzung.kurz(stufe)), "datum": heute},
        {"id": "holders", "wort": "widely held", "zahl": ganz(halter),
         "label": "addresses hold at least 100 KAS, one wallet can use many",
         "quelle": "source kaspalytics address thresholds, %s" % tag(halter_tag),
         "haken": "%s addresses with at least 100 KAS" % ganz(halter), "datum": tag(halter_tag)},
        {"id": "hashrate", "wort": "secured by work", "zahl": "%.1f" % ph,
         "label": "PH/s of proof of work, mean of %d days" % HASH_TAGE,
         "quelle": "source kaspa rest api, %s to %s" % (tag(von), tag(bis)),
         "haken": "%.1f PH/s of proof of work" % ph, "datum": "%s to %s" % (tag(von), tag(bis))},
        {"id": "daa", "wort": "a blockdag", "zahl": "%dM" % round(z["daa"] / 1e6),
         "label": "blocks since nov 2021, many at once, none thrown away",
         "quelle": "source kaspa rest api, daa score, %s" % heute,
         "haken": "%d million blocks since nov 2021" % round(z["daa"] / 1e6), "datum": heute},
    ]
    return k


def tagesgrafik_ids(fuer, log=None):
    """Die Fortsetzungen, deren Zahl die Tagesgrafik am selben Tag zeigt."""
    if log is None:
        try:
            log = json.loads((REPO / "data" / "tagesgrafik-log.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return set()
    aus = set()
    for e in log.get("laeufe", []):
        if e.get("datum") == str(fuer):
            aus.update(FORM_IDS.get(e.get("form"), ()))
    return aus


def seiten(z, fuer, schon=None, anzahl=MAX_SEITEN):
    """Die Seiten fuer karussell.py: titel, 4 bis 5 fortsetzungen, newsletter."""
    import karussell
    schon = tagesgrafik_ids(fuer) if schon is None else set(schon)
    # eine zahl mit stichtag aelter als FRIST_TAGE faellt raus, statt alt zu erscheinen
    if (z["zeit"].date() - dt.date.fromisoformat(z["holders"][1])).days > FRIST_TAGE:
        schon = schon | {"holders"}
    k = [x for x in kandidaten(z) if x["id"] not in schon][:anzahl]
    if len(k) < MIN_SEITEN:
        raise Stopp("nur %d fortsetzungen frei, die tagesgrafik zeigt heute %s"
                    % (len(k), ", ".join(sorted(schon))))
    heute = tag(z["zeit"].date())
    ss = [{"art": "titel", "vorlage": VORLAGE, "kopf": "KASPA IS", "satz": "kaspa is",
           "frage": "how would you finish it?",
           "datum": "as of %s, %d endings, each with a dated number" % (heute, len(k))}]
    for x in k:
        ss.append(dict(x, art="gedanke", kopf="KASPA IS", satz="kaspa is %s" % x["wort"],
                       datum="%s · %s" % (x["label"], x["quelle"])))
    ss.append(karussell.newsletter_seite())
    for i, x in enumerate(ss):
        x["seite"], x["von"] = i + 1, len(ss)
    return ss


def bausteine(ss):
    """Bausteine der Caption aus der ersten Fortsetzung, ein Methoden-Wort."""
    x = next(s for s in ss if s["art"] == "gedanke")
    n = sum(1 for s in ss if s["art"] == "gedanke")
    return {"zahl_zuerst": "%s, kaspa is %s" % (x["haken"], x["wort"]),
            "beobachtung": "kaspa is %s, %s" % (x["wort"], x["haken"]),
            "satz": x["quelle"],
            "einordnung": "one sentence and %d ways to end it, each with a dated number" % n,
            "pointe": "%d endings, every one of them checkable" % n,
            "frage": "how would you finish the sentence?"}


def caption(ss, fuer=None, stand=None, mit_plan=False):
    import karussell
    b = bausteine(ss)
    if fuer is None:
        erg = ("frage", karussell.caption(b["zahl_zuerst"], b["satz"], b["frage"]))
    else:
        erg = karussell.caption_nach_bauplan("karussell", fuer, b, stand)
    return erg if mit_plan else erg[1]


def texte(ss):
    """Alle sichtbaren Texte der Folien fuer die Wachen."""
    aus = []
    for x in ss:
        for k in ("satz", "zahl", "label", "quelle", "datum", "frage"):
            if x.get(k):
                aus.append(x[k])
    return aus


def vorbereiten(st, fuer, stand=None, z=None, schon=None):
    """Aus der Story-Datei mit vorlage kaspa-is: (seiten, caption, bauplan)."""
    import stufe_schaetzung
    if fuer and st.get("mittwoch") != fuer:
        raise Stopp("story-datei ist fuer %s, nicht fuer %s" % (st.get("mittwoch"), fuer))
    if (st.get("variante") or "v2") not in VARIANTEN:
        raise Stopp("variante %r, erlaubt %s" % (st.get("variante"), ", ".join(VARIANTEN)))
    if (st.get("variante") or "v2") == "zweifarbig" and not st.get("zweifarbig_frei"):
        # gepostet wird die variante erst, wenn Ben die fusszeile links freigibt
        raise Stopp("variante zweifarbig traegt @kaspapulse unten links, das verbietet die feed-regel "
                    "fusszeile mittig. freigabe mit \"zweifarbig_frei\": true in der story-datei")
    z = z or zahlen()
    ss = seiten(z, fuer, schon)
    plan, cap = caption(ss, fuer=fuer, stand=stand, mit_plan=True)
    heute = z["zeit"].date()
    fehler = [v for t in texte(ss) + [cap] for v in stufe_schaetzung.verstoesse(t, heute)]
    if fehler:
        raise Stopp("stufe, %s" % fehler[0])
    for x in ss:
        x["variante"] = st.get("variante") or "v2"
    return ss, cap, plan


# ------------------------------------------------------------ bild

# grund, schrift, leise, zahl, fortsetzung in der zweifarbigen headline. Teal
# #49EACB erreicht auf papier nur 1.3:1, dort steht die fortsetzung in einem
# dunklen teal mit 8.4:1 (die grafik-regel verlangt 7:1), auf stein in #49EACB
# mit 11.1:1
GRUND = {"A-papier": ("#F4F1EA", "#0B1A17", "#3A4744", "#0B1A17", "#0A4F43"),
         "D-dunkel": ("#1F1D1A", "#F2F5F4", "#D6D0C6", "#49EACB", "#49EACB")}

CSS = """
.kopfzeile{font:500 34px/1.2 'IBM Plex Mono',monospace;letter-spacing:.04em}
.headline{font:900 96px/1.0 Archivo,sans-serif;letter-spacing:-.02em;text-wrap:balance}
.luecke{display:inline-block;width:360px;height:14px;vertical-align:baseline;margin-left:22px}
.zahl{font:900 230px/.86 Archivo,sans-serif;letter-spacing:-.035em;white-space:nowrap}
.label{font:500 40px/1.25 'IBM Plex Sans',sans-serif;text-wrap:balance}
.quelle{font:400 34px/1.3 'IBM Plex Mono',monospace}
.handle{position:absolute;left:72px;bottom:72px;font:600 34px/1 'IBM Plex Mono',monospace}
"""


def seite_html(look, x, variante):
    """Eine Folie 1080x1350. In der Variante zweifarbig steht @kaspapulse
    unten links (Klasse wm, damit look_motor den Kontrast misst und die Farbe
    setzt), sonst die Wortmarke unten mittig."""
    import look_motor
    import look_takt
    import wortmarke
    esc = look_motor.esc
    grund, schrift, leise, zahl_f, fort_f = GRUND[look]
    zwei = variante == "zweifarbig"
    teile = ["<div class='t kopfzeile' style='left:72px;top:72px;color:%s'>%s</div>"
             % (leise, "kaspa is ___" if x["art"] == "titel" else "kaspa is, %d of %d" % (x["seite"] - 1, x["von"] - 2)),
             "<div class='linie' style='left:72px;right:72px;top:134px;background:%s'></div>" % leise]
    if x["art"] == "titel":
        teile += [
            "<div class='t headline' data-rolle='titel' style='left:72px;right:72px;top:360px;color:%s'>"
            "kaspa is<span class='luecke' style='background:%s'></span>?</div>"
            % (schrift, "#49EACB" if look == "D-dunkel" else schrift),
            "<div class='t label' style='left:72px;right:120px;top:720px;color:%s'>%s</div>"
            % (schrift, esc(x["frage"])),
            "<div class='t quelle' style='left:72px;right:72px;top:1000px;color:%s'>%s</div>"
            % (leise, esc(x["datum"])),
        ]
    else:
        fort = ("<span style='color:%s'>%s</span>" % (fort_f, esc(x["wort"])) if zwei else esc(x["wort"]))
        teile += [
            "<div class='t headline' data-rolle='titel' style='left:72px;right:72px;top:190px;color:%s'>"
            "kaspa is %s</div>" % (schrift, fort),
            "<div class='t zahl' data-rolle='zahl' data-fit='936' style='left:66px;top:540px;color:%s'>%s</div>"
            % (zahl_f, esc(x["zahl"])),
            "<div class='t label' style='left:72px;right:120px;top:790px;color:%s'>%s</div>"
            % (schrift, esc(x["label"])),
            "<div class='t quelle' style='left:72px;right:72px;top:1000px;color:%s'>%s</div>"
            % (leise, esc(x["quelle"])),
        ]
        if look == "A-papier":
            teile.append("<div class='linie' style='left:72px;width:240px;top:762px;height:8px;"
                         "background:#49EACB'></div>")
    if zwei:
        teile.append("<div class='fuss' data-rolle='fuss' style='left:72px;transform:none'>"
                     "<span class='wm'>@kaspapulse</span></div>")
    else:
        teile.append("<div class='fuss' data-rolle='fuss'>%s</div>" % wortmarke.html())
    css = (look_takt.schriften_css() + look_motor.CSS + CSS + "body{background:%s}" % grund
           + wortmarke.css(groesse=36, sperrung=6, kaspa=schrift, pulse=schrift))
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s</style></head>"
            "<body data-look='%s'>%s</body></html>" % (css, look, "".join(teile)))


def plan(ss, speicher, fuer, merken=True):
    """[(look, seite)]: der Titel-Look aus der Rotation des Kanals karussell,
    dann abwechselnd, die Newsletter-Folie im Gegen-Look."""
    import look_takt
    titel = look_takt.richtung_faellig(speicher, "karussell", fuer, "story", erlaubt=("A", "D"))
    folge = ("A-papier", "D-dunkel") if titel == "A" else ("D-dunkel", "A-papier")
    aus = [(folge[i % 2], x) for i, x in enumerate(ss[:-1])]
    aus.append(("D-hell" if aus[-1][0].startswith("A") else "A-papier", ss[-1]))
    if merken:
        look_takt.richtung_merken(speicher, "karussell", fuer, "story", erlaubt=("A", "D"))
    return aus


def bilder(fuer, ss, out, speicher=None, merken=False):
    """Alle Folien als PNG 1080x1350, durch dieselben Wachen wie Look v2
    (Passform, Ueberlappung, Wortmarke mit 4.5:1, content_wache). Gibt
    (pngs, info) zurueck."""
    import content_wache
    import look_motor
    import look_takt
    import tagesgrafik as tg
    from playwright.sync_api import sync_playwright
    variante = ss[0].get("variante") or "v2"
    sp = speicher if speicher is not None else look_takt.lesen()
    if not merken:
        sp = json.loads(json.dumps(sp))
    p_ = plan(ss, sp, fuer, merken=True)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pngs, info = [], []
    with sync_playwright() as p:
        b = tg.chromium_start(p)
        try:
            for i, (look, x) in enumerate(p_, 1):
                png = out / ("karussell-story-%s-%d-%s-%s.png" % (fuer, i, look, variante))
                if x["art"] == "newsletter":
                    inh = look_motor.newsletter_inhalt()
                    variante_logo, werte = look_motor.seite_rendern(b, look, inh, png, sp, "karussell")
                else:
                    variante_logo, werte = _rendern(b, look, x, variante, png, sp, content_wache, look_motor,
                                                    look_takt)
                pngs.append(png)
                info.append({"seite": i, "look": look, "art": x["art"], "logo": variante_logo,
                             "logo_kontrast": {k: round(v, 2) for k, v in werte.items()}})
        finally:
            b.close()
    if merken and speicher is not None:
        speicher.clear()
        speicher.update(sp)
    return pngs, {"seiten": info, "variante": variante}


def _rendern(b, look, x, variante, png, sp, content_wache, look_motor, look_takt):
    html = Path(png).with_suffix(".html")
    html.write_text(seite_html(look, x, variante), encoding="utf-8")
    pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
    try:
        pg.goto(html.resolve().as_uri())
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(250)
        f = pg.evaluate(look_motor.FIT_JS)
        if f:
            raise Stopp("%s, %s" % (look, "; ".join(f)))
        werte = look_motor.logo_kontraste(look_motor.logo_messen(pg))
        gueltig = [v for v, k in werte.items() if k >= look_motor.LOGO_MIN]
        logo = look_takt.logo_waehlen(sp, "karussell", gueltig)
        look_motor.logo_setzen(pg, logo)
        pg.wait_for_timeout(50)
        pg.screenshot(path=str(png))
        v = content_wache.pruefe_seite(pg, "instagram", png)
        if variante == "zweifarbig":
            # @kaspapulse unten links widerspricht der feed-regel "fusszeile
            # mittig" (content_wache, fuss_mitte). Nur dieser eine befund wird
            # fuer den entwurf hingenommen, Ben entscheidet (19.11.2026)
            v = [x for x in v if "fusszeile reicht in eine ecke" not in x] if v else v
        if v:
            raise Stopp("%s, wache, %s" % (look, "; ".join(v)))
    finally:
        pg.close()
        html.unlink()
    return logo, werte


# ------------------------------------------------------------ selbsttest

def probe_zahlen():
    t = dt.datetime(2026, 11, 25, 14, 0, tzinfo=dt.timezone.utc)
    tage = {(dt.date(2026, 11, 25) - dt.timedelta(days=i)).isoformat(): 340000.0 + i * 1000 for i in range(1, 10)}
    return zahlen(t, holer={"blockrate": (10.02, 600), "supply": (27.31e9, 28.70e9), "hashrate": tage,
                            "daa": 412000000, "holders": (297500, "2026-11-23")})


def selbsttest(bild=False, out=None):
    import karussell
    import stufe_schaetzung
    f = []

    def ok(name, bed, info=""):
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, ("  " + str(info)) if not bed and info else ""))
        if not bed:
            f.append(name)

    z = probe_zahlen()
    st = {"mittwoch": "2026-11-25", "vorlage": VORLAGE, "variante": "v2"}
    stand = {"tage": {}}
    ss, cap, plan_ = vorbereiten(st, "2026-11-25", stand=stand, z=z, schon=set())
    inhalt = [x for x in ss if x["art"] == "gedanke"]
    ok("folie 1 ist die luecke als frage, ohne zahl", ss[0]["art"] == "titel" and not ss[0].get("zahl")
       and ss[0]["frage"].endswith("?"))
    ok("5 fortsetzungen, am ende die newsletter-folie", len(inhalt) == 5 and ss[-1]["art"] == "newsletter",
       [x["id"] for x in inhalt])
    ok("jede fortsetzung mit zahl, datum und genau einem methoden-wort",
       all(x["zahl"] and x["datum"] and sum(w in x["quelle"] for w in ("counted", "computed", "source")) == 1
           for x in inhalt))
    ok("counted nur bei der eigenen zaehlung", [x["id"] for x in inhalt if "counted" in x["quelle"]] == ["blockrate"])
    r = next(x for x in inhalt if x["id"] == "reward")
    ok("reward-stufe als schaetzung, around 5 dec, estimate, ohne uhrzeit",
       "around 5 dec, estimate" in r["label"] and not stufe_schaetzung.verstoesse(r["label"], dt.date(2026, 11, 25)),
       r["label"])
    ok("textwachen der karussells ohne fund", karussell.text_pruefen(texte(ss)) == [],
       karussell.text_pruefen(texte(ss))[:3])
    ok("caption ohne fund", karussell.caption_pruefen(cap) == [], karussell.caption_pruefen(cap))
    ok("kein kurs, kein dollar, keine personen", not any(c in " ".join(texte(ss)) + cap for c in ("$", "price", "usd")))
    ss4, _, _ = vorbereiten(st, "2026-11-25", stand=stand, z=z, schon={"hashrate"})
    ok("was die tagesgrafik zeigt, faellt raus", "hashrate" not in [x.get("id") for x in ss4]
       and sum(1 for x in ss4 if x["art"] == "gedanke") == 5)
    try:
        vorbereiten(st, "2026-11-25", stand=stand, z=z, schon={"hashrate", "holders", "supply"})
        zu_wenig = False
    except Stopp:
        zu_wenig = True
    ok("weniger als 4 fortsetzungen frei stoppt", zu_wenig)
    z_alt = dict(z, holders=(297500, "2026-11-10"))
    ss_alt = seiten(z_alt, "2026-11-25", schon=set())
    ok("ein stichtag aelter als 10 tage faellt raus", "holders" not in [x.get("id") for x in ss_alt]
       and sum(1 for x in ss_alt if x["art"] == "gedanke") == 5)
    ok("blockrate ueber 10 minutes", "over 10 minutes," in inhalt[0]["quelle"], inhalt[0]["quelle"])
    try:
        vorbereiten(dict(st, mittwoch="2026-12-02"), "2026-11-25", stand=stand, z=z, schon=set())
        falsch = False
    except Stopp:
        falsch = True
    ok("story-datei fuer einen anderen mittwoch stoppt", falsch)
    ok("tagesgrafik-ids aus dem log", tagesgrafik_ids("2026-11-25", {"laeufe": [
        {"datum": "2026-11-25", "form": 1}, {"datum": "2026-11-24", "form": 3}]}) == {"holders", "hashrate"})
    h2 = seite_html("D-dunkel", ss[1], "zweifarbig")
    ok("zweifarbig, fortsetzung in teal, @kaspapulse unten links", "color:#49EACB'>" in h2
       and "@kaspapulse" in h2 and "left:72px;transform:none" in h2)
    ok("v2 mit der wortmarke unten mittig", "@kaspapulse" not in seite_html("A-papier", ss[1], "v2"))
    try:
        vorbereiten(dict(st, variante="zweifarbig"), "2026-11-25", stand=stand, z=z, schon=set())
        gesperrt = False
    except Stopp:
        gesperrt = True
    ok("zweifarbig nur mit freigabe in der story-datei", gesperrt)
    if bild:
        import tempfile
        o = Path(out or tempfile.mkdtemp(prefix="kaspa-ist-"))
        for var in VARIANTEN:
            s2 = [dict(x, variante=var) for x in ss]
            pngs, info = bilder("2026-11-25", s2, o / var, speicher={}, merken=False)
            ok("bild %s, %d folien durch die wachen" % (var, len(pngs)), len(pngs) == len(ss), info)
    print("")
    print("%d fehler" % len(f) if f else "alle testfaelle bestanden")
    return 1 if f else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--bild", action="store_true", help="im selbsttest auch rendern")
    ap.add_argument("--probe", action="store_true", help="frisch messen und bauen, nichts merken, nichts senden")
    ap.add_argument("--fuer", default="")
    ap.add_argument("--variante", default="v2", choices=VARIANTEN)
    ap.add_argument("--out", default="out/kaspa-ist")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest(a.bild, a.out if a.bild else None)
    if a.probe:
        st = {"mittwoch": a.fuer, "vorlage": VORLAGE, "variante": a.variante}
        ss, cap, plan_ = vorbereiten(st, a.fuer, stand={"tage": {}})
        pngs, info = bilder(a.fuer, ss, a.out, speicher=None, merken=False)
        Path(a.out, "caption.txt").write_text(cap + "\n", encoding="utf-8")
        print("\n".join(str(p) for p in pngs))
        print(json.dumps(info))
        print("CAPTION (%s)\n%s" % (plan_, cap))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
