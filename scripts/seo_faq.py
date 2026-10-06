#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seo_faq.py, macht das FAQPage-Schema einer Seite sichtbar (Ben, 06.10.2026, SEO-Ausbau).

Google verlangt, dass die Fragen und Antworten aus einem FAQPage-Schema auch
sichtbar auf der Seite stehen. Auf fast allen Seiten von kaspapulse.com stand
das Schema allein. Dieses Skript liest das Schema und schreibt dieselben
Fragen und Antworten wortgleich als Abschnitt in die Seite, zwischen die
Marken <!--AUTO:faq--> und <!--/AUTO:faq-->. Gibt es die Marken noch nicht,
setzt es sie vor den Newsletter-Kasten, sonst vor den Footer.

    python3 scripts/seo_faq.py kaspa-supply.html [weitere seiten]
    python3 scripts/seo_faq.py --selbsttest
"""
import html as htmlmod
import json
import re
import sys

MARKE = re.compile(r"<!--AUTO:faq-->.*?<!--/AUTO:faq-->", re.S)


def fragen(s):
    aus = []
    for b in re.findall(r'(?is)<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', s):
        try:
            d = json.loads(b)
        except ValueError:
            continue
        for obj in (d if isinstance(d, list) else [d]):
            if isinstance(obj, dict) and obj.get("@type") == "FAQPage":
                for q in obj.get("mainEntity") or []:
                    f = (q.get("name") or "").strip()
                    a = ((q.get("acceptedAnswer") or {}).get("text") or "").strip()
                    if f and a:
                        aus.append((f, a))
    return aus


def block(paare):
    teile = ["<!--AUTO:faq-->", '  <div class="faq">', "  <h2>Questions people ask</h2>"]
    for f, a in paare:
        teile.append("  <h3>%s</h3>" % htmlmod.escape(f, quote=False))
        teile.append("  <p>%s</p>" % htmlmod.escape(a, quote=False))
    teile += ["  </div>", "<!--/AUTO:faq-->"]
    return "\n".join(teile)


def einsetzen(s):
    paare = fragen(s)
    if not paare:
        return s, 0
    neu = block(paare)
    if MARKE.search(s):
        return MARKE.sub(lambda _m: neu, s, count=1), len(paare)
    for anker in ('  <div class="subscribe">', "  <footer>"):
        if anker in s:
            return s.replace(anker, neu + "\n" + anker, 1), len(paare)
    raise SystemExit("kein platz fuer die faq gefunden")


def selbsttest():
    s = ('<p>x</p>\n  <div class="subscribe">\n<script type="application/ld+json">{"@type":"FAQPage","mainEntity":['
         '{"@type":"Question","name":"Is it <safe>?","acceptedAnswer":{"@type":"Answer","text":"Yes & no."}}]}</script>')
    n, k = einsetzen(s)
    ok1 = k == 1 and "<h3>Is it &lt;safe&gt;?</h3>" in n and "<p>Yes &amp; no.</p>" in n
    n2, _ = einsetzen(n)
    ok2 = n2.count("<!--AUTO:faq-->") == 1
    print("ok" if ok1 and ok2 else "FEHL", "einsetzen und wiederholen")
    return 0 if ok1 and ok2 else 1


def main(argv):
    if argv[:1] == ["--selbsttest"]:
        return selbsttest()
    for p in argv:
        s = open(p, encoding="utf-8").read()
        n, k = einsetzen(s)
        if n != s:
            open(p, "w", encoding="utf-8").write(n)
        print("%s, %d fragen sichtbar" % (p, k))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
