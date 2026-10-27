# Bericht 27.10.2026: einfache Instagram-Story Di und Do, automatisch

Auftrag von Ben vom 27.10.2026. Workflow- und c2-Dateien kommen als PR: Claude prüft, Ben merged und setzt ein.

## Was gemacht wurde
- **`scripts/ig_story_auto.py`**, mit Selbsttest.
  - **Inhalt:**
    1. Die Tagesgrafik des Tages: das JPEG, das um 09:30 auf den Feed ging, mit Zahl, Datum und Herkunft aus `data/instagram-log.json`.
    2. Gibt es keine, die Zahl des Tages (`graphics/number-of-day.png`), aber nur, wenn `data/number-of-day.json` vom selben Tag ist.
    3. Sonst geht keine Story raus.
  - **Prüfung:** Vor jeder Story prüft das Skript, dass eine Zahl, ein Datum und counted, source oder computed dastehen. Die Texte laufen durch die Textregeln von `content_wache`, Kaufsprache und Kursziele fallen auf. Beide Bilder sind in ihrer eigenen Kette schon durch alle Wachen gegangen.
  - **Bild:** 1080 × 1920. Die 4:5-Grafik sitzt in der Mitte, oben und unten je 285 px in ihrer eigenen Randfarbe. Damit liegt nichts in den Flächen, die Instagram mit Namen und Antwortfeld belegt.
  - **Ohne Zusatz:** kein Sticker, keine Caption, kein Link.
  - **Posten:** über die Graph API mit `media_type=STORIES`, wie beim Karussell mit `INSTAGRAM_PAGE_TOKEN`. Der Token geht nur im Kopf mit, jede Ausgabe läuft durch `instagram.sauber()`. Hostnamen aus der Quelle der Zahl des Tages stehen im Log nur als Namen.
- **`.github/workflows/ig-story-auto.yml`:**

  | Modus | Wann | Was passiert |
  | --- | --- | --- |
  | `probe` | Dispatch von Hand, jeder Tag | nur nach #moderator-only, nie zu Instagram |
  | `entwurf` | Takt oder Zeitplan ohne `IG_STORY_AUTO_LIVE=true` | nur nach #moderator-only |
  | `scharf` | Takt oder Zeitplan, `IG_STORY_AUTO_LIVE=true` | Story geht raus, siehe Bedingungen unten |
  | `aus` | sonst | nichts, der Grund steht im Log |

  - **Bedingungen für scharf:**
    - Di oder Do
    - zwischen 17:15 und 19:30 Berlin
    - `IG_STORY_AUTO_STOPP` steht nicht auf heute oder „immer“
    - heute noch keine Story in der Merkdatei `data/ig-story-auto-log.json`
  - **Ablauf scharf:** JPEG nach `ig/` committen, warten bis kaspapulse.com es ausliefert, Container anlegen, Status prüfen, veröffentlichen, Merkdatei schreiben, Bestätigung nach #moderator-only.
- **Takt auf c2:** `takt-ig-story-auto.timer`, Di und Do 17:30 Berlin.
  - Dazu der Eintrag in `ausloesen.sh` (`modus=takt`), in `TAKTE` in `setup.sh` und eine Zeile im README.
  - **Warum ein Takt:** Geplante GitHub-Läufe kommen in diesem Konto 5 bis 8 Stunden zu spät. Der Cron von number-of-day für 08:12 UTC lief vom 21. bis 26.10.2026 zwischen 13:10 und 16:18 UTC.
  - Der Cron `30 16 * * 2,4` steht wie gewünscht trotzdem im Workflow, als Rückfall. Wegen des Zeitfensters postet ein verspäteter Lauf nie.
  - `systemd-analyze calendar` bestätigt: Di und Do 16:30 UTC, also 17:30 Berlin im Winter. Systemd rechnet die Sommerzeit selbst um.

