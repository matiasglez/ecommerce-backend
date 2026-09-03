from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.cart.serializers import CartSerializer, AddItemSerializer
from apps.cart.services import CartService

class CartViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == "add_item":
            return AddItemSerializer
        return CartSerializer
    
    def list(self, request):
        """Ver el contenido actual del carrito"""
        cart = CartService.get_or_create_cart(request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)
    
    def add_item(self, request):
        """Agregar o incrementar unidades de un producto"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        CartService.add_product_to_cart(
            user=request.user,
            product_id=serializer.validated_data["product_id"],
            quantity=serializer.validated_data["quantity"]
        )
        return Response({"message": "Producto agregado con exito."}, status=status.HTTP_200_OK)
    
    def delete_item(self, request, pk=None):
        """Remover por completo un producto del carrito."""
        CartService.remove_product_from_cart(user=request.user, product_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
