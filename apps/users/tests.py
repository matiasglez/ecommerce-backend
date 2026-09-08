from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

class UserTests(APITestCase):
    def test_register_user(self):
        response = self.client.post("/api/users/auth/register/", {
            "email": "test@example.com",
            "password": "12345678",
        }, format="json",)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="test@example.com").exists())
        
        
    def test_register_duplicate_email(self):
        User.objects.create_user(email="test@example.com", password="12345678")
        
        response = self.client.post("/api/users/auth/register/", {
            "email": "test@example.com",
            "password": "87654321",
        }, format="json",)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        
    def test_password_is_hashed(self):
        password = "12345678"
        
        self.client.post("/api/users/auth/register/", {
            "email": "test@example.com",
            "password": password,
        }, format="json",)
        
        user = User.objects.get(email="test@example.com")
        
        self.assertNotEqual(user.password, password)
        self.assertTrue(user.check_password(password))
        
        
    def test_login_returns_tokens(self):
        User.objects.create_user(email="test@example.com", password="12345678")
        
        response = self.client.post("/api/users/auth/login/", {
            "email": "test@example.com",
            "password": "12345678",
        }, format="json",)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        
    