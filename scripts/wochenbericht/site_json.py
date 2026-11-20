"""Aus zahlen.json die Datendatei der Wochenseite bauen (nur Werte, Fenster, Kennzeichnung, Quelle)."""
import json, sys
z = json.load(open(sys.argv[1])); aus = sys.argv[2]
zc, bc, bm = z["zcash"], z["bch"], z["bch_mainnet_computed"]
def utc(s): return s.replace(" ", "T")[:19] + "Z"
d = {
 "hinweis": "Wochenbericht 1 (Ben 20.11.2026). Werte aus kaspa-pulse, Datenbranches messung/zcash-mainnet und messung/bch-chipnet-xo, je Zahl label, Fenster und Quelle. Erzeugt aus dem Rechenlauf, nicht von Hand. Nach dem Aendern: python3 scripts/b2b_pages.py",
 "published": "2026-11-22", "number": 1,
 "zcash": {
  "window": {"from_utc": utc(zc["fenster"][0]), "to_utc": utc(zc["fenster"][1])},
  "listener_window": {"from_utc": zc["zuhoerer"]["fenster"][0], "to_utc": zc["zuhoerer"]["fenster"][1]},
  "heights": zc["hoehen"], "intervals": zc["abstaende"], "median_s": zc["median_s"], "mean_s": zc["mittel_s"],
  "over_75_pct": zc["ueber75_prozent"],
  "wait": {str(k): {"median_s": zc[f"warten_{k}"]["median_s"], "p90_s": zc[f"warten_{k}"]["p90_s"]} for k in (1, 3, 6)},
  "ideal": {str(k): {"median_s": v["0.5"], "p90_s": v["0.9"]} for k, v in z["zcash_computed_25s"].items()},
  "chain_blocks": zc["zuhoerer"]["kettenbloecke"], "orphaned": zc["zuhoerer"]["abgehaengt"],
  "orphaned_without_header": zc["zuhoerer"]["ohne_kopf"], "max_depth": zc["zuhoerer"]["groesste_tiefe"],
  "gaps": zc["luecken"], "cross_checks": zc["koepfe"]["gegenproben"]},
 "bch": {
  "activation_height": bc["aktivierung"],
  "window": {"from_utc": utc(bc["seit"]), "to_utc": utc(bc["bis"])},
  "listener_window": {"from_utc": utc(bc["zuhoerer"]["von"]), "to_utc": utc(bc["zuhoerer"]["bis"])},
  "listener_heights": bc["zuhoerer"]["hoehen"], "intervals": bc["abstaende"], "median_s": bc["median_s"], "mean_s": bc["mittel_s"],
  "diff1_pct": bc["diff1_prozent"],
  "wait": {str(k): {"median_s": bc[f"warten_{k}"]["median_s"], "p90_s": bc[f"warten_{k}"]["p90_s"], "p99_s": bc[f"warten_{k}"]["p99_s"],
                     "header_median_s": bc[f"warten_{k}"]["kopfzeit_median_s"], "header_p90_s": bc[f"warten_{k}"]["kopfzeit_p90_s"]} for k in (1, 3, 6, 12)},
  "mainnet_computed": {k: {"median_s": v["0.5"], "p90_s": v["0.9"], "p99_s": v["0.99"]} for k, v in bm.items()},
  "gaps": bc["luecken"], "cross_checks": bc["koepfe"]["gegenproben"]}}
json.dump(d, open(aus, "w"), indent=1, ensure_ascii=False); open(aus, "a").write("\n")
