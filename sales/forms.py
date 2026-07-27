from django import forms
from .models import (SalesTransaction, SalesTransactionLine, Payment,
                     Return, ReturnLine, Customer, CustomerAddress, SalesChannel)


class SalesTransactionForm(forms.ModelForm):
    class Meta:
        model = SalesTransaction
        fields = ['customer', 'channel', 'warehouse']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-input'}),
            'channel': forms.Select(attrs={'class': 'form-input'}),
            'warehouse': forms.Select(attrs={'class': 'form-input'}),
        }


class SalesTransactionLineForm(forms.ModelForm):
    quantity = forms.IntegerField(min_value=1)
    unit_price = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2)
    discount = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2, initial=0)

    class Meta:
        model = SalesTransactionLine
        fields = ['product', 'variant', 'quantity', 'unit_price', 'discount']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-input'}),
            'variant': forms.Select(attrs={'class': 'form-input'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'inputmode': 'decimal'}),
            'discount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'inputmode': 'decimal'}),
        }


class PaymentForm(forms.ModelForm):
    amount = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2)
    amount_tendered = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2, required=False)

    class Meta:
        model = Payment
        fields = ['method', 'amount', 'amount_tendered']
        widgets = {
            'method': forms.Select(attrs={'class': 'form-input'}),
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'inputmode': 'decimal'}),
            'amount_tendered': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'inputmode': 'decimal'}),
        }


class ReturnForm(forms.ModelForm):
    class Meta:
        model = Return
        fields = ['reason', 'refund_method']
        widgets = {
            'reason': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'refund_method': forms.Select(attrs={'class': 'form-input'}),
        }


class ReturnLineForm(forms.ModelForm):
    quantity_returned = forms.IntegerField(min_value=1)

    class Meta:
        model = ReturnLine
        fields = ['quantity_returned', 'restock', 'condition']
        widgets = {
            'quantity_returned': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
        }


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'email', 'phone', 'default_address', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'default_address': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }


class SalesChannelForm(forms.ModelForm):
    class Meta:
        model = SalesChannel
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Channel name'}),
        }
