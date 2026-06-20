from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Payment


@transaction.atomic
def create_payment(
    client,
    amount,
    payment_method,
    user,
    membership=None,
    payment_date=None,
    comment='',
):
    if not client:
        raise ValidationError('Клиент обязателен.')

    if amount is None or amount <= 0:
        raise ValidationError('Сумма оплаты должна быть больше 0.')

    if membership and membership.client_id != client.id:
        raise ValidationError('Абонемент должен принадлежать выбранному клиенту.')

    payment = Payment(
        client=client,
        membership=membership,
        amount=amount,
        payment_method=payment_method,
        payment_date=payment_date,
        comment=comment,
        created_by=user if user and user.is_authenticated else None,
        status=Payment.STATUS_PAID,
    )

    payment.full_clean()
    payment.save()

    return payment


@transaction.atomic
def cancel_payment(payment):
    if not payment:
        raise ValidationError('Оплата не найдена.')

    payment = Payment.objects.select_for_update().get(pk=payment.pk)

    if payment.status == Payment.STATUS_CANCELLED:
        raise ValidationError('Оплата уже отменена.')

    payment.status = Payment.STATUS_CANCELLED
    payment.save(update_fields=['status', 'updated_at'])

    return payment