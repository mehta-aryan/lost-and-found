"""
items/forms.py — Django forms.

ItemReportForm  – create / edit a report (validates date, image type + size)
MessageForm     – a single chat message (stripped, 1–1000 chars)
"""
from datetime import date as _date

from django import forms
from django.conf import settings

from .models import ItemReport


class ItemReportForm(forms.ModelForm):
    remove_image = forms.BooleanField(
        required=False, label='Remove current photo',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = ItemReport
        fields = ['report_type', 'category', 'title', 'description', 'image', 'location', 'date']
        labels = {
            'report_type': 'What are you reporting?',
            'title': 'Item name',
            'location': 'Where',
            'date': 'Date',
            'description': 'Description',
        }
        help_texts = {
            'title': '',
            'location': '',
            'date': '',
            'description': 'Colour, brand, marks, what was inside — anything that helps the owner recognise it.',
        }
        widgets = {
            'report_type': forms.RadioSelect(attrs={'class': 'type-input'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Blue Nike backpack', 'maxlength': '200',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Describe the item in detail…',
            }),
            'image': forms.FileInput(attrs={
                'class': 'visually-hidden',
                'accept': 'image/jpeg,image/png,image/webp',
                'data-image-input': '1',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Library, 2nd floor', 'maxlength': '200',
            }),
            'date': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Drop the "---------" placeholder choice: the user must pick Lost or Found.
        self.fields['report_type'].choices = ItemReport.REPORT_TYPE_CHOICES
        self.fields['date'].widget.attrs['max'] = _date.today().isoformat()
        self.fields['image'].widget.attrs['data-max-mb'] = str(getattr(settings, 'MAX_UPLOAD_SIZE_MB', 5))

    def full_clean(self):
        super().full_clean()
        # Mark invalid inputs so Bootstrap draws the red outline.
        for name in self.errors:
            field = self.fields.get(name)
            if field and name != 'report_type':
                css = field.widget.attrs.get('class', '')
                if 'is-invalid' not in css:
                    field.widget.attrs['class'] = (css + ' is-invalid').strip()

    def clean_date(self):
        value = self.cleaned_data.get('date')
        if value and value > _date.today():
            raise forms.ValidationError('Date cannot be in the future.')
        return value

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'content_type'):
            allowed = getattr(settings, 'ALLOWED_IMAGE_TYPES', ['image/jpeg', 'image/png', 'image/webp'])
            max_mb = getattr(settings, 'MAX_UPLOAD_SIZE_MB', 5)
            if image.content_type not in allowed:
                raise forms.ValidationError('Only JPEG, PNG, and WebP images are allowed.')
            if image.size > max_mb * 1024 * 1024:
                raise forms.ValidationError(f'Image must be smaller than {max_mb} MB.')
        return image

    def save(self, commit=True):
        item = super().save(commit=False)
        if self.cleaned_data.get('remove_image') and not self.files.get('image'):
            item.image = None            # old file is deleted by the pre_save signal
        if commit:
            item.save()
        return item


class MessageForm(forms.Form):
    body = forms.CharField(
        max_length=1000,
        min_length=1,
        strip=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Type a message… (Enter to send, Shift+Enter for newline)',
            'maxlength': '1000',
            'id': 'msgBody',
        }),
        error_messages={
            'required': 'Message cannot be empty.',
            'max_length': 'Message must be 1000 characters or fewer.',
            'min_length': 'Message cannot be empty.',
        },
    )

    def clean_body(self):
        return (self.cleaned_data.get('body') or '').strip()
