#!/usr/bin/env python3
"""chipnet_format_f.py - PulseHawk-Post Format F zum BCH chipnet.

Ben, 28.10.2026: Format F ("wie wir zaehlen", eine Methodenentscheidung mit
einer Grafik) fuer Sa 31.10. Die Entscheidung: unser berechneter Vergleich ist
eine ideale 600-s-Kette OHNE die chipnet-Regel fuer Mindestschwierigkeit (nach
2 x 600 s ohne Block). Der Abstand zwischen gezaehlt und berechnet zeigt also,
was die Regel aendert.

Eingang: eigene Koepfe (chipnet_koepfe.py) und der Stand von
chipnet_auswertung.py. Ausgang: text.txt (geprueft mit regel_pruefen aus
scripts/ph/ph_entwurf.py, hoechstens 280 Zeichen, ein Link zaehlt 23) und zwei
Grafiken, 1600 x 900 und 1080 x 1350. Mit --senden geht beides als Entwurf an
DISCORD_WEBHOOK_PH_DRAFTS (nur aus dem Workflow, die Adresse steht nirgends).

  python3 scripts/bch/chipnet_format_f.py --koepfe data/bch-chipnet/koepfe.csv.gz \\
      --stand data/bch-chipnet/stand-2026-10-30.json --aus data/bch-chipnet/format-f [--senden]
"""
import argparse
import csv
import gzip
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "ph"))
from ph_entwurf import FARBE, regel_pruefen  # noqa: E402

POW_LIMIT_BITS = "1d00ffff"
ZIEL_S = 600
REGEL_S = 2 * ZIEL_S
FALKE = os.path.join(HIER, "..", "..", "assets", "pulsehawk-falke.png")
LINK = "pulsehawk.io"
X_LINK_ZEICHEN = 23
X_GRENZE = 280
MONATE = "jan feb mar apr may jun jul aug sep oct nov dec".split()


def ts(text):
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()


def kurz(t):
    d = datetime.fromtimestamp(t, timezone.utc)
    return f"{d.day} {MONATE[d.month - 1]} {d:%H:%M}"


def x_zeichen(text):
    """Zeichen wie X sie zaehlt: der Link gilt als 23, sonst jedes Zeichen 1 (nur ASCII erlaubt)."""
    if any(ord(c) > 127 for c in text):
        raise SystemExit("text enthaelt nicht-ascii, die zaehlung waere unsicher")
    return len(text) - text.count(LINK) * len(LINK) + text.count(LINK) * X_LINK_ZEICHEN


def abstaende(koepfe, ab, bis):
    with gzip.open(koepfe, "rt") as f:
        k = sorted((int(r["hoehe"]), int(r["zeit"]), r["nbits"]) for r in csv.DictReader(f))
    paare = []
    for (_, t0, _), (h, t, b) in zip(k, k[1:]):
        if ab <= t <= bis:
            paare.append((t - t0, b == POW_LIMIT_BITS))
    return paare


def text_bauen(stand, n_mindest, n):
    b = stand["bereich"]
    ende = kurz(ts(stand["abruf_utc"].replace("T", " ").rstrip("Z")))
    zeilen = [
        "bch chipnet, and how we compare it.",
        f"we counted {n_mindest:,} of {n:,} blocks since 1 oct at minimum difficulty, all after gaps over 20 min.",
        "our computed line is an ideal 600 s chain without that rule.",
        f"window {kurz(ts(b['ab_utc']))} to {ende} utc.",
        f"method on {LINK}",
    ]
    return "\n".join(zeilen)


def pruefen(text):
    fehler = list(regel_pruefen(text))
    for satz in re.split(r"(?<=[.!?])\s+|\n", text):
        if satz and satz[0].isdigit():
            fehler.append(f"satz beginnt mit ziffer: {satz[:30]!r}")
    if re.search(r"\bxo\b", text):
        fehler.append("xo-bezug")
    if not text.endswith(f"method on {LINK}"):
        fehler.append("letzte zeile ist nicht 'method on pulsehawk.io'")
    z = x_zeichen(text)
    if z > X_GRENZE:
        fehler.append(f"{z} zeichen, hoechstens {X_GRENZE}")
    return fehler, z


