from django.contrib import admin
from django.utils.html import format_html
from apps.products.models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent", "created_on", "updated_on"]
    list_display_links = ["name"]
    prepopulated_fields = {"slug": ("name", )} # Autocompleta el slug
    search_fields = ["name"]
    list_filter = ["created_on"]
    ordering = ["name"]
    list_per_page = 20
    

@admin.register(Product)    
class ProductAdmin(admin.ModelAdmin):
    # Columnas que se mostraran en la lista de productos
    list_display = ["show_image", "name", "category", "price", "stock", "is_active", "created_on"]
    # Enlaces para hacer click y editar el producto
    list_display_links = ["show_image", "name"]
    # Campos para editar directamente desde la lista sin entrar al producto
    list_editable = ["price", "stock", "is_active"]
    # Filtros laterales para segmentar productos rapidamente
    list_filter = ["is_active", "category", "created_on"]
    # Buscador
    search_fields = ["name", "description", "category__name"]
    # Optimiza las consultas a la base de datos al traer la categoria relacionada
    list_select_related = ["category"]
    ordering = ["-created_on"]
    # Paginacion
    list_per_page = 20
    # Metodo para mostrar una miniatura de la imagen en la lista
    @admin.display(description="Image")
    def show_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />', obj.image.url)
        return "No image"
    
    show_image.short_description = "Miniature"