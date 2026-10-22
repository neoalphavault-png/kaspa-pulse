/* rahmen.js, das Menue im Rahmen der Unterseiten (Ben, 22.10.2026, PR 3).
   Dasselbe Verhalten wie auf der Startseite: am Desktop klappen die Gruppen
   auf (Hover oder Tippen), am Handy oeffnet der Knopf das ganze Menue mit
   allen Gruppen offen. Escape schliesst. */
(function () {
  "use strict";
  var menu = document.getElementById("menu"), burger = document.querySelector(".kpbar .burger");
  if (!menu || !burger) return;
  function zu() { menu.classList.remove("open"); burger.setAttribute("aria-expanded", "false"); burger.textContent = "menu"; }
  burger.addEventListener("click", function () {
    var o = menu.classList.toggle("open");
    burger.setAttribute("aria-expanded", o); burger.textContent = o ? "close" : "menu";
  });
  [].forEach.call(menu.querySelectorAll("a"), function (a) { a.addEventListener("click", zu); });
  function gruppenZu() {
    [].forEach.call(menu.querySelectorAll(".grp.open"), function (g) {
      g.classList.remove("open"); g.querySelector(".gbtn").setAttribute("aria-expanded", "false");
    });
  }
  [].forEach.call(menu.querySelectorAll(".gbtn"), function (b) {
    b.addEventListener("click", function (ev) {
      ev.stopPropagation();
      var g = b.parentNode, offen = g.classList.contains("open");
      gruppenZu();
      if (!offen) { g.classList.add("open"); b.setAttribute("aria-expanded", "true"); }
    });
  });
  document.addEventListener("click", function (e) { if (!e.target.closest || !e.target.closest(".grp")) gruppenZu(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") { gruppenZu(); zu(); } });
})();
