from decimal import Decimal
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cart.models import Cart, CartItem
from apps.orders.models import Order, OrderItem
from apps.products.models import Category, Product
from apps.orders.services import OrderService

User = get_user_model()

class OrderTests(APITestCase):
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

        self.client.force_authenticate(
            user=self.user
        )
    
    
    def add_product_to_cart(self, quantity=1):
        self.client.post("/api/cart/", {
            "product_id": str(self.product.id),
            "quantity": quantity,
        }, format="json")
        
        
    def test_list_orders(self):
        Order.objects.create(user=self.user, status="PENDING")
        
        response = self.client.get("/api/orders/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data["count"], 1)
        
        
    def test_retrieve_own_order(self):
        order = Order.objects.create(user=self.user, status="PENDING")
        
        response = self.client.get(f"/api/orders/{order.id}/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data["id"], order.id)
        
        
    def test_user_cannot_retrieve_other_users_order(self):
        order = Order.objects.create(user=self.other_user, status="PENDING")
        
        response = self.client.get(f"/api/orders/{order.id}/")
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        
    def test_checkout_creates_order(self):
        self.add_product_to_cart(quantity=2)
        
        response = self.client.post("/api/orders/checkout/", {}, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        order = Order.objects.get(user=self.user)
        
        self.assertEqual(order.status, "PENDING")
        
        self.assertEqual(order.order_items.count(), 1)
        
        
    def test_checkout_creates_order_item(self):
        self.add_product_to_cart(quantity=2)
        
        self.client.post("/api/orders/checkout/", {}, format="json")
        
        order = Order.objects.get(user=self.user)
        
        item = OrderItem.objects.get(order=order)
        
        self.assertEqual(item.product, self.product)
        
        self.assertEqual(item.quantity, 2)
        
        
    def test_checkout_saves_historical_price(self):
        self.add_product_to_cart(quantity=2)
        
        self.client.post("/api/orders/checkout/", {}, format="json")
        
        order = Order.objects.get(user=self.user)
        
        item = OrderItem.objects.get(order=order)       
        
        self.assertEqual(item.price, Decimal("1500.00"))
        
        self.product.price = Decimal("2000.00")
        
        self.product.save(update_fields=["price"])
        
        self.assertEqual(item.price, Decimal("1500.00"))
        
        
    def test_checkout_decreases_stock(self):
        self.add_product_to_cart(quantity=3)
        
        response = self.client.post("/api/orders/checkout/", {}, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)  

        self.product.refresh_from_db()
        
        self.assertEqual(self.product.stock, 7)
        
        
    def test_checkout_clears_cart(self):
        self.add_product_to_cart(quantity=2)
        
        self.client.post("/api/orders/checkout/", {}, format="json")
        
        cart = Cart.objects.get(user=self.user)
        
        self.assertEqual(cart.items.count(), 0)
        
        
    def test_checkout_empty_cart(self):
        response = self.client.post("/api/orders/checkout/", {}, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        self.assertTrue("cart" in response.data)
        
        
    def test_checkout_insufficient_stock(self):
        self.add_product_to_cart(quantity=11)
        
        response = self.client.post("/api/orders/checkout/", {}, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        self.assertFalse(Order.objects.filter(user=self.user).exists())
        
        
    def test_checkout_requires_authentication(self):
        self.client.force_authenticate(user=None)
        
        response = self.client.post("/api/orders/checkout/", {}, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    
    def test_checkout_sets_expiration_time(self): # Comprueba que una orden reciba fecha de exp
        self.add_product_to_cart(quantity=2)
        
        response = self.client.post("/api/orders/checkout/", {}, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        order = Order.objects.get(user=self.user)
        
        self.assertIsNotNone(order.expires_at)
        
        self.assertGreater(order.expires_at, timezone.now())
        
    
    def test_non_expired_order_remains_pending(self): # Orden vigente (todavia no se cancela)
        self.add_product_to_cart(quantity=2)
        
        self.client.post("/api/orders/checkout/", {}, format="json")
        
        order = Order.objects.get(user=self.user)
        
        OrderService.check_expiration(order)
        
        order.refresh_from_db()
        
        self.assertEqual(order.status, "PENDING")
        
    
    def test_expired_order_is_cancelled(self):
        self.add_product_to_cart(quantity=2)
        
        self.client.post("/api/orders/checkout/", {}, format="json")
        
        order = Order.objects.get(user=self.user)
        
        order.expires_at = timezone.now() - timedelta(minutes=1) # now = 15:30, expires_at = 15:29
        order.save(update_fields=["expires_at"])
        
        OrderService.check_expiration(order)
        
        order.refresh_from_db()
        
        self.assertEqual(order.status, "CANCELLED")
    
    
    def test_expired_order_restores_stock(self):
        self.add_product_to_cart(quantity=3)
        
        self.client.post("/api/orders/checkout/", {}, format="json")
        
        self.product.refresh_from_db()
        
        self.assertEqual(self.product.stock, 7)
        
        order = Order.objects.get(user=self.user)
        
        order.expires_at = timezone.now() - timedelta(minutes=1)
        order.save(update_fields=["expires_at"])
        
        OrderService.check_expiration(order)
        
        self.product.refresh_from_db()
        
        self.assertEqual(self.product.stock, 10)
        
    
    def test_expired_order_does_not_restore_stock_twice(self):
        self.add_product_to_cart(quantity=3)
        
        self.client.post("/api/orders/checkout/", {}, format="json")
        
        order = Order.objects.get(user=self.user)
        
        order.expires_at = timezone.now() - timedelta(minutes=1)
        order.save(update_fields=["expires_at"])
        
        OrderService.check_expiration(order)
        
        self.product.refresh_from_db()
        
        self.assertEqual(self.product.stock, 10)
        
        OrderService.check_expiration(order)
        
        self.product.refresh_from_db()
        
        self.assertEqual(self.product.stock, 10)        
        
        
        