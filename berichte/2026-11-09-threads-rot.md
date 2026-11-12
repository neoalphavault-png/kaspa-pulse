# Bericht 9.11.2026: Threads rot am 8.11., Ursache und Fix

Auftrag von Ben vom 8.11.2026, Frist Mo 9.11. 12:00. Geändert ist nur `scripts/threads.py`. Ben merged.

## Lauf threads #24 am 8.11. (42498492140)
- **Bild:** `ig/tagesgrafik-2026-11-08-form04-threads.jpg` liegt in Commit `467f01c`, 17:10:23 Berlin. Die raw-Adresse war sofort bereit.
- **Container:** 17895132135502428 wurde angelegt, Status FINISHED, um 17:10:27 Berlin.
- **Veröffentlichen:** `threads_publish` antwortete direkt danach mit HTTP 400. Die Antwort lautete `"code": 24, "error_subcode": 4279009, "error_user_title": "Media Not Found", "error_user_msg": "The media with id 17895132135502428 cannot be found."`, mit `"is_transient": false`.
- **Folge:** Der Lauf stoppte nach 24 s, nichts wurde veröffentlicht. „Log sichern“ war unverändert, und „threads ist rot, heute kein post“ war richtig.

## Ist der Token abgelaufen?
**Nein.** Belege:
- Im selben Lauf hat derselbe `THREADS_TOKEN` den Container angelegt (POST) und seinen Status gelesen (GET).
- Am 7.11. hat er außerdem einen Post veröffentlicht (Media 17915858658546267) und eigene Posts gelesen („log nachholen“).
- Ein abgelaufener Token führt bei Meta zu Code 190 (OAuthException „Error validating access token“), und schon das Anlegen des Containers würde scheitern. Hier kam Code 24 erst beim Veröffentlichen.

Der Wert des Tokens steht in keinem Log und in keiner Datei. Deshalb gibt es keinen Ablauf-Alarm in diesem PR.

## Ursache
Meta meldet den Container als FINISHED, bevor er sich veröffentlichen lässt. Das ist dasselbe Muster wie bei Instagram am 5.11. (Code 9007, Subcode 2207027). Dort holt `instagram.veroeffentlichen` das schon mit einer Pause und Nachfassen nach. `threads.posten` rief `threads_publish` dagegen ohne Pause und nur einmal auf. Bisher ging das meist gut, am 8.11. nicht.

## Fix (`scripts/threads.py`)
- **`veroeffentlichen(nutzer, cid)`:**
  - 10 s Pause nach FINISHED, dann `threads_publish`.
  - Bei Code 24/4279009 oder 9007 folgen bis zu 4 weitere Versuche nach 15, 30, 45 und 60 s. Im schlimmsten Fall sind das 160 s, der Job hat 45 min.
  - Vor jedem weiteren Versuch wird der Container abgefragt. Steht er auf PUBLISHED, ist der Post schon draußen. Dann geht nichts ein zweites Mal raus, und die Media-ID kommt aus der Liste der eigenen Posts.
  - Jeder andere Fehler bricht wie bisher sofort ab, mit geblendetem Token.
- **`graph(..., werfen=True)`:** gibt einen API-Fehler als `ApiFehler` mit Code und Subcode zurück, statt den Lauf zu beenden. Ohne `werfen` bleibt alles wie bisher.
- **`posten()`:** nutzt `veroeffentlichen()`.
- **Selbsttest:** 89 Fälle, 0 falsch. Neue Fälle:
  - „Media Not Found“, das Nachfassen bringt den Post.
  - 10 s Pause, dann 15 s vor dem zweiten Versuch.
  - Vor dem zweiten Versuch wird der Container abgefragt.
  - Steht der Container auf PUBLISHED, gibt es keinen zweiten Post, die Media-ID kommt aus der Liste.
  - Ein anderer Fehler bricht sofort ab, der Token ist geblendet.
  - Nach 5 Versuchen ist der Lauf rot, mit den Pausen 10, 15, 30, 45 und 60 s.
- Secret-Scan ohne Fund.

## Post vom 6.11.
Lauf #21 am 6.11. war aus einem anderen Grund rot. kaspapulse.com lieferte das Bild auch nach 1500 s nicht aus, weil das Pages-Deploy hing (`berichte/2026-11-07-threads-raw-bild.md`). Seit #273 holt Threads das Bild über die raw-Adresse, dieser Fehler kann so nicht mehr auftreten. Die Posts vom 6.11. und 8.11. fehlen auf dem Profil. Nachträglich postet der Takt nicht, das Zeitfenster endet um 19:30.

## Offen für Ben
- **Token-Erneuerung:** Langzeit-Tokens für Threads laufen nach 60 Tagen ab. Den Ausstellungstag kennt das Repo nicht. Soll ich eine automatische Erneuerung bauen, mit `th_refresh_token` einmal im Monat und einer Meldung nach #moderator-only, wenn sie scheitert? Dafür müsste ein Workflow das Secret schreiben können. Das braucht einen eigenen Token mit Secret-Rechten und ist deine Entscheidung.
