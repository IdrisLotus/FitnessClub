from django import forms
from django.utils import timezone

from .models import ClientMembership, MembershipType


class MembershipTypeForm(forms.ModelForm):
    class Meta:
        model = MembershipType
        fields = [
            'name',
            'duration_days',
            'visit_limit',
            'price',
            'description',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Абонемент на 1 месяц',
            }),
            'duration_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
            }),
            'visit_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()

        if not name:
            raise forms.ValidationError('Название абонемента обязательно.')

        return name

    def clean_duration_days(self):
        duration_days = self.cleaned_data.get('duration_days')

        if duration_days is not None and duration_days <= 0:
            raise forms.ValidationError('Длительность должна быть больше 0.')

        return duration_days

    def clean_visit_limit(self):
        visit_limit = self.cleaned_data.get('visit_limit')

        if visit_limit is not None and visit_limit <= 0:
            raise forms.ValidationError('Количество посещений должно быть больше 0.')

        return visit_limit

    def clean_price(self):
        price = self.cleaned_data.get('price')

        if price is not None and price < 0:
            raise forms.ValidationError('Стоимость не может быть отрицательной.')

        return price


class ClientMembershipForm(forms.ModelForm):
    class Meta:
        model = ClientMembership
        fields = [
            'membership_type',
            'start_date',
        ]
        widgets = {
            'membership_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['membership_type'].queryset = MembershipType.objects.filter(
            is_active=True
        ).order_by('name')

    def clean_membership_type(self):
        membership_type = self.cleaned_data.get('membership_type')

        if membership_type and not membership_type.is_active:
            raise forms.ValidationError('Нельзя назначить неактивный тип абонемента.')

        return membership_type