/* Progressive enhancement only. The page is complete without this file. */
(function () {
  "use strict";

  var root = document.documentElement;

  // Footer year, kept current automatically.
  var yearEl = document.querySelector("[data-year]");
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());

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
