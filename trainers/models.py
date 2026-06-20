from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from clients.models import Client


class Trainer(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_DISMISSED = 'dismissed'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Активен'),
        (STATUS_INACTIVE, 'Временно не работает'),
        (STATUS_DISMISSED, 'Уволен'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trainer_profile',
        verbose_name='Пользователь системы',
    )
    full_name = models.CharField(
        max_length=255,
        verbose_name='ФИО',
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Телефон',
    )
    email = models.EmailField(
        blank=True,
        verbose_name='Email',
    )
    specialization = models.CharField(
        max_length=255,
        verbose_name='Специализация',
    )
    experience_years = models.PositiveIntegerField(
        default=0,
        verbose_name='Стаж работы',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        verbose_name='Статус',
    )
    note = models.TextField(
        blank=True,
        verbose_name='Комментарий',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления',
    )

    class Meta:
        verbose_name = 'Тренер'
        verbose_name_plural = 'Тренеры'
        ordering = ['full_name']

    def __str__(self):
        return self.full_name

    def clean(self):
        if not self.full_name:
            raise ValidationError('ФИО тренера обязательно для заполнения.')

        if not self.specialization:
            raise ValidationError('Специализация обязательна для заполнения.')

        if self.experience_years is not None and self.experience_years < 0:
            raise ValidationError('Стаж работы не может быть отрицательным.')


class TrainerClientAssignment(models.Model):
    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.CASCADE,
        related_name='client_assignments',
        verbose_name='Тренер',
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='trainer_assignments',
        verbose_name='Клиент',
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_trainer_client_assignments',
        verbose_name='Кто закрепил',
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата закрепления',
    )
    note = models.TextField(
        blank=True,
        verbose_name='Комментарий',
    )

    class Meta:
        verbose_name = 'Клиент тренера'
        verbose_name_plural = 'Клиенты тренеров'
        unique_together = ('trainer', 'client')
        ordering = ['trainer__full_name', 'client__full_name']

    def __str__(self):
        return f'{self.client.full_name} — {self.trainer.full_name}'

    def clean(self):
        if not self.trainer_id:
            raise ValidationError('Тренер обязателен.')

        if not self.client_id:
            raise ValidationError('Клиент обязателен.')