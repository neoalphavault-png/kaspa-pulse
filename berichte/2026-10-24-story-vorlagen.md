# Bericht 24.10.2026: Instagram-Story-Vorlagen Mo bis Fr mit Anleitung

Branch `design/story-vorlagen`, eigener PR von main. Nichts wird automatisch auf Instagram gepostet.

## Was gemacht wurde
- **Generator `scripts/story_vorlage.py`:**
  - baut die Story als PNG in 1080 x 1920, im Look-Takt (dunkel, hell, teal, hell, eigene Serie `story`) mit der Wortmarke KASPA PULSE, ohne Falken
  - Rangfolge: Titel im Akzent, dann eine große Zahl oder ein großes Zitat, dann die Frage
  - darunter die gestrichelte, beschriftete Fläche für das Instagram-Element: „quiz here“, „slider here“, „poll here“, „question box here“, „link here“
  - alles liegt in der sicheren Fläche der `content_wache` (x 60 bis 900, y 270 bis 1500). Oben bleiben 14 % frei, unten mehr als 20 %.
- **Wochenplan:**

  | Tag | Art | Inhalt |
  | --- | --- | --- |
  | Mo | Quiz | „guess the week“: eine Wochenzahl aus dem letzten Weekly, vier Antworten, eine richtig |
  | Di | Emoji-Slider | „kaspa in real life“: Tagesemission gegen eine Zeit aus dem Alltag (Fußballspiel, Nacht, Film, Mittagspause, Kaffee) |
  | Mi | Umfrage | „your call“: zwei Optionen, eine Messfrage, nie der Kurs |
  | Do | Fragebox | Zitat aus dem Erklärer dieser Woche, darunter „what should we count next?“ |
  | Fr | Wahr oder falsch | „nobody counts this“ aus eigener Zählung (Entity X), dazu Newsletter-Zeile und Link-Fläche |
  | Di bis Sa | Auflösung | „yesterday's answer“ mit richtiger Antwort und Zahl, aus `data/story-log.json` |
- **Inhalt:**
  - zuerst aus `data/story-plan.json` (je Woche, Schlüssel ist der Montag, darin `mo` bis `fr`)
  - fehlt ein Eintrag, kommen Frage und Antworten aus festen Vorlagen und den Daten: Weekly, Emission, Zahl des Tages, Entity X
  - die Anleitung nennt in der Zeile `inhalt`, woher die Story kommt
- **Lieferung:** Workflow `story-vorlage.yml`, Takt `takt-story-vorlage.timer` Mo bis Sa 07:45 Berlin. Der Workflow schickt das PNG der Vorlage und das PNG der Auflösung nach #moderator-only (`DISCORD_WEBHOOK_OPS`). Dazu:
  - die Anleitung als Codeblock: Element, Frage, Antworten, richtige Antwort, Platzierung, Musikvorschlag (ruhig, elektronisch, ohne Gesang, mit einem Suchwort) und Link
  - den Hinweis „posten 17:30“
  - die Feed-Zahl des Tages
- **Kurzlink `/story`:**
  - `kaspapulse.com/story` leitet weiter auf `/?utm_source=instagram&utm_medium=story&utm_campaign=story`, wie die anderen Kurzlinks per meta refresh ohne JavaScript
  - `story` steht jetzt in `MEDIEN` in `scripts/utm.py` und im Spiegel in `utm.js`
- **Wachen**, vor dem Rendern und am gerenderten Bild:
  - Textregeln wie überall: Echtzeit-Wort, „percent“, Gedankenstrich, Doppelpunkt, Pfeil, Kursziel, „counted“ bei fremder Quelle, Zahl ohne Datum
  - keine Kursfrage (price, $, market cap, buy, sell …) und kein Köder (giveaway, free, tag a friend …)
  - Umfrage-Optionen höchstens 24 Zeichen, Quiz höchstens 4 Optionen, Slider nur mit Emoji
  - Element außerhalb der sicheren Fläche: Stopp
  - Text zu lang: Stopp, statt das Element nach unten zu schieben
  - Story-Zahl gleich Feed-Zahl: Stopp, auch in anderer Schreibweise (574M gleich 574,000,000)
- **Feed-Zahl:** Um 07:45 ist der Feed-Post von 09:30 noch nicht draußen. Die Zahl steht aber im Artefakt der Tagesgrafik von 07:30, das der Lauf über `instagram.artefakt` holt (dafür `actions: read`). Findet er sie nicht, kommt die Vorlage trotzdem, mit dem Hinweis „feed-zahl heute unbekannt, bitte gegen den feed-post von 09:30 prüfen“.

## Abnahme
- **Selbsttest** (`python3 scripts/story_vorlage.py --selbsttest`), 0 Fehler:
  - eine ganze Woche Mo bis Fr plus die Auflösungen Di bis Sa
  - jede Story in allen drei Looks gerendert und von der `content_wache` im Profil „story“ gemessen
  - dazu fünf Wochen hintereinander, damit jede Variante der festen Vorlagen einmal gebaut ist: 3 Quizfragen, 5 Alltagsvergleiche, 3 Umfragen, 4 Aussagen
  - jede Wache hat ihren eigenen Fall
