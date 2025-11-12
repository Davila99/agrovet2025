from django.db import migrations


def create_compact_categories(apps, schema_editor):
    Category = apps.get_model('add', 'Category')

    # Compact picker: 5 categories for veterinaria, 5 for agronomía
    categories = [
        # Veterinaria (5)
        'Veterinaria',
        'Medicamentos veterinarios',
        'Vacunas',
        'Antiparasitarios',
        'Alimentos para animales',

        # Agronomía (5)
        'Semillas',
        'Fertilizantes',
        'Pesticidas y plaguicidas',
        'Maquinaria agrícola',
        'Sistemas de riego',
    ]

    for name in categories:
        Category.objects.get_or_create(name=name)


def remove_compact_categories(apps, schema_editor):
    Category = apps.get_model('add', 'Category')
    names = [
        'Veterinaria',
        'Medicamentos veterinarios',
        'Vacunas',
        'Antiparasitarios',
        'Alimentos para animales',
        'Semillas',
        'Fertilizantes',
        'Pesticidas y plaguicidas',
        'Maquinaria agrícola',
        'Sistemas de riego',
    ]
    for n in names:
        Category.objects.filter(name=n).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('add', '0002_populate_categories'),
    ]

    operations = [
        migrations.RunPython(create_compact_categories, remove_compact_categories),
    ]
