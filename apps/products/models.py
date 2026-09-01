from django.db import models
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    
    # Relacion recursiva para subcategorias
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="subcategories"
    )
    
    active = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Categorie"
        verbose_name_plural = "Categories"
        ordering = ["name"]
        
    def __str__(self):
        return self.name
    
    # Autogenera el slug si no se proporciona uno
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
