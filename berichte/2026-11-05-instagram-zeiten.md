# Instagram-Zeiten nach den Insights

Auftrag von Ben vom 5.11.2026 (Auftrag A), vorbereitet am 5.11.2026 auf dem `main` nach dem Publish-Fix (Auftrag B, `39a7481`). Die PR berührt `deploy/` und `.github/workflows/`. Claude prüft, Ben merged, kein Selbst-Merge: `automerge-claude.yml` lässt den Branch wegen der gesperrten Pfade stehen.

## Nachtrag 6.11.2026, Wochen-Karussell Sa 13:00
Ben hat am 6.11. entschieden, das Wochen-Karussell auf Sa 13:00 zu legen und den Entwurf auf Sa 11:00. Tagesgrafik (12:30) und Karussell laufen damit nicht mehr gleichzeitig, und die Reihenfolge im Profil steht fest: erst die Tagesgrafik, darüber das Karussell.

| Was | Stand #257 vorher | jetzt |
| --- | --- | --- |
| `takt-karussell-woche.timer` | Sa 12:30 | `OnCalendar=Sat *-*-* 13:00:00 Europe/Berlin` |
| `takt-karussell-woche-entwurf.timer` | Sa 10:30 | `OnCalendar=Sat *-*-* 11:00:00 Europe/Berlin` |
| `karussell.POSTZEIT["woche"]` | 12:30 | 13:00 |
| Community-Hinweis | Sa ab 12:45 | Sa ab 13:15 |
| Veto-Satz | geht um 12:30 raus | geht um 13:00 raus |

- **Beschreibungen:** Die `Description` beider Timer sind angepasst. `karussell.yml` hat nur den Kommentar und die Beschreibung der Eingabe `art` geändert.
- **Weitere Dateien:** `deploy/c2/taktgeber/README.md`, die Kommentare in `look_takt.py` und die Docstrings in `karussell.py` und `karussell_post.py` sind nachgezogen.
- **systemd-analyze calendar:**
  - `Sat *-*-* 11:00:00 Europe/Berlin` ergibt Sa 7.11. 10:00 UTC, danach Sa 14.11. 10:00 UTC.
  - `Sat *-*-* 13:00:00 Europe/Berlin` ergibt Sa 7.11. 12:00 UTC, danach Sa 14.11. 12:00 UTC.
- **Selbsttests:** `karussell_post.py`, `karussell.py` und `look_takt.py` mit je 0 Fehlern.
  - Neu ist der Fall „12:30 berlin, die zeit der tagesgrafik, ist nicht im fenster“.
  - Die Postzeit ist Sa 13:00 = 12:00 UTC, der Community-Hinweis „Sa ab 13:15“, der Veto-Satz „geht um 13:00 raus“.
- **Dry Run Fenster am Sa 7.11.:** fällig von 12:45 bis 14:30. Nicht fällig um 10:30, 11:00, 12:30, 12:44 und 14:31.
- **Am Rand:** Der Meme-Entwurf läuft weiter Sa 13:00, gleichzeitig mit dem Wochen-Post. Das ist nur ein Entwurf, kein Post, und die Concurrency-Gruppe ist je Art getrennt (`karussell-woche`, `karussell-meme`). Die Reihenfolge im Profil berührt das nicht.
- **Für Ben:** Merge heute vor 12:15. Danach auf c2 `sudo /opt/kaspa-pulse/deploy/c2/setup.sh nachziehen`. `list-timers` zeigt für `takt-karussell-woche-entwurf` Sa 10:00 UTC und für `takt-karussell-woche` Sa 12:00 UTC.
- **Kopf:** wird nach dem Push eingetragen.

---

## Anlass

- Die Follower sind laut Insights Mo bis Sa 12 bis 18 Uhr und So 15 bis 18 Uhr aktiv.
- Die Feed-Bilder liefen bisher um 09:30, also bevor jemand da ist.

## Was geändert ist

| Was | vorher | jetzt | Datei |
| --- | --- | --- | --- |
| Instagram-Bild, Takt | täglich 09:30 | täglich 12:30 | `deploy/c2/taktgeber/takt-instagram-bild.timer` |
| Instagram-Bild, Fenster | 09:25 bis 11:30 | 12:25 bis 14:30 | `scripts/instagram.py`, `FENSTER_BERLIN` |
| Reel | Di bis So 12:00, Mo 17:00 | Di bis So 15:30, Mo 17:00 | `deploy/c2/taktgeber/takt-reel.timer` |
| Karussell Woche, posten | Sa 11:00 | Sa 13:00 | `takt-karussell-woche.timer` und `scripts/karussell.py`, `POSTZEIT["woche"]` |
| Karussell Woche, Entwurf | Sa 09:00 | Sa 11:00 | `takt-karussell-woche-entwurf.timer` |

Alle Zeiten gelten in Berlin-Zeit.

