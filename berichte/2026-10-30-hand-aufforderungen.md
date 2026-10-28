# Bericht 30.10.2026: Aufforderungen VON HAND für Kaspa Community und PulseHawk

Auftrag von Ben vom 28.10.2026. Frist Fr 30.10.2026 18:00 Berlin, gebaut am 28.10.2026.

## 1. Kaspa Community (Instagram-Broadcast-Kanal)
**Auslöser:** `karussell_post.py posten --art woche` vom c2-Takt, Sa 11:00. Direkt nach dem Posten gibt es drei Fälle:
- **Veröffentlicht, Kaspa-Kern:** Eine Nachricht nach #moderator-only.
  ```
  📤 VON HAND Sa ab 11:15, Instagram-App, Kanal Kaspa Community. Diesen Beitrag teilen
  <permalink aus der api-antwort>
  Text zum Kopieren
  more addresses hold real kas than a week ago, 808,128 in the week to 24 oct 2026, source kaspalytics address counts.
  ```
  - Der Satz ist mit den echten Zahlen für Sa 31.10.2026 aus `weekly-history.json` gerechnet. Er nimmt die stärkste Wochenzahl, also die von Seite 1. Keine davon ist eine eigene Zählung, deshalb steht dort „source“.
  - Er ist klein geschrieben und enthält keine Links und keine Hashtags.
  - Die Textwache prüft ihn vorher. Besteht er sie nicht, kommt die Aufforderung ohne Satz.
- **Veröffentlicht, aber Meme oder Token-Thema** (KRC-20, KCC-20, Token, Meme, Meme-Motiv): Statt der Aufforderung kommt „Diese Woche nicht in Kaspa Community teilen, Grund …“ nach #moderator-only.
- **Nicht veröffentlicht** (KARUSSELL_LIVE aus, Stopp oder Abbruch des Laufs): „kein Beitrag für Kaspa Community diese Woche“ mit Grund, nur nach #ops-log.

**Höchstens eine Aufforderung je Woche:**
- Gemerkt wird sie in `data/karussell-log.json` unter `community`.
- Die Zeile „kein Beitrag“ kommt auch nur einmal.
- Ein späterer, gelungener Post derselben Woche bekommt seine Aufforderung trotzdem.

**Wochenzahlen im Manifest:** Das Manifest des Entwurfs trägt jetzt die Wochenzahlen. So rechnet der Posten-Lauf den Satz aus genau dem Entwurf, der gepostet wird.

## 2. PulseHawk BCH (mittwochs nach dem Tempnet-Lauf)
- **Entwurf:** Er geht wie bisher über `ph_entwurf.py` nach #ph-entwuerfe. Die Datei bleibt unverändert, weil sie gleich in pulsehawk-site liegt.
- **Neu:** `scripts/ph/ph_hand.py` liest den fertigen Entwurf und prüft die Textregeln noch einmal mit `ph_entwurf.regel_pruefen`. Dann geht nach #moderator-only:
  ```
  📤 VON HAND Mi 17:45, X @pulsehawkio, https://x.com/compose/post. Erst nach ✅ von Claude im Chat posten
  posttext
  <der vollständige posttext>
  antwort mit weiteren tags      (nur wenn der entwurf eine antwort.txt hat)
  die grafik haengt im #ph-entwuerfe-post von heute (bch, layout …).
  ```
- **Zeitangabe:** Läuft der Entwurf ausser der Reihe, also nicht Mi vor 17:45, steht statt „Mi 17:45“ „heute, sobald freigegeben“.
- **Nur #ops-log statt #moderator-only:** wenn der Entwurf rot ist, wenn er nicht nach #ph-entwuerfe ging, wenn der Text fehlt oder gegen eine Textregel verstösst.
- **Antwort mit Tags:** Der Entwurf erzeugt bisher keine. Liegt einmal eine `antwort.txt` im Entwurf, kommt sie mit.

