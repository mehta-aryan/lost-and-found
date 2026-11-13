"""
items/forms.py — Django ModelForms for item submission.

ModelForm automatically generates form fields from the ItemReport model
and handles validation. Bootstrap classes are added via widget attrs.
"""
from django import forms
from .models import ItemReport


class ItemReportForm(forms.ModelForm):
    """
    Form for creating / editing an ItemReport.
    The 'report_type' is usually pre-selected via the quick-add modal,
    but the user can change it in the form.
    """

    class Meta:
        model = ItemReport
        fields = ['report_type', 'title', 'description', 'image', 'location', 'date']
        widgets = {
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Blue backpack',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the item in detail...',
            }),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Library 2nd floor',
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
        }

