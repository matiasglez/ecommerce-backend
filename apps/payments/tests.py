from decimal import Decimal
from datetime import timedelta          
from django.utils import timezone
from django.contrib.auth import get_user_model
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase


from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment, PaymentTransaction
from apps.products.models import Category, Product
from apps.cart.models import Cart, CartItem


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

        