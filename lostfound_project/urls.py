"""
lostfound_project URL Configuration

Root URL dispatcher:
  - /admin/          → Django admin panel
  - /accounts/       → django-allauth (Google login, logout, etc.)
  - /                → items app (dashboard, forms, detail pages)
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),   # allauth handles Google OAuth
    path('', include('items.urls')),               # Our items app
]

# Serve uploaded media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

