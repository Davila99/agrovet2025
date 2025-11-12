from django.db import migrations


def create_categories(apps, schema_editor):
    Category = apps.get_model('add', 'Category')

    categories = [
        # Veterinaria sector (~15)
        'Veterinaria',
        'Medicamentos veterinarios',
        'Vacunas',
        'Antiparasitarios',
        'Suplementos nutricionales',
        'Instrumental quirúrgico',
        'Productos de higiene y cuidado',
        'Diagnóstico y laboratorio veterinario',
        'Alimentación para mascotas',
        'Accesorios para mascotas',
        'Servicios veterinarios',
        'Consultoría veterinaria',
        'Reproducción e inseminación',
        'Terapias y rehabilitación',
        'Equipo de hospitalización',

        # Agronomía sector (~15)
        'Semillas',
        'Fertilizantes',
        'Pesticidas y plaguicidas',
        'Herramientas agrícolas',
        'Maquinaria agrícola',
        'Tractores e implementos',
        'Sistemas de riego',
        'Insumos agrícolas',
        'Productos para ganado',
        'Forrajes y alimentos para ganado',
        'Hormonas y reproductores',
        'Agricultura urbana y huertos',
        'Servicios de asesoría agropecuaria',
        'Postcosecha y almacenamiento',
        'Agroquímicos',
    ]

    for name in categories:
        Category.objects.get_or_create(name=name)


def remove_categories(apps, schema_editor):
    Category = apps.get_model('add', 'Category')
    names = [
        'Veterinaria',
        'Medicamentos veterinarios',
        'Vacunas',
        'Antiparasitarios',
        'Suplementos nutricionales',
        'Instrumental quirúrgico',
        'Productos de higiene y cuidado',
        'Diagnóstico y laboratorio veterinario',
        'Alimentación para mascotas',
        'Accesorios para mascotas',
        'Servicios veterinarios',
        'Consultoría veterinaria',
        'Reproducción e inseminación',
        'Terapias y rehabilitación',
        'Equipo de hospitalización',
        'Semillas',
        'Fertilizantes',
        'Pesticidas y plaguicidas',
        'Herramientas agrícolas',
        'Maquinaria agrícola',
        'Tractores e implementos',
        'Sistemas de riego',
        'Insumos agrícolas',
        'Productos para ganado',
        'Forrajes y alimentos para ganado',
        'Hormonas y reproductores',
        'Agricultura urbana y huertos',
        'Services de asesoría agropecuaria',
        'Postcosecha y almacenamiento',
        'Agroquímicos',
    ]
    # Note: reverse attempts to remove by name; if names were edited manually this may not remove them.
    for n in names:
        Category.objects.filter(name=n).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('add', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_categories, remove_categories),
    ]
