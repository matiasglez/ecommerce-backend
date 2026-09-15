# Ecommerce Backend (Django + DRF)

API REST de e-commerce con carrito, órdenes con reserva de stock, JWT y pagos vía Mercado Pago Checkout Pro.

## Requisitos

- Python 3.12+
- Cuenta de [Mercado Pago Developers](https://www.mercadopago.com.ar/developers) (credenciales de prueba)

## Setup

```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Completá SECRET_KEY, MERCADOPAGO_ACCESS_TOKEN y MERCADOPAGO_WEBHOOK_SECRET
python manage.py migrate
python manage.py runserver
```

Swagger: [http://127.0.0.1:8000/api/schema/swagger-ui/](http://127.0.0.1:8000/api/schema/swagger-ui/)

## Flujo de pago

1. Usuario autentica (`/api/users/`) y agrega items al carrito.
2. `POST /api/orders/checkout/` crea una orden `PENDING` (stock reservado, expira en 15 min).
3. `POST /api/payments/create/` con `{ "order_id": <id>, "payment_method": "MERCADOPAGO" }` crea la preferencia y devuelve `init_point`.
4. El frontend redirige al usuario a `init_point` (Checkout Pro).
5. Mercado Pago notifica `POST /api/payments/webhook/` (firma `x-signature`).
6. Si el pago está `approved` y la orden sigue `PENDING`, se marca Order/Payment como `PAID`.

### Variables de entorno relevantes

| Variable | Uso |
|----------|-----|
| `MERCADOPAGO_ACCESS_TOKEN` | Access token del SDK |
| `MERCADOPAGO_WEBHOOK_SECRET` | Secret de Webhooks (panel MP) |
| `FRONTEND_URL` | Base del front para `back_urls` (ej. `http://localhost:3000`) |
| `WEBHOOK_URL` | URL pública del backend (ngrok) para `notification_url` |
| `ALLOWED_HOSTS` | Hosts permitidos (incluí `.ngrok-free.dev` en local) |

### Webhooks en local

Exponé el backend con ngrok y poné esa URL en `WEBHOOK_URL`. El host debe estar en `ALLOWED_HOSTS`.

## Tests

```bash
python manage.py test apps.payments
```

## Apps

- `users` — registro / JWT
- `products` — catálogo
- `cart` — carrito
- `orders` — checkout + expiración
- `payments` — Mercado Pago + webhook
