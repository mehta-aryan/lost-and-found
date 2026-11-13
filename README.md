# 🔍 Campus Lost & Found

A centralized web application for college students to report lost items and log found items. Built with Django (MVT architecture), Bootstrap 5, and Google OAuth via django-allauth.

---

## 📁 Project Structure (MVT Mapping for Viva)

| MVT Layer  | File(s)                      | Purpose                                      |
|------------|------------------------------|----------------------------------------------|
| **Model**  | `items/models.py`            | Database schema (UserProfile, ItemReport)     |
| **View**   | `items/views.py`             | Business logic, request handling              |
| **Template** | `items/templates/`, `templates/base.html` | HTML presentation with Django Template Language |
| URLs       | `lostfound_project/urls.py`, `items/urls.py` | Maps URLs to views                |
| Forms      | `items/forms.py`             | ModelForm for validated user input            |
| Signals    | `items/signals.py`           | Auto-create UserProfile on user creation      |
| Admin      | `items/admin.py`             | Admin panel registration                      |
| Settings   | `lostfound_project/settings.py` | Project configuration                      |

---

## 🚀 Setup Instructions

### 1. Create & Activate Virtual Environment

```bash
cd "l&f"
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Superuser (for admin panel)

```bash
python manage.py createsuperuser
```

### 5. Run the Server

```bash
python manage.py runserver
```

Visit: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🔐 Google OAuth Setup (Step by Step)

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "Campus Lost and Found")
3. In the sidebar, go to **APIs & Services → Credentials**

### Step 2: Create OAuth 2.0 Credentials

1. Click **Create Credentials → OAuth client ID**
2. Choose **Web application**
3. Under **Authorized redirect URIs**, add:
   ```
   http://127.0.0.1:8000/accounts/google/login/callback/
   ```
4. Note down the **Client ID** and **Client Secret**

### Step 3: Configure in Django

**Option A: Edit `settings.py` directly** (simpler for development)

Open `lostfound_project/settings.py` and replace:
```python
'client_id': 'REPLACE_WITH_YOUR_GOOGLE_CLIENT_ID',
'secret': 'REPLACE_WITH_YOUR_GOOGLE_CLIENT_SECRET',
```

**Option B: Add via Django Admin** (recommended for production)

1. Run the server and go to http://127.0.0.1:8000/admin/
2. Under **Sites**, edit the default site:
   - Domain: `127.0.0.1:8000`
   - Name: `Campus Lost & Found`
3. Under **Social applications**, click **Add**:
   - Provider: Google
   - Name: Google
   - Client ID: *(paste your Client ID)*
   - Secret key: *(paste your Client Secret)*
   - Sites: move `127.0.0.1:8000` to the right

### Step 4: Restrict to College Email Domain

In `lostfound_project/settings.py`, change:
```python
ALLOWED_EMAIL_DOMAIN = "gmail.com"  # Change to "yourcollege.edu"
```

---

## 🧪 Running Tests

```bash
python manage.py test items -v2
```

Tests cover:
- Dashboard loads for authenticated users
- Anonymous users are redirected
- Creating lost and found items
- Image upload
- Owner can resolve their own items (AJAX)
- Non-owner cannot resolve others' items
- Search/filter by title and location
- My Reports page shows only own items
- UserProfile auto-creation signal

---

## ✨ Features

- **Google Sign-In** with college email restriction
- **Dashboard** with Lost/Found tabs, search, and item cards
- **Floating quick-add button** on every page
- **Item CRUD**: Create, Read, Update, Delete reports
- **AJAX resolution**: Mark items resolved without page reload
- **My Reports** page for personal items
- **Responsive** Bootstrap 5 design

---

## 📌 Notes

- **Database**: SQLite (default, no setup needed)
- **Media files**: Uploaded images stored in `media/` folder
- **Static files**: Custom CSS/JS in `static/` folder
- No React, DRF, or Tailwind — pure Django + Bootstrap