def grafik(pfad, breite, hoehe, paare, fenster):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    hoch = hoehe > breite
    # Lesbar auf 390 px Breite: Schrift in Pixeln mal 390/breite soll mindestens 9 px ergeben.
    s = breite / 1600
    gr = {"titel": 50 * s if not hoch else 46 * s * 1.48, "unter": 30 * s if not hoch else 30 * s * 1.48,
          "achse": 30 * s if not hoch else 30 * s * 1.48, "fuss": 28 * s if not hoch else 26 * s * 1.48}
    fig = plt.figure(figsize=(breite / 100, hoehe / 100), dpi=100, facecolor=FARBE["bg"])
    if hoch:
        ax = fig.add_axes([0.15, 0.24, 0.76, 0.37], facecolor=FARBE["bg"])
        y_titel, y_unter, y_fuss, y_fenster = 0.85, 0.81, 0.035, 0.08
    else:
        ax = fig.add_axes([0.1, 0.27, 0.83, 0.5], facecolor=FARBE["bg"])
        y_titel, y_unter, y_fuss, y_fenster = 0.9, 0.83, 0.035, 0.09
    fig.text(0.07 if not hoch else 0.08, y_titel, "bch chipnet block intervals", color=FARBE["txt"],
             fontsize=gr["titel"], fontweight="bold")
    fig.text(0.07 if not hoch else 0.08, y_unter, "counted against an ideal 600 s chain", color=FARBE["dim"],
             fontsize=gr["unter"])

    werte = [a for a, _ in paare]
    n = len(werte)
    breite_bin = 60
    kanten = list(range(0, 2400 + breite_bin, breite_bin))
    normal = [a for a, m in paare if not m and 0 <= a < kanten[-1]]
    mindest = [a for a, m in paare if m and 0 <= a < kanten[-1]]
    ax.hist([normal, mindest], bins=kanten, stacked=True, color=[FARBE["teal"], "#2E8F7D"],
            label=["counted", "counted, minimum difficulty"])
    xs = [k + breite_bin / 2 for k in kanten[:-1]]
    ys = [n * (math.exp(-(x - breite_bin / 2) / ZIEL_S) - math.exp(-(x + breite_bin / 2) / ZIEL_S)) for x in xs]
    ax.plot(xs, ys, color=FARBE["zweit"], linewidth=4 * s if not hoch else 4, label="computed, ideal 600 s")
    ax.axvline(REGEL_S, color=FARBE["txt"], linewidth=3 * s if not hoch else 3, linestyle=(0, (6, 4)))
    ax.text(REGEL_S - 30, ax.get_ylim()[1] * 0.9, "1,200 s", color=FARBE["txt"], fontsize=gr["achse"], ha="right")
    ax.set_xlim(0, kanten[-1])
    ax.set_xticks([0, 600, 1200, 1800, 2400])
    ax.set_xticklabels(["0", "600", "1,200", "1,800", "2,400"])
    ax.set_xlabel("seconds between blocks", fontsize=gr["achse"], color=FARBE["dim"])
    ax.set_ylabel("blocks", fontsize=gr["achse"], color=FARBE["dim"])
    ax.tick_params(colors=FARBE["dim"], labelsize=gr["achse"])
    for sp in ax.spines.values():
        sp.set_color(FARBE["linie"])
    ax.grid(color=FARBE["linie"], linewidth=1)
    ax.set_axisbelow(True)
    if hoch:
        leg = ax.legend(fontsize=gr["achse"] * 0.8, loc="lower left", bbox_to_anchor=(-0.02, 1.03),
                        facecolor=FARBE["bg"], edgecolor=FARBE["bg"])
    else:
        leg = ax.legend(fontsize=gr["achse"] * 0.8, loc="upper right", bbox_to_anchor=(1, 0.86),
                        facecolor=FARBE["bg"], edgecolor=FARBE["linie"])
    for t in leg.get_texts():
        t.set_color(FARBE["txt"])
    links = 0.07 if not hoch else 0.08
    fig.text(links, y_fenster, fenster, color=FARBE["dim"], fontsize=gr["fuss"])
    fig.text(links, y_fuss, "Data from PulseHawk", color=FARBE["teal"], fontsize=gr["fuss"])
    fig.text(0.95, y_fuss, LINK, color=FARBE["dim"], fontsize=gr["fuss"], ha="right")
    fig.savefig(pfad, facecolor=FARBE["bg"])
    plt.close(fig)
    with Image.open(pfad) as im, Image.open(FALKE) as falke:
        im = im.convert("RGBA")
        h = int(hoehe * (0.11 if not hoch else 0.085))
        falke = falke.resize((round(falke.width * h / falke.height), h), Image.LANCZOS)
        oben = int(0.05 * hoehe) if not hoch else int(0.035 * hoehe)
        im.alpha_composite(falke, (breite - falke.width - int(0.05 * breite), oben))
        im.convert("RGB").save(pfad)
    with Image.open(pfad) as im:
        assert im.size == (breite, hoehe), f"grafik hat {im.size}, erwartet {breite}x{hoehe}"


