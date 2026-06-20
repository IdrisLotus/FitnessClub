from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from memberships.models import ClientMembership
from memberships.services import get_active_membership_for_client

from .models import Visit


def get_validation_error_message(error):
    if hasattr(error, 'messages') and error.messages:
        return ' '.join(error.messages)

    if hasattr(error, 'message'):
        return error.message

    return str(error)


@transaction.atomic
def mark_client_visit(client, user, comment='', fitness_class=None, class_registration=None):
    """
    Отмечает посещение клиента.

    Используется:
    - при обычном посещении клиента;
    - при отметке клиента как посетившего занятие.

    Если переданы fitness_class и class_registration,
    посещение будет связано с занятием.
    """
    if not client:
        raise ValidationError('Клиент обязателен.')

    membership = get_active_membership_for_client(client)

    if not membership:
        raise ValidationError('Невозможно отметить посещение: у клиента нет активного абонемента.')

    membership = ClientMembership.objects.select_for_update().get(pk=membership.pk)

    today = timezone.localdate()

    if membership.status == ClientMembership.STATUS_FROZEN:
        raise ValidationError('Невозможно отметить посещение: абонемент заморожен.')

    if membership.status == ClientMembership.STATUS_CANCELLED:
        raise ValidationError('Невозможно отметить посещение: абонемент отменен.')

    if membership.status == ClientMembership.STATUS_EXPIRED or membership.end_date < today:
        membership.status = ClientMembership.STATUS_EXPIRED
        membership.save(update_fields=['status', 'updated_at'])
        raise ValidationError('Невозможно отметить посещение: срок действия абонемента истек.')

    if membership.status == ClientMembership.STATUS_COMPLETED or membership.remaining_visits <= 0:
        membership.status = ClientMembership.STATUS_COMPLETED
        membership.save(update_fields=['status', 'updated_at'])
        raise ValidationError('Невозможно отметить посещение: посещения закончились.')

    if class_registration:
        existing_visit = Visit.objects.filter(
            class_registration=class_registration,
            status=Visit.STATUS_ACTIVE,
        ).first()

        if existing_visit:
            raise ValidationError('Посещение по этой записи на занятие уже было отмечено.')

        if class_registration.client_id != client.id:
            raise ValidationError('Запись на занятие принадлежит другому клиенту.')

        if fitness_class and class_registration.fitness_class_id != fitness_class.id:
            raise ValidationError('Запись клиента не относится к выбранному занятию.')

    visit = Visit(
        client=client,
        membership=membership,
        fitness_class=fitness_class,
        class_registration=class_registration,
        comment=comment,
        created_by=user,
        status=Visit.STATUS_ACTIVE,
    )

    visit.full_clean()
    visit.save()

    membership.remaining_visits -= 1

    if membership.remaining_visits <= 0:
        membership.remaining_visits = 0
        membership.status = ClientMembership.STATUS_COMPLETED

    membership.save(update_fields=['remaining_visits', 'status', 'updated_at'])

    return visit


@transaction.atomic
def cancel_visit(visit):
    """
    Отменяет посещение без физического удаления.

    Если посещение было связано с занятием,
    статус записи на занятие возвращается в registered,
    чтобы не было рассинхронизации.
    """
    if not visit:
        raise ValidationError('Посещение не найдено.')

    visit = Visit.objects.select_for_update().select_related(
        'membership',
        'class_registration',
    ).get(pk=visit.pk)

    if visit.status == Visit.STATUS_CANCELLED:
        raise ValidationError('Посещение уже отменено.')

    visit.status = Visit.STATUS_CANCELLED
    visit.save(update_fields=['status', 'updated_at'])

    membership = visit.membership
    membership.remaining_visits += 1

    if membership.status == ClientMembership.STATUS_COMPLETED:
        membership.status = ClientMembership.STATUS_ACTIVE

    membership.save(update_fields=['remaining_visits', 'status', 'updated_at'])

    if visit.class_registration_id:
        registration = visit.class_registration

        if registration and registration.status == 'visited':
            registration.status = 'registered'
            registration.save(update_fields=['status', 'updated_at'])

    return visit