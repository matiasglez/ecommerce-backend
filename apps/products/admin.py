from django.contrib import admin
from django.utils.html import format_html
from apps.products.models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name", )} # Autocompleta el slug
    search_fields = ["name"]
    list_filter = ["created_on"]
    

@admin.register(Product)    
class ProductAdmin(admin.ModelAdmin):
    # Columnas que se mostraran en la lista de productos
    list_display = ["image", "name", "category", "price", "stock", "is_active", "created_on"]
    # Enlaces para hacer click y editar el producto
    list_display_links = ["image", "name"]
    # Campos para editar directamente desde la lista sin entrar al producto
    list_editable = ["price", "stock", "is_active"]
    # Filtros laterales para segmentar productos rapidamente
    list_filter = ["is_active", "category", "created_on"]
    # Buscador
    search_fields = ["name", "category__name"]
    # Paginacion
    list_per_page = 20
    # Metodo para mostrar una miniatura de la imagen en la lista
    def show_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />', obj.image.url)
        return format_html('<span style="color: #999;">Sin imagen</span>')
    
    show_image.short_description = "Miniature"