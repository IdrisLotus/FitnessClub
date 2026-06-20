from django import forms

from clients.models import Client
from trainers.models import Trainer, TrainerClientAssignment

from .models import ClassRegistration, FitnessClass


class FitnessClassForm(forms.ModelForm):
    class Meta:
        model = FitnessClass
        fields = [
            'title',
            'trainer',
            'class_date',
            'start_time',
            'end_time',
            'capacity',
            'description',
            'status',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'trainer': forms.Select(attrs={'class': 'form-select'}),
            'class_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['trainer'].queryset = Trainer.objects.filter(
            status=Trainer.STATUS_ACTIVE
        ).order_by('full_name')

        # Тренер создает занятие только для себя
        if self.user and not self.user.is_superuser:
            profile = getattr(self.user, 'profile', None)

            if profile and profile.role == 'trainer':
                trainer = Trainer.objects.filter(user=self.user).first()

                if trainer:
                    self.fields['trainer'].queryset = Trainer.objects.filter(pk=trainer.pk)
                    self.fields['trainer'].initial = trainer
                    self.fields['trainer'].disabled = True

    def clean_capacity(self):
        capacity = self.cleaned_data.get('capacity')

        if capacity is None or capacity <= 0:
            raise forms.ValidationError('Вместимость должна быть больше 0.')

        return capacity

    def clean(self):
        cleaned_data = super().clean()

        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError('Время окончания должно быть позже времени начала.')

        return cleaned_data


class ClassRegistrationForm(forms.ModelForm):
    class Meta:
        model = ClassRegistration
        fields = [
            'client',
        ]
        widgets = {
            'client': forms.Select(attrs={
                'class': 'form-select',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.fitness_class = kwargs.pop('fitness_class', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        clients = Client.objects.all().order_by('full_name')

        if hasattr(Client, 'Status'):
            clients = clients.filter(status=Client.Status.ACTIVE)
        else:
            clients = clients.filter(status='active')

        if self.user and not self.user.is_superuser:
            profile = getattr(self.user, 'profile', None)

            if profile and profile.role == 'trainer':
                trainer = Trainer.objects.filter(user=self.user).first()

                if trainer:
                    assigned_client_ids = TrainerClientAssignment.objects.filter(
                        trainer=trainer,
                    ).values_list('client_id', flat=True)

                    clients = clients.filter(id__in=assigned_client_ids)

        if self.fitness_class:
            registered_client_ids = ClassRegistration.objects.filter(
                fitness_class=self.fitness_class,
                status__in=[
                    ClassRegistration.STATUS_REGISTERED,
                    ClassRegistration.STATUS_VISITED,
                ],
            ).values_list('client_id', flat=True)

            clients = clients.exclude(id__in=registered_client_ids)

        self.fields['client'].queryset = clients
        self.fields['client'].empty_label = 'Выберите клиента'

    def clean_client(self):
        client = self.cleaned_data.get('client')

        if not client:
            raise forms.ValidationError('Выберите клиента.')

        return client