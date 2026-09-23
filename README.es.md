# E-commerce API — Django REST Framework

**[English](README.md) | Español**

API REST de un e-commerce desarrollada con **Django REST Framework**. Incluye catálogo de productos con categorías jerárquicas, carrito de compras, órdenes con expiración y restock automático, pagos con Mercado Pago (y un método `MOCK` para desarrollo) y webhook con verificación de firma HMAC-SHA256.

> Proyecto pensado como portfolio de desarrollo backend. Documentación interactiva de la API en Swagger.

## Stack

- Python 3.12 / Django 6.1
- Django REST Framework 3.18
- djangorestframework-simplejwt (autenticación JWT)
- drf-spectacular (OpenAPI / Swagger)
- PostgreSQL 17
- django-cors-headers
- Docker + docker-compose
- SDK oficial de Mercado Pago

## Funcionalidades

- Registro y login con JWT (access + refresh).
- Productos con UUID, precios y stock; categorías con subcategorías recursivas.
- Catálogo público de solo lectura; creación/edición restringida a staff.
- Carrito por usuario con control de stock acumulado.
- Checkout: crea la orden, descuenta stock, vacía el carrito y fija una fecha de expiración (15 min).
- Órdenes vencidas: al intentar pagar se cancelan y el stock se restaura (con transacciones para evitar sobreventa).
- Pagos MOCK (flujo de desarrollo) y Mercado Pago (preference de checkout).
- Webhook de Mercado Pago con verificación de firma HMAC-SHA256 y manejo idempotente de notificaciones.
- Admin personalizado para todas las apps.
- Documentación OpenAPI en `/api/schema/swagger-ui/`.

## Arquitectura

```
config/                  # settings, urls, wsgi/asgi
apps/
  users/                 # modelo custom User + JWT
  products/              # productos y categorías
  cart/                  # carrito de compras
  orders/                # órdenes y expiración
  payments/              # pagos, webhook e integración con Mercado Pago
```

Cada app separa **models / serializers / views / services / schemas (OpenAPI) / tests**, manteniendo la lógica de negocio en la capa de servicios.

## Instalación con Docker

Requisitos: Docker y Docker Compose.

1. Cloná el repositorio.
2. Creá el archivo `.env` a partir de `.env.example`:

   ```bash
   cp .env.example .env
   ```

3. Completá las variables (ver tabla de abajo).
4. Levantá los servicios:

   ```bash
   docker compose up --build
   ```

5. Aplicá las migraciones y creá un superusuario:

   ```bash
   docker compose run --rm web python manage.py migrate
   docker compose run --rm web python manage.py createsuperuser
   ```

La API queda disponible en `http://localhost:8000`, el admin en `/admin/` y Swagger en `/api/schema/swagger-ui/`.

## Variables de entorno

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave secreta de Django. Usá un valor largo y aleatorio en producción. |
| `DEBUG` | `True` para desarrollo, `False` en producción. |
| `ALLOWED_HOSTS` | Hosts permitidos separados por coma. |
| `POSTGRES_DB` | Nombre de la base. Coincide con el servicio `db` (`ecommerce`). |
| `POSTGRES_USER` | Usuario de la base (`postgres` por defecto en el servicio `db`). |
| `POSTGRES_PASSWORD` | Password de la base (debe coincidir con la del servicio `db`). |
| `POSTGRES_HOST` | Host de la base (`db` cuando se usa Docker Compose). |
| `POSTGRES_PORT` | Puerto de la base (`5432`). |
| `MP_ACCESS_TOKEN` | Access token de Mercado Pago (opcional, solo para pagos reales). |
| `MP_WEBHOOK_SECRET` | Secret para verificar la firma del webhook (opcional, ver sección webhook). |
| `FRONTEND_URL` | URL del frontend para los `back_urls` de Mercado Pago. |
| `BACKEND_URL` / `WEBHOOK_URL` | URL pública donde recibir el webhook. |
| `CORS_ALLOWED_ORIGINS` | Orígenes permitidos para CORS separados por coma. |
| `CSRF_TRUSTED_ORIGINS` | Orígenes de confianza para CSRF. |

> El servicio `db` de `docker-compose.yml` define credenciales por defecto (`ecommerce` / `postgres` / `postgres`). Si cambiás las de `.env`, actualizalas también en el servicio `db`.

## Endpoints

### Auth (`/api/users/`)
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/users/auth/register/` | Registra un usuario (email + password). |
| POST | `/api/users/auth/login/` | Obtiene `access` y `refresh`. |
| POST | `/api/users/auth/token/refresh/` | Renueva el access token. |

### Productos (`/api/products/`)
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/products/` | Lista productos (público). Filtro `?category_id=`. |
| POST | `/api/products/` | Crea un producto (staff). |
| GET/PUT/PATCH/DELETE | `/api/products/{uuid}/` | Detalle, edición y borrado (staff para escritura). |
| GET/POST | `/api/products/categories/` | Lista categorías raíz con subcategorías / crea categoría (staff). |

