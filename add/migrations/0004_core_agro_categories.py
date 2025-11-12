from django.db import migrations


def create_core_agro_categories(apps, schema_editor):
    Category = apps.get_model('add', 'Category')

    core = [
        'Medicamentos y salud animal',
        'Alimentos y suplementos',
        'Productos para ganado',
        'Semillas y plantas',
        'Fertilizantes y agroquímicos',
        'Maquinaria e implementos',
        'Herramientas e insumos',
        'Servicios agropecuarios',
    ]

    for name in core:
        Category.objects.get_or_create(name=name)


def remove_core_agro_categories(apps, schema_editor):
    Category = apps.get_model('add', 'Category')
    names = [
        'Medicamentos y salud animal',
        'Alimentos y suplementos',
        'Productos para ganado',
        'Semillas y plantas',
        'Fertilizantes y agroquímicos',
        'Maquinaria e implementos',
        'Herramientas e insumos',
        'Servicios agropecuarios',
    ]
    for n in names:
        Category.objects.filter(name=n).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('add', '0003_add_picker_categories'),
    ]

    operations = [
        migrations.RunPython(create_core_agro_categories, remove_core_agro_categories),
    ]
