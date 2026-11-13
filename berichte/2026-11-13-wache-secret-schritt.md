# Abriss-Wache des Zcash-Zuhörers, Secret nur im Sendeschritt (13.11.2026)

Ben am 13.11., Folgefix zu #313: In `zuhoerer-kette-wache.yml` stand der Webhook `DISCORD_WEBHOOK_LOG` im selben Schritt wie die Prüfung. Nach unserer Regel bekommt ein Secret nur der Sendeschritt.

<!-- discord -->
Abriss-Wache des Zcash-Zuhörers geteilt: Die Prüfung läuft ohne Secret und gibt nur die Meldetexte weiter, der Webhook steht allein im Sendeschritt. Das Verhalten ist sonst unverändert, fünf Fälle lokal getestet. PR, du merged. Bericht berichte/2026-11-13-wache-secret-schritt.md
<!-- /discord -->

## Was gemacht ist

- **Schritt 1 „kette pruefen“:**
  - Prüft wie bisher, aber nur mit `GH_TOKEN`.
  - Jede Meldung (Vorwarnung 7 Tage und 1 Tag vor dem Ende, Abriss) kommt als eine Zeile in eine Datei. Am Ende des Schritts geht die Datei als Ausgabe `texte` weiter, auch bei jedem frühen Ende.
- **Schritt 2 „melden“:** Läuft nur, wenn `texte` nicht leer ist. Nur dieser Schritt hat `DISCORD_WEBHOOK_LOG`, er sendet jede Zeile einzeln über `scripts/ops_melden.py`.
- **Lokal getestet:** Beide Schritte liefen mit einem Ersatz für `gh` und für den Versand.

  | Fall | Ergebnis |
  |---|---|
  | Kette läuft | keine Meldung |
  | Abriss | eine Meldung mit Laufnummer |
  | 7 Tage vor dem Ende | Vorwarnung |
  | 1 Tag vor dem Ende und Abriss | zwei Meldungen |
  | Endzeit fast erreicht | keine Meldung |

## PR-Nummern

- dieser PR, Folgefix zu #313

## Offene Fragen an Ben

Keine.

## Was Ben tun muss

- Den PR prüfen und mergen.
