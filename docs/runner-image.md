# Runner-Image: `ubuntu-24.04`, nicht `ubuntu-latest`

Ben, 10.10.2026.

Alle Workflows in `kaspa-pulse`, `pulse-studio` und `pulsehawk-site` laufen
auf **`ubuntu-24.04`**. `ubuntu-latest` steht in keiner Workflow-Datei mehr.

## Warum

Lauf 37 der Tagesgrafik trug am 10.10.2026 diesen Hinweis:

> The `ubuntu-latest` label will migrate to Ubuntu 26 beginning October 19,
> 2026.

`ubuntu-latest` hätte uns also mitten im Betrieb ein neues Betriebssystem
untergeschoben. Betroffen wäre vor allem, was nicht aus dem Repo kommt:

| Stelle | Risiko bei einem Image-Sprung |
| --- | --- |
| `python -m playwright install --with-deps chromium` | Systempakete für Chromium heißen je Ubuntu-Version anders |
| `pip install --only-binary=:all: pillow==11.3.0` | ein Rad für die neue Python-Version muss es erst geben |
| `actions/setup-python@v5` mit `3.12` | andere Vorinstallation, anderer Cache |
| `ffmpeg`, `fonts-*` aus `apt-get` | Paketnamen und Versionen |

Ein Sprung an einem Montagmorgen kostet die Lieferung des Tages. Ein Pin
kostet nichts.

## Wann das wieder angefasst wird

**Nicht automatisch.** Der Pin bleibt, bis jemand den Wechsel bewusst
vorbereitet: einen Workflow von Hand auf `ubuntu-26.04` stellen, laufen
lassen, und erst bei grün die anderen nachziehen. Ubuntu 24.04 ist bis
April 2029 im Support, es gibt also keine Eile.

**Node 20 bleibt vorerst, wie es ist** (Ben, 10.10.2026). Die Läufe melden
"Node.js 20 is deprecated … forced to run on Node.js 24", aber sie laufen.
Angefasst wird das erst, wenn es wirklich bricht — dann heißt die
Reparatur: `actions/checkout`, `actions/setup-python` und
`actions/upload-artifact` auf ihre nächste Hauptversion.

## Neue Workflows

`runs-on: ubuntu-24.04`. Das muss man sich nicht merken: **`secret_scan.py`
wacht darüber** (Ben, 10.10.2026, in allen drei Repos). Eine `runs-on`-Zeile
mit `ubuntu-latest` unter `.github/workflows/` macht den Lauf rot — im
Baumlauf, im Commit-Bereich und lokal schon vor dem Commit über die Hooks
in `.githooks/`.

Die Meldung nennt Datei und Zeile und sagt, was stattdessen dasteht:

```
secret-scan: alle dateien im checkout, 1 fund(e). Werte werden nie gezeigt.
  .github/workflows/zz-probe.yml:5  ubuntu-latest statt gepinntem image  fp=-

Kein Secret, aber auch nicht erwuenscht: runs-on gehoert auf ein gepinntes
Image, runs-on: ubuntu-24.04. ubuntu-latest wandert ab dem 19.10.2026 auf
Ubuntu 26. Begruendung: docs/runner-image.md in kaspa-pulse.
```

Es zählt **nur eine echte `runs-on`-Zeile**. Ein Kommentar in einem Workflow
darf `ubuntu-latest` nennen, und diese Datei hier darf es auch — sonst
ließe sich die Regel nicht mehr erklären. Weil es kein Secret ist, gibt es
keinen Fingerabdruck und keine Ausnahme über `.secret-scan-allow`: die Zeile
ist entweder richtig oder nicht da.

Beim Wechsel auf Ubuntu 26 wird diese Wache als Erstes angepasst, nicht
umgangen.
