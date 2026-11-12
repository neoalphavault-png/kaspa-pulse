# Instagram publish-fix: Pause und Nachfassen nach FINISHED

Auftrag von Ben vom 5.11.2026 (Auftrag B), erledigt am 5.11.2026. Nur `scripts/`, Selbst-Merge nach der Regel vom 26.10., keine Workflow-Änderung.

## Anlass

- Das Instagram-Bild vom 5.11. war rot ([Lauf 41994939458](https://github.com/neoalphavault-png/kaspa-pulse/actions/runs/41994939458)).
- `media_publish` kam direkt nach dem Status `FINISHED`. Meta antwortete mit http 400, code 9007, error_subcode 2207027 („media id is not available“).
- Ben hat den Job um 09:51 neu gestartet, der Post ist draußen.

## Was geändert ist

- **`scripts/instagram.py`**
  - `graph()` wirft jetzt `GraphFehler`, eine Unterklasse von `Fehler`. Sie trägt http-Status, `code` und `error_subcode` aus der Antwort. Der Fehlertext läuft wie bisher durch `sauber()`.
  - Neu ist `veroeffentlichen(u, cid, caption)`, die `posten()` jetzt aufruft:
    1. Nach `FINISHED` wartet sie 5 s, dann kommt `media_publish`.
    2. Bei genau code 9007 oder subcode 2207027 folgen bis zu 4 weitere Versuche, im Abstand von 15, 30, 45 und 60 s.
    3. Vor jedem neuen Versuch liest sie den Container mit `GET <container>?fields=status_code`. Steht er auf `PUBLISHED`, wird nicht noch einmal veröffentlicht. Die media-id kommt dann aus `GET <ig_user>/media` (limit 5), abgeglichen über die Caption. Passt keine Caption, stoppt der Lauf mit Fehler, ohne zweiten Post.
    4. Jeder andere Fehler bricht sofort ab, wie bisher. Nach dem fünften 9007 bricht der Lauf ebenfalls ab.
- **`scripts/karussell_post.py`**: `veroeffentlichen(cid, caption)` nutzt denselben Helfer.
- **`scripts/ig_story_auto.py`**: Die Story ruft `media_publish` genauso auf und nutzt deshalb ebenfalls den Helfer. Eine Story hat keine Caption. Steht ihr Container schon auf `PUBLISHED`, geht sie nicht doppelt raus, und die media-id bleibt leer.
- **`scripts/instagram_reel.py`**: Das Skript gibt es nicht. Kein anderes Skript ruft `media_publish` auf. `scripts/uhrwerk_proben.py` legt nur Probe-Container an und veröffentlicht nie.

## Selbsttest

`python3 scripts/instagram.py --selbsttest`: 63 Prüfungen, 0 Fehler. Neu sind:

| Prüfung | Ergebnis |
| --- | --- |
| graph liefert http 400, code 9007 und subcode 2207027 aus der Antwort | ok |
| scharf wartet nach FINISHED 5 s vor media_publish | ok |
| einmal 9007, nach 15 s und Status-Abfrage Erfolg (2 media_publish, Pausen 5 und 15 s) | ok |
| Container schon PUBLISHED, kein zweiter Post, media-id über die Caption (1 media_publish) | ok |
| PUBLISHED ohne passende Caption stoppt, kein zweiter Post | ok |
| höchstens vier weitere Versuche mit 15, 30, 45, 60 s (5 media_publish) | ok |
| anderer Fehler bricht sofort ab (1 media_publish, nur die 5-s-Pause) | ok |

Die übrigen Selbsttests sind weiter grün:

| Skript | Ergebnis |
| --- | --- |
| `scripts/karussell_post.py --selbsttest` | 0 Fehler |
| `scripts/ig_story_auto.py --selbsttest` | alle Testfälle bestanden |
| `scripts/uhrwerk_proben.py --selbsttest` | 26 Prüfungen grün |

## Offen

- Nichts. Der nächste scharfe Lauf zeigt im Log `container ... vor versuch 2`, falls Meta wieder zu früh `FINISHED` meldet.
