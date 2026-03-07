/**
 * analytics-google.js — Google Analytics gtag config (no inline script)
 * Reads tracking ID from meta name="ga-tracking-id"; must load after gtag/js is requested.
 */
(function () {
  'use strict';
  var meta = document.querySelector('meta[name="ga-tracking-id"]');
  var id = meta ? meta.getAttribute('content') : '';
  if (!id) return;
  window.dataLayer = window.dataLayer || [];
  function gtag() { dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag('js', new Date());
  gtag('config', id);
})();
