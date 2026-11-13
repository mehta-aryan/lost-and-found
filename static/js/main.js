/**
 * static/js/main.js — Client-side JavaScript for Campus Lost & Found
 *
 * Handles AJAX "Mark as Resolved" using fetch() with CSRF token.
 * No page reload needed — the badge updates live via DOM manipulation.
 */

document.addEventListener('DOMContentLoaded', function () {

  // ── Get CSRF token from the cookie (Django sets it automatically) ──
  function getCSRFToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + '=')) {
        return cookie.substring(name.length + 1);
      }
    }
    return '';
  }

  // ── Attach click handlers to all "Resolve" buttons ──
  document.querySelectorAll('.resolve-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const itemId = this.getAttribute('data-item-id');
      const button = this;

      // Confirm before resolving
      if (!confirm('Mark this item as resolved?')) return;

      // Send AJAX POST request to the resolve endpoint
      fetch('/item/' + itemId + '/resolve/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCSRFToken(),
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',    // Include session cookie
      })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        if (data.success) {
          // Update the status badge without reloading
          const badge = document.getElementById('status-badge-' + itemId);
          if (badge) {
            badge.textContent = 'Resolved';
            badge.className = 'badge bg-secondary';
          }
          // Hide the resolve button (no longer needed)
          button.style.display = 'none';
          // Fade the card if on dashboard
          const card = button.closest('.item-card');
          if (card) {
            card.classList.add('card-resolved');
          }
        } else {
          alert(data.error || 'Could not resolve the item.');
        }
      })
      .catch(function (err) {
        alert('Network error. Please try again.');
        console.error(err);
      });
    });
  });
});

