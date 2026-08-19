/* kaspa pulse navigation
   EIN block fuer alle seiten, geladen ueber capture.js, das ohnehin
   auf jeder seite haengt. Grund: das menue war eine einzige reihe aus
   inzwischen vierzehn pillen. Auf dem telefon steckt es hinter dem
   burger und funktioniert, auf dem desktop lief es ueber zwei zeilen und
   hat den kopf der seite zugestellt. Ab jetzt vier gruppen mit
   aufklappmenue, mobil bleiben alle gruppen im burger untereinander
   aufgeklappt stehen, das ist ein tipp weniger.

   Die vorhandene, statische liste in jeder seite bleibt im quelltext
   stehen und wird hier nur neu sortiert. Google sieht die links also
   weiter direkt im html. Eine neue seite eintragen heisst kuenftig:
   eine zeile in MENUE hier, sonst nichts. */
(function () {
  "use strict";
  var MENUE = [
    { t: "dashboard", h: "/" },
    { t: "network", k: [
      ["hashrate", "/kaspa-hashrate.html"],
      ["mining", "/kaspa-mining.html"],
      ["merged mining", "/merged-mining.html"],
      ["the halving", "/kaspa-halving.html"]
    ]},
    { t: "supply", k: [
      ["supply", "/kaspa-supply.html"],
      ["entity x", "/entity-x.html"],
      ["staking", "/kaspa-staking.html"]
    ]},
    { t: "tokens", k: [
      ["token standards", "/kaspa-token-standard.html"],
      ["smart contracts", "/kaspa-smart-contracts.html"],
      ["kron", "/kron.html"],
      ["tvl", "/kaspa-tvl.html"]
    ]},
    { t: "tools", k: [
      ["wallets", "/kaspa-wallets.html"],
      ["data sources", "/kaspa-data-sources.html"]
    ]}
  ];
  var nc = document.querySelector(".nav .nc");
  if (!nc) return;
  var hier = location.pathname.replace(/\/index\.html$/, "/");
  var css = ""
    + ".nav .nc{justify-content:center;gap:2px;padding:0 10px 9px;}"
    + ".nav .ngrp{position:relative;padding-bottom:6px;margin-bottom:-6px;}"
    + ".nav .ntop{background:none;border:1px solid transparent;color:#9BA3AB;font-family:inherit;"
    + "font-size:12px;padding:5px 8px;border-radius:999px;cursor:pointer;white-space:nowrap;}"
    + ".nav .ntop:hover{color:#FFFFFF;}"
    + ".nav .ntop i{font-style:normal;font-size:9px;margin-left:5px;opacity:0.6;vertical-align:1px;}"
    + ".nav .ngrp.on .ntop{color:#49EACB;background:rgba(73,234,203,0.08);border-color:rgba(73,234,203,0.25);}"
    + ".nav .ndrop{position:absolute;top:100%;left:50%;transform:translateX(-50%);display:none;"
    + "min-width:196px;background:#0B0E12;border:1px solid #1A1D21;border-radius:14px;padding:6px;"
    + "box-shadow:0 18px 44px rgba(0,0,0,0.6);z-index:70;}"
    + ".nav .ngrp:hover .ndrop,.nav .ngrp.open .ndrop{display:block;}"
    + ".nav .ndrop a{display:block;padding:9px 12px;border-radius:9px;font-size:13px;color:#9BA3AB;"
    + "text-decoration:none;white-space:nowrap;border:none;}"
    + ".nav .ndrop a:hover{color:#FFFFFF;background:rgba(255,255,255,0.05);}"
    + ".nav .ndrop a.cur{color:#49EACB;}"
    + "@media(max-width:640px){"
    // das aufgeklappte menue ist hoeher als ein telefonbildschirm. es
    // bekommt deshalb einen eigenen scrollbereich statt die seite darunter
    // zu schieben. overscroll-behavior sorgt dafuer, dass der wisch im
    // menue bleibt und nicht auf die seite ueberspringt.
    + ".nav .nc.open{gap:0;padding:4px 14px 16px;max-height:calc(100vh - 58px);"
    + "max-height:calc(100dvh - 58px);overflow-y:auto;overscroll-behavior:contain;"
    + "-webkit-overflow-scrolling:touch;scrollbar-width:none;}"
    + ".nav .ngrp{width:100%;padding-bottom:0;margin-bottom:0;}"
    + ".nav .nc.open > a{font-size:15px;padding:11px 12px;}"
    + ".nav .nc.open .ntop{width:100%;text-align:left;font-size:10px;letter-spacing:2px;"
    + "text-transform:uppercase;color:#6E757E;padding:13px 12px 3px;cursor:default;}"
    + ".nav .nc.open .ntop i{display:none;}"
    + ".nav .ngrp.on .ntop{background:none;border-color:transparent;}"
    // zwei spalten je gruppe. damit passt das ganze menue auf einen
    // telefonbildschirm und niemand muss ueberhaupt scrollen.
    + ".nav .nc.open .ndrop{position:static;display:grid;grid-template-columns:1fr 1fr;"
    + "gap:0 6px;transform:none;background:none;border:none;box-shadow:none;padding:0;min-width:0;}"
    + ".nav .nc.open .ndrop a{font-size:15px;padding:9px 12px;}"
    // der schwebende knopf verdeckt sonst den letzten menuepunkt
    + "body:has(.nav .nc.open) #kpcBtn{display:none;}"
    + "}"
    // auf schmalen geraeten brach der schriftzug oben auf drei zeilen um
    + "@media(max-width:400px){"
    + ".nav .nlogo{font-size:10.5px;letter-spacing:1.5px;}"
    + ".nav-cta{font-size:9px;padding:5px 9px;letter-spacing:1.5px;}"
    + "}";
  var st = document.createElement("style");
  st.textContent = css;
  document.head.appendChild(st);
  function link(t, h, klasse) {
    var a = document.createElement("a");
    a.href = h; a.textContent = t;
    if (h === hier) a.className = klasse;
    return a;
  }
  nc.innerHTML = "";
  MENUE.forEach(function (e) {
    if (!e.k) { nc.appendChild(link(e.t, e.h, "on")); return; }
    var g = document.createElement("div");
    g.className = "ngrp";
    var b = document.createElement("button");
    b.type = "button";
    b.className = "ntop";
    b.innerHTML = e.t + "<i>&#9662;</i>";
    b.setAttribute("aria-expanded", "false");
    var d = document.createElement("div");
    d.className = "ndrop";
    e.k.forEach(function (p) {
      var a = link(p[0], p[1], "cur");
      if (p[1] === hier) g.classList.add("on");
      d.appendChild(a);
    });
    // tippen oeffnet, ein zweites tippen schliesst. auf dem desktop
    // uebernimmt zusaetzlich hover, damit sich nichts hakelig anfuehlt.
    b.addEventListener("click", function (ev) {
      ev.stopPropagation();
      var offen = g.classList.contains("open");
      Array.prototype.forEach.call(nc.querySelectorAll(".ngrp.open"), function (x) {
        x.classList.remove("open");
        var t = x.querySelector(".ntop");
        if (t) t.setAttribute("aria-expanded", "false");
      });
      if (!offen) { g.classList.add("open"); b.setAttribute("aria-expanded", "true"); }
    });
    g.appendChild(b); g.appendChild(d); nc.appendChild(g);
  });
  document.addEventListener("click", function () {
    Array.prototype.forEach.call(nc.querySelectorAll(".ngrp.open"), function (x) {
      x.classList.remove("open");
    });
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    Array.prototype.forEach.call(nc.querySelectorAll(".ngrp.open"), function (x) {
      x.classList.remove("open");
    });
  });
})();

