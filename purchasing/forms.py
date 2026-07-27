from django import forms
from .models import PurchaseOrder, PurchaseOrderLine, ReorderRule


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'destination_warehouse', 'order_date', 'expected_date', 'notes']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-input'}),
            'destination_warehouse': forms.Select(attrs={'class': 'form-input'}),
            'order_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'expected_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }


class PurchaseOrderLineForm(forms.ModelForm):
    quantity_ordered = forms.IntegerField(min_value=1)
    unit_cost = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2)

    class Meta:
        model = PurchaseOrderLine
        fields = ['product', 'variant', 'quantity_ordered', 'unit_cost', 'batch_number', 'expiry_date']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-input'}),
            'variant': forms.Select(attrs={'class': 'form-input'}),
            'quantity_ordered': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'inputmode': 'decimal'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-input'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }


PurchaseOrderLineFormSet = forms.inlineformset_factory(
    PurchaseOrder, PurchaseOrderLine, form=PurchaseOrderLineForm,
    extra=3, can_delete=True
)


class ReorderRuleForm(forms.ModelForm):
    min_quantity = forms.IntegerField(min_value=0)
    max_quantity = forms.IntegerField(min_value=0)

    class Meta:
        model = ReorderRule
        fields = ['product', 'variant', 'warehouse', 'min_quantity', 'max_quantity', 'default_supplier', 'is_active']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-input'}),
            'variant': forms.Select(attrs={'class': 'form-input'}),
            'warehouse': forms.Select(attrs={'class': 'form-input'}),
            'min_quantity': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'max_quantity': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'default_supplier': forms.Select(attrs={'class': 'form-input'}),
        }
