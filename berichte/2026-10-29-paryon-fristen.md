# ParyonUSD, Fristen in Blöcken auf dem BCH Tempnet, Bericht 28.10.2026

Auftrag (Ben, 28.10.2026): Geschenk für ParyonUSD (Klasse A, Stufe 1). Ihre Rücknahme- und Zinsfristen laufen in Blöcken, 120 und 1.440 Blöcke. Wir zeigen, wie lang das in Wanduhrzeit auf dem Tempnet war. Frist Do 29.10. 12:00 Berlin.

## Was gezählt wird

Gezählt wird die Wanduhrzeit zwischen einem Tempnet-Block und dem Block 120 bzw. 1.440 Höhen später. Grundlage sind alle 17.625 Blöcke von der Aktivierung (327.989, 15.10.2026 12:56:56 UTC) bis zur Stichzeit des Wochenlaufs (28.10.2026 10:00 UTC, letzter Block 345.613 um 09:59:28 UTC). Jeder Block ist einmal Startblock, die Fenster überlappen also.

- **Header-Zeit:** Die Dauer kommt aus den Header-Zeitstempeln unserer eigenen Kette. Die Kette ist per P2P geholt und auf Verkettung und PoW geprüft (Wochenlauf, `da72b3e` auf `messung/bch-tempnet`).
- **Empfangszeit:** Getrennt davon steht die Dauer aus der ersten Ankündigung bei unserem Zuhörer (first_seen). Sie liegt nur für 25.10. 09:15 bis 28.10. 07:36 UTC vor. Ein Fenster zählt, wenn beide Endblöcke mitgeschnitten sind.
- **Berechnet:** Die Vergleichsspalte ist für ideale 60-s-Blöcke berechnet (Erlang mit n = 120 bzw. 1.440). Die Soll-Dauer ist 120 min bzw. 24 h.
- **Nicht gezählt:** ob Paryon die Frist am Startblock oder am Folgeblock beginnt. Eine Höhe mehr oder weniger ändert die Dauer im Mittel um 1 min.

## Ergebnis

CSV daneben: `berichte/2026-10-29-paryon-fristen.csv`.

**120 Blöcke (Soll 120 min)**

| Quelle | Fenster | Zeitraum UTC | p50 | p90 | p99 | Maximum |
|---|---:|---|---:|---:|---:|---:|
| Header, seit Aktivierung | 17.505 | 15.10. 12:56:56 bis 28.10. 09:59:28 | 120,6 min | 133,1 min | 198,9 min | 922,4 min (15,4 h), ab 327.989 |
| Empfang, Zuhörer | 4.084 | 25.10. 09:17:27 bis 28.10. 07:36:03 | 120,7 min | 129,2 min | 134,2 min | 139,1 min, ab 343.780 (27.10. 03:22 UTC) |
| Header, dieselben 4.084 Paare | 4.084 | wie Empfang | 120,6 min | 129,2 min | 134,2 min | 139,1 min |
| berechnet, 60 s | | | 119,7 min | 134,2 min | 146,9 min | |

**1.440 Blöcke (Soll 24 h)**

| Quelle | Fenster | Zeitraum UTC | p50 | p90 | p99 | Maximum |
|---|---:|---|---:|---:|---:|---:|
| Header, seit Aktivierung | 16.185 | 15.10. 12:56:56 bis 28.10. 09:59:28 | 24,06 h | 25,27 h | 30,57 h | 44,77 h, ab 327.989 |
| Empfang, Zuhörer | 2.764 | 25.10. 09:17:27 bis 28.10. 07:36:03 | 24,03 h | 24,20 h | 24,35 h | 24,39 h, ab 342.518 (26.10. 06:06 UTC) |
| Header, dieselben 2.764 Paare | 2.764 | wie Empfang | 24,03 h | 24,20 h | 24,35 h | 24,39 h |
| berechnet, 60 s | | | 23,99 h | 24,81 h | 25,50 h | |

