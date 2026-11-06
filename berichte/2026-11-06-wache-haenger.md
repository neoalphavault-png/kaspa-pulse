# Upgrade-Wache: Hänger in der NU7-Nacht, Neustart und Fix (6.11.2026)

Ben hat am 6.11. vier Punkte beauftragt: Neustart prüfen, die Probe bei +6 h prüfen, einen Fix bauen und eine neue Regel für Fristen anwenden.

<!-- discord -->
Upgrade-Wache: Fix gemergt (PR #266). Die laufende Wache auf c2 kennt ihn erst nach einem Neustart mit neuem Stand. Die nächste Pflichtprobe ist bei +24 h, am 7.11. um 02:34 UTC (03:34 Berlin).
<!-- teil -->
📤 VON HAND, fällig 6.11. 23:00 Berlin (spätestens 7.11. 03:30 Berlin): auf c2 sudo /opt/kaspa-pulse/deploy/c2/setup.sh wache zcash-mainnet ausführen, dann journalctl -u upgrade-wache@zcash-mainnet -n 20. Erwartet: Zeile mit "lauf" und wachsender Höhe. Holt den Fix aus PR #266 (Seed-Wiederholung, Eigenwache, Anker-Fix) vor der Probe bei +24 h. Bericht berichte/2026-11-06-wache-haenger.md
<!-- /discord -->

## 1. Nach dem Neustart

- **Neustart:** um 08:11:32 UTC laut Log der Wache (Zeile `start`).
- **Spitze:** Um 08:15:32 UTC stand sie bei **3.544.061**, und die Blockpause meldete die Entwarnung (Pause 17 s). Die Wache hat sich also neu verankert und sieht wieder neue Blöcke.
- **DNS:** Die Seeds waren beim Neustart offenbar wieder auflösbar.
- **Verbindungen je Software:** Die zeigt erst die nächste Zeile `lauf` um 09:11 UTC. Sie kommt mit dem Sync um 09:23 UTC ins Repo, und ich prüfe sie dann.

## 2. Probe bei +6 h

- **Fälligkeit:** Die Probe hängt an der Zeit, zu der die Wache die Aktivierung gesehen hat (02:34 UTC), sie ist also um 08:34 UTC fällig. Ausgefallen war sie um den Neustart (08:11 UTC) noch nicht. Die Wache hat den Zustand mit Aktivierungszeit und Proben beim Neustart behalten und führt die Probe aus, sobald sie fällig ist.
- **Prüfung:** mit dem Sync um 09:23 UTC (Zeile `peers_vor_upgrade`). Fehlt sie oder lief sie auf alter Spitze, kennzeichne ich sie im Report am 9.11. als „verspätet, Grund Wache hing“, mit Uhrzeit.
- **Probe bei +24 h:** Sie läuft am 7.11. um 02:34 UTC. Damit sie sicher läuft, soll die Wache vorher mit dem Fix neu starten, siehe „Was Ben tun muss“.

## 3. Ursache und Fix

**Journal (Ben):** ab 02:50 UTC alle 30 min „seed nicht aufloesbar (gaierror)“. Die DNS-Seeds waren von c2 aus nicht auflösbar.

**Zwei Fehler im Code der Wache:**
1. **Kein Rückfall ohne DNS.** Die Wache bekam ohne DNS keine neuen Adressen. Und der Anker über den Header-Client braucht selbst DNS, konnte also nicht neu verankern.
2. **Arbeit beginnt bei null.** Bei jedem Anker begann die aufsummierte Arbeit wieder bei null. Eine alte Spitze außerhalb des Ankers wog dann dauerhaft mehr als die echte Kette, und die eigene Spitze blieb stehen, obwohl Köpfe ankamen. Der Selbsttest zeigt das an der alten Fassung.

**Fix:** [PR #266](https://github.com/neoalphavault-png/kaspa-pulse/pull/266), Squash-Merge `4a67318`, nur `scripts/wache/`, selbst gemergt.
- **a) Seeds:**
  - Jeder Seed-Abruf läuft bis zu dreimal, mit 5, 15 und 45 s Abstand.
  - Kommt nichts, gelten die Adressen des letzten Erfolgs aus `peers-cache.json`. Die Datei hat Rechte 600 und bleibt auf c2. Sie liegt nicht unter `roh/` und kommt nie ins Repo.
  - Ohne Seeds fragt die Wache alle 5 min neu.
  - Dazu kommt `kette-cache.json` mit den letzten 300 Köpfen (ohne Adressen) für den Neustart.
- **b) Eigenwache `wache_haengt`:**
  - Steht die eigene Spitze 600 s, während Peers neuere Blöcke ankündigen oder höher melden, schickt die Wache „wache haengt …“ nach #ops-log.
  - Gleichzeitig holt sie die Köpfe direkt per getheaders von einem Peer, geprüft auf Verkettung und Arbeitsnachweis.
  - Solange es solche Hinweise gibt, gibt es keinen blockpause-Alarm.
- **Anker:** Der Anker schließt an die bekannte Arbeit an und rechnet die Nachfahren neu. Die Spitze ist dann wieder der Knoten mit der meisten Arbeit.
- **c) Selbsttest:** `python3 scripts/wache/selbsttest.py` prüft 19 Fälle, alle bestehen. Die alte Fassung fällt in 8 davon durch. Die bestehende Simulation ist weiter 6 von 6 ok.

**Folgen für den Report am 9.11.:** Spitzenwechsel (M3) und Kettenspaltung (M4) fehlen für 02:54 bis 08:11 UTC, also gut 5 h. Der Report nennt das unter „Grenzen“. Erste Sicht (M7) und die Abstände (M1, M2, M6) sind nicht betroffen.

## 4. Neue Regel ab 6.11.

Nennt ein Bericht unter „Was Ben tun muss“ eine Uhrzeit vor 09:05 Berlin oder eine, die in weniger als 3 h fällig ist, schicke ich die Aufgabe zusätzlich als Zeile „📤 VON HAND, fällig HH:MM“ nach #moderator-only. Der Weg dafür ist der Discord-Abschnitt dieses Berichts, gesendet über `bericht-discord.yml`.

## Offene Fragen an Ben

1. War die DNS-Störung auf c2 ein Problem des Resolvers? Die Wache übersteht so etwas jetzt, aber andere Dienste auf c2 brauchen DNS auch.

## Was Ben tun muss

1. **Fällig 6.11. 23:00 Berlin, spätestens 7.11. 03:30 Berlin:** auf c2 `sudo /opt/kaspa-pulse/deploy/c2/setup.sh wache zcash-mainnet`, danach `journalctl -u upgrade-wache@zcash-mainnet -n 20`. Ziel ist, dass der Fix vor der Probe bei +24 h läuft. Diese Aufgabe geht auch als „📤 VON HAND“ nach #moderator-only.
