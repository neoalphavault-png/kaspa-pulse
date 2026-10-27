# Bericht 27.10.2026: einfache Instagram-Story Di und Do, automatisch

Auftrag von Ben vom 27.10.2026. Workflow- und c2-Dateien kommen als PR: Claude prüft, Ben merged und setzt ein.

## Was gemacht wurde
- **`scripts/ig_story_auto.py`**, mit Selbsttest.
  - **Gestaltung als Köder** (Nachtrag von Ben am 27.10.2026). Keine flache Grafik, denn ein klickbarer Sticker geht über die API nicht. Die Story soll neugierig machen und aufs Profil führen.

    | Wo | Was |
    | --- | --- |
    | oben, Sekunde null | der Haken als Frage, Archivo 900, 80 px |
    | Mitte | die Kernzahl als Antwort, 220 px in #49EACB, darunter ihr Satz, Datum und counted, source oder computed |
    | unten | „full breakdown on our profile“ und die Wortmarke KASPA PULSE, kein Falke |

    - Marke dunkel: #080B0F, #F2F5F4, #49EACB.
    - Breite Zahlen werden geteilt („51.20“ groß, „%“ daneben). Ab fünf Stellen wird gekürzt (287,000 wird 287K), die genaue Zahl steht dann im Satz.
  - **Inhalt:**
    1. Die Tagesgrafik des Tages: Zahl, Satz, Datum und Herkunft aus `data/instagram-log.json`. Nur wenn sie um 07:30 ausgeliefert wurde und um 09:30 im Feed ist, dann stimmt auch „full breakdown on our profile“.
       - **Haken:** eine feste Frage je Form, die Zahl beantwortet sie. Zum Beispiel Form 11 „how much KAS has not moved in a year?“, Form 4 „how many blocks does kaspa add while you sleep?“, Form 5 „what actually pays kaspa miners?“.
    2. Gibt es keine, die Zahl des Tages vom selben Tag.
       - **Haken:** „did you expect this number?“
       - **Kernzahl:** die hervorgehobene Zahl aus ihrer Überschrift, also „583x“ und nicht der Dollarwert.
       - **Unten:** „more numbers like this, link in bio“.
    3. Sonst geht keine Story raus.
  - **Prüfung vor jeder Story:**
    - eine große Zahl, ein Datum, counted, source oder computed, der Haken endet mit „?“
    - die Textregeln von `content_wache`
    - die Kurs- und Köderwache der Story-Vorlage, also kein „$“, keine Kaufsprache und kein billiger Köder wie „secret“ oder „you won't believe“
    - beim Rendern die `content_wache` im Profil `story`: sichere Fläche 60–900 × 270–1500, Mindestgrößen, Kontrast
  - **Ohne Zusatz:** kein Sticker, keine Caption.
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
  - Köder: Haken der Form, Kernzahl aus der Überschrift statt Dollarwert, „$“, billiger Köder und ein Haken ohne Frage fallen auf, große Zahlen werden gekürzt
  - gerendert 1080 × 1920 auf dunklem Grund, `content_wache` im Profil `story` grün
  - Container mit `media_type=STORIES`, ohne Sticker und Caption, Token nie in der Ausgabe
- **Mit den echten Daten von heute:** Die Story aus Tagesgrafik Form 11 fragt „how much KAS has not moved in a year?“ und antwortet „51.20%“, darunter „of all KAS in circulation not moved in a year“ und „source kaspalytics, age estimated by daa score, 26 oct 2026“. Der Rückfall mit der Zahl des Tages vom 27.10.2026 („583x“) ist ebenfalls grün.
- **Weitere Prüfungen:** `instagram.py --selbsttest` grün, `bash -n` für setup.sh und ausloesen.sh grün, Secret-Scan sauber.
- **Kontaktbogen:** `docs/ig-story-auto/kontaktbogen-koeder-2026-10-27.png`. Er zeigt vier Stories: heute (Form 11), den Rückfall mit der Zahl des Tages, Form 4 mit gekürzter Zahl und Form 5. Rot umrandet ist die sichere Fläche.
- **Alle Formen:** Die elf Haken bestehen alle Wachen. Mit den echten Zahlen aus dem Instagram-Log haben die Formen 1 bis 6 und 8 bis 11 gerendert und sind grün. Form 7 (Community) hatte noch keinen Eintrag.

## Abnahme, Probelauf
**Bestanden am 27.10.2026, nach dem Merge von #160.**
- `ig-story-auto.yml` mit `modus=probe` auf main, Lauf 40530044466, grün.
- **Plan:** „probe, von hand, nur nach #moderator-only“.
- **Gebaut:** die Köder-Story aus der Tagesgrafik von heute (Form 11), `ig/story-auto-2026-10-27.jpg`, gerendert und durch die Story-Wache.
- **Geschickt:** nach #moderator-only, Discord antwortet mit HTTP 200.
- **Übersprungen,** wie es bei einer Probe sein muss: JPEG-Commit, Posten bei Instagram und Merkdatei. Bei Instagram ist nichts angekommen.

## PR-Nummern
- #160, Workflow, Skript, c2-Takt und dieser Bericht

## Offene Fragen an Ben
1. **Haken:** Passen dir die elf Fragen je Form? Sie stehen in `HAKEN` in `scripts/ig_story_auto.py`, jede Änderung ist eine Zeile.
2. **Konflikt mit #144:** #144 ändert ebenfalls `TAKTE` in `setup.sh` und das Taktgeber-README. Wer zuerst gemergt wird, ist egal, den zweiten rebase ich dann auf main.

## Was Ben tun muss
Steht im Discord-Abschnitt, der beim Push dieses Branches nach #moderator-only geht.

<!-- discord -->
**Automatische IG-Story Di und Do, Lieferung 27.10.2026**
- **PR:** #160 (Workflow ig-story-auto.yml, Skript, c2-Takt Di und Do 17:30)
- **Als Köder gestaltet:** oben eine Frage, in der Mitte die große Kernzahl mit Datum und Herkunft, unten „full breakdown on our profile“. Die Zahl kommt aus der Tagesgrafik des Tages, sonst aus der Zahl des Tages. Kein Sticker, keine Caption.
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
