# Zusatz 17.11.2026 abends: BCH Chipnet umgestellt, Gegenprobe Sovright

Auftrag Ben 17.11.2026 abends, nach Punkt 3 (Hostname-Fix #327) des Auftrags vom Tag.

<!-- discord -->
Zusatz 17.11.: Der BCH-Zuhörer läuft seit 17.11. 19:44 UTC auf Chipnet, als Probe vom PR-Branch, PR 329 an Ben, Workflow. Die Chipnet-Köpfe sind aktuell. Die Aktivierungshöhe ist nach unseren eigenen Köpfen 332.451, counted, Kopfzeit 15.11. 12:35:56 UTC. Danach liegt der Median der Abstände bei 52 s, davor bei 529,5 s. Sovright-Abgleich bis 8.11. 15:30 UTC: 39 Orphans in beiden Listen, 13 nur bei uns, 22 nur bei Sovright. Forumsentwurf im Bericht. Bericht berichte/2026-11-17-chipnet-sovright.md
<!-- /discord -->

## A. BCH Chipnet

**Kopf-Zählung:**
- `chipnet_koepfe.py` auf `messung/bch-chipnet-xo` kürzt jetzt die Software-Kennung wie auf main (#327).
- Der Anstoß startete „bch chipnet“, Lauf 5, grün. Commit `e0fd65d`.
- Abruf 17.11. 19:41 UTC, Höhe 313.654 bis 335.744, BCHN-Checkpoints geprüft.
- Gegenprobe: drei Peers, je 500 von 500 gleich.
- Kein Peer lieferte bei 327.989 den Tempnet-Block.

**Aktivierungshöhe, counted aus unseren Köpfen:**
- Regel nach BCHN: Das Upgrade gilt für den ersten Block, dessen Vorgänger einen Median der letzten 11 Kopfzeiten (MTP) von mindestens 1794744000 hat, also 15.11.2026 12:00:00 UTC.
- **Erster Block unter dem Upgrade: 332.451**, Kopfzeit 15.11.2026 12:35:56 UTC. Der MTP seines Vorgängers ist 12:08:24 UTC, beim Block davor waren es 11:48:22 UTC.
- Abstände nach Kopfzeit:
  - die 500 vor der Aktivierung im Median 529,5 s, im Mittel 600,6 s
  - danach bis 335.744 (17.11. 19:40 UTC) 3.293 Abstände, im Median 52 s, im Mittel 60,2 s
  - Davon tragen 948 Blöcke Difficulty 1.
- Das steht nur hier, nicht im Kalender auf pulsehawk.io (Ben, 17.11.).

**Zuhörer:**
- **PR #329, Ben merged:**
  - `tempnet_lauscher.py --netz chipnet`, mit Peers aus BCHN chainparams und umgekehrter Abzweig-Probe
  - `chipnet_koepfe.py` nach main
  - der neue Workflow `bch-chipnet-lauscher.yml`
- **Startzeit:** 17.11.2026 19:44 UTC, Lauf 1 der Kette. Er läuft als Probe vom PR-Branch, wie heute erlaubt, ohne Secret und ohne Commit nach main.
- **Kette:** Läufe von 330 min, die Daten gehen auf `messung/bch-chipnet-xo` unter `data/bch-chipnet/lauscher/`. Der erste Daten-Commit kommt gegen 01:20 UTC. Die Kette läuft vorerst bis 31.12.2026, das Ende legst du fest.
- **Wochenbericht:** Der erste BCH-Wochenbericht am Sa 22.11. enthält damit die Chipnet-Tage ab 17.11. 19:44 UTC.
- **c2:** Die Kopie des Zuhörers auf c2 (`deploy/c2/`) ist nicht umgestellt. Das ist ein Deploy-Thema und bleibt bei dir.

## B. Gegenprobe Sovright (Zcash, Forum 59035, Beitrag 13)

**Grundlage:**
- **Unsere Zählung:** Zuhörer-Serie NU7, Fenster 5.11. 17:02 bis 8.11. 15:30:05 UTC, 52 Orphans ab der Aktivierung, alle mit Tiefe 1. 12 davon kamen nur als Hash ohne Kopf. Die volle Liste habe ich mit derselben Auswertung aus den Rohdaten auf `messung/zcash-mainnet` nachgerechnet, dieselben Zahlen wie bisher (9.062 Kettenblöcke, 9.055 angekündigt, 52 Orphans).
- **Sovright:** source Sovright (zmanian), `nu7-orphans-post.csv` aus dem Gist in Beitrag 13. Ich habe sie aus der HTML-Seite gelesen, nur als Daten, und nur Höhen, Hashes, Zeiten und die Spalte „gesehen von“ übernommen.
  - 243 Orphans vom 6.11. 02:34 bis 14.11. 16:02 UTC.
  - Im überlappenden Fenster bis 8.11. 15:30:05 UTC sind es 61: 34 nur von ihren Zuhörern, 13 von Zuhörern und Zebras, 14 nur von den Zebras, deren Logs am 7.11. 16:31 UTC beginnen.
- **Abgleich:** Block für Block über den Orphan-Hash.

**Ergebnis:**

| | Anzahl |
|---|---:|
| in beiden | 39 |
| nur bei uns | 13, davon 7 mit Höhe und 6 ohne Kopf |
| nur bei Sovright | 22, davon 14 nur von ihren Zebras gesehen |

- **Höhen:** In 5 gemeinsamen Orphans weicht die Höhe um eins ab. Sovright markiert alle fünf als inferred oder inferred_low_confidence. Unsere Höhe kommt aus dem Vorgänger-Hash im Kopf.
- **Gewinner-Hashes:** Alle 243 liegen auf unserer Kette, jeweils auf der Höhe, die Sovright nennt.
- **Ohne Kopf:** Bei 6 gemeinsamen Orphans hatten wir keinen Kopf, die Höhe dort kommt nur aus der Liste.
- **Nur bei uns:** Keiner der 7 mit Höhe hat bei Sovright einen anderen Orphan auf derselben Höhe.
- **Kenbak (Beitrag 16):** Er hat seine Liste gegen Sovright abgeglichen, unsere ist die dritte unabhängige Zählung. Einen Abgleich direkt gegen Kenbaks Daten habe ich nicht gemacht.

**In beiden (39):**

| Höhe (unsere) | Höhe (Sovright) | Orphan-Hash, Anfang | Höhenquelle Sovright |
|---:|---:|---|---|
| 3.543.576 | 3.543.576 | `0000000000abd03733abc3` | inferred |
| ohne Kopf | 3.543.606 | `0000000000f119a4409700` | inferred |
| 3.543.996 | 3.543.996 | `00000000012aca618763a6` | inferred |
| 3.544.249 | 3.544.249 | `000000000044c668f9936f` | inferred |
| 3.544.422 | 3.544.423 | `0000000000032b7cf8af1a` | inferred |
| 3.544.651 | 3.544.651 | `00000000003ad574be4631` | inferred |
| 3.544.804 | 3.544.804 | `0000000000588b55df1371` | inferred |
| 3.544.912 | 3.544.911 | `000000000148fa4b41b841` | inferred_low_confidence |
| 3.545.137 | 3.545.137 | `000000000100a06a987aa8` | inferred |
| 3.545.280 | 3.545.281 | `000000000101a1158abb42` | inferred_low_confidence |
| ohne Kopf | 3.545.467 | `0000000000cb0ef3e3eb4d` | inferred |
| ohne Kopf | 3.545.577 | `00000000013eccfda56b6e` | inferred |
| 3.545.634 | 3.545.634 | `0000000001330a700eb9bf` | inferred |
| 3.545.656 | 3.545.657 | `0000000000e9afab565945` | inferred_low_confidence |
| 3.545.708 | 3.545.707 | `00000000002b89bb16c4d1` | inferred_low_confidence |
| 3.546.115 | 3.546.115 | `0000000000c4c900db2b5c` | inferred |
| 3.546.586 | 3.546.586 | `00000000011447018c08a0` | inferred |
| ohne Kopf | 3.546.781 | `0000000000f9e874262ebe` | inferred |
| 3.546.956 | 3.546.956 | `00000000008c6b6f4c8a98` | inferred |
| ohne Kopf | 3.546.958 | `00000000009a5a97c5e8a2` | inferred |
| 3.547.184 | 3.547.184 | `000000000090d6e3ef65b1` | inferred_low_confidence |
| 3.547.243 | 3.547.243 | `0000000000e2178e208c18` | inferred_low_confidence |
| 3.547.828 | 3.547.828 | `00000000001c044a742bae` | inferred |
| 3.548.118 | 3.548.118 | `0000000000eb377705e943` | inferred |
| 3.548.184 | 3.548.184 | `00000000002fa81bb6012b` | inferred |
| 3.548.351 | 3.548.351 | `0000000000cdaefe3ed4c3` | inferred |
| ohne Kopf | 3.548.448 | `0000000000db9b2f88657f` | inferred |
| 3.548.551 | 3.548.551 | `00000000006b94bca2efab` | inferred |
| 3.548.623 | 3.548.623 | `0000000000c9c03c851a5f` | inferred |
| 3.548.856 | 3.548.856 | `00000000005dffafafba6c` | zebra_log |
| 3.548.913 | 3.548.913 | `000000000135ee6295c0f7` | zebra_log |
| 3.549.274 | 3.549.274 | `0000000000a74227370676` | zebra_log |
| 3.549.711 | 3.549.711 | `00000000014b67b9aa6067` | zebra_log |
| 3.549.925 | 3.549.925 | `000000000114e45de3f4f3` | zebra_log |
| 3.550.138 | 3.550.138 | `00000000009a5dc87eb5c8` | zebra_log |
| 3.550.276 | 3.550.276 | `0000000000e6b5882e90b6` | zebra_log |
| 3.550.612 | 3.550.612 | `0000000000181526f9859d` | zebra_log |
| 3.550.780 | 3.550.780 | `0000000000af571ab01c93` | zebra_log |
| 3.551.039 | 3.551.039 | `00000000009f783ad74bed` | zebra_log |

**Nur bei uns (13):**

| Höhe | Orphan-Hash, Anfang | erste Ankündigung bei uns (UTC) |
|---:|---|---|
| 3.543.512 | `00000000006ad747aabe42` | 2026-11-06 03:56:03 |
| ohne Kopf | `0000000000d1e5865f23e1` | 2026-11-06 05:30:49 |
| 3.543.863 | `0000000000094630fbf7d6` | 2026-11-06 06:49:23 |
| 3.543.902 | `0000000000976e98ea1a17` | 2026-11-06 07:06:04 |
| 3.543.993 | `0000000000fa874c2c1e9b` | 2026-11-06 07:48:19 |
| 3.544.113 | `0000000001319dfb90aaa2` | 2026-11-06 08:34:53 |
| 3.544.161 | `0000000000b5f4edfd2242` | 2026-11-06 08:52:57 |
| ohne Kopf | `0000000000a9e5d5346992` | 2026-11-06 15:12:49 |
| ohne Kopf | `0000000001241b4e4ed456` | 2026-11-06 15:38:51 |
| ohne Kopf | `000000000011011fc862fd` | 2026-11-06 21:13:47 |
| 3.547.189 | `000000000004c26f8e67d1` | 2026-11-07 05:57:26 |
| ohne Kopf | `0000000000450d580bda8e` | 2026-11-07 10:33:59 |
| ohne Kopf | `00000000010d44e66e27a2` | 2026-11-07 12:07:58 |

**Nur bei Sovright (22):**

| Höhe | Orphan-Hash, Anfang | gesehen von | s nach dem Gewinner |
|---:|---|---|---:|
| 3.543.866 | `0000000000340e909e9656` | listener | 3,232 |
| 3.544.478 | `000000000138f1291ba2cd` | listener | 7,958 |
| 3.545.026 | `0000000000eb354cba9c82` | listener | 0,594 |
| 3.545.709 | `00000000007bedb43b20d6` | listener | 0,493 |
| 3.546.424 | `00000000015c739a127334` | listener | 0,013 |
| 3.549.048 | `0000000000125b17562b0b` | zebra | 28,934 |
| 3.549.292 | `000000000138ec0aac1ef4` | zebra | 3,117 |
| 3.549.534 | `000000000071e4ed37deee` | zebra | 3,401 |
| 3.549.811 | `00000000010c3d2d12edef` | zebra | 4,816 |
| 3.549.912 | `00000000005936fe6fc2b0` | zebra | 0,817 |
| 3.549.916 | `00000000008ffccef820ff` | zebra | 4,497 |
| 3.549.924 | `00000000009f01578a1525` | zebra | 14,685 |
| 3.550.062 | `0000000000238639205e06` | zebra | 8,393 |
| 3.550.178 | `00000000009618c2eb5f8a` | zebra | 18,478 |
| 3.550.365 | `000000000133173bac2b05` | listener+zebra | 0,095 |
| 3.550.430 | `0000000000c08888899e61` | zebra | 39,878 |
| 3.550.482 | `000000000053bf16a42e9f` | zebra | 5,429 |
| 3.550.683 | `000000000139167df7df96` | zebra | 9,358 |
| 3.550.846 | `0000000000842798a614d1` | zebra | 0,209 |
| 3.551.118 | `0000000000fd723c4b4dfd` | listener+zebra | 0,04 |
| 3.551.248 | `00000000007f2795594bd4` | listener+zebra | 0,261 |
| 3.551.286 | `0000000000a68438fa8b27` | zebra | 2,651 |

**Forumsentwurf (Ben postet), ein Punkt, 114 Wörter, kein Link, keine Position zu 20 s oder zur Abstimmung:**

> A third independent count for the start of that window. Our own Zcash listener ran from the NU7 activation to 8 Nov 15:30 utc and recorded 52 orphans. Matched block by block against the Sovright list for the same stretch, 39 are in both, 13 only in ours and 22 only in the Sovright list. Of our 13, seven have heights 3,543,512, 3,543,863, 3,543,902, 3,543,993, 3,544,113, 3,544,161 and 3,547,189, and six reached us as hash without a header. Of the 22, fourteen were seen only by the Sovright Zebras. In five shared orphans the height differs by one, each marked inferred in the list, while ours comes from the parent hash in the header.

## PR-Nummern

- kaspa-pulse#329, Zuhörer auf Chipnet, Ben merged
- kaspa-pulse#327, Kennung, gemergt `5b46156` (Vorbedingung)
- dieser Bericht

## Offene Fragen an Ben

1. **Ende der Chipnet-Kette:** Vorläufig ist es der 31.12.2026. Passt das, oder soll sie wie Zcash bis Ende Januar laufen?
2. **Wochenzahl Chipnet:** Soll sie gegen 60 s gerechnet werden, ab der Aktivierungshöhe 332.451? Die alte Chipnet-Auswertung rechnet gegen 600 s.

## Was Ben tun muss

- #329 mergen. Die Kette läuft schon und wechselt nach dem Merge selbst auf main, sobald der Branch gelöscht ist.
- Den Forumsentwurf posten.
- c2 bei Bedarf umstellen.
