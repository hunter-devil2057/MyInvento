from django import forms
from .models import Product, Category, ProductVariant, ProductImage


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'parent': forms.Select(attrs={'class': 'form-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        qs = Category.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('A category with this name already exists.')
        return name


class ProductForm(forms.ModelForm):
    primary_image_file = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-input', 'accept': 'image/*'}),
        label='Product Image',
    )
    cost_price = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2, initial=0)
    sale_price = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2, initial=0)

    class Meta:
        model = Product
        fields = ['sku', 'name', 'description', 'category', 'unit_of_measure',
                  'cost_price', 'sale_price', 'tax_class', 'valuation_method',
                  'image_url', 'track_batches', 'track_serials', 'is_active', 'is_published']
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. PROD-001'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Product name'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Product description...'}),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'unit_of_measure': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. pcs, kg, box'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'inputmode': 'decimal'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'inputmode': 'decimal'}),
            'tax_class': forms.Select(attrs={'class': 'form-input'}, choices=[
                ('Standard', 'Standard'), ('Zero-rated', 'Zero-rated'), ('Exempt', 'Exempt'),
            ]),
            'valuation_method': forms.Select(attrs={'class': 'form-input'}),
            'image_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://example.com/image.jpg'}),
        }


class StockLevelForm(forms.Form):
    warehouse_id = forms.IntegerField(widget=forms.HiddenInput())
    warehouse_name = forms.CharField(widget=forms.HiddenInput())
    quantity = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'min': '0', 'style': 'width:100px;text-align:center'}),
    )


class ProductVariantForm(forms.ModelForm):
    cost_price_override = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2, required=False)
    sale_price_override = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2, required=False)

    class Meta:
        model = ProductVariant
        fields = ['sku', 'attributes', 'barcode', 'cost_price_override', 'sale_price_override', 'is_active']
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-input'}),
            'barcode': forms.TextInput(attrs={'class': 'form-input'}),
            'cost_price_override': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'inputmode': 'decimal'}),
            'sale_price_override': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'inputmode': 'decimal'}),
        }


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'is_primary', 'order']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
            'order': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
        }


ProductImageFormSet = forms.inlineformset_factory(
    Product, ProductImage, form=ProductImageForm,
    extra=0, can_delete=True
)