/* kaspa pulse capture layer
   ein script fuer alle seiten: sticky button + exit intent / timer modal.
   posts gehen an dasselbe brevo formular wie die subscribe box unten.
   verhalten: nach abo nie wieder, nach wegklicken 7 tage ruhe.

   AENDERUNG 18.08.2026, zwei punkte.

   1. Auf schmalen bildschirmen ist es kein fenster mehr, das die seite
      zudeckt, sondern ein schmales band am unteren rand. Google stuft
      aufdringliche einblendungen auf mobilgeraeten ab, ein band am rand
      faellt ausdruecklich nicht darunter. Unsere seiten leben von der
      suche, das risiko gehen wir nicht ein. Die flaeche daneben ist
      durchklickbar, das band faengt keine tipps mehr ab.
   2. Zusaetzlicher ausloeser ueber die scrolltiefe. Wer 55 prozent einer
      seite gelesen hat, hat sein interesse gezeigt, und darauf zu warten
      ist besser als auf eine feste sekundenzahl. Der zeitgeber bleibt als
      rueckfall bestehen.

   Wer es selbst sehen will, muss ein privates fenster benutzen. Nach einer
   anmeldung setzt das script eine markierung im browser und blendet danach
   gar nichts mehr ein, auch den knopf nicht. */
