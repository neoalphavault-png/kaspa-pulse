"""Bericht berichte/2026-11-21-wochenbericht-1.md aus zahlen.json und den Texten."""
import json, sys, subprocess
z = json.load(open(sys.argv[1])); site_pr = sys.argv[2]; aus = sys.argv[3]
texte = subprocess.run([sys.executable, sys.argv[0].replace("bericht.py", "texte.py"), sys.argv[1]], capture_output=True, text=True).stdout
blocks = {}
for teil in texte.split("== ")[1:]:
    kopf, txt = teil.split("\n", 1); blocks[kopf.split(",")[0]] = (kopf, txt.strip())
zc, bc, bm = z["zcash"], z["bch"], z["bch_mainnet_computed"]
def d(s):
    s = int(round(s)); h, r = divmod(s, 3600); m, x = divmod(r, 60)
    return " ".join((["%d h" % h] if h else []) + (["%d min" % m] if h or m else []) + ["%d s" % x])
n = lambda x: "{:,}".format(x).replace(",", ".")
pz = lambda x: ("%s" % x).replace(".", ",")
lz = zc["zuhoerer"]; lb = bc["zuhoerer"]
def luecken(g): return "keine, die Läufe überlappen" if not g else "; ".join("%s bis %s UTC (%s)" % (a, b, d(s)) for a, b, s in g)
rate = 100.0 * lz["abgehaengt"] / (lz["kettenbloecke"] + lz["abgehaengt"])
zeilen = []
def zl(was, wert, art, datei, commit, stich): zeilen.append("| %s | %s | %s | `%s` | `%s` | %s |" % (was, wert, art, datei, commit.split()[0], stich))
kz, kb, zz, zb = zc["koepfe"], bc["koepfe"], lz, lb
zl("Zcash, Kettenblöcke beim Zuhörer", n(lz["kettenbloecke"]), "counted", zz["datei"], zz["commit"], "%s bis %s" % (lz["fenster"][0], lz["fenster"][1]))
zl("Zcash, verwaiste Blöcke (untere Grenze)", "%s (%s %%), davon %s ohne Kopf, Tiefe höchstens %s" % (n(lz["abgehaengt"]), pz(round(rate, 2)), lz["ohne_kopf"], lz["groesste_tiefe"]), "counted", zz["datei"], zz["commit"], "wie oben")
zl("Zcash, Blockabstände", "%s, Median %s, Mittel %s s" % (n(zc["abstaende"]), d(zc["median_s"]), pz(zc["mittel_s"])), "counted", kz["datei"], kz["commit"], "%s bis %s UTC, Abruf %s" % (zc["fenster"][0], zc["fenster"][1], kz["abruf_utc"]))
zl("Zcash, Anteil über 75 s", "%s %%" % pz(zc["ueber75_prozent"]), "counted", kz["datei"], kz["commit"], "wie oben")
for k in (1, 3, 6):
    zl("Zcash, Wartezeit %d Bestätigungen, üblich / 9 von 10" % k, "%s / %s" % (d(zc["warten_%d" % k]["median_s"]), d(zc["warten_%d" % k]["p90_s"])), "counted", kz["datei"], kz["commit"], "wie oben")
for k in (1, 3, 6):
    zl("Zcash, ideale 25-s-Kette, %d Bestätigungen" % k, "%s / %s" % (d(z["zcash_computed_25s"][str(k)]["0.5"]), d(z["zcash_computed_25s"][str(k)]["0.9"])), "computed", "Erlang, Mittel 25 s", "-", "-")
zl("BCH Chipnet, Aktivierungshöhe", n(bc["aktivierung"]), "counted", kb["datei"], kb["commit"], "MTP-Regel, Abruf %s" % kb["abruf_utc"])
zl("BCH Chipnet, Abstände seit Aktivierung", "%s, Median %s, Mittel %s s" % (n(bc["abstaende"]), d(bc["median_s"]), pz(bc["mittel_s"])), "counted", kb["datei"], kb["commit"], "%s bis %s UTC" % (bc["seit"], bc["bis"]))
zl("BCH Chipnet, Anteil Difficulty 1", "%s %% (%s Blöcke)" % (pz(bc["diff1_prozent"]), n(bc["diff1"])), "counted", kb["datei"], kb["commit"], "wie oben")
for k in (1, 3, 6, 12):
    w = bc["warten_%d" % k]
    zl("BCH Chipnet, Wartezeit %d Bestätigungen nach Ankunft, üblich / 9 von 10 / 99 von 100" % k, "%s / %s / %s (Kopfzeit %s / %s)" % (d(w["median_s"]), d(w["p90_s"]), d(w["p99_s"]), d(w["kopfzeit_median_s"]), d(w["kopfzeit_p90_s"])), "counted", lb["datei"], lb["commit"], "%s bis %s UTC" % (lb["von"], lb["bis"]))
for k in (1, 3, 6, 12):
    zl("BCH Mainnet, %d Bestätigungen, üblich / 9 von 10 / 99 von 100" % k, "%s / %s / %s" % (d(bm[str(k)]["0.5"]), d(bm[str(k)]["0.9"]), d(bm[str(k)]["0.99"])), "computed", "Erlang, Mittel 600 s", "-", "-")
tab = "\n".join(["| Zahl | Wert | Art | Datei | Commit | Stichzeit oder Fenster (UTC) |", "|---|---|---|---|---|---|"] + zeilen)
txt = open(sys.argv[0].replace("bericht.py", "bericht_rahmen.md")).read()
txt = txt.format(tab=tab, site_pr=site_pr,
  zl=luecken(zc["luecken"]), zl_n=zc["laeufe"], bl=luecken(bc["luecken"]), bl_n=bc["laeufe"],
  zcash_kopf=blocks["zcash_59124"][0], zcash=blocks["zcash_59124"][1], bch_kopf=blocks["bch_2173"][0], bch=blocks["bch_2173"][1],
  x_kopf=blocks["x"][0], x=blocks["x"][1], z_bis=zc["fenster"][1], l_bis=lz["fenster"][1],
  z_orph=n(lz["abgehaengt"]), z_chain=n(lz["kettenbloecke"]), b6=d(bc["warten_6"]["median_s"]), b12=d(bc["warten_12"]["median_s"]))
open(aus, "w").write(txt)
