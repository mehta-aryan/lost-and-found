"""
items/signals.py

  • create a UserProfile for every new User
  • delete image files from disk when a report is deleted or its photo is replaced
"""
from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import ItemReport, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(pre_save, sender=ItemReport)
def delete_replaced_image(sender, instance, **kwargs):
    """If the photo changed (or was removed), delete the old file."""
    update_fields = kwargs.get('update_fields')
    if not instance.pk or (update_fields is not None and 'image' not in update_fields):
        return
    old = ItemReport.objects.filter(pk=instance.pk).only('image').first()
    if old and old.image:
        new_name = instance.image.name if instance.image else None
        if old.image.name != new_name:
            old.image.delete(save=False)


@receiver(post_delete, sender=ItemReport)
def delete_image_with_report(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)
