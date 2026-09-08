import uuid
from django.db import transaction
from rest_framework.exceptions import ValidationError, PermissionDenied
from apps.orders.models import Order
from apps.payments.models import Payment, PaymentTransaction


class PaymentService:
    @staticmethod
    @transaction.atomic
    def process_payment(user, order_id, payment_method):
        try:
            order = Order.objects.select_for_update().get(id=order_id, user=user)
        except Order.DoesNotExist:
            raise PermissionDenied("No tienes permiso para pagar esta orden")
        
        if order.status != "PENDING":
            raise ValidationError({"error": "Solo puedes pagar una orden que este pendiente"})
        
        if payment_method != Payment.PaymentMethod.MOCK:
            raise ValidationError({"payment_method": "El metodo de pago todavia no esta disponible"})
        
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
        # Se crea transaccion
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
        