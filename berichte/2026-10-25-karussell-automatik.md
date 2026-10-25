# Bericht 25.10.2026: Karussell und Meme automatisch auf Instagram

Branch `feat/karussell-automatik`, PR #143.

## Befund
- **Nur Entwürfe:** `karussell.yml` baute bisher nur Entwürfe nach #moderator-only. Den Wochen-Entwurf vom Fr 23.10. 18:00 hat niemand gepostet.
- **Kein Meme-Lauf:** Für das Meme am So 25.10. gab es keinen Lauf. Der einmalige Timer `takt-karussell-meme-2026-10-25.timer` stand nicht in `TAKTE` in `deploy/c2/setup.sh`, `setup.sh nachziehen` hat ihn also nie verlinkt. Dasselbe gilt für `takt-karussell-woche` und `takt-karussell-story`. Ob die beiden von Hand verlinkt waren, kann ich von hier nicht sehen.

## Was gemacht wurde
- **Neues Skript `scripts/karussell_post.py`** (mit `--selbsttest`), drei Schritte:
  - **entwurf**, 2 Stunden vor dem Post:
    - baut die Seiten im Look aus dem gemeinsamen Raster (`data/look-takt.json`) und prüft Texte und Caption
    - schickt Bilder und Caption nach #moderator-only mit dem Satz „geht um HH:MM raus, Veto: karussell-stopp (Variable KARUSSELL_STOPP auf JJJJ-MM-TT oder immer)“
    - legt alles als Artefakt `karussell-entwurf-<art>-<datum>` ab, mit einer Prüfsumme je Bild
  - **posten**, zum Termin:
    - holt genau die Bilder aus dem Entwurf; neu gebaut wird nichts, das Meme würde sonst eine andere Blockrate messen
    - prüft die Prüfsummen und die Caption noch einmal und macht JPEGs
    - legt die Bilder als Release-Anhang `karussell-ablage` in `neoalphavault-png/kaspapulse-media` ab, wie die Reels, und prüft, dass sie abholbar sind
    - legt über die Graph API die Container an: Karussell mit Kind-Containern bis 10 Seiten, eine Seite als Einzelbild
    - veröffentlicht nur, wenn scharf
    - löscht die Anhänge danach immer, auch wenn vorher etwas scheitert, und schreibt `data/karussell-log.json`
  - **probe**: beides in einem Lauf, nie veröffentlicht, nichts gemerkt. Das ist der Vorschau-Lauf.
- **Scharf nur, wenn alles zusammenkommt:**
  - Der Lauf kommt vom Takt (`start=takt`). Von Hand ist immer trocken.
  - Die Variable `KARUSSELL_LIVE` steht auf `true` (Standard: aus).
  - `KARUSSELL_STOPP` steht weder auf dem Postdatum noch auf `immer`.
  - Der Takt liegt im Fenster von 15 Minuten vor bis 90 Minuten nach der Postzeit, und das Datum ist heute in Berlin.
  - Der Termin ist noch nicht gepostet; ein zweiter Lauf postet nicht doppelt.
- **Takte (Berlin):**

  | Art | Entwurf | Post |
  | --- | --- | --- |
  | woche | Sa 09:00 | Sa 11:00 |
  | story | Mi 16:00 | Mi 18:00 |
  | meme | Sa 13:00 | Sa 15:00 |

  - Es gibt jetzt sechs wiederkehrende Timer in `deploy/c2/taktgeber/` und dazu sechs Fälle in `ausloesen.sh`.
  - Der einmalige Meme-Timer ist entfernt.
  - Die sechs Namen stehen jetzt in `TAKTE`, damit `setup.sh nachziehen` sie einspielt.
  - Die Befehle für den Server stehen im README des Taktgebers, Abschnitt „Karussell und Meme einspielen“.
- **Look:** Das Raster bleibt die Quelle. Weil der Samstag jetzt dreimal postet (Tagesgrafik 09:30, Karussell 11:00, Meme 15:00), steht das Meme im Rang hinter dem Karussell (`look_takt.RANG`). Der Selbsttest prüft die Folge an einem Samstag.
- **Nie zwei Diagramme nebeneinander:** Im Profilraster steht nur Seite 1, und zwar neben der Tagesgrafik, die oft ein Diagramm ist. Neue Wache `karussell.deckblatt_pruefen`: Seite 1 trägt nie ein Diagramm. Die Balken stehen weiter nur auf Seite 2 und 3, je eins.
- **Caption nach den Content-Regeln**, fünf Blöcke:
  1. Haken mit Zahl
  2. ein Satz mit Stichtag und Quelle
  3. eine Frage
  4. „Weekly Kaspa numbers in our newsletter, link in bio.“
  5. höchstens 5 Hashtags

  Kein Link. `karussell.caption_pruefen` prüft das Block für Block, dazu die Echtzeit- und Quellenwachen wie bei der Tagesgrafik: kein Echtzeit-Wort, „counted“ nur bei eigener Zählung, eine Quelle und ein Datum müssen dastehen. Woche, Story und Meme bauen ihre Caption danach.
- **Meme, ein Motiv nur einmal:** Das Meme hat genau ein Motiv („KAsPa“ aus dem Periodensystem). Ist es einmal gepostet, kommt samstags kein Entwurf mehr, sondern nur die Zeile „ein neues Motiv fehlt“ in #moderator-only. Dasselbe Bild jede Woche wäre schlechter als keins. Siehe Frage 2.

