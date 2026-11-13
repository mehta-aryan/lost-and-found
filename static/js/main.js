/**
 * static/js/main.js — Client-side JavaScript
 *
 * 1. AJAX "Mark as Resolved" using fetch() with CSRF token
 *    — badge updates live, no page reload needed.
 * 2. Tab memory — the active tab (Lost / Found) persists across
 *    page loads using localStorage.
 */

document.addEventListener('DOMContentLoaded', function () {

  // ── CSRF token helper (reads from Django's csrftoken cookie) ──
  function getCSRFToken() {
    var name = 'csrftoken';
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
      var c = cookies[i].trim();
      if (c.indexOf(name + '=') === 0) {
        return c.substring(name.length + 1);
      }
    }
    return '';
  }

  // ── AJAX Resolve ──────────────────────────────────────────────
  document.querySelectorAll('.resolve-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var itemId = this.getAttribute('data-item-id');
      var button = this;

      if (!confirm('Mark this item as resolved?')) return;

      // Disable button to prevent double-clicks
      button.disabled = true;
      button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> …';

      fetch('/item/' + itemId + '/resolve/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCSRFToken(),
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
      })
      .then(function (resp) {
        return resp.json().then(function (data) {
          return { ok: resp.ok, data: data };
        });
      })
      .then(function (result) {
        if (result.ok && result.data.success) {
          // Update badge text and colour
          var badge = document.getElementById('status-badge-' + itemId);
          if (badge) {
            badge.textContent = 'Resolved';
            badge.className = 'badge bg-secondary';
          }
          // Remove the resolve button
          button.remove();
          // Fade the card
          var card = button.closest ? button.closest('.item-card') : null;
          if (card) card.classList.add('card-resolved');
        } else {
          alert(result.data.error || 'Could not resolve the item.');
          button.disabled = false;
          button.innerHTML = '<i class="bi bi-check-circle"></i> Resolve';
        }
      })
      .catch(function (err) {
        alert('Network error — please try again.');
        console.error(err);
        button.disabled = false;
        button.innerHTML = '<i class="bi bi-check-circle"></i> Resolve';
      });
    });
  });

  // ── Tab memory (localStorage) ────────────────────────────────
  var TABS_KEY = 'dashboard_active_tab';
  var tabEls = document.querySelectorAll('#itemTabs button[data-bs-toggle="tab"]');

  // Restore saved tab on page load
  var saved = localStorage.getItem(TABS_KEY);
  if (saved) {
    tabEls.forEach(function (tab) {
      if (tab.getAttribute('data-bs-target') === saved) {
        var bsTab = new bootstrap.Tab(tab);
        bsTab.show();
      }
    });
  }

  // Save active tab whenever the user switches
  tabEls.forEach(function (tab) {
    tab.addEventListener('shown.bs.tab', function () {
      localStorage.setItem(TABS_KEY, this.getAttribute('data-bs-target'));
    });
  });
});
