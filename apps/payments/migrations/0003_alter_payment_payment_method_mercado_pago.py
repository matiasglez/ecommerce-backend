# Generated manually for Mercado Pago-only payment methods

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0002_alter_payment_payment_method"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="payment_method",
            field=models.CharField(
                choices=[("MERCADOPAGO", "Mercado Pago")],
                default="MERCADOPAGO",
                max_length=30,
            ),
        ),
    ]