## Probe
- **Selbsttests mit Probe-Modus:** In der Probe geht alles nur nach #ops-log.
  - `karussell_post` hat 13 neue Fälle: Satz, Textregeln, Probe, VON HAND, eine je Woche, kein Beitrag, drei Sperren, Kaspa-Kern.
  - `ph_hand` hat 10 Fälle: Probe, VON HAND, Kopf wortgleich, Posttext, Antwort, Zeit, Regelverstoss, roter Entwurf, ohne Text.
  - Dazu `ph_entwurf`, `karussell`, `meme_wahr` und `ops_melden`, alle grün.
- **Echte Probe von main, Lauf 40669790792, grün.** Das Wochen-Karussell für Sa 31.10. lief trocken durch, Container 18097312919222481, nicht veröffentlicht. Auszug aus dem Job-Log:
  ```
  karussell woche fuer 2026-10-31 trocken durchgelaufen, container 18097312919222481, nicht veroeffentlicht (probe)
  [log] kein DISCORD_WEBHOOK_LOG, nur im job-log (kaspa community):
  PROBE, kaspa community, nicht ausfuehren.
  kein Beitrag fuer Kaspa Community diese Woche (2026-10-31), KARUSSELL_LIVE ist nicht gesetzt, nur trocken
  ```
- **Zwei Fehlmeldungen in #moderator-only:**
  - Ein erster Probelauf von meinem Branch scheiterte (40669319992), weil die Bildablage unter `ig/` nur von main erlaubt ist. Der alte Rot-Schritt auf main schickte dabei „karussell woche probe ist rot“ nach #moderator-only.
  - Dasselbe ist heute früh beim Cheat Sheet passiert.
  - Beides verschwindet mit #184, dann gehen rote Läufe nach #ops-log. Proben fahre ich nur noch von main.

## PR-Nummern
- #191, Skripte, selbst gemergt (182a5c6)
- #192, Workflows, setzt auf #184 auf, wartet auf Ben
  - `karussell.yml`: Im Schritt posten kommt `DISCORD_WEBHOOK_OPS` dazu.
  - `ph-entwurf-bch.yml`: neuer Schritt „aufforderung von hand“.

## Selbst-Merge
- #191 als 182a5c6, 28.10.2026. Nur Skripte, Checks grün, keine Konflikte. Die neuen öffentlichen Texte, also der Satz für Kaspa Community, bestehen die Textwache.

## Wie es bis zum Merge von #184 und #192 läuft
- **Kaspa Community:** Funktioniert schon mit dem jetzigen main, weil der posten-Schritt dort noch `DISCORD_WEBHOOK_OPS` hat. Am Sa 31.10. bleibt es aber bei „kein Beitrag“, solange KARUSSELL_LIVE nicht gesetzt ist.
- **PulseHawk:** Die Aufforderung kommt erst nach #192.

## Was Ben tun muss
Siehe „📤 VON HAND“ im Discord-Abschnitt.

<!-- discord -->
**Aufforderungen VON HAND, 28.10.2026**
- **Kaspa Community:** Nach dem Wochen-Karussell (Sa 11:00) kommt hierher „Sa ab 11:15 teilen“ mit Permalink und einem Satz zum Kopieren. Bei Meme oder Token-Thema kommt „diese Woche nicht teilen“ mit Grund. Ohne Post nur eine Zeile ins Ops-Log. Höchstens eine je Woche. Läuft schon (#191).
- **PulseHawk BCH:** Nach dem Entwurf in #ph-entwuerfe kommt hierher „Mi 17:45, X @pulsehawkio“ mit dem ganzen Posttext. Erst nach ✅ von Claude posten. Ist der Entwurf rot oder bricht er eine Textregel, kommt nichts hierher. Kommt mit #192.
- **Probe von main grün**, beide Selbsttests grün.
- **Bericht:** berichte/2026-10-30-hand-aufforderungen.md
<!-- teil -->
📤 VON HAND, wenn du Zeit hast, GitHub. **#184 und dann #192 mergen**
Erst die Workflows für die Discord-Kanäle:
https://github.com/neoalphavault-png/kaspa-pulse/pull/184
dann die Aufforderungen für PulseHawk und Kaspa Community:
https://github.com/neoalphavault-png/kaspa-pulse/pull/192
Ohne #184 landen rote Läufe weiter hier, heute zweimal von meinen Proben. Das tut mir leid.
<!-- /discord -->