### Carrito (`/api/cart/`)
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/cart/` | Carrito actual del usuario (items + total). |
| POST | `/api/cart/` | Agrega producto o incrementa cantidad (`product_id`, `quantity`). |
| DELETE | `/api/cart/item/{product_id}/` | Elimina completamente un producto del carrito. |

### Órdenes (`/api/orders/`)
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/orders/` | Órdenes del usuario. |
| GET | `/api/orders/{id}/` | Detalle de una orden del usuario. |
| POST | `/api/orders/checkout/` | Crea una orden a partir del carrito (descuenta stock, expira en 15 min). |

### Pagos (`/api/payments/`)
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/payments/` | Pagos del usuario. |
| POST | `/api/payments/create/` | Crea un pago para una orden (`order_id`, `payment_method`: `MOCK` o `MERCADOPAGO`). |
| POST | `/api/payments/mercadopago/webhook/` | Webhook de Mercado Pago (público, con verificación de firma). |

## Autenticación

1. Registrate (`/api/users/auth/register/`).
2. Logueate (`/api/users/auth/login/`) y usá el `access` token como `Authorization: Bearer <token>`.
3. Cuando expire, renovalo con `refresh` en `/api/users/auth/token/refresh/`.

Los endpoints protegidos devuelven `401` sin token. En Swagger hay un botón **Authorize** para pegar el token.

## Flujo de compra

1. El usuario agrega productos al carrito (se valida stock acumulado).
2. `/api/orders/checkout/` crea la orden **PENDING**, descuenta stock (con `select_for_update` para evitar sobreventa) y vacía el carrito.
3. `/api/payments/create/` crea el pago:
   - **MOCK**: aprueba al instante, marca la orden **PAID** y registra la transacción.
   - **MERCADOPAGO**: devuelve un `init_point` para redirigir al checkout de Mercado Pago.
4. El webhook de Mercado Pago notifica el resultado y actualiza pago/orden.

Si la orden vence antes de pagarse, al intentar pagarla se cancela (CANCELLED) y el stock se restaura.

## Mercado Pago

- Configurá `MP_ACCESS_TOKEN` en `.env`.
- Para recibir webhooks en desarrollo, usá una URL pública expuesta con [ngrok](https://ngrok.com) y seteá `WEBHOOK_URL` a esa dirección:

  ```
  WEBHOOK_URL=https://tu-nombre.ngrok-free.app
  ```

- En el panel de Mercado Pago configurá la notificación hacia `https://<host>/api/payments/mercadopago/webhook/` y el **webhook secret** (o el secret de la firma). Con `MP_WEBHOOK_SECRET` seteado, el endpoint exige la firma válida; sin él, el webhook rechaza las peticiones.
- La verificación valida el header `x-signature` (parámetros `ts` y `v1`) usando `x-request-id` y el `data.id` del payload.

## Tests

La suite tiene **67 tests** de API: usuarios, productos, categorías, carrito, órdenes, pagos, webhook y la firma del webhook.

```bash
docker compose run --rm web python manage.py test
```

Para correr una app puntual:

```bash
docker compose run --rm web python manage.py test apps.payments
```

## Decisiones técnicas

- **Usuario con email como username**: modelo `User` custom con `AUTH_USER_MODEL`.
- **UUID en productos**: evita enumerar el catálogo; órdenes/pagos usan PK entera.
- **Precio histórico**: `OrderItem` guarda el precio al momento de la compra; si el producto se borra, el historial sobrevive (`SET_NULL`).
- **Stock y concurrencia**: el checkout bloquea filas de producto con `select_for_update` dentro de una transacción.
- **Expiración de órdenes**: se evalúa al querer pagar; si está vencida, se cancela y restaura stock. Idealmente un job periódico lo complementaría (ver limitaciones).
- **Idempotencia del webhook**: `PaymentTransaction.transaction_id` es único; las notificaciones repetidas no duplican transacciones.
- **Firma del webhook**: HMAC-SHA256 sobre `id;request-id;ts;` con `hmac.compare_digest`.

## Limitaciones

- La expiración de órdenes es **lazy**: solo se resuelve al intentar pagar (no hay tarea en segundo plano).
- Sin rate limiting en login/registro (a mejorar antes de producción).
- El registro no aplica los password validators de Django (a mejorar).
- La integración real con Mercado Pago requiere token válido y una URL pública para el webhook; el flujo `MOCK` sirve para probar todo lo demás offline.
- El setup de Docker usa el dev server de Django (`runserver`); para producción faltaría `gunicorn` y servir `static`/`media` (p. ej. WhiteNoise).
- No hay email de verificación ni recuperación de contraseña.
```