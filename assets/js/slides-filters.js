/**
 * slides-filters.js — Filter slides listing by year and conference (vanilla JS)
 * Binds to #filter-year, #filter-conference and .slides-grid__item; no inline handlers.
 */
(function () {
  'use strict';

  function filterSlides() {
    var yearEl = document.getElementById('filter-year');
    var confEl = document.getElementById('filter-conference');
    var year = yearEl ? yearEl.value : '';
    var conf = confEl ? confEl.value : '';
    var items = document.querySelectorAll('.slides-grid__item');
    var visible = 0;
    items.forEach(function (item) {
      var show = true;
      if (year && item.dataset.year !== year) show = false;
      if (conf && item.dataset.conference !== conf) show = false;
      item.style.display = show ? '' : 'none';
      if (show) visible++;
    });
    var countEl = document.getElementById('slides-count');
    if (countEl) {
      countEl.textContent = visible + ' presentation' + (visible !== 1 ? 's' : '');
    }
  }

  function init() {
    var yearEl = document.getElementById('filter-year');
    var confEl = document.getElementById('filter-conference');
    if (yearEl) yearEl.addEventListener('change', filterSlides);
    if (confEl) confEl.addEventListener('change', filterSlides);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
