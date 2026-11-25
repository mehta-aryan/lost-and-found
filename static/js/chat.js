/**
 * static/js/chat.js — Campus Lost & Found: private chat
 *
 * - Renders initial server-side bubbles via textContent (no innerHTML for user text)
 * - Sends messages via fetch; falls back to plain form submit when JS unavailable
 * - Polls /chat/<pk>/poll/?after=<id> every ~4 s while visible, pauses when hidden
 * - Polls immediately on window focus (once, without duplicate interval)
 * - De-duplicates by message id
 * - Auto-scrolls to bottom unless the user has scrolled up
 * - Shows network errors via window.showToast() from main.js
 * - Enter = send, Shift+Enter = newline
 * - Auto-grows textarea; resets after send
 * - Consistent timestamps from data-ts ISO attribute
 * - Date separators between messages of different days
 */
(function () {
  'use strict';

  var box      = document.getElementById('chatMsgs');
  var form     = document.getElementById('chatForm');
  var textarea = document.getElementById('msgBody');
  var sendBtn  = document.getElementById('sendBtn');

  if (!box) return;   // not on the chat page

  var SEND_URL = box.dataset.sendUrl;
  var POLL_URL = box.dataset.pollUrl;
  var ME       = parseInt(box.dataset.me, 10);
  var closed   = box.dataset.closed === '1';

  // ── Helpers ──────────────────────────────────────────────────────────────

  function getCSRF() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function safeShowToast(msg, kind) {
    if (typeof window.showToast === 'function') window.showToast(msg, kind || 'danger');
  }

  function formatTime(iso) {
    try {
      return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) { return ''; }
  }

  function localDateKey(iso) {
    var d = new Date(iso);
    return d.getFullYear() + '-' + d.getMonth() + '-' + d.getDate();
  }

  function dateSeparatorLabel(iso) {
    var d = new Date(iso);
    var today = new Date();
    var yesterday = new Date(); yesterday.setDate(today.getDate() - 1);
    if (d.toDateString() === today.toDateString()) return 'Today';
    if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
    return d.toLocaleDateString([], { day: 'numeric', month: 'short', year: 'numeric' });
  }

  // ── Seed from server-rendered messages ───────────────────────────────────
  var renderedIds = {};
  var lastDateKey = null;

  Array.prototype.forEach.call(box.querySelectorAll('[data-msg-id]'), function (el) {
    var bodyEl = el.querySelector('.bubble[data-body]');
    if (bodyEl) {
      bodyEl.textContent = bodyEl.getAttribute('data-body');
      bodyEl.removeAttribute('data-body');
    }
    var ts = el.getAttribute('data-ts');
    var metaEl = el.querySelector('.bubble-meta');
    if (ts && metaEl) metaEl.textContent = formatTime(ts);
    renderedIds[el.dataset.msgId] = true;
    if (ts) lastDateKey = localDateKey(ts);  // track last date but don't insert separators for initial load
  });

  function lastRenderedId() {
    var ids = Object.keys(renderedIds).map(Number);
    return ids.length ? Math.max.apply(null, ids) : 0;
  }

  // ── Scroll ───────────────────────────────────────────────────────────────
  var atBottom = true;
  box.addEventListener('scroll', function () {
    atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 60;
  });
  function scrollToBottom() {
    box.scrollTop = box.scrollHeight;
  }

  scrollToBottom();

  // ── Append a new message bubble ──────────────────────────────────────────
  function appendMessage(m) {
    if (renderedIds[m.id]) return;
    renderedIds[m.id] = true;

    // Date separator
    if (m.ts) {
      var key = localDateKey(m.ts);
      if (key !== lastDateKey) {
        lastDateKey = key;
        var sep = document.createElement('div');
        sep.className = 'date-sep';
        sep.textContent = dateSeparatorLabel(m.ts);
        box.appendChild(sep);
      }
    }

    var group = document.createElement('div');
    group.className = 'msg-group ' + (m.mine ? 'mine' : 'theirs');
    group.setAttribute('data-msg-id', m.id);
    if (m.ts) group.setAttribute('data-ts', m.ts);

    var bubble = document.createElement('div');
    bubble.className = 'bubble ' + (m.mine ? 'bubble-mine' : 'bubble-theirs');
    bubble.textContent = m.body;    // textContent only — never innerHTML

    var meta = document.createElement('div');
    meta.className = 'bubble-meta';
    meta.textContent = m.ts ? formatTime(m.ts) : '';

    group.appendChild(bubble);
    group.appendChild(meta);
    box.appendChild(group);

    if (atBottom) scrollToBottom();
  }

  // ── Seen indicator ───────────────────────────────────────────────────────
  var seenEl = null;  // the current "Seen" element

  function updateSeenIndicator(seen) {
    if (!seen) {
      if (seenEl && seenEl.parentNode) seenEl.parentNode.removeChild(seenEl);
      return;
    }
    var mineGroups = box.querySelectorAll('.msg-group.mine');
    if (!mineGroups.length) {
      if (seenEl && seenEl.parentNode) seenEl.parentNode.removeChild(seenEl);
      return;
    }
    var lastMine = mineGroups[mineGroups.length - 1];
    if (seenEl && seenEl.parentNode === lastMine) return;
    if (seenEl && seenEl.parentNode) seenEl.parentNode.removeChild(seenEl);
    if (!seenEl) {
      seenEl = document.createElement('div');
      seenEl.className = 'seen-indicator';
      seenEl.innerHTML = '<i class="bi bi-check2-all" aria-hidden="true"></i> Seen';
    }
    lastMine.appendChild(seenEl);
    if (atBottom) scrollToBottom();
  }

  var initialMine = box.querySelectorAll('.msg-group.mine');
  if (initialMine.length) {
    updateSeenIndicator(initialMine[initialMine.length - 1].getAttribute('data-read') === '1');
  }

  // ── Polling ──────────────────────────────────────────────────────────────
  var pollTimer = null;
  var POLL_MS   = 4000;

  function poll() {
    if (closed) return;
    var after = lastRenderedId();
    fetch(POLL_URL + '?after=' + after, { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.closed && !closed) {
          closed = true;
          showClosedBanner();
        }
        var msgs = data.messages || [];
        var maxSeenId = after;
        msgs.forEach(function (m) {
          appendMessage(m);
          maxSeenId = Math.max(maxSeenId, Number(m.id) || 0);
        });
        if (typeof data.seen !== 'undefined') {
          var mineGroups = box.querySelectorAll('.msg-group.mine');
          var lastMine = mineGroups.length ? mineGroups[mineGroups.length - 1] : null;
          // Guard against a stale poll overriding a message just sent in this tab
          if (!lastMine || Number(lastMine.dataset.msgId) <= maxSeenId) {
            updateSeenIndicator(Boolean(data.seen));
          }
        }
      })
      .catch(function () { /* silent — network hiccup */ });
  }

  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }

  function startPolling() {
    if (closed) return;
    stopPolling();
    pollTimer = setInterval(poll, POLL_MS);
  }

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) stopPolling(); else { poll(); startPolling(); }
  });
  // On focus: poll once, then let the existing interval continue (or start one)
  window.addEventListener('focus', function () {
    if (!document.hidden) {
      poll();
      if (!pollTimer) startPolling();
    }
  });

  if (!closed) {
    poll();
    startPolling();
  }

  // ── Show closed state dynamically ────────────────────────────────────────
  function showClosedBanner() {
    var footer = document.querySelector('.chat-footer');
    if (!footer) return;
    footer.innerHTML = '';
    var banner = document.createElement('div');
    banner.className = 'chat-closed-banner';
    banner.innerHTML = '<i class="bi bi-lock"></i> This report is resolved — chat is read-only.';
    footer.appendChild(banner);
  }

  // ── Textarea auto-grow ───────────────────────────────────────────────────
  if (textarea) {
    var MAX_ROWS = 6;
    var lineH = 0;
    function autoGrow() {
      textarea.style.height = 'auto';
      if (!lineH) {
        var cs = window.getComputedStyle(textarea);
        lineH = parseFloat(cs.lineHeight) || 20;
      }
      var maxH = lineH * MAX_ROWS + parseFloat(window.getComputedStyle(textarea).paddingTop) * 2;
      textarea.style.height = Math.min(textarea.scrollHeight, maxH) + 'px';
    }
    textarea.addEventListener('input', autoGrow);
  }

  // ── Send ─────────────────────────────────────────────────────────────────
  if (!form || !textarea) return;

  textarea.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    }
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var body = textarea.value.trim();
    if (!body) return;
    if (body.length > 1000) {
      safeShowToast('Message must be 1000 characters or fewer.', 'danger');
      return;
    }

    sendBtn.disabled = true;
    textarea.disabled = true;

    var fd = new FormData();
    fd.append('body', body);
    fd.append('csrfmiddlewaretoken', getCSRF());

    fetch(SEND_URL, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin',
      body: fd,
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.d.error || 'Could not send message.');
        textarea.value = '';
        textarea.style.height = '';   // reset auto-grow
        appendMessage(res.d);
        updateSeenIndicator(Boolean(res.d.read));
        scrollToBottom();
        atBottom = true;
      })
      .catch(function (err) {
        safeShowToast(err.message || 'Network error. Try again.', 'danger');
      })
      .finally(function () {
        sendBtn.disabled = false;
        textarea.disabled = false;
        textarea.focus();
      });
  });
})();
