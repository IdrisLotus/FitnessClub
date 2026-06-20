from django.db import models

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Client(models.Model):
    class Gender(models.TextChoices):
        MALE = 'male', 'Мужской'
        FEMALE = 'female', 'Женский'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Активный'
        INACTIVE = 'inactive', 'Неактивный'
        FROZEN = 'frozen', 'Заморожен'
        ARCHIVED = 'archived', 'В архиве'

    full_name = models.CharField(
        max_length=255,
        verbose_name='ФИО'
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата рождения'
    )
    phone = models.CharField(
        max_length=20,
        verbose_name='Телефон'
    )
    email = models.EmailField(
        blank=True,
        verbose_name='Email'
    )
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        blank=True,
        verbose_name='Пол'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name='Статус'
    )
    registration_date = models.DateField(
        default=timezone.localdate,
        verbose_name='Дата регистрации'
    )
    note = models.TextField(
        blank=True,
        verbose_name='Комментарий'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ['full_name']

    def __str__(self):
        return self.full_name

    def clean(self):
        errors = {}

        if not self.full_name or not self.full_name.strip():
            errors['full_name'] = 'ФИО клиента обязательно для заполнения.'

        if not self.phone or not self.phone.strip():
            errors['phone'] = 'Телефон клиента обязателен для заполнения.'

        if self.birth_date and self.birth_date > timezone.localdate():
            errors['birth_date'] = 'Дата рождения не может быть позже текущей даты.'

        if self.registration_date and self.registration_date > timezone.localdate():
            errors['registration_date'] = 'Дата регистрации не может быть позже текущей даты.'

        if errors:
            raise ValidationError(errors)
