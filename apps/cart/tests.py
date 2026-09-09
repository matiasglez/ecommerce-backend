from django.contrib.auth import get_user_model
from rest_framework import status
from django.urls import reverse
from rest_framework.test import APITestCase
from decimal import Decimal
from apps.cart.models import Cart, CartItem
from apps.products.models import Category, Product

User = get_user_model()

class CartTests(APITestCase):
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
            name="Coca cola",
            description="Gaseosa",
            price=1500.00,
            stock=10,
            is_active=True,
        )
        
        self.client.force_authenticate(user=self.user)
        
        
    def test_unauthenticated_user_cannot_access_cart(self):
        self.client.logout()
        response = self.client.get("/api/cart/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        
    def test_get_cart(self):
        response = self.client.get("/api/cart/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data["items"], [])
        
        self.assertEqual(response.data["total"], Decimal("0.00"))
        
        
    def test_add_product_to_cart(self):
        response = self.client.post("/api/cart/", {
            "product_id": str(self.product.id),
            "quantity": 2,
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        cart = Cart.objects.get(user=self.user)
        
        item = CartItem.objects.get(cart=cart, product=self.product)
        
        self.assertEqual(item.quantity, 2)
        
        
    def test_add_same_product_increments_quantity(self):
        self.client.post("/api/cart/", {
            "product_id": str(self.product.id),
            "quantity": 2,
        }, format="json")
        
        response = self.client.post("/api/cart/", {
            "product_id": str(self.product.id),
            "quantity": 3,
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        cart = Cart.objects.get(user=self.user)
        
        item = CartItem.objects.get(cart=cart, product=self.product)
        
        self.assertEqual(item.quantity, 5)
        
        
    def test_cannot_add_negative_or_zero_quantity(self):
        response = self.client.post("/api/cart/", {
            "product_id": str(self.product.id),
            "quantity": -1,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        
    def test_cannot_add_more_than_stock(self):
        response = self.client.post("/api/cart/", {
            "product_id": str(self.product.id),
            "quantity": 11,
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        self.assertFalse(CartItem.objects.exists())
        
        
    def test_cannot_exceed_stock_when_incrementing(self):
        self.client.post("/api/cart/", {
            "product_id": str(self.product.id),
            "quantity": 8,
        }, format="json")
        
        response = self.client.post("/api/cart/", {
            "product_id": str(self.product.id),
            "quantity": 3,
        }, format="json",)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        cart = Cart.objects.get(user=self.user)
        
        item = CartItem.objects.get(cart=cart, product=self.product)
        
        self.assertEqual(item.quantity, 8)
        
        
    def test_same_product_does_not_create_duplicate_items(self):
        self.client.post("/api/cart/", {
            "product_id": str(self.product.id),
            "quantity": 2,
        }, format="json")
        
        self.client.post("/api/cart/", {
            "product_id": str(self.product.id),
            "quantity": 3,
        }, format="json")        
        
        cart = Cart.objects.get(user=self.user)
        
        self.assertEqual(cart.items.filter(product=self.product).count(), 1)
        
        
    def test_delete_product_from_cart(self):
        self.client.post("/api/cart/", {
            "product_id": str(self.product.id),
            "quantity": 2,
        }, format="json")     

        response = self.client.delete(reverse("cart-delete", kwargs={"pk": self.product.id}))
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        self.assertFalse(CartItem.objects.filter(product=self.product).exists())
        
        
    def test_each_user_has_own_cart(self):
        self.client.post("/api/cart/", {
            "product_id": str(self.product.id),
            "quantity": 2,
        }, format="json")    
        
        self.client.force_authenticate(user=self.other_user)
        
        response = self.client.get("/api/cart/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data["items"], [])
        
        
    def test_cart_total_and_item_subtotal(self):
        self.client.post("/api/cart/", {
            "product_id": str(self.product.id),
            "quantity": 2,
        }, format="json")   

        response = self.client.get("/api/cart/")
        
        self.assertEqual(response.data["items"][0]["subtotal"], Decimal("3000.00"))
        
        self.assertEqual(response.data["total"], Decimal("3000.00"))
        