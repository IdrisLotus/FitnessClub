from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from clients.models import Client
from trainers.models import Trainer


class FitnessClass(models.Model):
    STATUS_PLANNED = 'planned'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PLANNED, 'Запланировано'),
        (STATUS_COMPLETED, 'Проведено'),
        (STATUS_CANCELLED, 'Отменено'),
    ]

    title = models.CharField(
        max_length=255,
        verbose_name='Название занятия',
    )
    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.PROTECT,
        related_name='fitness_classes',
        verbose_name='Тренер',
    )
    class_date = models.DateField(
        verbose_name='Дата занятия',
    )
    start_time = models.TimeField(
        verbose_name='Время начала',
    )
    end_time = models.TimeField(
        verbose_name='Время окончания',
    )
    capacity = models.PositiveIntegerField(
        verbose_name='Вместимость',
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PLANNED,
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
        verbose_name = 'Занятие'
        verbose_name_plural = 'Занятия'
        ordering = ['class_date', 'start_time']

    def __str__(self):
        return f'{self.title} — {self.class_date:%d.%m.%Y} {self.start_time:%H:%M}'

    def clean(self):
        errors = {}

        if not self.title or not self.title.strip():
            errors['title'] = 'Название занятия обязательно для заполнения.'

        if not self.trainer_id:
            errors['trainer'] = 'Тренер обязателен.'

        if not self.class_date:
            errors['class_date'] = 'Дата занятия обязательна.'

        if self.start_time and self.end_time and self.end_time <= self.start_time:
            errors['end_time'] = 'Время окончания должно быть позже времени начала.'

        if self.capacity is not None and self.capacity <= 0:
            errors['capacity'] = 'Вместимость должна быть больше 0.'

        if errors:
            raise ValidationError(errors)


class ClassRegistration(models.Model):
    STATUS_REGISTERED = 'registered'
    STATUS_CANCELLED = 'cancelled'
    STATUS_VISITED = 'visited'
    STATUS_MISSED = 'missed'

    STATUS_CHOICES = [
        (STATUS_REGISTERED, 'Записан'),
        (STATUS_CANCELLED, 'Отменен'),
        (STATUS_VISITED, 'Посетил'),
        (STATUS_MISSED, 'Не пришел'),
    ]

    fitness_class = models.ForeignKey(
        FitnessClass,
        on_delete=models.CASCADE,
        related_name='registrations',
        verbose_name='Занятие',
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='class_registrations',
        verbose_name='Клиент',
    )
    registration_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата записи',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_REGISTERED,
        verbose_name='Статус записи',
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
        verbose_name = 'Запись на занятие'
        verbose_name_plural = 'Записи на занятия'
        ordering = ['-registration_date']
        unique_together = ('fitness_class', 'client')

    def __str__(self):
        return f'{self.client.full_name} — {self.fitness_class.title}'

    def clean(self):
        errors = {}

        if not self.fitness_class_id:
            errors['fitness_class'] = 'Занятие обязательно.'

        if not self.client_id:
            errors['client'] = 'Клиент обязателен.'

        if self.fitness_class_id:
            if self.fitness_class.status == FitnessClass.STATUS_CANCELLED:
                errors['fitness_class'] = 'Нельзя записать клиента на отмененное занятие.'

        if errors:
            raise ValidationError(errors)