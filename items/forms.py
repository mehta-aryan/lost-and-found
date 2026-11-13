"""
items/forms.py — Django ModelForms for item submission.

ModelForm auto-generates form fields from the ItemReport model
and handles validation.  Bootstrap classes are added via widget attrs.
Custom clean methods enforce:
  • date cannot be in the future
  • uploaded image must be JPEG / PNG / WebP and ≤ MAX_UPLOAD_SIZE_MB
"""
from datetime import date as _date

from django import forms
from django.conf import settings

from .models import ItemReport


class ItemReportForm(forms.ModelForm):
    """
    Form for creating / editing an ItemReport.
    The 'report_type' is usually pre-selected via the quick-add modal,
    but the user can still change it in the form.
    """

    class Meta:
        model = ItemReport
        fields = ['report_type', 'title', 'description', 'image', 'location', 'date']
        widgets = {
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Blue backpack',
                'maxlength': '200',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the item in detail…',
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/png,image/webp',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Library 2nd floor',
                'maxlength': '200',
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
        }

    # ── Custom field-level validation ──────────────────────

    def clean_date(self):
        """Reject dates that lie in the future."""
        value = self.cleaned_data.get('date')
        if value and value > _date.today():
            raise forms.ValidationError('Date cannot be in the future.')
        return value

    def clean_image(self):
        """Enforce file-type whitelist and maximum size."""
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'content_type'):
            allowed = getattr(settings, 'ALLOWED_IMAGE_TYPES',
                              ['image/jpeg', 'image/png', 'image/webp'])
            max_mb = getattr(settings, 'MAX_UPLOAD_SIZE_MB', 5)

            if image.content_type not in allowed:
                raise forms.ValidationError(
                    'Only JPEG, PNG, and WebP images are allowed.'
                )
            if image.size > max_mb * 1024 * 1024:
                raise forms.ValidationError(
                    f'Image must be smaller than {max_mb} MB.'
                )
        return image
