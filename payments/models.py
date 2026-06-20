from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from clients.models import Client
from memberships.models import ClientMembership


class Payment(models.Model):
    METHOD_CASH = 'cash'
    METHOD_CARD = 'card'
    METHOD_TRANSFER = 'transfer'
    METHOD_OTHER = 'other'

    METHOD_CHOICES = [
        (METHOD_CASH, 'Наличные'),
        (METHOD_CARD, 'Банковская карта'),
        (METHOD_TRANSFER, 'Перевод'),
        (METHOD_OTHER, 'Другое'),
    ]

    STATUS_PAID = 'paid'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PAID, 'Проведена'),
        (STATUS_CANCELLED, 'Отменена'),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Клиент',
    )
    membership = models.ForeignKey(
        ClientMembership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name='Абонемент',
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Сумма',
    )
    payment_date = models.DateField(
        default=timezone.localdate,
        verbose_name='Дата оплаты',
    )
    payment_method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        verbose_name='Способ оплаты',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PAID,
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
        related_name='created_payments',
        verbose_name='Кто внес оплату',
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
        verbose_name = 'Оплата'
        verbose_name_plural = 'Оплаты'
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f'{self.client.full_name} — {self.amount}'

    def clean(self):
        errors = {}

        if not self.client_id:
            errors['client'] = 'Клиент обязателен.'

        if self.amount is not None and self.amount <= 0:
            errors['amount'] = 'Сумма оплаты должна быть больше 0.'

        if self.client_id and self.membership_id:
            if self.membership.client_id != self.client_id:
                errors['membership'] = 'Абонемент должен принадлежать выбранному клиенту.'

        if errors:
            raise ValidationError(errors)