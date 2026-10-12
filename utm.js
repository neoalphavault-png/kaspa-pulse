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
  var KEYS = ["utm_source", "utm_medium", "utm_campaign", "utm_medium_raw"];
  /* Spiegel von MEDIEN in scripts/utm.py (Ben, 12.10.2026). Dort ist die
     Liste zuhause, hier braucht sie der Browser. utm.py --selftest liest
     diese Zeile und vergleicht beide, damit sie nicht auseinanderlaufen. */
  var MEDIEN = ["shorts", "video", "post", "chat", "mail", "email", "site", "reply",
                "bio", "description", "channel"];
  var STORE = "kp_utm";
  var FELD = {
    utm_source: "utmSource",
    utm_medium: "utmMedium",
    utm_campaign: "utmCampaign",
    utm_medium_raw: "utmMediumRaw"
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
      ["utm_source", "utm_medium", "utm_campaign"].forEach(function (k) {
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
    /* Eine Gattung, die nicht in MEDIEN steht, eroeffnet in der Auswertung
       eine eigene Zeile - genau das, was die Liste verhindern soll. Sie
       zaehlt deshalb als "other", und was im Link stand, bleibt daneben in
       UTM_MEDIUM_RAW lesbar (Ben, 12.10.2026, Anlass: utm_medium=social).
       RAW traegt immer das Original, auch wenn es bekannt war - so
       beantwortet das Feld eine Frage und nicht zwei. */
    var roh = utm.utm_medium || "";
    var gattung = !roh ? "none" : (MEDIEN.indexOf(roh) >= 0 ? roh : "other");
    var werte = {
      utm_source: utm.utm_source || "direct",
      utm_medium: gattung,
      utm_campaign: utm.utm_campaign || "none",
      utm_medium_raw: roh || "none"
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