## Prüfung
- **Selbsttest `ig_story_auto.py`, alle Fälle grün:**
  - probe an jedem Tag, Mittwoch aus, ohne LIVE nur Entwurf
  - LIVE im Fenster scharf, ein 6 Stunden verspäteter Cron nie scharf
  - Veto auf heute und auf „immer“
  - Merkdatei: nur eine Story je Tag, ein fehlgeschlagener Versuch sperrt nicht
  - Reihenfolge Tagesgrafik vor Zahl des Tages, ohne beides Stopp
  - Echtzeitwort, fehlende Herkunft, fehlendes Datum und Kaufsprache fallen auf
  - Bild 1080 × 1920, Rand in der Randfarbe
  - Container mit `media_type=STORIES`, ohne Sticker und Caption, Token nie in der Ausgabe
- **Mit den echten Daten von heute:** Die Story aus der Tagesgrafik Form 11 trägt „51.20% of all KAS in circulation not moved in a year“, 26 oct 2026, source kaspalytics. Der Rückfall „Zahl des Tages“ vom 27.10.2026 ist ebenfalls grün.
- **Weitere Prüfungen:** `instagram.py --selbsttest` grün, `bash -n` für setup.sh und ausloesen.sh grün, Secret-Scan sauber.
- **Kontaktbogen:** `docs/ig-story-auto/kontaktbogen-2026-10-27.png`. Links die Story aus der Tagesgrafik, rechts der Rückfall. Rot umrandet sind die Flächen, die Instagram belegt.

## Abnahme, Probelauf
Noch offen. Ein Dispatch geht nur für Workflows, die auf main liegen. Der Versuch auf dem Branch endete am 27.10.2026 mit 404.

Direkt nach dem Merge starte ich `ig-story-auto.yml` mit `modus=probe`. Die Story kommt dann nur nach #moderator-only, das Ergebnis trage ich hier nach. Bis dahin zeigen der Kontaktbogen und der Lauf mit den echten Daten von heute, was die Probe schickt.

## PR-Nummern
- #160, Workflow, Skript, c2-Takt und dieser Bericht

## Offene Fragen an Ben
1. **Datum auf dem Bild:** Die Story wiederholt um 17:30 die Tagesgrafik, die um 09:30 schon im Feed war. Auf ihr steht die Messzeit des Morgens („27 oct 2026, 06:30 utc“). Passt das, oder soll die Story lieber immer die Zahl des Tages zeigen?
2. **Konflikt mit #144:** #144 ändert ebenfalls `TAKTE` in `setup.sh` und das Taktgeber-README. Wer zuerst gemergt wird, ist egal, den zweiten rebase ich dann auf main.

## Was Ben tun muss
Steht im Discord-Abschnitt, der beim Push dieses Branches nach #moderator-only geht.

<!-- discord -->
**Automatische IG-Story Di und Do, Lieferung 27.10.2026**
- **PR:** #160 (Workflow ig-story-auto.yml, Skript, c2-Takt Di und Do 17:30)
- **Inhalt:** die Tagesgrafik des Tages als Story 1080 x 1920. Ohne sie die Zahl des Tages. Kein Sticker, keine Caption, kein Link.
- **Scharf nur mit IG_STORY_AUTO_LIVE=true:** sonst nur der Entwurf hier. Veto mit IG_STORY_AUTO_STOPP, je Tag höchstens eine Story.
- **Warum zusätzlich ein Takt auf c2:** Geplante GitHub-Läufe kommen hier 5 bis 8 Stunden zu spät. Der Cron bleibt als Rückfall, postet aber nie verspätet.
- **Bericht:** berichte/2026-10-27-ig-story-auto.md, Kontaktbogen in docs/ig-story-auto/
<!-- teil -->
📤 VON HAND, 1 von 2: **mergen und den Takt einspielen**
1. PR #160 auf GitHub mergen
2. Auf c2 den neuen Takt nachziehen, Befehl zum Kopieren:
```
sudo bash deploy/c2/setup.sh nachziehen
```
3. Mir Bescheid geben, dann starte ich den Probelauf. Er geht nur hierher.
<!-- teil -->
📤 VON HAND, 2 von 2: **scharf schalten, erst nach einem sauberen Probelauf**
In kaspa-pulse unter Settings, Secrets and variables, Actions, Variables:
1. Neue Variable, Name:
```
IG_STORY_AUTO_LIVE
```
Wert:
```
true
```
2. Veto für einen Tag: Variable IG_STORY_AUTO_STOPP mit dem Datum, zum Beispiel
```
2026-10-29
```
Für immer aus:
```
immer
```
<!-- /discord -->
