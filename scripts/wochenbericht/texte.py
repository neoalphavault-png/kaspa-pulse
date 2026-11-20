"""Forum- und X-Texte aus zahlen.json, mit Wortzahl. Englisch, Textregeln."""
import json, sys, datetime as dt
z = json.load(open(sys.argv[1])); zc, bc, bm = z["zcash"], z["bch"], z["bch_mainnet_computed"]
def d(s):
    s = int(round(s)); m, x = divmod(s, 60)
    return ("%d min %d s" % (m, x)) if m else ("%d s" % x)
def tag(s):  # '2026-11-20 14:11:00' -> '20 Nov 14:11 utc'
    t = dt.datetime.strptime(s[:16].replace("T", " "), "%Y-%m-%d %H:%M"); return "%d %s %s utc" % (t.day, t.strftime("%b"), t.strftime("%H:%M"))
n = lambda x: "{:,}".format(x)
lz = zc["zuhoerer"]
zt = ("Our weekly count, as promised. From the start of our current listener series at %s to %s our listener counted %s orphaned blocks next to %s chain blocks, "
      "one vantage point, so read it as a lower bound. Our headers to %s give a median block interval of %s, and %s %% of intervals ran longer than 75 s. "
      "Three blocks usually took %s, six blocks %s, and 9 of 10 times six blocks came within %s. "
      "@dismad would a weekly line like this help you plan, or is another number more useful?") % (
      tag(lz["fenster"][0]), tag(lz["fenster"][1]), n(lz["abgehaengt"]), n(lz["kettenbloecke"]), tag(zc["fenster"][1]), d(zc["median_s"]), zc["ueber75_prozent"],
      d(zc["warten_3"]["median_s"]), d(zc["warten_6"]["median_s"]), d(zc["warten_6"]["p90_s"]))
bt = ("Waiting times on chipnet with one minute blocks, from the first sighting of each block at our listener, %s to %s, blocks %s to %s. "
      "One confirmation usually took %s, three %s, six %s, and twelve %s. Nine of ten times six blocks arrived within %s, and 99 of 100 times within %s. "
      "Of the blocks since the activation at %s, %s %% carry difficulty 1, and they are part of every wait. "
      "For mainnet at 600 s, six blocks would usually take %s, computed, not counted.") % (
      tag(bc["zuhoerer"]["von"]), tag(bc["zuhoerer"]["bis"]), n(bc["zuhoerer"]["hoehen"][0]), n(bc["zuhoerer"]["hoehen"][1]),
      d(bc["warten_1"]["median_s"]), d(bc["warten_3"]["median_s"]), d(bc["warten_6"]["median_s"]), d(bc["warten_12"]["median_s"]),
      d(bc["warten_6"]["p90_s"]), d(bc["warten_6"]["p99_s"]), n(bc["aktivierung"]), bc["diff1_prozent"], d(bm["6"]["0.5"]))
xt = ("Bitcoin Cash chipnet with one minute blocks. We counted the wait for six confirmations at our listener, usually %s, and 9 of 10 times within %s. "
      "Wallets and pools, which wait do you show your users before you call a payment done?") % (d(bc["warten_6"]["median_s"]), d(bc["warten_6"]["p90_s"]))
for name, t in (("zcash_59124", zt), ("bch_2173", bt), ("x", xt)):
    print("== %s, %d woerter, %d zeichen\n%s\n" % (name, len(t.split()), len(t), t))
