from rest_framework import serializers
from apps.products.models import Category, Product

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    
    class Meta:
        model = Product
        fields = [
            "id", "category", "category_name", "name",
            "description", "price", "stock", "image",
            "is_active", "created_on"
        ]
        

class CategorySerializer(serializers.ModelSerializer):
    """Serializador principal para listar categorias en forma de arbol"""
    subcategories = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "parent", "subcategories"]
        # Dejamos slug como lectura en la API
        read_only_fields = ["slug"]
        
    def get_subcategories(self, obj):
        # Tomamos subcategorias hijas
        sub_categories = obj.subcategories.all()
        # Llamamos recursivamente el mismo serializador
        return CategorySerializer(sub_categories, many=True).data