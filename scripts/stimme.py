#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stimme.py, die Stimm-Regel fuer alle automatischen Texte (Ben, 07.11.2026).

Die Regel steht in claude/regel-stimme-menschlich-2026-11-07.md. Dieser
Baustein haelt sie fuer alle Kanaele an einer Stelle: X-Tagespost, Instagram-
Caption der Tagesgrafik, Threads, Discord (#daily-graphic), Karussell und
Meme. Die Ops-Meldungen (#ops-log, #moderator-only) sind keine oeffentlichen
Texte und laufen nicht hier durch.

SCHREIBUNG. Normale Gross- und Kleinschreibung: Satzanfang gross, Eigennamen
richtig (Kaspa, Bitcoin, KAS, PH/s, UTC, DAA, Kaspalytics ...). Die Vorlagen
schreiben weiter klein, schreibung() setzt die Grossbuchstaben erst am
fertigen Posttext. Hashtags, Handles und Links bleiben, wie sie sind. Die
Bildtexte (Kopf, Datumszeile) gehen hier nicht durch, sie sind Bild.

BAUPLAENE. Ein Text folgt genau einem Bauplan:
  beobachtung   der Satz mit der Zahl, dann Fenster und Quelle
  vergleich     Bitcoin als Massstab, zwei Zahlen nebeneinander, ohne
                Werturteil. Nur mit einer echten, datierten Bitcoin-Zahl aus
                data/bitcoin-massstab.json, sonst faellt er aus
  einordnung    der Satz mit der Zahl, Fenster und Quelle, dazu ein Satz,
                der die Zahl einordnet
  pointe        der Satz mit der Zahl, Fenster und Quelle, dazu eine kurze
                trockene Pointe
  frage         wie beobachtung, am Ende eine Frage. Nur gelegentlich: an
                jedem FRAGE_TAKT-ten Tag fuer einen Kanal, sonst nur als
                Reserve, wenn kein anderer Bauplan mehr frei ist
  datum_voran   das Datum fuehrt ("On 6 Nov 2026, ..."), dann nur die Quelle
  zahl_zuerst   die Zahl mit Einheit fuehrt, dann Fenster und Quelle

TAGESREGEL. Derselbe Bauplan nie zweimal am selben Tag ueber alle Kanaele.
data/stimme-stand.json haelt je Tag, welcher Kanal welchen Bauplan hat; die
Tagesgrafik (X, Instagram, Threads, Discord) schreibt ihn mit --log-schreiben,
Karussell und Meme in ihrem Entwurf. Die Wahl ist deterministisch: Reihenfolge
aus Datum und Kanal, der erste freie Bauplan, dessen Text die Wachen haelt.
Ein zweiter Lauf am selben Tag bekommt denselben Bauplan wieder.

FLOSKELN, METHODE. Fuenf Floskeln sind gesperrt, im Text und im Quelltext
der Textskripte. Je Text hoechstens ein Methoden-Wort (counted, computed oder
source), keine der drei alten Schlussfragen.

    python3 scripts/stimme.py --selbsttest
    python3 scripts/stimme.py --pruefen --text "..." [--bauplan frage]
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
STAND = REPO / "data" / "stimme-stand.json"
BITCOIN = REPO / "data" / "bitcoin-massstab.json"

BAUPLAENE = ("beobachtung", "vergleich", "einordnung", "pointe", "frage", "datum_voran", "zahl_zuerst")
# X nicht: der automatische X-Post von @gokugalax ist abgeschaltet (Ben, 07.11.2026)
PLATTFORMEN = ("instagram", "threads", "discord", "karussell", "meme")
# an jedem 4. tag darf ein kanal fragen, reihum; sonst ist die frage reserve
FRAGE_TAKT = 4
HALTEN_TAGE = 30

FLOSKELN = ("one thing we keep in mind", "useful view", "good work by", "the part worth watching",
            "method on pulsehawk.io")
ALTE_FRAGEN = ("what number would you put next to this one?", "how many kas is that?",
               "what was that work paid?")
METHODE = re.compile(r"\b(counted|computed|source)\b", re.I)
# Bitcoin nur als Massstab: zwei Zahlen nebeneinander, kein Urteil
WERTURTEIL = re.compile(r"\b(better|worse|best|worst|faster|slower|superior|inferior|beats?|beaten|"
                        r"wins?|outperforms?|stronger|weaker|than bitcoin|than btc|kills?|killer)\b", re.I)
BITCOIN_WORT = re.compile(r"\b(bitcoin|btc)\b", re.I)
# die echtzeitwoerter der regel, die pruefe_eine noch nicht kennt
ECHTZEIT_DAZU = re.compile(r"\b(today|tonight|this morning|this evening|for now)\b", re.I)
REKORD = re.compile(r"\b(record|all.time high|ath)\b", re.I)
ZEITRAUM = re.compile(r"\b(since|in the \d+|in \d+ (days|weeks|months)|week to|days to|in our (log|series))\b",
                      re.I)


class StimmeStopp(ValueError):
    """Kein Bauplan frei oder eine Regel gebrochen."""


# ------------------------------------------------------------ schreibung

MONATE = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
_MON = "(?:%s)" % "|".join(MONATE)
EIGENNAMEN = (
    (r"kaspa pulse", "Kaspa Pulse"), (r"kaspa rest api", "Kaspa REST API"), (r"rest api", "REST API"),
    (r"kaspa", "Kaspa"), (r"bitcoin", "Bitcoin"), (r"btc", "BTC"), (r"kaspalytics", "Kaspalytics"),
    (r"utc", "UTC"), (r"daa", "DAA"), (r"iupac", "IUPAC"), (r"kas", "KAS"), (r"ph/s", "PH/s"),
    (r"entity x", "Entity X"), (r"discord", "Discord"), (r"youtube", "YouTube"),
    (r"instagram", "Instagram"), (r"crescendo", "Crescendo"), (r"kasplex", "Kasplex"),
    (r"igra", "Igra"), (r"kcc-20", "KCC-20"), (r"ipv4", "IPv4"), (r"on x at", "on X at"),
    (r"monday", "Monday"), (r"tuesday", "Tuesday"), (r"wednesday", "Wednesday"),
    (r"thursday", "Thursday"), (r"friday", "Friday"), (r"saturday", "Saturday"), (r"sunday", "Sunday"),
)
_SCHUTZ = re.compile(r"https?://\S+|www\.\S+|[#@][\w-]+|\b[\w-]+\.(?:com|org|io|net|stream|xyz|app|dev|de|fyi)\b\S*",
                     re.I)


def schreibung(text):
    """Normale Gross- und Kleinschreibung fuer einen fertigen Posttext."""
    if not text:
        return text
    geschuetzt = []

    def weg(m):
        geschuetzt.append(m.group(0))
        return "\x00%d\x00" % (len(geschuetzt) - 1)
    t = _SCHUTZ.sub(weg, text)
    for klein, gross in EIGENNAMEN:
        # nur die kleine form, "KAsPa" im meme bleibt, wie es ist
        t = re.sub(r"(?<![\w/-])%s(?![\w-])" % re.escape(klein).replace(r"\ ", " "), gross, t)
    # monate: nach einer tageszahl oder vor einer jahreszahl
    t = re.sub(r"\b(\d{1,2}) (%s)\b" % _MON, lambda m: "%s %s" % (m.group(1), m.group(2).capitalize()), t,
               flags=re.I)
    t = re.sub(r"\b(%s) ((?:19|20)\d\d)\b" % _MON, lambda m: "%s %s" % (m.group(1).capitalize(), m.group(2)), t,
               flags=re.I)
    # satzanfang: textbeginn, nach . ? ! mit leerraum, nach jedem zeilenumbruch
    t = re.sub(r"(^|[.!?][ \t]+|\n[ \t]*)([a-z])", lambda m: m.group(1) + m.group(2).upper(), t)
    return re.sub(r"\x00(\d+)\x00", lambda m: geschuetzt[int(m.group(1))], t)


def klein_verstoesse(text):
    """Was an der Schreibung noch klein steht, als Liste."""
    aus = []
    # ein handle oder link am satzanfang bleibt, wie er ist, und gilt als gross
    t = _SCHUTZ.sub("Q", text or "")
    for m in re.finditer(r"(?:^|[.!?][ \t]+|\n[ \t]*)([a-z])", t):
        aus.append("satz beginnt klein bei %r" % t[m.start(1):m.start(1) + 12])
        break
    for wort in ("kaspa", "bitcoin", "utc", "kaspalytics"):
        if re.search(r"(?<![\w/-])%s(?![\w-])" % wort, t):
            aus.append("%s klein geschrieben" % wort)
    return aus


# ------------------------------------------------------------ regeln

def regel_verstoesse(text, bauplan=None):
    """Die Stimm-Regel an einem fertigen Posttext. bauplan None heisst: ein
    Text ohne eigenen Bauplan (die Antwort unter dem X-Post), er fragt nicht."""
    aus = []
    t = text or ""
    klein = t.lower()
    for f in FLOSKELN:
        if f in klein:
            aus.append("floskel %r" % f)
    for f in ALTE_FRAGEN:
        if f in klein:
            aus.append("alte schlussfrage %r" % f)
    n = len(METHODE.findall(t))
    if n > 1:
        aus.append("%d methoden-woerter (counted, computed, source), hoechstens 1" % n)
    fragen = t.count("?")
    if bauplan == "frage":
        if fragen != 1:
            aus.append("bauplan frage braucht genau eine frage, hat %d" % fragen)
    elif fragen:
        aus.append("frage ohne bauplan frage")
    if BITCOIN_WORT.search(t) and bauplan != "vergleich":
        aus.append("bitcoin ausserhalb des bauplans vergleich")
    m = WERTURTEIL.search(t)
    if m:
        aus.append("werturteil %r" % m.group(0))
    m = ECHTZEIT_DAZU.search(t)
    if m:
        aus.append("echtzeit-wort %r" % m.group(0))
    import content_wache
    m = content_wache.UNGENAU.search(t)
    if m:
        aus.append("ungenau %r" % m.group(0))
    if REKORD.search(t) and not ZEITRAUM.search(t):
        aus.append("rekord ohne zeitraum")
    if "percent" in klein:
        aus.append("'percent' statt %")
    aus += klein_verstoesse(t)
    if bauplan is not None and bauplan not in BAUPLAENE:
        aus.append("unbekannter bauplan %r" % bauplan)
    return aus


def tag_verstoesse(belegung):
    """belegung {kanal: bauplan} eines Tages. Derselbe Bauplan zweimal ist ein Verstoss."""
    aus, gesehen = [], {}
    for k in sorted(belegung):
        b = belegung[k]
        if b in gesehen:
            aus.append("bauplan %s am selben tag auf %s und %s" % (b, gesehen[b], k))
        gesehen[b] = k
    return aus


def floskeln_im_quelltext(dateien=None):
    """Die Floskeln im Quelltext der Textskripte, als Liste (Datei, Floskel).
    Die Sperrliste selbst in diesem Baustein zaehlt nicht."""
    dateien = dateien or [HERE / n for n in TEXTSKRIPTE]
    aus = []
    for p in dateien:
        try:
            klein = Path(p).read_text(encoding="utf-8").lower()
        except OSError:
            continue
        for f in FLOSKELN:
            if f in klein:
                aus.append((Path(p).name, f))
    return aus


TEXTSKRIPTE = ("tagesgrafik.py", "karussell.py", "look_motor.py", "meme_wahr.py", "threads.py",
               "instagram.py", "karussell_post.py")


# ------------------------------------------------------------ wahl

def _datum(tag):
    return tag if isinstance(tag, dt.date) else dt.date.fromisoformat(str(tag)[:10])


def frage_kanal(tag):
    """Der Kanal, der an diesem Tag fragen darf, oder None."""
    o = _datum(tag).toordinal()
    if o % FRAGE_TAKT:
        return None
    return PLATTFORMEN[(o // FRAGE_TAKT) % len(PLATTFORMEN)]


def reihenfolge(tag, plattform):
    """Die Baupläne fuer diesen Kanal an diesem Tag, in der Reihenfolge, in
    der sie versucht werden. Die Frage steht vorn nur beim Fragekanal des
    Tages, sonst ganz hinten als Reserve."""
    basis = [b for b in BAUPLAENE if b != "frage"]
    k = (_datum(tag).toordinal() + PLATTFORMEN.index(plattform)) % len(basis)
    folge = basis[k:] + basis[:k]
    return (["frage"] + folge) if frage_kanal(tag) == plattform else (folge + ["frage"])


def lesen(pfad=None):
    try:
        d = json.loads(Path(pfad or STAND).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) and isinstance(d.get("tage"), dict) else {"tage": {}}
    except (OSError, ValueError):
        return {"tage": {}}


def schreiben(stand, pfad=None, heute=None):
    heute = _datum(heute or dt.date.today())
    grenze = (heute - dt.timedelta(days=HALTEN_TAGE)).isoformat()
    stand["tage"] = {k: v for k, v in sorted(stand.get("tage", {}).items()) if k >= grenze}
    Path(pfad or STAND).write_text(json.dumps(stand, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                   encoding="utf-8")


def waehlen(tag, plattform, bauen, stand, pruefen=None):
    """Waehlt den Bauplan fuer einen Kanal und baut den Text.

    bauen(bauplan) gibt den fertigen Text oder None, wenn der Bauplan fuer
    diesen Kanal oder diese Daten nicht geht. pruefen(text, bauplan) gibt die
    Befunde der Kanalwache. Genommen wird der erste freie Bauplan, dessen
    Text alle Wachen haelt; er steht danach in stand. Gibt (bauplan, text)."""
    if plattform not in PLATTFORMEN:
        raise StimmeStopp("unbekannter kanal %r" % plattform)
    t_iso = _datum(tag).isoformat()
    heute = stand.setdefault("tage", {}).setdefault(t_iso, {})
    belegt = {b for k, b in heute.items() if k != plattform}
    folge = reihenfolge(tag, plattform)
    if heute.get(plattform) in folge:
        folge.remove(heute[plattform])
        folge.insert(0, heute[plattform])
    gruende = []
    for b in folge:
        if b in belegt:
            continue
        text = bauen(b)
        if not text:
            continue
        befunde = regel_verstoesse(text, b) + (list(pruefen(text, b)) if pruefen else [])
        if befunde:
            gruende.append("%s, %s" % (b, "; ".join(befunde)))
            continue
        heute[plattform] = b
        return b, text
    raise StimmeStopp("%s am %s, kein bauplan frei (belegt %s)%s" % (
        plattform, t_iso, ", ".join(sorted(belegt)) or "-", "; " + " | ".join(gruende) if gruende else ""))


# ------------------------------------------------------------ bausteine

def saetze(bauplan, kern, beleg, herkunft="", stand="", einordnung="", pointe="", frage="",
           vergleich="", zahl_kern=""):
    """Die Saetze eines Textes nach Bauplan, ohne Schreibung. Leer, wenn der
    Bauplan mit diesen Bausteinen nicht geht.

    kern       der Satz mit der Zahl ("kaspa miners ran 350 quadrillion ...")
    beleg      Fenster oder Datum und Quelle, hoechstens ein Methoden-Wort
    herkunft   nur die Quelle, ohne Datum, fuer datum_voran
    stand      das Datum der Zahl ("6 nov 2026"), fuer datum_voran
    zahl_kern  die Zahl mit Einheit vorn ("350.2 PH/s of hashrate")"""
    def satz(t):
        t = (t or "").strip().rstrip(" .")
        return (t + ".") if t and not t.endswith("?") else t
    if bauplan == "beobachtung":
        return [satz(kern), satz(beleg)]
    if bauplan == "zahl_zuerst":
        return [satz(zahl_kern), satz(beleg)] if zahl_kern else []
    if bauplan == "datum_voran":
        if not (stand and herkunft):
            return []
        k = kern.strip()
        return [satz("on %s, %s" % (stand, k[:1].lower() + k[1:])), satz(herkunft)]
    if bauplan == "einordnung":
        return [satz(kern), satz(beleg), satz(einordnung)] if einordnung else []
    if bauplan == "pointe":
        return [satz(kern), satz(beleg), satz(pointe)] if pointe else []
    if bauplan == "frage":
        return [satz(kern), satz(beleg), frage.strip()] if frage and frage.strip().endswith("?") else []
    if bauplan == "vergleich":
        return [satz(kern), satz(beleg), satz(vergleich)] if vergleich else []
    return []


def bitcoin_zahl(kennzahl, bis, pfad=None):
    """Eine datierte Bitcoin-Zahl als Massstab, oder None.

    data/bitcoin-massstab.json ist {"zahlen": [{"kennzahl": "...", "datum":
    "JJJJ-MM-TT", "satz": "bitcoin ... on 6 nov 2026"}]}. Genommen wird der
    juengste Eintrag der Kennzahl, der nicht nach bis liegt und hoechstens
    7 Tage alt ist. Der Satz muss sein Datum tragen. Ohne Datei kein
    Vergleich (Stand 07.11.2026: die Datei gibt es noch nicht)."""
    try:
        d = json.loads(Path(pfad or BITCOIN).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    bis = _datum(bis)
    beste = None
    for e in d.get("zahlen") or []:
        try:
            tag = _datum(e.get("datum", ""))
        except ValueError:
            continue
        if e.get("kennzahl") != kennzahl or tag > bis or (bis - tag).days > 7:
            continue
        satz = str(e.get("satz", ""))
        if not re.search(r"\b\d{1,2} %s\b" % _MON, satz, re.I) or not re.search(r"\d", satz):
            continue
        if WERTURTEIL.search(satz) or METHODE.search(satz):
            continue
        if beste is None or tag > beste[0]:
            beste = (tag, satz)
    return beste[1] if beste else None


# ------------------------------------------------------------ selbsttest

def selbsttest():
    fehler = 0

    def ok(name, bed, extra=""):
        nonlocal fehler
        print("%-4s %s%s" % ("ok" if bed else "FEHL", name, ("  " + str(extra)) if not bed and extra else ""))
        fehler += 0 if bed else 1

    ok("mindestens 5 bauplaene", len(BAUPLAENE) >= 5 and len(set(BAUPLAENE)) == len(BAUPLAENE))
    for b in ("beobachtung", "vergleich", "einordnung", "pointe", "frage"):
        ok("bauplan %s vorhanden" % b, b in BAUPLAENE)
    # schreibung
    s = schreibung("kaspa miners ran 350 quadrillion hashes every second.\n"
                   "daily average 6 nov 2026, source kaspa rest api.")
    ok("schreibung satzanfang und eigennamen", s == "Kaspa miners ran 350 quadrillion hashes every second.\n"
       "Daily average 6 Nov 2026, source Kaspa REST API.", s)
    s = schreibung("as of 5 nov 2026, counted by kaspa pulse.\n\nWeekly Kaspa numbers in our newsletter, "
                   "link in bio.\n\n#kaspa #kas #blockdag")
    ok("hashtags bleiben klein", s.endswith("#kaspa #kas #blockdag") and s.startswith("As of 5 Nov 2026, counted "
                                                                                       "by Kaspa Pulse."), s)
    s = schreibung("all the weekly numbers in one mail, every monday. https://kaspapulse.com/x")
    ok("links bleiben, wochentag gross", s == "All the weekly numbers in one mail, every Monday. "
       "https://kaspapulse.com/x", s)
    ok("it goes on X at 17:00", "it goes on X at 17:00" in schreibung("share it first, it goes on x at 17:00."))
    ok("KAS, PH/s, UTC, DAA", schreibung("1.23M kas at 12:05 utc, 350 ph/s, the daa score") ==
       "1.23M KAS at 12:05 UTC, 350 PH/s, the DAA score")
    ok("gemischte schreibung bleibt (KAsPa)", "spell KAsPa" in schreibung("together they spell KAsPa"))
    ok("monat vor der jahreszahl", schreibung("blocks since nov 2021") == "Blocks since Nov 2021")
    ok("schreibung ist idempotent", schreibung(schreibung("kaspa on 4 nov 2026. bitcoin too.")) ==
       schreibung("kaspa on 4 nov 2026. bitcoin too."))
    ok("klein faellt auf", bool(klein_verstoesse("kaspa miners ran 350 PH/s on 6 nov.")))
    ok("gross ist sauber", not klein_verstoesse(schreibung("kaspa miners ran 350 PH/s on 6 nov.")))
    # regeln
    gut = "Kaspa miners ran 350 quadrillion hashes every second.\nDaily average 6 Nov 2026, source Kaspa REST API."
    ok("sauberer text ist gruen", not regel_verstoesse(gut, "beobachtung"), regel_verstoesse(gut, "beobachtung"))
    for f in FLOSKELN:
        ok("floskel %r faellt auf, auch gross" % f, bool(regel_verstoesse(gut + " " + f.upper() + ".", "beobachtung")))
    for f in ALTE_FRAGEN:
        ok("alte frage %r faellt auf" % f, bool(regel_verstoesse(gut + "\n" + f.capitalize(), "frage")))
    ok("zwei methoden-woerter fallen auf",
       bool(regel_verstoesse(gut + " Counted by Kaspa Pulse.", "beobachtung")))
    ok("computed und source zusammen fallen auf",
       bool(regel_verstoesse("Reward computed on 4 Nov 2026, source Kaspa REST API.", "beobachtung")))
    ok("frage ohne bauplan frage faellt auf", bool(regel_verstoesse(gut + "\nWho keeps that count?", "pointe")))
    ok("frage mit bauplan frage ist gruen", not regel_verstoesse(gut + "\nWho keeps that count?", "frage"))
    ok("bauplan frage ohne frage faellt auf", bool(regel_verstoesse(gut, "frage")))
    ok("bitcoin ausserhalb vergleich faellt auf", bool(regel_verstoesse(gut + " Bitcoin 5 Nov 2026.", "pointe")))
    ok("bitcoin im vergleich ohne urteil ist gruen",
       not regel_verstoesse(gut + "\nBitcoin averaged 1,000 EH/s on 6 Nov 2026.", "vergleich"))
    ok("werturteil faellt auf",
       bool(regel_verstoesse(gut + "\nBitcoin is slower on 6 Nov 2026.", "vergleich")))
    ok("today faellt auf", bool(regel_verstoesse(gut + " Today.", "beobachtung")))
    ok("for now faellt auf", bool(regel_verstoesse(gut + " For now.", "beobachtung")))
    # das wort wird zusammengesetzt, sonst faende es content_wache im quelltext
    ok("ungenaues mengenwort faellt auf", bool(regel_verstoesse(gut + " A mean" + "ingful step.", "beobachtung")))
    ok("tagesregel, doppelt faellt auf", bool(tag_verstoesse({"x": "pointe", "meme": "pointe"})))
    ok("tagesregel, verschieden ist gruen", not tag_verstoesse({"x": "pointe", "meme": "frage"}))
    # wahl
    d = dt.date(2026, 11, 9)
    st = {"tage": {}}
    texte = {}
    for k in PLATTFORMEN:
        b, t = waehlen(d, k, lambda b: "Kaspa did %s on 9 Nov 2026%s" % (
            b, "?" if b == "frage" else "." if b != "vergleich" else ". Bitcoin did 1 on 9 Nov 2026."), st)
        texte[k] = b
    ok("fuenf kanaele, fuenf verschiedene bauplaene", len(set(texte.values())) == len(PLATTFORMEN), texte)
    ok("x ist kein kanal der stimm-regel", "x" not in PLATTFORMEN)
    ok("der stand traegt alle sechs", st["tage"]["2026-11-09"] == texte)
    b2, _ = waehlen(d, "threads", lambda b: "Kaspa did %s on 9 Nov 2026." % b if b != "frage" else
                    "Kaspa did it on 9 Nov 2026?", st)
    ok("zweiter lauf am selben tag bekommt denselben bauplan", b2 == texte["threads"])
    st2 = {"tage": {}}
    a = [waehlen(d, k, lambda b: "Kaspa did %s on 9 Nov 2026." % b if b != "frage" else "Did it?", st2)[0]
         for k in ("instagram", "threads", "discord")]
    st3 = {"tage": {}}
    a3 = [waehlen(d, k, lambda b: "Kaspa did %s on 9 Nov 2026." % b if b != "frage" else "Did it?", st3)[0]
          for k in ("instagram", "threads", "discord")]
    ok("die wahl ist deterministisch", a == a3, (a, a3))
    ok("ohne bitcoin-zahl kein vergleich", "vergleich" not in a)
    tage = [d + dt.timedelta(days=i) for i in range(28)]
    fragen = sum(1 for t in tage if frage_kanal(t))
    ok("frage nur gelegentlich, %d von 28 tagen vorn" % fragen, 0 < fragen <= 28 // FRAGE_TAKT + 1)
    erste = {reihenfolge(t, "threads")[0] for t in tage}
    ok("der erste bauplan wechselt ueber die tage (%s)" % ", ".join(sorted(erste)), len(erste) >= 5)
    voll = {"tage": {"2026-11-09": {"threads": "beobachtung"}}}
    try:
        waehlen(d, "meme", lambda b: "Kaspa did it on 9 Nov 2026." if b == "beobachtung" else None, voll)
        ok("kein freier bauplan stoppt", False)
    except StimmeStopp:
        ok("kein freier bauplan stoppt", True)
    # saetze
    z = saetze("datum_voran", "kaspa miners ran 350 quadrillion hashes every second", "x",
               herkunft="source kaspa rest api hashrate", stand="6 nov 2026")
    ok("datum voran", schreibung(" ".join(z)) == "On 6 Nov 2026, Kaspa miners ran 350 quadrillion hashes every "
       "second. Source Kaspa REST API hashrate.", z)
    ok("einordnung ohne satz geht nicht", saetze("einordnung", "a", "b") == [])
    ok("frage ohne fragezeichen geht nicht", saetze("frage", "a", "b", frage="who") == [])
    # bitcoin-zahl
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "b.json"
        p.write_text(json.dumps({"zahlen": [
            {"kennzahl": "x", "datum": "2026-11-06", "satz": "bitcoin added 144 blocks on 6 nov 2026"},
            {"kennzahl": "x", "datum": "2026-10-20", "satz": "bitcoin added 140 blocks on 20 oct 2026"},
            {"kennzahl": "y", "datum": "2026-11-06", "satz": "bitcoin is slower on 6 nov 2026"}]}))
        ok("bitcoin-zahl, juengste passende", bitcoin_zahl("x", "2026-11-07", p) ==
           "bitcoin added 144 blocks on 6 nov 2026")
        ok("bitcoin-zahl, zu alt faellt weg", bitcoin_zahl("x", "2026-11-30", p) is None)
        ok("bitcoin-zahl mit werturteil faellt weg", bitcoin_zahl("y", "2026-11-07", p) is None)
        ok("ohne datei keine bitcoin-zahl", bitcoin_zahl("x", "2026-11-07", Path(tmp) / "fehlt.json") is None)
        sp = Path(tmp) / "s.json"
        schreiben({"tage": {"2026-09-01": {"x": "pointe"}, "2026-11-09": {"x": "frage"}}}, sp, "2026-11-09")
        ok("stand haelt nur 30 tage", lesen(sp) == {"tage": {"2026-11-09": {"x": "frage"}}})
    q = floskeln_im_quelltext()
    ok("keine floskel im quelltext der textskripte (%s)" % q, not q)
    print("%d fehler" % fehler)
    return 1 if fehler else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--pruefen", action="store_true")
    ap.add_argument("--text", default="")
    ap.add_argument("--bauplan", default=None)
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.pruefen:
        aus = regel_verstoesse(a.text, a.bauplan)
        print("\n".join(aus) if aus else "gruen")
        return 1 if aus else 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
