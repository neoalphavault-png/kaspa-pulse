# BCH Tempnet, Versatz der Uhr in jedem Zuhörer-Lauf (7./8.11.2026)

Ben hat am 7.11. entschieden, dass jeder Zuhörer-Lauf im BCH Tempnet Versatz und Status der Uhr mitschreibt. Grund ist die Forum-Antwort an rufitnes (#35) und bitcoincashautist (#34). Ziel ist der Merge bis Mo 9.11. 12:00, damit die restlichen Läufe bis 15.11. den Versatz haben.

<!-- discord -->
BCH Tempnet, Uhr-Versatz als PR auf main bereit (Workflow, Ben merged bis Mo 12:00). Quelle ist chronyc tracking. Im Handlauf stand der Versatz am Ende bei 1,3 µs (Normal). Am Anfang war chrony noch nicht synchronisiert. Bericht berichte/2026-11-08-bch-uhr-versatz.md
<!-- /discord -->

## Was gemacht wurde

- **`scripts/bch/uhr_versatz.py`, neu:**
  - Es fragt zuerst `chronyc -n tracking` ab und übernimmt nur `System time`, `Last offset`, `RMS offset` und `Leap status`.
  - Fehlt chronyc, nimmt es `timedatectl timesync-status` und übernimmt nur `Offset`, `Jitter` und `Leap`.
  - Referenz-ID, Server, IP und Hostname übernimmt es nie. Ein Wert, der wie eine Adresse aussieht, wird verworfen.
  - Liefert keine Quelle einen Versatz, steht `"versatz": "nicht verfügbar"` da. Das Skript endet immer ohne Fehler.
  - `--selbsttest` mit Beispielausgaben beider Befehle, 6 von 6 bestanden.
- **`.github/workflows/bch-tempnet-lauscher.yml`:**
  - Neue Schritte „uhr am anfang“ vor dem Zuhören und „uhr am ende“ danach, beide mit `continue-on-error`.
  - Beim Sichern der Rohdaten kommen beide Messungen unter `uhr` (`anfang`, `ende`) ins `meta.json` des Laufs. Haben beide keine Quelle, steht zusätzlich `"versatz": "nicht verfügbar"` im `meta.json`. Kein Schritt kann den Lauf abbrechen.
  - Den Schritt, der ins `meta.json` schreibt, habe ich lokal mit und ohne Quelle getestet.

## Handlauf, erster gemessener Versatz

Lauf 42384410612, 7.11. 15:02 bis 15:07 UTC, 5 min. Gestartet über den eingebauten Testweg, einen Push auf `messung/bch-tempnet-woche2` mit `dauer_min=5`, der den Workflow aus diesem Branch ausführt. Rohdaten in `data/bch/lauscher/20261107T1502/` auf `messung/bch-tempnet`.

**Quelle: `chronyc tracking`.** Auf dem Runner ubuntu-24.04 läuft chrony.

| | Anfang 15:02:31 UTC | Ende 15:07:33 UTC |
|---|---|---|
| System time | 0.000000000 seconds slow of NTP time | 0.000001277 seconds fast of NTP time |
| Last offset | +0.000000000 seconds | +0.000002032 seconds |
| RMS offset | 0.000000000 seconds | 0.000010719 seconds |
| Leap status | **Not synchronised** | Normal |

- **Ende:** Die Uhr ging 1,3 µs vor (counted, chrony-Schätzung). Der letzte Versatz lag bei 2,0 µs, der mittlere bei 10,7 µs. Das ist weit unter der Millisekunde, mit der wir die Erste Sicht schreiben.
- **Anfang:** chrony war beim Start des Laufs noch **nicht synchronisiert**. Die Nullen sind keine Messung, sondern „noch keine Schätzung“. Der Runner war erst Sekunden alt.
- **Folge für die bisherigen Läufe:** Auch dort lief der Zuhörer vermutlich in den ersten Minuten mit einer Uhr, die chrony noch nicht eingeregelt hatte. Wie groß der Versatz in dieser Zeit war, wissen wir nicht. Ab dem Merge steht in jedem Lauf, ob die Uhr am Anfang schon synchron war und wie groß der Versatz am Ende ist.
- **Keine Referenz-ID, kein Server, keine IP** im `meta.json`, geprüft.
- **Forum-Ordner:** `data/bch/lauscher/forum/` auf `messung/bch-tempnet` ist unverändert, kein Diff seit `dbae9da`. Der Handlauf hat wie jeder Lauf nur seinen Laufordner geschrieben und `bloecke.csv` und `zusammenfassung.json` neu berechnet.
- **Branch:** `messung/bch-tempnet-woche2` bleibt mit dem Handlauf-Commit stehen.

## Offene Fragen an Ben

1. Soll der Zuhörer erst lauschen, wenn chrony synchron ist, zum Beispiel mit `chronyc waitsync` und höchstens 2 min Wartezeit? Damit hätten auch die ersten Minuten jedes Laufs eine eingeregelte Uhr. Das wäre eine weitere kleine Änderung am Workflow.

## Was Ben tun muss

1. Den PR mit `bch-tempnet-lauscher.yml` und `scripts/bch/uhr_versatz.py` prüfen und bis Mo 9.11. 12:00 mergen. Der nächste Lauf nach dem Merge schreibt dann den Versatz mit.
