from decimal import Decimal
from datetime import timedelta          
from unittest.mock import patch, MagicMock

import hashlib
import hmac

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase


from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment, PaymentTransaction
from apps.products.models import Category, Product
from apps.cart.models import Cart, CartItem
from apps.payments.integrations.mercadopago import MercadoPagoClient


User = get_user_model()

class PaymentTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="12345678"
        )
        
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="12345678"
        )
        
        self.category = Category.objects.create(
            name="Bebidas",
        )
        
        self.product = Product.objects.create(
            category=self.category,
            name="Coca Cola",
            description="Gaseosa",
            price=1500.00,
            stock=10,
            is_active=True,
        )
        
        self.order = Order.objects.create(user=self.user, status="PENDING")

        self.client.force_authenticate(
            user=self.user
        )
        

    def test_create_mock_payment(self):
        response = self.client.post("/api/payments/create/", {
            "order_id": self.order.id,
            "payment_method": "MOCK",
        }, format="json",)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
    
    def test_payment_is_created(self):
        self.client.post("/api/payments/create/", {
            "order_id": self.order.id,
            "payment_method": "MOCK",
        }, format="json")
        
        self.assertTrue(Payment.objects.filter(order=self.order).exists())


    def test_payment_transaction_is_created(self):
        self.client.post("/api/payments/create/", {
            "order_id": self.order.id,
            "payment_method": "MOCK",
        }, format="json")
        
        payment = Payment.objects.get(order=self.order)
        
        self.assertTrue(PaymentTransaction.objects.filter(payment=payment).exists())
        
        
    def test_payment_is_marked_as_paid(self):
        self.client.post("/api/payments/create/", {
            "order_id": self.order.id,
            "payment_method": "MOCK",
        }, format="json")
        
        payment = Payment.objects.get(order=self.order)
        
        self.assertEqual(payment.status, Payment.PaymentStatus.PAID)
        
    
    def test_payment_amount_matches_order_total(self):
        Cart.objects.create(user=self.user)
        
        cart = Cart.objects.get(user=self.user)
        
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        
        self.order.delete()
        
        self.order = Order.objects.create(user=self.user, status="PENDING")
        
        # Creamos item manualmente para definir el total
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=Decimal("1500.00"),
        )
        
        response = self.client.post("/api/payments/create/", {
            "order_id": self.order.id,
            "payment_method": "MOCK",
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        payment = Payment.objects.get(order=self.order)
        
        self.assertEqual(payment.amount, Decimal("3000.00"))
        
    
    def test_nonexistent_order_returns_error404(self):
        response = self.client.post("/api/payments/create/", {
            "order_id": 99999,
            "payment_method": "MOCK",
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    
    def test_cannot_pay_another_users_order(self):
        other_order = Order.objects.create(user=self.other_user, status="PENDING")
        
        response = self.client.post("/api/payments/create/", {
            "order_id": other_order.id,
            "payment_method": "MOCK",
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    
    def test_cannot_pay_already_paid_order(self):
        self.order.status = "PAID"
        self.order.save(update_fields=["status"])
        
        response = self.client.post("/api/payments/create/", {
            "order_id": self.order.id,
            "payment_method": "MOCK",
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        
    def test_unsupported_payment_method(self):
        response = self.client.post("/api/payments/create/", {
            "order_id": self.order.id,
            "payment_method": "PayPal",
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        
    def test_user_only_sees_own_payments(self):
        own_payment = Payment.objects.create(
            order=self.order,
            amount="1000.00",
            status=Payment.PaymentStatus.PAID,
            payment_method=Payment.PaymentMethod.MOCK,
        )
        
        other_order = Order.objects.create(user=self.other_user, status="PENDING")
        
        Payment.objects.create(
            order=other_order,
            amount="2000.00",
            status=Payment.PaymentStatus.PENDING,
            payment_method=Payment.PaymentMethod.MOCK,
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
        self.client.post("/api/cart/", {
            "product_id": str(self.product.id),
            "quantity": quantity,
        }, format="json")
        
    
    def test_cannot_pay_expired_order(self):
        self.add_product_to_cart(quantity=2)
        
        self.client.post("/api/orders/checkout/", {}, format="json")
        
        order = Order.objects.filter(user=self.user).latest("id")
        
        order.expires_at = timezone.now() - timedelta(minutes=1)
        order.save(update_fields=["expires_at"])
        
        response = self.client.post("/api/payments/create/", {
            "order_id": order.id,
            "payment_method": "MOCK",
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) 
        
        order.refresh_from_db()
        
        self.assertEqual(order.status, "CANCELLED")
        
    
    def test_expired_order_restores_stock_when_payment_is_attempted(self):
        self.add_product_to_cart(quantity=3)
        
        self.client.post("/api/orders/checkout/", {}, format="json")
        
        self.product.refresh_from_db()
        
        self.assertEqual(self.product.stock, 7)
        
        order = Order.objects.filter(user=self.user).latest("id")
        
        order.expires_at = timezone.now() - timedelta(minutes=1)
        order.save(update_fields=["expires_at"])
        
        response = self.client.post("/api/payments/create/", {
            "order_id": order.id,
            "payment_method": "MOCK",
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        self.product.refresh_from_db()
        
        self.assertEqual(self.product.stock, 10)
        
    
    def test_expired_order_does_not_create_payment(self):
        self.add_product_to_cart(quantity=2)
        
        self.client.post("/api/orders/checkout/", {}, format="json")
        
        order = Order.objects.filter(user=self.user).latest("id")
        
        order.expires_at = timezone.now() - timedelta(minutes=1)
        order.save(update_fields=["expires_at"])
        
        response = self.client.post("/api/payments/create/", {
            "order_id": order.id,
            "payment_method": "MOCK",
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        self.assertFalse(Payment.objects.filter(order=order).exists())

    @patch("apps.payments.integrations.mercadopago.MercadoPagoClient.create_preference")
    def test_create_mercadopago_payment(self, mock_create_preference):
        mock_create_preference.return_value = {
            "init_point": "https://www.mercadopago.com/checkout/v1/redirect?pref_id=test-pref-123"
        }

        response = self.client.post("/api/payments/create/", {
            "order_id": self.order.id,
            "payment_method": "MERCADOPAGO",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["init_point"],
            "https://www.mercadopago.com/checkout/v1/redirect?pref_id=test-pref-123"
        )
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.status, Payment.PaymentStatus.PENDING)
        self.assertEqual(payment.payment_method, Payment.PaymentMethod.MERCADO_PAGO)

    @patch("mercadopago.SDK")
    def test_preference_uses_localhost_back_urls_for_local_demo(self, mock_sdk):
        pref_create = MagicMock(return_value={"response": {"init_point": "https://mp/redirect"}})
        mock_sdk.return_value.preference.return_value.create = pref_create

        payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("1500.00"),
            status=Payment.PaymentStatus.PENDING,
            payment_method=Payment.PaymentMethod.MERCADO_PAGO,
        )

        client = MercadoPagoClient()
        client.create_preference(self.order, payment)

        payload = pref_create.call_args.args[0]
        self.assertEqual(
            payload["back_urls"]["success"],
            "http://localhost:3000/checkout/success",
        )
        self.assertEqual(
            payload["back_urls"]["failure"],
            "http://localhost:3000/checkout/failure",
        )
        self.assertEqual(
            payload["back_urls"]["pending"],
            "http://localhost:3000/checkout/pending",
        )
        self.assertNotIn("auto_return", payload)

    @patch("apps.payments.integrations.mercadopago.MercadoPagoClient.verify_webhook_signature", return_value=True)
    @patch("apps.payments.integrations.mercadopago.MercadoPagoClient.get_payment_info")
    def test_mercadopago_webhook_approved(self, mock_get_payment, mock_verify):
        # Creamos el pago pendiente previo
        payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("1500.00"),
            status=Payment.PaymentStatus.PENDING,
            payment_method=Payment.PaymentMethod.MERCADO_PAGO,
        )

        mock_get_payment.return_value = {
            "status": "approved",
            "external_reference": str(self.order.id),
            "transaction_amount": 1500.00,
        }

        # Desautenticamos para simular peticion externa de Mercado Pago
        self.client.force_authenticate(user=None)

        response = self.client.post("/api/payments/mercadopago/webhook/", {
            "type": "payment",
            "data": {"id": "123456789"},
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(payment.status, Payment.PaymentStatus.PAID)
        self.assertEqual(self.order.status, "PAID")
        self.assertTrue(PaymentTransaction.objects.filter(
            payment=payment,
            transaction_id="123456789",
            status=PaymentTransaction.TransactionStatus.APPROVED,
        ).exists())

    @patch("apps.payments.integrations.mercadopago.MercadoPagoClient.verify_webhook_signature", return_value=True)
    @patch("apps.payments.integrations.mercadopago.MercadoPagoClient.get_payment_info")
    def test_mercadopago_webhook_rejected(self, mock_get_payment, mock_verify):
        payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("1500.00"),
            status=Payment.PaymentStatus.PENDING,
            payment_method=Payment.PaymentMethod.MERCADO_PAGO,
        )

        mock_get_payment.return_value = {
            "status": "rejected",
            "external_reference": str(self.order.id),
            "transaction_amount": 1500.00,
        }

        self.client.force_authenticate(user=None)

        response = self.client.post("/api/payments/mercadopago/webhook/", {
            "type": "payment",
            "data": {"id": "987654321"},
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(payment.status, Payment.PaymentStatus.PENDING)
        self.assertEqual(self.order.status, "PENDING")
        self.assertTrue(PaymentTransaction.objects.filter(
            payment=payment,
            transaction_id="987654321",
            status=PaymentTransaction.TransactionStatus.REJECTED,
        ).exists())

    @patch("apps.payments.integrations.mercadopago.MercadoPagoClient.verify_webhook_signature", return_value=True)
    def test_mercadopago_webhook_invalid_payload(self, mock_verify):
        self.client.force_authenticate(user=None)

        response = self.client.post("/api/payments/mercadopago/webhook/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    @patch("apps.payments.integrations.mercadopago.MercadoPagoClient.verify_webhook_signature")
    def test_mercadopago_webhook_invalid_signature(self, mock_verify):
        mock_verify.return_value = False
        self.client.force_authenticate(user=None)

        response = self.client.post("/api/payments/mercadopago/webhook/", {
            "type": "payment",
            "data": {"id": "123456789"},
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    @staticmethod
    def _build_signature(secret, data_id, request_id, ts):
        manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
        return hmac.new(
            secret.encode("utf-8"),
            manifest.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()


    @override_settings(MP_WEBHOOK_SECRET="test-webhook-secret")
    @patch("apps.payments.integrations.mercadopago.MercadoPagoClient.get_payment_info")
    def test_mercadopago_webhook_with_valid_signature(self, mock_get_payment):
        mock_get_payment.return_value = {}

        self.client.force_authenticate(user=None)

        data_id = "123456789"
        request_id = "req-12345"
        ts = "1706907200"
        v1 = self._build_signature("test-webhook-secret", data_id, request_id, ts)

        response = self.client.post(
            f"/api/payments/mercadopago/webhook/?type=payment&data.id={data_id}",
            {"type": "payment", "data": {"id": data_id}},
            format="json",
            HTTP_X_SIGNATURE=f"ts={ts},v1={v1}",
            HTTP_X_REQUEST_ID=request_id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


    @override_settings(MP_WEBHOOK_SECRET="test-webhook-secret")
    def test_mercadopago_webhook_with_invalid_signature(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            "/api/payments/mercadopago/webhook/?type=payment&data.id=123456789",
            {"type": "payment", "data": {"id": "123456789"}},
            format="json",
            HTTP_X_SIGNATURE="ts=1706907200,v1=invalid-signature-value",
            HTTP_X_REQUEST_ID="req-12345",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    @override_settings(MP_WEBHOOK_SECRET="")
    def test_mercadopago_webhook_without_secret_is_rejected(self):
        self.client.force_authenticate(user=None)

        data_id = "123456789"
        request_id = "req-12345"
        ts = "1706907200"
        v1 = self._build_signature("", data_id, request_id, ts)

        response = self.client.post(
            f"/api/payments/mercadopago/webhook/?type=payment&data.id={data_id}",
            {"type": "payment", "data": {"id": data_id}},
            format="json",
            HTTP_X_SIGNATURE=f"ts={ts},v1={v1}",
            HTTP_X_REQUEST_ID=request_id,
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PaymentConfirmTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="confirm@example.com",
            password="12345678"
        )

        self.other_user = User.objects.create_user(
            email="confirm-other@example.com",
            password="12345678"
        )

        self.category = Category.objects.create(name="Accesorios")

        self.product = Product.objects.create(
            category=self.category,
            name="Garrafa de agua",
            description="Agua",
            price=1000.00,
            stock=10,
            is_active=True,
        )

        self.order = Order.objects.create(user=self.user, status="PENDING")
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=Decimal("1000.00"),
        )

        self.payment = Payment.objects.create(
            order=self.order,
            amount=self.order.total_cost,
            status=Payment.PaymentStatus.PENDING,
            payment_method=Payment.PaymentMethod.MERCADO_PAGO,
            init_point="https://www.mercadopago.com.ar/checkout/v1/redirect?pref_id=123",
        )

        self.client.force_authenticate(user=self.user)

    def _approved_info(self):
        return {
            "id": "567890",
            "external_reference": str(self.order.id),
            "status": "approved",
            "transaction_amount": 1000.0,
        }

    @patch("apps.payments.integrations.mercadopago.MercadoPagoClient.get_payment_info")
    def test_confirm_approved_marks_order_paid(self, mock_get_payment):
        mock_get_payment.return_value = self._approved_info()

        response = self.client.post("/api/payments/confirm/", {
            "order_id": self.order.id,
            "payment_id": "567890",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.order.status, "PAID")
        self.assertEqual(self.payment.status, Payment.PaymentStatus.PAID)
        transaction = PaymentTransaction.objects.get(payment=self.payment)
        self.assertEqual(transaction.status, PaymentTransaction.TransactionStatus.APPROVED)

    @patch("apps.payments.integrations.mercadopago.MercadoPagoClient.get_payment_info")
    def test_confirm_creates_payment_when_missing(self, mock_get_payment):
        self.payment.delete()
        mock_get_payment.return_value = {
            "id": "777",
            "external_reference": str(self.order.id),
            "status": "approved",
            "transaction_amount": 1000.0,
        }

        response = self.client.post("/api/payments/confirm/", {
            "order_id": self.order.id,
            "payment_id": "777",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.status, Payment.PaymentStatus.PAID)
        self.assertEqual(payment.payment_method, Payment.PaymentMethod.MERCADO_PAGO)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "PAID")

    @patch("apps.payments.integrations.mercadopago.MercadoPagoClient.get_payment_info")
    def test_confirm_rejects_mismatched_external_reference(self, mock_get_payment):
        info = self._approved_info()
        info["external_reference"] = "99999"
        mock_get_payment.return_value = info

        response = self.client.post("/api/payments/confirm/", {
            "order_id": self.order.id,
            "payment_id": "567890",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "PENDING")

    @patch("apps.payments.integrations.mercadopago.MercadoPagoClient.get_payment_info")
    def test_confirm_rejects_unknown_payment(self, mock_get_payment):
        mock_get_payment.return_value = {}

        response = self.client.post("/api/payments/confirm/", {
            "order_id": self.order.id,
            "payment_id": "does-not-exist",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_order_from_another_user_is_404(self):
        other_order = Order.objects.create(user=self.other_user, status="PENDING")

        response = self.client.post("/api/payments/confirm/", {
            "order_id": other_order.id,
            "payment_id": "567890",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("apps.payments.integrations.mercadopago.MercadoPagoClient.get_payment_info")
    def test_confirm_is_idempotent(self, mock_get_payment):
        mock_get_payment.return_value = self._approved_info()

        first = self.client.post("/api/payments/confirm/", {
            "order_id": self.order.id,
            "payment_id": "567890",
        }, format="json")

        second = self.client.post("/api/payments/confirm/", {
            "order_id": self.order.id,
            "payment_id": "567890",
        }, format="json")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "PAID")

    @patch("apps.payments.integrations.mercadopago.MercadoPagoClient.get_payment_info")
    def test_confirm_pending_keeps_order_pending(self, mock_get_payment):
        info = self._approved_info()
        info["status"] = "pending"
        mock_get_payment.return_value = info

        response = self.client.post("/api/payments/confirm/", {
            "order_id": self.order.id,
            "payment_id": "567890",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.order.status, "PENDING")
        self.assertEqual(self.payment.status, Payment.PaymentStatus.PENDING)

    @patch("apps.payments.integrations.mercadopago.MercadoPagoClient.get_payment_info")
    def test_confirm_requires_authentication(self, mock_get_payment):
        mock_get_payment.return_value = self._approved_info()
        self.client.force_authenticate(user=None)

        response = self.client.post("/api/payments/confirm/", {
            "order_id": self.order.id,
            "payment_id": "567890",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        