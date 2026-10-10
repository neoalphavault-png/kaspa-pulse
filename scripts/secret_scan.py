#!/usr/bin/env python3
"""secret_scan.py - sucht Schluessel, Tokens und Secrets in Dateien und Commits.

Regel (Ben, 02.10.2026): Keine Schluessel, Tokens oder Secrets im Chat und nie
in einer Datei im Repo. Sie liegen nur in GitHub Secrets und werden aus der
Umgebung gelesen.

Anlass: Am 30.09.2026 standen OAuth-Werte im Klartext in scripts/x_post.py.
GitHubs Secret-Scanning meldete 0 Alerts. Deshalb dieser eigene Check mit
unseren Mustern.

Der Scanner gibt NIE einen gefundenen Wert aus. Er nennt Datei, Zeile, Art
und einen Fingerabdruck (die ersten 12 Zeichen von sha256 des Treffers).
Am Fingerabdruck erkennt man denselben Treffer an mehreren Stellen wieder.

  python3 scripts/secret_scan.py --staged           # pre-commit
  python3 scripts/secret_scan.py --bereich A..B     # CI, neue Commits
  python3 scripts/secret_scan.py --neu-gegen REF    # alle Commits nicht in REF
  python3 scripts/secret_scan.py --baum             # alle Dateien im Checkout
  python3 scripts/secret_scan.py --historie         # jede Dateiversion aller Branches
  python3 scripts/secret_scan.py --selbsttest

Exit 1, sobald etwas gefunden ist. Ausnahmen nur ueber Fingerabdruecke in
.secret-scan-allow (eine Zeile je Ausnahme, mit Begruendung), nie ueber den
Wert selbst.
"""
import argparse
import fnmatch
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ALLOW = REPO / ".secret-scan-allow"

