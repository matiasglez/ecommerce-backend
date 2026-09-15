from django.db import transaction
from rest_framework.exceptions import ValidationError, NotFound
from apps.orders.models import Order
from apps.orders.services import OrderService
from apps.payments.models import Payment, PaymentTransaction
from apps.payments.integrations.mercadopago import (
    create_payment_preference,
    get_payment_details,
)


class PaymentService:
    @staticmethod
    def process_payment(user, order_id, payment_method):
        try:
            order = Order.objects.get(id=order_id, user=user)
        except Order.DoesNotExist:
            raise NotFound({"error": "Esta orden no existe"})

        # Debe correr fuera del atomic de pago: si falla la validación,
        # no queremos rollback de la cancelación / reposición de stock.
        order = OrderService.check_expiration(order)

        if order.status != "PENDING":
            raise ValidationError(
                {"error": "La orden ya no esta disponible para pagar"}
            )

        if payment_method != Payment.PaymentMethod.MERCADO_PAGO:
            raise ValidationError(
                {
                    "payment_method": (
                        "Solo se admite el metodo de pago MERCADOPAGO"
                    )
                }
            )

        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order.id, user=user)

            if order.status != "PENDING":
                raise ValidationError(
                    {"error": "La orden ya no esta disponible para pagar"}
                )

            payment, created = Payment.objects.get_or_create(
                order=order,
                defaults={
                    "amount": order.total_cost,
                    "status": Payment.PaymentStatus.PENDING,
                    "payment_method": payment_method,
                },
            )

            if not created and payment.status == Payment.PaymentStatus.PAID:
                raise ValidationError({"payment": "Esta orden ya fue pagada"})

        init_point = create_payment_preference(order)
        return payment, init_point

    @staticmethod
    def handle_mercado_pago_webhook(payment_id):
        payment_info = get_payment_details(payment_id)

        if not payment_info:
            return False

        order_id = payment_info.get("external_reference")
        mp_status = payment_info.get("status")

        if not order_id or mp_status != "approved":
            return False

        with transaction.atomic():
            try:
                order = Order.objects.select_for_update().get(id=order_id)
            except Order.DoesNotExist:
                return False

            # Idempotencia: ya cobrada
            if order.status == "PAID":
                return True

            # No revivir CANCELLED (p. ej. expirada con stock ya restaurado)
            if order.status != "PENDING":
                return False

            order.status = "PAID"
            order.save(update_fields=["status"])

            payment, _ = Payment.objects.get_or_create(
                order=order,
                defaults={
                    "amount": order.total_cost,
                    "status": Payment.PaymentStatus.PENDING,
                    "payment_method": Payment.PaymentMethod.MERCADO_PAGO,
                },
            )

            if payment.status != Payment.PaymentStatus.PAID:
                payment.status = Payment.PaymentStatus.PAID
                payment.save(update_fields=["status"])

            PaymentTransaction.objects.get_or_create(
                payment=payment,
                transaction_id=str(payment_id),
                defaults={
                    "amount": payment.amount,
                    "status": PaymentTransaction.TransactionStatus.APPROVED,
                },
            )

            return True
