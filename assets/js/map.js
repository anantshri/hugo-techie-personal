/**
 * map.js — Leaflet map for talk locations
 * Reads slides.json, places markers with popups, optional clustering
 */
(function () {
  'use strict';

  document.querySelectorAll('.talks-map').forEach(initMap);

  function initMap(el) {
    var zoom = parseInt(el.dataset.zoom, 10) || 2;
    var useCluster = el.dataset.cluster !== 'false';
    var dataUrl = el.dataset.url;

    if (!dataUrl) return;

    // Fix Leaflet default icon paths for vendored setup
    L.Icon.Default.imagePath = '/lib/leaflet/images/';

    var map = L.map(el.id, {
      scrollWheelZoom: false,
      center: [20, 0],
      zoom: zoom
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 18
    }).addTo(map);

    // Enable scroll zoom on focus
    map.on('click', function () { map.scrollWheelZoom.enable(); });
    map.on('mouseout', function () { map.scrollWheelZoom.disable(); });

    // Load data
    fetch(dataUrl)
      .then(function (r) { return r.json(); })
      .then(function (talks) {
        if (!talks || !talks.length) return;

        var markerLayer = useCluster ? L.markerClusterGroup() : L.layerGroup();

        talks.forEach(function (talk) {
          var marker = L.marker([talk.lat, talk.lng]);

          var popup = '<div class="map-popup">';
          if (talk.thumbnail) {
            popup += '<a href="' + talk.url + '"><img src="' + talk.thumbnail + '" alt="" class="map-popup__thumb"></a>';
          }
          popup += '<div class="map-popup__body">';
          popup += '<a href="' + talk.url + '" class="map-popup__title">' + talk.title + '</a>';
          if (talk.conference) {
            popup += '<div class="map-popup__conf">' + talk.conference + '</div>';
          }
          popup += '<div class="map-popup__meta">' + talk.city + ' &middot; ' + talk.date + '</div>';
          popup += '</div></div>';

          marker.bindPopup(popup, { maxWidth: 280, minWidth: 200 });
          markerLayer.addLayer(marker);
        });

        markerLayer.addTo(map);

        // Fit bounds to markers
        if (talks.length > 1) {
          var bounds = L.latLngBounds(talks.map(function (t) { return [t.lat, t.lng]; }));
          map.fitBounds(bounds, { padding: [30, 30], maxZoom: 10 });
        } else {
          map.setView([talks[0].lat, talks[0].lng], 10);
        }
      })
      .catch(function (err) {
        console.warn('Failed to load map data:', err);
      });
  }
})();