**Was die Zahlen zeigen**
- **Header gegen Empfang:** Über dieselben Blockpaare liegen beide Dauern höchstens 3,3 min auseinander, im Median um 0 min. Für Fristen dieser Länge reicht die Header-Zeit.
- **Lange Fenster am Anfang:** p99 und Maximum seit Aktivierung kommen aus den ersten Tagen. Am 15.10. lag der mittlere Abstand bei 3.585 s, am 16.10. bei Höhe 328.223 gab es eine Lücke von 20.863 s. Beide Maxima beginnen bei 327.989.
- **Ab 18.10. 00:00 UTC** (15.115 bzw. 13.795 Fenster):
  - 120 Blöcke: p50 120,5 min, p99 146,7 min, Maximum 158,3 min
  - 1.440 Blöcke: p50 24,09 h, p99 26,96 h, Maximum 27,19 h
- **Seit 21.10. 10:00 UTC** (9.933 bzw. 8.613 Fenster):
  - 120 Blöcke: p50 120,0 min, p99 139,5 min, Maximum 147,2 min
  - 1.440 Blöcke: p50 24,00 h, p99 24,96 h, Maximum 25,14 h
- **Kürzer als berechnet:** Seit 21.10. liegen p90 und p99 unter den für 60 s berechneten Werten. Das passt zum kurzen Ende der Blockabstände aus dem Wochenbericht (`berichte/2026-10-28-bch-tempnet-woche2.md`).

**Lücken im Mitschnitt:** Die Höhen 341.265 bis 341.273 (25.10. 09:27 bis 09:34 UTC) und 342.892 bis 342.894 (26.10. 12:37 bis 12:39 UTC) fehlen. Fenster, die dort beginnen oder enden, zählen nur bei der Header-Zeit.

## Entwurf der Antwort unter dem Post von @ParyonUSD

Ben postet. Den Post selbst habe ich nicht gelesen, x.com ist für uns gesperrt, und das umgehe ich nicht. Der Entwurf geht deshalb nur auf die beiden Fristen aus deinem Auftrag ein.

```
bch tempnet since 15 oct, by header time.
we counted 120 block windows at 2 h 1 min median and 3 h 19 min p99.
windows of 1,440 blocks took 24.1 h median and 30.6 h p99, against 24.0 h and 25.5 h computed for 60 s blocks.
window 15 oct 12:56 to 28 oct 09:59 utc.
```

- **262 Zeichen** mit Zeilenumbrüchen. Nur ASCII, auf X zählt das genauso.
- **Regelprüfung** (`regel_pruefen` aus `scripts/ph/ph_entwurf.py`):
  - klein geschrieben, keine Gedankenstriche, keine Pfeile
  - kein Doppelpunkt außer in Uhrzeiten, kein Satzanfang mit Ziffer (selbst geprüft, die Funktion prüft das nicht)
  - „counted“ genau einmal, „computed“ für die Zielzeit, Fenster in UTC
  - kein Echtzeitwort, kein Preis, keine Position zum CHIP, kein Link, kein Angebot
- **Einzige Meldung:** Der Hinweis „method on pulsehawk.io“ fehlt. Das ist Absicht. X macht daraus einen Link, und du wolltest keinen.

## Offene Fragen an Ben

1. Soll die Antwort die Werte seit Aktivierung nennen, wie beauftragt, oder die ruhigeren Werte seit 21.10.? Mit den Werten seit 21.10. stünde für 1.440 Blöcke p99 bei 25,0 h statt 30,6 h. Das wirkt fairer gegenüber dem Netz, weil die langen Fenster nur aus den ersten beiden Tagen kommen.
2. Weißt du, ob Paryon die Frist ab dem Block der Anfrage oder ab dem nächsten Block zählt? Für die Zahlen macht es höchstens rund 1 min aus, für den Text nichts.

## Was Ben tun muss

- Den Entwurf prüfen und selbst unter dem Post antworten. Ich poste nichts.
- Den PR prüfen und mergen. Er ändert keinen Workflow, keine deploy- und keine c2-Datei. Weil der Antwort-Entwurf den Methodenhinweis bewusst weglässt, besteht er die Regelprüfung nicht vollständig. Deshalb merge ich nicht selbst.

Der Secret-Scan ist sauber. Bericht und CSV enthalten keine Peer-IPs, keine Hostnamen, keine Wallet-Adressen und keine Rohdaten des Zuhörers, nur Kennzahlen.
