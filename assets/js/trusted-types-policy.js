/**
 * trusted-types-policy.js — Default Trusted Type policy for Leaflet and other libs
 * Must load before any script that assigns to innerHTML (e.g. Leaflet).
 * Creates a default policy so existing innerHTML assignments are allowed.
 */
(function () {
  'use strict';
  if (typeof trustedTypes !== 'undefined' && trustedTypes.createPolicy) {
    try {
      trustedTypes.createPolicy('default', {
        createHTML: function (s) { return s; },
        createScriptURL: function (s) { return s; },
        createURL: function (s) { return s; }
      });
    } catch (e) {
      /* policy may already exist */
    }
  }
})();
