# 🔍 Campus Lost & Found

A web app where college students report lost items, log found items, and get them back to their owners. Built with Django (MVT), Bootstrap 5 and Google sign-in via django-allauth.

Reports look like **claim tickets** (punched hole, perforated stub). Lost is red, Found is teal, and there is a light and a dark theme.

---

## ✨ Features

- **Google sign-in, college accounts only.** Verified email + domain check; local sign-up is closed so it can't be bypassed
- **Dashboard** with Lost / Found tabs, search (name, place, description), category and status filters, pagination
- **Messages between students.** "I found this" on a lost report, "This is mine" on a found one. The poster gets an email, then accepts or declines. Accepting resolves the report
- **Possible matches** shown on every open report (opposite type, same category, within 14 days, shared words)
- **Report CRUD** with categories, photo upload (drag & drop, preview, type/size checks), and automatic clean-up of old photos
- **AJAX "Mark resolved"** with CSRF protection and a confirm dialog
- **My reports** page: your posts (with unread-message badge) and the messages you sent
- **Light / dark theme**, responsive layout, keyboard-accessible, respects reduced-motion
- **Admin**: filters, inline status edit, bulk "mark resolved"
- **`seed_demo`** command to fill the app with sample data
- **97 automated tests**

---

## 📁 Project structure (MVT mapping for viva)

| Layer | File(s) | Purpose |
|---|---|---|
| **Model** | `items/models.py` | `UserProfile`, `ItemReport` (with categories), `Claim` |
| **View** | `items/views.py` | Dashboard, detail, CRUD, resolve (AJAX), claim + respond |
| **Template** | `templates/base.html`, `items/templates/items/` | Django Template Language; `_item_card`, `_item_form`, `_field`, `_pagination` are reusable partials |
| URLs | `lostfound_project/urls.py`, `items/urls.py` | URL → view mapping |
| Forms | `items/forms.py` | `ItemReportForm` (validation), `ClaimForm` |
| Auth adapters | `items/adapter.py` | Domain restriction + closed local sign-up |
| Matching | `items/matching.py` | "Possible matches" scoring |
| Signals | `items/signals.py` | Auto-create profile; delete orphaned photos |
| Context processor | `items/context_processors.py` | Unread-message count, avatar, upload limit in every template |
| Template tags | `items/templatetags/items_extras.py` | Pagination URLs that keep filters, short "ago" format |
| Admin | `items/admin.py` | Admin configuration |
| Static | `static/css/style.css`, `static/js/main.js` | Design system, theme, toasts, AJAX, photo picker |

---

## 🚀 Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows   (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt

copy .env.example .env         # macOS/Linux: cp .env.example .env   — then edit .env

python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo     # optional: sample reports and messages
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

## ✉️ Email notifications

By default emails are printed in the terminal running `runserver`, which is fine for a demo. For real email set `DJANGO_EMAIL_BACKEND` and the `EMAIL_*` values (see `.env.example`). A mail failure never breaks the page.

---

## 🧪 Tests

```bash
python manage.py test items -v2
```

Covers: sign-in rules (domain, unverified email, look-alike domains, closed sign-up, landing redirect), dashboard filters and pagination, search, create/edit/delete and ownership, image validation and file clean-up, AJAX resolve incl. CSRF, the message → accept/decline flow, matching rules, My reports, models, profile signal, template filters and `seed_demo`.

---

## 🛡️ Security notes

- Secrets and `DEBUG` come from environment variables; the app refuses to start with `DJANGO_DEBUG=0` and no secret key.
- Every write is checked on the server for ownership (hiding buttons is not relied on).
- Uploads must be real JPEG/PNG/WebP images (checked with Pillow, not the file name) and under 5 MB.
- All state-changing views are POST + CSRF protected.
- When deploying: set `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_HTTPS=1`, run `collectstatic`, and serve static/media with your web server (or WhiteNoise).

---

## 📌 Notes

- Database: SQLite. Media: `media/`. Static: `static/`.
- Bootstrap, Bootstrap Icons and Google Fonts are loaded from CDNs, so the browser needs internet access.
- No React, DRF or Tailwind: just Django + Bootstrap + a little vanilla JS.
