from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.payments.views import PaymentViewSet, MercadoPagoWebhookView


router = DefaultRouter()
router.register(r"", PaymentViewSet, basename="payments")

urlpatterns = [
    path("mercadopago/webhook/", MercadoPagoWebhookView.as_view(), name="mp-webhook"),
    path("", include(router.urls)),
]
