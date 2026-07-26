from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import UserProfile


AUTH_INPUT_ATTRS = {'class': 'inp'}


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        **AUTH_INPUT_ATTRS, 'placeholder': 'Enter your username', 'autocomplete': 'username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        **AUTH_INPUT_ATTRS, 'placeholder': 'Enter your password', 'autocomplete': 'current-password'
    }))


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        **AUTH_INPUT_ATTRS, 'placeholder': 'you@example.com'
    }))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={
        **AUTH_INPUT_ATTRS, 'placeholder': 'First name'
    }))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={
        **AUTH_INPUT_ATTRS, 'placeholder': 'Last name'
    }))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            **AUTH_INPUT_ATTRS, 'placeholder': 'Choose a username'
        })
        self.fields['password1'].widget.attrs.update({
            **AUTH_INPUT_ATTRS, 'placeholder': 'Create a password'
        })
        self.fields['password2'].widget.attrs.update({
            **AUTH_INPUT_ATTRS, 'placeholder': 'Confirm your password'
        })
        self.fields['username'].label = ''
        self.fields['password1'].label = ''
        self.fields['password2'].label = ''
        self.fields['password1'].help_text = ''


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)

    class Meta:
        model = UserProfile
        fields = ['phone', 'role']

    def __init__(self, *args, **kwargs):
        user = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if user and hasattr(user, 'user'):
            self.fields['first_name'].initial = user.user.first_name
            self.fields['last_name'].initial = user.user.last_name
            self.fields['email'].initial = user.user.email
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': 'form-input'})


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': 'form-input'})
