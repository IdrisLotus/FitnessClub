from django import forms
from django.utils import timezone

from memberships.models import ClientMembership

from .models import Payment


class PaymentForm(forms.Form):
    membership = forms.ModelChoiceField(
        queryset=ClientMembership.objects.none(),
        required=False,
        label='Абонемент',
        empty_label='Без привязки к абонементу',
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
    )

    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        label='Сумма',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0.01',
            'step': '0.01',
            'placeholder': 'Например: 3500.00',
        }),
    )

    payment_date = forms.DateField(
        initial=timezone.localdate,
        label='Дата оплаты',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        }),
    )

    payment_method = forms.ChoiceField(
        choices=Payment.METHOD_CHOICES,
        label='Способ оплаты',
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
    )

    comment = forms.CharField(
        required=False,
        label='Комментарий',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Комментарий к оплате, если требуется',
        }),
    )

    def __init__(self, *args, **kwargs):
        self.client = kwargs.pop('client', None)
        super().__init__(*args, **kwargs)

        if self.client:
            self.fields['membership'].queryset = (
                ClientMembership.objects
                .filter(client=self.client)
                .select_related('membership_type')
                .order_by('-start_date', '-created_at')
            )
        else:
            self.fields['membership'].queryset = ClientMembership.objects.none()

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')

        if amount is None:
            raise forms.ValidationError('Укажите сумму оплаты.')

        if amount <= 0:
            raise forms.ValidationError('Сумма оплаты должна быть больше 0.')

        return amount

    def clean_membership(self):
        membership = self.cleaned_data.get('membership')

        if membership and self.client and membership.client_id != self.client.id:
            raise forms.ValidationError('Абонемент должен принадлежать выбранному клиенту.')

        return membership