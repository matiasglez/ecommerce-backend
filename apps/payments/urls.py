from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"", views.PaymentViewSet, basename="payments")

urlpatterns = [
    path("", include(router.urls)),
    path("success/", views.payment_success, name="payment-success"),
    path("failure/", views.payment_failure, name="payment-failure"),
    path("pending/", views.payment_pending, name="payment-pending"),
]
