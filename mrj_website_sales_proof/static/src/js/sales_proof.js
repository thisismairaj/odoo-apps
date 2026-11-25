/* Honest Sales Popup: shows real recent orders, real views today and the shop's own trust messages. */
(function () {
    "use strict";

    var FIRST_DELAY = 6000, SHOW_FOR = 7000, GAP = 20000;
    var store = window.sessionStorage;

    function get(key) { try { return store.getItem(key); } catch (e) { return null; } }
    function set(key, val) { try { store.setItem(key, val); } catch (e) { /* private mode */ } }

    function timeAgo(iso) {
        var secs = Math.round((new Date(iso).getTime() - Date.now()) / 1000);
        var lang = document.documentElement.lang || "en";
        var rtf = window.Intl && Intl.RelativeTimeFormat ? new Intl.RelativeTimeFormat(lang, { numeric: "auto" }) : null;
        var steps = [["day", 86400], ["hour", 3600], ["minute", 60]];
        for (var i = 0; i < steps.length; i++) {
            if (Math.abs(secs) >= steps[i][1]) {
                var n = Math.round(secs / steps[i][1]);
                return rtf ? rtf.format(n, steps[i][0]) : Math.abs(n) + " " + steps[i][0] + "s ago";
            }
        }
        return rtf ? rtf.format(0, "minute") : "just now";
    }

    function icon(kind) {
        var path = kind === "views"
            ? "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12zm10 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"
            : "M20 6L9 17l-5-5";
        var span = document.createElement("span");
        span.className = "mrj-sp-icon";
        span.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" ' +
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="' + path + '"/></svg>';
        return span;
    }

    function fill(box, card) {
        var body = box.querySelector(".mrj-sp-body");
        var old = box.querySelector(".mrj-sp-img, .mrj-sp-icon");
        if (old) { old.remove(); }
        body.textContent = "";
        if (card.kind === "order") {
            var img = document.createElement("img");
            img.className = "mrj-sp-img"; img.src = card.img; img.alt = ""; img.loading = "lazy";
            box.insertBefore(img, body);
            body.appendChild(document.createTextNode(card.text + " "));
            var a = document.createElement("a");
            a.href = card.url; a.textContent = card.product;
            body.appendChild(a);
            var meta = document.createElement("span");
            meta.className = "mrj-sp-meta"; meta.textContent = timeAgo(card.at);
            body.appendChild(meta);
        } else {
            box.insertBefore(icon(card.kind), body);
            body.textContent = card.text;
        }
    }

    function build() {
        var box = document.createElement("div");
        box.className = "mrj-sp"; box.hidden = true;
        box.setAttribute("role", "status"); box.setAttribute("aria-live", "polite");
        box.innerHTML = '<div class="mrj-sp-body"></div><button type="button" class="mrj-sp-close" aria-label="Close">&times;</button>';
        document.body.appendChild(box);
        return box;
    }

    function start(data) {
        var cards = data.cards || [];
        if (!cards.length) { return; }
        var box = build(), timer;
        box.querySelector(".mrj-sp-close").addEventListener("click", function () {
            set("mrj_sp_off", "1"); clearTimeout(timer); box.classList.remove("is-on"); box.hidden = true;
        });
        function next() {
            var shown = parseInt(get("mrj_sp_shown") || "0", 10);
            if (get("mrj_sp_off") || shown >= data.max) { return; }
            if (document.body.classList.contains("editor_enable")) { timer = setTimeout(next, GAP); return; }
            fill(box, cards[shown % cards.length]);
            set("mrj_sp_shown", String(shown + 1));
            box.hidden = false;
            requestAnimationFrame(function () { box.classList.add("is-on"); });
            timer = setTimeout(function () {
                box.classList.remove("is-on");
                setTimeout(function () { box.hidden = true; }, 400);
                timer = setTimeout(next, GAP);
            }, SHOW_FOR);
        }
        var params = new URLSearchParams(window.location.search);
        timer = setTimeout(next, params.has("mrj_sp_now") ? 300 : FIRST_DELAY);
    }

    function init() {
        if (get("mrj_sp_off")) { return; }
        var marker = document.querySelector(".mrj-sp-product");
        var params = marker ? { product_template_id: parseInt(marker.dataset.id, 10) } : {};
        fetch("/mrj_sales_proof/cards", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: params }),
        }).then(function (r) { return r.json(); })
          .then(function (res) { if (res && res.result) { start(res.result); } })
          .catch(function () { /* the popup is optional; never break the page */ });
    }

    if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", init); } else { init(); }
})();
