/* Progressive enhancement only. The page is complete without this file.
   No inline styles are used anywhere (the production CSP forbids them):
   state is expressed with classes and attributes, and the reading progress bar
   is drawn by a CSS scroll-driven animation. */
(function () {
  "use strict";

  var root = document.documentElement;

  // Footer year, kept current automatically.
  var yearEl = document.querySelector("[data-year]");
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());

  // --- Section index panel ------------------------------------------------
  var toc = document.querySelector("[data-toc]");
  if (toc) {
    var tocToggle = toc.querySelector("summary");
    toc.addEventListener("click", function (event) {
      // Choosing a section closes the panel; the anchor still navigates.
      if (event.target.closest && event.target.closest("a")) toc.open = false;
    });
    document.addEventListener("click", function (event) {
      if (toc.open && !toc.contains(event.target)) toc.open = false;
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && toc.open) {
        toc.open = false;
        if (tocToggle) tocToggle.focus();
      }
    });
  }

  // --- Print action (only offered when it can work) -----------------------
  var printBtn = document.querySelector("[data-print]");
  if (printBtn) {
    printBtn.hidden = false;
    printBtn.addEventListener("click", function () { window.print(); });
  }

  // --- Language switch keeps the reader in the same section ---------------
  var langSwitch = document.querySelector(".lang-switch");
  if (langSwitch && window.location.hash.length > 1) {
    langSwitch.setAttribute("href", langSwitch.getAttribute("href") + window.location.hash);
  }

  // --- Current section, progress and back-to-top --------------------------
  var toTop = document.querySelector("[data-back-to-top]");
  var headerEl = document.querySelector(".site-header");
  var sections = Array.prototype.slice.call(document.querySelectorAll("main section[id]"));
  var links = Array.prototype.slice.call(
    document.querySelectorAll('.primary-nav a[href^="#"], .toc-list a[href^="#"]')
  );
  var linksById = {};
  links.forEach(function (link) {
    var id = link.getAttribute("href").slice(1);
    (linksById[id] = linksById[id] || []).push(link);
  });

  function markCurrent(id) {
    Object.keys(linksById).forEach(function (key) {
      var isCurrent = key === id;
      linksById[key].forEach(function (link) {
        link.classList.toggle("is-active", isCurrent);
        if (isCurrent) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
    });
  }

  var ticking = false;
  function update() {
    ticking = false;
    var y = window.pageYOffset || root.scrollTop || 0;
    var headerH = headerEl ? headerEl.offsetHeight : 0;
    if (toTop) toTop.hidden = y < 600;

    // A section becomes current once its top crosses the reading line:
    // just below the sticky header, or 40% of the viewport on tall screens.
    var line = Math.max(headerH + 48, window.innerHeight * 0.4);
    var current = "";
    for (var i = 0; i < sections.length; i++) {
      var box = sections[i].getBoundingClientRect();
      if (box.top <= line) current = sections[i].id;
    }
    // At the end of the page the last section may never cross the line.
    if (sections.length && y + window.innerHeight >= document.documentElement.scrollHeight - 2) {
      current = sections[sections.length - 1].id;
    }
    markCurrent(current);
  }
  function requestUpdate() {
    if (!ticking) {
      ticking = true;
      window.requestAnimationFrame(update);
    }
  }
  window.addEventListener("scroll", requestUpdate, { passive: true });
  window.addEventListener("resize", requestUpdate);
  window.addEventListener("hashchange", requestUpdate);
  update();

  if (toTop) {
    toTop.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "auto" });
    });
  }

  // --- Reveal on scroll ---------------------------------------------------
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduceMotion || !("IntersectionObserver" in window)) return;

  // Only hide reveal elements once we know they will be revealed.
  root.classList.add("motion");

  var items = document.querySelectorAll(".reveal");
  var io = new IntersectionObserver(
    function (entries, observer) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-in");
          observer.unobserve(entry.target);
        }
      });
    },
    { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
  );
  items.forEach(function (el) { io.observe(el); });
})();
