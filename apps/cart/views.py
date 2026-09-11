from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from apps.cart.serializers import CartSerializer, AddItemSerializer
from apps.cart.services import CartService
from drf_spectacular.utils import extend_schema
from apps.cart.schemas import cart_schema_view


@cart_schema_view
@extend_schema(tags=["cart"])
class CartViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == "add_item":
            return AddItemSerializer
        return CartSerializer
    
    def list(self, request):
        """Get current shopping cart content."""
        cart = CartService.get_or_create_cart(request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=["post"], url_path="items")
    def add_item(self, request):
        """Add a product or increase quantity."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        CartService.add_product_to_cart(
            user=request.user,
            product_id=serializer.validated_data["product_id"],
            quantity=serializer.validated_data["quantity"]
        )
        return Response({"message": "Product added successfully."}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=["delete"], url_path="items")
    def delete_item(self, request, pk=None):
        """Remove a product completely from the cart."""
        CartService.remove_product_from_cart(user=request.user, product_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
