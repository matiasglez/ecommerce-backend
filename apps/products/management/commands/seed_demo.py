import html

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils.text import slugify

from apps.products.models import Category, Product
from apps.users.models import User

# Colores de la paleta VOLT
DARK = "#0E0E12"
VOLT = "#C8F400"
ACCENTS = {
    "Calzado": "#2E6BFF",
    "Ropa Deportiva": "#FF5B2E",
    "Entrenamiento": "#C8F400",
    "Accesorios": "#F5B301",
}

DATA = [
    {
        "category": ("Calzado", "Running"),
        "name": "Zapatillas Volt Rush",
        "price": "189999.00",
        "stock": 15,
        "description": "Zapatillas de running con amortiguación media, ideales para entrenamientos de 5 a 15 km. Upper transpirable y suela de agarre multiterreno.",
    },
    {
        "category": ("Calzado", "Básquet"),
        "name": "Zapatillas Full Court",
        "price": "219999.00",
        "stock": 10,
        "description": "Diseñadas para el básquet: soporte en el tobillo, amortiguación en el talón y tracción de cancha adentro y afuera.",
    },
    {
        "category": ("Calzado", "Fútbol"),
        "name": "Botines Grip FG",
        "price": "159999.00",
        "stock": 12,
        "description": "Botines con tapones fijos para césped natural. Material compuesto liviano y ajuste de caña baja.",
    },
    {
        "category": ("Ropa Deportiva", "Remeras"),
        "name": "Remera Dry Fit",
        "price": "34999.00",
        "stock": 40,
        "description": "Remera técnica de secado rápido con costuras planas. Libre de etiquetas molestas, ideal para el día a día de entrenamiento.",
    },
    {
        "category": ("Ropa Deportiva", "Shorts"),
        "name": "Short Entrenamiento",
        "price": "29999.00",
        "stock": 35,
        "description": "Short con cintura elástica y bolsillo portaobjetos. Liviano, con forrería interior y corte holgado.",
    },
    {
        "category": ("Ropa Deportiva", "Buzos"),
        "name": "Buzo Volt Club",
        "price": "74999.00",
        "stock": 20,
        "description": "Abrigo post-entrenamiento con interior cepillado y bolsillos con cierre. Corte slim con el estampado de la marca.",
    },
    {
        "category": ("Entrenamiento", "Fitness"),
        "name": "Pack Cuerdas Fitness",
        "price": "12999.00",
        "stock": 25,
        "description": "Set de 4 cuerdas con manijas ergonómicas para sumar a tus rutinas de fuerza, movilidad y estiramiento.",
    },
    {
        "category": ("Entrenamiento", "Funcional"),
        "name": "Mancuernas Ajustables Home",
        "price": "98999.00",
        "stock": 8,
        "description": "Juego de mancuernas ajustables de 2 a 10 kg por unidad. Rápido cambio de carga con seguro de giro.",
    },
    {
        "category": ("Accesorios", "Botellas"),
        "name": "Botella Térmica 750ml",
        "price": "11499.00",
        "stock": 50,
        "description": "Botella de acero inoxidable de doble pared. Mantiene el agua fría hasta 24 h y libre de BPA.",
    },
    {
        "category": ("Accesorios", "Mochilas"),
        "name": "Mochila Entrenamiento 25L",
        "price": "46999.00",
        "stock": 18,
        "description": "Mochila con compartimento para zapatillas, bolsillo antihumedad y organizador de accesorios. Ideal gimnasio o handball.",
    },
]


def _svg_image(product_name, category_name, accent):
    """Genera una imagen SVG sencilla y deportiva para el producto."""
    label = html.escape(product_name.upper().split(" ")[0])
    cat = html.escape(category_name.upper())
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">
  <rect width="800" height="800" fill="{DARK}"/>
  <polygon points="800,0 800,520 300,800 800,800" fill="{accent}" opacity="0.9"/>
  <polygon points="0,800 0,240 260,800" fill="{accent}" opacity="0.25"/>
  <text x="48" y="120" font-family="Arial, Helvetica, sans-serif" font-size="34" font-weight="bold" letter-spacing="8" fill="{accent}">VOLT</text>
  <text x="48" y="180" font-family="Arial, Helvetica, sans-serif" font-size="22" letter-spacing="4" fill="#8A8A93">/ {cat}</text>
  <text x="48" y="560" font-family="Arial, Helvetica, sans-serif" font-size="120" font-weight="900" letter-spacing="-2" fill="#F5F5F7">{label}</text>
  <rect x="48" y="620" width="120" height="14" fill="{accent}"/>
