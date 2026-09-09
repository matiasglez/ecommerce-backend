from django.urls import path
from apps.cart.views import CartViewSet

urlpatterns = [
    path("",
        CartViewSet.as_view({
            "get": "list",
            "post": "add_item"}),
        name="cart"),
    path(
    "cart/item/<uuid:pk>/",
    CartViewSet.as_view({"delete": "delete_item"}),
    name="cart-delete",
)
]