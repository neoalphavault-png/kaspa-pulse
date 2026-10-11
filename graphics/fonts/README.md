# Schriften fuer das Cheat Sheet

Hier liegen nur die Schnitte, die `scripts/cheat_sheet.py` einbettet, und nur
der Latin-Teilsatz. Sie liegen im Repo statt in `node_modules`, damit der
Monatsbau ohne npm laeuft und ein Lauf von heute in zwei Jahren dasselbe PDF
ergibt. Die Zeichen stehen im PDF eingebettet, also nichts nachladen.

Alles unter der SIL Open Font License 1.1, der Text steht in
`LICENSE-OFL-1.1.txt`. Die Rechtevermerke sind aus der name-Tabelle der
Dateien selbst gelesen, nicht abgeschrieben.

| Familie | Schnitte | Rechtevermerk in der Datei |
| --- | --- | --- |
| Archivo | 600, 800, 900 | Copyright 2020 The Archivo Project Authors (https://github.com/Omnibus-Type/Archivo) |
| IBM Plex Sans | 400, 500, 600 | Copyright 2019 IBM Corp. All rights reserved. |
| IBM Plex Mono | 400, 500 | Copyright 2017 IBM Corp. All rights reserved. |

Herkunft der Dateien: die npm-Pakete `@fontsource/archivo`,
`@fontsource/ibm-plex-sans` und `@fontsource/ibm-plex-mono`, je Fassung 5.2.5,
Dateien `files/<familie>-latin-<schnitt>-normal.woff2`. Die beiden
Lizenzdateien dieser Pakete tragen in der ersten Zeile "Google Inc.", was fuer
IBM Plex nicht stimmt; darum steht hier der Lizenztext einmal ohne diese Zeile
und die Vermerke oben aus den Schriften.

Einen Schnitt nachziehen: dasselbe Paket in derselben Fassung holen, die
Latin-Datei hierher legen, Tabelle ergaenzen und in `FONTS` in
`scripts/cheat_sheet.py` eintragen. Nie eine Datei aus einem CDN, die Fassung
muss benannt bleiben.
