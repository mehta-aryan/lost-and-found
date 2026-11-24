/**
 * static/js/chat.js — Campus Lost & Found: private chat
 *
 * - Renders initial server-side bubbles via textContent (no innerHTML for user text)
 * - Sends messages via fetch; falls back to plain form submit when JS unavailable
 * - Polls /chat/<pk>/poll/?after=<id> every ~4 s while visible, pauses when hidden
 * - Polls immediately on window focus
 * - De-duplicates by message id
 * - Auto-scrolls to bottom unless the user has scrolled up
 * - Shows network errors via showToast() from main.js
 * - Enter = send, Shift+Enter = newline
 */
(function () {
  'use strict';

  var box     = document.getElementById('chatMsgs');
  var form    = document.getElementById('chatForm');
  var textarea = document.getElementById('msgBody');
  var sendBtn  = document.getElementById('sendBtn');

  if (!box) return;   // not on the chat page

  var SEND_URL   = box.dataset.sendUrl;
  var POLL_URL   = box.dataset.pollUrl;
  var ME         = parseInt(box.dataset.me, 10);
  var closed     = box.dataset.closed === '1';

  // ── Render initial bubbles (textContent, never innerHTML for user body) ──
  Array.prototype.forEach.call(box.querySelectorAll('.bubble[data-body]'), function (el) {
    el.textContent = el.getAttribute('data-body');
    el.removeAttribute('data-body');
  });

  // ── Helpers ──────────────────────────────────────────────────────────────

  function getCSRF() {
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function safeShowToast(msg, kind) {
    if (typeof showToast === 'function') showToast(msg, kind || 'danger');
  }

  var renderedIds = {};
  // Seed from server-rendered messages
  Array.prototype.forEach.call(box.querySelectorAll('[data-msg-id]'), function (el) {
    renderedIds[el.dataset.msgId] = true;
  });

  function lastRenderedId() {
    var ids = Object.keys(renderedIds).map(Number);
    return ids.length ? Math.max.apply(null, ids) : 0;
  }

  var atBottom = true;
  box.addEventListener('scroll', function () {
    atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 60;
  });
  function scrollToBottom() {
    box.scrollTop = box.scrollHeight;
  }

  function formatTime(iso) {
    try {
      return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) { return ''; }
  }

  function appendMessage(m) {
    if (renderedIds[m.id]) return;
    renderedIds[m.id] = true;

    var group = document.createElement('div');
    group.className = 'msg-group ' + (m.mine ? 'mine' : 'theirs');
    group.setAttribute('data-msg-id', m.id);

    var bubble = document.createElement('div');
    bubble.className = 'bubble ' + (m.mine ? 'bubble-mine' : 'bubble-theirs');
    bubble.textContent = m.body;    // textContent only — never innerHTML

    var meta = document.createElement('div');
    meta.className = 'bubble-meta';
    meta.textContent = formatTime(m.ts);

    group.appendChild(bubble);
    group.appendChild(meta);
    box.appendChild(group);

    if (atBottom) scrollToBottom();
  }

  scrollToBottom();

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
        (data.messages || []).forEach(appendMessage);
      })
      .catch(function () { /* silent — network hiccup */ });
  }

  function startPolling() {
    if (closed) return;
    stopPolling();
    poll();
    pollTimer = setInterval(poll, POLL_MS);
  }

  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) stopPolling(); else startPolling();
  });
  window.addEventListener('focus', function () { if (!document.hidden) { stopPolling(); poll(); startPolling(); } });

  if (!closed) startPolling();

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
        textarea.style.height = '';
        appendMessage(res.d);
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