- **Bei 390 px angesehen:** alle sechs Tage, alle drei Looks. Der kleinste Text (40 px, Datumszeile und Beschriftungen) ist bei 390 px gut lesbar. Jeder Lauf legt dazu eine Vorschau `story-<datum>-vorschau-390.png` ab.
- **Kontaktbogen**, gebaut mit den echten Daten aus dem Repo, im Look-Takt (Zahl des Tages vom 24.10. mit dem Datum des Donnerstags):
  - die 5 Vorlagen: `docs/story/kontaktbogen-vorlagen.png`
  - die 5 Auflösungen: `docs/story/kontaktbogen-aufloesungen.png`
- **Weitere Tests, alle grün:**
  - die Selbsttests von `kurzlinks.py` (6 Kurzlinks) und `kurzlinks.py --pruefen`
  - `utm.py --selftest` (prüft auch den Spiegel in `utm.js`)
  - `content_wache.py`, `look_takt.py` und `karussell.py`
  - Secret-Scan sauber
- **Offen nach dem Merge:**
  - **echter Lauf in Discord:** Aus dieser Umgebung geht das nicht, weil die Secrets nur in GitHub liegen. Nach dem Merge bitte einmal von Hand starten, siehe unten.
  - **301 für /story:** GitHub Pages leitet `/story` mit 301 auf `/story/` weiter, von dort führt die meta refresh auf die UTM-Adresse, genau wie bei `/ig` und `/x`. Einen echten 301 direkt auf die UTM-Adresse kann Pages nicht. Ich prüfe das nach dem Deploy und trage es nach.

## PR-Nummern
- dieser PR: folgt im Sammelfenster 16:00
- Zusammenhang: #134 (Rahmen), #137 und #139 (Jekyll)

## Offene Fragen an Ben
1. **utm_source:** Im Auftrag stand `utm_source=ig`. Ich habe `instagram` genommen. `ig` steht nicht in `utm.QUELLEN`; es würde in der Auswertung eine zweite Zeile neben `instagram` eröffnen, und `kurzlinks.py` bricht bei einer unbekannten Quelle ab. Die Story unterscheidet sich trotzdem durch `utm_medium=story`. Soll es doch `ig` sein? Dann trage ich `ig` als eigene Quelle ein.
2. **„kanal-links“:** Eine Datei oder einen Abschnitt mit diesem Namen finde ich weder im Repo noch in den Docs. Wo liegt die Liste? Vielleicht in pulse-studio, auf pulsehawk-site oder in Notion? Den Eintrag ergänze ich dann.
3. **Discord-Kanal:** Ich habe #moderator-only (`DISCORD_WEBHOOK_OPS`) genommen; dort kommen auch die Karussell-Entwürfe an. Falls die Story-Vorlagen in einen anderen Kanal sollen, brauche ich den Namen des Secrets. Den Wert bitte nicht schicken.
4. **Donnerstag ohne Erklärer:** Steht nichts in `story-plan.json` und keine frische `data/karussell-story.json`, nimmt der Donnerstag die Zahl des Tages mit ihrem Satz. Ihre Schlagzeile vergleicht oft mit Bitcoin, das lässt die Wache in der Story nicht zu. Die Anleitung sagt dann „zahl des tages …, kein erklaerer gefunden“. Soll die Routine „Donnerstags-Erklärer vorbereiten“ zusätzlich einen Eintrag `do` in `story-plan.json` schreiben? Dann steht dort der stärkste Satz des Erklärers.
5. **Montag:** Um 07:45 am Montag ist das neue Weekly noch nicht da. Das Quiz nimmt die letzte Ausgabe, im Bild steht ihr Datum („week to 17 oct“). Passt das, oder soll das Quiz erst nach dem Weekly kommen? Dafür müsste nur der Takt später laufen, der Hinweis „posten 17:30“ bleibt.
6. **Beobachtung:** In `TAKTE` in `deploy/c2/setup.sh` fehlen threads, die Karussells und das Uhrwerk. `story-vorlage` habe ich eingetragen. Falls die anderen von Hand verlinkt sind, ist das in Ordnung.

## Was Ben tun muss
1. **PR prüfen und mergen.** Er enthält die Workflow-Datei `story-vorlage.yml` und die c2-Dateien (`takt-story-vorlage.timer`, `ausloesen.sh`, `setup.sh`, README).
2. **Auf c2:** einmal `sudo ./setup.sh nachziehen`. Danach steht `takt-story-vorlage` in `systemctl list-timers 'takt-*'`.
3. **Echter Lauf:** einmal von Hand starten, Actions, `story-vorlage`, Run workflow, mit `datum` leer und `senden` an. In #moderator-only sollten dann PNG, Anleitung und „posten 17:30“ ankommen. Heute (Samstag) kommt nur eine Auflösung, und auch die nur, wenn gestern eine Vorlage gesendet wurde. Für den ersten echten Lauf darum `datum` auf einen Werktag setzen, zum Beispiel 2026-10-26: der Lauf baut dann die Montags-Vorlage. Damit steht der Montag schon im Log.
4. **Fragen 1 bis 5 oben beantworten.**
