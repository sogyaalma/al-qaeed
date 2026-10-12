/* Progressive enhancement only. The page is complete without this file. */
(function () {
  "use strict";

  var root = document.documentElement;

  // Footer year, kept current automatically.
  var yearEl = document.querySelector("[data-year]");
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());

  // Scrollspy: highlight the nav link of the section in view.
  // Progressive enhancement; the nav works the same without JavaScript.
  var nav = document.querySelector(".primary-nav");
  if (nav && "IntersectionObserver" in window) {
    var links = {};
    nav.querySelectorAll('a[href^="#"]').forEach(function (a) {
      links[a.getAttribute("href").slice(1)] = a;
    });
    var sections = Object.keys(links)
      .map(function (id) { return document.getElementById(id); })
      .filter(Boolean);
    var setActive = function (id) {
      Object.keys(links).forEach(function (key) {
        var on = key === id;
        links[key].classList.toggle("is-active", on);
        if (on) links[key].setAttribute("aria-current", "location");
        else links[key].removeAttribute("aria-current");
      });
    };
    var update = function () {
      var line = window.innerHeight * 0.4;
      var current = null;
      sections.forEach(function (s) {
        if (s.getBoundingClientRect().top <= line) current = s.id;
      });
      // At the end of the page the last section may never cross the line.
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) {
        current = sections[sections.length - 1].id;
      }
      setActive(current);
    };
    var spy = new IntersectionObserver(update, { rootMargin: "-40% 0px -55% 0px" });
    sections.forEach(function (s) { spy.observe(s); });
  }

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
