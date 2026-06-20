from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import UserProfile


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Логин',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите логин',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль',
            'autocomplete': 'current-password',
        })
    )

    error_messages = {
        'invalid_login': (
            'Пожалуйста, введите правильные логин и пароль. '
            'Оба поля чувствительны к регистру.'
        ),
        'inactive': 'Эта учетная запись отключена.',
    }


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['role', 'phone']
        labels = {
            'role': 'Роль',
            'phone': 'Телефон',
        }
        widgets = {
            'role': forms.Select(attrs={
                'class': 'form-select',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите телефон',
            }),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()

        if len(phone) > 20:
            raise forms.ValidationError('Телефон не должен быть длиннее 20 символов.')

        return phone