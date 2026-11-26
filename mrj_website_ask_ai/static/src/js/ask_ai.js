/* Ask AI About This Product: opens the shopper's own assistant with the question filled in. */
(function () {
    "use strict";

    function copyText(text) {
        if (navigator.clipboard && window.isSecureContext) {
            return navigator.clipboard.writeText(text).catch(function () {});
        }
        var area = document.createElement("textarea");
        area.value = text;
        area.setAttribute("readonly", "");
        area.style.position = "fixed";
        area.style.opacity = "0";
        document.body.appendChild(area);
        area.select();
        try { document.execCommand("copy"); } catch (e) { /* nothing else to try */ }
        document.body.removeChild(area);
        return Promise.resolve();
    }

    function setup(root) {
        if (root.dataset.ready) { return; }
        root.dataset.ready = "1";
        var btn = root.querySelector(".mrj-askai-btn");
        var menu = root.querySelector(".mrj-askai-menu");
        var toast = root.querySelector(".mrj-askai-toast");
        var timer;
        // Move the menu to <body>: the product column is its own stacking context (z-index 0), which would
        // otherwise put the menu under the next page section.
        document.body.appendChild(menu);
        function say(msg) {
            toast.textContent = msg;
            toast.classList.add("is-on");
            clearTimeout(timer);
            timer = setTimeout(function () { toast.classList.remove("is-on"); }, 3500);
        }
        function place() {
            // Below the button, or above it when there is no room below; kept inside the viewport.
            var r = btn.getBoundingClientRect();
            var mh = menu.offsetHeight, mw = menu.offsetWidth, gap = 6;
            var top = r.bottom + gap;
            if (top + mh > window.innerHeight - 8 && r.top - gap - mh > 8) { top = r.top - gap - mh; }
            var left = Math.min(r.left, window.innerWidth - mw - 8);
            menu.style.top = Math.max(8, top) + "px";
            menu.style.left = Math.max(8, left) + "px";
        }
        function open(state) {
            menu.hidden = !state;
            btn.setAttribute("aria-expanded", state ? "true" : "false");
            if (state) { place(); }
        }
        btn.addEventListener("click", function (e) { e.preventDefault(); open(menu.hidden); });
        // Capture phase, so a page script that stops click propagation can't keep the menu open.
        document.addEventListener("pointerdown", function (e) {
            if (!menu.hidden && !btn.contains(e.target) && !menu.contains(e.target)) { open(false); }
        }, true);
        document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !menu.hidden) { open(false); btn.focus(); } });
        // A click inside an iframe (chat widget, video) never reaches this document, but it blurs the window.
        window.addEventListener("blur", function () { if (!menu.hidden) { open(false); } });
        window.addEventListener("scroll", function () { if (!menu.hidden) { place(); } }, true);
        window.addEventListener("resize", function () { if (!menu.hidden) { place(); } });
        menu.addEventListener("click", function (e) {
            var item = e.target.closest(".mrj-askai-item");
            if (!item) { return; }
            if (item.dataset.kind === "copy") {
                copyText(root.dataset.copy).then(function () { say(root.dataset.msgCopiedAll); });
            } else {
                if (item.dataset.copyFirst === "1") {
                    copyText(root.dataset.prompt).then(function () { say(root.dataset.msgCopied); });
                }
                window.open(item.dataset.url, "_blank", "noopener");
            }
            open(false);
        });
    }

    function init() { document.querySelectorAll(".mrj-askai").forEach(setup); }
    if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", init); } else { init(); }
})();
