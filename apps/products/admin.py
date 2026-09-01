from django.contrib import admin
from apps.products.models import Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name", )} # Autocompleta el slug
    
    