def senden(aus, text, dateien):
    hook = os.environ.get("DISCORD_WEBHOOK_PH_DRAFTS", "").strip()
    if not hook.startswith(("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/")):
        print("DISCORD_WEBHOOK_PH_DRAFTS fehlt oder ist keine Discord-Webhook-Adresse", file=sys.stderr)
        sys.exit(1)
    inhalt = f"entwurf fuer @pulsehawkio, bch chipnet format f, sa 31.10. 16:30 berlin, nicht gepostet\n```\n{text}\n```"
    grenze = "----ph" + uuid.uuid4().hex
    teile = []

    def feld(name, wert, dateiname=None, typ=None):
        k = f'Content-Disposition: form-data; name="{name}"'
        if dateiname:
            k += f'; filename="{dateiname}"'
        if typ:
            k += f"\r\nContent-Type: {typ}"
        teile.append(f"--{grenze}\r\n{k}\r\n\r\n".encode() + wert + b"\r\n")
    feld("payload_json", json.dumps({"content": inhalt, "allowed_mentions": {"parse": []}}).encode(),
         typ="application/json")
    for i, d in enumerate(dateien):
        with open(os.path.join(aus, d), "rb") as f:
            feld(f"files[{i}]", f.read(), d, "image/png")
    body = b"".join(teile) + f"--{grenze}--\r\n".encode()
    req = urllib.request.Request(hook, data=body, headers={
        "Content-Type": f"multipart/form-data; boundary={grenze}", "User-Agent": "pulsehawk-entwurf/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print(f"entwurf an discord geschickt, http {r.status}")
    except urllib.error.HTTPError as e:
        print(f"discord lehnt ab, http {e.code}", file=sys.stderr)
        sys.exit(1)
    except (urllib.error.URLError, OSError) as e:
        print(f"discord nicht erreicht, {type(e).__name__}", file=sys.stderr)
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--koepfe", required=True)
    ap.add_argument("--stand", required=True)
    ap.add_argument("--aus", required=True)
    ap.add_argument("--senden", action="store_true")
    args = ap.parse_args()

    stand = json.load(open(args.stand))
    b = stand["bereich"]
    paare = abstaende(args.koepfe, ts(b["ab_utc"]), ts(b["bis_utc"]))
    n, n_mindest = len(paare), sum(1 for _, m in paare if m)
    c = stand["counted"]
    assert n == b["abstaende"], f"{n} abstaende, stand nennt {b['abstaende']}"
    assert n_mindest == c["mindestschwierigkeit"]["bloecke"], "mindestschwierigkeit weicht vom stand ab"
    ueber = [a for a, m in paare if a > REGEL_S]
    assert all(m for a, m in paare if a > REGEL_S), "ein abstand ueber 1.200 s ohne mindestschwierigkeit"

    text = text_bauen(stand, n_mindest, n)
    fehler, z = pruefen(text)
    if fehler:
        print("regelverstoss: " + "; ".join(fehler), file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.aus, exist_ok=True)
    abruf = ts(stand["abruf_utc"].replace("T", " ").rstrip("Z"))
    fenster = (f"window {kurz(ts(b['ab_utc']))} to {kurz(abruf)} utc, blocks {b['von_hoehe']:,} to "
               f"{b['bis_hoehe']:,}")
    fenster_hoch = (f"window {kurz(ts(b['ab_utc']))} to {kurz(abruf)} utc\n"
                    f"blocks {b['von_hoehe']:,} to {b['bis_hoehe']:,}, {n:,} intervals")
    dateien = ["format-f-1600x900.png", "format-f-1080x1350.png"]
    grafik(os.path.join(args.aus, dateien[0]), 1600, 900, paare, fenster)
    grafik(os.path.join(args.aus, dateien[1]), 1080, 1350, paare, fenster_hoch)
    with open(os.path.join(args.aus, "text.txt"), "w") as f:
        f.write(text + "\n")
    meta = {"stand": os.path.basename(args.stand), "abstaende": n, "mindestschwierigkeit": n_mindest,
            "ueber_1200_s": len(ueber), "zeichen_x": z, "zeichen_roh": len(text), "grafiken": dateien}
    with open(os.path.join(args.aus, "meta.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(text)
    print(json.dumps(meta, ensure_ascii=False))
    if args.senden:
        senden(args.aus, text, dateien)


if __name__ == "__main__":
    main()
