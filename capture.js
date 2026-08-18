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
