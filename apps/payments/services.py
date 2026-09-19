import uuid
from django.db import transaction
from rest_framework.exceptions import ValidationError, NotFound
from apps.orders.models import Order
from apps.orders.services import OrderService
from apps.payments.models import Payment, PaymentTransaction
from apps.payments.integrations.mercadopago import MercadoPagoClient


class PaymentService:
    @staticmethod
    @transaction.atomic
    def process_payment(user, order_id, payment_method):
        try:
            order = Order.objects.select_for_update().get(id=order_id, user=user)
        except Order.DoesNotExist:
            raise NotFound({"error": "Esta orden no existe"})
        
        order = OrderService.check_expiration(order)
        
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
            preference = mp_client.create_preference(order, payment)
            
            # Guardamos la url de checkout para la respuesta
            payment.init_point = preference.get("init_point") if preference else None
            return payment, None

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
        mp_status = payment_info.get("status")
        amount = payment_info.get("transaction_amount")

        if not order_id:
            return None

        try:
            order = Order.objects.get(id=int(order_id))
            payment = order.payment
        except (Order.DoesNotExist, Payment.DoesNotExist, ValueError):
            return None

        with transaction.atomic():
            # Idempotencia: buscamos o creamos la transaccion
            payment_transaction, _ = PaymentTransaction.objects.get_or_create(
                transaction_id=str(payment_id),
                defaults={
                    "payment": payment,
                    "amount": amount or payment.amount,
                    "status": PaymentTransaction.TransactionStatus.PENDING,
                },
            )

            # Actualizamos segun el estado en Mercado Pago
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

        return payment_transaction

        