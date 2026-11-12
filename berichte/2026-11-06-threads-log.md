# Bericht 6.11.2026: Threads-Lauf rot am 4.11. und 5.11., Log robust (Nachtrag 6.11., Wartezeit 1500 s)

Auftrag von Ben vom 5.11.2026. Ziel ist, dass der Lauf am Fr 6.11. um 17:10 Berlin komplett grün ist. Die Änderung betrifft `.github/workflows/threads.yml`, deshalb merged Ben.

## Nachtrag 6.11.2026, Wartezeit auf das Bild 1500 s
Ben hat am 6.11. dem Vorschlag aus „Risiko für Fr 6.11. 17:10“ zugestimmt.

- **Warum ein neuer PR:** #260 war um 09:13 Berlin schon gemergt. Die Änderung kommt deshalb in einen eigenen PR von main, Branch `fix/threads-bild-frist`.
- **Kopf der Änderung:** `75cae65`. Der Commit mit diesem Nachtrag liegt direkt darauf.
- **Wartezeit:** `scripts/threads.py` hat die Konstante `BILD_FRIST = 1500`. Der Schritt „jpeg auf kaspapulse.com“ in `threads.yml` wartet jetzt mit `frist=threads.BILD_FRIST` statt mit 600 s. Instagram und das Karussell behalten 600 s.
- **Job-Zeit:** `timeout-minutes` steigt von 30 auf 45. 1500 s Wartezeit plus etwa 2 min für den Rest des Laufs passen hinein, und das Zeitfenster bis 19:30 reicht ebenfalls.
- **Selbsttest:** 79 Fälle, 0 falsch. Neu sind drei Fälle. Sie prüfen die Frist 1500 s, dass `timeout-minutes` die Frist plus 15 min abdeckt und dass der Workflow `threads.BILD_FRIST` nutzt.
- **Prüfung:** YAML lädt. `url_warten` nimmt `frist` an. Secret-Scan ohne Fund.

---

## 1. Ursache am 5.11., Lauf threads #20 (42061797050)
**Was passiert ist**
- Veröffentlicht wurde um 17:11:45 Berlin, mit Container 17894169666502428 und Media 17975335962157821.
- Danach legte „log sichern“ den Commit `threads log [bot]` an (1 Datei, 8 Zeilen). `git pull --rebase` meldete „Current branch main is up to date“.
- Der Push kam zurück mit „remote: fatal error in commit_refs_rules“ und „! [remote rejected] main -> main“.

**Rulesets und Branch-Schutz von main**
- `rules/branches/main` zeigt nur das Ruleset 25866330 „main-schutz“, aktiv, Ziel der Default-Branch.
- Es enthält zwei Regeln, `deletion` und `non_fast_forward`. Es gibt keine Bypass-Liste, keine Pfadregel, keine Größenregel und keine Pflicht für Status-Checks oder Signaturen.
- Der klassische Branch-Schutz (`branches/main/protection`) ist mit dem Token dieser Sitzung nicht lesbar, die API antwortet mit 403. Das Ruleset ist die einzige Regel, die `rules/branches/main` meldet.

**Vergleich mit Bot-Pushes, die durchgingen**

| | threads log, 5.11. 17:11 | threads bild, 5.11. 17:10 | threads log, 1. bis 3.11. | entity x state update |
| --- | --- | --- | --- | --- |
| Pfad | `data/threads-post-log.json` | `ig/…-threads.jpg` | `data/threads-post-log.json` | `data/…` |
| Größe | 8 Zeilen, Datei 4.4 KB | ein JPEG | je 8 Zeilen | klein |
| Autor | kaspa-pulse-bot, bot@kaspapulse.com | derselbe | derselbe | derselbe |
| Token | `GITHUB_TOKEN` des Laufs | derselbe, im selben Lauf | derselbe | `GITHUB_TOKEN` |
| Push | abgelehnt | durch (`f800061`) | durch (`29d373d`, `9aed3ea`, `0dff301`) | durch |

