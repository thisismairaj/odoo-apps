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
        function say(msg) {
            toast.textContent = msg;
            toast.classList.add("is-on");
            clearTimeout(timer);
            timer = setTimeout(function () { toast.classList.remove("is-on"); }, 3500);
        }
        function open(state) {
            menu.hidden = !state;
            btn.setAttribute("aria-expanded", state ? "true" : "false");
        }
        btn.addEventListener("click", function (e) { e.stopPropagation(); open(menu.hidden); });
        document.addEventListener("click", function (e) { if (!menu.hidden && !root.contains(e.target)) { open(false); } });
        document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !menu.hidden) { open(false); btn.focus(); } });
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
