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

`runs-on: ubuntu-24.04`. Wer `ubuntu-latest` schreibt, nimmt den Sprung
wieder in Kauf.
