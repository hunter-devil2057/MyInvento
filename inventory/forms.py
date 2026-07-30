from django import forms
from .models import Warehouse, StockTransfer, StockTransferLine, StockCountSession, StockCountLine


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'address', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        qs = Warehouse.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('A warehouse with this name already exists.')
        return name


class StockAdjustForm(forms.Form):
    warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.filter(is_active=True), widget=forms.Select(attrs={'class': 'form-input'}))
    quantity_delta = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-input'}))
    reason_code = forms.ModelChoiceField(queryset=None, widget=forms.Select(attrs={'class': 'form-input'}))
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 2}))
    variant = forms.ModelChoiceField(queryset=None, required=False, widget=forms.Select(attrs={'class': 'form-input'}))


class StockTransferForm(forms.ModelForm):
    class Meta:
        model = StockTransfer
        fields = ['source_warehouse', 'destination_warehouse', 'notes']
        widgets = {
            'source_warehouse': forms.Select(attrs={'class': 'form-input'}),
            'destination_warehouse': forms.Select(attrs={'class': 'form-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }


class StockTransferLineForm(forms.ModelForm):
    quantity = forms.IntegerField(min_value=1)

    class Meta:
        model = StockTransferLine
        fields = ['product', 'variant', 'quantity']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-input'}),
            'variant': forms.Select(attrs={'class': 'form-input'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
        }


StockTransferLineFormSet = forms.inlineformset_factory(
    StockTransfer, StockTransferLine, form=StockTransferLineForm,
    extra=3, can_delete=True
)


class StockCountForm(forms.ModelForm):
    class Meta:
        model = StockCountSession
        fields = ['warehouse']
        widgets = {
            'warehouse': forms.Select(attrs={'class': 'form-input'}),
        }


class StockCountLineForm(forms.ModelForm):
    counted_qty = forms.IntegerField(min_value=0, required=False)

    class Meta:
        model = StockCountLine
        fields = ['counted_qty']
        widgets = {
            'counted_qty': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
        }


StockCountLineFormSet = forms.inlineformset_factory(
    StockCountSession, StockCountLine, form=StockCountLineForm,
    extra=0, can_delete=False
)
