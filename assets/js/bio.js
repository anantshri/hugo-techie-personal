(function () {
  'use strict';

  function switchBioTab(btn, section) {
    var format = btn.getAttribute('data-format');
    section.querySelectorAll('.bio-tab').forEach(function (t) {
      t.classList.remove('active');
    });
    btn.classList.add('active');
    section.querySelectorAll('.bio-content-pane').forEach(function (p) {
      p.classList.remove('active');
    });
    var pane = section.querySelector('[data-pane="' + format + '"]');
    if (pane) pane.classList.add('active');
  }

  function copyBio(btn, section) {
    var activeTab = section.querySelector('.bio-tab.active');
    var format = activeTab ? activeTab.getAttribute('data-format') : 'html';
    var pane = section.querySelector('[data-pane="' + format + '"]');
    if (!pane) return;

    var content = format === 'html' ? pane.innerHTML.trim() : pane.textContent.trim();

    navigator.clipboard.writeText(content).then(function () {
      var orig = btn.innerHTML;
      btn.innerHTML = '\u2713 Copied!';
      btn.classList.add('copied');
      setTimeout(function () {
        btn.innerHTML = orig;
        btn.classList.remove('copied');
      }, 2000);
    });
  }

  document.addEventListener('click', function (e) {
    var tab = e.target.closest('.bio-tab');
    if (tab) {
      var section = tab.closest('[data-bio-section]');
      if (section) switchBioTab(tab, section);
      return;
    }

    var copyBtn = e.target.closest('.bio-copy-btn');
    if (copyBtn) {
      var section = copyBtn.closest('[data-bio-section]');
      if (section) copyBio(copyBtn, section);
    }
  });
})();