**Schluss**
- Der Commit war ein Fast-Forward, und keine Regel des Rulesets trifft ihn.
- Derselbe Bot hat mit demselben Token im selben Lauf 80 s vorher gepusht, und denselben Pfad an drei Tagen davor.
- „fatal error in commit_refs_rules“ ist deshalb ein interner Fehler von GitHub bei der Prüfung der Regeln, keine Sperre. Ein zweiter Versuch hätte nach aller Wahrscheinlichkeit gereicht.
- GitHub hatte an diesem Nachmittag weitere Störungen. Das Pages-Deploy von `bac8ad7` um 16:07 Berlin hing 11 Minuten, siehe Nachtrag vom 5.11. in `berichte/2026-10-30-look-v2.md`.

**Folge**
- Danach lief „rot nach ops-log“ auf `failure()` und meldete „threads ist rot, heute kein post“. Das war falsch, der Post war draußen.

## 2. Lauf threads #19 am 4.11. (41864653528)
- **Gesamtdauer:** Der Lauf stand 18 min 57 s offen, von 17:10:06 bis 17:29:03 Berlin. Der Job selbst lief 10 min 19 s, von 17:10:09 bis 17:20:28.
- **Schritt, der hing:** Schritt 8 „jpeg auf kaspapulse.com“, von 17:10:19 bis 17:20:23.
  - Der Push des Bildes ging durch (`9746e7b`).
  - Dann wartete `instagram.url_warten` 600 s auf das Bild auf kaspapulse.com und brach ab.
  - Log-Zeile 17:20:23: `scripts/instagram.py, line 357, in url_warten`, „bild nach 600 s nicht oeffentlich, zuletzt http 404“.
- **Ursache:** Das Pages-Deploy für `5483073` (entity-x-Bot, 17:07) hing 14 Minuten und wurde um 17:20:55 abgebrochen. Das Deploy für `9746e7b` war erst um 17:24:10 fertig, 4 Minuten nach dem Abbruch des Laufs.
- **Veröffentlicht:** nein. Schritt 9 „container, status, veroeffentlichen nur wenn scharf“ wurde übersprungen, es gab keinen Container und keinen Post.
- **Meldung:** „threads ist rot, heute kein post“ war an diesem Tag richtig.
- **Log:** Es gibt keinen Eintrag für den 4.11., weil das Log nur veröffentlichte Posts führt. Nachzutragen ist nichts.

## 3. „log sichern“ robust (`scripts/threads.py log-sichern`)
- **Ablauf:** Vor jedem Push läuft `git pull --rebase --autostash origin main`. Auf den ersten Push folgen bis zu drei Wiederholungen nach 10, 20 und 40 s, zusammen also höchstens 4 Pushes in 70 s.
- **Push klappt:** Der Schritt ist grün, wie bisher.
- **Push scheitert, Post ist draußen:** Der Schritt bleibt grün. Nach #ops-log geht „threads gepostet, log nicht gesichert“ mit dem Link auf den Lauf.
- **Push scheitert, kein Post:** Der Schritt ist rot.
- **Nachholen:** Der neue Schritt „log nachholen“ läuft vor der Tagessperre. Er fragt die eigenen Threads-Posts der letzten 7 Tage über die API ab (`/{user}/threads`, Felder id, text, timestamp).
  - Jeder Post, der im Log fehlt, kommt als Eintrag mit `nachgeholt` dazu, der Tag ist der Berliner Tag des Zeitstempels.
  - Ein Eintrag ohne Text bekommt seinen Text.
  - Damit hält die Sperre „ein Post am Tag“ auch dann, wenn ein Log-Push verloren ging.
  - Ein Fehler in diesem Schritt hält den Post nicht auf (`continue-on-error`).
- **Wann gesichert wird:** „log sichern“ läuft jetzt immer, nicht nur wenn der Post fällig ist. Ein nachgeholter Eintrag wird so auch an einem Tag ohne Post gesichert.