- **Unverändert:** Discord-Post der Tagesgrafik (07:30), YouTube-Short (Di bis So 12:00) und das Schalter-Karussell Fr 6.11. (Entwurf 09:00, posten 11:00).
- **Reel:** Der Kommentar im Timer sagt, dass der Reel ab jetzt von der Short-Zeit entkoppelt ist und erst nach dem Merge in pulse-studio aktiv werden darf.
- **`karussell.POSTZEIT`:** Ohne diese Änderung läge der Posten-Lauf um 13:00 außerhalb des Fensters (11:00 −15/+90 min) und würde nie posten. Der Entwurf hätte außerdem „geht um 11:00 raus“ geschrieben. Der Termin für die Kaspa-Community steht jetzt „Sa ab 13:15“.
- **Selbsttests angepasst:**
  - `instagram.py`: fällig um 12:35, nicht fällig um 12:05, nicht fällig ab 14:30 (14:29 noch fällig), nicht mehr fällig um 09:35, Winterzeit 11:30 UTC = 12:30 Berlin. Fenster und Tagessperre für Takt und Hand werden auf neuen Zeiten geprüft.
  - `karussell_post.py`: Sa 13:00 = 12:00 UTC, 11:00 und 12:30 sind nicht im Fenster, Community „Sa ab 13:15“.
  - `karussell.py`: Veto-Satz „geht um 13:00 raus“.
  - `look_takt.py`: Probezeit im Trockenlauf 12:40 statt 09:40.
- **Nachgezogene Kommentare und Texte:**
  - `.github/workflows/tagesgrafik.yml`: nur Kommentare, cron und Jobs unverändert.
  - `.github/workflows/karussell.yml`: Kommentar und Beschreibung der Eingabe `art`.
  - `deploy/c2/taktgeber/README.md`: Zeitplan, Fenster und ein neuer Abschnitt „Instagram-Zeiten nach den Insights“.
  - `deploy/c2/setup.sh`: nur die Kontrollanzeige am Ende von `nachziehen`, jetzt 12:30 und Di bis So 15:30.
  - Ops-Text in `scripts/tagesgrafik.py`: „caption für den Post um 12:30“.
  - Kommentare in `scripts/look_takt.py`.

## Selbsttests

| Skript | Ergebnis |
| --- | --- |
| `scripts/instagram.py --selbsttest` | 0 Fehler |
| `scripts/karussell_post.py --selbsttest` | 0 Fehler |
| `scripts/karussell.py --selbsttest` | 0 Fehler |
| `scripts/look_takt.py --selbsttest` | 0 Fehler |
| `scripts/look_motor.py --selbsttest` | 0 Fehler |
| `scripts/ig_story_auto.py --selbsttest` | alle bestanden |
| `scripts/tagesgrafik.py --selftest` | 0 Fehler |

- Die Kalenderzeilen sind mit `systemd-analyze calendar` geprüft. Die nächsten Termine in UTC (Winterzeit, Berlin = UTC+1):

| Timer | Termin Berlin | nächster Termin |
| --- | --- | --- |
| `takt-instagram-bild` | täglich 12:30 | Fr 6.11. 11:30 UTC |
| `takt-reel` | Di bis So 15:30 | täglich 14:30 UTC |
| `takt-reel` | Mo 17:00 | Mo 9.11. 16:00 UTC |
| `takt-karussell-woche-entwurf` | Sa 11:00 | Sa 7.11. 10:00 UTC |
| `takt-karussell-woche` | Sa 13:00 | Sa 7.11. 12:00 UTC |

- `setup.sh` hat die Syntaxprüfung mit `sh -n` bestanden. Beide Workflows sind gültiges YAML.

## Dry Run auf dem Betriebspfad

`instagram.main(["faellig", "--takt", ...])` lief mit den echten `data/tagesgrafik-log.json` und `data/instagram-log.json`.

- Die Uhr war fest auf den 5.11.2026 gestellt, also Winterzeit.
- Es gab keinen Token, und der Netzzugriff war gesperrt (ein Aufruf hätte den Lauf abgebrochen). Es ging nichts an Instagram.
- Für die Zeitreihe ist der heutige Post aus einer Kopie des Logs entfernt, damit die Tagessperre nicht alles verdeckt.

```
09:30 berlin --takt faellig=0  nicht faellig, 09:30 berlin liegt nicht zwischen 12:25 und 14:30
12:05 berlin --takt faellig=0  nicht faellig, 12:05 berlin liegt nicht zwischen 12:25 und 14:30
12:24 berlin --takt faellig=0  nicht faellig, 12:24 berlin liegt nicht zwischen 12:25 und 14:30
12:25 berlin --takt faellig=1  faellig
12:30 berlin --takt faellig=1  faellig
12:35 berlin --takt faellig=1  faellig
14:29 berlin --takt faellig=1  faellig
14:30 berlin --takt faellig=0  nicht faellig, 14:30 berlin liegt nicht zwischen 12:25 und 14:30
15:30 berlin --takt faellig=0  nicht faellig, 15:30 berlin liegt nicht zwischen 12:25 und 14:30
```

