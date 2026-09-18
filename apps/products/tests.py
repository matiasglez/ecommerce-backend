from django.contrib.auth import get_user_model
from django.db.models.deletion import ProtectedError
from uuid import UUID
from rest_framework import status
from rest_framework.test import APITestCase

from apps.products.models import Category, Product

User = get_user_model()


class ProductTests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            email = "staff@example.com",
            password = "12345678",
            is_staff = True
        )
        
        self.user = User.objects.create_user(
            email="test@example.com",
            password="12345678",
        )
        
        self.category = Category.objects.create(
            name = "Bebidas",
            description = "Bebidas para mayor recuperacion"
        )
        
        self.client.force_authenticate(user=self.staff_user)
        
    def test_anonymous_user_can_list_products(self):
        self.client.force_authenticate(user=None)
        
        response = self.client.get("/api/products/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_anonymous_user_cannot_create_product(self):
        self.client.force_authenticate(user=None)
        
        response = self.client.post("/api/products/", {
            "category": self.category.id,
            "name": "Radar",
            "description": "Energizante",
            "price": 3000.00,
            "stock": 10,
            "is_active": True,
        }, format="json",)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_non_staff_user_cannot_create_product(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post("/api/products/", {
            "category": self.category.id,
            "name": "Radar",
            "description": "Energizante",
            "price": 3000.00,
            "stock": 10,
            "is_active": True,
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)    
    
    def test_create_product(self):
        response = self.client.post("/api/products/", {
            "category": self.category.id,
            "name": "Radar",
            "description": "Energizante",
            "price": 3000.00,
            "stock": 10,
            "is_active": True
        }, format="json",)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Product.objects.filter(name="Radar").exists())
        
    def test_non_staff_user_cannot_delete_product(self):
        product = Product.objects.create(
            category=self.category,
            name="Radar",
            description="Energizante",
            price=3000,
            stock=10,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(f"/api/products/{product.id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_product_uses_uuid(self):
        response = self.client.post("/api/products/", {
            "category": self.category.id,
            "name": "Speed",
            "description": "Energizante",
            "price": 2400.00,
            "stock": 5,
            "is_active": True  
        }, format="json",)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        product = Product.objects.get(name="Speed")
        
        self.assertIsInstance(product.id, UUID)
        
    def test_product_list(self):
        Product.objects.create(
            category=self.category,
            name="Radar",
            description="Energizante",
            price=3000,
            stock=10,
        )
        response = self.client.get("/api/products/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        
    def test_filter_products_by_category(self):
        other_category = Category.objects.create(name="Snacks")
        
        Product.objects.create(
            category=self.category,
            name="Speed",
            description="Energizante",
            price=2400.00,
            stock=5,
        )
        
        Product.objects.create(
            category=other_category,
            name="Papas",
            description="Snack",
            price=1000.00,
            stock=5,
        )
        
        response = self.client.get(f"/api/products/?category_id={self.category.id}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data["count"], 1)
        
        self.assertEqual(response.data["results"][0]["name"], "Speed")
    
    def test_filter_products_by_parent_category(self):
        subcategory = Category.objects.create(
            name="Energizantes",
            parent=self.category
        )
        
        Product.objects.create(
            category=subcategory,
            name="Speed",
            description="Energizante",
            price=2400.00,
            stock=5
        )
        
        response = self.client.get(f"/api/products/?category_id={self.category.id}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data["count"], 1)
        
        self.assertEqual(response.data["results"][0]["name"], "Speed")
    
    
    def test_root_categories_only_in_list(self):
        root = self.category
        
        Category.objects.create(
            name="Bebidas sin alcohol",
            parent=root,
        )
        
        response = self.client.get("/api/products/categories/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data["count"], 1)
        
        self.assertEqual(response.data["results"][0]["name"], "Bebidas")
        
    def test_categories_include_subcategories(self):
        Category.objects.create(
            name="Gaseosas",
            parent=self.category,
        )
        
        response = self.client.get("/api/products/categories/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        root_category = response.data["results"][0]
        
        self.assertEqual(root_category["name"], "Bebidas")
        
        self.assertEqual(len(root_category["subcategories"]), 1)
        
        self.assertEqual(root_category["subcategories"][0]["name"], "Gaseosas")
        
    def test_slug_is_generated_automatically(self):
        response = self.client.post("/api/products/categories/", {
            "name": "Productos de higiene",
            "description": "Higiene"
        }, format="json",)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        category = Category.objects.get(name="Productos de higiene")
        
        self.assertEqual(category.slug, "productos-de-higiene")
        
    def test_category_cannot_be_deleted_if_has_products(self):
        Product.objects.create(
            category=self.category,
            name="Radar",
            description="Energizante",
            price=3000.00,
            stock=10,
        )
        
        with self.assertRaises(ProtectedError):
            self.category.delete()
        
    def test_product_cannot_have_negative_stock(self):
        response = self.client.post("/api/products/", {
                "category": self.category.id,
                "name": "Producto inválido",
                "description": "Stock negativo",
                "price": 1000.00,
                "stock": -1,
                "is_active": True,
            }, format="json",)
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