## 4. „kein post“ nur ohne Post
- `threads.py posten` schreibt direkt nach `threads_publish` die Schritt-Ausgabe `veroeffentlicht=1`, noch bevor das Log geschrieben wird.
- „rot nach ops-log“ wertet sie aus:
  - Ohne Post meldet der Lauf „threads ist rot, heute kein post“.
  - Mit Post und trotzdem rotem Lauf meldet er „threads gepostet, der lauf ist trotzdem rot“.
- Ein abgelehnter Log-Push macht den Lauf nicht mehr rot, wenn der Post draußen ist.

## 5. Nachgetragene Log-Einträge
- **5.11.:** nachgetragen mit Container 17894169666502428, Media 17975335962157821 und Bild `tagesgrafik-2026-11-05-form02-threads.jpg`.
  - Die IDs stammen aus dem Log von Lauf 42061797050.
  - Ein zweiter Post wurde nicht angelegt.
  - Die Threads-API und das Artefakt der Tagesgrafik sind aus meiner Arbeitsumgebung gesperrt. Der Text ist deshalb leer, und der Eintrag trägt den Vermerk `nachgetragen`. Beim Lauf am Fr 6.11. fragt „log nachholen“ die API ab, findet Media 17975335962157821 und setzt den Text ein. Steht die ID dort nicht, kommt kein Text, und ich sehe mir das im Lauf an.
- **4.11.:** kein Eintrag, siehe Punkt 2, es gab keinen Post.
- **Tagessperre:** Der 5.11. ist jetzt gesperrt, der 6.11. ist frei. Geprüft mit `darf_posten`.

## 6. Selbsttest
`python3 scripts/threads.py --selbsttest`: 76 Fälle, 0 falsch. Neu sind:
- **Push abgelehnt nach Veröffentlichung:**
  - Ergebnis „nicht gesichert“, also grün.
  - Pausen 10, 20 und 40 s, 4 Pushes, `pull --rebase` vor jedem.
  - Meldung „threads gepostet, log nicht gesichert“.
- **Push abgelehnt ohne Veröffentlichung:** Ergebnis „rot“, dieselben Versuche, keine Meldung „gepostet“.
- **Weitere Fälle:**
  - Der zweite Push geht durch.
  - Ein unverändertes Log erzeugt keinen Commit.
  - `nachtragen` füllt einen fehlenden Text und holt einen fehlenden Post mit Berliner Tag.
  - Zweimal nachtragen ändert nichts.
  - Ein nachgeholter Post sperrt den Tag.

Zusätzlich lief `log_sichern` mit echtem git gegen ein lokales Repo, dessen Hook jeden Push ablehnt. Ergebnis nach 4 Versuchen „nicht gesichert“ mit Meldung. Ohne Hook ging der Push im ersten Versuch durch.

## Risiko für Fr 6.11. 17:10
- **Was am 4.11. passiert ist:** Der Threads-Lauf wartet 600 s darauf, dass kaspapulse.com das Bild ausliefert. Der entity-x-Bot committet jede Stunde um :07. Hängt dessen Pages-Deploy wie am 4.11. 17:07 oder am 5.11. 16:07, reichen 600 s nicht.
- **Was dieser PR daran ändert:** nichts.
- **Vorschlag:** die Wartezeit nur für Threads auf 1500 s heben und `timeout-minutes` auf 45. Das Zeitfenster reicht bis 19:30. Am 4.11. wäre der Post damit um 17:24 rausgegangen. Soll ich das in diesen PR nehmen?

## Prüfung
- Selbsttest grün, YAML lädt.
- Secret-Scan vor dem Push ohne Fund. Im Bericht stehen keine Werte von Tokens.
- Nicht angefasst: `post_manifest.py`, `uhrwerk.yml`, `insights_sammler.py`, `data/insights/`.
