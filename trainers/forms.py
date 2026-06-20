from django import forms
from django.contrib.auth.models import User

from accounts.models import UserProfile
from clients.models import Client

from .models import Trainer, TrainerClientAssignment


class TrainerForm(forms.ModelForm):
    class Meta:
        model = Trainer
        fields = [
            'user',
            'full_name',
            'phone',
            'email',
            'specialization',
            'experience_years',
            'status',
            'note',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Иванов Иван Иванович',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+7 999 123-45-67',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'trainer@example.com',
            }),
            'specialization': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: силовые тренировки',
            }),
            'experience_years': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
            }),
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        trainer_role = getattr(UserProfile, 'ROLE_TRAINER', 'trainer')

        trainer_users = User.objects.filter(
            profile__role=trainer_role,
            is_active=True,
        ).order_by('username')

        if self.instance and self.instance.pk and self.instance.user:
            trainer_users = trainer_users | User.objects.filter(pk=self.instance.user.pk)

        self.fields['user'].queryset = trainer_users.distinct()
        self.fields['user'].required = False
        self.fields['user'].widget.attrs.update({'class': 'form-select'})
        self.fields['user'].empty_label = 'Не выбран'

    def clean_full_name(self):
        full_name = self.cleaned_data.get('full_name', '').strip()

        if not full_name:
            raise forms.ValidationError('ФИО тренера обязательно для заполнения.')

        return full_name

    def clean_specialization(self):
        specialization = self.cleaned_data.get('specialization', '').strip()

        if not specialization:
            raise forms.ValidationError('Специализация обязательна для заполнения.')

        return specialization

    def clean_experience_years(self):
        experience_years = self.cleaned_data.get('experience_years')

        if experience_years is not None and experience_years < 0:
            raise forms.ValidationError('Стаж работы не может быть отрицательным.')

        return experience_years


class TrainerClientAssignmentForm(forms.ModelForm):
    class Meta:
        model = TrainerClientAssignment
        fields = [
            'client',
            'note',
        ]
        widgets = {
            'client': forms.Select(attrs={
                'class': 'form-select',
            }),
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Комментарий к закреплению, если требуется',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.trainer = kwargs.pop('trainer', None)
        super().__init__(*args, **kwargs)

        clients = Client.objects.all().order_by('full_name')

        if hasattr(Client, 'Status'):
            clients = clients.exclude(status=Client.Status.ARCHIVED)
        else:
            clients = clients.exclude(status='archived')

        if self.trainer:
            assigned_client_ids = TrainerClientAssignment.objects.filter(
                trainer=self.trainer,
            ).values_list('client_id', flat=True)

            clients = clients.exclude(id__in=assigned_client_ids)

        self.fields['client'].queryset = clients
        self.fields['client'].empty_label = 'Выберите клиента'

    def clean_client(self):
        client = self.cleaned_data.get('client')

        if not client:
            raise forms.ValidationError('Выберите клиента.')

        if self.trainer and TrainerClientAssignment.objects.filter(
            trainer=self.trainer,
            client=client,
        ).exists():
            raise forms.ValidationError('Этот клиент уже закреплен за данным тренером.')

        return client