#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
newsletter_subject.py - holt den Betreff aus dem Newsletter-HTML.

Damit der Betreff an genau einer Stelle steht, naemlich in der Datei, die
auch verschickt wird. Reihenfolge:

    1. <meta name="x-subject" content="...">   die verbindliche Angabe
    2. <title>...</title>                      Notnagel
    3. Dateiname                               damit nie ein leerer Betreff rausgeht

    python3 scripts/newsletter_subject.py newsletter/2026-09-14.html
"""
import html as htmllib
import os
import re
import sys

META = re.compile(r'<meta[^>]+name=["\']x-subject["\'][^>]*content=["\'](.*?)["\']', re.I | re.S)
META2 = re.compile(r'<meta[^>]+content=["\'](.*?)["\'][^>]*name=["\']x-subject["\']', re.I | re.S)
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def subject(path):
    with open(path, encoding="utf-8") as fh:
        doc = fh.read()
    for rx in (META, META2, TITLE):
        m = rx.search(doc)
        if m:
            s = htmllib.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
            if s:
                return s
    return os.path.splitext(os.path.basename(path))[0]


def main():
    if len(sys.argv) != 2:
        sys.exit("aufruf: newsletter_subject.py <datei.html>")
    if not os.path.isfile(sys.argv[1]):
        sys.exit("datei fehlt: %s" % sys.argv[1])
    print(subject(sys.argv[1]))


if __name__ == "__main__":
    main()
