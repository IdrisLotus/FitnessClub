from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from clients.models import Client
from memberships.models import ClientMembership


class Visit(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Активно'),
        (STATUS_CANCELLED, 'Отменено'),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='visits',
        verbose_name='Клиент',
    )
    membership = models.ForeignKey(
        ClientMembership,
        on_delete=models.PROTECT,
        related_name='visits',
        verbose_name='Абонемент',
    )
    fitness_class = models.ForeignKey(
        'schedule.FitnessClass',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='visits',
        verbose_name='Занятие',
    )
    class_registration = models.OneToOneField(
        'schedule.ClassRegistration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='visit',
        verbose_name='Запись на занятие',
    )
    visit_datetime = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата и время посещения',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        verbose_name='Статус',
    )
    comment = models.TextField(
        blank=True,
        verbose_name='Комментарий',
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_visits',
        verbose_name='Кто отметил',
    )

    class Meta:
        verbose_name = 'Посещение'
        verbose_name_plural = 'Посещения'
        ordering = ['-visit_datetime']

    def __str__(self):
        return f'{self.client.full_name} — {self.visit_datetime:%d.%m.%Y %H:%M}'

    def clean(self):
        errors = {}

        if self.status == self.STATUS_ACTIVE:
            if not self.client_id:
                errors['client'] = 'Нельзя создать активное посещение без клиента.'

            if not self.membership_id:
                errors['membership'] = 'Нельзя создать активное посещение без абонемента.'

        if self.client_id and self.membership_id:
            if self.membership.client_id != self.client_id:
                errors['membership'] = 'Абонемент должен принадлежать выбранному клиенту.'

            if self.membership.status == ClientMembership.STATUS_CANCELLED:
                errors['membership'] = 'Нельзя создать посещение с отмененным абонементом.'

        if errors:
            raise ValidationError(errors)