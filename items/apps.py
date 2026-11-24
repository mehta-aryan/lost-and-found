"""
items/apps.py — App configuration.
Imports signals when the app is ready.
"""
from django.apps import AppConfig


class ItemsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'items'
    verbose_name = 'Lost & Found Items'

    def ready(self):
        # Import signals so the post_save handlers are registered
        import items.signals  # noqa: F401
