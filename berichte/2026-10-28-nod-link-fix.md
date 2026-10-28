# Bericht 28.10.2026: Zahl des Tages, Link im X-Hauptpost

Auftrag von Ben vom 28.10.2026, Frist heute 22:00 Berlin.

## 1. Ursache
- **Fehler:** Lauf 248 (Run 40658605768), Schritt „post to x“ meldete: „Der Hauptpost traegt einen Link, und X_LINKANTWORT steht auf aus. Nichts gepostet“. Die Wache in `scripts/x_post.py` hat richtig gestoppt.
- **Text vom 28.10.:**
  ```
  layer 2 tvl on kaspa is down 29% against 3 weeks ago. $989K today, $1.39M then, both read from defillama.com 23 days apart.
  ```
  „defillama.com“ ist eine Domain, X macht daraus einen Link.
- **Verursacher:** Commit **00f47c3 vom 17.10.2026**, „zahl des tages: read from bei fremden quellen, messtag statt right now“, Datei **`scripts/number_of_day_data.py`**, Funktion `herkunft_post()`. Sie schreibt seitdem den Quellnamen aus `KENNZAHLEN` in den Hauptpost, und dort steht er als Domain (`defillama.com`, `api.kaspa.org`).
- **Nicht** aus den Selbst-Merges #183 bis #193. Keiner davon berührt `number_of_day_data.py` oder `x_post.py`.
- **Nicht nur der 28.10.:** Derselbe Fehler stoppte zwei weitere Tage, beide fehlen im X-Log:

  | Tag | Lauf | Domain im Hauptpost |
  | --- | --- | --- |
  | 20.10.2026 | 213 (Run 39391686183) | defillama.com |
  | 25.10.2026 | 233 (Run 40177623043) | api.kaspa.org |

## 2. Fix (#196, selbst gemergt)
- **Quelle ohne Domain:** Im Hauptpost steht jetzt „both read from defillama …“ bzw. „both read from the kaspa rest api …“. Unbekannte Domains werden auf ihren Namen gekürzt.
- **Bild und Selbstantwort:** Das Bild nennt die Quelle unverändert. Die Selbstantwort trägt den Link nur, wenn X_LINKANTWORT an ist. Das regelt `x_post.py` wie bisher.

## 3. Wache im Generator
- **Neue Prüfung:** `hauptpost_verstoesse()` in `number_of_day_data.py` findet im Hauptpost jede URL (http, www), jede Domain (zum Beispiel kaspapulse.com, defillama.com, api.kaspa.org) und „link in bio“.
- **Bei einem Fund:**
  - Der Generator bricht vor dem Schreiben ab, also vor Bild und Post.
  - Er setzt `picked=0` und meldet nach #ops-log, wer betroffen war und warum.
  - Der Lauf wird rot.
- **Selbsttest:**
  - Der Hausstil-Test über alle Kandidaten prüft die Wache mit.
  - Dazu kommen sechs Sätze, die stoppen müssen, und vier, die durchgehen müssen.
  - Rauchtest von `main()` mit dem Text vom 28.10.: rc 1, nichts geschrieben, Meldung nach #ops-log.
- **Workflow (#197, wartet auf Ben):** Damit die Meldung #ops-log erreicht, braucht der Schritt „pick the number“ `DISCORD_WEBHOOK_LOG`. Bis zum Merge steht sie nur im Job-Log. Der Abbruch selbst greift schon ohne #197.

## 4. Heute nichts nachgepostet
Ich habe keinen Lauf ausgelöst. Der nächste reguläre Lauf ist Do 29.10.2026, 08:12 UTC.

## Nebenbefund, deine Entscheidung
Der Hauptpost vom 28.10. hatte zwei weitere Stellen, die unsere Textregeln anders sehen: „$989K **today**“ (Echtzeit-Wort und Dollarbetrag). Ebenso tragen frühere Posts Preise, zum Beispiel „kas closed the week at $0.03534“ und „one kas buys 45 satoshis today“. `x_post.py` lässt das durch. Ich habe daran nichts geändert. Sag Bescheid, ob die Zahl des Tages auf X Preise und „today“ zeigen darf.

## PR-Nummern
- #196, Skript, selbst gemergt
- #197, Workflow `number-of-day.yml`, wartet auf Ben

## Selbst-Merge
- #196 als 19fab39, 28.10.2026. Nur `scripts/number_of_day_data.py` und dieser Bericht, Checks grün, keine Konflikte. Der Selbsttest ist grün. Die Zahl des Tages vom Do 29.10. läuft damit ohne Domain im Hauptpost.

## Was Ben tun muss
Siehe „📤 VON HAND“ im Discord-Abschnitt.

<!-- discord -->
**Zahl des Tages, Link im X-Hauptpost, 28.10.2026**
- **Ursache:** Commit 00f47c3 vom 17.10., Datei scripts/number_of_day_data.py. Die Quelle stand als Domain im Hauptpost (defillama mit der Endung .com). Nicht aus #183 bis #193.
- **Auch betroffen:** 20.10. (Lauf 213) und 25.10. (Lauf 233), beide nicht auf X.
- **Fix live (#196):** Die Quelle steht ohne Domain im Hauptpost. Der Generator bricht vor dem Posten ab, wenn eine URL, Domain oder „link in bio“ im Hauptpost steht, und meldet nach #ops-log. Selbsttest grün.
- **Heute nichts nachgepostet.** Do 29.10. 08:12 UTC läuft normal.
- **Bericht:** berichte/2026-10-28-nod-link-fix.md
<!-- teil -->
📤 VON HAND, wenn du Zeit hast, GitHub. **#197 mergen**
Gibt dem Generator der Zahl des Tages den Webhook für #ops-log, damit die Abbruch-Meldung dort ankommt. Der Abbruch selbst wirkt schon ohne.
https://github.com/neoalphavault-png/kaspa-pulse/pull/197
Frage dazu, Antwort genügt: Darf die Zahl des Tages auf X Preise und „today“ zeigen, etwa „$989K today“? Bisher lässt die Wache das durch.
<!-- /discord -->
