from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import ClientMembership


def calculate_end_date(start_date, membership_type):
    """
    Рассчитывает дату окончания абонемента.
    Формула: дата окончания = дата начала + длительность в днях.
    """
    if not start_date:
        raise ValidationError('Дата начала обязательна.')

    if not membership_type:
        raise ValidationError('Тип абонемента обязателен.')

    if membership_type.duration_days <= 0:
        raise ValidationError('Длительность абонемента должна быть больше 0.')

    return start_date + timedelta(days=membership_type.duration_days)


@transaction.atomic
def create_client_membership(client, membership_type, start_date):
    """
    Создает абонемент клиента на основе выбранного типа абонемента.

    Клиент берется из URL во view.
    end_date и remaining_visits рассчитываются автоматически.
    """
    if not client:
        raise ValidationError('Клиент обязателен.')

    if not membership_type:
        raise ValidationError('Тип абонемента обязателен.')

    if not membership_type.is_active:
        raise ValidationError('Нельзя назначить неактивный тип абонемента.')

    if membership_type.duration_days <= 0:
        raise ValidationError('Длительность абонемента должна быть больше 0.')

    if membership_type.visit_limit <= 0:
        raise ValidationError('Количество посещений в типе абонемента должно быть больше 0.')

    if membership_type.price < 0:
        raise ValidationError('Стоимость абонемента не может быть отрицательной.')

    end_date = calculate_end_date(start_date, membership_type)

    membership = ClientMembership(
        client=client,
        membership_type=membership_type,
        start_date=start_date,
        end_date=end_date,
        remaining_visits=membership_type.visit_limit,
        status=ClientMembership.STATUS_ACTIVE,
    )

    membership.full_clean()
    membership.save()

    return membership


def update_membership_status(membership):
    """
    Обновляет статус абонемента:
    - expired, если срок действия истек;
    - completed, если закончились посещения;
    - frozen/cancelled не трогает, если такая логика задана в модели.
    """
    if not membership:
        raise ValidationError('Абонемент не найден.')

    membership.update_status(save=True)
    membership.refresh_from_db()

    return membership


@transaction.atomic
def freeze_membership(membership):
    """
    Замораживает активный абонемент.
    """
    if not membership:
        raise ValidationError('Абонемент не найден.')

    update_membership_status(membership)

    if membership.status == ClientMembership.STATUS_CANCELLED:
        raise ValidationError('Нельзя заморозить отмененный абонемент.')

    if membership.status == ClientMembership.STATUS_COMPLETED:
        raise ValidationError('Нельзя заморозить завершенный абонемент.')

    if membership.status == ClientMembership.STATUS_EXPIRED:
        raise ValidationError('Нельзя заморозить истекший абонемент.')

    if membership.status == ClientMembership.STATUS_FROZEN:
        raise ValidationError('Абонемент уже заморожен.')

    membership.status = ClientMembership.STATUS_FROZEN
    membership.save(update_fields=['status', 'updated_at'])

    return membership


@transaction.atomic
def activate_membership(membership):
    """
    Активирует замороженный или ранее активный абонемент,
    если срок не истек и есть оставшиеся посещения.
    """
    if not membership:
        raise ValidationError('Абонемент не найден.')

    if membership.status == ClientMembership.STATUS_CANCELLED:
        raise ValidationError('Нельзя активировать отмененный абонемент.')

    if membership.status == ClientMembership.STATUS_COMPLETED:
        raise ValidationError('Нельзя активировать завершенный абонемент.')

    today = timezone.localdate()

    if membership.end_date < today:
        membership.status = ClientMembership.STATUS_EXPIRED
        membership.save(update_fields=['status', 'updated_at'])
        raise ValidationError('Нельзя активировать абонемент с истекшим сроком действия.')

    if membership.remaining_visits <= 0:
        membership.status = ClientMembership.STATUS_COMPLETED
        membership.save(update_fields=['status', 'updated_at'])
        raise ValidationError('Нельзя активировать абонемент без оставшихся посещений.')

    membership.status = ClientMembership.STATUS_ACTIVE
    membership.save(update_fields=['status', 'updated_at'])

    return membership


@transaction.atomic
def cancel_membership(membership):
    """
    Отменяет абонемент без физического удаления.
    """
    if not membership:
        raise ValidationError('Абонемент не найден.')

    if membership.status == ClientMembership.STATUS_CANCELLED:
        raise ValidationError('Абонемент уже отменен.')

    membership.status = ClientMembership.STATUS_CANCELLED
    membership.save(update_fields=['status', 'updated_at'])

    return membership


@transaction.atomic
def complete_membership(membership):
    """
    Завершает абонемент вручную и обнуляет остаток посещений.
    """
    if not membership:
        raise ValidationError('Абонемент не найден.')

    if membership.status == ClientMembership.STATUS_CANCELLED:
        raise ValidationError('Нельзя завершить отмененный абонемент.')

    membership.status = ClientMembership.STATUS_COMPLETED
    membership.remaining_visits = 0
    membership.save(update_fields=['status', 'remaining_visits', 'updated_at'])

    return membership


def get_active_membership_for_client(client):
    """
    Возвращает первый действительный активный абонемент клиента.

    Активным считается абонемент, у которого:
    - status == active;
    - end_date >= today;
    - remaining_visits > 0.
    """
    if not client:
        return None

    memberships = ClientMembership.objects.filter(
        client=client,
        status=ClientMembership.STATUS_ACTIVE,
    ).select_related(
        'client',
        'membership_type',
    ).order_by(
        'end_date',
        '-created_at',
    )

    for membership in memberships:
        membership = update_membership_status(membership)

        if membership.is_valid():
            return membership

    return None