## Test
- **Selbsttests grün:**
  - `karussell_post.py`, unter anderem ein ganzer Posten-Lauf gegen eine nachgebaute API: Karussell und Einzelbild, trocken und scharf, Doppelpost-Sperre, Stopp, Fenster, Aufräumen nach einem Graph-Fehler, ein verändertes Bild wird nicht gepostet
  - `karussell.py`, `meme_wahr.py` und `look_takt.py`
- **Secret-Scan:** sauber.
- **Lokal gebaut:** woche für Sa 24.10. und meme. Kontaktbogen `docs/karussell/probe-2026-10-24.png`.
- **Trockenläufe auf GitHub** (`schritt=probe`, Branch `feat/karussell-automatik`):
  - **Erste Runde**, Läufe [6](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40206486025) (meme) und [7](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40206488612) (woche):
    - **meme:** Die Probe hat einen alten Fehler in `meme_wahr.py` gefunden. Mit echter Messung („9.9 blocks a second“) lief Seite 2 um 123 px rechts aus dem Bild. Nur der Rückfall „10 blocks a second“ passte, und mit dem war der Entwurf lokal gebaut worden. Das wäre am Samstag beim echten Meme genauso passiert.
    - **Behoben:** Die Einheit steht jetzt unter der Zahl. Der Selbsttest rendert drei gemessene Werte in allen drei Looks.
  - **Zweite Runde**, Läufe [8](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40207525942) (meme, 31.10.) und [9](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/40207527933) (woche, 24.10.):
    - **Entwurf in beiden grün:**
      - Selbsttests grün, Seiten gebaut und von der Wache gemessen
      - Entwurf mit „PROBE“ und dem Veto-Satz in #moderator-only
      - Artefakt mit Manifest hochgeladen
      - Das Meme hat diesmal echt gemessen, 10 Minuten lang, mit 2 Seiten
    - **Posten in beiden sauber gestoppt** mit „kein MEDIA_REPO_TOKEN, die bilder haben keinen oeffentlichen ort“. Das Secret ist in kaspa-pulse nicht gesetzt (Frage 1).
    - **Noch offen:** Ablage, Container-Anlage und Graph-Antwort sind auf GitHub noch nicht durchgelaufen. Den Schritt deckt bisher nur der Selbsttest gegen die nachgebaute API ab. Nach dem Setzen des Secrets bitte eine Probe starten: Actions, `karussell`, `schritt=probe`, `art=woche`, `fuer=2026-10-24`.
    - Die Läufe sind rot, weil der Posten-Schritt stoppt. Nach jedem roten Lauf ging die Meldung „karussell … probe ist rot“ nach #moderator-only.

## Offene Fragen an Ben
1. **MEDIA_REPO_TOKEN:** Das Secret gibt es in pulse-studio. Ist es auch in kaspa-pulse gesetzt? Ohne es hat der Posten-Lauf keinen öffentlichen Ort für die Bilder und stoppt mit „kein MEDIA_REPO_TOKEN“. Bitte denselben Token als Secret in kaspa-pulse eintragen. Er braucht Schreibrecht auf Releases in kaspapulse-media. Den Wert bitte nicht schicken.
2. **Meme-Serie:** Für „jeden Samstag“ braucht die Serie neue Motive. Soll ich weitere Motive für `meme_wahr.py` vorschlagen, jedes mit belegter Zahl?
3. **Insights:** Die Tagesgrafik trägt ihre Posts in `data/insights/manifest.jsonl` ein. Das Karussell tut das nicht, weil `data/insights/` und `post_manifest.py` nicht angefasst werden sollen. Soll das Karussell dort eingetragen werden?
4. **Woche am Samstag:** Das Karussell braucht die Montagsausgabe derselben Woche in `weekly-history.json`. Fehlt sie, kommt kein Entwurf, und der Lauf ist rot. Das war schon vorher so.

## Was Ben tun muss
1. PR prüfen und mergen. Er enthält die Workflow-Datei `karussell.yml` und die c2-Dateien.
2. Das Secret `MEDIA_REPO_TOKEN` in kaspa-pulse setzen, falls es fehlt (Frage 1).
3. Auf c2 die Befehle aus dem README des Taktgebers ausführen, Abschnitt „Karussell und Meme einspielen“: alten Meme-Timer abschalten, `setup.sh nachziehen`, die sechs Timer aktivieren, `list-timers` prüfen.
4. Nach dem ersten sauberen Vorschau-Lauf die Variable `KARUSSELL_LIVE=true` setzen. Ein sauberer Vorschau-Lauf ist ein `probe` oder ein Takt-Lauf mit „trocken durchgelaufen, container …“. Vorher bleibt alles trocken.

## Nachtrag: Abnahme von #139 (Jekyll, reports/ und graphics/fonts/README.md)
#139 ist am 25.10.2026 gemergt. Geprüft nach dem Deploy auf kaspapulse.com, 25.10.2026 gegen 20:20 UTC:
- **404**, wie gewünscht:
  - `/deploy/c2/` und `/deploy/c2/setup.sh`
  - `/berichte/` und `/berichte/2026-10-23-zcash-mainnet.html`
  - `/reports/` und `/reports/uhrwerk-roh-2026-10-19.html` (auch `.md` und ohne Endung)
  - `/graphics/fonts/README.html` und `.md`
- **200:** `/data/covenants/abgleich-2026-10-09/METHOD.html` bleibt öffentlich (Ben, 24.10.).
- **200** auch für Startseite, `/archive/`, `/method/`, `/entity-x.html`, `/impressum.html` und `/datenschutz.html`.
- Gleich nach dem Merge lieferte `/reports/…` noch 200, fünf Minuten später 404. Das war der laufende Pages-Deploy.
