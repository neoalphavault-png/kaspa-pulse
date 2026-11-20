"""Zahlen fuer den Wochenbericht. Liest nur Dateien aus den Datenbranches."""
import csv, gzip, json, math, statistics as st, subprocess, sys, datetime as dt
R = "/home/user/kaspa-pulse"
def git(*a): return subprocess.run(["git", "-C", R, *a], capture_output=True, check=True).stdout
def show(ref, p): return git("show", f"{ref}:{p}")
def commit(ref, p): return git("log", "-1", "--format=%h %cI", ref, "--", p).decode().strip()
def ts(s): s=s.replace(" ","T"); b=dt.datetime.strptime(s[:19],"%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp(); return b+(float("0."+s[20:23]) if len(s)>20 and s[19]=="." else 0)
def iso(t): return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
def q(v,p): s=sorted(v); k=(len(s)-1)*p; f=math.floor(k); c=min(f+1,len(s)-1); return s[f]+(s[c]-s[f])*(k-f)
out = {}
Z = "origin/messung/zcash-mainnet"; B = "origin/messung/bch-chipnet-xo"
# ---------- Zcash
km = json.loads(show(Z, "data/zcash-mainnet/koepfe-meta.json"))
koepfe = {int(r["hoehe"]): int(r["zeit"]) for r in csv.DictReader(gzip.open(__import__("io").BytesIO(show(Z,"data/zcash-mainnet/koepfe.csv.gz")),"rt"))}
zus = json.loads(show(Z, "data/zcash-mainnet/lauscher-dauer/zusammenfassung.json"))
von = ts("2026-11-12T21:36:48"); bis = ts(km["abruf_utc"])
hs = [h for h in sorted(koepfe) if von <= koepfe[h] < bis and h-1 in koepfe]
iv = [koepfe[h]-koepfe[h-1] for h in hs]
def fenster(k): return [koepfe[h+k-1]-koepfe[h-1] for h in hs if h+k-1 in koepfe and koepfe[h+k-1] < bis]
z = {"koepfe": {"datei": "data/zcash-mainnet/koepfe.csv.gz", "commit": commit(Z,"data/zcash-mainnet/koepfe.csv.gz"), "abruf_utc": km["abruf_utc"], "spitze": km["spitze_hoehe"],
       "gegenproben": [(g["verglichen"], g["gleich"]) for g in km["gegenproben"]]},
     "fenster": [iso(von), iso(bis)], "hoehen": [hs[0], hs[-1]], "abstaende": len(iv), "median_s": st.median(iv),
     "mittel_s": round(sum(iv)/len(iv),2), "ueber75_prozent": round(100*sum(1 for v in iv if v>75)/len(iv),2)}
for k in (1,3,6):
    f = fenster(k); z[f"warten_{k}"] = {"n": len(f), "median_s": q(f,.5), "p90_s": q(f,.9)}
z["zuhoerer"] = {"datei": "data/zcash-mainnet/lauscher-dauer/zusammenfassung.json", "commit": commit(Z,"data/zcash-mainnet/lauscher-dauer/zusammenfassung.json"),
     "fenster": zus["fenster_utc"], "kettenbloecke": zus["kettenbloecke_im_fenster"], "angekuendigt": zus["davon_angekuendigt_gesehen"],
     "abgehaengt": zus["abgehaengt_anzahl"], "ohne_kopf": zus["abgehaengt_ohne_kopf"], "groesste_tiefe": zus["groesste_tiefe"], "abgedeckt_min": zus["abgedeckt_min"]}
# luecken zcash
metas = sorted(p for p in git("ls-tree","--name-only",Z,"data/zcash-mainnet/lauscher-dauer/").decode().split() if p.endswith("-meta.json"))
lf = sorted((ts(json.loads(show(Z,p))["start_utc"]), ts(json.loads(show(Z,p))["ende_utc"])) for p in metas)
z["laeufe"] = len(lf); z["luecken"] = [(iso(a[1]), iso(b[0]), round(b[0]-a[1])) for a, b in zip(lf, lf[1:]) if b[0] > a[1] + 1]
out["zcash"] = z
# ---------- BCH chipnet
A = 332451
cm = json.loads(show(B, "data/bch-chipnet/koepfe-meta.json"))
ck = {int(r["hoehe"]): (int(r["zeit"]), r["nbits"]) for r in csv.DictReader(gzip.open(__import__("io").BytesIO(show(B,"data/bch-chipnet/koepfe.csv.gz")),"rt"))}
top = max(ck); civ = [ck[h][0]-ck[h-1][0] for h in range(A, top+1)]
b = {"koepfe": {"datei": "data/bch-chipnet/koepfe.csv.gz", "commit": commit(B,"data/bch-chipnet/koepfe.csv.gz"), "abruf_utc": cm["abruf_utc"], "spitze": top,
       "gegenproben": [(g["verglichen"], g["gleich"]) for g in cm["gegenproben"]]},
     "aktivierung": A, "seit": iso(ck[A-1][0]), "bis": iso(ck[top][0]), "abstaende": len(civ), "median_s": st.median(civ), "mittel_s": round(sum(civ)/len(civ),2),
     "diff1_prozent": round(100*sum(1 for h in range(A, top+1) if ck[h][1]=="1d00ffff")/(top-A+1),1), "diff1": sum(1 for h in range(A, top+1) if ck[h][1]=="1d00ffff")}
rows = list(csv.DictReader(__import__("io").StringIO(show(B,"data/bch-chipnet/lauscher/bloecke.csv").decode())))
seen = {int(r["height"]): ts(r["first_seen_utc"]) for r in rows if r["first_seen_utc"]}
sh = sorted(seen)
b["zuhoerer"] = {"datei": "data/bch-chipnet/lauscher/bloecke.csv", "commit": commit(B,"data/bch-chipnet/lauscher/bloecke.csv"), "hoehen": [sh[0], sh[-1]],
                 "von": iso(seen[sh[0]]), "bis": iso(seen[sh[-1]]), "bloecke": len(sh)}
for k in (1,3,6,12):
    f = [seen[h+k-1]-seen[h-1] for h in sh if h-1 in seen and h+k-1 in seen]
    g = [ck[h+k-1][0]-ck[h-1][0] for h in sh if h-1 in ck and h+k-1 in ck]
    b[f"warten_{k}"] = {"n": len(f), "median_s": round(q(f,.5),1), "p90_s": round(q(f,.9),1), "p99_s": round(q(f,.99),1),
                        "kopfzeit_median_s": q(g,.5), "kopfzeit_p90_s": q(g,.9)}
bz = json.loads(show(B,"data/bch-chipnet/lauscher/zusammenfassung.json"))
b["zuhoerer"].update({"zus_commit": commit(B,"data/bch-chipnet/lauscher/zusammenfassung.json"), "kettenbloecke": bz["kettenbloecke"], "angekuendigt": bz["davon_angekuendigt_gesehen"], "stale": bz["stale"]["anzahl"]})
bm = sorted(p for p in git("ls-tree","-r","--name-only",B,"data/bch-chipnet/lauscher/").decode().split() if p.endswith("/meta.json"))
bl = sorted((ts(json.loads(show(B,p))["start_utc"]), ts(json.loads(show(B,p))["ende_utc"])) for p in bm)
b["laeufe"] = len(bl); b["luecken"] = [(iso(a[1]), iso(c[0]), round(c[0]-a[1])) for a, c in zip(bl, bl[1:]) if c[0] > a[1] + 1]
# lucken in den first-seen-hoehen
b["hoehen_ohne_sichtung"] = sum(1 for h in range(sh[0], sh[-1]+1) if h not in seen)
out["bch"] = b
# ---------- BCH mainnet computed, Erlang mit 600 s
def erlang_cdf(x, k, m): l = x/m; return 1 - math.exp(-l)*sum(l**i/math.factorial(i) for i in range(k))
def erlang_q(p, k, m):
    lo, hi = 0.0, 600.0*k*20
    for _ in range(200):
        mid = (lo+hi)/2
        lo, hi = (mid, hi) if erlang_cdf(mid,k,m) < p else (lo, mid)
    return round(mid)
out["bch_mainnet_computed"] = {k: {p: erlang_q(p, k, 600) for p in (0.5, 0.9, 0.99)} for k in (1,3,6,12)}
out["zcash_computed_25s"] = {k: {p: round(erlang_q(p, k, 25),1) for p in (0.5, 0.9)} for k in (1,3,6)}
json.dump(out, open(sys.argv[1], "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
