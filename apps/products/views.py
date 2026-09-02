from rest_framework import viewsets, permissions
from apps.products.models import Category, Product
from apps.products.serializers import CategorySerializer, ProductSerializer
from django.db.models import Q
from drf_spectacular.utils import extend_schema

@extend_schema(tags=['categories'])
class CategoryViewSet(viewsets.ModelViewSet):
    # Evitamos el problema de consultas lentas (N+1)
    queryset = Category.objects.all().prefetch_related("subcategories")
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Al listar (/api/categories/), solo queremos las raíces.
        # Las subcategorías se anidan solas gracias al SerializerMethodField.
        if self.action == "list":
            return queryset.filter(parent__isnull=True)
        return self.queryset
        
@extend_schema(tags=['products'])        
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().select_related("category") # Optimiza la consulta uniendo tablas
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Permitir filtrar productos por categoria mediante la URL /api/products/?category_id=1
        category_id = self.request.query_params.get("category_id")
        if category_id:
            # Filtra si pertenece a esa categoria o a una subcategoria de la misma
            queryset = queryset.filter(
                Q(category_id=category_id) | Q(category__parent_id=category_id)
            )
        return queryset
        