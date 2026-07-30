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

    def clean_name(self):
        name = self.cleaned_data['name']
        qs = Supplier.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('A supplier with this name already exists.')
        return name

    def clean_email(self):
        email = self.cleaned_data.get('email', '')
        if email:
            qs = Supplier.objects.filter(email__iexact=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('A supplier with this email already exists.')
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if phone:
            qs = Supplier.objects.filter(phone=phone)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('A supplier with this phone number already exists.')
        return phone
