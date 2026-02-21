/**
 * slideviewer.js — Vanilla JS slide viewer
 * Keyboard nav (←/→/Home/End/G/F/Escape), touch swipe, fullscreen, grid overview, URL hash
 */
(function () {
  'use strict';

  document.querySelectorAll('.slide-viewer').forEach(initViewer);

  function initViewer(viewer) {
    var total = parseInt(viewer.dataset.total, 10) || 0;
    if (total === 0) return;

    var current = 1;
    var slides = viewer.querySelectorAll('.slide-viewer__slide');
    var counter = viewer.querySelector('.slide-viewer__current');
    var prevBtn = viewer.querySelector('.slide-viewer__prev');
    var nextBtn = viewer.querySelector('.slide-viewer__next');
    var gridBtn = viewer.querySelector('.slide-viewer__grid-btn');
    var fsBtn = viewer.querySelector('.slide-viewer__fs-btn');
    var grid = viewer.querySelector('.slide-viewer__grid');
    var gridItems = grid ? grid.querySelectorAll('.slide-viewer__grid-item') : [];

    // ---- Navigation ----
    function goTo(n, pushHash) {
      if (n < 1) n = 1;
      if (n > total) n = total;
      if (n === current) return;

      slides[current - 1].classList.remove('slide-viewer__slide--active');
      slides[n - 1].classList.add('slide-viewer__slide--active');
      current = n;

      if (counter) counter.textContent = current;
      updateNavButtons();
      preloadAdjacent();

      if (pushHash !== false) {
        history.replaceState(null, '', '#slide-' + current);
      }
    }

    function next() { goTo(current + 1); }
    function prev() { goTo(current - 1); }

    function updateNavButtons() {
      if (prevBtn) prevBtn.disabled = current <= 1;
      if (nextBtn) nextBtn.disabled = current >= total;
    }

    // ---- Preload adjacent slides ----
    function preloadAdjacent() {
      var range = 2;
      for (var i = current - range; i <= current + range; i++) {
        if (i < 1 || i > total) continue;
        var img = slides[i - 1].querySelector('img');
        if (img && img.loading === 'lazy') {
          img.loading = 'eager';
        }
      }
    }

    // ---- Grid overlay ----
    function toggleGrid() {
      if (!grid) return;
      var open = grid.hidden;
      grid.hidden = !open;
      if (open) {
        // Highlight current slide in grid
        gridItems.forEach(function (item) {
          item.classList.toggle('slide-viewer__grid-item--active',
            parseInt(item.dataset.slide, 10) === current);
        });
      }
    }

    if (gridBtn) {
      gridBtn.addEventListener('click', toggleGrid);
    }

    if (gridItems.length) {
      gridItems.forEach(function (item) {
        item.addEventListener('click', function () {
          goTo(parseInt(item.dataset.slide, 10));
          grid.hidden = true;
        });
      });
    }

    // ---- Fullscreen ----
    function toggleFullscreen() {
      if (!document.fullscreenElement) {
        viewer.requestFullscreen().catch(function () {});
      } else {
        document.exitFullscreen();
      }
    }

    if (fsBtn) {
      fsBtn.addEventListener('click', toggleFullscreen);
    }

    // ---- Keyboard ----
    viewer.addEventListener('keydown', function (e) {
      switch (e.key) {
        case 'ArrowLeft':
        case 'ArrowUp':
          e.preventDefault();
          prev();
          break;
        case 'ArrowRight':
        case 'ArrowDown':
        case ' ':
          e.preventDefault();
          next();
          break;
        case 'Home':
          e.preventDefault();
          goTo(1);
          break;
        case 'End':
          e.preventDefault();
          goTo(total);
          break;
        case 'g':
        case 'G':
          e.preventDefault();
          toggleGrid();
          break;
        case 'f':
        case 'F':
          e.preventDefault();
          toggleFullscreen();
          break;
        case 'Escape':
          if (grid && !grid.hidden) {
            e.preventDefault();
            grid.hidden = true;
          }
          break;
      }
    });

    // ---- Click nav buttons ----
    if (prevBtn) prevBtn.addEventListener('click', prev);
    if (nextBtn) nextBtn.addEventListener('click', next);

    // ---- Touch / swipe ----
    var touchStartX = 0;
    var touchStartY = 0;
    var swiping = false;

    viewer.addEventListener('touchstart', function (e) {
      touchStartX = e.changedTouches[0].clientX;
      touchStartY = e.changedTouches[0].clientY;
      swiping = true;
    }, { passive: true });

    viewer.addEventListener('touchend', function (e) {
      if (!swiping) return;
      swiping = false;
      var dx = e.changedTouches[0].clientX - touchStartX;
      var dy = e.changedTouches[0].clientY - touchStartY;
      // Only count horizontal swipes (dx > dy and at least 50px)
      if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 50) {
        if (dx < 0) next();
        else prev();
      }
    }, { passive: true });

    // ---- URL hash on load ----
    function readHash() {
      var match = location.hash.match(/^#slide-(\d+)$/);
      if (match) {
        var n = parseInt(match[1], 10);
        if (n >= 1 && n <= total) {
          goTo(n, false);
        }
      }
    }

    readHash();
    window.addEventListener('hashchange', readHash);

    // ---- Initial state ----
    updateNavButtons();
    preloadAdjacent();
  }
})();
