from django import forms
from .models import Supplier


class SupplierForm(forms.ModelForm):
    lead_time_days = forms.IntegerField(min_value=0, initial=7)

    class Meta:
        model = Supplier
        fields = ['name', 'contact_name', 'email', 'phone', 'address', 'lead_time_days']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'lead_time_days': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
        }
