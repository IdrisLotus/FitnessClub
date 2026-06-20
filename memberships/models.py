from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from clients.models import Client


class MembershipType(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name='Название',
    )
    duration_days = models.PositiveIntegerField(
        verbose_name='Длительность, дней',
    )
    visit_limit = models.PositiveIntegerField(
        verbose_name='Количество посещений',
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Стоимость',
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен',
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
        verbose_name = 'Тип абонемента'
        verbose_name_plural = 'Типы абонементов'
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        errors = {}

        if not self.name or not self.name.strip():
            errors['name'] = 'Название абонемента обязательно для заполнения.'

        if self.duration_days is not None and self.duration_days <= 0:
            errors['duration_days'] = 'Длительность должна быть больше 0.'

        if self.visit_limit is not None and self.visit_limit <= 0:
            errors['visit_limit'] = 'Количество посещений должно быть больше 0.'

        if self.price is not None and self.price < 0:
            errors['price'] = 'Стоимость не может быть отрицательной.'

        if errors:
            raise ValidationError(errors)


class ClientMembership(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_EXPIRED = 'expired'
    STATUS_COMPLETED = 'completed'
    STATUS_FROZEN = 'frozen'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Активен'),
        (STATUS_EXPIRED, 'Истек'),
        (STATUS_COMPLETED, 'Завершен'),
        (STATUS_FROZEN, 'Заморожен'),
        (STATUS_CANCELLED, 'Отменен'),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='Клиент',
    )
    membership_type = models.ForeignKey(
        MembershipType,
        on_delete=models.PROTECT,
        related_name='client_memberships',
        verbose_name='Тип абонемента',
    )
    start_date = models.DateField(
        verbose_name='Дата начала',
    )
    end_date = models.DateField(
        verbose_name='Дата окончания',
    )
    remaining_visits = models.PositiveIntegerField(
        verbose_name='Остаток посещений',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        verbose_name='Статус',
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
        verbose_name = 'Абонемент клиента'
        verbose_name_plural = 'Абонементы клиентов'
        ordering = ['-start_date', '-created_at']

    def __str__(self):
        return f'{self.client.full_name} — {self.membership_type.name}'

    def clean(self):
        errors = {}

        if not self.client_id:
            errors['client'] = 'Клиент обязателен.'

        if not self.membership_type_id:
            errors['membership_type'] = 'Тип абонемента обязателен.'

        if self.membership_type_id and not self.membership_type.is_active:
            errors['membership_type'] = 'Нельзя назначить неактивный тип абонемента.'

        if not self.start_date:
            errors['start_date'] = 'Дата начала обязательна.'

        if self.start_date and self.end_date and self.end_date < self.start_date:
            errors['end_date'] = 'Дата окончания не может быть раньше даты начала.'

        if self.remaining_visits is not None and self.remaining_visits < 0:
            errors['remaining_visits'] = 'Остаток посещений не может быть отрицательным.'

        if errors:
            raise ValidationError(errors)

    def is_valid(self):
        today = timezone.localdate()

        return (
            self.status == self.STATUS_ACTIVE
            and self.end_date >= today
            and self.remaining_visits > 0
        )

    def update_status(self, save=True):
        if self.status in [self.STATUS_CANCELLED, self.STATUS_FROZEN]:
            return self.status

        today = timezone.localdate()

        if self.remaining_visits == 0:
            self.status = self.STATUS_COMPLETED
        elif self.end_date < today:
            self.status = self.STATUS_EXPIRED
        else:
            self.status = self.STATUS_ACTIVE

        if save:
            self.save(update_fields=['status', 'updated_at'])

        return self.status
