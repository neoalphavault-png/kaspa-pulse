/* utm.js, die Herkunft einer Anmeldung ueberlebt den Klick.
 *
 * WARUM
 * Der Newsletter-Link traegt seit dem 16.09.2026 utm_source, utm_medium und
 * utm_campaign (scripts/utm.py). Das sagt uns, welcher Klick ankam. Es sagt
 * uns NICHT, welche Anmeldung daraus wurde: der Besucher landet auf der
 * Startseite, scrollt, liest, traegt seine Adresse ein, und Brevo sieht nur
 * eine Adresse. Dieses Skript schreibt die Herkunft in die versteckten
 * Felder des Formulars, damit sie am Kontakt haengt.
 *
 * DREI EIGENHEITEN, DIE ABSICHT SIND
 * 1. Letzter Kontakt gewinnt, nicht der erste. Wer ueber den angepinnten
 *    Kommentar wiederkommt und sich DANN antraegt, ist dem Pin zuzurechnen.
 * 2. Die Werte ueberleben einen Seitenwechsel (sessionStorage), aber nicht
 *    die Sitzung. Ein Besucher, der in drei Wochen ohne Parameter
 *    wiederkommt, ist "direct", und das ist ehrlicher als eine Quelle,
 *    an die sich niemand erinnert.
 * 3. Nur was auf der Liste steht, kommt durch. Quelle und Gattung werden
 *    gegen QUELLEN und MEDIEN aus scripts/utm.py geprueft, die Kampagne
 *    gegen dieselbe Slug-Regel. Alles andere heisst "other". Ein Tippfehler
 *    in einer Videobeschreibung ("youtube-shorts") macht damit keine zweite
 *    Zeile in der Auswertung auf, sondern faellt in einen Topf, den man
 *    sieht. Der Selbsttest in scripts/utm.py vergleicht beide Listen.
 *
 * Speicher kann fehlen (privates Fenster, blockierte Site-Daten). Jeder
 * Zugriff steht deshalb in try/catch, und ohne Speicher funktioniert das
 * Formular genauso, nur ohne Erinnerung.
 */
(function () {
  "use strict";
  var KEYS = ["utm_source", "utm_medium", "utm_campaign"];
  var STORE = "kp_utm";
  var FELD = {
    utm_source: "utmSource",
    utm_medium: "utmMedium",
    utm_campaign: "utmCampaign"
  };

  /* Wortgleiche Kopie von QUELLEN und MEDIEN aus scripts/utm.py. Wer dort
     eine Quelle ergaenzt, ergaenzt sie hier; der Selbsttest dort schlaegt
     an, wenn es jemand vergisst. */
  var QUELLEN = ["yt-description", "yt-pinned", "youtube", "x", "discord",
                 "tg", "newsletter", "site"];
  var MEDIEN = ["shorts", "video", "post", "chat", "mail", "site"];

  /* Fuer die Kampagne gibt es keine feste Liste, jede Folge bringt eine
     neue. utm.py laesst jeden Slug zu, also laesst diese Zeile denselben
     zu; eine Aufzaehlung wuerde jede kommende Kampagne zu "other" machen,
     bis jemand diese Datei anfasst. */
  var SLUG = /^[a-z0-9][a-z0-9-]{0,63}$/;

  /* Was wir selbst einsetzen, wenn nichts ankommt, und der Sammeltopf. */
  var EIGEN = { utm_source: "direct", utm_medium: "none", utm_campaign: "none" };
  var ANDERE = "other";

  function sauber(v) {
    /* Nur normalisieren: Rand weg, klein, gekappt. Frueher hat diese Stelle
       verbotene Zeichen herausgestrichen, und genau das war das Leck: aus
       "Week In 30" wurde "weekin30", ein Wert, der gueltig aussieht, keiner
       ist und in Brevo eine eigene Zeile aufmacht. Geprueft wird jetzt in
       erlaubt(); was nicht auf der Liste steht, heisst "other". */
    return String(v == null ? "" : v).trim().toLowerCase().slice(0, 128);
  }

  function erlaubt(k, v) {
    /* Der Abgleich. Leer bleibt leer, damit setzen() den eigenen Wert
       einsetzt; alles Unbekannte wird "other". */
    if (!v) { return ""; }
    if (v === EIGEN[k] || v === ANDERE) { return v; }
    if (k === "utm_source") { return QUELLEN.indexOf(v) < 0 ? ANDERE : v; }
    if (k === "utm_medium") { return MEDIEN.indexOf(v) < 0 ? ANDERE : v; }
    return SLUG.test(v) ? v : ANDERE;
  }

  function ausUrl() {
    var out = null;
    try {
      var q = new URLSearchParams(window.location.search);
      KEYS.forEach(function (k) {
        var v = sauber(q.get(k));
        if (v) { out = out || {}; out[k] = v; }
      });
    } catch (e) { /* alter Browser ohne URLSearchParams */ }
    return out;
  }

  function gelesen() {
    try { return JSON.parse(window.sessionStorage.getItem(STORE) || "null"); }
    catch (e) { return null; }
  }

  function gemerkt(v) {
    try { window.sessionStorage.setItem(STORE, JSON.stringify(v)); } catch (e) {}
  }

  var utm = ausUrl();
  if (utm) { gemerkt(utm); } else { utm = gelesen() || {}; }

  function setzen() {
    /* Leer ist verboten. Ein leeres Feld laesst sich in Brevo nicht von einem
       kaputten Feld unterscheiden; "none" sagt "kam ohne", und das ist eine
       Aussage. Gilt fuer alle drei, auch wenn eine Quelle da ist: wer
       ?utm_source=yt-description ohne Rest aufruft, ist
       yt-description / none / none, nicht yt-description / / . */
    KEYS.forEach(function (k) {
      var el = document.getElementById(FELD[k]);
      if (el) { el.value = erlaubt(k, utm[k]) || EIGEN[k]; }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setzen);
  } else {
    setzen();
  }
})();
