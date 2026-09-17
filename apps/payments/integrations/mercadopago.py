import mercadopago
from django.conf import settings


class MercadoPagoClient:
    def __init__(self):
        self.sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)

    def create_preference(self, order, payment):
        # Items de la orden
        items = []
        for item in order.order_items.select_related("product").all():
            title = item.product.name if item.product else f"Producto #{item.id}"
            items.append({
                "id": str(item.product.id if item.product else item.id),
                "title": title,
                "quantity": int(item.quantity),
                "unit_price": float(item.price),
                "currency_id": "ARS",
            })

        # Si la orden no tiene items detallados, usamos un item generico con el monto total
        if not items:
            items.append({
                "id": str(order.id),
                "title": f"Orden #{order.id}",
                "quantity": 1,
                "unit_price": float(payment.amount),
                "currency_id": "ARS",
            })

        preference_data = {
            "items": items,
            "payer": {
                "email": order.user.email,
            },
            "back_urls": {
                "success": f"{settings.FRONTEND_URL}/payment/success",
                "failure": f"{settings.FRONTEND_URL}/payment/failure",
                "pending": f"{settings.FRONTEND_URL}/payment/pending",
            },
            "auto_return": "approved",
            "external_reference": str(order.id),
            "notification_url": f"{settings.BACKEND_URL}/api/payments/mercadopago/webhook/",
        }

        preference_response = self.sdk.preference().create(preference_data)
        return preference_response.get("response", {})

    def get_payment_info(self, payment_id):
        # Consulta el pago en la API de Mercado Pago
        payment_response = self.sdk.payment().get(str(payment_id))
        return payment_response.get("response", {})

