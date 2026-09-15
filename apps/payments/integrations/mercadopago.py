import hashlib
import hmac
from typing import Optional

import mercadopago
from django.conf import settings
from rest_framework.exceptions import ValidationError


class MercadoPagoAPIError(ValidationError):
    """Error controlado al hablar con la API de Mercado Pago."""


def get_mp_sdk():
    token = settings.MERCADOPAGO_ACCESS_TOKEN
    if not token or not isinstance(token, str):
        raise MercadoPagoAPIError(
            {"mercadopago": "MERCADOPAGO_ACCESS_TOKEN no está configurado."}
        )
    return mercadopago.SDK(token)


def create_payment_preference(order):
    sdk = get_mp_sdk()

    items_data = []
    for item in order.order_items.select_related("product").all():
        items_data.append(
            {
                "id": str(item.product.id) if item.product else f"item-{item.id}",
                "title": item.product.name if item.product else "Producto descontinuado",
                "quantity": item.quantity,
                "unit_price": float(item.price),
                "currency_id": "ARS",
            }
        )

    preference_data = {
        "items": items_data,
        "payer": {
            "email": order.user.email,
        },
        "external_reference": str(order.id),
        "back_urls": {
            "success": f"{settings.FRONTEND_URL}/checkout/success",
            "failure": f"{settings.FRONTEND_URL}/checkout/failure",
            "pending": f"{settings.FRONTEND_URL}/checkout/pending",
        },
        "auto_return": "approved",
        "notification_url": f"{settings.BACKEND_URL}/api/payments/webhook/",
    }

    preference_response = sdk.preference().create(preference_data)
    http_status = preference_response.get("status")
    body = preference_response.get("response") or {}

    if http_status not in (200, 201):
        raise MercadoPagoAPIError(
            {
                "mercadopago": "No se pudo crear la preferencia de pago.",
                "details": body,
            }
        )

    init_point = body.get("init_point")
    if not init_point:
        raise MercadoPagoAPIError(
            {"mercadopago": "La preferencia no devolvió init_point."}
        )

    return init_point


def get_payment_details(payment_id):
    sdk = get_mp_sdk()
    payment_response = sdk.payment().get(payment_id)

    if payment_response.get("status") == 200:
        return payment_response.get("response")
    return None


def verify_webhook_signature(
    *,
    x_signature: Optional[str],
    x_request_id: Optional[str],
    data_id: Optional[str],
) -> bool:
    """
    Valida la firma HMAC-SHA256 de notificaciones Webhooks de Mercado Pago.
    Manifest: id:<data.id>;request-id:<x-request-id>;ts:<ts>;
    """
    secret = settings.MERCADOPAGO_WEBHOOK_SECRET
    if not secret:
        # En desarrollo local sin secret configurado se permite; en prod se rechaza.
        return bool(settings.DEBUG)

    if not x_signature:
        return False

    parts = {}
    for chunk in x_signature.split(","):
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        parts[key.strip()] = value.strip()

    ts = parts.get("ts")
    v1 = parts.get("v1")
    if not ts or not v1:
        return False

    manifest_parts = []
    if data_id:
        manifest_parts.append(f"id:{str(data_id).lower()}")
    if x_request_id:
        manifest_parts.append(f"request-id:{x_request_id}")
    manifest_parts.append(f"ts:{ts}")
    manifest = ";".join(manifest_parts) + ";"

    expected = hmac.new(
        secret.encode("utf-8"),
        manifest.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, v1)
