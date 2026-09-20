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
 * ZWEI EIGENHEITEN, DIE ABSICHT SIND
 * 1. Letzter Kontakt gewinnt, nicht der erste. Wer ueber den angepinnten
 *    Kommentar wiederkommt und sich DANN antraegt, ist dem Pin zuzurechnen.
 * 2. Die Werte ueberleben einen Seitenwechsel (sessionStorage), aber nicht
 *    die Sitzung. Ein Besucher, der in drei Wochen ohne Parameter
 *    wiederkommt, ist "direct", und das ist ehrlicher als eine Quelle,
 *    an die sich niemand erinnert.
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

  function sauber(v) {
    /* nur das, was wir selbst vergeben: klein, kurz, keine Sonderzeichen.
       Alles andere ist entweder ein Tippfehler oder jemand, der etwas in
       unsere Kontaktliste schreiben will. */
    return String(v || "").toLowerCase().replace(/[^a-z0-9._-]/g, "").slice(0, 64);
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
    var werte = {
      utm_source: utm.utm_source || "direct",
      utm_medium: utm.utm_medium || "none",
      utm_campaign: utm.utm_campaign || "none"
    };
    KEYS.forEach(function (k) {
      var el = document.getElementById(FELD[k]);
      if (el) { el.value = werte[k]; }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setzen);
  } else {
    setzen();
  }
})();
