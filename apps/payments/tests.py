from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment, PaymentTransaction
from apps.products.models import Category, Product


User = get_user_model()

MP_METHOD = "MERCADOPAGO"
INIT_POINT = "https://www.mercadopago.com.ar/checkout/v1/redirect?pref_id=test"


class PaymentTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="12345678",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="12345678",
        )
        self.category = Category.objects.create(name="Bebidas")
        self.product = Product.objects.create(
            category=self.category,
            name="Coca Cola",
            description="Gaseosa",
            price=1500.00,
            stock=10,
            is_active=True,
        )
        self.order = Order.objects.create(user=self.user, status="PENDING")
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=Decimal("1500.00"),
        )
        self.client.force_authenticate(user=self.user)

    @patch(
        "apps.payments.services.create_payment_preference",
        return_value=INIT_POINT,
    )
    def test_create_mercadopago_payment(self, _mock_pref):
        response = self.client.post(
            "/api/payments/create/",
            {"order_id": self.order.id, "payment_method": MP_METHOD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["init_point"], INIT_POINT)
        self.assertTrue(Payment.objects.filter(order=self.order).exists())

    @patch(
        "apps.payments.services.create_payment_preference",
        return_value=INIT_POINT,
    )
    def test_payment_stays_pending_until_webhook(self, _mock_pref):
        self.client.post(
            "/api/payments/create/",
            {"order_id": self.order.id, "payment_method": MP_METHOD},
            format="json",
        )
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.status, Payment.PaymentStatus.PENDING)
        self.assertFalse(PaymentTransaction.objects.filter(payment=payment).exists())

    @patch(
        "apps.payments.services.create_payment_preference",
        return_value=INIT_POINT,
    )
    def test_payment_amount_matches_order_total(self, _mock_pref):
        item = self.order.order_items.get()
        item.quantity = 2
        item.save(update_fields=["quantity"])
        response = self.client.post(
            "/api/payments/create/",
            {"order_id": self.order.id, "payment_method": MP_METHOD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.amount, Decimal("3000.00"))

    def test_nonexistent_order_returns_error404(self):
        response = self.client.post(
            "/api/payments/create/",
            {"order_id": 99999, "payment_method": MP_METHOD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_pay_another_users_order(self):
        other_order = Order.objects.create(user=self.other_user, status="PENDING")
        response = self.client.post(
            "/api/payments/create/",
            {"order_id": other_order.id, "payment_method": MP_METHOD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_pay_already_paid_order(self):
        self.order.status = "PAID"
        self.order.save(update_fields=["status"])
        response = self.client.post(
            "/api/payments/create/",
            {"order_id": self.order.id, "payment_method": MP_METHOD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_payment_method(self):
        response = self.client.post(
            "/api/payments/create/",
            {"order_id": self.order.id, "payment_method": "PayPal"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_only_sees_own_payments(self):
        own_payment = Payment.objects.create(
            order=self.order,
            amount="1000.00",
            status=Payment.PaymentStatus.PAID,
            payment_method=Payment.PaymentMethod.MERCADO_PAGO,
        )
        other_order = Order.objects.create(user=self.other_user, status="PENDING")
        Payment.objects.create(
            order=other_order,
            amount="2000.00",
            status=Payment.PaymentStatus.PENDING,
            payment_method=Payment.PaymentMethod.MERCADO_PAGO,
        )
        response = self.client.get("/api/payments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], own_payment.id)

    def test_payment_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/payments/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def add_product_to_cart(self, quantity=1):
        self.client.post(
            "/api/cart/",
            {"product_id": str(self.product.id), "quantity": quantity},
            format="json",
        )

    @patch(
        "apps.payments.services.create_payment_preference",
        return_value=INIT_POINT,
    )
    def test_cannot_pay_expired_order(self, _mock_pref):
        self.order.delete()
        self.add_product_to_cart(quantity=2)
        self.client.post("/api/orders/checkout/", {}, format="json")
        order = Order.objects.filter(user=self.user).latest("id")
        order.expires_at = timezone.now() - timedelta(minutes=1)
        order.save(update_fields=["expires_at"])

        response = self.client.post(
            "/api/payments/create/",
            {"order_id": order.id, "payment_method": MP_METHOD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.status, "CANCELLED")

    @patch(
        "apps.payments.services.create_payment_preference",
        return_value=INIT_POINT,
    )
    def test_expired_order_restores_stock_when_payment_is_attempted(self, _mock_pref):
        self.order.delete()
        self.add_product_to_cart(quantity=3)
        self.client.post("/api/orders/checkout/", {}, format="json")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 7)

        order = Order.objects.filter(user=self.user).latest("id")
        order.expires_at = timezone.now() - timedelta(minutes=1)
        order.save(update_fields=["expires_at"])

        response = self.client.post(
            "/api/payments/create/",
            {"order_id": order.id, "payment_method": MP_METHOD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)

    @patch(
        "apps.payments.services.create_payment_preference",
        return_value=INIT_POINT,
    )
    def test_expired_order_does_not_create_payment(self, _mock_pref):
        self.order.delete()
        self.add_product_to_cart(quantity=2)
        self.client.post("/api/orders/checkout/", {}, format="json")
        order = Order.objects.filter(user=self.user).latest("id")
        order.expires_at = timezone.now() - timedelta(minutes=1)
        order.save(update_fields=["expires_at"])

        response = self.client.post(
            "/api/payments/create/",
            {"order_id": order.id, "payment_method": MP_METHOD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Payment.objects.filter(order=order).exists())


class WebhookTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="webhook@example.com",
            password="12345678",
        )
        self.category = Category.objects.create(name="Snacks")
        self.product = Product.objects.create(
            category=self.category,
            name="Papas",
            description="Snack",
            price=500.00,
            stock=5,
            is_active=True,
        )
        self.order = Order.objects.create(user=self.user, status="PENDING")
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=Decimal("500.00"),
        )

    @patch("apps.payments.views.verify_webhook_signature", return_value=False)
    def test_webhook_rejects_invalid_signature(self, _mock_sig):
        response = self.client.post(
            "/api/payments/webhook/?type=payment&data.id=123",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("apps.payments.views.verify_webhook_signature", return_value=True)
    @patch("apps.payments.services.get_payment_details")
    def test_webhook_ignores_non_approved_payment(self, mock_details, _mock_sig):
        mock_details.return_value = {
            "status": "pending",
            "external_reference": str(self.order.id),
        }
        response = self.client.post(
            "/api/payments/webhook/?type=payment&data.id=999",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "PENDING")

    @patch("apps.payments.views.verify_webhook_signature", return_value=True)
    @patch("apps.payments.services.get_payment_details")
    def test_webhook_marks_pending_order_as_paid(self, mock_details, _mock_sig):
        mock_details.return_value = {
            "status": "approved",
            "external_reference": str(self.order.id),
        }
        response = self.client.post(
            "/api/payments/webhook/?type=payment&data.id=mp-tx-1",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "PAID")
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.status, Payment.PaymentStatus.PAID)
        self.assertTrue(
            PaymentTransaction.objects.filter(
                payment=payment, transaction_id="mp-tx-1"
            ).exists()
        )

    @patch("apps.payments.views.verify_webhook_signature", return_value=True)
    @patch("apps.payments.services.get_payment_details")
    def test_webhook_does_not_revive_cancelled_order(self, mock_details, _mock_sig):
        self.order.status = "CANCELLED"
        self.order.save(update_fields=["status"])
        mock_details.return_value = {
            "status": "approved",
            "external_reference": str(self.order.id),
        }
        response = self.client.post(
            "/api/payments/webhook/?type=payment&data.id=mp-tx-2",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "CANCELLED")

    def test_webhook_signature_helper(self):
        from django.test import override_settings
        import hashlib
        import hmac
        from apps.payments.integrations.mercadopago import verify_webhook_signature

        secret = "test-secret"
        data_id = "123"
        request_id = "abc"
        ts = "1704908010"
        manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
        v1 = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()

        with override_settings(MERCADOPAGO_WEBHOOK_SECRET=secret, DEBUG=False):
            self.assertTrue(
                verify_webhook_signature(
                    x_signature=f"ts={ts},v1={v1}",
                    x_request_id=request_id,
                    data_id=data_id,
                )
            )
            self.assertFalse(
                verify_webhook_signature(
                    x_signature=f"ts={ts},v1=deadbeef",
                    x_request_id=request_id,
                    data_id=data_id,
                )
            )
