from django import forms


class VisitForm(forms.Form):
    comment = forms.CharField(
        required=False,
        label='Комментарий',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Комментарий к посещению, если требуется',
        }),
    )