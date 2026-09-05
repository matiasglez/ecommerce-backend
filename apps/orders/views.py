from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from apps.orders.models import Order 
from apps.orders.serializers import OrderSerializer


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
    ):
    
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
    
    @extend_schema(
        request=OrderSerializer,
        responses=OrderSerializer,
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)