</svg>"""
    return ContentFile(svg.encode("utf-8"))


class Command(BaseCommand):
    help = "Carga categorias y productos demo con identidad VOLT (idempotente)."

    def _remove_duplicate_products(self):
        # Si dos deploys corren el seed a la vez, get_or_create/create puede
        # duplicar productos (name no es unique). Nos quedamos con el mas
        # antiguo (OrderItem usa SET_NULL, el historial de compras sobrevive).
        duplicated_names = list(
            Product.objects.values("name")
            .annotate(total=Count("id"))
            .filter(total__gt=1)
            .values_list("name", flat=True)
        )
        for name in duplicated_names:
            keep = Product.objects.filter(name=name).order_by("id").first()
            removed = Product.objects.filter(name=name).exclude(pk=keep.pk).count()
            Product.objects.filter(name=name).exclude(pk=keep.pk).delete()
            self.stdout.write(self.style.WARNING(f"Duplicados eliminados de '{name}': {removed}"))

    def handle(self, *args, **options):
        # Self-heal ANTES de upsert: si quedaron duplicados de un deploy
        # anterior, get_or_create lanzaria MultipleObjectsReturned y romperia
        # el deploy.
        self._remove_duplicate_products()

        root_by_slug = {}
        for root_name, accent in ACCENTS.items():
            root, _ = Category.objects.get_or_create(name=root_name)
            root.description = f"Todo en {root_name.lower()} para entrenar al máximo."
            root.save()
            root_by_slug[root.slug] = (root, accent)

        for category, name, price, stock, description in [
            (c["category"], c["name"], c["price"], c["stock"], c["description"]) for c in DATA
        ]:
            root_name, sub_name = category
            root, accent = root_by_slug[slugify(root_name)] if slugify(root_name) in root_by_slug else (Category.objects.get(name=root_name), ACCENTS[root_name])
            sub, _ = Category.objects.get_or_create(name=sub_name, parent=root)
            sub.description = f"{sub_name} · Volt Store"
            sub.save()

            # filter().first() en vez de get_or_create: si un deploy anterior
            # dejo duplicados (o dos seeds corren a la vez), get_or_create
            # lanzaria MultipleObjectsReturned y romperia el deploy.
            product = Product.objects.filter(name=name).order_by("id").first()
            created = product is None
            if created:
                product = Product(name=name)
            product.category = sub
            product.description = description
            product.price = price
            product.stock = stock
            product.is_active = True

            # Las imagenes deben usar nombres estables: si el archivo del seed
            # esta horneado en la imagen Docker, apuntamos directo a ese nombre.
            # Los sufijos de storage se generan en runtime y desaparecen en cada
            # redeploy (el filesystem del contenedor es efimero) -> 404.
            base_name = f"products/{slugify(product.name)}.svg"
            image_name = product.image.name if product.image else ""
            image_ok = bool(image_name) and default_storage.exists(image_name)
            if not image_ok:
                if default_storage.exists(base_name):
                    product.image.name = base_name
                else:
                    product.image.save(
                        f"{slugify(product.name)}.svg",
                        _svg_image(product.name, sub.name, accent),
                        save=False,
                    )
            product.save()

            self.stdout.write(self.style.SUCCESS(f"{'Creado' if created else 'Actualizado'} producto: {product.name}"))

        # Y otra vez al final, por si dos seeds corrieron en paralelo durante
        # este mismo arranque.
        self._remove_duplicate_products()

        if not User.objects.filter(email="admin@voltstore.com").exists():
            User.objects.create_user(
                email="admin@voltstore.com",
                password="Volt123456!",
                is_staff=True,
                is_superuser=True,
            )
            self.stdout.write(self.style.SUCCESS("Creado superusuario demo: admin@voltstore.com / Volt123456!"))

        self.stdout.write(self.style.SUCCESS(
            f"Seed finalizado: {Product.objects.filter(is_active=True).count()} productos activos, "
            f"{Category.objects.count()} categorias."
        ))