Mit dem echten Log, in dem der Post von heute 09:51 steht:

```
12:30 berlin --takt faellig=0  nicht faellig, heute (2026-11-05) schon an instagram
```

`karussell_post.faellig("woche", "2026-11-07", "takt", ...)` mit festen Zeiten und leerem Log:

```
sa 10:30 / 11:00 / 12:30 / 12:44  nicht im fenster um 13:00
sa 12:45 / 13:00 / 14:30          faellig
sa 14:31                          nicht im fenster um 13:00
```

## Reihenfolge für Ben und die Befehle auf c2

**Warum die Reihenfolge zählt:**

- Das Fenster in `instagram.py` gilt ab dem Merge sofort, weil GitHub immer `main` nimmt.
- Die Timer auf c2 gelten erst nach dem Neueinlesen.
- Das Neueinlesen (`daemon-reload`) gilt für alle Timer zugleich. Instagram-Bild und Reel lassen sich also nicht getrennt umstellen.
- `entity-x-sync` setzt `/opt/kaspa-pulse` stündlich auf `origin/main` zurück. Die neuen Timer-Dateien liegen auf c2 also spätestens eine Stunde nach dem Merge auf der Platte. Jedes spätere `daemon-reload` macht sie aktiv, auch ein fremdes.

**Reihenfolge:**

1. **Zuerst pulse-studio:** Die PR der Sitzung „shorts builder“ (Reel-Fenster auf Di bis So 15:30, Mo 17:00, Short bleibt 12:00) wird gemergt. Vorher diese PR nicht mergen. Sonst lehnt der Reel-Lauf um 15:30 ab, sobald c2 irgendwann neu einliest.
2. **Dann diese PR**, an einem Tag außer Samstag (Samstag wegen des Karussells), am besten zwischen 09:45 und 12:15 Berlin. Dann ist das Bild des Tages schon um 09:30 draußen. Die Tagessperre verhindert, dass der neue 12:30-Takt am selben Tag ein zweites Bild schickt. Nicht vor 09:30 mergen, ohne gleich auf c2 nachzuziehen: dann wäre 09:30 nicht mehr fällig, und 12:30 käme an diesem Tag nicht.
3. **Direkt danach auf c2:**

   ```sh
   sudo /opt/kaspa-pulse/deploy/c2/setup.sh nachziehen
   ```

   `nachziehen` holt `main` (`git pull --ff-only`), liest die Units neu ein (`systemctl daemon-reload`), startet jeden Takt neu und zeigt am Ende `systemctl list-timers` sowie die Ortszeiten. Neue Timer gibt es in dieser PR nicht.

   Als Nachweis danach:

   ```sh
   systemctl list-timers 'takt-instagram-bild.timer' 'takt-reel.timer' \
     'takt-karussell-woche.timer' 'takt-karussell-woche-entwurf.timer' --no-pager
   systemctl cat takt-reel.timer | grep OnCalendar
   systemd-analyze calendar 'Tue..Sun *-*-* 15:30:00 Europe/Berlin' 'Sat *-*-* 11:00:00 Europe/Berlin' 'Sat *-*-* 13:00:00 Europe/Berlin'
   ```

   **Erwartet** (`list-timers` zeigt die Zeitzone des Servers, UTC, im Winter eine Stunde vor Berlin):

   | Timer | NEXT in UTC |
   | --- | --- |
   | `takt-instagram-bild` | 11:30 |
   | `takt-reel` | Di bis So 14:30, Mo 16:00 |
   | `takt-karussell-woche-entwurf` | Sa 10:00 |
   | `takt-karussell-woche` | Sa 12:00 |

   `systemctl cat` zeigt beide `OnCalendar`-Zeilen mit 15:30 und 17:00.
4. **Am ersten Tag prüfen:**
   - Um 12:30 erscheint in Actions ein `tagesgrafik`-Lauf vom Typ `workflow_dispatch`.
   - Ab 15:30 erscheint der Reel-Lauf in pulse-studio.

## Offen

- **Samstag 12:30 doppelt:** entschieden am 6.11., siehe Nachtrag oben. Das Karussell geht um 13:00, der Entwurf um 11:00.
- **cron-Rückfall in `tagesgrafik.yml`:** Er bleibt auf 07:30 und 08:30 UTC, laut Auftrag nur Kommentare. Mit dem gemessenen Verzug von sechs bis sieben Stunden landet er bei etwa 14:30 bis 16:00 Berlin. Das ist meist nach dem Fenster. Fällt der Takt einmal aus und der Rückfall kommt vor 14:30, postet er als Ersatz. Die Tagessperre verhindert einen Doppelpost.
