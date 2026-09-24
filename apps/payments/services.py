import uuid
from django.db import transaction
from rest_framework.exceptions import ValidationError, NotFound
from apps.orders.models import Order
from apps.orders.services import OrderService
from apps.payments.models import Payment, PaymentTransaction
from apps.payments.integrations.mercadopago import MercadoPagoClient


class PaymentService:
    @staticmethod
    def process_payment(user, order_id, payment_method):
        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(id=order_id, user=user)
                order = OrderService.check_expiration(order)
        except Order.DoesNotExist:
            raise NotFound({"error": "Esta orden no existe"})
        
        if order.status != "PENDING":
            raise ValidationError({"error": "La orden ya no esta disponible para pagar"})
        
        if payment_method not in [Payment.PaymentMethod.MOCK, Payment.PaymentMethod.MERCADO_PAGO]:
            raise ValidationError({"payment_method": "El metodo de pago todavia no esta disponible"})
        
        with transaction.atomic():
            payment, created = Payment.objects.get_or_create(
                order=order,
                defaults={
                    "amount": order.total_cost,
                    "status": Payment.PaymentStatus.PENDING,
                    "payment_method": payment_method,
                },
            )

            # Si existe pero esta pagado no se permite otro pago
            if not created and payment.status == Payment.PaymentStatus.PAID:
                raise ValidationError({"payment": "Esta orden ya fue pagada"})

            # Si cambio de metodo de pago, actualizamos
            if not created and payment.payment_method != payment_method:
                payment.payment_method = payment_method
                payment.save(update_fields=["payment_method", "updated_on"])

            # Metodo MOCK
            if payment_method == Payment.PaymentMethod.MOCK:
                transaction_id = f"MOCK-{uuid.uuid4()}"
                
                payment_transaction = PaymentTransaction.objects.create(
                    payment=payment,
                    transaction_id=transaction_id,
                    amount=payment.amount,
                    status=PaymentTransaction.TransactionStatus.APPROVED,
                )
                
                # Se actualiza payment 
                payment.status = Payment.PaymentStatus.PAID
                payment.save(update_fields=["status", "updated_on"])
                
                # Se actualiza orden
                order.status = "PAID"
                order.save(update_fields=["status"])
                
                return payment, payment_transaction

            # Metodo MERCADO PAGO
            if payment_method == Payment.PaymentMethod.MERCADO_PAGO:
                mp_client = MercadoPagoClient()
                try:
                    preference = mp_client.create_preference(order, payment)
                except Exception as exc:
                    # Propagamos el motivo real al frontend (token inválido, etc.)
                    raise ValidationError({"error": str(exc)})
                
                # Guardamos la url de checkout para la respuesta
                payment.init_point = preference.get("init_point") if preference else None
                payment.save(update_fields=["init_point", "updated_on"])
                return payment, None

    @staticmethod
    def apply_mp_payment_info(payment, order, payment_info, transaction_id=None):
        """Aplica el estado reportado por Mercado Pago a un pago/orden (idempotente)."""
        mp_status = payment_info.get("status")
        amount = payment_info.get("transaction_amount")

        payment_id = (
            transaction_id
            or str(payment_info.get("id", ""))
            or f"mp-unknown-{payment.id}"
        )

        with transaction.atomic():
            payment_transaction, _ = PaymentTransaction.objects.get_or_create(
                transaction_id=payment_id,
                defaults={
                    "payment": payment,
                    "amount": amount or payment.amount,
                    "status": PaymentTransaction.TransactionStatus.PENDING,
                },
            )

            if mp_status == "approved":
                payment_transaction.status = PaymentTransaction.TransactionStatus.APPROVED
                payment_transaction.save(update_fields=["status"])

                payment.status = Payment.PaymentStatus.PAID
                payment.save(update_fields=["status", "updated_on"])

                order.status = "PAID"
                order.save(update_fields=["status"])

            elif mp_status in ["rejected", "cancelled"]:
                payment_transaction.status = PaymentTransaction.TransactionStatus.REJECTED
                payment_transaction.save(update_fields=["status"])

            elif mp_status == "refunded":
                payment_transaction.status = PaymentTransaction.TransactionStatus.REFUNDED
                payment_transaction.save(update_fields=["status"])

            elif mp_status == "pending":
                payment_transaction.status = PaymentTransaction.TransactionStatus.PENDING
                payment_transaction.save(update_fields=["status"])

        return payment_transaction

    @staticmethod
    def handle_webhook(data):
        # Buscamos el ID del pago en el payload o query
        payment_id = None
        if "data" in data and isinstance(data["data"], dict):
            payment_id = data["data"].get("id")
        if not payment_id:
            payment_id = data.get("id")

        if not payment_id:
            return None

        event_type = data.get("type") or data.get("topic")
        if event_type and event_type not in ["payment"]:
            return None

        # Consultamos el estado real del pago en Mercado Pago
        mp_client = MercadoPagoClient()
        payment_info = mp_client.get_payment_info(payment_id)
        if not payment_info:
            return None

        order_id = payment_info.get("external_reference")
        if not order_id:
            return None

        try:
            order = Order.objects.get(id=int(order_id))
            payment = order.payment
        except (Order.DoesNotExist, Payment.DoesNotExist, ValueError):
            return None

        return PaymentService.apply_mp_payment_info(
            payment, order, payment_info, transaction_id=str(payment_id)
        )

    @staticmethod
    def confirm_mercadopago_payment(user, order, payment_id=None):
        """Confirma el pago consultando la API de Mercado Pago.

        Con payment_id usa /payments/{id}; sin el, busca el pago mas reciente
        de la orden por external_reference (para no depender de la
        redireccion de retorno del frontend).
        """
        mp_client = MercadoPagoClient()
        if payment_id:
            payment_info = mp_client.get_payment_info(payment_id)
        else:
            payment_info = mp_client.search_payment_by_external_reference(order.id)

        if payment_info is None:
            raise ValidationError({"error": "No pudimos recuperar el pago de Mercado Pago"})

        if payment_info.get("external_reference") is None:
            raise ValidationError({"error": "No pudimos recuperar el pago de Mercado Pago"})

        if str(payment_info.get("external_reference")) != str(order.id):
            raise ValidationError({"error": "El pago no corresponde a esta orden"})

        if not user.is_authenticated or order.user_id != user.id:
            raise ValidationError({"error": "No puedes confirmar esta orden"})

        payment, _ = Payment.objects.get_or_create(
            order=order,
            defaults={
                "amount": order.total_cost,
                "status": Payment.PaymentStatus.PENDING,
                "payment_method": Payment.PaymentMethod.MERCADO_PAGO,
            },
        )
        if payment.payment_method != Payment.PaymentMethod.MERCADO_PAGO:
            payment.payment_method = Payment.PaymentMethod.MERCADO_PAGO
            payment.save(update_fields=["payment_method", "updated_on"])

        PaymentService.apply_mp_payment_info(payment, order, payment_info, transaction_id=str(payment_info.get("id", "")))
        return payment

        