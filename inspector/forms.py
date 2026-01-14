from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import UserProfile

# Create your models here.

class StyledLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control bg-light border-0 py-2',
        'placeholder': 'name@example.com'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control bg-light border-0 py-2',
        'placeholder': 'Enter Password'
    }))

class StyledSignupForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control bg-light border-0 py-2',
        'placeholder': 'name@example.com'
    }))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply the same teal-style classes to all fields automatically
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control bg-light border-0 py-2'})

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['allergies', 'restrictions', 'health_goals']
        widgets = {
            'allergies': forms.TextInput(attrs={'class': 'form-control bg-light border-0 py-2', 'placeholder': 'e.g., Peanuts, Dairy, Shellfish'}),
            'restrictions': forms.TextInput(attrs={'class': 'form-control bg-light border-0 py-2', 'placeholder': 'e.g., Gluten-Free, Vegan, Low-FODMAP'}),
            'health_goals': forms.TextInput(attrs={'class': 'form-control bg-light border-0 py-2', 'placeholder': 'e.g., Weight loss, Muscle gain'}),
        }