(function () {
  "use strict";
  var ACTION = "https://f926321f.sibforms.com/serve/MUIFAFRuw_TYaNSX3EkJvy138Dd428wMUmHj9SzFap7QLCSAeGmK2p9tHNGmw4FZsutIFsyZ5cbZXGXBYqZGd1a7G_WknNhFvbOZBCI4w0NMVg902P0LTdsllkJVLWfGjkublTW32QT5hFY_LTqkN6ihwbEvTmL5P34zQ6SKTHugFPnR90YZeWSMdEkK8mr6HAvO4-S9dXwuZdkQMA==";
  var KEY = "kp_capture";
  var WEEK = 7 * 24 * 3600 * 1000;
  var state = {};
  try { state = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
  function save() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} }
  if (state.done) return;
  var css = ""
    + "#kpcBtn{position:fixed;right:16px;bottom:16px;z-index:9000;background:#0E141A;"
    + "border:1px solid rgba(73,234,203,0.5);color:#49EACB;font-family:'Helvetica Neue',Arial,sans-serif;"
    + "font-size:12px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;border-radius:999px;"
    + "padding:11px 18px;cursor:pointer;box-shadow:0 4px 24px rgba(0,0,0,0.5);}"
    + "#kpcBtn:hover{background:rgba(73,234,203,0.12);}"
    + "#kpcOv{position:fixed;inset:0;z-index:9500;background:rgba(3,4,6,0.78);display:none;"
    + "align-items:center;justify-content:center;padding:18px;backdrop-filter:blur(3px);}"
    + "#kpcOv.on{display:flex;}"
    + "#kpcCard{position:relative;max-width:430px;width:100%;background:#0B0E12;border:1px solid rgba(73,234,203,0.4);"
    + "border-radius:18px;padding:30px 26px 24px;text-align:center;color:#fff;"
    + "font-family:'Helvetica Neue',Arial,sans-serif;box-shadow:0 0 60px rgba(73,234,203,0.10);}"
    + "#kpcX{position:absolute;top:10px;right:14px;background:none;border:none;color:#7A828C;"
    + "font-size:22px;cursor:pointer;line-height:1;padding:4px;}"
    + "#kpcCard .b{display:inline-block;font-size:10px;letter-spacing:2px;color:#49EACB;"
    + "background:rgba(73,234,203,0.10);border:1px solid rgba(73,234,203,0.35);border-radius:999px;"
    + "padding:3px 10px;margin-bottom:12px;text-transform:uppercase;font-weight:700;}"
    + "#kpcCard .h{font-size:20px;font-weight:700;line-height:1.25;}"
    + "#kpcCard .h b{color:#49EACB;}"
    + "#kpcCard .s{font-size:12.5px;color:#9BA3AB;margin-top:8px;line-height:1.45;}"
    + "#kpcForm{display:flex;gap:8px;margin-top:16px;}"
    + "#kpcForm input[type=email]{flex:1;background:#050608;border:1px solid #1A1D21;border-radius:8px;"
    + "padding:11px 13px;color:#fff;font-size:14px;font-family:inherit;min-width:0;}"
    + "#kpcForm input[type=email]:focus{outline:none;border-color:#49EACB;}"
    + "#kpcForm button{background:#49EACB;color:#04120E;border:none;border-radius:8px;font-weight:700;"
    + "padding:11px 16px;font-size:13px;cursor:pointer;font-family:inherit;white-space:nowrap;}"
    + "#kpcMsg{font-size:12px;margin-top:10px;min-height:14px;}"
    + "#kpcMsg.ok{color:#49EACB;}#kpcMsg.err{color:#E36A6A;}"
    + "#kpcCard .f{font-size:10.5px;color:#7A828C;margin-top:10px;}"
    // schmaler bildschirm: band statt fenster. der hintergrund bleibt frei
    // und durchklickbar, nur die karte selbst faengt tipps ab.
    + "@media(max-width:759px){"
    + "#kpcOv{background:none;backdrop-filter:none;align-items:flex-end;padding:8px;pointer-events:none;}"
    + "#kpcCard{pointer-events:auto;max-width:none;text-align:left;border-radius:14px;"
    + "padding:16px 16px 14px;box-shadow:0 -8px 34px rgba(0,0,0,0.6);}"
    + "#kpcCard .b{margin-bottom:8px;}"
    + "#kpcCard .h{font-size:16px;}"
    + "#kpcCard .s{font-size:12px;margin-top:5px;}"
    + "#kpcForm{flex-direction:column;margin-top:11px;}"
    + "#kpcX{top:8px;right:10px;}"
    + "}"
    + "@media(max-width:480px){#kpcBtn{right:10px;bottom:10px;padding:10px 14px;font-size:11px;}}";
  var st = document.createElement("style");
  st.textContent = css;
  document.head.appendChild(st);
  var wrap = document.createElement("div");
  wrap.innerHTML = ""
    + "<button id='kpcBtn' type='button'>free cheat sheet</button>"
    + "<div id='kpcOv' role='dialog' aria-modal='true' aria-label='newsletter'>"
    + "<div id='kpcCard'>"
    + "<button id='kpcX' type='button' aria-label='close'>&times;</button>"
    + "<div class='b'>free &middot; one page</div>"
    + "<div class='h'>the 8 kaspa numbers <b>whales watch</b></div>"
    + "<div class='s'>how to read supply, hashrate and whale flows like the big wallets do. plus the pulse every monday. no hype, no spam.</div>"
    + "<form id='kpcForm'>"
    + "<input type='email' name='EMAIL' placeholder='you@email.com' required>"
    + "<input type='text' name='email_address_check' value='' style='position:absolute;left:-9999px;' tabindex='-1' autocomplete='off' aria-hidden='true'>"
    + "<input type='hidden' name='locale' value='en'>"
    + "<input type='hidden' name='html_type' value='simple'>"
    + "<button type='submit'>get the sheet</button>"
    + "</form>"
    + "<div id='kpcMsg'></div>"
    + "<div class='f'>free &middot; unsubscribe anytime &middot; delivered after email confirmation</div>"
    + "</div></div>";
  document.body.appendChild(wrap);
  var ov = document.getElementById("kpcOv");
  var msg = document.getElementById("kpcMsg");
  var opened = false;
  function open() {
    if (state.done) return;
    ov.classList.add("on");
    opened = true;
  }
  function close() {
    ov.classList.remove("on");
    state.snooze = Date.now();
    save();
  }
  document.getElementById("kpcBtn").addEventListener("click", open);
  document.getElementById("kpcX").addEventListener("click", close);
  ov.addEventListener("click", function (e) { if (e.target === ov) close(); });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && ov.classList.contains("on")) close();
  });
  document.getElementById("kpcForm").addEventListener("submit", function (e) {
    e.preventDefault();
    var f = e.target, btn = f.querySelector("button[type=submit]");
    btn.disabled = true; btn.textContent = "…";
    msg.className = ""; msg.textContent = "";
    fetch(ACTION, { method: "POST", body: new FormData(f) })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j && j.success) {
          msg.className = "ok";
          msg.textContent = "✓ check your inbox and click the confirmation link. the sheet lands right after.";
          state.done = 1; save();
          var b = document.getElementById("kpcBtn");
          if (b) b.style.display = "none";
          f.style.display = "none";
        } else {
          msg.className = "err";
          msg.textContent = (j && j.message) || "something went wrong, please try again";
          btn.disabled = false; btn.textContent = "get the sheet";
        }
      })
      .catch(function () {
        msg.className = "err";
        msg.textContent = "something went wrong, please try again";
        btn.disabled = false; btn.textContent = "get the sheet";
      });
  });
  // automatik: exit intent am desktop, scrolltiefe und zeitgeber ueberall.
  // nach wegklicken 7 tage ruhe, der button bleibt trotzdem da.
  var quiet = state.snooze && (Date.now() - state.snooze < WEEK);
  if (!quiet) {
    var fired = false, start = Date.now();
    function autoOpen() {
      if (fired || opened) return;
      // wer den anmeldekasten gerade im blick hat, braucht keine einblendung
      var box = document.querySelector(".subscribe");
      if (box) {
        var r = box.getBoundingClientRect();
        if (r.top < window.innerHeight && r.bottom > 0) return;
      }
      fired = true;
      open();
    }
    // scrolltiefe, fruehestens nach zwoelf sekunden
    function onScroll() {
      if (fired || Date.now() - start < 12000) return;
      var h = document.documentElement;
      var tief = (h.scrollTop + window.innerHeight) / Math.max(h.scrollHeight, 1);
      if (tief >= 0.55) { window.removeEventListener("scroll", onScroll); autoOpen(); }
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    if (window.matchMedia && window.matchMedia("(hover:none)").matches) {
      setTimeout(autoOpen, 25000);
    } else {
      document.addEventListener("mouseout", function (e) {
        if (!e.relatedTarget && e.clientY <= 8) autoOpen();
      });
      setTimeout(autoOpen, 45000);
    }
  }
})();
