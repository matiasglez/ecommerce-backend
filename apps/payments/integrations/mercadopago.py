import hmac
import hashlib
import mercadopago
from django.conf import settings


class MercadoPagoClient:
    def __init__(self):
        self.sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)

    @staticmethod
    def verify_webhook_signature(request, payment_id=None):
        secret = settings.MP_WEBHOOK_SECRET
        if not secret:
            return False

        x_signature = request.headers.get("x-signature") or request.META.get("HTTP_X_SIGNATURE")
        x_request_id = request.headers.get("x-request-id") or request.META.get("HTTP_X_REQUEST_ID")

        if not x_signature or not x_request_id:
            return False

        parts = {}
        for part in x_signature.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                parts[k.strip()] = v.strip()

        ts = parts.get("ts")
        v1 = parts.get("v1")

        if not ts or not v1:
            return False

        data_id = request.query_params.get("data.id") or payment_id or ""
        manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"

        expected_signature = hmac.new(
            secret.encode("utf-8"),
            manifest.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, v1)


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
                "success": f"{settings.FRONTEND_URL}/checkout/success",
                "failure": f"{settings.FRONTEND_URL}/checkout/failure",
                "pending": f"{settings.FRONTEND_URL}/checkout/pending",
            },
            "auto_return": "approved",
            "external_reference": str(order.id),
            "notification_url": f"{settings.BACKEND_URL}/api/payments/mercadopago/webhook/",
        }

        preference_response = self.sdk.preference().create(preference_data)
        
        response_data = preference_response.get("response", {})
        
        if not response_data and isinstance(preference_response, dict):
            response_data = preference_response
        
        return response_data

    def get_payment_info(self, payment_id):
        # Consulta el pago en la API de Mercado Pago
        payment_response = self.sdk.payment().get(str(payment_id))
        return payment_response.get("response", {})