# (art, muster). Die Reihenfolge zaehlt: ein spezielles Muster schlaegt das
# allgemeine. Eine Stelle, die schon getroffen ist, wird nicht doppelt gezaehlt.
MUSTER = [
    ("privater schluessel", r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
    ("google service account", r'"type"\s*:\s*"service_account"'),
    ("google oauth client-id", r"\b\d{6,}-[a-z0-9]{32}\.apps\.googleusercontent\.com\b"),
    ("google oauth client-secret", r"\bGOCSPX-[A-Za-z0-9_\-]{20,}"),
    ("google api-key (youtube)", r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    ("google refresh-token", r"\b1//0[0-9A-Za-z_\-]{30,}"),
    ("google access-token", r"\bya29\.[0-9A-Za-z_\-]{20,}"),
    ("brevo api-key", r"\bxkeysib-[a-f0-9]{64}-[A-Za-z0-9]{16}\b"),
    ("brevo smtp-key", r"\bxsmtpsib-[a-f0-9]{64}-[A-Za-z0-9]{16}\b"),
    ("discord webhook", r"https?://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\d{15,22}/[A-Za-z0-9_\-]{30,}"),
    ("telegram bot-token", r"\b\d{8,10}:AA[A-Za-z0-9_\-]{30,}\b"),
    ("github token", r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})\b"),
    ("slack token", r"\bxox[abposr]-[A-Za-z0-9\-]{10,}"),
    ("anthropic key", r"\bsk-ant-[A-Za-z0-9_\-]{20,}"),
    ("openai key", r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{32,}"),
    ("x access-token", r"\b[1-9]\d{5,19}-[A-Za-z0-9]{20,60}\b"),
    ("x bearer-token", r"\bAAAAAAAAAAAAAAAAAAAAA[A-Za-z0-9%]{30,}"),
    # Kaspa (Ben, 03.10.2026, vor dem Experiment "100 Zahlungen"). Ein
    # privater Schluessel ist 64 Hex wie eine Tx-ID, deshalb nur mit Namen
    # oder im Aufruf PrivateKey(...). Erweiterte Schluessel (xprv/kprv) sehen
    # nach nichts anderem aus.
    ("kaspa privater schluessel", r"""(?ix)
        ["']?[a-z0-9_\-]*(?:priv|private|seed|wif)[a-z0-9_\-]*["']?
        \s*[:=]\s*["']?([0-9a-f]{64})\b"""),
    ("kaspa privater schluessel", r"""(?i)PrivateKey\(\s*["']([0-9a-f]{64})["']"""),
    ("erweiterter privater schluessel", r"\b((?:xprv|kprv|tprv|ktrv)[1-9A-HJ-NP-Za-km-z]{100,112})\b"),
    # Zuweisung an einen Namen mit key/secret/token/password, in Python,
    # YAML, JSON, JS oder Shell. Der Wert muss nach Zufall aussehen.
    ("zuweisung key/secret/token", r"""(?ix)
        ["']?[a-z0-9_\-]*(?:api[_\-]?key|apikey|secret|token|passw(?:or)?d|consumer[_\-]?key|access[_\-]?key)[a-z0-9_\-]*["']?
        \s*[:=]\s*
        ["']([A-Za-z0-9/+_=\-\.]{16,})["']"""),
]
KOMP = [(a, re.compile(m)) for a, m in MUSTER]

# Dateinamen, die nie ins Repo gehoeren, egal was drinsteht.
VERBOTENE_NAMEN = [".env", ".env.*", "*.key", "*.pem", "*.p12", "*.pfx", "id_rsa", "id_ed25519",
                   "credentials*.json", "token*.json", "client_secret*.json", "service-account*.json"]
ERLAUBTE_NAMEN = [".env.example", ".env.beispiel"]

MAX_BYTES = 5_000_000


def zufaellig(wert):
    """Ein echter Schluessel mischt Buchstaben und Ziffern. Ein Platzhalter wie
    'DEIN_TOKEN_HIER' oder ein Dateiname nicht."""
    if not wert or len(wert) < 16:
        return False
    if wert.startswith("${") or wert.startswith("$("):
        return False
    hat_ziffer = any(c.isdigit() for c in wert)
    hat_buchstabe = any(c.isalpha() for c in wert)
    if not (hat_ziffer and hat_buchstabe):
        return False
    if re.fullmatch(r"[A-Za-z0-9_\-]+\.(?:py|js|json|yml|yaml|html|md|png|txt|csv|gz)", wert):
        return False
    return len(set(wert)) >= 10


def fingerabdruck(wert):
    return hashlib.sha256(wert.encode("utf-8", "replace")).hexdigest()[:12]


def erlaubt():
    if not ALLOW.exists():
        return set()
    fp = set()
    for z in ALLOW.read_text(encoding="utf-8").splitlines():
        z = z.split("#", 1)[0].strip()
        if re.fullmatch(r"[0-9a-f]{12}", z):
            fp.add(z)
    return fp


def name_verboten(pfad):
    n = os.path.basename(pfad)
    if any(fnmatch.fnmatch(n, e) for e in ERLAUBTE_NAMEN):
        return False
    return any(fnmatch.fnmatch(n, v) for v in VERBOTENE_NAMEN)


# Seed-Woerter: 12 oder mehr Woerter der BIP39-Liste in Folge, auch ueber
# Zeilen ("1. abandon", "2. ability" ...). Zahlen und Satzzeichen zaehlen
# nicht, jedes andere Wort bricht die Folge. "the", "and", "of" stehen nicht
# auf der Liste, deshalb kommt normaler Text kaum auf 12.
SEED_LISTE = Path(__file__).resolve().parent / "bip39_english.txt"
SEED_MIN = 12
_SEED = set()
# Die Liste selbst ist die einzige Datei, die 2048 Seed-Woerter am Stueck
# enthaelt. Sie ist ausgenommen und dafuer im Selbsttest per sha256 an die
# offizielle BIP39-Liste gebunden, damit sich darin kein Seed verstecken kann.
SEED_LISTE_REPO = "scripts/bip39_english.txt"
BIP39_LISTE_PRUEFSUMME = "2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda"


def seed_woerter():
    if not _SEED and SEED_LISTE.exists():
        _SEED.update(SEED_LISTE.read_text(encoding="utf-8").split())
    return _SEED


class SeedLauf:
    """Zaehlt Seed-Woerter in Folge ueber Zeilen. zeile() gibt den
    Fingerabdruck zurueck, sobald eine Folge 12 Woerter erreicht, einmal je
    Folge, sonst None. Der Fingerabdruck ist der der ganzen Folge bis dahin;
    die Woerter selbst verlassen die Klasse nie."""

    def __init__(self):
        self.woerter, self.start, self.gemeldet = [], 0, False

    def zeile(self, nr, text):
        liste = seed_woerter()
        if not liste:
            return None
        treffer = None
        for w in re.findall(r"[A-Za-z]+", text):
            w = w.lower()
            if w in liste:
                if not self.woerter:
                    self.start, self.gemeldet = nr, False
                self.woerter.append(w)
                if len(self.woerter) >= SEED_MIN and not self.gemeldet:
                    self.gemeldet = True
                    treffer = (self.start, fingerabdruck(" ".join(self.woerter)))
            else:
                self.woerter = []
        return treffer


def zeile_pruefen(text):
    """Liste von (art, fingerabdruck) fuer eine Zeile. Gibt keine Werte zurueck."""
    funde, belegt = [], []
    for art, rx in KOMP:
        for m in rx.finditer(text):
            a, b = m.span()
            if any(a < y and x < b for x, y in belegt):
                continue
            wert = m.group(1) if m.groups() and m.group(1) else m.group(0)
            if art.startswith("zuweisung") and not zufaellig(wert):
                continue
            belegt.append((a, b))
            funde.append((art, fingerabdruck(wert)))
    return funde


def text_pruefen(pfad, text, ok):
    funde, lauf = [], SeedLauf()
    if pfad.endswith(SEED_LISTE_REPO):
        lauf = None
    for nr, z in enumerate(text.splitlines(), 1):
        if len(z) > 20000:
            z = z[:20000]
        for art, fp in zeile_pruefen(z):
            if fp not in ok:
                funde.append((pfad, nr, art, fp))
        s = lauf.zeile(nr, z) if lauf else None
        if s and s[1] not in ok:
            funde.append((pfad, s[0], "seed-woerter", s[1]))
    return funde


def ist_binaer(daten):
    return b"\0" in daten[:8000]


def git(*args, binaer=False):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True)
    if r.returncode:
        raise SystemExit("git %s: %s" % (" ".join(args[:3]), r.stderr.decode()[-300:]))
    return r.stdout if binaer else r.stdout.decode("utf-8", "replace")


# ------------------------------------------------- Wache gegen ubuntu-latest
# Ben, 10.10.2026. "ubuntu-latest" wandert ab dem 19.10.2026 auf Ubuntu 26
# und wuerde uns mitten im Betrieb ein neues Image unterschieben: Playwright
# braucht andere Systempakete, das Pillow-Rad muss es erst geben, apt-Pakete
# heissen anders. Alle Workflows sind darum auf ubuntu-24.04 gepinnt. Diese
# Wache haelt das fest, damit es nicht beim naechsten neuen Workflow
# zurueckfaellt. Begruendung: docs/runner-image.md in kaspa-pulse.
#
# Kein Secret, deshalb kein Fingerabdruck und keine Ausnahme ueber
# .secret-scan-allow - die Zeile ist einfach falsch oder nicht da.
WF_ORDNER = ".github/workflows/"
WF_ART = "ubuntu-latest statt gepinntem image"
# Nur echte runs-on-Zeilen. Ein Kommentar oder eine Doku, die ubuntu-latest
# erwaehnt, ist in Ordnung - sonst koennte man es nicht mehr erklaeren.
_WF_LATEST = re.compile(r"""runs-on:\s*\[?\s*["']?ubuntu-latest""")


def in_workflows(pfad):
    return (pfad or "").replace("\\", "/").startswith(WF_ORDNER)


def workflow_zeile(pfad, zeile):
    """True, wenn diese Zeile in dieser Datei ubuntu-latest festlegt."""
    return bool(in_workflows(pfad) and _WF_LATEST.search(zeile))


def diff_pruefen(diff, ok, quelle):
    """Nur hinzugefuegte Zeilen eines Diffs. Zeilennummer in der neuen Datei."""
    funde, pfad, nr, lauf = [], None, 0, SeedLauf()
    for z in diff.splitlines():
        if z.startswith("+++ "):
            pfad = z[6:] if z.startswith("+++ b/") else None
            lauf = None if pfad == SEED_LISTE_REPO else SeedLauf()
            if pfad and name_verboten(pfad):
                funde.append((pfad, 0, "verbotener dateiname", "-"))
            continue
        m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", z)
        if m:
            nr = int(m.group(1))
            lauf = None if pfad == SEED_LISTE_REPO else SeedLauf()
            continue
        if pfad is None:
            continue
        if z.startswith("+"):
            if workflow_zeile(pfad, z[1:]):
                funde.append((pfad, nr, WF_ART, "-"))
            for art, fp in zeile_pruefen(z[1:]):
                if fp not in ok:
                    funde.append((pfad, nr, art, fp))
            s = lauf.zeile(nr, z[1:]) if lauf else None
            if s and s[1] not in ok:
                funde.append((pfad, s[0], "seed-woerter", s[1]))
            nr += 1
        elif not z.startswith("-"):
            nr += 1
    return [(f"{quelle} {p}", n, a, fp) for p, n, a, fp in funde]


def commits_pruefen(commits, ok):
    funde = []
    for c in commits:
        diff = git("show", "--format=", "-U0", "--no-color", "--no-ext-diff", c)
        funde += diff_pruefen(diff, ok, c[:7])
    return funde


def baum_pruefen(ok, dateien=None):
    funde = []
    namen = dateien or [p for p in git("ls-files", "-z").split("\0") if p]
    for p in namen:
        if name_verboten(p):
            funde.append((p, 0, "verbotener dateiname", "-"))
        f = REPO / p
        if not f.is_file() or f.stat().st_size > MAX_BYTES:
            continue
        daten = f.read_bytes()
        if ist_binaer(daten):
            continue
        text = daten.decode("utf-8", "replace")
        if in_workflows(p):
            funde += [(p, i, WF_ART, "-") for i, z in enumerate(text.splitlines(), 1)
                      if _WF_LATEST.search(z)]
        funde += text_pruefen(p, text, ok)
    return funde


def historie_pruefen(ok):
    """Jede Dateiversion, die von irgendeinem Branch oder Tag erreichbar ist.
    Zu jedem Treffer: der Commit, der die Version eingefuehrt hat, und die
    Branches, deren Spitze sie heute noch enthaelt."""
    pfade = {}
    for z in git("rev-list", "--objects", "--all").splitlines():
        teile = z.split(" ", 1)
        if len(teile) == 2:
            pfade.setdefault(teile[0], set()).add(teile[1])
    typen = git("cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
                "--batch-all-objects").splitlines()
    blobs = [z.split()[0] for z in typen
             if z.split()[1] == "blob" and int(z.split()[2]) <= MAX_BYTES and z.split()[0] in pfade]
    funde = []
    for b in blobs:
        for p in pfade[b]:
            if name_verboten(p):
                funde.append((b, p, 0, "verbotener dateiname", "-"))
        daten = git("cat-file", "blob", b, binaer=True)
        if ist_binaer(daten):
            continue
        for p in sorted(pfade[b])[:1]:
            for _, nr, art, fp in text_pruefen(p, daten.decode("utf-8", "replace"), ok):
                funde.append((b, p, nr, art, fp))
    if not funde:
        return []
    spitzen = {}
    for ref in git("for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes").split():
        if ref.endswith("/HEAD"):
            continue
        spitzen[ref] = set(git("ls-tree", "-r", "--format=%(objectname)", ref).split())
    aus = []
    for b, p, nr, art, fp in funde:
        erst = git("log", "--all", "--format=%h %ad", "--date=short", "--find-object=" + b).split("\n")
        erst = [e for e in erst if e]
        drin = sorted(r for r, s in spitzen.items() if b in s)
        aus.append((p, nr, art, fp, erst[-1] if erst else "?", drin))
    return aus


def melden(funde, titel):
    if not funde:
        print("secret-scan: %s, nichts gefunden" % titel)
        return 0
    print("secret-scan: %s, %d fund(e). Werte werden nie gezeigt." % (titel, len(funde)))
    for f in funde:
        if len(f) == 4:
            p, nr, art, fp = f
            print("  %s:%s  %s  fp=%s" % (p, nr, art, fp))
        else:
            p, nr, art, fp, erst, drin = f
            print("  %s:%s  %s  fp=%s  eingefuehrt %s  heute auf %s"
                  % (p, nr, art, fp, erst, ", ".join(drin) if drin else "keiner branch-spitze"))
    if any(f[2] != WF_ART for f in funde):
        print("\nNicht pushen. Den Wert aus der Datei nehmen, als GitHub Secret ablegen und")
        print("im Code aus der Umgebung lesen (os.environ). War er schon auf GitHub, gilt er")
        print("als verbrannt und wird neu erzeugt.")
    if any(f[2] == WF_ART for f in funde):
        print("\nKein Secret, aber auch nicht erwuenscht: runs-on gehoert auf ein gepinntes")
        print("Image, runs-on: ubuntu-24.04. ubuntu-latest wandert ab dem 19.10.2026 auf")
        print("Ubuntu 26. Begruendung: docs/runner-image.md in kaspa-pulse.")
    if os.environ.get("GITHUB_ACTIONS"):
        for f in funde:
            print("::error file=%s,line=%s::secret-scan %s (fp=%s)" % (
                str(f[0]).split(" ")[-1], max(int(f[1]), 1), f[2], f[3]))
    return 1


def selbsttest():
    fehler = 0

    def ok(name, bed):
        nonlocal fehler
        print("%-4s %s" % ("ok" if bed else "FEHL", name))
        fehler += 0 if bed else 1

    # Erfundene Werte, zur Laufzeit zusammengesetzt, damit diese Datei selbst
    # keinen Treffer enthaelt.
    erfunden = {
        "x access-token": "1234567890" + "-" + "TestOnlyNotARealToken" + "0123456789abc",
        "brevo api-key": "xkeysib" + "-" + "0" * 64 + "-" + "TestOnly12345678",
        "discord webhook": "https://discord.com/api/web" + "hooks/" + "123456789012345678/" + "T" * 40,
        "google api-key (youtube)": "AI" + "za" + "T" * 35,
        "google oauth client-secret": "GOC" + "SPX-" + "TestOnly" + "x" * 20,
        "telegram bot-token": "123456789" + ":AA" + "T" * 33,
        "github token": "gh" + "p_" + "T" * 36,
        "privater schluessel": "-----BEGIN " + "RSA PRIVATE KEY-----",
    }
    for art, wert in erfunden.items():
        f = zeile_pruefen('x = "%s"' % wert)
        ok("%s wird erkannt" % art, any(a == art for a, _ in f))
        ok("%s, ausgabe enthaelt den wert nicht" % art, all(wert not in str(x) for x in f))
    zuw = 'X_API_SECRET = "' + "Ab3dEf5hIj7lMn9pQr1tUv3xYz5" + '"'
    ok("zuweisung an *_SECRET wird erkannt", any(a.startswith("zuweisung") for a, _ in zeile_pruefen(zuw)))
    for harmlos in ('X_API_KEY = os.environ["X_API_KEY"]',
                    'token: ${{ secrets.X_ACCESS_TOKEN }}',
                    'ENV = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")',
                    '"token_file": "entity_x_state.json"',
                    'secret = "DEIN_SECRET_HIER_EINTRAGEN"',
                    'tx 65f120cf8cbeec472a20f283c5da84d3d9a4ac775c8326c7a1871c8a4a924964',
                    'kaspa:qpz2vgvlxhmyhmt22h538pjzmvvd52nuut80y5zulgpvyerlskvvwm7n4uk5a',
                    'datum 2026-09-30 um 17:00 berlin, 2026-10-01T11:44:23Z'):
        ok("harmlos bleibt still: %s" % harmlos[:40], zeile_pruefen(harmlos) == [])
    ok(".env ist verboten", name_verboten("config/.env"))
    ok("credentials.json ist verboten", name_verboten("credentials.json"))
    ok("token_youtube.json ist verboten", name_verboten("token_youtube.json"))
    ok(".env.example ist erlaubt", not name_verboten(".env.example"))
    diff = ("+++ b/scripts/neu.py\n@@ -0,0 +1,2 @@\n+a = 1\n+tok = \"%s\"\n" % erfunden["x access-token"])
    f = diff_pruefen(diff, set(), "abc1234")
    ok("diff, zeile 2 in scripts/neu.py", len(f) == 1 and f[0][1] == 2 and f[0][0].endswith("scripts/neu.py"))
    # kaspa (Ben, 03.10.2026). Werte zur Laufzeit gebaut, nie echte.
    hexwert = "0f" * 32
    for zeile in ('KASPA_TESTWALLET_PRIVKEY = "%s"' % hexwert,
                  'private_key: %s' % hexwert,
                  'k = PrivateKey("%s")' % hexwert,
                  '{"seed": "%s"}' % hexwert):
        f = zeile_pruefen(zeile)
        ok("kaspa-schluessel erkannt: %s" % zeile[:24], any(a == "kaspa privater schluessel" for a, _ in f)
           and all(hexwert not in str(x) for x in f))
    ok("kprv erkannt", any(a == "erweiterter privater schluessel"
                           for a, _ in zeile_pruefen("x = kprv" + "T" * 107)))
    for harmlos in ('tx_id = "%s"' % hexwert, 'transaction_id: %s' % hexwert,
                    'priv = os.environ["KASPA_TESTWALLET_PRIVKEY"]',
                    'KASPA_TESTWALLET_PRIVKEY: ${{ secrets.KASPA_TESTWALLET_PRIVKEY }}'):
        ok("harmlos bleibt still: %s" % harmlos[:40], zeile_pruefen(harmlos) == [])
    liste = sorted(seed_woerter())
    ok("bip39-liste geladen, 2048 woerter", len(liste) == 2048)
    ok("bip39-liste ist die offizielle (sha256)",
       hashlib.sha256(SEED_LISTE.read_bytes()).hexdigest() == BIP39_LISTE_PRUEFSUMME)
    ok("die liste selbst ist ausgenommen", text_pruefen(SEED_LISTE_REPO, SEED_LISTE.read_text(), set()) == [])
    zwoelf = [liste[i * 170] for i in range(12)]
    f = text_pruefen("s.txt", "a = 1\nseed: %s\n" % " ".join(zwoelf), set())
    ok("12 seed-woerter in einer zeile", [(n, a) for _, n, a, _ in f] == [(2, "seed-woerter")]
       and all(w not in str(f) for w in zwoelf))
    f = text_pruefen("s.md", "\n".join("%d. %s" % (i + 1, w) for i, w in enumerate(zwoelf)), set())
    ok("12 seed-woerter als nummerierte liste, treffer auf zeile 1", [(n, a) for _, n, a, _ in f]
       == [(1, "seed-woerter")])
    f = text_pruefen("s.txt", " ".join(zwoelf[:11]), set())
    ok("11 woerter sind noch kein seed", f == [])
    diff = "+++ b/n.txt\n@@ -0,0 +1,12 @@\n" + "".join("+%s\n" % w for w in zwoelf)
    ok("seed im diff ueber zeilen", [a for _, _, a, _ in diff_pruefen(diff, set(), "abc1234")] == ["seed-woerter"])
    for satz in ("The miners earned more in new coins than in fees over the last thirty days.",
                 "kaspa cuts its block reward again in two days, once a month, and twelve steps halve it",
                 "Die Rotation hat Form 3 zum zweiten Tag in Folge gewaehlt, das ist gegen die Wochenregel."):
        ok("text bleibt still: %s" % satz[:30], text_pruefen("t.md", satz, set()) == [])
    # Wache gegen ubuntu-latest (Ben, 10.10.2026)
    wf = ".github/workflows/beispiel.yml"
    ok("ubuntu-latest in einem workflow wird gefangen",
       workflow_zeile(wf, "    runs-on: ubuntu-latest"))
    ok("auch in anfuehrungszeichen und als liste",
       workflow_zeile(wf, 'runs-on: "ubuntu-latest"')
       and workflow_zeile(wf, "runs-on: [ubuntu-latest]"))
    ok("gepinntes image bleibt still", not workflow_zeile(wf, "    runs-on: ubuntu-24.04"))
    ok("ein kommentar darf ubuntu-latest nennen",
       not workflow_zeile(wf, "      # frueher stand hier ubuntu-latest"))
    ok("eine doku darf ubuntu-latest nennen",
       not workflow_zeile("docs/runner-image.md", "`ubuntu-latest` wandert auf Ubuntu 26"))
    ok("ausserhalb von .github/workflows zaehlt es nicht",
       not workflow_zeile("deploy/beispiel.yml", "runs-on: ubuntu-latest"))
    print("%d fehler" % fehler)
    return 1 if fehler else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--staged", action="store_true")
    g.add_argument("--bereich")
    g.add_argument("--neu-gegen")
    g.add_argument("--baum", action="store_true")
    g.add_argument("--historie", action="store_true")
    g.add_argument("--dateien", nargs="+")
    g.add_argument("--selbsttest", action="store_true")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    ok = erlaubt()
    if a.staged:
        diff = git("diff", "--cached", "-U0", "--no-color", "--no-ext-diff")
        return melden(diff_pruefen(diff, ok, "staged"), "vorgemerkte aenderungen")
    if a.bereich:
        commits = [c for c in git("rev-list", a.bereich).split() if c]
        return melden(commits_pruefen(commits, ok), "%d commit(s) in %s" % (len(commits), a.bereich))
    if a.neu_gegen:
        commits = [c for c in git("rev-list", "HEAD", "--not", a.neu_gegen).split() if c]
        return melden(commits_pruefen(commits, ok), "%d commit(s) nicht in %s" % (len(commits), a.neu_gegen))
    if a.baum:
        return melden(baum_pruefen(ok), "alle dateien im checkout")
    if a.dateien:
        return melden(baum_pruefen(ok, a.dateien), "%d datei(en)" % len(a.dateien))
    return melden(historie_pruefen(ok), "historie aller branches")


if __name__ == "__main__":
    sys.exit(main())
