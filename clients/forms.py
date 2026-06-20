from django import forms
from django.utils import timezone

from .models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            'full_name',
            'birth_date',
            'phone',
            'email',
            'gender',
            'status',
            'registration_date',
            'note',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите ФИО клиента',
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+7...',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'client@example.com',
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select',
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
            }),
            'registration_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Комментарий администратора',
            }),
        }

    def clean_full_name(self):
        full_name = self.cleaned_data.get('full_name', '').strip()

        if not full_name:
            raise forms.ValidationError('ФИО клиента обязательно для заполнения.')

        return full_name

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()

        if not phone:
            raise forms.ValidationError('Телефон клиента обязателен для заполнения.')

        return phone

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')

        if birth_date and birth_date > timezone.localdate():
            raise forms.ValidationError('Дата рождения не может быть позже текущей даты.')

        return birth_date

    def clean_registration_date(self):
        registration_date = self.cleaned_data.get('registration_date')

        if registration_date and registration_date > timezone.localdate():
            raise forms.ValidationError('Дата регистрации не может быть позже текущей даты.')

        return registration_date