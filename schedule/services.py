from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.permissions import is_admin, is_trainer
from trainers.models import Trainer
from visits.models import Visit
from visits.services import cancel_visit, mark_client_visit

from .models import ClassRegistration, FitnessClass


ACTIVE_REGISTRATION_STATUSES = [
    ClassRegistration.STATUS_REGISTERED,
    ClassRegistration.STATUS_VISITED,
]


def get_trainer_for_user(user):
    if not user or not user.is_authenticated:
        return None

    return Trainer.objects.filter(user=user).first()


def can_user_create_class(user):
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser or is_admin(user):
        return True

    if is_trainer(user) and get_trainer_for_user(user):
        return True

    return False


def can_trainer_access_class(user, fitness_class):
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser or is_admin(user):
        return True

    trainer = get_trainer_for_user(user)

    if not trainer:
        return False

    return fitness_class.trainer_id == trainer.id


def get_active_registrations_count(fitness_class):
    if not fitness_class:
        return 0

    return ClassRegistration.objects.filter(
        fitness_class=fitness_class,
        status__in=ACTIVE_REGISTRATION_STATUSES,
    ).count()


def get_available_places(fitness_class):
    if not fitness_class:
        return 0

    return fitness_class.capacity - get_active_registrations_count(fitness_class)


@transaction.atomic
def register_client_to_class(fitness_class, client):
    if not fitness_class:
        raise ValidationError('Занятие не найдено.')

    if not client:
        raise ValidationError('Клиент обязателен.')

    fitness_class = FitnessClass.objects.select_for_update().get(pk=fitness_class.pk)

    if fitness_class.status == FitnessClass.STATUS_CANCELLED:
        raise ValidationError('Нельзя записать клиента на отмененное занятие.')

    if fitness_class.status == FitnessClass.STATUS_COMPLETED:
        raise ValidationError('Нельзя записать клиента на уже проведенное занятие.')

    existing_registration = ClassRegistration.objects.filter(
        fitness_class=fitness_class,
        client=client,
    ).first()

    if existing_registration:
        if existing_registration.status == ClassRegistration.STATUS_CANCELLED:
            if get_available_places(fitness_class) <= 0:
                raise ValidationError('Невозможно записать клиента: свободных мест нет.')

            existing_registration.status = ClassRegistration.STATUS_REGISTERED
            existing_registration.full_clean()
            existing_registration.save(update_fields=['status', 'updated_at'])

            return existing_registration

        raise ValidationError('Клиент уже записан на это занятие.')

    if get_available_places(fitness_class) <= 0:
        raise ValidationError('Невозможно записать клиента: свободных мест нет.')

    registration = ClassRegistration(
        fitness_class=fitness_class,
        client=client,
        status=ClassRegistration.STATUS_REGISTERED,
    )
    registration.full_clean()
    registration.save()

    return registration


@transaction.atomic
def cancel_registration(registration):
    if not registration:
        raise ValidationError('Запись не найдена.')

    registration = ClassRegistration.objects.select_for_update().select_related(
        'fitness_class',
        'client',
    ).get(pk=registration.pk)

    if registration.status == ClassRegistration.STATUS_CANCELLED:
        raise ValidationError('Запись уже отменена.')

    if registration.status == ClassRegistration.STATUS_VISITED:
        visit = Visit.objects.filter(
            class_registration=registration,
            status=Visit.STATUS_ACTIVE,
        ).first()

        if visit:
            cancel_visit(visit)

        registration.refresh_from_db()

    registration.status = ClassRegistration.STATUS_CANCELLED
    registration.save(update_fields=['status', 'updated_at'])

    return registration


@transaction.atomic
def mark_registration_visited(registration, user):
    """
    Отмечает клиента как посетившего занятие.

    Дополнительно:
    - создает Visit;
    - связывает Visit с FitnessClass и ClassRegistration;
    - списывает 1 посещение с активного абонемента;
    - защищает от повторного списания.
    """
    if not registration:
        raise ValidationError('Запись не найдена.')

    registration = ClassRegistration.objects.select_for_update().select_related(
        'fitness_class',
        'client',
    ).get(pk=registration.pk)

    if registration.status == ClassRegistration.STATUS_CANCELLED:
        raise ValidationError('Нельзя изменить отмененную запись.')

    if registration.status == ClassRegistration.STATUS_MISSED:
        raise ValidationError('Нельзя отметить посещение: клиент уже отмечен как не пришедший.')

    if registration.status == ClassRegistration.STATUS_VISITED:
        raise ValidationError('Клиент уже отмечен как посетивший занятие.')

    fitness_class = registration.fitness_class

    if fitness_class.status == FitnessClass.STATUS_CANCELLED:
        raise ValidationError('Нельзя отметить посещение на отмененном занятии.')

    existing_visit = Visit.objects.filter(
        class_registration=registration,
        status=Visit.STATUS_ACTIVE,
    ).first()

    if existing_visit:
        raise ValidationError('Посещение по этой записи уже существует.')

    mark_client_visit(
        client=registration.client,
        user=user,
        comment=f'Посещение занятия: {fitness_class.title}',
        fitness_class=fitness_class,
        class_registration=registration,
    )

    registration.status = ClassRegistration.STATUS_VISITED
    registration.save(update_fields=['status', 'updated_at'])

    return registration


@transaction.atomic
def mark_registration_missed(registration):
    if not registration:
        raise ValidationError('Запись не найдена.')

    registration = ClassRegistration.objects.select_for_update().select_related(
        'fitness_class',
        'client',
    ).get(pk=registration.pk)

    if registration.status == ClassRegistration.STATUS_CANCELLED:
        raise ValidationError('Нельзя изменить отмененную запись.')

    if registration.status == ClassRegistration.STATUS_VISITED:
        raise ValidationError('Нельзя отметить как не пришел: посещение уже было списано.')

    registration.status = ClassRegistration.STATUS_MISSED
    registration.save(update_fields=['status', 'updated_at'])

    return registration


@transaction.atomic
def cancel_class(fitness_class):
    if not fitness_class:
        raise ValidationError('Занятие не найдено.')

    fitness_class = FitnessClass.objects.select_for_update().get(pk=fitness_class.pk)

    if fitness_class.status == FitnessClass.STATUS_CANCELLED:
        raise ValidationError('Занятие уже отменено.')

    if fitness_class.status == FitnessClass.STATUS_COMPLETED:
        raise ValidationError('Нельзя отменить уже проведенное занятие.')

    fitness_class.status = FitnessClass.STATUS_CANCELLED
    fitness_class.save(update_fields=['status', 'updated_at'])

    return fitness_class


@transaction.atomic
def complete_class(fitness_class, user):
    if not fitness_class:
        raise ValidationError('Занятие не найдено.')

    fitness_class = FitnessClass.objects.select_for_update().get(pk=fitness_class.pk)

    if not can_trainer_access_class(user, fitness_class):
        raise ValidationError('У вас нет доступа к этому занятию.')

    if fitness_class.status == FitnessClass.STATUS_CANCELLED:
        raise ValidationError('Нельзя отметить отмененное занятие проведенным.')

    if fitness_class.status == FitnessClass.STATUS_COMPLETED:
        raise ValidationError('Занятие уже отмечено как проведенное.')

    fitness_class.status = FitnessClass.STATUS_COMPLETED
    fitness_class.save(update_fields=['status', 'updated_at'])

    return fitness_class