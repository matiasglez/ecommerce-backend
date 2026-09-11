from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.orders.models import Order 
from apps.orders.serializers import OrderSerializer
from apps.orders.services import OrderService
from apps.orders.schemas import order_schema_view

@order_schema_view
@extend_schema(tags=["orders"])
class OrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
    ):
    
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
    
    @action(
        detail=False,
        methods=["post"],
        url_path="checkout",
    )
    def checkout(self, request):
        order = OrderService.checkout(user=request.user)
        
        serializer = self.get_serializer(order)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)