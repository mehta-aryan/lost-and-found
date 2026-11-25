/**
 * static/js/main.js — Campus Lost & Found (vanilla JS, no build step)
 *
 *  1. Theme toggle (light / dark), remembered in localStorage
 *  2. Toasts for Django flash messages + a showToast() helper
 *  3. Confirm modal (replaces window.confirm) for forms and the Resolve button
 *  4. AJAX "Mark as resolved" with CSRF token — updates the page without reload
 *  5. Photo picker: preview, drag & drop, type/size check
 *  6. Dashboard: remember last tab, auto-submit filter selects
 *  7. Copy-link button
 *  8. Count-up animation for resolved count + tab counts
 *  9. Card stagger index + image shimmer cleanup
 */
(function () {
  'use strict';

  var $  = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  function store(action, key, value) {           // localStorage can throw (private mode)
    try {
      if (action === 'get') return localStorage.getItem(key);
      if (action === 'set') localStorage.setItem(key, value);
    } catch (e) { /* ignore */ }
    return null;
  }

  function getCSRFToken() {
    var meta = $('meta[name="csrf-token"]');                 // rendered on every page by base.html
    if (meta && meta.content) return meta.content;
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  /* ── 1. Theme ─────────────────────────────── */
  var themeBtn = $('#themeToggle');
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      var root = document.documentElement;
      var next = root.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-bs-theme', next);
      store('set', 'lf-theme', next);
    });
  }

  /* ── 2. Toasts ────────────────────────────── */
  function showToast(message, kind) {
    var stack = $('#toastStack');
    if (!stack || !window.bootstrap) return;
    var el = document.createElement('div');
    el.className = 'toast lf-toast align-items-center border-0 text-bg-' + (kind || 'success');
    el.setAttribute('role', kind === 'danger' ? 'alert' : 'status');
    el.setAttribute('aria-live', kind === 'danger' ? 'assertive' : 'polite');
    el.innerHTML = '<div class="d-flex"><div class="toast-body"></div>' +
      '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>' +
      '<div class="toast-progress"></div>';
    el.querySelector('.toast-body').textContent = message;      // textContent → no HTML injection
    stack.appendChild(el);
    el.addEventListener('hidden.bs.toast', function () { el.remove(); });
    new bootstrap.Toast(el, { delay: 5000 }).show();
  }
  window.showToast = showToast;   // expose globally so chat.js can use it

  $$('#toastStack .toast').forEach(function (el) {              // server-rendered flash messages
    new bootstrap.Toast(el, { delay: 6000 }).show();
  });

  // A toast queued before a page reload (see resolve on the detail page)
  try {
    var queued = sessionStorage.getItem('lf-flash');
    if (queued) {
      sessionStorage.removeItem('lf-flash');
      var parsed = JSON.parse(queued);
      showToast(parsed.message, parsed.kind);
    }
  } catch (e) { /* ignore */ }

  /* ── 3. Confirm modal ─────────────────────── */
  var confirmEl = $('#confirmModal');
  var confirmModal = confirmEl && window.bootstrap ? new bootstrap.Modal(confirmEl) : null;
  var pendingAction = null;

  function askConfirm(opts, onConfirm) {
    if (!confirmModal) { if (window.confirm(opts.body || opts.title)) onConfirm(); return; }
    $('#confirmTitle').textContent = opts.title || 'Are you sure?';
    $('#confirmBody').textContent = opts.body || '';
    var ok = $('#confirmOk');
    ok.textContent = opts.label || 'Confirm';
    ok.className = 'btn ' + (opts.danger ? 'btn-danger' : 'btn-primary');
    pendingAction = onConfirm;
    confirmModal.show();
  }

  if (confirmEl) {
    $('#confirmOk').addEventListener('click', function () {
      var fn = pendingAction;
      pendingAction = null;
      confirmModal.hide();
      if (fn) fn();
    });
    confirmEl.addEventListener('hidden.bs.modal', function () { pendingAction = null; });
  }

  // <form data-confirm="Body text" data-confirm-title="…" data-confirm-label="…" data-confirm-danger>
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form.matches || !form.matches('form[data-confirm]') || form.dataset.confirmed) return;
    e.preventDefault();
    askConfirm({
      title: form.dataset.confirmTitle,
      body: form.dataset.confirm,
      label: form.dataset.confirmLabel,
      danger: form.hasAttribute('data-confirm-danger')
    }, function () {
      form.dataset.confirmed = '1';
      if (form.requestSubmit) form.requestSubmit(); else form.submit();
    });
  });

  /* ── 4. AJAX resolve ──────────────────────── */
  function resolveItem(btn) {
    var id = btn.dataset.itemId;
    var original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Saving…';

    fetch(btn.dataset.url, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCSRFToken(), 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin'
    })
      .then(function (resp) { return resp.json().then(function (data) { return { ok: resp.ok, data: data }; }); })
      .then(function (result) {
        if (!(result.ok && result.data.success)) throw new Error(result.data.error || 'Could not resolve this report.');

        if (btn.hasAttribute('data-reload')) {                  // detail page: show stamp then reload
          // Stamp animation on the ticket media/photo frame
          var mediaArea = document.querySelector('.photo-frame, .tag-media');
          if (mediaArea && !mediaArea.querySelector('.stamp')) {
            var stamp = document.createElement('span');
            stamp.className = 'stamp animate-in';
            stamp.setAttribute('data-label', 'Resolved');
            mediaArea.style.position = 'relative';
            mediaArea.appendChild(stamp);
          }
          try { sessionStorage.setItem('lf-flash', JSON.stringify({ message: 'Report marked as resolved.', kind: 'success' })); } catch (e) { /* ignore */ }
          setTimeout(function () { window.location.reload(); }, 650);
          return;
        }
        $$('.tag-card[data-item-id="' + id + '"]').forEach(function (card) {
          card.classList.add('is-resolved');
          var media = $('.tag-media', card);
          if (media && !$('.stamp', media)) {
            var stamp = document.createElement('span');
            stamp.className = 'stamp animate-in';
            stamp.setAttribute('data-label', 'Resolved');
            media.appendChild(stamp);
          }
        });
        $$('.resolve-btn[data-item-id="' + id + '"]').forEach(function (b) { b.remove(); });
        showToast('Report marked as resolved.', 'success');
      })
      .catch(function (err) {
        btn.disabled = false;
        btn.innerHTML = original;
        showToast(err.message || 'Network error. Please try again.', 'danger');
      });
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.resolve-btn');
    if (!btn) return;
    askConfirm({
      title: 'Mark as resolved?',
      body: 'Use this once the item is back with its owner. The report stops appearing in open lists.',
      label: 'Mark resolved'
    }, function () { resolveItem(btn); });
  });

  /* ── 5. Photo picker ──────────────────────── */
  $$('[data-dropzone]').forEach(function (zone) {
    var wrap = zone.closest('.dropzone-wrap');
    var input = $('input[type="file"]', wrap);
    var preview = $('.dz-preview', zone);
    var empty = $('.dz-empty', zone);
    var nameEl = $('.dz-name', zone);
    var errorEl = $('.dz-error', wrap);
    if (!input) return;

    var maxMb = parseFloat(input.dataset.maxMb || '5');
    var okTypes = ['image/jpeg', 'image/png', 'image/webp'];

    function setError(msg) { if (errorEl) { errorEl.textContent = msg || ''; errorEl.classList.toggle('d-none', !msg); } }

    function handle(file) {
      setError('');
      if (!file) return;
      if (okTypes.indexOf(file.type) === -1) { input.value = ''; setError('Only JPEG, PNG, and WebP images are allowed.'); return; }
      if (file.size > maxMb * 1024 * 1024) { input.value = ''; setError('Image must be smaller than ' + maxMb + ' MB.'); return; }
      var reader = new FileReader();
      reader.onload = function (ev) {
        preview.src = ev.target.result;
        preview.classList.remove('d-none');
        if (empty) empty.classList.add('d-none');
        if (nameEl) nameEl.textContent = file.name + ' · ' + (file.size / 1024 / 1024).toFixed(1) + ' MB — click to change';
      };
      reader.readAsDataURL(file);
    }

    input.addEventListener('change', function () { handle(input.files[0]); });
    ['dragenter', 'dragover'].forEach(function (t) {
      zone.addEventListener(t, function (e) { e.preventDefault(); zone.classList.add('is-drag'); });
    });
    ['dragleave', 'drop'].forEach(function (t) {
      zone.addEventListener(t, function (e) { e.preventDefault(); zone.classList.remove('is-drag'); });
    });
    zone.addEventListener('drop', function (e) {
      if (e.dataTransfer && e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        handle(input.files[0]);
      }
    });
  });

  /* ── 6. Dashboard: tab memory + filters ───── */
  var tabs = $('#itemTabs');
  if (tabs && window.bootstrap) {
    var KEY = 'lf-active-tab';
    var tabButtons = $$('button[data-bs-toggle="tab"]', tabs);

    if (tabs.dataset.explicit !== '1') {                        // URL didn't pick a tab → restore the last one
      var saved = store('get', KEY);
      tabButtons.forEach(function (b) {
        if (saved && b.getAttribute('data-bs-target') === saved) new bootstrap.Tab(b).show();
      });
    }
    tabButtons.forEach(function (b) {
      b.addEventListener('shown.bs.tab', function () { store('set', KEY, b.getAttribute('data-bs-target')); });
    });
  }

  $$('select[data-autosubmit]').forEach(function (sel) {
    sel.addEventListener('change', function () { sel.form.submit(); });
  });

  /* ── 7. Copy link ─────────────────────────── */
  $$('[data-copy-link]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (!navigator.clipboard) { showToast('Copy is not available in this browser.', 'danger'); return; }
      navigator.clipboard.writeText(window.location.href.split('#')[0]).then(function () {
        showToast('Link copied.', 'info');
      });
    });
  });

  /* ── 8. Count-up animation ────────────────── */
  function countUp(el) {
    var target = parseInt(el.textContent, 10);
    if (!target || target < 2) return;   // no point animating 0 or 1
    var start = 0;
    var dur = 600;
    var startTs = null;
    function step(ts) {
      if (!startTs) startTs = ts;
      var prog = Math.min((ts - startTs) / dur, 1);
      // ease-out: prog^0.5
      el.textContent = Math.round(start + (target - start) * Math.sqrt(prog));
      if (prog < 1) requestAnimationFrame(step);
      else el.textContent = target;
    }
    requestAnimationFrame(step);
  }

  // Resolved count
  $$('.reunited.tnum').forEach(function (el) {
    // The number is inside the text; we need to target just the number
    // The HTML is: "N reports resolved so far" — wrap the number via JS
    var text = el.textContent;
    var m = text.match(/^(\d+)/);
    if (!m) return;
    var span = document.createElement('span');
    span.textContent = m[1];
    el.textContent = text.replace(m[1], '');
    el.prepend(span);
    countUp(span);
  });

  // Tab count badges
  $$('.seg .count.tnum').forEach(function (el) {
    countUp(el);
  });

  /* ── 9. Image shimmer cleanup ─────────────── */
  $$('img[loading="lazy"]').forEach(function (img) {
    if (img.complete) {
      img.classList.add('loaded');
    } else {
      img.addEventListener('load', function () { img.classList.add('loaded'); });
    }
  });

  /* ── 10. Card stagger --i index ───────────── */
  $$('.tag-card').forEach(function (card, i) {
    // Cap at 8 for performance (after that instant)
    card.style.setProperty('--i', Math.min(i, 8));
  });

})();
