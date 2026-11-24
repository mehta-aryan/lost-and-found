# 🔍 Campus Lost & Found

A web app where college students report lost items, log found items, and get them back to their owners. Built with Django (MVT), Bootstrap 5 and Google sign-in via django-allauth.

Reports look like **claim tickets** (punched hole, perforated stub). Lost is red, Found is teal, and there is a light and a dark theme.

---

## ✨ Features

- **Google sign-in, college accounts only.** Verified email + domain check; local sign-up is closed so it can't be bypassed
- **Dashboard** with Lost / Found tabs, search (name, place, description), category and status filters, pagination
- **Private in-app chat.** "I found this" on a lost report, "This is mine" on a found one. Conversations stay private between the poster and each visitor — no emails are sent or exposed
- **Possible matches** shown on every open report (opposite type, same category, within 14 days, shared words)
- **Report CRUD** with categories, photo upload (drag & drop, preview, type/size checks), and automatic clean-up of old photos
- **AJAX "Mark resolved"** with CSRF protection and a confirm dialog (allowed for the poster or staff); resolving locks existing chats to read-only
- **My reports & Messages inbox** with unread-message badges
- **Light / dark theme**, responsive layout, keyboard-accessible, respects reduced-motion
- **Admin**: filters, inline status edit, bulk "mark resolved", conversation & message inspection
- **`seed_demo`** command to fill the app with sample data
- **Automated test suite** covering auth, CRUD, chat, permissions, and matching

---

## 📁 Project structure (MVT mapping for viva)

| Layer | File(s) | Purpose |
|---|---|---|
| **Model** | `items/models.py` | `UserProfile`, `ItemReport` (with categories), `Conversation`, `Message` |
| **View** | `items/views.py` | Dashboard, detail, CRUD, resolve (AJAX), inbox & chat (`start_chat`, `chat_detail`, `send_message`, `poll_chat`) |
| **Template** | `templates/base.html`, `items/templates/items/` | Django Template Language; `inbox.html`, `chat.html`, `_item_card`, `_item_form`, `_field`, `_pagination` |
| URLs | `lostfound_project/urls.py`, `items/urls.py` | URL → view mapping |
| Forms | `items/forms.py` | `ItemReportForm` (validation), `MessageForm` |
| Auth adapters | `items/adapter.py` | Domain restriction + closed local sign-up |
| Matching | `items/matching.py` | "Possible matches" scoring |
| Signals | `items/signals.py` | Auto-create profile; delete orphaned photos |
| Context processor | `items/context_processors.py` | Unread-message count, avatar, upload limit in every template |
| Template tags | `items/templatetags/items_extras.py` | Pagination URLs that keep filters, short "ago" format |
| Admin | `items/admin.py` | Admin configuration (including `Conversation` + read-only `Message` inline) |
| Static | `static/css/style.css`, `static/js/main.js`, `static/js/chat.js` | Design system, theme, toasts, AJAX, photo picker, chat polling |

---

## 🚀 Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows   (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt

copy .env.example .env         # macOS/Linux: cp .env.example .env   — then edit .env

python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo     # optional: sample reports and conversations
python manage.py runserver
```

Open http://127.0.0.1:8000

**Signing in without Google (development):** sign in at http://127.0.0.1:8000/admin/ with your superuser, then open http://127.0.0.1:8000/ — the session is shared.

---

## 🔐 Google OAuth

1. [Google Cloud Console](https://console.cloud.google.com/) → new project → **APIs & Services → Credentials → Create credentials → OAuth client ID → Web application**
2. Authorized redirect URI: `http://127.0.0.1:8000/accounts/google/login/callback/`
3. Give Django the credentials, either:
   - **A. `.env`** (simplest): set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`, or
   - **B. Admin**: leave those two empty; in `/admin/` edit **Sites** (domain `127.0.0.1:8000`) and add a **Social application** (Google) with your ID/secret and that site.
4. **Restrict to your college** — set `DJANGO_ALLOWED_EMAIL_DOMAIN=yourcollege.edu` in `.env`.
   The default `gmail.com` lets any Gmail user in. The check runs on the server and also requires Google to report the email as verified.

---

## 💬 How chat works

- On any open report, another student can click **I found this** / **This is mine** to open a private 1-on-1 `Conversation` with the poster.
- Only the poster and that visitor can view, send, or poll messages in the conversation (everyone else gets 404).
- New messages are fetched automatically every ~4 seconds while the tab is visible (`chat.js`), and opening or polling marks incoming messages as read.
- Sending is rate-limited to 30 messages/minute per user via Django's cache.
- When the poster (or staff) marks the report **Resolved**, existing chats remain readable as read-only history and no new chats or messages can be sent.
- No emails are sent anywhere in the app, and no user's email address is ever shown to another user.

---

## 🧪 Tests

```bash
python manage.py test items -v2
```

Covers: sign-in rules (domain, unverified email, look-alike domains, closed sign-up, landing redirect), dashboard filters and pagination, search, create/edit/delete and ownership, image validation and file clean-up, AJAX resolve (owner + staff + CSRF), private chat (start, send, poll, unread counts, read-only on resolve, 404 for outsiders, no emails sent/exposed), matching rules, My reports, models, profile signal, template filters and `seed_demo`.

---

## 🛡️ Security notes

- Secrets and `DEBUG` come from environment variables; the app refuses to start with `DJANGO_DEBUG=0` and no secret key.
- Every write and chat access is checked on the server for ownership/participation (hiding buttons is not relied on).
- Uploads must be real JPEG/PNG/WebP images (checked with Pillow, not the file name) and under 5 MB.
- All state-changing views are POST + CSRF protected.
- When deploying: set `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_HTTPS=1`, `DJANGO_ALLOWED_EMAIL_DOMAIN`, run `collectstatic`, and serve static/media with your web server (or WhiteNoise).

---

## 📌 Notes

- Database: SQLite. Media: `media/`. Static: `static/`.
- Bootstrap, Bootstrap Icons and Google Fonts are loaded from CDNs, so the browser needs internet access.
- No React, DRF or Tailwind: just Django + Bootstrap + a little vanilla JS.
