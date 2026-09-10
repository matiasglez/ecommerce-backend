from decimal import Decimal
from django.contrib.auth import get_user_model
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